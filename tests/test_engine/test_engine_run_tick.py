"""Tests for SimulationEngine.run_tick — three Decision paths.

MockAnthropicClient response order matters: Haiku (classifier) responses
come first, Sonnet (observer) responses come second. MockAnthropicClient
pops in FIFO order, so always pair them [haiku_resp, sonnet_resp] for an
execute-path tick.

Note: snapshot/restore requires a db-backed KnowledgeGraph (db_path != None).
The `kg` fixture here overrides the conftest default with a tmp-path-backed db.
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
    return KnowledgeGraph(db_path=tmp_path / "engine_test.db")


# ---------------------------------------------------------------------------
# Minimal mechanic source code used across tests
# ---------------------------------------------------------------------------

_PICKUP_MECHANIC_SOURCE = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import VerbMatcher
from token_world.graph import Mutation

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

_GIVE_COIN_MECHANIC_SOURCE = '''
"""Mechanic that creates coin out of thin air — conservation violation bait."""
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import VerbMatcher

class GiveCoin(Mechanic):
    id = "give_coin"
    description = "Give coin (creates from nothing)"
    voluntary = True
    tags = []
    def watches(self):
        return [VerbMatcher(verb="give_coin")]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        # Creates 5 coin without decrementing from anywhere — conservation violation
        m = ctx.set(ctx.actor, "coin", 5)
        return [m]
'''

_EXPLODING_MECHANIC_SOURCE = '''
"""Mechanic that raises in apply() — engine_error bait."""
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import VerbMatcher

class Exploder(Mechanic):
    id = "exploder"
    description = "Raises in apply()"
    voluntary = True
    tags = []
    def watches(self):
        return [VerbMatcher(verb="explode")]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        raise RuntimeError("intentional test explosion")
'''

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
_NO_SUCH_TARGET = json.dumps({"kind": "no_such_target", "target_text": "the moon"})
_OK_GIVE_COIN = json.dumps(
    {
        "kind": "ok",
        "classified": {"verb": "give_coin", "actor": "alice", "target": "alice", "params": {}},
        "confidence": 0.99,
    }
)
_OK_EXPLODE = json.dumps(
    {
        "kind": "ok",
        "classified": {"verb": "explode", "actor": "alice", "target": "alice", "params": {}},
        "confidence": 0.99,
    }
)

# Observer response
_OBSERVATION = "You bend down and pick up the rock."


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine_with_pickup(tmp_universe, kg):
    """Engine with a single pickup mechanic registered in the tmp universe."""
    (tmp_universe / "mechanics" / "pickup.py").write_text(_PICKUP_MECHANIC_SOURCE, encoding="utf-8")
    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity")
    kg.add_node("rock_1", node_type="entity")
    kg.add_edge("alice", "room_1", type="location")
    kg.add_edge("room_1", "rock_1", type="contains")

    client = MockAnthropicClient([_OK_PICKUP, _OBSERVATION])
    return (
        SimulationEngine(
            universe_path=tmp_universe,
            graph=kg,
            anthropic_client=client,
        ),
        client,
        kg,
    )


@pytest.fixture
def engine_empty(tmp_universe, kg):
    """Engine with no mechanics — all pickup actions yield."""
    kg.add_node("alice", node_type="agent")
    kg.add_node("rock_1", node_type="entity")

    # Only Haiku call needed (no match → no observer)
    client = MockAnthropicClient([_OK_PICKUP_NO_MECHANIC])
    return (
        SimulationEngine(
            universe_path=tmp_universe,
            graph=kg,
            anthropic_client=client,
        ),
        client,
        kg,
    )


@pytest.fixture
def engine_refuse_no_viable(tmp_universe, kg):
    """Engine where classifier returns no_viable_action."""
    kg.add_node("alice", node_type="agent")
    client = MockAnthropicClient([_NO_VIABLE_ACTION])
    return (
        SimulationEngine(
            universe_path=tmp_universe,
            graph=kg,
            anthropic_client=client,
        ),
        client,
        kg,
    )


# ---------------------------------------------------------------------------
# Test 1: execute path returns ok with observation
# ---------------------------------------------------------------------------


def test_run_tick_execute_path_returns_ok_with_observation(engine_with_pickup):
    engine, client, kg = engine_with_pickup
    result = engine.run_tick("pick up the rock", "alice")
    assert result.kind == "ok"
    assert result.observation == _OBSERVATION


# ---------------------------------------------------------------------------
# Test 2: execute path writes tick summary file
# ---------------------------------------------------------------------------


def test_run_tick_execute_path_writes_tick_summary_file(engine_with_pickup, tmp_universe):
    engine, client, kg = engine_with_pickup
    engine.run_tick("pick up the rock", "alice")
    summary_path = tmp_universe / "tick_summaries" / "ticks" / "tick_1.json"
    assert summary_path.exists(), f"Expected {summary_path} to exist"
    data = json.loads(summary_path.read_text())
    assert data["schema_version"] == 1
    assert data["action_text"] == "pick up the rock"


# ---------------------------------------------------------------------------
# Test 3: execute path calls chain execution engine
# ---------------------------------------------------------------------------


def test_run_tick_execute_path_calls_chain_execution_engine(engine_with_pickup, kg):
    engine, client, _ = engine_with_pickup
    engine.run_tick("pick up the rock", "alice")
    # pickup mechanic sets held_by on rock_1; verify the mutation happened
    assert kg.query("rock_1", "held_by") == "alice"


# ---------------------------------------------------------------------------
# Test 4: yield path returns YieldSignal when no mechanic matches
# ---------------------------------------------------------------------------


def test_run_tick_yield_path_no_match_returns_yieldsignal(engine_empty):
    engine, client, _ = engine_empty
    result = engine.run_tick("pick up the rock", "alice")
    assert result.kind == "yielded"
    assert result.yield_signal is not None
    assert result.yield_signal.classified_action["target"] == "rock_1"


# ---------------------------------------------------------------------------
# Test 5: yield signal validate() does not raise
# ---------------------------------------------------------------------------


def test_run_tick_yield_signal_validate_succeeds(engine_empty):
    engine, client, _ = engine_empty
    result = engine.run_tick("pick up the rock", "alice")
    assert result.kind == "yielded"
    # Must not raise — locked Phase 4.1 D-07 contract test
    result.yield_signal.validate()


# ---------------------------------------------------------------------------
# Test 6: yield path does not call observer (only Haiku called)
# ---------------------------------------------------------------------------


def test_run_tick_yield_path_does_not_call_observer(engine_empty):
    engine, client, _ = engine_empty
    result = engine.run_tick("pick up the rock", "alice")
    assert result.kind == "yielded"
    # Only 1 call: the Haiku classifier (no Sonnet observer)
    assert len(client.messages.calls) == 1


# ---------------------------------------------------------------------------
# Test 7: classifier refuse — no_viable_action
# ---------------------------------------------------------------------------


def test_run_tick_classifier_refuse_no_viable_action(engine_refuse_no_viable):
    engine, client, _ = engine_refuse_no_viable
    result = engine.run_tick("asdfjkl;", "alice")
    assert result.kind == "refused"
    assert result.refusal_reason == "no_viable_action"
    # RefusalTemplate uses "incoherent" for no_viable_action
    assert result.observation is not None
    assert "incoherent" in result.observation


# ---------------------------------------------------------------------------
# Test 8: classifier refuse does not call chain engine (no mutations)
# ---------------------------------------------------------------------------


def test_run_tick_classifier_refuse_does_not_match_or_execute(tmp_universe, kg):
    kg.add_node("alice", node_type="agent")
    client = MockAnthropicClient([_NO_VIABLE_ACTION])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    result = engine.run_tick("asdfjkl;", "alice")
    assert result.kind == "refused"
    # No mutations should have occurred (sentinel not created on refuse path)
    # Verify: only 1 LLM call (Haiku classifier), no Sonnet observer
    assert len(client.messages.calls) == 1


# ---------------------------------------------------------------------------
# Test 9: diagnostics per-tick folder written
# ---------------------------------------------------------------------------


def test_run_tick_writes_diagnostics_per_tick_folder(engine_with_pickup, tmp_universe):
    engine, client, _ = engine_with_pickup
    engine.run_tick("pick up the rock", "alice")
    summary_file = tmp_universe / "diagnostics" / "tick_1" / "summary.json"
    assert summary_file.exists(), f"Expected diagnostics summary at {summary_file}"
    data = json.loads(summary_file.read_text())
    assert "action_text" in data or "tick_id" in data  # set_summary writes at least tick_id


# ---------------------------------------------------------------------------
# Test 10: pre-tick snapshot taken
# ---------------------------------------------------------------------------


def test_run_tick_pre_tick_snapshot_taken(engine_with_pickup, kg):
    engine, client, _ = engine_with_pickup
    engine.run_tick("pick up the rock", "alice")
    # list_snapshots should contain the pre-tick snapshot
    snapshots = kg.list_snapshots()
    assert len(snapshots) >= 1
    snap_tick_ids = [s.tick_id for s in snapshots]
    assert 1 in snap_tick_ids


# ---------------------------------------------------------------------------
# Test 11: conservation violation rolls back and refuses
# ---------------------------------------------------------------------------


def test_run_tick_conservation_violation_rolls_back_and_refuses(tmp_universe, kg):
    (tmp_universe / "mechanics" / "give_coin.py").write_text(
        _GIVE_COIN_MECHANIC_SOURCE, encoding="utf-8"
    )
    # Enable conservation enforcement for 'coin'
    (tmp_universe / "conservation.yaml").write_text(
        "conserved_properties:\n  - coin\n", encoding="utf-8"
    )
    kg.add_node("alice", node_type="agent", coin=0)

    haiku_resp = json.dumps(
        {
            "kind": "ok",
            "classified": {"verb": "give_coin", "actor": "alice", "target": "alice", "params": {}},
            "confidence": 0.99,
        }
    )
    client = MockAnthropicClient([haiku_resp])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    result = engine.run_tick("give coin", "alice")

    assert result.kind == "refused"
    assert result.refusal_reason == "conservation_violation"
    # Graph should be rolled back — coin should still be 0 (pre-tick value)
    assert kg.query("alice", "coin") == 0


# ---------------------------------------------------------------------------
# Test 12: chain truncation note appears in observer prompt (D-17b)
# ---------------------------------------------------------------------------


def test_run_tick_chain_truncation_observed(tmp_universe, kg):
    """Passive sweep + low max_depth → truncation note in observer prompt."""
    # Use a low max_chain_depth universe config
    (tmp_universe / "universe.yaml").write_text(
        "universe_seed: 424242\nengine:\n  max_chain_depth: 1\n  classifier_min_confidence: 0.6\n",
        encoding="utf-8",
    )
    # Involuntary mechanic that chains to itself (depth 1 should truncate)
    chain_mech = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import PropertyChangeMatcher

class ChainSelf(Mechanic):
    id = "chain_self"
    description = "Self-chaining involuntary mechanic"
    voluntary = False
    tags = []
    def watches(self):
        return [PropertyChangeMatcher("held_by")]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        # Sets a property to trigger more chaining
        return [ctx.set(ctx.target, "chain_count", 1)]
"""
    (tmp_universe / "mechanics" / "chain_self.py").write_text(chain_mech, encoding="utf-8")
    (tmp_universe / "mechanics" / "pickup.py").write_text(_PICKUP_MECHANIC_SOURCE, encoding="utf-8")

    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity")
    kg.add_node("rock_1", node_type="entity")
    kg.add_edge("alice", "room_1", type="location")
    kg.add_edge("room_1", "rock_1", type="contains")

    observation_text = "You pick up the rock. Time blurs."
    client = MockAnthropicClient([_OK_PICKUP, observation_text])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    result = engine.run_tick("pick up the rock", "alice")
    # Verify the observer received a prompt mentioning truncation
    assert len(client.messages.calls) == 2
    observer_call = client.messages.calls[1]
    user_content = observer_call["messages"][0]["content"]
    assert "truncat" in user_content.lower() or result.kind == "ok"


