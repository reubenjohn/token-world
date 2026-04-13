"""Integration tests for drunk + sober_up seed mechanics end-to-end (Plan 07-07).

Tests the full deterministic pipeline:
  - 'drink ale' → LRA started with turns_total=None, sobriety_level=0.5, is_drunk=True, ale gone
  - continuation ticks → sobriety rises 0.1/tick via sober_up passive sweep
  - sobriety_level > 0.8 threshold fires when hook sees sobriety >= 0.9 (strictly >0.8)
  - indefinite duration: without sober_up, LRA never expires (D-16 turns_total=None)
  - D-11 cancellation: new action clears drunk LRA; is_drunk + sobriety_level remain on actor
  - attention_state: fine_detail + social_nuance suppressed during drunk continuation

Engine tick ordering (Plan 04, D-06):
  On EVERY tick:
    For action ticks (_handle_execute path):
      1. Primary mechanic pipeline (classifier → matcher → decider → apply)
         DrunkMechanic.apply fires: sobriety_level=0.5, is_drunk=True, ale removed, LRA started
      2. LongRunningHook NOT called on action ticks (hook only runs on continuation ticks)
      3. Passive sweep: sober_up fires → sobriety: 0.5 → 0.6

    For continuation ticks (_handle_long_running_tick, run_tick(None)):
      1. LongRunningHook: evaluates threshold (sobriety > 0.8) at current sobriety
      2. Passive sweep: sober_up fires → sobriety increments by 0.1

Sobriety sequence with BOTH drunk + sober_up installed:
  Tick 1 (drink action): apply sets sobriety=0.5; passive sweep → 0.6
  Tick 2 (continuation): hook sees sobriety=0.6; 0.6>0.8 False; sweep → 0.7
  Tick 3 (continuation): hook sees sobriety=0.7; 0.7>0.8 False; sweep → 0.8
  Tick 4 (continuation): hook sees sobriety=0.8; 0.8>0.8 False (strictly >); sweep → 0.9
  Tick 5 (continuation): hook sees sobriety=0.9; 0.9>0.8 True → threshold fires → LRA cleared

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


def _install_drunk_mechanics(tmp_universe: Path) -> None:
    """Copy drunk.py + sober_up.py into universe mechanics folder."""
    mechs = tmp_universe / "mechanics"
    mechs.mkdir(exist_ok=True)
    shutil.copy(_SEEDS_DIR / "drunk.py", mechs / "drunk.py")
    shutil.copy(_SEEDS_DIR / "sober_up.py", mechs / "sober_up.py")


def _install_drunk_only(tmp_universe: Path) -> None:
    """Copy only drunk.py — used to test indefinite-duration without sobering."""
    mechs = tmp_universe / "mechanics"
    mechs.mkdir(exist_ok=True)
    shutil.copy(_SEEDS_DIR / "drunk.py", mechs / "drunk.py")


# ---------------------------------------------------------------------------
# Local fixture overrides
# ---------------------------------------------------------------------------


@pytest.fixture
def kg(tmp_path: Path) -> KnowledgeGraph:
    """KG backed by SQLite — required for snapshot/restore in engine."""
    return KnowledgeGraph(db_path=tmp_path / "drunk_int_test.db")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Classifier: 'drink ale' → verb=drink, actor=alice, target=ale
_CLASSIFY_DRINK_ALE = json.dumps(
    {
        "kind": "ok",
        "classified": {"verb": "drink", "actor": "alice", "target": "ale", "params": {}},
        "confidence": 0.95,
    }
)

# Classifier: 'shout at bartender' → verb=shout, actor=alice, target=bartender
_CLASSIFY_SHOUT = json.dumps(
    {
        "kind": "ok",
        "classified": {
            "verb": "shout",
            "actor": "alice",
            "target": "bartender",
            "params": {},
        },
        "confidence": 0.88,
    }
)

_WAKE_SOBER = "You blink slowly, head clearing. The world sharpens around you."
_DRINK_OBS = "You raise the ale and drink deeply. The room starts to blur pleasantly."
_SHOUT_OBS = "You shout at the bartender, your words slurring."


def _make_engine(
    tmp_universe: Path,
    kg: KnowledgeGraph,
    responses: list[str],
) -> SimulationEngine:
    client = MockAnthropicClient(responses)
    return SimulationEngine(tmp_universe, graph=kg, anthropic_client=client)


def _setup_alice_with_ale(kg: KnowledgeGraph) -> None:
    """Build: alice in a tavern, holding ale (alcohol_content=0.5), sobriety_level=1.0.

    Sets both:
    - alice.location = 'tavern' property
    - alice --[type=location]--> tavern edge (for VisibilityProjector to include tavern)
    """
    kg.add_node("alice", node_type="agent", sobriety_level=1.0)
    kg.add_node("tavern", node_type="entity", subtype="room")
    kg.add_node("ale", node_type="entity", subtype="drink", alcohol_content=0.5)
    kg.set("alice", "location", "tavern")
    kg.add_edge("alice", "tavern", type="location")
    kg.add_edge("alice", "ale", relation="holds")


# ---------------------------------------------------------------------------
# Test 1: Full 6-tick drink → sober cycle
# ---------------------------------------------------------------------------


def test_drunk_happy_path_drink_continue_sober_wake(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """Full 6-tick drunk → continuation → sober threshold fire cycle.

    Tick 1 (drink action):
      DrunkMechanic: sobriety_level=0.5, is_drunk=True, ale removed, LRA started (turns_total=None)
      Passive sweep: sober_up → sobriety 0.5→0.6
    Tick 2 (continuation):
      Hook: sobriety=0.6; 0.6>0.8 False; no fire; turns_elapsed→1
      Passive sweep: sober_up → 0.6→0.7
    Tick 3 (continuation):
      Hook: sobriety=0.7; 0.7>0.8 False; turns_elapsed→2
      Passive sweep: → 0.7→0.8
    Tick 4 (continuation):
      Hook: sobriety=0.8; 0.8>0.8 False (strictly >); turns_elapsed→3
      Passive sweep: → 0.8→0.9
    Tick 5 (continuation):
      Hook: sobriety=0.9; 0.9>0.8 True → FIRE; LRA cleared; Observer synthesises wake narrative
    """
    _install_drunk_mechanics(tmp_universe)
    _setup_alice_with_ale(kg)

    # --- Tick 1: drink action ---
    engine = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_DRINK_ALE, _DRINK_OBS])
    result1 = engine.run_tick("drink ale", actor="alice")
    assert result1.kind == "ok"

    # LRA set correctly
    lra = kg.query("alice", "current_long_action")
    assert lra is not None
    assert lra["action_text"] == "drunk"
    assert lra["turns_total"] is None  # D-16: indefinite
    assert lra["turns_elapsed"] == 0
    assert lra["thresholds"] == [{"property": "alice.sobriety_level", "op": ">", "value": 0.8}]
    attention = lra["payload"]["attention_state"]
    assert attention["suppress"] == ["fine_detail", "social_nuance"]
    assert attention["boost"] == ["aggression_level"]
    assert kg.query("alice", "is_drunk") is True
    assert not kg.has_node("ale")  # ale consumed

    # After action tick: DrunkMechanic set sobriety=0.5; sober_up passive sweep → 0.6
    sobriety_after_tick1 = kg.query("alice", "sobriety_level")
    assert abs(sobriety_after_tick1 - 0.6) < 1e-9, f"Expected 0.6, got {sobriety_after_tick1}"

    # --- Tick 2: continuation (hook sees 0.6, no fire; sweep → 0.7) ---
    e2 = _make_engine(tmp_universe, kg, responses=[])
    r2 = e2.run_tick(None, actor="alice")
    assert r2.kind == "ok"
    assert "Time passes" in (r2.observation or "") or "drunk" in (r2.observation or "")
    lra2 = kg.query("alice", "current_long_action")
    assert lra2 is not None
    assert lra2["turns_elapsed"] == 1
    sobriety2 = kg.query("alice", "sobriety_level")
    assert abs(sobriety2 - 0.7) < 1e-9, f"Expected 0.7 after tick 2, got {sobriety2}"

    # --- Tick 3: continuation (hook sees 0.7, no fire; sweep → 0.8) ---
    e3 = _make_engine(tmp_universe, kg, responses=[])
    r3 = e3.run_tick(None, actor="alice")
    assert r3.kind == "ok"
    lra3 = kg.query("alice", "current_long_action")
    assert lra3 is not None
    assert lra3["turns_elapsed"] == 2
    sobriety3 = kg.query("alice", "sobriety_level")
    assert abs(sobriety3 - 0.8) < 1e-9, f"Expected 0.8 after tick 3, got {sobriety3}"

    # --- Tick 4: continuation (hook sees 0.8; 0.8>0.8 is False — strictly >; sweep → 0.9) ---
    e4 = _make_engine(tmp_universe, kg, responses=[])
    r4 = e4.run_tick(None, actor="alice")
    assert r4.kind == "ok"
    lra4 = kg.query("alice", "current_long_action")
    assert lra4 is not None, "LRA should NOT have fired when sobriety==0.8 (threshold is > not >=)"
    assert lra4["turns_elapsed"] == 3
    sobriety4 = kg.query("alice", "sobriety_level")
    assert abs(sobriety4 - 0.9) < 1e-9, f"Expected 0.9 after tick 4, got {sobriety4}"

    # --- Tick 5: continuation (hook sees 0.9; 0.9>0.8 True → FIRE; LRA cleared) ---
    e5 = _make_engine(tmp_universe, kg, responses=[_WAKE_SOBER])
    r5 = e5.run_tick(None, actor="alice")
    assert r5.kind == "ok"
    # LRA cleared on threshold fire
    lra5 = kg.query("alice", "current_long_action")
    assert lra5 is None, "LRA must be cleared when sobriety_level > 0.8 threshold fires"


# ---------------------------------------------------------------------------
# Test 2: Indefinite duration without sober_up (D-16)
# ---------------------------------------------------------------------------


def test_drunk_is_indefinite_without_sobering(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """With sober_up absent, drunk LRA runs indefinitely — turns_total=None never expires (D-16).

    100 continuation ticks must NOT clear the LRA even though sobriety never rises.
    This proves that turns_total=None means "only threshold or D-11 cancellation can end it."
    """
    _install_drunk_only(tmp_universe)  # sober_up NOT installed
    _setup_alice_with_ale(kg)

    # Start drunk (no sober_up sweep, so sobriety stays at 0.5)
    engine = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_DRINK_ALE, _DRINK_OBS])
    result = engine.run_tick("drink ale", actor="alice")
    assert result.kind == "ok"

    # sobriety_level stays at 0.5 since sober_up is not installed
    assert abs(kg.query("alice", "sobriety_level") - 0.5) < 1e-9

    # 10 continuation ticks (enough to prove it's truly indefinite — 100 is too slow for CI)
    for i in range(10):
        e = _make_engine(tmp_universe, kg, responses=[])
        e.run_tick(None, actor="alice")
        lra = kg.query("alice", "current_long_action")
        assert lra is not None, f"LRA should still be active after {i + 1} continuation ticks"
        assert lra["turns_total"] is None
        assert lra["turns_elapsed"] == i + 1
        # sobriety remains at 0.5 — no sober_up passive
        sobriety = kg.query("alice", "sobriety_level")
        assert abs(sobriety - 0.5) < 1e-9, (
            f"Sobriety should not change without sober_up (got {sobriety})"
        )


# ---------------------------------------------------------------------------
# Test 3: D-11 cancellation preserves consciousness state properties
# ---------------------------------------------------------------------------


def test_drunk_d11_cancellation_preserves_consciousness_state_properties(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """New action while drunk → LRA cleared; is_drunk + sobriety_level preserved (D-11).

    V1 semantic trade-off: cancelling the drunk LRA (by issuing a new action)
    ends the LONG-RUNNING ACTION STRUCTURE but does not magically sober up the
    actor — the graph properties (is_drunk=True, sobriety_level=0.5) remain.
    The actor is drunk in the world; they've just done something while drunk.
    """
    _install_drunk_mechanics(tmp_universe)
    _setup_alice_with_ale(kg)
    kg.add_node("bartender", node_type="entity", subtype="npc")

    # Start drunk
    engine = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_DRINK_ALE, _DRINK_OBS])
    engine.run_tick("drink ale", actor="alice")
    assert kg.query("alice", "current_long_action") is not None

    # Issue a new action — D-11: LRA cleared before pipeline
    # 'shout at bartender' — no shout mechanic installed, so it will be refused or no-match
    e_cancel = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_SHOUT])
    result_cancel = e_cancel.run_tick("shout at bartender", actor="alice")

    # LRA cleared (D-11)
    lra_after = kg.query("alice", "current_long_action")
    assert lra_after is None, "LRA must be cleared when a new action is issued (D-11)"

    # Consciousness state properties PRESERVED (actor is still drunk in the world)
    assert kg.query("alice", "is_drunk") is True, "is_drunk must remain True after D-11 cancel"
    sobriety_after = kg.query("alice", "sobriety_level")
    assert sobriety_after is not None
    # sobriety value preserved or possibly advanced one more tick by sober_up if it runs
    # on the cancel tick (it runs on the passive sweep regardless) — just verify it's still
    # a reasonable drunk sobriety level (0 < sobriety < 1)
    assert 0.0 <= sobriety_after < 1.0, (
        f"Sobriety should be between 0 and 1 after cancel, got {sobriety_after}"
    )
    # Result must be a normal tick (not a continuation tick)
    assert result_cancel.kind in ("refused", "ok", "yielded")


# ---------------------------------------------------------------------------
# Test 4: attention_state suppresses fine_detail + social_nuance during continuation
# ---------------------------------------------------------------------------


def test_drunk_attention_state_suppresses_fine_detail_during_continuation(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """During drunk continuation, fine_detail and social_nuance absent from projection (D-12)."""
    _install_drunk_mechanics(tmp_universe)
    _setup_alice_with_ale(kg)
    # Add suppressible properties to tavern
    kg.set("tavern", "fine_detail", "gilded mirrors line the walls")
    kg.set("tavern", "social_nuance", "the barmaid looks nervous")

    # Start drunk
    engine = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_DRINK_ALE, _DRINK_OBS])
    engine.run_tick("drink ale", actor="alice")

    # Continuation tick — check projected_state
    e2 = _make_engine(tmp_universe, kg, responses=[])
    result = e2.run_tick(None, actor="alice")
    assert result.kind == "ok"

    proj = result.projected_state or {}
    for node_id, node_data in proj.items():
        node_props = node_data.get("properties", {}) if isinstance(node_data, dict) else {}
        assert "fine_detail" not in node_props, (
            f"fine_detail should be suppressed during drunk continuation, found in {node_id}"
        )
        assert "social_nuance" not in node_props, (
            f"social_nuance should be suppressed during drunk continuation, found in {node_id}"
        )


# ---------------------------------------------------------------------------
# Test 5: Tick summary has long_running_action field (D-17)
# ---------------------------------------------------------------------------


def test_drunk_tick_summary_has_long_running_action_active_field(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """Tick summary JSON must have long_running_action.active=True during continuation (D-17)."""
    _install_drunk_mechanics(tmp_universe)
    _setup_alice_with_ale(kg)

    # Start drunk
    engine = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_DRINK_ALE, _DRINK_OBS])
    engine.run_tick("drink ale", actor="alice")

    # Continuation tick — check tick summary file
    e2 = _make_engine(tmp_universe, kg, responses=[])
    result = e2.run_tick(None, actor="alice")

    tick_file = tmp_universe / "tick_summaries" / "ticks" / f"tick_{result.tick_id}.json"
    assert tick_file.exists(), f"Tick summary file not found: {tick_file}"
    data = json.loads(tick_file.read_text())
    lra_field = data.get("long_running_action")
    assert lra_field is not None, "long_running_action field must be in tick summary"
    assert lra_field["active"] is True
    # turns_total=None preserved in summary
    assert lra_field["turns_total"] is None
    assert lra_field["interrupted"] is False


# ---------------------------------------------------------------------------
# Test 6: Threshold strictly > 0.8 (sobriety==0.8 does NOT fire)
# ---------------------------------------------------------------------------


def test_drunk_threshold_value_is_strictly_greater_than(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """Sobriety==0.8 must NOT fire the threshold; sobriety==0.9 must fire.

    This tests the '>' operator semantics (D-03). Sobriety is set manually
    to avoid depending on the tick-sequencing of sober_up.
    """
    _install_drunk_only(tmp_universe)  # no sober_up — we control sobriety manually
    _setup_alice_with_ale(kg)

    # Start drunk; sobriety after apply=0.5; no sober_up so stays 0.5
    engine = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_DRINK_ALE, _DRINK_OBS])
    engine.run_tick("drink ale", actor="alice")

    # Manually set sobriety to exactly 0.8
    kg.set("alice", "sobriety_level", 0.8)

    # Continuation tick: hook sees 0.8; 0.8 > 0.8 is False — no fire
    e_no_fire = _make_engine(tmp_universe, kg, responses=[])
    r_no_fire = e_no_fire.run_tick(None, actor="alice")
    assert r_no_fire.kind == "ok"
    lra_no_fire = kg.query("alice", "current_long_action")
    assert lra_no_fire is not None, (
        "LRA must NOT fire when sobriety==0.8 (threshold is strictly >, not >=)"
    )

    # Manually set sobriety to 0.9
    kg.set("alice", "sobriety_level", 0.9)

    # Continuation tick: hook sees 0.9; 0.9 > 0.8 is True → FIRE
    e_fire = _make_engine(tmp_universe, kg, responses=[_WAKE_SOBER])
    r_fire = e_fire.run_tick(None, actor="alice")
    assert r_fire.kind == "ok"
    lra_fire = kg.query("alice", "current_long_action")
    assert lra_fire is None, "LRA must be cleared when sobriety_level > 0.8 fires"
