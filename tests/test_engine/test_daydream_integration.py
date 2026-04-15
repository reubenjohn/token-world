"""Integration tests for the daydream seed mechanic end-to-end (quick 260413-syz).

Tests the full deterministic pipeline — daydream is the FOURTH composability
demonstrator alongside sleep (bounded physiological), autopilot_travel
(bounded movement), and drunk (indefinite chemical). Daydream exercises the
bounded cognitive case (turns_total=4, short shallow distraction).

Covered scenarios:
  - daydream action → LRA started (turns_total=4), is_daydreaming=True, thresholds set
  - 3 continuation ticks → turns_elapsed advances; 4th completes naturally → LRA cleared
  - Strict '>' threshold semantics: noise=0.3 no fire, noise=0.4 no fire, noise=0.5 fires
  - attention_state: ambient_sound + peripheral_vision suppressed from projected_state
  - D-11 implicit cancellation — new action text clears daydream LRA
  - Classifier is NOT called on continuation ticks (run_tick(None) path)

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


def _install_daydream_mechanic(tmp_universe: Path) -> None:
    """Copy daydream.py into the universe's mechanics folder so registry picks it up."""
    mechs = tmp_universe / "mechanics"
    mechs.mkdir(exist_ok=True)
    shutil.copy(_SEEDS_DIR / "daydream.py", mechs / "daydream.py")


# ---------------------------------------------------------------------------
# Local fixture overrides
# ---------------------------------------------------------------------------


@pytest.fixture
def kg(tmp_path: Path) -> KnowledgeGraph:
    """KG backed by SQLite — required for snapshot/restore in engine."""
    return KnowledgeGraph(db_path=tmp_path / "daydream_int_test.db")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Classifier response for 'daydream' action
_CLASSIFY_DAYDREAM = json.dumps(
    {
        "kind": "ok",
        "actions": [{"verb": "daydream", "actor": "alice", "target": "alice", "params": {}}],
        "confidence": 0.95,
    }
)

# Classifier response for low-confidence / no match (used in D-11 cancellation test)
_CLASSIFY_NO_MATCH = json.dumps({"kind": "no_viable_action", "reason": "no match"})

_SNAP_OUT_NOISE = "You snap out of your daydream as a loud noise pierces the room."
_DAYDREAM_END = "Your thoughts drift back to the present; you've been daydreaming."


def _make_engine(
    tmp_universe: Path,
    kg: KnowledgeGraph,
    responses: list[str],
) -> SimulationEngine:
    client = MockAnthropicClient(responses)
    return SimulationEngine(tmp_universe, graph=kg, anthropic_client=client)


def _setup_alice_in_study(kg: KnowledgeGraph, noise_level: float = 0.2) -> None:
    """Add alice and a study room to the graph.

    Sets both:
    - alice.location = "study" property (for DaydreamMechanic.apply() to read)
    - alice --[type=location]--> study edge (for VisibilityProjector to include study)

    Both are required for threshold evaluation to see the room during continuation
    ticks (STATE.md line 145 — VisibilityProjector follows type=location edges).
    """
    kg.add_node("alice", node_type="agent", health=0.8)
    kg.add_node("study", node_type="entity", noise_level=noise_level)
    kg.set("alice", "location", "study")
    kg.add_edge("alice", "study", type="location")


# ---------------------------------------------------------------------------
# Test 1: happy path — 4-tick completion cycle
# ---------------------------------------------------------------------------


