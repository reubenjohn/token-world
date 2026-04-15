"""Tests for Phase 16 composite-action engine wiring (SC-3 regression suite).

Covers:
- test_schema_version_is_2: classifier SCHEMA_VERSION == "2.0"
- test_single_verb_back_compat: 1-element actions list → 1 mechanic executed (back-compat)
- test_multi_verb_two_mechanics: 2-action classifier mock → 2 mechanic executions
- test_multi_verb_first_sub_refused_second_runs: refuse-continues policy
- test_multi_verb_first_sub_yields_halts_tick: first-yield-wins policy
- test_tick_summary_has_classified_actions_list: classified_actions list in persisted JSON

MockAnthropicClient response order matters: Haiku (classifier) first, Sonnet (observer) second.
For execute-path ticks, responses are [haiku_classifier_resp, sonnet_observer_resp].
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_engine.conftest import MockAnthropicClient
from token_world.engine import SimulationEngine
from token_world.graph import KnowledgeGraph

# ---------------------------------------------------------------------------
# Local kg fixture: requires SQLite persistence for snapshot/restore
# ---------------------------------------------------------------------------


@pytest.fixture
def kg(tmp_path: Path) -> KnowledgeGraph:
    """KnowledgeGraph backed by a temp SQLite db — required for snapshot/restore."""
    return KnowledgeGraph(db_path=tmp_path / "composite_test.db")


# ---------------------------------------------------------------------------
# Mechanic source code strings
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

_OPEN_MECHANIC_SOURCE = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import VerbMatcher

class Open(Mechanic):
    id = "open"
    description = "Open a container entity"
    voluntary = True
    tags = []
    def watches(self):
        return [VerbMatcher(verb="open")]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        return [ctx.set(ctx.target, "is_open", True)]
"""

_REFUSING_PICKUP_SOURCE = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import VerbMatcher

class RefusingPickup(Mechanic):
    id = "pickup"
    description = "Pickup mechanic that always refuses"
    voluntary = True
    tags = []
    def watches(self):
        return [VerbMatcher(verb="pickup")]
    def check(self, ctx):
        return CheckResult(passed=False, reasons=["cannot pickup here"])
    def apply(self, ctx):
        return []
