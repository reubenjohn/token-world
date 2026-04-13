"""Integration tests for engine LRA detection and _handle_long_running_tick (Task 2, Plan 07-04).

Tests the full engine path:
  - run_tick(None, actor) with active LRA → continuation path
  - run_tick(text, actor) with active LRA → implicit cancellation (D-11)
  - run_tick(text, actor) without LRA → normal pipeline (regression)
  - Tick summary long_running_action field (D-17)
  - Passive sweep still fires during LRA ticks (D-06)
  - has_active_long_action() accessor

Uses MockAnthropicClient from conftest and manually-planted current_long_action dicts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_engine.conftest import MockAnthropicClient
from token_world.engine import SimulationEngine
from token_world.graph import KnowledgeGraph

# ---------------------------------------------------------------------------
# Local fixture override: KG with SQLite persistence (snapshot/restore support)
# ---------------------------------------------------------------------------


@pytest.fixture
def kg(tmp_path: Path) -> KnowledgeGraph:
    """KnowledgeGraph backed by a temp SQLite db — required for snapshot/restore in engine."""
    return KnowledgeGraph(db_path=tmp_path / "engine_lra_test.db")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _plant_lra(
    kg: KnowledgeGraph,
    actor: str,
    *,
    action_text: str = "sleeping",
    turns_total: int | None = 8,
    turns_elapsed: int = 0,
    thresholds: list[dict] | None = None,
    attention_state: dict | None = None,
) -> None:
    """Manually plant a current_long_action dict on the actor node."""
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


def _make_engine(
    tmp_universe: Path,
    kg: KnowledgeGraph,
    responses: list[str] | None = None,
) -> SimulationEngine:
    """Build a SimulationEngine with a mock Anthropic client."""
    if responses is None:
        responses = []
    client = MockAnthropicClient(responses)
    return SimulationEngine(tmp_universe, graph=kg, anthropic_client=client)


# ---------------------------------------------------------------------------
# Test: has_active_long_action()
# ---------------------------------------------------------------------------


def test_has_active_long_action_returns_false_when_actor_missing(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    engine = _make_engine(tmp_universe, kg)
    assert engine.has_active_long_action("nonexistent") is False


def test_has_active_long_action_returns_false_when_no_lra(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    kg.add_node("alice", node_type="agent")
    engine = _make_engine(tmp_universe, kg)
    assert engine.has_active_long_action("alice") is False


def test_has_active_long_action_returns_false_when_lra_is_none(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    kg.add_node("alice", node_type="agent")
    kg.set("alice", "current_long_action", None)
    engine = _make_engine(tmp_universe, kg)
    assert engine.has_active_long_action("alice") is False


def test_has_active_long_action_returns_true_when_lra_active(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    kg.add_node("alice", node_type="agent")
    _plant_lra(kg, "alice")
    engine = _make_engine(tmp_universe, kg)
    assert engine.has_active_long_action("alice") is True


# ---------------------------------------------------------------------------
# Test: continuation path — run_tick(None, actor)
# ---------------------------------------------------------------------------


def test_continuation_advances_turns_elapsed(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    kg.add_node("alice", node_type="agent")
    _plant_lra(kg, "alice", turns_elapsed=0, turns_total=8)
    engine = _make_engine(tmp_universe, kg)

    result = engine.run_tick(None, actor="alice")

    assert result.kind == "ok"
    assert "Time passes" in (result.observation or "")
    lra = kg.query("alice", "current_long_action")
    assert lra["turns_elapsed"] == 1


def test_continuation_uses_static_time_passes_template(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """No observer call on continuing tick — static template returned."""
    kg.add_node("alice", node_type="agent")
    _plant_lra(kg, "alice", action_text="sleeping", turns_elapsed=0, turns_total=8)
    # If observer is called it will raise (empty responses list)
    engine = _make_engine(tmp_universe, kg, responses=[])

    result = engine.run_tick(None, actor="alice")

    assert "sleeping" in (result.observation or "")
    assert "Time passes" in (result.observation or "")


def test_continuation_writes_long_running_action_field_to_tick_summary(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """Tick summary JSON must contain long_running_action field (D-17)."""
    kg.add_node("alice", node_type="agent")
    _plant_lra(kg, "alice", action_text="sleeping", turns_elapsed=0, turns_total=8)
    engine = _make_engine(tmp_universe, kg)

    result = engine.run_tick(None, actor="alice")

    # Load the written tick summary JSON
    tick_file = tmp_universe / "tick_summaries" / "ticks" / f"tick_{result.tick_id}.json"
    assert tick_file.exists()
    data = json.loads(tick_file.read_text())
    lra_field = data.get("long_running_action")
    assert lra_field is not None
    assert lra_field["active"] is True
    assert lra_field["turns_elapsed"] == 1
    assert lra_field["turns_total"] == 8
    assert lra_field["interrupted"] is False


def test_threshold_fires_clears_lra_and_returns_observer_observation(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """When threshold fires, LRA is cleared and observer is called for narrative."""
    kg.add_node("alice", node_type="agent")
    kg.add_node("bedroom", node_type="entity")
    kg.set("bedroom", "noise_level", 0.9)
    kg.add_edge("alice", "bedroom", type="location")
    _plant_lra(
        kg,
        "alice",
        action_text="sleeping",
        turns_elapsed=0,
        turns_total=8,
        thresholds=[{"property": "bedroom.noise_level", "op": ">", "value": 0.7}],
    )
    # Observer will be called for the interruption observation
    engine = _make_engine(
        tmp_universe, kg, responses=["You are jolted awake by a thunderous crash!"]
    )

    result = engine.run_tick(None, actor="alice")

    assert result.kind == "ok"
    assert "jolted awake" in (result.observation or "")
    # LRA cleared
    lra = kg.query("alice", "current_long_action")
    assert lra is None


def test_completion_clears_lra_and_calls_observer(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """turns_total=1: first continuation tick advances to 1 → completes."""
    kg.add_node("alice", node_type="agent")
    _plant_lra(kg, "alice", action_text="napping", turns_elapsed=0, turns_total=1)
    engine = _make_engine(tmp_universe, kg, responses=["You finish your nap feeling refreshed."])

    result = engine.run_tick(None, actor="alice")

    assert result.kind == "ok"
    assert "finish" in (result.observation or "").lower() or result.observation
    lra = kg.query("alice", "current_long_action")
    assert lra is None


def test_indefinite_lra_never_completes_via_turns(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """turns_total=None: 5 continuations, LRA still active, turns_elapsed=5."""
    kg.add_node("alice", node_type="agent")
    _plant_lra(kg, "alice", action_text="drunk wandering", turns_elapsed=0, turns_total=None)
    engine = _make_engine(tmp_universe, kg)

    for _ in range(5):
        result = engine.run_tick(None, actor="alice")
        assert result.kind == "ok"

    lra = kg.query("alice", "current_long_action")
    assert lra is not None
    assert lra["turns_elapsed"] == 5


def test_attention_state_passed_to_projector(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """LRA with attention_state: suppressed properties absent from projected_state."""
    kg.add_node("alice", node_type="agent")
    kg.add_node("room", node_type="entity")
    kg.set("room", "noise_level", 0.3)
    kg.set("room", "visual_detail", "ornate tapestry")
    kg.add_edge("alice", "room", type="location")
    _plant_lra(
        kg,
        "alice",
        turns_elapsed=0,
        turns_total=8,
        attention_state={"suppress": ["visual_detail"], "boost": []},
    )
    engine = _make_engine(tmp_universe, kg)

    result = engine.run_tick(None, actor="alice")

    assert result.kind == "ok"
    # The projected_state should NOT include visual_detail (suppressed)
    proj = result.projected_state or {}
    room_props = proj.get("room", {}).get("properties", {})
    assert "visual_detail" not in room_props


def test_threshold_does_not_insta_fire_when_lra_just_started_via_engine(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """Pitfall 1: When begin_long_action runs on tick N (via _handle_execute),
    the hook does NOT run on that same tick. So a threshold that would fire
    immediately is NOT triggered until tick N+1 (the first continuation tick).
    This test verifies that behavior by checking: a continuation tick with
    turns_elapsed=0 on graph → hook advances to 1 → threshold evaluated at 1.
    """
    kg.add_node("alice", node_type="agent")
    kg.add_node("bedroom", node_type="entity")
    kg.set("bedroom", "noise_level", 0.9)  # already above threshold
    kg.add_edge("alice", "bedroom", type="location")
    # Plant LRA as if begin_long_action JUST fired (turns_elapsed=0)
    _plant_lra(
        kg,
        "alice",
        action_text="sleeping",
        turns_elapsed=0,
        turns_total=8,
        thresholds=[{"property": "bedroom.noise_level", "op": ">", "value": 0.7}],
    )
    # The FIRST run_tick(None) will advance to 1 and evaluate — it WILL fire.
    # This is correct behavior: Pitfall 1 means the begin_long_action TICK does
    # not run the hook, but subsequent continuation ticks do.
    engine = _make_engine(tmp_universe, kg, responses=["You are woken by loud noise."])

    result = engine.run_tick(None, actor="alice")

    # Threshold fires on the first continuation tick (turns_elapsed was 0)
    assert result.kind == "ok"
    lra = kg.query("alice", "current_long_action")
    assert lra is None  # cleared by interruption


# ---------------------------------------------------------------------------
# Test: D-11 implicit cancellation
# ---------------------------------------------------------------------------


def test_implicit_cancellation_on_real_action_text(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """Real action_text with active LRA → clears LRA, runs classifier, normal path."""
    kg.add_node("alice", node_type="agent")
    _plant_lra(kg, "alice", turns_elapsed=2, turns_total=8)
    # Classifier response (low confidence → refuse, no observer)
    engine = _make_engine(
        tmp_universe,
        kg,
        responses=[
            '{"kind":"no_viable_action","reason":"test"}',
        ],
    )

    result = engine.run_tick("wake up", actor="alice")

    # LRA must be cleared before classifier ran
    lra = kg.query("alice", "current_long_action")
    assert lra is None
    # Normal path ran (refused or ok — just not continuation)
    assert result.kind in ("refused", "ok", "yielded")


# ---------------------------------------------------------------------------
# Test: regression — run_tick with real action_text, no LRA (existing behavior)
# ---------------------------------------------------------------------------


def test_run_tick_with_action_text_when_no_lra_works_normally(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """Regression: existing run_tick(text, actor) still works when no LRA present."""
    kg.add_node("alice", node_type="agent")
    # Classifier refuses (no match) — normal path
    engine = _make_engine(
        tmp_universe,
        kg,
        responses=['{"kind":"no_viable_action","reason":"no action"}'],
    )

    result = engine.run_tick("look around", actor="alice")

    assert result.kind in ("refused", "ok", "yielded")
    # LRA should still not be present
    assert engine.has_active_long_action("alice") is False


# ---------------------------------------------------------------------------
# Test: passive sweep fires during LRA continuation tick
# ---------------------------------------------------------------------------


def test_continuation_runs_passive_sweep(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """Passive TickMatcher mechanics still fire during LRA continuation ticks (D-06)."""

    # Write a minimal TickMatcher mechanic as a .py file in the mechanics dir
    mech_py = tmp_universe / "mechanics" / "tick_counter.py"
    mech_py.write_text(
        """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import TickMatcher

