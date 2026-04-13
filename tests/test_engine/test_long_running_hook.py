"""Tests for LongRunningHook and HookResult (Task 1, Plan 07-04).

Uses FakeObserver to test hook orchestration in isolation. No engine.py changes yet.

D-06: Hook advances turns_elapsed, evaluates thresholds, emits observation.
D-20: LongRunningHook is a class in long_running_hook.py.
D-22: "Time passes" observation is a static template for continuing case.
D-10: Interruption/completion observations go through observer.synthesize().
Pitfall 1: Hook only runs on continuation path; insta-cancel is impossible
           because begin_long_action tick never calls the hook.
"""

from __future__ import annotations

from token_world.engine.long_running import ThresholdSpec
from token_world.engine.long_running_hook import LongRunningHook
from token_world.graph import KnowledgeGraph

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class FakeObserver:
    """Records synthesize() kwargs; returns fixed text."""

    def __init__(self, text: str = "fake observation") -> None:
        self.text = text
        self.calls: list[dict] = []

    def synthesize(self, **kwargs) -> str:  # noqa: ANN002
        self.calls.append(kwargs)
        return self.text


def _make_kg() -> KnowledgeGraph:
    return KnowledgeGraph(db_path=None)


def _actor_with_lra(
    kg: KnowledgeGraph,
    actor: str = "alice",
    *,
    action_text: str = "sleeping",
    turns_total: int | None = 8,
    turns_elapsed: int = 0,
    thresholds: list[dict] | None = None,
    attention_state: dict | None = None,
) -> None:
    if not kg.has_node(actor):
        kg.add_node(actor, node_type="agent")
    payload: dict = {}
    if attention_state is not None:
        payload["attention_state"] = attention_state
    kg.set(
        actor,
        "current_long_action",
        {
            "action_text": action_text,
            "turns_total": turns_total,
            "turns_elapsed": turns_elapsed,
            "thresholds": thresholds or [],
            "payload": payload,
        },
    )


def _make_hook() -> LongRunningHook:
    return LongRunningHook()


def _make_projection(
    *,
    actor: str = "alice",
    room_id: str = "bedroom",
    noise_level: float = 0.3,
) -> dict:
    return {
        actor: {"type": "agent", "properties": {}, "edges": []},
        room_id: {
            "type": "entity",
            "properties": {"noise_level": noise_level},
            "edges": [],
        },
    }


# ---------------------------------------------------------------------------
# Test: inactive cases (graceful no-op)
# ---------------------------------------------------------------------------


def test_hook_returns_inactive_when_actor_missing() -> None:
    kg = _make_kg()
    hook = _make_hook()
    result = hook.process(
        actor="nonexistent",
        projection={},
        graph=kg,
        tick_id_str="1",
        observer=FakeObserver(),
        tick_diag_ctx=None,
    )
    assert result.active is False
    assert result.interrupted is False
    assert result.completed is False
    assert result.continuing is False
    assert result.fired_threshold is None
    assert result.observation is None
    assert result.action_text == ""


def test_hook_returns_inactive_when_no_lra() -> None:
    kg = _make_kg()
    kg.add_node("alice", node_type="agent")
    hook = _make_hook()
    result = hook.process(
        actor="alice",
        projection={},
        graph=kg,
        tick_id_str="1",
        observer=FakeObserver(),
        tick_diag_ctx=None,
    )
    assert result.active is False


def test_hook_returns_inactive_when_lra_is_none() -> None:
    kg = _make_kg()
    kg.add_node("alice", node_type="agent")
    kg.set("alice", "current_long_action", None)
    hook = _make_hook()
    result = hook.process(
        actor="alice",
        projection={},
        graph=kg,
        tick_id_str="1",
        observer=FakeObserver(),
        tick_diag_ctx=None,
    )
    assert result.active is False


def test_hook_returns_inactive_when_lra_is_malformed() -> None:
    """Non-dict LRA (e.g., a string) is treated as no LRA — returns active=False."""
    kg = _make_kg()
    kg.add_node("alice", node_type="agent")
    kg.set("alice", "current_long_action", "not_a_dict")
    hook = _make_hook()
    result = hook.process(
        actor="alice",
        projection={},
        graph=kg,
        tick_id_str="1",
        observer=FakeObserver(),
        tick_diag_ctx=None,
    )
    assert result.active is False


def test_hook_does_not_raise_on_bad_lra_shape() -> None:
    """Hook must not raise regardless of LRA data shape."""
    kg = _make_kg()
    kg.add_node("alice", node_type="agent")
    kg.set("alice", "current_long_action", 42)  # int, not dict
    hook = _make_hook()
    # Should not raise
    result = hook.process(
        actor="alice",
        projection={},
        graph=kg,
        tick_id_str="1",
        observer=FakeObserver(),
        tick_diag_ctx=None,
    )
    assert result.active is False


# ---------------------------------------------------------------------------
# Test: continuing case
# ---------------------------------------------------------------------------


