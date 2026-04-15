"""Integration tests for autopilot_travel + autopilot_advance (Plan 07-06, D-01, D-18).

Tests the full deterministic pipeline end-to-end:
  - 'travel to room_d' → LRA started with route, turns_total=3, hazard thresholds
  - 3 continuation ticks → LRA completes; alice has advanced through the route
  - hazard_level > 0.5 in room_b → interrupts on the tick the hook evaluates room_b
  - attention_state: fine_detail suppressed in projected_state during continuation
  - D-11 cancellation: new action text clears LRA and reverts to normal pipeline

Engine tick ordering (Pitfall 6 in Phase 7 research):
  On EVERY tick (both action and continuation), the engine runs:
    For action ticks (_handle_execute path):
      1. Primary mechanic pipeline (classifier → matcher → decider → apply)
      2. Post-execute: LongRunningHook is NOT called here (Pitfall 1: hook only runs
         on continuation ticks)
      3. Passive sweep (AutopilotAdvanceMechanic fires → alice advances one hop)

    For continuation ticks (_handle_long_running_tick path, run_tick(None)):
      1. LongRunningHook (evaluates thresholds at actor's CURRENT location)
      2. Passive sweep (AutopilotAdvanceMechanic → alice advances one hop)

So after the action tick, the passive sweep has ALREADY run once:
  - LRA next_index: 1 → 2 (alice moved from route[0] to route[1])
  - alice.location = route[1] (room_b for a 4-room route)

After continuation tick 1:
  - Hook evaluates alice in room_b (current after action-tick sweep)
  - Passive sweep: route[2] (room_c), next_index → 3
  - turns_elapsed = 1

After continuation tick 2:
  - Hook evaluates alice in room_c
  - Passive sweep: route[3] (room_d), next_index → 4 (exhausted)
  - turns_elapsed = 2

After continuation tick 3 (completion):
  - Hook: turns_elapsed(2) + 1 == turns_total(3) → LRA completed, cleared
  - Observer synthesises completion narrative

All tests are deterministic using MockAnthropicClient from conftest.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.test_engine.conftest import MockAnthropicClient
from token_world.engine import SimulationEngine
from token_world.graph import KnowledgeGraph
from token_world.mechanic import seeds as seeds_pkg

# ---------------------------------------------------------------------------
# Seed mechanic installation helpers
# ---------------------------------------------------------------------------

_SEEDS_DIR = Path(seeds_pkg.__file__).parent


def _install_autopilot_mechanics(tmp_universe: Path) -> None:
    """Copy both autopilot seed mechanics into the universe's mechanics folder."""
    mechs = tmp_universe / "mechanics"
    mechs.mkdir(exist_ok=True)
    shutil.copy(_SEEDS_DIR / "autopilot_travel.py", mechs / "autopilot_travel.py")
    shutil.copy(_SEEDS_DIR / "autopilot_advance.py", mechs / "autopilot_advance.py")


# ---------------------------------------------------------------------------
# Local fixture overrides
# ---------------------------------------------------------------------------


@pytest.fixture
def kg(tmp_path: Path) -> KnowledgeGraph:
    """KG backed by SQLite — required for snapshot/restore in engine."""
    return KnowledgeGraph(db_path=tmp_path / "autopilot_int_test.db")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Classifier: 'travel to room_d' → verb=travel, target=room_d
_CLASSIFY_TRAVEL = json.dumps(
    {
        "kind": "ok",
        "actions": [
            {
                "verb": "travel",
                "actor": "alice",
                "target": "room_d",
                "params": {},
            }
        ],
        "confidence": 0.92,
    }
)

# Classifier: 'look around' → verb=look, actor=alice, target=alice
_CLASSIFY_LOOK = json.dumps(
    {
        "kind": "ok",
        "actions": [
            {
                "verb": "look",
                "actor": "alice",
                "target": "alice",
                "params": {},
            }
        ],
        "confidence": 0.90,
    }
)

_TRAVEL_COMPLETE = "You arrive at room_d, dusty but unharmed."
_HAZARD_INTERRUPT = "A surge of danger in the corridor jolts you to a halt."
_LOOK_OBS = "You look around carefully."


