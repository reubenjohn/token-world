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
    "Use ONLY verbs from the provided list. Use ONLY actor/target node IDs from the\n"
    "provided list. If the input is gibberish or otherwise unprocessable, emit\n"
    '"no_viable_action". If you can identify a target TEXT but it maps to no known\n'
    'node ID, emit "no_such_target". Emit ONLY the JSON object -- no prose.\n'
)

_VERDICT_ADAPTER: TypeAdapter[ClassifierVerdict] = TypeAdapter(ClassifierVerdict)


@dataclass(slots=True)
class Classifier:
    """Haiku-backed classifier with retry-once-on-malformed."""

    client: Any  # anthropic.Anthropic | a test fake with .messages.create
    model: str = _MODEL
    max_tokens: int = 1024

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
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = response.content[0].text if response.content else ""
        if tick_diag_ctx is not None:
            tick_diag_ctx.write_response(
                "classification",
                raw,
                suffix=f"_attempt{attempt}" if attempt > 1 else "",
            )
        return raw

    def _parse(self, raw: str) -> ClassifierVerdict | None:
        raw_stripped = raw.strip()
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
