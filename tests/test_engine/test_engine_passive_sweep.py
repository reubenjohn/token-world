"""Tests for SimulationEngine passive sweep (D-17, GAP-ENG07).

The passive sweep runs AFTER the primary voluntary action's chain completes
(execute path only — not on yield or refuse paths).

Mechanic source constants are written to the tmp_universe/mechanics/ directory
at test setup. All mechanics are minimal valid Python files.

Note: The `kg` fixture here uses a db-backed KnowledgeGraph (required for
snapshot/restore which run_tick uses on the execute path).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_engine.conftest import MockAnthropicClient
from token_world.engine import SimulationEngine
from token_world.graph import KnowledgeGraph

# ---------------------------------------------------------------------------
# Local override: kg with SQLite persistence (snapshot/restore support)
# ---------------------------------------------------------------------------


@pytest.fixture
def kg(tmp_path: Path) -> KnowledgeGraph:
    """KnowledgeGraph backed by a temp SQLite db — required for snapshot/restore."""
    return KnowledgeGraph(db_path=tmp_path / "sweep_test.db")


# ---------------------------------------------------------------------------
# Mechanic sources
# ---------------------------------------------------------------------------

_PICKUP_MECHANIC = """
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

_TICK_COUNTER_MECHANIC = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import TickMatcher

class TickCounter(Mechanic):
    id = "tick_counter"
    description = "Increments tick_counter on _world every tick"
    voluntary = False
    tags = []
    def watches(self):
        return [TickMatcher()]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        world_id = "_world"
        if not ctx.has_node(world_id):
            ctx.add_node(world_id, node_type="entity")
        props = ctx.query_node(world_id)  # returns dict of all properties
        current = props.get("tick_counter", 0)
        return [ctx.set(world_id, "tick_counter", current + 1)]
"""

_DECAY_MECHANIC = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import DecayMatcher

class DecayTick(Mechanic):
    id = "decay_tick"
    description = "Decay nodes with decay_period property"
    voluntary = False
    tags = []
    def watches(self):
        return [DecayMatcher()]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        mutations = []
        for node_id in ctx.find_nodes(decay_period=1):
            props = ctx.query_node(node_id)
            current = props.get("durability", 10)
            mutations.append(ctx.set(node_id, "durability", current - 1))
        return mutations
"""

_SEASON_REACTION_MECHANIC = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import WorldPropertyMatcher

class SeasonReaction(Mechanic):
    id = "season_reaction"
    description = "React when world season property changes"
    voluntary = False
    tags = []
    def watches(self):
        return [WorldPropertyMatcher("season")]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        # Set a flag on _world to confirm the reaction fired
        if not ctx.has_node("_world"):
            ctx.add_node("_world", node_type="entity")
        return [ctx.set("_world", "season_reacted", True)]
"""

_WORLD_SETTER_MECHANIC = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import VerbMatcher

class WorldSetter(Mechanic):
    id = "world_setter"
    description = "Sets world.season via voluntary action"
    voluntary = True
    tags = []
    def watches(self):
        return [VerbMatcher(verb="set_season")]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        if not ctx.has_node("_world"):
            ctx.add_node("_world", node_type="entity")
        return [ctx.set("_world", "season", "winter")]
"""

_ACTOR_RECORDER_MECHANIC = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import TickMatcher

class ActorRecorder(Mechanic):
    id = "actor_recorder"
    description = "Records the actor value on _world"
    voluntary = False
    tags = []
    def watches(self):
        return [TickMatcher()]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        if not ctx.has_node("_world"):
            ctx.add_node("_world", node_type="entity")
        return [ctx.set("_world", "last_sweep_actor", ctx.actor)]
"""

_MUTATION_COUNTER_MECHANIC = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import TickMatcher

class MutationCounter(Mechanic):
    id = "mutation_counter"
    description = "Increments a counter property on _world; sweep mutation included in summary"
    voluntary = False
    tags = []
    def watches(self):
        return [TickMatcher()]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        if not ctx.has_node("_world"):
            ctx.add_node("_world", node_type="entity")
        props = ctx.query_node("_world")
        current = props.get("sweep_count", 0)
        return [ctx.set("_world", "sweep_count", current + 1)]
"""

# Classifier/observer canned responses