def test_hook_continuing_advances_turns_elapsed() -> None:
    kg = _make_kg()
    _actor_with_lra(kg, turns_elapsed=0, turns_total=8)
    hook = _make_hook()
    result = hook.process(
        actor="alice",
        projection=_make_projection(),
        graph=kg,
        tick_id_str="1",
        observer=FakeObserver(),
        tick_diag_ctx=None,
    )
    assert result.active is True
    assert result.continuing is True
    lra = kg.query("alice", "current_long_action")
    assert lra["turns_elapsed"] == 1


def test_hook_continuing_returns_time_passes_template() -> None:
    kg = _make_kg()
    _actor_with_lra(kg, action_text="sleeping", turns_elapsed=0, turns_total=8)
    hook = _make_hook()
    result = hook.process(
        actor="alice",
        projection=_make_projection(),
        graph=kg,
        tick_id_str="1",
        observer=FakeObserver(),
        tick_diag_ctx=None,
    )
    assert result.observation is not None
    assert "Time passes" in result.observation
    assert "sleeping" in result.observation


def test_hook_continuing_observation_uses_action_text_in_template() -> None:
    kg = _make_kg()
    _actor_with_lra(kg, action_text="traveling to the market", turns_elapsed=0, turns_total=5)
    hook = _make_hook()
    result = hook.process(
        actor="alice",
        projection=_make_projection(),
        graph=kg,
        tick_id_str="1",
        observer=FakeObserver(),
        tick_diag_ctx=None,
    )
    assert "traveling to the market" in result.observation


def test_hook_continuing_does_not_clear_lra() -> None:
    kg = _make_kg()
    _actor_with_lra(kg, turns_elapsed=0, turns_total=8)
    hook = _make_hook()
    hook.process(
        actor="alice",
        projection=_make_projection(),
        graph=kg,
        tick_id_str="1",
        observer=FakeObserver(),
        tick_diag_ctx=None,
    )
    lra = kg.query("alice", "current_long_action")
    assert lra is not None
    assert isinstance(lra, dict)


def test_hook_continuing_action_text_echoed_in_result() -> None:
    kg = _make_kg()
    _actor_with_lra(kg, action_text="sleeping", turns_elapsed=0, turns_total=8)
    hook = _make_hook()
    result = hook.process(
        actor="alice",
        projection=_make_projection(),
        graph=kg,
        tick_id_str="1",
        observer=FakeObserver(),
        tick_diag_ctx=None,
    )
    assert result.action_text == "sleeping"


# ---------------------------------------------------------------------------
# Test: attention state echoed
# ---------------------------------------------------------------------------


def test_hook_attention_state_echoed_in_result() -> None:
    attn = {"suppress": ["visual_detail"], "boost": ["noise_level"]}
    kg = _make_kg()
    _actor_with_lra(kg, turns_elapsed=0, turns_total=8, attention_state=attn)
    hook = _make_hook()
    result = hook.process(
        actor="alice",
        projection=_make_projection(),
        graph=kg,
        tick_id_str="1",
        observer=FakeObserver(),
        tick_diag_ctx=None,
    )
    assert result.attention_state == attn


def test_hook_no_attention_state_yields_none_in_result() -> None:
    kg = _make_kg()
    _actor_with_lra(kg, turns_elapsed=0, turns_total=8, attention_state=None)
    hook = _make_hook()
    result = hook.process(
        actor="alice",
        projection=_make_projection(),
        graph=kg,
        tick_id_str="1",
        observer=FakeObserver(),
        tick_diag_ctx=None,
    )
    assert result.attention_state is None


# ---------------------------------------------------------------------------
# Test: interruption case
# ---------------------------------------------------------------------------


def test_hook_interrupted_clears_lra_and_calls_observer() -> None:
    kg = _make_kg()
    _actor_with_lra(
        kg,
        turns_elapsed=0,
        turns_total=8,
        thresholds=[{"property": "bedroom.noise_level", "op": ">", "value": 0.7}],
    )
    projection = _make_projection(noise_level=0.9)  # threshold fires
    observer = FakeObserver(text="You are jolted awake by a loud noise!")
    hook = _make_hook()
    result = hook.process(
        actor="alice",
        projection=projection,
        graph=kg,
        tick_id_str="1",
        observer=observer,
        tick_diag_ctx=None,
    )
    assert result.active is True
    assert result.interrupted is True
    assert result.completed is False
    assert result.continuing is False
    # LRA must be cleared
    lra = kg.query("alice", "current_long_action")
    assert lra is None
    # Observer was called
    assert len(observer.calls) == 1
    assert result.observation == "You are jolted awake by a loud noise!"


def test_hook_interrupted_passes_interruption_context_to_observer() -> None:
    kg = _make_kg()
    _actor_with_lra(
        kg,
        action_text="sleeping",
        turns_elapsed=0,
        turns_total=8,
        thresholds=[{"property": "bedroom.noise_level", "op": ">", "value": 0.7}],
    )
    projection = _make_projection(noise_level=0.9)
    observer = FakeObserver()
    hook = _make_hook()
    hook.process(
        actor="alice",
        projection=projection,
        graph=kg,
        tick_id_str="1",
        observer=observer,
        tick_diag_ctx=None,
    )
    assert len(observer.calls) == 1
    call_kwargs = observer.calls[0]
    assert "interruption_context" in call_kwargs
    ctx = call_kwargs["interruption_context"]
    assert "interrupted_by" in ctx
    assert ctx["long_action"] == "sleeping"
    assert ctx["interrupted_by"]["property"] == "bedroom.noise_level"


