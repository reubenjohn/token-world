"""Tests for 5 canonical adversarial scenario YAML files (Task 2, AUTO-05)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Test 8: nonsense_barrage.yaml loads correctly
# ---------------------------------------------------------------------------


def test_nonsense_barrage_scenario_loads() -> None:
    """Test 8 (RED): nonsense_barrage.yaml loads; 20 turns all inject:nonsense; seed=100."""
    from token_world.playtest import Scenario

    path = Path("scenarios/adversarial/nonsense_barrage.yaml")
    scenario = Scenario.load(path)

    assert scenario.name == "nonsense_barrage"
    assert scenario.seed == 100
    assert len(scenario.turns) == 20

    for i, turn in enumerate(scenario.turns):
        assert "inject" in turn, f"Turn {i} is not an inject turn: {turn}"
        assert turn["inject"] == "nonsense", (
            f"Turn {i} inject type is {turn['inject']!r}, expected 'nonsense'"
        )


# ---------------------------------------------------------------------------
# Test 9: rule_violation.yaml loads correctly
# ---------------------------------------------------------------------------


def test_rule_violation_scenario_loads() -> None:
    """Test 9 (RED): rule_violation.yaml loads; 15 turns; at least one inject:adversarial."""
    from token_world.playtest import Scenario

    path = Path("scenarios/adversarial/rule_violation.yaml")
    scenario = Scenario.load(path)

    assert scenario.name == "rule_violation"
    assert scenario.seed == 101
    assert len(scenario.turns) == 15

    adversarial_injects = [t for t in scenario.turns if t.get("inject") == "adversarial"]
    assert len(adversarial_injects) >= 1, (
        "rule_violation must contain at least one inject:adversarial"
    )


# ---------------------------------------------------------------------------
# Test 10: repetition_loop.yaml loads correctly
# ---------------------------------------------------------------------------


def test_repetition_loop_scenario_loads() -> None:
    """Test 10 (RED): repetition_loop.yaml loads; 10+ turns with inject:repeat_last."""
    from token_world.playtest import Scenario

    path = Path("scenarios/adversarial/repetition_loop.yaml")
    scenario = Scenario.load(path)

    assert scenario.name == "repetition_loop"
    assert scenario.seed == 102
    assert len(scenario.turns) >= 10

    repeat_turns = [t for t in scenario.turns if t.get("inject") == "repeat_last"]
    assert len(repeat_turns) >= 1, "repetition_loop must contain at least one inject:repeat_last"


# ---------------------------------------------------------------------------
# Test 11: edge_case_stress.yaml loads correctly
# ---------------------------------------------------------------------------


def test_edge_case_stress_scenario_loads() -> None:
    """Test 11 (RED): edge_case_stress.yaml loads; 20 turns of inject:edge_case."""
    from token_world.playtest import Scenario

    path = Path("scenarios/adversarial/edge_case_stress.yaml")
    scenario = Scenario.load(path)

    assert scenario.name == "edge_case_stress"
    assert scenario.seed == 103
    assert len(scenario.turns) == 20

    edge_turns = [t for t in scenario.turns if t.get("inject") == "edge_case"]
    assert len(edge_turns) == 20, f"Expected 20 edge_case turns, got {len(edge_turns)}"


# ---------------------------------------------------------------------------
# Test 12: mixed_chaos.yaml loads correctly
# ---------------------------------------------------------------------------


def test_mixed_chaos_scenario_loads() -> None:
    """Test 12 (RED): mixed_chaos.yaml loads; 30 turns; adversarial_rate 0.2-0.4."""
    from token_world.playtest import Scenario

    path = Path("scenarios/adversarial/mixed_chaos.yaml")
    scenario = Scenario.load(path)

    assert scenario.name == "mixed_chaos"
    assert scenario.seed == 104
    assert len(scenario.turns) == 30
    assert 0.2 <= scenario.adversarial_rate <= 0.4, (
        f"adversarial_rate {scenario.adversarial_rate} not in [0.2, 0.4]"
    )

    # Must contain at least one of each inject type
    inject_types = {t["inject"] for t in scenario.turns if "inject" in t}
    assert "adversarial" in inject_types, "mixed_chaos must contain inject:adversarial"
    assert "nonsense" in inject_types, "mixed_chaos must contain inject:nonsense"


# ---------------------------------------------------------------------------
# Test 13: mixed_chaos drives runner end-to-end (integration)
# ---------------------------------------------------------------------------


def _make_varied_tick_results(count: int):
    """Build a list of TickResult mocks: mostly ok, occasional yielded/refused."""
    from token_world.engine.engine import TickResult
    from token_world.graph.models import Mutation
    from token_world.mechanic.trace import CheckResult, ExecutionTrace, TraceNode

    results = []
    for i in range(count):
        if i % 7 == 0 and i > 0:
            # yielded turn — but for simplicity treat as ok (runner re-runs on yield)
            # Use ok so we don't need harness mock complexity
            pass
        trace = ExecutionTrace(
            root=TraceNode(
                mechanic_id="mock",
                actor="agent",
                target="agent",
                check_result=CheckResult(passed=True, reasons=[]),
                mutations=[
                    Mutation(
                        type="set_property",
                        target="item",
                        property="loc",
                        old_value=None,
                        new_value="room",
                    )
                ],
            ),
            total_mechanics_executed=1,
            max_depth_reached=1,
            truncated=False,
        )
        results.append(
            TickResult.ok(
                tick_id=f"tick_{i}",
                observation=f"Turn {i} observation.",
                trace=trace,
                projected_state={"room": {"properties": {}}},
            )
        )
    return results


def test_mixed_chaos_scenario_drives_runner_end_to_end(tmp_path: Path) -> None:
    """Test 13 (RED): mixed_chaos.yaml drives PlaytestRunner 30 turns; no crash; 30 TurnRecords."""
    import json

    from token_world.playtest import PlaytestRunner, Scenario

    path = Path("scenarios/adversarial/mixed_chaos.yaml")
    scenario = Scenario.load(path)

    tick_results = _make_varied_tick_results(30)

    engine = MagicMock()
    engine.run_tick.side_effect = tick_results

    agent = MagicMock()
    agent.run_turn.return_value = "look around"
    agent.agent_id = "test_agent"

    memory = MagicMock()
    memory.store_turn.return_value = None

    runner = PlaytestRunner(
        engine=engine,
        agent=agent,
        memory=memory,
        agent_id="test_agent",
        session_id="test_session",
    )

    report_path = runner.run(tmp_path, turns=30, scenario=scenario, no_operator=True)

    data = json.loads(report_path.read_text())
    assert len(data["turns"]) == 30, f"Expected 30 turns in report, got {len(data['turns'])}"

    for turn_record in data["turns"]:
        assert "turn_number" in turn_record
        assert "action_text" in turn_record
        assert "kind" in turn_record


# ---------------------------------------------------------------------------
# Test 14: all adversarial scenarios use seeds 100-110
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scenario_file",
    [
        "scenarios/adversarial/nonsense_barrage.yaml",
        "scenarios/adversarial/rule_violation.yaml",
        "scenarios/adversarial/repetition_loop.yaml",
        "scenarios/adversarial/edge_case_stress.yaml",
        "scenarios/adversarial/mixed_chaos.yaml",
    ],
)
def test_all_adversarial_scenarios_use_small_seeds(scenario_file: str) -> None:
    """Test 14 (RED): Each adversarial scenario uses a seed in [100, 110]."""
    from token_world.playtest import Scenario

    scenario = Scenario.load(Path(scenario_file))
    assert 100 <= scenario.seed <= 110, f"{scenario_file}: seed {scenario.seed} not in [100, 110]"


# ---------------------------------------------------------------------------
# Test 15: adversarial README mentions all five scenario names
# ---------------------------------------------------------------------------


def test_adversarial_readme_lists_all_five_scenarios() -> None:
    """Test 15 (RED): scenarios/adversarial/README.md mentions each scenario name."""
    readme = Path("scenarios/adversarial/README.md")
    assert readme.exists(), "scenarios/adversarial/README.md must exist"

    content = readme.read_text(encoding="utf-8")
    expected_names = [
        "nonsense_barrage",
        "rule_violation",
        "repetition_loop",
        "edge_case_stress",
        "mixed_chaos",
    ]
    for name in expected_names:
        assert name in content, f"README.md missing scenario name: {name!r}"