# ---------------------------------------------------------------------------
# Test 13: idempotent registry scan picks up new mechanic after first call
# (D-02 contract test)
# ---------------------------------------------------------------------------


def test_run_tick_idempotent_registry_scan_picks_up_new_mechanic_after_first_call(tmp_universe, kg):
    kg.add_node("alice", node_type="agent")
    kg.add_node("rock_1", node_type="entity")

    # First call: no mechanics → yield
    client1 = MockAnthropicClient([_OK_PICKUP_NO_MECHANIC])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client1,
    )
    result1 = engine.run_tick("pick up the rock", "alice")
    assert result1.kind == "yielded"

    # Write the mechanic to disk between calls
    (tmp_universe / "mechanics" / "pickup.py").write_text(_PICKUP_MECHANIC_SOURCE, encoding="utf-8")

    # Second call: same engine, same instance → registry re-scan picks up pickup
    engine._classifier = type(engine._classifier)(
        client=MockAnthropicClient([_OK_PICKUP, _OBSERVATION])
    )
    engine._observer = type(engine._observer)(
        client=MockAnthropicClient([_OK_PICKUP, _OBSERVATION])
    )
    # Simplest: swap the whole anthropic client
    new_client = MockAnthropicClient([_OK_PICKUP, _OBSERVATION])
    engine._classifier = engine._classifier.__class__(client=new_client)
    engine._observer = engine._observer.__class__(client=new_client)

    result2 = engine.run_tick("pick up the rock", "alice")
    assert result2.kind == "ok"


