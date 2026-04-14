"""Sonnet-backed observation synthesiser (D-15 hard-grounding, Plan 05-05).

Consumes a VisibilityProjector projection + ExecutionTrace and produces grounded
prose the resident agent reads. Refusal narratives pass through unchanged.

Per D-15: the system prompt enumerates a hard grounding constraint so Sonnet does
not invent facts beyond what the projection dict contains. Phase 5 ships the
constraint plus a cheap substring grounding assertion in tests; the full
LLM-verifier rubric is deferred to Phase 6 TEST-04.

Per D-24: token usage is captured on the instance after each synthesize() call
for tick-summary cost accounting.

This module is intentionally NOT wired into a tick pipeline — that is Plan 05-08's
job. Observer here is a self-contained, testable component.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from token_world.engine.llm_backend import (
    AnthropicSDKBackend,
    LLMBackend,
    get_backend,
)
from token_world.mechanic.trace import ExecutionTrace, collect_mutations

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-5-20250929"

# ---------------------------------------------------------------------------
# System prompt — D-15 hard grounding constraint
# The literal phrase "use only facts that appear in the provided state" is
# asserted by test #2 (substring match, not full equality, so wording can evolve
# around it per D-26 researcher discretion).
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = (
    "You are the observation synthesiser for a text-based simulation. Given a\n"
    "projected state dict and an execution trace, write a short (1-3 sentence)\n"
    "second-person prose observation describing what the resident agent now\n"
    "perceives.\n"
    "\n"
    "HARD GROUNDING CONSTRAINT: use only facts that appear in the provided state\n"
    "dict. If a property is not present, do not mention it. Do not invent objects,\n"
    "properties, or sensory details. If the projection is sparse (dark room, no\n"
    "items), describe only the absence — never invent atmosphere.\n"
    "\n"
    "OUTCOME CONSISTENCY: when the execution trace lists graph mutations, the\n"
    "narrative outcome MUST match those mutations. Mutations are ground truth:\n"
    "the action_text is only an intent, the mutations are what actually happened.\n"
    "If a mutation sets ``locked: true -> false`` the object is now unlocked and\n"
    "your narrative must reflect success, even if the action_text sounded hesitant.\n"
    "If a mutation list is empty (no ``locked`` change, no state change to the\n"
    "attempted target), the attempt failed and your narrative must reflect\n"
    "failure — do not invent a positive outcome the graph does not record.\n"
    "\n"
    "Output the observation text directly. No prefix, no suffix, no JSON wrapping."
)

# Darkness fallback text returned without an LLM call when projection is empty.
_DARKNESS_FALLBACK = "You can sense nothing — only darkness and silence."


class _UsageCapturingSDKBackend(AnthropicSDKBackend):
    """SDK backend wrapper that captures the most-recent usage block (D-24).

    Used by :class:`Observer` to preserve ``last_input_tokens`` /
    ``last_output_tokens`` telemetry under the Phase 07.1 ``LLMBackend``
    abstraction. The CLI backend and direct-LLMBackend injection do not
    populate ``_last_usage``; Observer's token counters remain at 0 for those
    paths per CONTEXT D-07 (CLI subscription = no token visibility).

    This subclass lives in ``observer.py`` (not ``llm_backend.py``) because
    Plan 01 owns the backend module and this token-capture escape hatch is
    Observer-specific — the classifier and resident agent do not need it.
    """

    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self._last_usage: dict[str, int] | None = None

    def call(self, *, model: str, system: str, prompt: str, max_tokens: int) -> str:
        resp = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        usage = getattr(resp, "usage", None)
        if usage is not None:
            self._last_usage = {
                "input_tokens": int(getattr(usage, "input_tokens", 0)),
                "output_tokens": int(getattr(usage, "output_tokens", 0)),
            }
        else:
            self._last_usage = None
        if not resp.content:
            return ""
        text: str = resp.content[0].text
        return text


def _render_chain_truncation_note(trace: ExecutionTrace) -> str:
    """Return a one-line note for the observer when chain was truncated (D-17b)."""
    return (
        f"Note: chain truncated at depth {trace.max_depth_reached} — "
        "Time blurs as events cascade beyond perception."
    )


def _format_mutation(mut: Any) -> str:
    """Render a single Mutation as a one-line bullet for the observer prompt.

    Truncates very long values (nested lists of history dicts) so one chatty
    mutation can't blow the Sonnet context budget. We care that the LLM sees
    the *kind* of change (e.g. ``locked: True -> False``), not the full list
    of every past tampering attempt. Short scalar values pass through
    unmodified so boolean flips remain legible.

    Args:
        mut: A :class:`token_world.graph.Mutation` instance (duck-typed to
            avoid an import cycle inside the observer module).

    Returns:
        A single bullet line like ``  - old_chest.locked: True -> False``
        or ``  - mira.inventory: <list of 3> -> <list of 4>`` for bulky lists.
    """
    target = getattr(mut, "target", "?")
    prop = getattr(mut, "property", None)
    old_value = getattr(mut, "old_value", None)
    new_value = getattr(mut, "new_value", None)
    mtype = getattr(mut, "type", "set_property")

    if mtype != "set_property" or prop is None:
        # Structural mutation (add_node/add_edge/remove_*) — render as a label.
        return f"  - {mtype}: {target}"

    def _brief(val: Any) -> str:
        if isinstance(val, list):
            return f"<list of {len(val)}>"
        if isinstance(val, dict):
            return f"<dict with {len(val)} keys>"
        rendered = repr(val)
        if len(rendered) > 80:
            return rendered[:77] + "..."
        return rendered

    return f"  - {target}.{prop}: {_brief(old_value)} -> {_brief(new_value)}"


@dataclass(slots=True)
class Observer:
    """Sonnet-backed observation synthesiser (D-15 hard-grounding).

    Consumes a VisibilityProjector projection + ExecutionTrace and produces a
    grounded prose observation the resident agent reads. Refusal narratives
    pass through unchanged.

    Args:
        client: An ``anthropic.Anthropic`` instance **or** a test fake with a
            ``.messages.create(**kwargs)`` method. Injected via constructor so
            tests can pass a mock without patching the module.
        model: Sonnet model ID. Override per-instance to test against a different
            variant.
        max_tokens: Maximum tokens for the Sonnet response.
        last_input_tokens: Populated after each ``synthesize()`` call (D-24).
        last_output_tokens: Populated after each ``synthesize()`` call (D-24).
    """

    client: Any = None  # deprecated; kept for backward compatibility (D-02)
    model: str = _MODEL
    max_tokens: int = 1024
    last_input_tokens: int = 0  # populated after each synthesize() for tick-summary cost
    last_output_tokens: int = 0
    backend: LLMBackend | None = None

    def __post_init__(self) -> None:
        """Wrap client / default to get_backend() if no backend injected (D-02, D-10).

        Uses :class:`_UsageCapturingSDKBackend` for the auto-wrap path so SDK-backed
        tests continue to see ``last_input_tokens`` / ``last_output_tokens`` populated
        (D-24). The CLI backend and direct-injection paths leave the counters at 0
        per CONTEXT D-07.
        """
        if self.backend is None:
            if self.client is not None:
                object.__setattr__(self, "backend", _UsageCapturingSDKBackend(self.client))
            else:
                object.__setattr__(self, "backend", get_backend())

    @classmethod
    def system_prompt_text(cls) -> str:
        """Return the observer system prompt text (for SHA-256 hash-based change detection)."""
        return _SYSTEM_PROMPT

    def synthesize(
        self,
        *,
        projection: dict[str, dict[str, Any]],
        trace: ExecutionTrace | None,
        refusal_narrative: str | None = None,
        actor_id: str,
        action_text: str = "",
        tick_diag_ctx: Any = None,
        interruption_context: dict | None = None,
    ) -> str:
        """Produce grounded observation text.

        Refusal short-circuit: if ``refusal_narrative`` is provided, return it
        verbatim (no LLM call, no rewriting, no fabrication). Diagnostics still
        write so the operator can see the refusal payload.

        Empty-projection fallback: if ``projection`` is empty or contains only
        the actor entry with no edges / properties beyond identity, return a
        darkness/silence narrative without an LLM call.

        Otherwise: build a grounded prompt from (system + projection JSON +
        trace summary + action_text), call Sonnet once, capture token usage on
        ``self.last_input_tokens / self.last_output_tokens``, write diagnostics
        if ``tick_diag_ctx`` is provided, and return the response text.

        Args:
            projection: Visibility-projected state dict from
                ``VisibilityProjector.project_for(actor_id)``.
            trace: The execution trace from the chain engine, or ``None`` if
                the tick did not execute (refusal, yield).
            refusal_narrative: Pre-rendered refusal text from
                ``RefusalTemplate.render()``; passed through verbatim.
            actor_id: The resident agent's node ID.
            action_text: The free-form action text from the resident agent.
            tick_diag_ctx: Optional ``TickDiagnostics`` context. When provided,
                ``write_observation(prompt, response, parsed)`` is called once.
            interruption_context: Optional Phase 7 long-running action context dict
                (D-10, D-21). When non-None, a context block is prepended to the
                user prompt so Sonnet can ground the interruption/completion narrative.
                Shape: ``{"interrupted_by": {...}, "long_action": str}`` for
                interruptions, or ``{"completed": True, "long_action": str}`` for
                completions.

        Returns:
            Observation text string. Always non-empty.
        """
        # ---- Refusal short-circuit ----------------------------------------
        if refusal_narrative is not None:
            if tick_diag_ctx is not None:
                tick_diag_ctx.write_observation(
                    prompt="(refusal short-circuit — no LLM call)",
                    response=refusal_narrative,
                    parsed={"text": refusal_narrative, "source": "refusal_template"},
                )
            return refusal_narrative

        # ---- Empty-projection fallback ------------------------------------
        if self._is_empty_projection(projection):
            fallback = _DARKNESS_FALLBACK
            if tick_diag_ctx is not None:
                tick_diag_ctx.write_observation(
                    prompt="(empty-projection fallback — no LLM call)",
                    response=fallback,
                    parsed={"text": fallback, "source": "empty_projection_fallback"},
                )
            return fallback

        # ---- Build prompt ---------------------------------------------------
        user_prompt = self._build_user_prompt(
            projection, trace, actor_id, action_text, interruption_context
        )
        full_prompt = _SYSTEM_PROMPT + "\n\n---\n\n" + user_prompt

        # ---- Call Sonnet via LLMBackend (exactly once — no internal retry) --
        assert self.backend is not None  # __post_init__ guarantees this
        text = self.backend.call(
            model=self.model,
            system=_SYSTEM_PROMPT,
            prompt=user_prompt,
            max_tokens=self.max_tokens,
        )

        # ---- Capture token usage (D-24, adjusted for LLMBackend abstraction) -
        # Only _UsageCapturingSDKBackend (the SDK auto-wrap path) exposes
        # _last_usage; CLI / direct-injection backends leave counters at 0
        # per CONTEXT D-07 (CLI subscription does not expose token counts).
        last_usage = getattr(self.backend, "_last_usage", None)
        if last_usage is not None:
            self.last_input_tokens = int(last_usage.get("input_tokens", 0))
            self.last_output_tokens = int(last_usage.get("output_tokens", 0))

        # ---- Diagnostics (D-22, D-23) ------------------------------------
        if tick_diag_ctx is not None:
            tick_diag_ctx.write_observation(
                prompt=full_prompt,
                response=text,
                parsed={"text": text, "source": "sonnet_synthesis"},
            )

        return text

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_empty_projection(self, projection: dict[str, Any]) -> bool:
        """Return True if the projection is effectively empty (dark room / no content).

        An empty projection is:
        - An empty dict, or
        - A single-entry dict for the actor alone with no edges and at most 2
          properties (just identity — no meaningful observable world state).
        """
        if not projection:
            return True
        if len(projection) == 1:
            only_entry = next(iter(projection.values()))
            if not only_entry.get("edges") and len(only_entry.get("properties", {})) <= 2:
                return True
        return False

    def _build_user_prompt(
        self,
        projection: dict[str, dict[str, Any]],
        trace: ExecutionTrace | None,
        actor_id: str,
        action_text: str,
        interruption_context: dict | None = None,
    ) -> str:
        """Assemble the user-facing prompt with all data slots (D-26).

        Phase 7 (D-10, D-21): when interruption_context is provided, prepend a
        context block describing the long-running action outcome so Sonnet can
        ground the narrative in the cause of interruption or completion.
        """
        lines: list[str] = []
        # Phase 7 D-10, D-21: interruption/completion context block
        if interruption_context is not None:
            long_action = interruption_context.get("long_action", "")
            if interruption_context.get("completed"):
                lines.append(
                    f"Context: the agent has finished a long-running action: {long_action!r}. "
                    "Write a second-person narrative grounded in the projected state describing "
                    "what they now perceive as the action concludes."
                )
            elif "interrupted_by" in interruption_context:
                iby = interruption_context["interrupted_by"]
                prop = iby.get("property", "?")
                op = iby.get("op", "?")
                val = iby.get("value", "?")
                lines.append(
                    f"Context: the agent was interrupted while: {long_action!r}. "
                    f"The interruption was triggered by: {prop} {op} {val}. "
                    "Write a second-person narrative grounded in the projected state describing "
                    "what interrupted them and what they now perceive."
                )
            lines.append("")  # blank separator

        lines += [
            f"Actor: {actor_id}",
            f"Action attempted: {action_text!r}",
            f"Projected state (JSON): {json.dumps(projection, sort_keys=True)}",
            "Execution outcome:",
        ]

        if trace is not None:
            mutations = collect_mutations(trace)
            lines += [
                f"  - Mechanic: {trace.root.mechanic_id} "
                f"(executed {trace.total_mechanics_executed} mechanics, "
                f"depth {trace.max_depth_reached})",
                f"  - Mutations: {len(mutations)} graph changes",
            ]
            # E4 grounding fix: include actual mutation content so the LLM can
            # narrate success vs failure from ground truth instead of guessing
            # from the action_text. Without this, the observer saw only a
            # count ("3 graph changes") and could freely invent outcomes
            # contradicting the graph (willowbrook tick 32/35 drift).
            for mut in mutations:
                lines.append(_format_mutation(mut))
            lines.append(f"  - Truncated: {trace.truncated}")
            if trace.truncated:
                lines.append(_render_chain_truncation_note(trace))
        else:
            lines.append("  - No mechanic executed (refusal or yield)")

        return "\n".join(lines)