def _make_engine(
    tmp_universe: Path,
    kg: KnowledgeGraph,
    responses: list[str],
) -> SimulationEngine:
    client = MockAnthropicClient(responses)
    return SimulationEngine(tmp_universe, graph=kg, anthropic_client=client)


def _setup_4_room_linear(kg: KnowledgeGraph) -> None:
    """Build 4-room linear graph with alice in room_a.

    room_a -- room_b -- room_c -- room_d (bidirectional edges via 'passage' relation)
    alice.location = 'room_a'; alice connected to room_a via 'location' edge
    (the VisibilityProjector uses location edges to include rooms in projection)
    """
    kg.add_node("alice", node_type="agent", health=0.9)
    kg.add_node("room_a", node_type="entity")
    kg.add_node("room_b", node_type="entity")
    kg.add_node("room_c", node_type="entity")
    kg.add_node("room_d", node_type="entity")

    # Alice's location property + edge for projector
    kg.set("alice", "location", "room_a")
    kg.add_edge("alice", "room_a", type="location")

    # Bidirectional room passages
    kg.add_edge("room_a", "room_b", relation="passage")
    kg.add_edge("room_b", "room_a", relation="passage")
    kg.add_edge("room_b", "room_c", relation="passage")
    kg.add_edge("room_c", "room_b", relation="passage")
    kg.add_edge("room_c", "room_d", relation="passage")
    kg.add_edge("room_d", "room_c", relation="passage")


# ---------------------------------------------------------------------------
# Test 1: Happy path — 4-room traversal completes in 3 continuation ticks
# ---------------------------------------------------------------------------