"""

# ---------------------------------------------------------------------------
# Classifier response JSON strings
# ---------------------------------------------------------------------------

_OK_SINGLE_PICKUP = json.dumps(
    {
        "kind": "ok",
        "actions": [{"verb": "pickup", "actor": "alice", "target": "rock_1", "params": {}}],
        "confidence": 0.95,
    }
)

_OK_TWO_ACTIONS = json.dumps(
    {
        "kind": "ok",
        "actions": [
            {"verb": "open", "actor": "alice", "target": "chest_1", "params": {}},
            {"verb": "pickup", "actor": "alice", "target": "rock_1", "params": {}},
        ],
        "confidence": 0.95,
    }
)

# First action (pickup) will refuse; second (open) will succeed
_OK_REFUSE_FIRST_THEN_OPEN = json.dumps(
    {
        "kind": "ok",
        "actions": [
            {"verb": "pickup", "actor": "alice", "target": "rock_1", "params": {}},
            {"verb": "open", "actor": "alice", "target": "chest_1", "params": {}},
        ],
        "confidence": 0.95,
    }
)

# First action has no matching mechanic (open), second has match (pickup)
_OK_NO_MATCH_FIRST = json.dumps(
    {
        "kind": "ok",
        "actions": [
            {"verb": "open", "actor": "alice", "target": "chest_1", "params": {}},
            {"verb": "pickup", "actor": "alice", "target": "rock_1", "params": {}},
        ],
        "confidence": 0.95,
    }
)

_OBSERVATION = "You open the chest and pick up the rock."
_PARTIAL_OBSERVATION = "You open the chest."
_REFUSE_OBSERVATION = "You try to pick it up but fail."


# ---------------------------------------------------------------------------
# Helper: scaffold a universe with specific mechanics
# ---------------------------------------------------------------------------


def _build_universe(tmp_universe: Path, mechanic_sources: dict[str, str]) -> None:
    """Write mechanic .py files into the universe mechanics/ directory."""
    for filename, source in mechanic_sources.items():
        (tmp_universe / "mechanics" / filename).write_text(source, encoding="utf-8")


def _build_graph(kg: KnowledgeGraph) -> None:
    """Add standard test nodes to the graph."""
    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity")
    kg.add_node("rock_1", node_type="entity")
    kg.add_node("chest_1", node_type="entity")
    kg.add_edge("alice", "room_1", type="location")
    kg.add_edge("room_1", "rock_1", type="contains")
    kg.add_edge("room_1", "chest_1", type="contains")


# ---------------------------------------------------------------------------
# SC-4 schema version test (already passes from Wave 1)
# ---------------------------------------------------------------------------


def test_schema_version_is_2() -> None:
    """SC-4: SCHEMA_VERSION must be '2.0' (set in Wave 1)."""
    from token_world.engine.classifier import SCHEMA_VERSION

    assert SCHEMA_VERSION == "2.0", f"Expected '2.0', got {SCHEMA_VERSION!r}"


# ---------------------------------------------------------------------------
# SC-2 back-compat: single-verb input produces single-trace entry
# ---------------------------------------------------------------------------


def test_single_verb_back_compat(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """1-element actions list → exactly 1 mechanic executed (back-compat guarantee)."""
    _build_universe(tmp_universe, {"pickup.py": _PICKUP_MECHANIC_SOURCE})
    _build_graph(kg)

    client = MockAnthropicClient([_OK_SINGLE_PICKUP, _OBSERVATION])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    result = engine.run_tick("pick up the rock", actor="alice")

    assert result.kind == "ok", f"Expected ok, got {result.kind!r}: {result.observation}"
    assert result.trace is not None
    # Single sub-action: root node should be from the pickup mechanic
    assert result.trace.root.mechanic_id == "pickup"
    # Rock should now be held by alice
    assert kg.query("rock_1", "held_by") == "alice"


# ---------------------------------------------------------------------------
# SC-3: multi-verb produces two trace entries
# ---------------------------------------------------------------------------


def test_multi_verb_two_mechanics(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """2-action classifier mock → engine executes both mechanics, trace covers both.

    Classifier returns: [{verb:"open", target:"chest_1"}, {verb:"pickup", target:"rock_1"}]
    Both mechanics registered → tick should produce ok result with mutations from both.
    """
    _build_universe(
        tmp_universe,
        {
            "open.py": _OPEN_MECHANIC_SOURCE,
            "pickup.py": _PICKUP_MECHANIC_SOURCE,
        },
    )
    _build_graph(kg)

    client = MockAnthropicClient([_OK_TWO_ACTIONS, _OBSERVATION])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    result = engine.run_tick("open the chest and take the rock", actor="alice")

    assert result.kind == "ok", f"Expected ok, got {result.kind!r}: {result.observation}"
    assert result.trace is not None

    # Both mutations should be reflected in the graph
    assert kg.query("chest_1", "is_open") is True, "chest should be open"
    rock_props = kg.query("rock_1")
    assert rock_props.get("held_by") == "alice", "rock should be held by alice"


# ---------------------------------------------------------------------------
# SC-3: refuse-continues policy
# ---------------------------------------------------------------------------


def test_multi_verb_first_sub_refused_second_runs(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """First sub-action's check() returns False → refuse-continues; second runs.

    Classifier returns: [{verb:"pickup", target:"rock_1"}, {verb:"open", target:"chest_1"}]
    pickup's check() always fails; open's check() passes.
    Tick result should be ok (second mechanic ran); chest_1.is_open==True.
    rock_1.held_by should NOT be set (first mechanic refused).
    """
    _build_universe(
        tmp_universe,
        {
            "pickup.py": _REFUSING_PICKUP_SOURCE,  # always refuses
            "open.py": _OPEN_MECHANIC_SOURCE,  # always passes
        },
    )
    _build_graph(kg)

    client = MockAnthropicClient([_OK_REFUSE_FIRST_THEN_OPEN, _PARTIAL_OBSERVATION])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    result = engine.run_tick("pick up the rock and open the chest", actor="alice")

    assert result.kind == "ok", (
        f"Expected ok (refuse-continues policy), got {result.kind!r}: {result.observation}"
    )
    # Second mechanic should have run
    assert kg.query("chest_1", "is_open") is True, "open mechanic should have run"
    # First mechanic was refused — rock should NOT have held_by set
    rock_props = kg.query("rock_1")
    assert rock_props.get("held_by") is None, "refused mechanic should not have mutated rock"


# ---------------------------------------------------------------------------
# SC-3: first-yield-wins policy
# ---------------------------------------------------------------------------


def test_multi_verb_first_sub_yields_halts_tick(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """First sub-action has no matching mechanic → yields; second never evaluated.

    Classifier returns: [{verb:"open", target:"chest_1"}, {verb:"pickup", target:"rock_1"}]
    Only pickup mechanic registered (no open) → first action yields.
    Result should be 'yielded'; rock should NOT be mutated.
    """
    # Only register pickup, NOT open
    _build_universe(tmp_universe, {"pickup.py": _PICKUP_MECHANIC_SOURCE})
    _build_graph(kg)

    # Only classifier response needed — yield path doesn't call observer
    client = MockAnthropicClient([_OK_NO_MATCH_FIRST])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    result = engine.run_tick("open the chest and take the rock", actor="alice")

    assert result.kind == "yielded", f"Expected yielded, got {result.kind!r}: {result.observation}"
    # Second mechanic should never have run
    rock_props = kg.query("rock_1")
    assert rock_props.get("held_by") is None, "rock should not be mutated after yield"


# ---------------------------------------------------------------------------
# classified_actions list in tick summary JSON
# ---------------------------------------------------------------------------


def test_tick_summary_has_classified_actions_list(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """After a multi-verb tick, tick JSON must have 'classified_actions' key with 2 items.

    Also verifies back-compat: 'classified_action' (singular) should still be present
    and equal to classified_actions[0].
    """
    _build_universe(
        tmp_universe,
        {
            "open.py": _OPEN_MECHANIC_SOURCE,
            "pickup.py": _PICKUP_MECHANIC_SOURCE,
        },
    )
    _build_graph(kg)

    client = MockAnthropicClient([_OK_TWO_ACTIONS, _OBSERVATION])
    engine = SimulationEngine(
        universe_path=tmp_universe,
        graph=kg,
        anthropic_client=client,
    )
    result = engine.run_tick("open the chest and take the rock", actor="alice")
    assert result.kind == "ok"

    # Find the tick summary file
    tick_dir = tmp_universe / "tick_summaries" / "ticks"
    tick_files = list(tick_dir.glob("tick_*.json"))
    assert len(tick_files) == 1, f"Expected 1 tick file, got {len(tick_files)}"

    data = json.loads(tick_files[0].read_text())

    # classified_actions must be a list with 2 entries
    assert "classified_actions" in data, (
        f"'classified_actions' key missing from tick JSON: {list(data.keys())}"
    )
    classified_actions = data["classified_actions"]
    assert isinstance(classified_actions, list), f"Expected list, got {type(classified_actions)}"
    assert len(classified_actions) == 2, (
        f"Expected 2 classified_actions, got {len(classified_actions)}"
    )

    # Back-compat: classified_action (singular) should be present and equal to classified_actions[0]
    assert "classified_action" in data, "'classified_action' back-compat key missing"
    assert data["classified_action"] == classified_actions[0], (
        "classified_action (back-compat) should equal classified_actions[0]"
    )