_OK_PICKUP = json.dumps(
    {
        "kind": "ok",
        "actions": [{"verb": "pickup", "actor": "alice", "target": "rock_1", "params": {}}],
        "confidence": 0.95,
    }
)
_OK_SET_SEASON = json.dumps(
    {
        "kind": "ok",
        "actions": [{"verb": "set_season", "actor": "alice", "target": "alice", "params": {}}],
        "confidence": 0.95,
    }
)
_OK_PICKUP_NO_MECHANIC = json.dumps(
    {
        "kind": "ok",
        "actions": [{"verb": "pickup", "actor": "alice", "target": "rock_1", "params": {}}],
        "confidence": 0.95,
    }
)
_NO_VIABLE_ACTION = json.dumps({"kind": "no_viable_action", "reason": "gibberish"})
_OBSERVATION = "You pick it up."


# ---------------------------------------------------------------------------
# Test 1: TickMatcher fires every tick
# ---------------------------------------------------------------------------


def test_tick_matcher_mechanic_fires_every_tick(tmp_universe, kg):
    """TickMatcher involuntary mechanic executes once per tick."""
    (tmp_universe / "mechanics" / "pickup.py").write_text(_PICKUP_MECHANIC, encoding="utf-8")
    (tmp_universe / "mechanics" / "tick_counter.py").write_text(
        _TICK_COUNTER_MECHANIC, encoding="utf-8"
    )
    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity")
    kg.add_node("rock_1", node_type="entity")
    kg.add_edge("alice", "room_1", type="location")
    kg.add_edge("room_1", "rock_1", type="contains")

    client = MockAnthropicClient([_OK_PICKUP, _OBSERVATION, _OK_PICKUP, _OBSERVATION])
    engine = SimulationEngine(universe_path=tmp_universe, graph=kg, anthropic_client=client)
    engine.run_tick("pick up rock", "alice")
    engine.run_tick("pick up rock", "alice")

    assert kg.has_node("_world")
    assert kg.query("_world", "tick_counter") == 2


# ---------------------------------------------------------------------------
# Test 2: DecayMatcher fires when node has decay_period
# ---------------------------------------------------------------------------


def test_decay_matcher_mechanic_fires_when_node_has_decay_period(tmp_universe, kg):
    """DecayMatcher involuntary mechanic reduces durability of decay_period nodes."""
    (tmp_universe / "mechanics" / "pickup.py").write_text(_PICKUP_MECHANIC, encoding="utf-8")
    (tmp_universe / "mechanics" / "decay_tick.py").write_text(_DECAY_MECHANIC, encoding="utf-8")

    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity")
    kg.add_node("rock_1", node_type="entity", decay_period=1, durability=10)
    kg.add_edge("alice", "room_1", type="location")
    kg.add_edge("room_1", "rock_1", type="contains")

    client = MockAnthropicClient([_OK_PICKUP, _OBSERVATION])
    engine = SimulationEngine(universe_path=tmp_universe, graph=kg, anthropic_client=client)
    engine.run_tick("pick up rock", "alice")

    # Decay mechanic should have decremented durability from 10 to 9
    assert kg.query("rock_1", "durability") == 9


# ---------------------------------------------------------------------------
# Test 3: WorldPropertyMatcher fires only when world property mutated
# ---------------------------------------------------------------------------


def test_world_property_matcher_fires_only_when_world_property_mutated(tmp_universe, kg):
    """SeasonReaction fires only when world.season is mutated in the same tick."""
    (tmp_universe / "mechanics" / "world_setter.py").write_text(
        _WORLD_SETTER_MECHANIC, encoding="utf-8"
    )
    (tmp_universe / "mechanics" / "season_reaction.py").write_text(
        _SEASON_REACTION_MECHANIC, encoding="utf-8"
    )
    (tmp_universe / "mechanics" / "pickup.py").write_text(_PICKUP_MECHANIC, encoding="utf-8")

    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity")
    kg.add_node("rock_1", node_type="entity")
    kg.add_edge("alice", "room_1", type="location")
    kg.add_edge("room_1", "rock_1", type="contains")

    # Tick 1: pickup does NOT mutate world.season → season_reaction should NOT fire
    client1 = MockAnthropicClient([_OK_PICKUP, _OBSERVATION])
    engine = SimulationEngine(universe_path=tmp_universe, graph=kg, anthropic_client=client1)
    engine.run_tick("pick up rock", "alice")
    # _world may not even exist yet; season_reacted must not be set
    if kg.has_node("_world"):
        assert "season_reacted" not in kg.query("_world")

    # Tick 2: set_season DOES mutate world.season → season_reaction SHOULD fire
    client2 = MockAnthropicClient([_OK_SET_SEASON, _OBSERVATION])
    engine._classifier = engine._classifier.__class__(client=client2)
    engine._observer = engine._observer.__class__(client=client2)
    engine.run_tick("set season", "alice")
    assert kg.has_node("_world")
    assert kg.query("_world").get("season_reacted") is True