def test_autopilot_travel_4_room_happy_path(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """Alice travels room_a → room_b → room_c → room_d then LRA completes.

    Because the passive sweep runs on EVERY tick (including the action tick),
    Alice advances one hop immediately after the LRA is started:
      - After action tick:      alice in room_b (passive sweep fired; next_index=2)
      - After continuation 1:   alice in room_c (sweep again; turns_elapsed=1, next_index=3)
      - After continuation 2:   alice in room_d (sweep again; turns_elapsed=2, next_index=4)
      - After continuation 3:   LRA completed (turns_elapsed=2+1=3 == turns_total=3)
    """
    _install_autopilot_mechanics(tmp_universe)
    _setup_4_room_linear(kg)

    # --- Action tick: start travel ---
    engine = _make_engine(
        tmp_universe,
        kg,
        responses=[
            _CLASSIFY_TRAVEL,
            "You set out on the road to room_d, compass in hand.",
        ],
    )
    result0 = engine.run_tick("travel to room_d", actor="alice")
    assert result0.kind == "ok"

    # LRA structural shape (before/after passive sweep on action tick)
    lra = kg.query("alice", "current_long_action")
    assert lra is not None
    assert lra["action_text"] == "traveling to room_d"
    assert lra["turns_total"] == 3
    assert lra["turns_elapsed"] == 0
    assert lra["payload"]["route"] == ["room_a", "room_b", "room_c", "room_d"]
    # Passive sweep ran on action tick: next_index advanced from 1 → 2
    assert lra["payload"]["next_index"] == 2
    assert lra["payload"]["attention_state"] == {
        "suppress": ["fine_detail"],
        "boost": ["hazard_level"],
    }
    assert {"property": "room_a.hazard_level", "op": ">", "value": 0.5} in lra["thresholds"]
    assert {"property": "room_b.hazard_level", "op": ">", "value": 0.5} in lra["thresholds"]
    assert {"property": "room_c.hazard_level", "op": ">", "value": 0.5} in lra["thresholds"]
    assert {"property": "room_d.hazard_level", "op": ">", "value": 0.5} in lra["thresholds"]
    assert kg.query("alice", "is_traveling") is True
    # Alice already moved to room_b (passive sweep on action tick)
    assert kg.query("alice", "location") == "room_b"

    # --- Continuation tick 1 ---
    # Hook evaluates: alice in room_b (from action-tick sweep); no hazard → no interrupt
    # Passive sweep: route[2]=room_c; next_index → 3; turns_elapsed → 1
    e1 = _make_engine(tmp_universe, kg, responses=[])
    r1 = e1.run_tick(None, actor="alice")
    assert r1.kind == "ok"
    assert "Time passes" in (r1.observation or "") or "traveling" in (r1.observation or "")
    assert kg.query("alice", "location") == "room_c"
    lra1 = kg.query("alice", "current_long_action")
    assert lra1["turns_elapsed"] == 1
    assert lra1["payload"]["next_index"] == 3

    # --- Continuation tick 2 ---
    # Hook: alice in room_c; no hazard → no interrupt; turns_elapsed → 2
    # Passive sweep: route[3]=room_d; next_index → 4
    e2 = _make_engine(tmp_universe, kg, responses=[])
    r2 = e2.run_tick(None, actor="alice")
    assert r2.kind == "ok"
    assert kg.query("alice", "location") == "room_d"
    lra2 = kg.query("alice", "current_long_action")
    assert lra2["turns_elapsed"] == 2
    assert lra2["payload"]["next_index"] == 4

    # --- Continuation tick 3 — completion ---
    # Hook: turns_elapsed(2) + 1 == turns_total(3) → completed; LRA cleared
    # Observer synthesises completion narrative
    # Passive sweep: next_index(4) >= len(route)(4) → no-op
    e3 = _make_engine(tmp_universe, kg, responses=[_TRAVEL_COMPLETE])
    r3 = e3.run_tick(None, actor="alice")
    assert r3.kind == "ok"
    # LRA cleared on completion
    lra3 = kg.query("alice", "current_long_action")
    assert lra3 is None


# ---------------------------------------------------------------------------
# Test 2: Route payload persists across ticks unchanged
# ---------------------------------------------------------------------------


def test_autopilot_travel_route_payload_persists_across_ticks(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """Route list must be identical on every tick after start."""
    _install_autopilot_mechanics(tmp_universe)
    _setup_4_room_linear(kg)

    engine = _make_engine(
        tmp_universe,
        kg,
        responses=[_CLASSIFY_TRAVEL, "You begin the journey."],
    )
    engine.run_tick("travel to room_d", actor="alice")

    expected_route = ["room_a", "room_b", "room_c", "room_d"]
    for tick_n in range(2):
        e = _make_engine(tmp_universe, kg, responses=[])
        e.run_tick(None, actor="alice")
        lra = kg.query("alice", "current_long_action")
        assert lra is not None, f"LRA unexpectedly cleared at continuation tick {tick_n}"
        assert lra["payload"]["route"] == expected_route


# ---------------------------------------------------------------------------
# Test 3: next_index advances each tick
# ---------------------------------------------------------------------------


def test_autopilot_travel_next_index_advances_each_tick(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """next_index must advance by 1 per tick (action tick passive sweep runs too).

    After action tick: next_index=2 (passive sweep on action tick fired once)
    After continuation 1: next_index=3
    After continuation 2: next_index=4 (route exhausted)
    """
    _install_autopilot_mechanics(tmp_universe)
    _setup_4_room_linear(kg)

    engine = _make_engine(
        tmp_universe,
        kg,
        responses=[_CLASSIFY_TRAVEL, "On the road."],
    )
    engine.run_tick("travel to room_d", actor="alice")
    # After action tick: passive sweep ran → next_index=2
    lra_after_action = kg.query("alice", "current_long_action")
    assert lra_after_action["payload"]["next_index"] == 2

    # Continuation 1 → next_index=3
    e1 = _make_engine(tmp_universe, kg, responses=[])
    e1.run_tick(None, actor="alice")
    lra1 = kg.query("alice", "current_long_action")
    assert lra1["payload"]["next_index"] == 3

    # Continuation 2 → next_index=4 (exhausted; no-op on further sweeps)
    e2 = _make_engine(tmp_universe, kg, responses=[])
    e2.run_tick(None, actor="alice")
    lra2 = kg.query("alice", "current_long_action")
    assert lra2["payload"]["next_index"] == 4


# ---------------------------------------------------------------------------
# Test 4: Hazard interruption
# ---------------------------------------------------------------------------


def test_autopilot_travel_hazard_interruption_on_second_room(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """Hazard in room_b triggers interruption on the continuation tick the hook evaluates room_b.

    Timeline with passive sweep running on action tick:
      Action tick:   travel starts; passive sweep → alice moves to room_b (next_index=2)
      Tick 1 (cont): hook evaluates alice in room_b; room_b.hazard_level=0.8 > 0.5
                     → threshold fires → LRA interrupted → hazard narrative

    This demonstrates that alice "perceives" room_b on the FIRST continuation tick
    because the passive sweep on the action tick already placed her there.
    """
    _install_autopilot_mechanics(tmp_universe)
    _setup_4_room_linear(kg)

    # Set hazard in room_b before travel starts
    kg.set("room_b", "hazard_level", 0.8)

    # Action tick: start travel; passive sweep advances alice to room_b
    engine = _make_engine(
        tmp_universe,
        kg,
        responses=[_CLASSIFY_TRAVEL, "You set off toward room_d."],
    )
    result0 = engine.run_tick("travel to room_d", actor="alice")
    assert result0.kind == "ok"
    # After action tick: passive sweep moved alice to room_b
    assert kg.query("alice", "location") == "room_b"

    # Continuation tick 1: hook evaluates room_b.hazard_level=0.8 > 0.5 → interrupt
    e1 = _make_engine(tmp_universe, kg, responses=[_HAZARD_INTERRUPT])
    r1 = e1.run_tick(None, actor="alice")
    assert r1.kind == "ok"

    # LRA must be cleared (interrupted)
    lra_after = kg.query("alice", "current_long_action")
    assert lra_after is None


# ---------------------------------------------------------------------------
# Test 5: attention_state suppresses fine_detail during continuation
# ---------------------------------------------------------------------------


def test_autopilot_travel_attention_state_applied_during_continuation(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """During autopilot travel, fine_detail must be absent from projected_state (D-12)."""
    _install_autopilot_mechanics(tmp_universe)
    _setup_4_room_linear(kg)
    # Add fine_detail to room_a so we can verify it's suppressed
    kg.set("room_a", "fine_detail", "ornate archways line the hall")

    engine = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_TRAVEL, "You begin traveling."])
    engine.run_tick("travel to room_d", actor="alice")

    # Continuation tick — check projected_state
    e2 = _make_engine(tmp_universe, kg, responses=[])
    result = e2.run_tick(None, actor="alice")
    assert result.kind == "ok"

    proj = result.projected_state or {}
    # fine_detail must NOT appear in any node's projected properties
    for _node_id, node_data in proj.items():
        node_props = node_data.get("properties", {}) if isinstance(node_data, dict) else {}
        assert "fine_detail" not in node_props, (
            f"fine_detail should be suppressed during autopilot travel, "
            f"found in node data: {node_data}"
        )


# ---------------------------------------------------------------------------
# Test 6: D-11 cancellation — new action clears LRA, pipeline runs normally
# ---------------------------------------------------------------------------


def test_autopilot_travel_cancellation_by_new_action(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """New action_text while traveling → LRA cleared, normal pipeline runs (D-11)."""
    _install_autopilot_mechanics(tmp_universe)
    _setup_4_room_linear(kg)

    # Start travel
    engine = _make_engine(
        tmp_universe,
        kg,
        responses=[_CLASSIFY_TRAVEL, "Off to room_d!"],
    )
    engine.run_tick("travel to room_d", actor="alice")
    assert kg.query("alice", "current_long_action") is not None

    # One continuation tick
    e1 = _make_engine(tmp_universe, kg, responses=[])
    e1.run_tick(None, actor="alice")

    lra_mid = kg.query("alice", "current_long_action")
    assert lra_mid is not None
    assert lra_mid["turns_elapsed"] == 1

    # Issue a new action — D-11: clears LRA before pipeline runs
    # 'look around' may fail without the look mechanic installed, but the LRA
    # must still be cleared before the pipeline runs (D-11 guarantee)
    e_cancel = _make_engine(
        tmp_universe,
        kg,
        responses=[_CLASSIFY_LOOK, _LOOK_OBS],
    )
    result_cancel = e_cancel.run_tick("look around", actor="alice")

    # LRA must be cleared before the new pipeline ran
    lra_after = kg.query("alice", "current_long_action")
    assert lra_after is None
    # New tick ran normally (not a continuation tick)
    assert result_cancel.kind in ("refused", "ok", "yielded")
