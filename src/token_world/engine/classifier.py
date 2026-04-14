"""Haiku-backed action classifier (D-04, D-05, D-06).

Wraps :class:`anthropic.Anthropic` raw SDK to turn free-form resident-agent
action text into a :class:`ClassifierVerdict`. Pydantic-validated JSON output;
one retry on malformed response before giving up with ``no_viable_action``.

Diagnostics: every call optionally writes prompt/response/parsed into a
:class:`DiagnosticsSink` tick context (Phase 4 AUTO-02).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from pydantic import TypeAdapter, ValidationError

from token_world.engine.llm_backend import (
    AnthropicSDKBackend,
    LLMBackend,
    get_backend,
)
from token_world.engine.models import (
    ClassifierVerdict,
    VerdictLowConfidence,
    VerdictNoSuchTarget,
    VerdictNoViableAction,
    VerdictOk,
)

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = (
    "You are the action classifier for a text-based simulation. Given a resident\n"
    "agent's natural-language action, output a JSON object with one of four shapes:\n"
    "\n"
    '{"kind":"ok","classified":{"verb":"<verb>","actor":"<actor id>","target":"<target id|null>",'  # noqa: E501
    '"indirect_object":"<recipient id|null>","params":{}},"confidence":0.0-1.0}\n'
    '{"kind":"no_viable_action","reason":"<why the input is unprocessable>"}\n'
    '{"kind":"no_such_target","target_text":"<text for which the graph has no node>"}\n'  # noqa: E501
    '{"kind":"low_confidence","reason":"<why>","best_guess":{...classified...},"confidence":0.0-1.0}\n'  # noqa: E501
    "\n"
    "The provided `Available verbs` list is a hint, NOT a constraint. Always\n"
    "classify the action with its most natural single verb. If that verb happens\n"
    "to be in the list, great — the engine will match an existing mechanic. If\n"
    "it is not in the list, classify it anyway; the engine will yield to the\n"
    "operator to author a new mechanic. Either way, emit `kind:ok` with the\n"
    "natural verb. Examples:\n"
    "  action 'I water the garden' → ok, verb='water' (even if not listed)\n"
    "  action 'I draw water from the well' → ok, verb='draw'\n"
    "  action 'I hum to the fire' → ok, verb='hum'\n"
    "Use ONLY actor/target node IDs from the provided list for target/actor fields.\n"
    'ONLY emit "no_viable_action" when the input is genuine gibberish (e.g.\n'
    "'asdfqwerty') or has no coherent intent. An action with a clear verb that\n"
    "happens not to be in the list is NOT grounds for no_viable_action.\n"
    "If you can identify a target TEXT but it maps to no known node ID, emit\n"
    '"no_such_target". Emit ONLY the JSON object -- no prose.\n'
)

_VERDICT_ADAPTER: TypeAdapter[ClassifierVerdict] = TypeAdapter(ClassifierVerdict)


def _strip_markdown_fence(raw: str) -> str:
    """Strip ```[lang]\\n...\\n``` fences from a response.

    The ``claude-cli`` backend (Phase 7.1) sometimes wraps JSON in markdown
    code fences even when the system prompt says "JSON only." Handles both
    language-tagged (```json) and bare (```) fences, plus multiple stacked
    fences (rare). Returns ``raw`` unchanged when no fence is found.
    """
    s = raw.strip()
    # Repeatedly peel leading/trailing fences. Common case: one pair.
    for _ in range(3):  # bound iterations — defense against pathological input
        if s.startswith("```"):
            # drop first line (``` or ```json)
            newline = s.find("\n")
            s = s[newline + 1 :] if newline != -1 else s[3:]
            s = s.strip()
        if s.endswith("```"):
            s = s[:-3].rstrip()
        else:
            break
    return s


@dataclass(slots=True)
class Classifier:
    """Haiku-backed classifier with retry-once-on-malformed."""

    client: Any = None  # deprecated; kept for backward compatibility (D-02)
    model: str = _MODEL
    max_tokens: int = 1024
    backend: LLMBackend | None = None

    def __post_init__(self) -> None:
        """Wrap client / default to get_backend() if no backend injected (D-02, D-10)."""
        if self.backend is None:
            if self.client is not None:
                object.__setattr__(self, "backend", AnthropicSDKBackend(self.client))
            else:
                object.__setattr__(self, "backend", get_backend())

    @classmethod
    def system_prompt_text(cls) -> str:
        """Return the classifier system prompt text (for SHA-256 hash-based change detection)."""
        return _SYSTEM_PROMPT

    def classify(
        self,
        action_text: str,
        actor: str,
        *,
        available_verbs: list[str],
        known_node_ids: list[str],
        min_confidence: float = 0.6,
        tick_diag_ctx: Any = None,  # optional DiagnosticsSink tick context
    ) -> ClassifierVerdict:
        """Classify a resident-agent action into a structured verdict.

        Args:
            action_text: Free-form text from the resident agent.
            actor: Node ID of the acting agent.
            available_verbs: Verbs from the current mechanic registry.
            known_node_ids: All node IDs currently in the knowledge graph.
            min_confidence: Ok verdicts below this threshold become low_confidence.
            tick_diag_ctx: Optional diagnostics sink receiving prompt/response/parsed.

        Returns:
            A :class:`ClassifierVerdict` (one of four variants).
        """
        user_prompt = self._build_user_prompt(action_text, actor, available_verbs, known_node_ids)
        if tick_diag_ctx is not None:
            tick_diag_ctx.write_prompt(
                "classification", _SYSTEM_PROMPT + "\n\n---\n\n" + user_prompt
            )

        # First attempt
        raw = self._send(user_prompt, tick_diag_ctx=tick_diag_ctx)
        verdict = self._parse(raw)
        if verdict is None:
            # Retry once with a corrective prompt
            corrective = (
                user_prompt + "\n\nYour prior response could not be parsed. "
                "Emit ONLY valid JSON matching one of the shapes specified."
            )
            raw = self._send(corrective, tick_diag_ctx=tick_diag_ctx, attempt=2)
            verdict = self._parse(raw)
        if verdict is None:
            verdict = VerdictNoViableAction(reason="classifier output malformed after retry")

        # Post-processing: confidence threshold + known-node target check
        verdict = self._apply_confidence_threshold(verdict, min_confidence)
        verdict = self._apply_known_target_check(verdict, known_node_ids)

        if tick_diag_ctx is not None:
            tick_diag_ctx.write_parsed("classification", json.loads(verdict.model_dump_json()))
        return verdict

    def _build_user_prompt(
        self,
        action_text: str,
        actor: str,
        available_verbs: list[str],
        known_node_ids: list[str],
    ) -> str:
        return (
            f"Actor: {actor}\n"
            f"Available verbs: {sorted(available_verbs)}\n"
            f"Known node IDs: {sorted(known_node_ids)}\n"
            f"Action text: {action_text!r}\n"
        )

    def _send(self, user_prompt: str, *, tick_diag_ctx: Any, attempt: int = 1) -> str:
        assert self.backend is not None  # __post_init__ guarantees this
        raw = self.backend.call(
            model=self.model,
            system=_SYSTEM_PROMPT,
            prompt=user_prompt,
            max_tokens=self.max_tokens,
        )
        if tick_diag_ctx is not None:
            tick_diag_ctx.write_response(
                "classification",
                raw,
                suffix=f"_attempt{attempt}" if attempt > 1 else "",
            )
        return raw

    def _parse(self, raw: str) -> ClassifierVerdict | None:
        raw_stripped = _strip_markdown_fence(raw).strip()
        if not raw_stripped:
            return None
        try:
            return _VERDICT_ADAPTER.validate_json(raw_stripped)
        except (ValidationError, json.JSONDecodeError, ValueError) as e:
            logger.debug("Classifier parse failed: %s", e)
            return None

    def _apply_confidence_threshold(
        self, verdict: ClassifierVerdict, min_confidence: float
    ) -> ClassifierVerdict:
        if isinstance(verdict, VerdictOk) and verdict.confidence < min_confidence:
            return VerdictLowConfidence(
                reason=(
                    f"classifier confidence {verdict.confidence:.2f} "
                    f"below threshold {min_confidence:.2f}"
                ),
                best_guess=verdict.classified,
                confidence=verdict.confidence,
            )
        return verdict

    def _apply_known_target_check(
        self, verdict: ClassifierVerdict, known_node_ids: list[str]
    ) -> ClassifierVerdict:
        if not isinstance(verdict, VerdictOk):
            return verdict
        classified = verdict.classified
        # Check target (direct object)
        if classified.target is not None and classified.target not in known_node_ids:
            return VerdictNoSuchTarget(target_text=classified.target)
        # Check indirect_object (GAP-ENG02 — ditransitive verbs like give/teach)
        if (
            classified.indirect_object is not None
            and classified.indirect_object not in known_node_ids
        ):
            return VerdictNoSuchTarget(target_text=classified.indirect_object)
        return verdict
