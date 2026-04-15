"""Integration tests for the sleep seed mechanic end-to-end (Plan 07-05, D-14, D-18).

Tests the full deterministic pipeline:
  - sleep action → LRA started, is_sleeping=True
  - continuation ticks → turns_elapsed advances, static 'Time passes' observation
  - noise threshold fires → LRA cleared, interruption observation from MockAnthropic
  - 8-tick completion → hook calls observer for completion narrative, LRA cleared
  - D-11 implicit cancellation — new action text clears sleep LRA
  - Classifier is NOT called on continuation ticks (run_tick(None) path)
  - attention_state: visual_detail suppressed from projected_state during sleep

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
# Seed mechanic installation helper
# ---------------------------------------------------------------------------

_SEEDS_DIR = Path(seeds_pkg.__file__).parent


def _install_sleep_mechanic(tmp_universe: Path) -> None:
    """Copy sleep.py into the universe's mechanics folder so registry picks it up."""
    mechs = tmp_universe / "mechanics"
    mechs.mkdir(exist_ok=True)
    shutil.copy(_SEEDS_DIR / "sleep.py", mechs / "sleep.py")


# ---------------------------------------------------------------------------
# Local fixture overrides
# ---------------------------------------------------------------------------


@pytest.fixture
def kg(tmp_path: Path) -> KnowledgeGraph:
    """KG backed by SQLite — required for snapshot/restore in engine."""
    return KnowledgeGraph(db_path=tmp_path / "sleep_int_test.db")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Classifier response for 'sleep' action
_CLASSIFY_SLEEP = json.dumps(
    {
        "kind": "ok",
        "actions": [{"verb": "sleep", "actor": "alice", "target": "alice", "params": {}}],
        "confidence": 0.95,
    }
)

# Classifier response for 'go north' action
_CLASSIFY_GO_NORTH = json.dumps(
    {
        "kind": "ok",
        "actions": [{"verb": "go", "actor": "alice", "target": "north", "params": {}}],
        "confidence": 0.90,
    }
)

# Classifier response for low-confidence / no match
_CLASSIFY_NO_MATCH = json.dumps({"kind": "no_viable_action", "reason": "no match"})

_WAKE_NOISE = "You jolt awake to a loud noise piercing the room."
_WAKE_COMPLETED = "You wake naturally, rested after 8 hours of sleep."


def _make_engine(
    tmp_universe: Path,
    kg: KnowledgeGraph,
    responses: list[str],
) -> SimulationEngine:
    client = MockAnthropicClient(responses)
    return SimulationEngine(tmp_universe, graph=kg, anthropic_client=client)


def _setup_alice_in_bedroom(kg: KnowledgeGraph) -> None:
    """Add alice and a bedroom to the graph.

    Sets both:
    - alice.location = "bedroom" property (for SleepMechanic.apply() to read)
    - alice --[type=location]--> bedroom edge (for VisibilityProjector to include bedroom)
    """
    kg.add_node("alice", node_type="agent", health=0.8)
    kg.add_node("bedroom", node_type="entity", noise_level=0.3)
    kg.set("alice", "location", "bedroom")
    kg.add_edge("alice", "bedroom", type="location")


# ---------------------------------------------------------------------------
# Test 1 + 2 + 3: sleep → continue → wake on noise
# ---------------------------------------------------------------------------


def test_sleep_then_continue_then_wake_on_noise(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """Full sleep → continue → noise threshold → wake cycle (D-18, D-08, D-10)."""
    _install_sleep_mechanic(tmp_universe)
    _setup_alice_in_bedroom(kg)

    # --- Step 1: 'sleep' action → LRA starts ---
    # Responses: classifier (Haiku) + observer (Sonnet) for the initial sleep tick
    engine = _make_engine(
        tmp_universe,
        kg,
        responses=[
            _CLASSIFY_SLEEP,
            "You settle into a deep sleep.",  # observer for initial sleep apply
        ],
    )
    result1 = engine.run_tick("sleep", actor="alice")
    assert result1.kind == "ok"

    # LRA set up correctly
    lra = kg.query("alice", "current_long_action")
    assert lra is not None
    assert lra["action_text"] == "sleeping"
    assert lra["turns_total"] == 8
    assert lra["turns_elapsed"] == 0
    assert kg.query("alice", "is_sleeping") is True
    # Thresholds include noise for bedroom
    assert {"property": "bedroom.noise_level", "op": ">", "value": 0.7} in lra["thresholds"]
    assert {"property": "alice.health", "op": "<", "value": 0.2} in lra["thresholds"]

    # --- Step 2: continuation tick — quiet bedroom, no threshold fires ---
    # No classifier call, no observer call (static template)
    engine2 = _make_engine(tmp_universe, kg, responses=[])
    result2 = engine2.run_tick(None, actor="alice")
    assert result2.kind == "ok"
    assert "Time passes" in (result2.observation or "")
    assert "sleeping" in (result2.observation or "")

    lra2 = kg.query("alice", "current_long_action")
    assert lra2["turns_elapsed"] == 1  # advanced

    # --- Step 3: bump noise → threshold fires → wake ---
    kg.set("bedroom", "noise_level", 0.9)
    engine3 = _make_engine(tmp_universe, kg, responses=[_WAKE_NOISE])
    result3 = engine3.run_tick(None, actor="alice")
    assert result3.kind == "ok"
    assert "jolted awake" in (result3.observation or "") or "loud noise" in (
        result3.observation or ""
    )

    # LRA cleared
    lra3 = kg.query("alice", "current_long_action")
    assert lra3 is None


# ---------------------------------------------------------------------------
# Test: tick summary contains long_running_action field (D-17)
# ---------------------------------------------------------------------------


def test_sleep_continuation_tick_summary_has_long_running_action_field(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """Tick summary JSON must have long_running_action.active=True during continuation."""
    _install_sleep_mechanic(tmp_universe)
    _setup_alice_in_bedroom(kg)

    # Start sleep
    engine = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_SLEEP, "You fall asleep."])
    engine.run_tick("sleep", actor="alice")

    # Continuation tick
    engine2 = _make_engine(tmp_universe, kg, responses=[])
    result = engine2.run_tick(None, actor="alice")

    tick_file = tmp_universe / "tick_summaries" / "ticks" / f"tick_{result.tick_id}.json"
    assert tick_file.exists()
    data = json.loads(tick_file.read_text())
    lra_field = data.get("long_running_action")
    assert lra_field is not None
    assert lra_field["active"] is True
    assert lra_field["turns_elapsed"] == 1
    assert lra_field["turns_total"] == 8
    assert lra_field["interrupted"] is False