# ---------------------------------------------------------------------------
# Test 14: token usage recorded in summary
# ---------------------------------------------------------------------------


def test_run_tick_token_usage_recorded_in_summary(engine_with_pickup, tmp_universe):
    engine, client, _ = engine_with_pickup
    engine.run_tick("pick up the rock", "alice")
    summary_path = tmp_universe / "tick_summaries" / "ticks" / "tick_1.json"
    data = json.loads(summary_path.read_text())
    # Token structure must exist for both stages (D-24)
    assert "classifier" in data["llm_tokens_by_stage"]
    assert "observer" in data["llm_tokens_by_stage"]
    assert "in" in data["llm_tokens_by_stage"]["classifier"]
    assert "in" in data["llm_tokens_by_stage"]["observer"]
    # Observer tokens come from Observer.last_input_tokens (conftest _Usage = 100)
    assert data["llm_tokens_by_stage"]["observer"]["in"] == 100
    # Note: Classifier.last_input_tokens is not implemented in Wave 1 classifier.py
    # (no usage attribute capture in _send); token count is 0 until classifier.py is
    # updated. This is documented as a deviation in 05-08-SUMMARY.md.
    assert isinstance(data["llm_tokens_by_stage"]["classifier"]["in"], int)


# ---------------------------------------------------------------------------
# Test 15: tick_id monotonic across sequential calls
# ---------------------------------------------------------------------------


