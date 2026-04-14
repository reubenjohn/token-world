"""Tests for TurnScorer D-12 rubric metrics (Task 2)."""

from __future__ import annotations


def _make_tick_result(
    kind: str,
    *,
    observation: str | None = None,
    projected_state: dict | None = None,
    trace=None,
    refusal_reason: str | None = None,
):
    """Construct a TickResult-like mock with the required fields."""
    from token_world.engine.engine import TickResult

    if kind == "ok":
        return TickResult.ok(
            tick_id="tick_1",
            observation=observation or "You look around.",
            trace=trace,
            projected_state=projected_state,
        )
    elif kind == "yielded":
        from token_world.operator.yield_signal import YieldSignal

        signal = YieldSignal(
            tick_id="tick_1",
            universe_path="/tmp/test",
            action_text="look",
            classified_action={"verb": "look", "target": None, "params": {}},
            actor_state={},
            candidate_mechanic_ids=[],
        )
        return TickResult.yielded(tick_id="tick_1", signal=signal)
    elif kind == "refused":
        return TickResult.refused(
            tick_id="tick_1",
            observation=observation or "You cannot do that.",
            refusal_reason=refusal_reason or "no_viable_action",
        )
    raise ValueError(f"Unknown kind: {kind!r}")


def _make_trace_with_mutations(mutation_count: int):
    """Create a minimal ExecutionTrace with the given number of mutations."""
    from token_world.graph.models import Mutation
    from token_world.mechanic.trace import CheckResult, ExecutionTrace, TraceNode

    mutations = [
        Mutation(
            type="set_property",
            target=f"node_{i}",
            property="prop",
            old_value=None,
            new_value="new",
        )
        for i in range(mutation_count)
    ]
    root = TraceNode(
        mechanic_id="test_mechanic",
        actor="alice",
        target="alice",
        check_result=CheckResult(passed=True, reasons=[]),
        mutations=mutations,
    )
    return ExecutionTrace(
        root=root,
        total_mechanics_executed=1,
        max_depth_reached=1,
        truncated=False,
    )


# ---------------------------------------------------------------------------
# mechanic_match_rate tests (12-14)
# ---------------------------------------------------------------------------


def test_mechanic_match_rate_ok_is_one() -> None:
    """Test 12: ok result -> mechanic_match_rate == 1.0."""
    from token_world.playtest import TurnScorer

    result = _make_tick_result("ok", trace=_make_trace_with_mutations(1))
    scorer = TurnScorer()
    score = scorer.score(
        result=result,
        action_text="look around",
        action_history=[],
        previous_non_refusal_count=0,
        total_turns_so_far=0,
    )
    assert score.mechanic_match_rate == 1.0


def test_mechanic_match_rate_yielded_is_zero() -> None:
    """Test 13: yielded result -> mechanic_match_rate == 0.0."""
    from token_world.playtest import TurnScorer

    result = _make_tick_result("yielded")
    scorer = TurnScorer()
    score = scorer.score(
        result=result,
        action_text="unknown action",
        action_history=[],
        previous_non_refusal_count=0,
        total_turns_so_far=0,
    )
    assert score.mechanic_match_rate == 0.0


def test_mechanic_match_rate_refused_is_half() -> None:
    """Test 14: refused result -> mechanic_match_rate == 0.5."""
    from token_world.playtest import TurnScorer

    result = _make_tick_result("refused")
    scorer = TurnScorer()
    score = scorer.score(
        result=result,
        action_text="bad action",
        action_history=[],
        previous_non_refusal_count=0,
        total_turns_so_far=0,
    )
    assert score.mechanic_match_rate == 0.5


def test_mechanic_match_rate_refused_check_failed_is_one() -> None:
    """§E6: refused with reason=mechanic_check_failed scores like ok (1.0).

    A mechanic was matched and dispatched — only its runtime precondition
    check returned passed=False. Avoid double-penalising an honest refusal
    that previously looked like a successful 0-mutation execute.
    """
    from token_world.playtest import TurnScorer

    result = _make_tick_result("refused", refusal_reason="mechanic_check_failed")
    scorer = TurnScorer()
    score = scorer.score(
        result=result,
        action_text="pick up the rock",
        action_history=[],
        previous_non_refusal_count=0,
        total_turns_so_far=0,
    )
    assert score.mechanic_match_rate == 1.0


