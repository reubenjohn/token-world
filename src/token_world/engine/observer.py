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

from token_world.mechanic.trace import ExecutionTrace, TraceNode

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
    "Output the observation text directly. No prefix, no suffix, no JSON wrapping."
)

# Darkness fallback text returned without an LLM call when projection is empty.
_DARKNESS_FALLBACK = "You can sense nothing — only darkness and silence."


def _flatten_mutations(trace: ExecutionTrace) -> list[Any]:
    """Recursively collect all mutations from a trace tree."""

    def _collect(node: TraceNode) -> list[Any]:
        result = list(node.mutations)
        for child in node.children:
            result.extend(_collect(child))
        return result

    return _collect(trace.root)


def _render_chain_truncation_note(trace: ExecutionTrace) -> str:
    """Return a one-line note for the observer when chain was truncated (D-17b)."""
    return (
        f"Note: chain truncated at depth {trace.max_depth_reached} — "
        "Time blurs as events cascade beyond perception."
    )


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

    client: Any  # anthropic.Anthropic | test fake with .messages.create
    model: str = _MODEL
    max_tokens: int = 1024
    last_input_tokens: int = 0  # populated after each synthesize() for tick-summary cost
    last_output_tokens: int = 0

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
        user_prompt = self._build_user_prompt(projection, trace, actor_id, action_text)
        full_prompt = _SYSTEM_PROMPT + "\n\n---\n\n" + user_prompt

        # ---- Call Sonnet (exactly once per synthesize — no internal retry) --
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # ---- Capture token usage (D-24) ------------------------------------
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.last_input_tokens = getattr(usage, "input_tokens", 0)
            self.last_output_tokens = getattr(usage, "output_tokens", 0)

        text = response.content[0].text if response.content else ""

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
    ) -> str:
        """Assemble the user-facing prompt with all data slots (D-26)."""
        lines: list[str] = [
            f"Actor: {actor_id}",
            f"Action attempted: {action_text!r}",
            f"Projected state (JSON): {json.dumps(projection, sort_keys=True)}",
            "Execution outcome:",
        ]

        if trace is not None:
            mutation_count = len(_flatten_mutations(trace))
            lines += [
                f"  - Mechanic: {trace.root.mechanic_id} "
                f"(executed {trace.total_mechanics_executed} mechanics, "
                f"depth {trace.max_depth_reached})",
                f"  - Mutations: {mutation_count} graph changes",
                f"  - Truncated: {trace.truncated}",
            ]
            if trace.truncated:
                lines.append(_render_chain_truncation_note(trace))
        else:
            lines.append("  - No mechanic executed (refusal or yield)")

        return "\n".join(lines)
