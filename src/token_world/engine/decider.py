"""Decider — precedence ladder from classifier verdict + match result to Decision (D-12).

The ladder:
    1. Classifier refusal → RefuseDecision
    2. Match succeeded   → ExecuteDecision
    3. Match failed      → YieldDecision

Yield is last because it's the expensive path (operator spawns Opus subagent).
"""

from __future__ import annotations

from token_world.engine.models import (
    ClassifierVerdict,
    Decision,
    ExecuteDecision,
    MatchedResult,
    MatchResult,
    NoMatchResult,
    RefuseDecision,
    VerdictLowConfidence,
    VerdictNoSuchTarget,
    VerdictNoViableAction,
    VerdictOk,
    YieldDecision,
)


def decide(
    verdict: ClassifierVerdict,
    match_result: MatchResult | None,
    *,
    action_text: str = "",
) -> Decision:
    """Compute the engine decision from classifier + matcher outputs (D-12).

    Args:
        verdict: The output of the classifier stage.
        match_result: The output of the matcher stage. Required when
            ``verdict`` is :class:`VerdictOk`; may be ``None`` for refusal
            verdicts (the matcher is never run in those cases).
        action_text: The raw action text from the resident agent. Carried
            into :class:`RefuseDecision`.details so the observer can include
            what the agent tried in the narrative.

    Returns:
        A :class:`Decision` — one of :class:`ExecuteDecision`,
        :class:`YieldDecision`, or :class:`RefuseDecision`.

    Raises:
        ValueError: If verdict is :class:`VerdictOk` but ``match_result``
            is ``None``.
        TypeError: If ``verdict`` or ``match_result`` is an unrecognised type
            (should never happen with Pydantic-validated inputs).
    """
    # Ladder rung 1: classifier-level refusal
    if isinstance(verdict, VerdictNoViableAction):
        return RefuseDecision(
            reason_code="no_viable_action",
            details={"action_text": action_text, "reason": verdict.reason},
        )
    if isinstance(verdict, VerdictNoSuchTarget):
        return RefuseDecision(
            reason_code="no_such_target",
            details={"target_text": verdict.target_text, "action_text": action_text},
        )
    if isinstance(verdict, VerdictLowConfidence):
        return RefuseDecision(
            reason_code="low_confidence",
            details={"action_text": action_text, "reason": verdict.reason},
        )

    # Verdict is VerdictOk → match_result must be provided
    if not isinstance(verdict, VerdictOk):
        # Defensive: Pydantic validated types, but keep mypy exhaustive
        raise TypeError(f"Unexpected verdict type: {type(verdict).__name__}")
    if match_result is None:
        raise ValueError("match_result required when verdict is VerdictOk")

    # Ladder rung 2: execute
    if isinstance(match_result, MatchedResult):
        return ExecuteDecision(mechanic_id=match_result.mechanic_id)

    # Ladder rung 3: yield
    if isinstance(match_result, NoMatchResult):
        return YieldDecision(
            classified=match_result.classified,
            candidates=list(match_result.candidates),
        )

    raise TypeError(f"Unexpected match_result type: {type(match_result).__name__}")
