"""Unit tests for token_world.engine.models.

Covers ClassifiedAction, ClassifierVerdict discriminated union,
MatchResult, Decision, and TickSummary.
"""

from __future__ import annotations

import json

from pydantic import TypeAdapter

from token_world.engine.models import (
    ClassifiedAction,
    ClassifierVerdict,
    ExecuteDecision,
    MatchedResult,
    MatchResult,
    NoMatchResult,
    RefuseDecision,
    TickSummary,
    VerdictLowConfidence,
    VerdictNoSuchTarget,
    VerdictNoViableAction,
    VerdictOk,
    YieldDecision,
)

# ---------------------------------------------------------------------------
# ClassifiedAction
# ---------------------------------------------------------------------------


def test_classified_action_basic() -> None:
    """Construct with verb/actor/target; params defaults to {}."""
    ca = ClassifiedAction(verb="pickup", actor="alice", target="rock_1")
    assert ca.verb == "pickup"
    assert ca.actor == "alice"
    assert ca.target == "rock_1"
    assert ca.params == {}


def test_classified_action_indirect_object_optional() -> None:
    """indirect_object defaults to None."""
    ca = ClassifiedAction(verb="give", actor="alice")
    assert ca.indirect_object is None


def test_classified_action_ignores_extras() -> None:
    """Extra fields from Haiku output don't crash parsing."""
    data = {
        "verb": "jump",
        "actor": "bob",
        "extra_haiku_field": "should be ignored",
        "another_extra": 42,
    }
    _ca = ClassifiedAction(
        **{
            k: v
            for k, v in data.items()
            if k in ClassifiedAction.model_fields or k == "extra_haiku_field"
        }
    )
    # Must succeed without raising ValidationError
    ca2 = ClassifiedAction.model_validate(data)
    assert ca2.verb == "jump"


def test_classified_action_roundtrip_matches_yield_signal_shape() -> None:
    """ClassifiedAction().model_dump() has verb/actor/target/params keys for YieldSignal."""
    ca = ClassifiedAction(verb="pickup", actor="alice", target="rock_1")
    dump = ca.model_dump()
    # All keys required by YieldSignal.classified_action must be present
    assert "verb" in dump
    assert "actor" in dump
    assert "target" in dump
    assert "params" in dump


# ---------------------------------------------------------------------------
# ClassifierVerdict discriminated union
# ---------------------------------------------------------------------------


_ta = TypeAdapter(ClassifierVerdict)


def test_verdict_ok_parse_from_json() -> None:
    """kind=ok parses to VerdictOk."""
    raw = json.dumps(
        {
            "kind": "ok",
            "classified": {"verb": "pickup", "actor": "alice"},
            "confidence": 0.9,
        }
    )
    verdict = _ta.validate_json(raw)
    assert isinstance(verdict, VerdictOk)
    assert verdict.kind == "ok"
    assert verdict.confidence == 0.9


def test_verdict_no_viable_action_parse_from_json() -> None:
    """kind=no_viable_action parses to VerdictNoViableAction."""
    raw = json.dumps({"kind": "no_viable_action", "reason": "gibberish"})
    verdict = _ta.validate_json(raw)
    assert isinstance(verdict, VerdictNoViableAction)
    assert verdict.reason == "gibberish"


def test_verdict_no_such_target_parse_from_json() -> None:
    """kind=no_such_target parses to VerdictNoSuchTarget."""
    raw = json.dumps({"kind": "no_such_target", "target_text": "the dragon"})
    verdict = _ta.validate_json(raw)
    assert isinstance(verdict, VerdictNoSuchTarget)
    assert verdict.target_text == "the dragon"


def test_verdict_low_confidence_parse_from_json() -> None:
    """kind=low_confidence parses to VerdictLowConfidence."""
    raw = json.dumps(
        {
            "kind": "low_confidence",
            "reason": "ambiguous",
            "confidence": 0.4,
        }
    )
    verdict = _ta.validate_json(raw)
    assert isinstance(verdict, VerdictLowConfidence)
    assert verdict.reason == "ambiguous"


def test_match_result_discriminator() -> None:
    """MatchResult discriminates matched vs no_match correctly."""
    ta = TypeAdapter(MatchResult)
    matched = ta.validate_python(
        {"kind": "matched", "mechanic_id": "pickup", "score": 10, "reasoning": "exact"}
    )
    no_match = ta.validate_python(
        {"kind": "no_match", "classified": {"verb": "pickup", "actor": "alice"}}
    )
    assert isinstance(matched, MatchedResult)
    assert isinstance(no_match, NoMatchResult)


def test_tick_summary_schema_version_is_1() -> None:
    """TickSummary requires schema_version=1."""
    ts = TickSummary(
        tick_id="t1",
        timestamp_iso="2026-01-01T00:00:00Z",
        action_text="pick up rock",
        classified_action=None,
        matched_mechanic_id=None,
        yielded=False,
        refused=False,
        refusal_reason=None,
        mutations={},
        observation_text=None,
        duration_ms=42,
        llm_tokens_by_stage={},
        llm_cost_usd_by_stage={},
    )
    assert ts.schema_version == 1


def test_verdict_ok_extra_fields_ignored() -> None:
    """Extra Haiku fields on ok verdict are silently dropped."""
    raw = json.dumps(
        {
            "kind": "ok",
            "classified": {"verb": "speak", "actor": "alice", "extra_llm_field": "ignored"},
            "confidence": 0.85,
            "some_extra_reasoning": "...",
        }
    )
    verdict = _ta.validate_json(raw)
    assert isinstance(verdict, VerdictOk)
    assert verdict.confidence == 0.85


def test_decision_variants() -> None:
    """Decision union covers execute, yield, and refuse variants."""
    from pydantic import TypeAdapter as TA

    from token_world.engine.models import Decision

    ta = TA(Decision)
    exec_d = ta.validate_python({"kind": "execute", "mechanic_id": "pickup"})
    yield_d = ta.validate_python({"kind": "yield", "classified": {"verb": "x", "actor": "a"}})
    refuse_d = ta.validate_python({"kind": "refuse", "reason_code": "no_viable_action"})
    assert isinstance(exec_d, ExecuteDecision)
    assert isinstance(yield_d, YieldDecision)
    assert isinstance(refuse_d, RefuseDecision)