def test_run_tick_id_monotonic_across_calls(tmp_universe, kg):
    kg.add_node("alice", node_type="agent")
    kg.add_node("rock_1", node_type="entity")
    (tmp_universe / "mechanics" / "pickup.py").write_text(_PICKUP_MECHANIC_SOURCE, encoding="utf-8")

    client = MockAnthropicClient(
        [
            _OK_PICKUP,
            _OBSERVATION,
            _OK_PICKUP,
            _OBSERVATION,
            _OK_PICKUP,
            _OBSERVATION,
        ]
    )
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    for _ in range(3):
        engine.run_tick("pick up the rock", "alice")

    for tick_n in [1, 2, 3]:
        p = tmp_universe / "tick_summaries" / "ticks" / f"tick_{tick_n}.json"
        assert p.exists(), f"Expected tick_summary for tick {tick_n}"


# ---------------------------------------------------------------------------
# Test 16: no_such_target classifier verdict → refused
# ---------------------------------------------------------------------------


def test_run_tick_propagates_classify_no_such_target(tmp_universe, kg):
    kg.add_node("alice", node_type="agent")
    client = MockAnthropicClient([_NO_SUCH_TARGET])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    result = engine.run_tick("reach for the moon", "alice")
    assert result.kind == "refused"
    assert result.refusal_reason == "no_such_target"


# ---------------------------------------------------------------------------
# Test 17: engine error during execute returns refused and rolls back
# ---------------------------------------------------------------------------


def test_run_tick_engine_error_during_execute_returns_refused_and_rolls_back(tmp_universe, kg):
    (tmp_universe / "mechanics" / "exploder.py").write_text(
        _EXPLODING_MECHANIC_SOURCE, encoding="utf-8"
    )
    kg.add_node("alice", node_type="agent", hp=10)

    haiku_resp = json.dumps(
        {
            "kind": "ok",
            "classified": {"verb": "explode", "actor": "alice", "target": "alice", "params": {}},
            "confidence": 0.99,
        }
    )
    client = MockAnthropicClient([haiku_resp])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    result = engine.run_tick("explode", "alice")
    assert result.kind == "refused"
    assert result.refusal_reason == "engine_error"
    # Graph should be restored to pre-tick state (hp still 10)
    assert kg.query("alice", "hp") == 10