# ---------------------------------------------------------------------------
# Test 4: Passive sweep does NOT run on yield path
# ---------------------------------------------------------------------------


def test_passive_sweep_does_not_run_on_yield_path(tmp_universe, kg):
    """Yield path: no mechanics registered, sweep involuntary should not fire."""
    # Register only the tick_counter involuntary (no voluntary = yield always)
    (tmp_universe / "mechanics" / "tick_counter.py").write_text(
        _TICK_COUNTER_MECHANIC, encoding="utf-8"
    )
    kg.add_node("alice", node_type="agent")
    kg.add_node("rock_1", node_type="entity")

    # No voluntary mechanics → classifier ok but no match → yield
    client = MockAnthropicClient([_OK_PICKUP_NO_MECHANIC])
    engine = SimulationEngine(universe_path=tmp_universe, graph=kg, anthropic_client=client)
    result = engine.run_tick("pick up rock", "alice")
    assert result.kind == "yielded"

    # Tick counter should NOT have incremented (sweep skipped on yield)
    assert not kg.has_node("_world") or kg.query("_world", "tick_counter") is None


# ---------------------------------------------------------------------------
# Test 5: Passive sweep does NOT run on refuse path
# ---------------------------------------------------------------------------


def test_passive_sweep_does_not_run_on_refuse_path(tmp_universe, kg):
    """Refuse path: classifier refuses, sweep involuntary should not fire."""
    (tmp_universe / "mechanics" / "tick_counter.py").write_text(
        _TICK_COUNTER_MECHANIC, encoding="utf-8"
    )
    kg.add_node("alice", node_type="agent")

    client = MockAnthropicClient([_NO_VIABLE_ACTION])
    engine = SimulationEngine(universe_path=tmp_universe, graph=kg, anthropic_client=client)
    result = engine.run_tick("asdfjkl;", "alice")
    assert result.kind == "refused"

    # Tick counter should NOT have incremented (sweep skipped on refuse)
    assert not kg.has_node("_world") or kg.query("_world", "tick_counter") is None


# ---------------------------------------------------------------------------
# Test 6: Passive sweep uses sentinel actor node
# ---------------------------------------------------------------------------


def test_passive_sweep_uses_sentinel_actor_node(tmp_universe, kg):
    """Sweep mechanics receive '_engine_tick_sentinel' as ctx.actor."""
    (tmp_universe / "mechanics" / "pickup.py").write_text(_PICKUP_MECHANIC, encoding="utf-8")
    (tmp_universe / "mechanics" / "actor_recorder.py").write_text(
        _ACTOR_RECORDER_MECHANIC, encoding="utf-8"
    )
    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity")
    kg.add_node("rock_1", node_type="entity")
    kg.add_edge("alice", "room_1", type="location")
    kg.add_edge("room_1", "rock_1", type="contains")

    client = MockAnthropicClient([_OK_PICKUP, _OBSERVATION])
    engine = SimulationEngine(universe_path=tmp_universe, graph=kg, anthropic_client=client)
    engine.run_tick("pick up rock", "alice")

    assert kg.query("_world", "last_sweep_actor") == "_engine_tick_sentinel"


# ---------------------------------------------------------------------------
# Test 7: Sentinel node created idempotently across multiple ticks
# ---------------------------------------------------------------------------


def test_passive_sweep_sentinel_node_idempotent_creation(tmp_universe, kg):
    """Sentinel node created once; repeated run_tick calls don't duplicate it."""
    (tmp_universe / "mechanics" / "pickup.py").write_text(_PICKUP_MECHANIC, encoding="utf-8")
    (tmp_universe / "mechanics" / "tick_counter.py").write_text(
        _TICK_COUNTER_MECHANIC, encoding="utf-8"
    )
    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity")
    kg.add_node("rock_1", node_type="entity")
    kg.add_edge("alice", "room_1", type="location")
    kg.add_edge("room_1", "rock_1", type="contains")

    client = MockAnthropicClient(
        [_OK_PICKUP, _OBSERVATION, _OK_PICKUP, _OBSERVATION, _OK_PICKUP, _OBSERVATION]
    )
    engine = SimulationEngine(universe_path=tmp_universe, graph=kg, anthropic_client=client)
    engine.run_tick("pick up rock", "alice")
    engine.run_tick("pick up rock", "alice")
    engine.run_tick("pick up rock", "alice")

    # Sentinel exists exactly once
    assert kg.has_node("_engine_tick_sentinel")
    sentinel_nodes = [n for n in kg.nodes() if n == "_engine_tick_sentinel"]
    assert len(sentinel_nodes) == 1