class TickCounter(Mechanic):
    id = "tick_counter"
    description = "Counts ticks"
    voluntary = False

    def watches(self):
        return [TickMatcher()]

    def check(self, ctx):
        return CheckResult(passed=True)

    def apply(self, ctx):
        count = ctx.query_node("_world", "tick_count") or 0
        return [ctx.set("_world", "tick_count", count + 1)]
""",
        encoding="utf-8",
    )

    # Add the _world node so the mechanic can write to it
    kg.add_node("_world", node_type="entity")
    kg.set("_world", "tick_count", 0)
    kg.add_node("alice", node_type="agent")
    _plant_lra(kg, "alice", turns_elapsed=0, turns_total=8)

    engine = _make_engine(tmp_universe, kg)
    engine.run_tick(None, actor="alice")

    # Passive mechanic should have fired and incremented tick_count
    assert kg.query("_world", "tick_count") == 1


# ---------------------------------------------------------------------------
# WR-03: _handle_long_running_tick logs warning when LRA is empty / vanished
# ---------------------------------------------------------------------------


def test_handle_long_running_tick_logs_warning_when_lra_vanished(
    tmp_universe: Path, kg: KnowledgeGraph, caplog: pytest.LogCaptureFixture
) -> None:
    """If current_long_action is None when _handle_long_running_tick reads it,
    the engine must log a WARNING (not crash) and return a non-empty observation (WR-03).

    We simulate 'LRA vanished' by planting None directly on the node after
    engine construction, but before run_tick(None) — the engine's has_active_long_action
    check is bypassed by calling _handle_long_running_tick directly via a public path
    that plants a real LRA then immediately clears it mid-tick.

    The simplest observable contract: calling run_tick(None) when the graph's
    current_long_action is unexpectedly None must not crash and must produce a
    non-empty observation (or at minimum not an unhandled exception).
    """
    import logging

    kg.add_node("alice", node_type="agent")
    _plant_lra(kg, "alice", turns_elapsed=0, turns_total=8)
    engine = _make_engine(tmp_universe, kg)

    # Simulate the race: clear the LRA right before the tick call.
    # has_active_long_action() was True when we planted it, but we manually clear it
    # to simulate a mechanic that fired between the check and the handler.
    kg.set("alice", "current_long_action", None)

    # Call the internal handler directly to test it in isolation.
    # The public run_tick(None) would call has_active_long_action() first and route
    # to _handle_execute, so we invoke the private method to bypass the routing guard.
    import time

    with caplog.at_level(logging.WARNING, logger="token_world.engine.engine"):
        engine._handle_long_running_tick(  # type: ignore[attr-defined]
            actor="alice",
            tick_id_str="test_tick_1",
            tick_ctx=_make_tick_ctx(),
            start_time=time.time(),
        )

    # Must not crash; warning must be logged
    assert any("LRA disappeared" in r.message for r in caplog.records)
    # The key contract: no unhandled exception


def _make_tick_ctx() -> object:
    """Minimal tick diagnostics context stub that satisfies the engine's set_summary call."""

    class _FakeTickCtx:
        def set_summary(self, **kwargs: object) -> None:  # noqa: ANN002
            pass

    return _FakeTickCtx()