# ---------------------------------------------------------------------------
# observation_groundedness tests (15-17)
# ---------------------------------------------------------------------------


def test_groundedness_one_when_projection_nodeid_in_observation() -> None:
    """Test 15: projection node id appears in observation -> 1.0."""
    from token_world.playtest import TurnScorer

    result = _make_tick_result(
        "ok",
        observation="Alice moves into the room",
        projected_state={"alice": {"properties": {}}, "room": {"properties": {}}},
        trace=_make_trace_with_mutations(1),
    )
    scorer = TurnScorer()
    score = scorer.score(
        result=result,
        action_text="move",
        action_history=[],
        previous_non_refusal_count=0,
        total_turns_so_far=0,
    )
    assert score.observation_groundedness == 1.0


def test_groundedness_half_when_projection_empty_or_none() -> None:
    """Test 16: projected_state is None or empty dict -> 0.5."""
    from token_world.playtest import TurnScorer

    scorer = TurnScorer()

    # None case
    result_none = _make_tick_result(
        "ok",
        observation="You look around.",
        projected_state=None,
        trace=_make_trace_with_mutations(0),
    )
    score_none = scorer.score(
        result=result_none,
        action_text="look",
        action_history=[],
        previous_non_refusal_count=0,
        total_turns_so_far=0,
    )
    assert score_none.observation_groundedness == 0.5

    # Empty dict case
    result_empty = _make_tick_result(
        "ok",
        observation="You look around.",
        projected_state={},
        trace=_make_trace_with_mutations(0),
    )
    score_empty = scorer.score(
        result=result_empty,
        action_text="look",
        action_history=[],
        previous_non_refusal_count=0,
        total_turns_so_far=0,
    )
    assert score_empty.observation_groundedness == 0.5


def test_groundedness_half_when_no_node_found_in_observation() -> None:
    """Test 17: projected_state keys don't appear in observation -> 0.5."""
    from token_world.playtest import TurnScorer

    result = _make_tick_result(
        "ok",
        observation="You see nothing interesting.",
        projected_state={"alice": {"properties": {}}, "chest_a7": {"properties": {}}},
        trace=_make_trace_with_mutations(1),
    )
    scorer = TurnScorer()
    score = scorer.score(
        result=result,
        action_text="look",
        action_history=[],
        previous_non_refusal_count=0,
        total_turns_so_far=0,
    )
    assert score.observation_groundedness == 0.5


# ---------------------------------------------------------------------------
# mutation_count tests (18-20)
# ---------------------------------------------------------------------------


def test_mutation_count_one_when_mutations_present() -> None:
    """Test 18: trace with >= 1 mutation -> mutation_count == 1.0."""
    from token_world.playtest import TurnScorer

    result = _make_tick_result("ok", trace=_make_trace_with_mutations(3))
    scorer = TurnScorer()
    score = scorer.score(
        result=result,
        action_text="pick up lantern",
        action_history=[],
        previous_non_refusal_count=0,
        total_turns_so_far=0,
    )
    assert score.mutation_count == 1.0


def test_mutation_count_half_when_trace_exists_but_empty() -> None:
    """Test 19: trace with 0 mutations -> 0.5."""
    from token_world.playtest import TurnScorer

    result = _make_tick_result("ok", trace=_make_trace_with_mutations(0))
    scorer = TurnScorer()
    score = scorer.score(
        result=result,
        action_text="wait",
        action_history=[],
        previous_non_refusal_count=0,
        total_turns_so_far=0,
    )
    assert score.mutation_count == 0.5


def test_mutation_count_zero_when_refused() -> None:
    """Test 20: refused result (trace None) -> mutation_count == 0.0."""
    from token_world.playtest import TurnScorer

    result = _make_tick_result("refused")
    scorer = TurnScorer()
    score = scorer.score(
        result=result,
        action_text="bad action",
        action_history=[],
        previous_non_refusal_count=0,
        total_turns_so_far=0,
    )
    assert score.mutation_count == 0.0


# ---------------------------------------------------------------------------
# refusal_rate tests (21)
# ---------------------------------------------------------------------------