def test_daydream_happy_path_completes_after_4_ticks(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """Full daydream → 3 continuations → 4th completes naturally → LRA cleared.

    Turn-by-turn (turns_total=4, quiet study noise=0.2):
      Tick 1 (daydream action): apply sets is_daydreaming=True; LRA started,
          turns_elapsed=0
      Tick 2 (continuation): turns_elapsed → 1
      Tick 3 (continuation): turns_elapsed → 2
      Tick 4 (continuation): turns_elapsed → 3
      Tick 5 (continuation): turns_elapsed reaches 4 == turns_total → complete,
          observer synthesises end narrative, LRA cleared
    """
    _install_daydream_mechanic(tmp_universe)
    _setup_alice_in_study(kg)

    # --- Tick 1: 'daydream' action → LRA starts ---
    engine = _make_engine(
        tmp_universe,
        kg,
        responses=[
            _CLASSIFY_DAYDREAM,
            "You let your mind wander.",  # observer for initial daydream apply
        ],
    )
    result1 = engine.run_tick("daydream", actor="alice")
    assert result1.kind == "ok"

    # LRA set up correctly
    lra = kg.query("alice", "current_long_action")
    assert lra is not None
    assert lra["action_text"] == "daydreaming"
    assert lra["turns_total"] == 4
    assert lra["turns_elapsed"] == 0
    assert kg.query("alice", "is_daydreaming") is True
    # Thresholds include noise for study and health for alice
    assert {"property": "study.noise_level", "op": ">", "value": 0.4} in lra["thresholds"]
    assert {"property": "alice.health", "op": "<", "value": 0.2} in lra["thresholds"]
    # attention_state recorded in payload
    attention = lra["payload"]["attention_state"]
    assert attention["suppress"] == ["ambient_sound", "peripheral_vision"]
    assert attention["boost"] == ["noise_level"]

    # --- Ticks 2, 3, 4: continuations — turns_elapsed → 1, 2, 3 ---
    for expected_elapsed in (1, 2, 3):
        e = _make_engine(tmp_universe, kg, responses=[])
        r = e.run_tick(None, actor="alice")
        assert r.kind == "ok"
        assert "Time passes" in (r.observation or "")
        assert "daydreaming" in (r.observation or "")
        lra_mid = kg.query("alice", "current_long_action")
        assert lra_mid is not None, f"LRA cleared prematurely at turns_elapsed={expected_elapsed}"
        assert lra_mid["turns_elapsed"] == expected_elapsed

    # --- Tick 5: 4th continuation → completion (turns_elapsed would reach 4) ---
    engine_final = _make_engine(tmp_universe, kg, responses=[_DAYDREAM_END])
    result_final = engine_final.run_tick(None, actor="alice")
    assert result_final.kind == "ok"

    # LRA must be cleared on completion
    lra_final = kg.query("alice", "current_long_action")
    assert lra_final is None, "LRA must be cleared when turns_elapsed reaches turns_total"
    # clear_on_end applied: is_daydreaming now False
    assert kg.query("alice", "is_daydreaming") is False


# ---------------------------------------------------------------------------
# Test 2: strict '>' threshold semantics at 0.4 (noise 0.3 no fire, 0.4 no fire, 0.5 fires)
# ---------------------------------------------------------------------------


def test_daydream_threshold_fires_at_noise_above_0_4_not_at_0_3(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """Threshold op='>', value=0.4: only strictly greater than 0.4 fires.

    noise=0.3 → 0.3 > 0.4 is False → no fire
    noise=0.4 → 0.4 > 0.4 is False → no fire (strictly >, not >=, matching drunk pattern)
    noise=0.5 → 0.5 > 0.4 is True → fires → LRA cleared
    """
    _install_daydream_mechanic(tmp_universe)
    _setup_alice_in_study(kg, noise_level=0.3)

    # Start daydream (noise=0.3)
    engine = _make_engine(
        tmp_universe, kg, responses=[_CLASSIFY_DAYDREAM, "You let your mind drift."]
    )
    engine.run_tick("daydream", actor="alice")
    assert kg.query("alice", "current_long_action") is not None

    # Continuation with noise=0.3 → 0.3 > 0.4 False → LRA still active
    e1 = _make_engine(tmp_universe, kg, responses=[])
    r1 = e1.run_tick(None, actor="alice")
    assert r1.kind == "ok"
    lra1 = kg.query("alice", "current_long_action")
    assert lra1 is not None, "LRA must NOT fire at noise=0.3 (0.3>0.4 is False)"

    # Bump noise to exactly 0.4 → 0.4 > 0.4 is False → still no fire
    kg.set("study", "noise_level", 0.4)
    e2 = _make_engine(tmp_universe, kg, responses=[])
    r2 = e2.run_tick(None, actor="alice")
    assert r2.kind == "ok"
    lra2 = kg.query("alice", "current_long_action")
    assert lra2 is not None, "LRA must NOT fire at noise=0.4 (threshold is strictly >, not >=)"

    # Bump noise to 0.5 → 0.5 > 0.4 is True → FIRE
    kg.set("study", "noise_level", 0.5)
    e3 = _make_engine(tmp_universe, kg, responses=[_SNAP_OUT_NOISE])
    r3 = e3.run_tick(None, actor="alice")
    assert r3.kind == "ok"
    lra3 = kg.query("alice", "current_long_action")
    assert lra3 is None, "LRA must be cleared when noise_level > 0.4 fires"


# ---------------------------------------------------------------------------
# Test 3: attention_state suppresses ambient_sound + peripheral_vision
# ---------------------------------------------------------------------------


def test_daydream_attention_state_suppresses_ambient_sound_during_continuation(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """During daydream continuation, ambient_sound and peripheral_vision absent from projection.

    attention_state suppress=["ambient_sound", "peripheral_vision"] (D-12 pattern).
    Both properties must be stripped from the projected study state.
    """
    _install_daydream_mechanic(tmp_universe)
    _setup_alice_in_study(kg)
    # Add suppressible properties to the study
    kg.set("study", "ambient_sound", "birds chirping")
    kg.set("study", "peripheral_vision", "moving shadows")

    # Start daydream
    engine = _make_engine(
        tmp_universe, kg, responses=[_CLASSIFY_DAYDREAM, "You drift off thinking."]
    )
    engine.run_tick("daydream", actor="alice")

    # Continuation tick — check projected_state
    e2 = _make_engine(tmp_universe, kg, responses=[])
    result = e2.run_tick(None, actor="alice")
    assert result.kind == "ok"

    proj = result.projected_state or {}
    study_props = proj.get("study", {}).get("properties", {})
    assert "ambient_sound" not in study_props, (
        f"ambient_sound should be suppressed during daydream, got: {study_props}"
    )
    assert "peripheral_vision" not in study_props, (
        f"peripheral_vision should be suppressed during daydream, got: {study_props}"
    )


# ---------------------------------------------------------------------------
# Test 4: D-11 implicit cancellation — new action text clears LRA
# ---------------------------------------------------------------------------


def test_daydream_cancelled_by_new_agent_action(tmp_universe: Path, kg: KnowledgeGraph) -> None:
    """New action_text while daydreaming → LRA cleared, normal pipeline runs (D-11)."""
    _install_daydream_mechanic(tmp_universe)
    _setup_alice_in_study(kg)

    # Start daydream
    engine = _make_engine(
        tmp_universe, kg, responses=[_CLASSIFY_DAYDREAM, "You begin to daydream."]
    )
    engine.run_tick("daydream", actor="alice")
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
    assert lra_after is None, "LRA must be cleared when a new action is issued (D-11)"
    # Normal pipeline ran (refused or ok — not continuation)
    assert result_cancel.kind in ("refused", "ok", "yielded")


# ---------------------------------------------------------------------------
# Test 5: classifier NOT called on continuation ticks
# ---------------------------------------------------------------------------


def test_daydream_continuation_does_not_call_classifier(
    tmp_universe: Path, kg: KnowledgeGraph
) -> None:
    """run_tick(None) during daydream must not trigger classifier calls (D-07).

    Verification: each continuation client has an empty response list. If the
    classifier (Haiku) were called, _MessagesProxy.create() would raise
    RuntimeError("MockAnthropicClient ran out of responses") — so reaching the
    assertion without errors proves no classifier call happened.
    """
    _install_daydream_mechanic(tmp_universe)
    _setup_alice_in_study(kg)

    # Start daydream (needs classifier + observer)
    engine = _make_engine(tmp_universe, kg, responses=[_CLASSIFY_DAYDREAM, "You daydream."])
    engine.run_tick("daydream", actor="alice")

    # 3 continuation ticks with empty clients — any classifier call would raise
    for _ in range(3):
        client = MockAnthropicClient([])
        e = SimulationEngine(tmp_universe, graph=kg, anthropic_client=client)
        e.run_tick(None, actor="alice")
        # If we reach here, no LLM call was made
        assert client.messages.calls == [], "Classifier was called on continuation tick"
