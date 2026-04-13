"""Tests for PlaytestRunner LRA integration (Task 3, Plan 07-04).

Verifies that when has_active_long_action() returns True, the runner:
- Skips agent.run_turn() (saves LLM call — Pitfall 2)
- Calls engine.run_tick(None, actor) instead of run_tick(text, actor)
- Stores "[long_running_continuation]" in memory (keeps rolling window intact)
- Uses the marker for TurnRecord and scoring

D-07: runner transparent to LRA; engine generates synthetic tick internally.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


def _fake_ok_result(tick_id: str = "tick_1") -> object:
    """Build a minimal ok TickResult."""
    from token_world.engine.engine import TickResult

    return TickResult.ok(
        tick_id=tick_id,
        observation="Time passes.",
        trace=None,
        projected_state={},
    )


class FakeEngine:
    """Engine fake with controllable has_active_long_action and run_tick recording."""

    def __init__(self, results: list, has_lra_sequence: list[bool]) -> None:
        self._results = list(results)
        self._has_lra_sequence = list(has_lra_sequence)
        self.run_tick_calls: list[tuple] = []

    def has_active_long_action(self, actor: str) -> bool:
        if self._has_lra_sequence:
            return self._has_lra_sequence.pop(0)
        return False

    def run_tick(self, action_text: str | None, *, actor: str) -> object:
        self.run_tick_calls.append((action_text, actor))
        return self._results.pop(0)


class FakeAgent:
    """Agent fake that records run_turn() calls."""

    def __init__(self, action: str = "look around") -> None:
        self.action = action
        self.run_turn_call_count = 0
        self._client = MagicMock()

    def run_turn(self) -> str:
        self.run_turn_call_count += 1
        return self.action


class FakeMemory:
    """Memory fake that records store_turn calls."""

    def __init__(self) -> None:
        self.store_turn_calls: list[tuple] = []

    def store_turn(self, agent_id, session_id, turn_num, action_text, observation, tick_id) -> None:
        self.store_turn_calls.append(
            (agent_id, session_id, turn_num, action_text, observation, tick_id)
        )

    def maybe_compact_summary(self, session_id, client) -> None:
        pass


def _build_runner(engine=None, agent=None, memory=None, tmp_path: Path | None = None):
    from token_world.playtest import PlaytestRunner

    if tmp_path is None:
        # Provide a minimal fallback universe dir for tests that need it
        import tempfile

        tmp_path = Path(tempfile.mkdtemp())
        (tmp_path / "mechanics").mkdir(exist_ok=True)
        (tmp_path / "diagnostics").mkdir(exist_ok=True)
        (tmp_path / "tick_summaries").mkdir(exist_ok=True)
        (tmp_path / "universe.yaml").write_text(
            "universe_seed: 1\nengine:\n  max_chain_depth: 5\n  classifier_min_confidence: 0.6\n"
        )
        (tmp_path / "conservation.yaml").write_text("conserved_properties: []\n")

    runner = PlaytestRunner(
        engine=engine or FakeEngine([_fake_ok_result()], []),
        agent=agent or FakeAgent(),
        memory=memory or FakeMemory(),
        agent_id="alice",
        session_id="session_1",
        harness_factory=lambda ud: MagicMock(),
        progress_fn=lambda s: None,
    )
    return runner, tmp_path


# ---------------------------------------------------------------------------
# Test: LRA active → skip agent.run_turn, call run_tick(None)
# ---------------------------------------------------------------------------


def test_runner_skips_agent_run_turn_when_lra_active(tmp_path: Path) -> None:
    """When has_active_long_action returns True, agent.run_turn must NOT be called."""
    engine = FakeEngine(
        results=[_fake_ok_result("tick_1")],
        has_lra_sequence=[True],
    )
    agent = FakeAgent()
    runner, _ = _build_runner(engine=engine, agent=agent, tmp_path=tmp_path)

    runner.run(tmp_path, turns=1, no_operator=True)

    assert agent.run_turn_call_count == 0
    # Engine received action_text=None
    assert engine.run_tick_calls[0][0] is None


def test_runner_calls_run_tick_with_none_when_lra_active(tmp_path: Path) -> None:
    engine = FakeEngine(
        results=[_fake_ok_result("tick_1")],
        has_lra_sequence=[True],
    )
    runner, _ = _build_runner(engine=engine, tmp_path=tmp_path)

    runner.run(tmp_path, turns=1, no_operator=True)

    action_text, actor = engine.run_tick_calls[0]
    assert action_text is None
    assert actor == "alice"


def test_runner_uses_marker_for_memory_when_lra_active(tmp_path: Path) -> None:
    """memory.store_turn must receive '[long_running_continuation]' for LRA turns."""
    engine = FakeEngine(
        results=[_fake_ok_result("tick_1")],
        has_lra_sequence=[True],
    )
    memory = FakeMemory()
    runner, _ = _build_runner(engine=engine, memory=memory, tmp_path=tmp_path)

    runner.run(tmp_path, turns=1, no_operator=True)

    assert len(memory.store_turn_calls) == 1
    stored_action = memory.store_turn_calls[0][3]  # index 3 = action_text
    assert stored_action == "[long_running_continuation]"


# ---------------------------------------------------------------------------
# Test: No LRA → agent.run_turn is called normally (regression)
# ---------------------------------------------------------------------------


def test_runner_calls_agent_normally_when_no_lra(tmp_path: Path) -> None:
    """Regression: has_active_long_action=False → agent.run_turn called as before."""
    engine = FakeEngine(
        results=[_fake_ok_result("tick_1")],
        has_lra_sequence=[False],
    )
    agent = FakeAgent(action="look around")
    runner, _ = _build_runner(engine=engine, agent=agent, tmp_path=tmp_path)

    runner.run(tmp_path, turns=1, no_operator=True)

    assert agent.run_turn_call_count == 1
    action_text, actor = engine.run_tick_calls[0]
    assert action_text == "look around"


# ---------------------------------------------------------------------------
# Test: mixed LRA and normal turns
# ---------------------------------------------------------------------------


def test_runner_mixed_lra_and_normal_turns(tmp_path: Path) -> None:
    """4 turns: [normal, LRA, LRA, normal] — agent.run_turn called 2x."""
    engine = FakeEngine(
        results=[_fake_ok_result(f"tick_{i}") for i in range(4)],
        has_lra_sequence=[False, True, True, False],
    )
    agent = FakeAgent(action="go north")
    memory = FakeMemory()
    runner, _ = _build_runner(engine=engine, agent=agent, memory=memory, tmp_path=tmp_path)

    runner.run(tmp_path, turns=4, no_operator=True)

    assert agent.run_turn_call_count == 2
    # Verify run_tick call action_text sequence
    calls = [c[0] for c in engine.run_tick_calls]
    assert calls == ["go north", None, None, "go north"]


# ---------------------------------------------------------------------------
# Test: scenario action skipped when LRA active (v1 LRA wins)
# ---------------------------------------------------------------------------


def test_runner_scenario_skipped_when_lra_active(tmp_path: Path) -> None:
    """v1 behavior: when LRA is active, scenario action is skipped for that turn.

    Turn 0: no LRA → scenario action used.
    Turn 1: LRA active → None sent to engine (scenario action ignored).
    """
    from token_world.playtest.scenarios import Scenario

    # Build a 2-turn scenario
    scenario_path = tmp_path / "scenario.yaml"
    import yaml

    scenario_path.write_text(
        yaml.dump(
            {
                "name": "test",
                "description": "test",
                "adversarial_rate": 0.0,
                "seed": 0,
                "turns": [{"action": "open door"}, {"action": "go north"}],
            }
        )
    )
    scenario = Scenario.load(scenario_path)

    engine = FakeEngine(
        results=[_fake_ok_result(f"tick_{i}") for i in range(2)],
        has_lra_sequence=[False, True],
    )
    runner, _ = _build_runner(engine=engine, tmp_path=tmp_path)

    runner.run(tmp_path, turns=2, scenario=scenario, no_operator=True)

    calls = [c[0] for c in engine.run_tick_calls]
    # Turn 0: no LRA → scenario action "open door"
    assert calls[0] == "open door"
    # Turn 1: LRA → None (scenario "go north" skipped)
    assert calls[1] is None


# ---------------------------------------------------------------------------
# Test: TurnRecord captures marker for LRA turns
# ---------------------------------------------------------------------------


def test_runner_records_continuation_in_turn_record(tmp_path: Path) -> None:
    """TurnRecord for an LRA turn must have action_text='[long_running_continuation]'."""
    engine = FakeEngine(
        results=[_fake_ok_result("tick_1")],
        has_lra_sequence=[True],
    )
    runner, _ = _build_runner(engine=engine, tmp_path=tmp_path)

    report_path = runner.run(tmp_path, turns=1, no_operator=True)

    import json

    data = json.loads(report_path.read_text())
    turn = data["turns"][0]
    assert turn["action_text"] == "[long_running_continuation]"


# ---------------------------------------------------------------------------
# Test: scoring still runs for continuation turns
# ---------------------------------------------------------------------------


def test_runner_scoring_includes_continuation_turn(tmp_path: Path) -> None:
    """aggregate_scores is computed even when all turns are LRA continuations."""
    engine = FakeEngine(
        results=[_fake_ok_result(f"tick_{i}") for i in range(3)],
        has_lra_sequence=[True, True, True],
    )
    runner, _ = _build_runner(engine=engine, tmp_path=tmp_path)

    report_path = runner.run(tmp_path, turns=3, no_operator=True)

    import json

    data = json.loads(report_path.read_text())
    assert len(data["turns"]) == 3
    assert "aggregate_scores" in data
    # AggregateScores has composite, not turn_count; verify it's populated
    assert "composite" in data["aggregate_scores"]