def test_refusal_rate_inverse_ratio() -> None:
    """Test 21: after 10 turns with 2 refusals, refusal_rate = 8/10 = 0.8."""
    from token_world.playtest import TurnScorer

    # Simulating: 8 non-refusals happened in previous turns (previous_non_refusal_count=8)
    # Now we're on total_turns_so_far=9 (0-indexed), about to do non-refusal turn
    # Result: (8 + 1) / (9 + 1) = 9/10 = 0.9
    # For the test: 2 refusals out of 10 total means 8 non-refusals
    # On the 10th turn (total_turns_so_far=9), if previous=8 non-refusals and current is ok:
    # (8 + 1) / (9 + 1) = 0.9
    # But the test says 8/10 = 0.8, meaning current is a refusal:
    # (8 + 0) / (9 + 1) = 0.8 ✓
    scorer = TurnScorer()
    result = _make_tick_result("refused")  # current turn is a refusal
    score = scorer.score(
        result=result,
        action_text="bad action",
        action_history=[],
        previous_non_refusal_count=8,  # 8 non-refusals before this turn
        total_turns_so_far=9,  # this is turn index 9 (0-based), total=10
    )
    assert score.refusal_rate == pytest.approx(0.8, abs=0.001)


# ---------------------------------------------------------------------------
# action_novelty tests (22-24)
# ---------------------------------------------------------------------------


def test_action_novelty_one_for_first_turn() -> None:
    """Test 22: empty action_history -> novelty == 1.0."""
    from token_world.playtest import TurnScorer

    result = _make_tick_result("ok", trace=_make_trace_with_mutations(1))
    scorer = TurnScorer()
    score = scorer.score(
        result=result,
        action_text="look around",
        action_history=[],
        previous_non_refusal_count=0,
        total_turns_so_far=0,
    )
    assert score.action_novelty == 1.0


def test_action_novelty_zero_for_identical_repeat() -> None:
    """Test 23: identical action in history -> novelty close to 0."""
    from token_world.playtest import TurnScorer

    result = _make_tick_result("ok", trace=_make_trace_with_mutations(1))
    scorer = TurnScorer()
    score = scorer.score(
        result=result,
        action_text="walk east",
        action_history=["walk east"],
        previous_non_refusal_count=1,
        total_turns_so_far=1,
    )
    # Cosine of identical bags = 1.0, novelty = 1 - 1.0 = 0.0
    assert score.action_novelty == pytest.approx(0.0, abs=0.001)


def test_action_novelty_between_for_partial_overlap() -> None:
    """Test 24: partial word overlap -> novelty between 0.1 and 0.9."""
    from token_world.playtest import TurnScorer

    result = _make_tick_result("ok", trace=_make_trace_with_mutations(1))
    scorer = TurnScorer()
    score = scorer.score(
        result=result,
        action_text="walk west",
        action_history=["walk east"],
        previous_non_refusal_count=1,
        total_turns_so_far=1,
    )
    # "walk west" vs "walk east" share "walk" -> partial cosine
    assert 0.1 < score.action_novelty < 0.9


# ---------------------------------------------------------------------------
# composite and dump tests (25-26)
# ---------------------------------------------------------------------------


def test_composite_is_mean_of_five_metrics() -> None:
    """Test 25: composite = mean of 5 metrics."""
    from token_world.playtest import TurnScore

    score = TurnScore(
        mechanic_match_rate=0.5,
        observation_groundedness=1.0,
        mutation_count=1.0,
        refusal_rate=1.0,
        action_novelty=0.5,
        composite=(0.5 + 1.0 + 1.0 + 1.0 + 0.5) / 5,
    )
    assert score.composite == pytest.approx(0.8, abs=0.001)


def test_turn_score_model_dump_has_all_fields() -> None:
    """Test 26: model_dump has exactly the 6 expected fields."""
    from token_world.playtest import TurnScore

    score = TurnScore(
        mechanic_match_rate=1.0,
        observation_groundedness=1.0,
        mutation_count=1.0,
        refusal_rate=1.0,
        action_novelty=1.0,
        composite=1.0,
    )
    dumped = score.model_dump()
    expected_keys = {
        "mechanic_match_rate",
        "observation_groundedness",
        "mutation_count",
        "refusal_rate",
        "action_novelty",
        "composite",
    }
    assert set(dumped.keys()) == expected_keys


import pytest  # noqa: E402 -- needs to be after test definitions that use pytest.approx