def test_hook_interrupted_returns_fired_threshold_in_result() -> None:
    kg = _make_kg()
    _actor_with_lra(
        kg,
        turns_elapsed=0,
        turns_total=8,
        thresholds=[{"property": "bedroom.noise_level", "op": ">", "value": 0.7}],
    )
    projection = _make_projection(noise_level=0.9)
    hook = _make_hook()
    result = hook.process(
        actor="alice",
        projection=projection,
        graph=kg,
        tick_id_str="1",
        observer=FakeObserver(),
        tick_diag_ctx=None,
    )
    assert result.fired_threshold is not None
    assert isinstance(result.fired_threshold, ThresholdSpec)
    assert result.fired_threshold.property == "bedroom.noise_level"
    assert result.fired_threshold.op == ">"
    assert result.fired_threshold.value == 0.7


# ---------------------------------------------------------------------------
# Test: completion case
# ---------------------------------------------------------------------------


def test_hook_completed_when_turns_elapsed_reaches_turns_total() -> None:
    """Two-tick LRA: second hook call should trigger completion."""
    kg = _make_kg()
    _actor_with_lra(kg, turns_elapsed=0, turns_total=2)
    projection = _make_projection()
    observer = FakeObserver(text="You have finished sleeping.")
    hook = _make_hook()

    # First call: turns_elapsed 0 → 1; turns_total=2 → not complete yet
    result1 = hook.process(
        actor="alice",
        projection=projection,
        graph=kg,
        tick_id_str="1",
        observer=observer,
        tick_diag_ctx=None,
    )
    assert result1.continuing is True
    assert result1.completed is False
    lra = kg.query("alice", "current_long_action")
    assert lra["turns_elapsed"] == 1

    # Second call: turns_elapsed 1 → 2; 2 >= 2 → complete
    result2 = hook.process(
        actor="alice",
        projection=projection,
        graph=kg,
        tick_id_str="2",
        observer=observer,
        tick_diag_ctx=None,
    )
    assert result2.completed is True
    assert result2.interrupted is False
    assert result2.continuing is False
    # LRA cleared
    lra_after = kg.query("alice", "current_long_action")
    assert lra_after is None
    # Observer called for completion
    assert len(observer.calls) == 1


def test_hook_completed_passes_completion_context_to_observer() -> None:
    kg = _make_kg()
    _actor_with_lra(kg, action_text="sleeping", turns_elapsed=1, turns_total=2)
    observer = FakeObserver()
    hook = _make_hook()
    hook.process(
        actor="alice",
        projection=_make_projection(),
        graph=kg,
        tick_id_str="1",
        observer=observer,
        tick_diag_ctx=None,
    )
    assert len(observer.calls) == 1
    ctx = observer.calls[0]["interruption_context"]
    assert ctx["completed"] is True
    assert ctx["long_action"] == "sleeping"


# ---------------------------------------------------------------------------
# Test: indefinite LRA (turns_total=None)
# ---------------------------------------------------------------------------


def test_hook_indefinite_action_never_completes() -> None:
    """turns_total=None should never trigger completion, even after many ticks."""
    kg = _make_kg()
    _actor_with_lra(kg, turns_elapsed=0, turns_total=None)
    projection = _make_projection()
    hook = _make_hook()
    observer = FakeObserver()

    for tick in range(20):
        result = hook.process(
            actor="alice",
            projection=projection,
            graph=kg,
            tick_id_str=str(tick),
            observer=observer,
            tick_diag_ctx=None,
        )
        assert result.continuing is True, f"Should still be continuing at tick {tick}"
        assert result.completed is False

    lra = kg.query("alice", "current_long_action")
    assert lra is not None
    assert lra["turns_elapsed"] == 20
    # Observer never called (no interruption, no completion)
    assert len(observer.calls) == 0


# ---------------------------------------------------------------------------
# Test: threshold fires takes precedence over completion
# ---------------------------------------------------------------------------


def test_hook_threshold_fired_takes_precedence_over_completion() -> None:
    """A tick where BOTH threshold fires AND turns_elapsed reaches turns_total:
    threshold wins (interrupted=True, fired_threshold set, completed=False).
    """
    kg = _make_kg()
    _actor_with_lra(
        kg,
        turns_elapsed=1,  # will become 2 on this tick
        turns_total=2,  # would also complete at 2
        thresholds=[{"property": "bedroom.noise_level", "op": ">", "value": 0.7}],
    )
    projection = _make_projection(noise_level=0.9)  # threshold fires too
    observer = FakeObserver(text="Interrupted!")
    hook = _make_hook()
    result = hook.process(
        actor="alice",
        projection=projection,
        graph=kg,
        tick_id_str="1",
        observer=observer,
        tick_diag_ctx=None,
    )
    assert result.interrupted is True
    assert result.completed is False
    assert result.fired_threshold is not None
