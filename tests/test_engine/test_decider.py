"""Tests for the decide() precedence ladder (D-12).

Verifies:
  - Classifier refusals short-circuit to RefuseDecision
  - VerdictOk + MatchedResult → ExecuteDecision
  - VerdictOk + NoMatchResult → YieldDecision
  - Match result is ignored when classifier refuses
  - action_text propagates into RefuseDecision.details
"""

from __future__ import annotations

import pytest

from token_world.engine.decider import decide
from token_world.engine.models import (
    ClassifiedAction,
    ExecuteDecision,
    MatchedResult,
    NoMatchResult,
    RefuseDecision,
    VerdictLowConfidence,
    VerdictNoSuchTarget,
    VerdictNoViableAction,
    VerdictOk,
    YieldDecision,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _classified(verb: str = "take", target: str = "rock") -> ClassifiedAction:
    return ClassifiedAction(verb=verb, actor="player", target=target)


def _matched(mechanic_id: str = "pickup") -> MatchedResult:
    return MatchedResult(mechanic_id=mechanic_id, score=3, reasoning="verb match")


def _no_match(candidates: list[str] | None = None) -> NoMatchResult:
    classified = _classified()
    return NoMatchResult(classified=classified, candidates=candidates or [])


def _verdict_ok(verb: str = "take") -> VerdictOk:
    return VerdictOk(actions=[_classified(verb=verb)], confidence=0.95)


# ---------------------------------------------------------------------------
# Tests: Classifier refusal verdicts
# ---------------------------------------------------------------------------


class TestDeciderClassifierRefusals:
    """Classifier-level refusals always short-circuit to RefuseDecision."""

    def test_no_viable_action_returns_refuse(self) -> None:
        verdict = VerdictNoViableAction(reason="gibberish input")
        result = decide(verdict, None)
        assert isinstance(result, RefuseDecision)
        assert result.reason_code == "no_viable_action"

    def test_no_such_target_returns_refuse(self) -> None:
        verdict = VerdictNoSuchTarget(target_text="invisible dragon")
        result = decide(verdict, None)
        assert isinstance(result, RefuseDecision)
        assert result.reason_code == "no_such_target"

    def test_no_such_target_details_contains_target_text(self) -> None:
        verdict = VerdictNoSuchTarget(target_text="the amulet of yendor")
        result = decide(verdict, None)
        assert isinstance(result, RefuseDecision)
        assert result.details.get("target_text") == "the amulet of yendor"

    def test_low_confidence_returns_refuse(self) -> None:
        verdict = VerdictLowConfidence(reason="ambiguous input", confidence=0.3, best_guess=None)
        result = decide(verdict, None)
        assert isinstance(result, RefuseDecision)
        assert result.reason_code == "low_confidence"

    def test_action_text_propagates_into_refuse_details(self) -> None:
        verdict = VerdictNoViableAction(reason="not a word")
        result = decide(verdict, None, action_text="grumblefizz the orb")
        assert isinstance(result, RefuseDecision)
        assert result.details.get("action_text") == "grumblefizz the orb"

    def test_classifier_refusal_short_circuits_even_if_match_provided(self) -> None:
        """Precedence: classifier wins; match result is ignored."""
        verdict = VerdictNoViableAction(reason="nonsense")
        match = _matched("pickup")
        result = decide(verdict, match)
        # Must still refuse, not execute
        assert isinstance(result, RefuseDecision)
        assert result.reason_code == "no_viable_action"


# ---------------------------------------------------------------------------
# Tests: VerdictOk paths
# ---------------------------------------------------------------------------


class TestDeciderVerdictOkPaths:
    """When classifier says ok, match result determines execute vs yield."""

    def test_verdict_ok_with_matched_returns_execute(self) -> None:
        verdict = _verdict_ok()
        match = _matched("pickup")
        result = decide(verdict, match)
        assert isinstance(result, ExecuteDecision)
        assert result.mechanic_id == "pickup"

    def test_verdict_ok_with_no_match_returns_yield(self) -> None:
        verdict = _verdict_ok()
        match = _no_match()
        result = decide(verdict, match)
        assert isinstance(result, YieldDecision)

    def test_yield_carries_candidates(self) -> None:
        verdict = _verdict_ok()
        match = _no_match(candidates=["mechanic_a", "mechanic_b"])
        result = decide(verdict, match)
        assert isinstance(result, YieldDecision)
        assert result.candidates == ["mechanic_a", "mechanic_b"]

    def test_verdict_ok_without_match_result_raises(self) -> None:
        verdict = _verdict_ok()
        with pytest.raises(ValueError):
            decide(verdict, None)

    def test_execute_mechanic_id_matches_input(self) -> None:
        verdict = _verdict_ok()
        match = _matched("crafting_table_build")
        result = decide(verdict, match)
        assert isinstance(result, ExecuteDecision)
        assert result.mechanic_id == "crafting_table_build"