# ---------------------------------------------------------------------------
# Test: 8-tick completion
# ---------------------------------------------------------------------------


def test_sleep_completes_after_turns_total_ticks(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """After 8 continuation ticks, LRA completes and observer is called (D-18)."""
    _install_sleep_mechanic(tmp_universe)
    _setup_alice_in_bedroom(kg)

    # Start sleep
    engine = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_SLEEP, "You drift off."])
    engine.run_tick("sleep", actor="alice")

    # Run 7 continuation ticks (quiet bedroom)
    for i in range(7):
        e = _make_engine(tmp_universe, kg, responses=[])
        result = e.run_tick(None, actor="alice")
        assert result.kind == "ok"
        lra = kg.query("alice", "current_long_action")
        assert lra is not None, f"LRA cleared prematurely at iteration {i}"
        assert lra["turns_elapsed"] == i + 1

    # 8th continuation tick → completion
    engine_final = _make_engine(tmp_universe, kg, responses=[_WAKE_COMPLETED])
    result_final = engine_final.run_tick(None, actor="alice")
    assert result_final.kind == "ok"
    # LRA must be cleared
    lra_final = kg.query("alice", "current_long_action")
    assert lra_final is None


# ---------------------------------------------------------------------------
# Test: D-11 implicit cancellation — new action text clears LRA
# ---------------------------------------------------------------------------


def test_sleep_cancelled_by_new_agent_action(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """New action_text while sleeping → LRA cleared, normal pipeline runs (D-11)."""
    _install_sleep_mechanic(tmp_universe)
    _setup_alice_in_bedroom(kg)

    # Start sleep
    engine = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_SLEEP, "You fall asleep."])
    engine.run_tick("sleep", actor="alice")
    assert kg.query("alice", "current_long_action") is not None

    # Two continuation ticks
    for _ in range(2):
        e = _make_engine(tmp_universe, kg, responses=[])
        e.run_tick(None, actor="alice")

    lra_mid = kg.query("alice", "current_long_action")
    assert lra_mid is not None
    assert lra_mid["turns_elapsed"] == 2

    # New action — no-match so just a refuse, but LRA is cancelled
    engine_cancel = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_NO_MATCH])
    result_cancel = engine_cancel.run_tick("look around", actor="alice")

    # LRA must be cleared before pipeline ran
    lra_after = kg.query("alice", "current_long_action")
    assert lra_after is None
    # Normal pipeline ran (refused or ok — not continuation)
    assert result_cancel.kind in ("refused", "ok", "yielded")


# ---------------------------------------------------------------------------
# Test: classifier NOT called on continuation ticks
# ---------------------------------------------------------------------------


def test_sleep_continuation_does_not_call_classifier(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """run_tick(None) during sleep must not trigger classifier calls (D-07).

    Verification: each continuation client has an empty response list. If the
    classifier (Haiku) were called, _MessagesProxy.create() would raise
    RuntimeError("MockAnthropicClient ran out of responses") — so reaching the
    assertion without errors proves no classifier call happened.
    """
    _install_sleep_mechanic(tmp_universe)
    _setup_alice_in_bedroom(kg)

    # Start sleep (needs classifier + observer)
    engine = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_SLEEP, "You sleep."])
    engine.run_tick("sleep", actor="alice")

    # 3 continuation ticks with empty clients — any classifier call would raise
    for _ in range(3):
        client = MockAnthropicClient([])
        e = SimulationEngine(tmp_universe, graph=kg, anthropic_client=client)
        e.run_tick(None, actor="alice")
        # If we reach here, no LLM call was made
        assert client.messages.calls == [], "Classifier was called on continuation tick"


# ---------------------------------------------------------------------------
# Test: attention_state suppresses visual_detail from projected_state
# ---------------------------------------------------------------------------


def test_sleep_attention_state_suppresses_visual_detail(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """During sleep, visual_detail must be absent from projected_state (D-12)."""
    _install_sleep_mechanic(tmp_universe)
    kg.add_node("alice", node_type="agent", health=0.8)
    kg.add_node("bedroom", node_type="entity", noise_level=0.3, visual_detail="ornate tapestry")
    kg.set("alice", "location", "bedroom")

    # Start sleep
    engine = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_SLEEP, "You sleep."])
    engine.run_tick("sleep", actor="alice")

    # Continuation tick — check projected_state
    engine2 = _make_engine(tmp_universe, kg, responses=[])
    result = engine2.run_tick(None, actor="alice")
    assert result.kind == "ok"

    proj = result.projected_state or {}
    bedroom_props = proj.get("bedroom", {}).get("properties", {})
    assert "visual_detail" not in bedroom_props, (
        f"visual_detail should be suppressed during sleep, got: {bedroom_props}"
    )