# ---------------------------------------------------------------------------
# Test 8: Passive sweep mutations counted in tick summary
# ---------------------------------------------------------------------------


def test_passive_sweep_mutations_counted_in_tick_summary(tmp_universe, kg):
    """Sweep mechanic mutations are included in tick_summary mutation count."""
    (tmp_universe / "mechanics" / "pickup.py").write_text(_PICKUP_MECHANIC, encoding="utf-8")
    (tmp_universe / "mechanics" / "mutation_counter.py").write_text(
        _MUTATION_COUNTER_MECHANIC, encoding="utf-8"
    )
    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity")
    kg.add_node("rock_1", node_type="entity")
    kg.add_edge("alice", "room_1", type="location")
    kg.add_edge("room_1", "rock_1", type="contains")

    client = MockAnthropicClient([_OK_PICKUP, _OBSERVATION])
    engine = SimulationEngine(universe_path=tmp_universe, graph=kg, anthropic_client=client)
    engine.run_tick("pick up rock", "alice")

    # Read tick summary
    summary_path = tmp_universe / "tick_summaries" / "ticks" / "tick_1.json"
    assert summary_path.exists()
    data = json.loads(summary_path.read_text())

    # Primary pickup mutation (held_by) + sweep mutation_counter mutation (sweep_count)
    # = at least 2 mutations total
    assert data["mutations"]["count"] >= 2


# ---------------------------------------------------------------------------
# Test 9: WR-01 regression — sweep mechanic that raises records a TraceNode
# ---------------------------------------------------------------------------

_EXPLODING_SWEEP_MECHANIC = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import TickMatcher

class ExplodingSweep(Mechanic):
    id = "exploding_sweep"
    description = "Raises in apply() — used to test WR-01 regression"
    voluntary = False
    tags = []
    def watches(self):
        return [TickMatcher()]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        raise RuntimeError("intentional sweep explosion")
"""


def test_passive_sweep_exception_in_apply_records_trace_node(tmp_universe, kg):
    """WR-01: when a sweep mechanic raises in apply(), a TraceNode with empty
    mutations is appended to the combined trace so the failure is observable
    in diagnostics and the tick summary."""
    (tmp_universe / "mechanics" / "pickup.py").write_text(_PICKUP_MECHANIC, encoding="utf-8")
    (tmp_universe / "mechanics" / "exploding_sweep.py").write_text(
        _EXPLODING_SWEEP_MECHANIC, encoding="utf-8"
    )

    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity")
    kg.add_node("rock_1", node_type="entity")
    kg.add_edge("alice", "room_1", type="location")
    kg.add_edge("room_1", "rock_1", type="contains")

    client = MockAnthropicClient([_OK_PICKUP, _OBSERVATION])
    engine = SimulationEngine(universe_path=tmp_universe, graph=kg, anthropic_client=client)
    result = engine.run_tick("pick up rock", "alice")

    # The tick must still succeed (exception is non-fatal to the tick)
    assert result.kind == "ok"

    # The combined trace must include a TraceNode for the failing sweep mechanic
    assert result.trace is not None
    all_mechanic_ids = _collect_mechanic_ids(result.trace)
    assert "exploding_sweep" in all_mechanic_ids, (
        f"Expected 'exploding_sweep' TraceNode in trace. Found: {all_mechanic_ids}"
    )

    # The failing sweep mechanic's TraceNode must have zero mutations
    exploding_node = _find_trace_node(result.trace, "exploding_sweep")
    assert exploding_node is not None
    assert exploding_node.mutations == [], (
        f"Expected empty mutations for failed sweep, got: {exploding_node.mutations}"
    )


def _collect_mechanic_ids(trace) -> list[str]:
    """Walk the trace tree and collect all mechanic_ids."""
    ids = []
    stack = [trace.root]
    while stack:
        node = stack.pop()
        ids.append(node.mechanic_id)
        stack.extend(node.children)
    return ids


def _find_trace_node(trace, mechanic_id: str):
    """Find the first TraceNode with the given mechanic_id, or None."""
    stack = [trace.root]
    while stack:
        node = stack.pop()
        if node.mechanic_id == mechanic_id:
            return node
        stack.extend(node.children)
    return None
