"""Tests for TickResult.projected_state field — Phase 6 Plan 00.

These tests exercise the three run_tick result kinds (ok/yielded/refused) and
verify the new `projected_state` field is populated on the execute path and None
on the yield/refuse paths. Also includes a pure unit test for the classmethod.

Pattern follows test_engine_run_tick.py:
- `kg` fixture overrides conftest to use SQLite persistence (snapshot/restore).
- `tmp_universe` from conftest provides minimum scaffolding.
- MockAnthropicClient from conftest provides canned LLM responses.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_engine.conftest import MockAnthropicClient
from token_world.engine import SimulationEngine, TickResult
from token_world.graph import KnowledgeGraph

# ---------------------------------------------------------------------------
# Local override: kg with SQLite persistence (required for snapshot/restore)
# ---------------------------------------------------------------------------


@pytest.fixture
def kg(tmp_path: Path) -> KnowledgeGraph:
    """KnowledgeGraph backed by a temp SQLite db — required for snapshot/restore."""
    return KnowledgeGraph(db_path=tmp_path / "projected_state_test.db")


# ---------------------------------------------------------------------------
# Minimal mechanic source for execute-path tests
# ---------------------------------------------------------------------------

_PICKUP_MECHANIC_SOURCE = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import VerbMatcher

class Pickup(Mechanic):
    id = "pickup"
    description = "Pick up a target entity"
    voluntary = True
    tags = []
    def watches(self):
        return [VerbMatcher(verb="pickup")]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        return [ctx.set(ctx.target, "held_by", ctx.actor)]
"""

# Classifier responses
_OK_PICKUP = json.dumps(
    {
        "kind": "ok",
        "classified": {"verb": "pickup", "actor": "alice", "target": "rock_1", "params": {}},
        "confidence": 0.95,
    }
)
_OK_PICKUP_NO_MECHANIC = _OK_PICKUP  # same, but no mechanics registered
_NO_VIABLE_ACTION = json.dumps({"kind": "no_viable_action", "reason": "gibberish"})
_OBSERVATION = "You bend down and pick up the rock. It feels cold and rough."


# ---------------------------------------------------------------------------
# Test 1: ok path carries a non-empty projected_state dict
# ---------------------------------------------------------------------------


def test_tick_result_ok_carries_projected_state(tmp_universe, kg):
    """EXECUTE path: TickResult.projected_state is a non-empty dict including actor ID."""
    (tmp_universe / "mechanics" / "pickup.py").write_text(_PICKUP_MECHANIC_SOURCE, encoding="utf-8")
    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity")
    kg.add_node("rock_1", node_type="entity")
    kg.add_edge("alice", "room_1", type="location")
    kg.add_edge("room_1", "rock_1", type="contains")

    client = MockAnthropicClient([_OK_PICKUP, _OBSERVATION])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    result = engine.run_tick("pick up the rock", "alice")

    assert result.kind == "ok"
    assert result.projected_state is not None, "projected_state must not be None on ok path"
    assert isinstance(result.projected_state, dict), "projected_state must be a dict"
    assert len(result.projected_state) > 0, "projected_state must not be empty"
    # The projection dict is keyed by node IDs visible to the actor;
    # at minimum the actor itself should appear
    assert "alice" in result.projected_state, (
        f"Expected 'alice' in projected_state keys, got: {list(result.projected_state.keys())}"
    )


# ---------------------------------------------------------------------------
# Test 2: yielded path has projected_state = None
# ---------------------------------------------------------------------------


def test_tick_result_yielded_has_no_projected_state(tmp_universe, kg):
    """YIELD path: TickResult.projected_state is None (no observer call happened)."""
    # No mechanics registered → pickup action yields
    kg.add_node("alice", node_type="agent")
    kg.add_node("rock_1", node_type="entity")

    # Only Haiku call needed (no match → no observer)
    client = MockAnthropicClient([_OK_PICKUP_NO_MECHANIC])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    result = engine.run_tick("pick up the rock", "alice")

    assert result.kind == "yielded"
    assert result.projected_state is None, (
        f"projected_state must be None on yield path, got: {result.projected_state!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: refused path has projected_state = None
# ---------------------------------------------------------------------------


def test_tick_result_refused_has_no_projected_state(tmp_universe, kg):
    """REFUSE path: TickResult.projected_state is None (classifier refused, no projection)."""
    kg.add_node("alice", node_type="agent")

    client = MockAnthropicClient([_NO_VIABLE_ACTION])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    result = engine.run_tick("asdfjkl;", "alice")

    assert result.kind == "refused"
    assert result.projected_state is None, (
        f"projected_state must be None on refuse path, got: {result.projected_state!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: pure unit test — TickResult.ok() classmethod accepts projected_state kw
# ---------------------------------------------------------------------------


def test_tick_result_ok_classmethod_accepts_projected_state_kw():
    """TickResult.ok() must accept projected_state as an optional keyword argument."""
    projection = {"a": {"x": 1}, "b": {"y": 2}}
    result = TickResult.ok(
        tick_id="tick_1",
        observation="foo",
        trace=None,
        projected_state=projection,
    )
    assert result.projected_state == projection, (
        f"Expected projected_state={projection!r}, got: {result.projected_state!r}"
    )
    assert result.kind == "ok"
    assert result.tick_id == "tick_1"
    assert result.observation == "foo"
    assert result.trace is None
