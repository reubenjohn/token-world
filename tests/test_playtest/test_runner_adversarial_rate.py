"""Tests for PlaytestRunner auto-injection via Scenario.adversarial_rate (IN-03).

Phase 6 IN-03: ``Scenario.adversarial_rate`` is parsed from YAML but the
runner previously ignored it. These tests lock in the wiring:

* rate 0.0 -> no injections ever (existing behavior preserved)
* rate 1.0 -> every agent-decide turn gets an injection
* rate 0.5 with a fixed seed -> deterministic subset of turns get injections
* ``adversarial_categories=["role_break"]`` -> only that category is sampled
* rate > 0 but no entries in the filtered category -> graceful no-op + warning
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from unittest.mock import MagicMock

from token_world.playtest import PlaytestRunner, Scenario
from token_world.playtest.adversarial import AdversarialBank

# ---------------------------------------------------------------------------
# Shared helpers (mirrors test_runner.py for consistency)
# ---------------------------------------------------------------------------


def _fake_ok_result(tick_id: str = "tick_1") -> object:
    """Build a minimal ok TickResult."""
    from token_world.engine.engine import TickResult
    from token_world.graph.models import Mutation
    from token_world.mechanic.trace import CheckResult, ExecutionTrace, TraceNode

    trace = ExecutionTrace(
        root=TraceNode(
            mechanic_id="test",
            actor="agent",
            target="agent",
            check_result=CheckResult(passed=True, reasons=[]),
            mutations=[
                Mutation(
                    type="set_property",
                    target="item",
                    property="location",
                    old_value=None,
                    new_value="inventory",
                )
            ],
        ),
        total_mechanics_executed=1,
        max_depth_reached=1,
        truncated=False,
    )
    return TickResult.ok(
        tick_id=tick_id,
        observation="You look around.",
        trace=trace,
        projected_state={"room": {"properties": {}}},
    )


def _make_fake_engine(turns: int) -> MagicMock:
    engine = MagicMock()
    engine.run_tick.side_effect = [_fake_ok_result(f"tick_{i + 1}") for i in range(turns)]
    return engine


def _make_fake_agent(action: str = "look around") -> MagicMock:
    agent = MagicMock()
    agent.run_turn.return_value = action
    agent.agent_id = "resident_1"
    return agent


def _make_fake_memory() -> MagicMock:
    memory = MagicMock()
    memory.store_turn.return_value = None
    return memory


def _build_runner(engine: MagicMock, agent: MagicMock, memory: MagicMock) -> PlaytestRunner:
    return PlaytestRunner(
        engine=engine,
        agent=agent,
        memory=memory,
        agent_id="resident_1",
        session_id="session_1",
    )


def _all_agent_decide_scenario(
    *,
    adversarial_rate: float,
    adversarial_categories: list[str] | None = None,
    seed: int = 42,
    turns: int = 20,
) -> Scenario:
    """Build a Scenario whose turns are entirely agent-decide (action: null)."""
    return Scenario(
        name="test_scenario",
        description="Auto-injection test scenario",
        adversarial_rate=adversarial_rate,
        adversarial_categories=adversarial_categories,
        seed=seed,
        turns=[{"action": None} for _ in range(turns)],
    )


def _read_report(tmp_path: Path) -> dict:
    report_dir = tmp_path / "playtest-reports"
    report_path = next(report_dir.iterdir())
    return json.loads(report_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Rate 0.0 -> no injections (regression: existing behavior)
# ---------------------------------------------------------------------------


def test_adversarial_rate_zero_means_no_injections(tmp_path: Path) -> None:
    """rate=0.0 -> agent.run_turn() fires on every agent-decide turn; no injections."""
    n = 10
    engine = _make_fake_engine(n)
    agent = _make_fake_agent("hello world")
    memory = _make_fake_memory()

    scenario = _all_agent_decide_scenario(adversarial_rate=0.0, turns=n)

    runner = _build_runner(engine, agent, memory)
    runner.run(tmp_path, turns=n, scenario=scenario)

    # agent.run_turn must be called exactly once per turn
    assert agent.run_turn.call_count == n

    data = _read_report(tmp_path)
    assert len(data["turns"]) == n
    # Every record must be marked adversarial_injected=False
    assert all(t["adversarial_injected"] is False for t in data["turns"])
    # Every action_text should match the agent's stubbed reply
    assert all(t["action_text"] == "hello world" for t in data["turns"])


# ---------------------------------------------------------------------------
# Rate 1.0 -> every agent-decide turn injects
# ---------------------------------------------------------------------------


def test_adversarial_rate_one_means_every_turn_injects(tmp_path: Path) -> None:
    """rate=1.0 -> every agent-decide turn is auto-injected, agent.run_turn never called."""
    n = 10
    engine = _make_fake_engine(n)
    agent = _make_fake_agent("never called")
    memory = _make_fake_memory()

    scenario = _all_agent_decide_scenario(adversarial_rate=1.0, turns=n)

    runner = _build_runner(engine, agent, memory)
    runner.run(tmp_path, turns=n, scenario=scenario)

    # agent.run_turn must NEVER be called — every turn was substituted
    agent.run_turn.assert_not_called()

    data = _read_report(tmp_path)
    assert len(data["turns"]) == n
    # Every record flagged
    assert all(t["adversarial_injected"] is True for t in data["turns"])

    # Every action text must come from the AdversarialBank corpus
    corpus = {e.text for e in AdversarialBank().list_all()}
    for t in data["turns"]:
        assert t["action_text"] in corpus, (
            f"Expected injected action {t['action_text']!r} to come from AdversarialBank"
        )


# ---------------------------------------------------------------------------
# Rate 0.5 -> deterministic subset of turns are injected (seed-stable)
# ---------------------------------------------------------------------------


def test_adversarial_rate_half_is_seed_deterministic(tmp_path: Path) -> None:
    """rate=0.5 seed=42 -> two runs yield identical injection decisions."""
    n = 40

    def _run_once(out_dir: Path) -> list[bool]:
        engine = _make_fake_engine(n)
        agent = _make_fake_agent("agent reply")
        memory = _make_fake_memory()
        scenario = _all_agent_decide_scenario(adversarial_rate=0.5, seed=42, turns=n)
        runner = _build_runner(engine, agent, memory)
        runner.run(out_dir, turns=n, scenario=scenario)
        data = _read_report(out_dir)
        return [t["adversarial_injected"] for t in data["turns"]]

    run_a = _run_once(tmp_path / "run_a")
    run_b = _run_once(tmp_path / "run_b")

    assert run_a == run_b, "Same seed must produce identical injection decisions"

    # Sanity: the outcome is neither all-True nor all-False — a proper mix.
    assert any(run_a), "rate=0.5 produced zero injections (very unlikely for n=40)"
    assert not all(run_a), "rate=0.5 produced all injections (very unlikely for n=40)"

    # And roughly 50% (allow wide slack for a 40-sample binomial)
    fired = sum(run_a)
    assert 10 <= fired <= 30, f"rate=0.5 produced {fired}/{n} injections — too skewed"


# ---------------------------------------------------------------------------
# adversarial_categories filter -> only that category is sampled
# ---------------------------------------------------------------------------


def test_adversarial_categories_filter_restricts_samples(tmp_path: Path) -> None:
    """adversarial_categories=['role_break'] -> injected texts are all from role_break."""
    n = 30
    engine = _make_fake_engine(n)
    agent = _make_fake_agent("agent reply")
    memory = _make_fake_memory()

    scenario = _all_agent_decide_scenario(
        adversarial_rate=1.0,
        adversarial_categories=["role_break"],
        seed=7,
        turns=n,
    )

    runner = _build_runner(engine, agent, memory)
    runner.run(tmp_path, turns=n, scenario=scenario)

    role_break_texts = {e.text for e in AdversarialBank().list_all() if e.category == "role_break"}

    data = _read_report(tmp_path)
    assert len(data["turns"]) == n
    for t in data["turns"]:
        assert t["adversarial_injected"] is True
        assert t["action_text"] in role_break_texts, (
            f"Injected action {t['action_text']!r} must come from the role_break category only"
        )


# ---------------------------------------------------------------------------
# Empty filtered corpus -> graceful no-op + RuntimeWarning
# ---------------------------------------------------------------------------


def test_adversarial_rate_with_empty_category_pool_warns_and_falls_back(tmp_path: Path) -> None:
    """If the coin fires but the corpus filter is empty, runner warns and calls agent.run_turn().

    This guards the "graceful no-op + warning" contract: real AdversarialBank
    categories are never empty, so we inject an empty-returning bank via
    monkey-patching the runner's pre-built instance.
    """
    n = 5
    engine = _make_fake_engine(n)
    agent = _make_fake_agent("fallback action")
    memory = _make_fake_memory()

    # Force rate=1.0 so the coin always fires; the bank will always raise.
    scenario = _all_agent_decide_scenario(adversarial_rate=1.0, turns=n)

    class _EmptyBank:
        def sample(self, rng, *, category=None, max_difficulty=3):  # type: ignore[no-untyped-def]
            raise ValueError("empty for test")

    runner = _build_runner(engine, agent, memory)
    # Replace the bank that __post_init__ built. run() does not rebuild it,
    # so the _EmptyBank survives into _maybe_sample_adversarial.
    runner._adversarial_bank = _EmptyBank()  # type: ignore[assignment]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        runner.run(tmp_path, turns=n, scenario=scenario)

    # Every turn produced a RuntimeWarning
    runtime_warnings = [w for w in caught if issubclass(w.category, RuntimeWarning)]
    assert len(runtime_warnings) == n, (
        f"Expected {n} RuntimeWarning(s), got {len(runtime_warnings)}"
    )
    assert all("AdversarialBank" in str(w.message) for w in runtime_warnings)

    # Run completed without crashing — every turn fell back to agent.run_turn()
    assert agent.run_turn.call_count == n

    data = _read_report(tmp_path)
    # All turns used the agent's fallback action and are marked not injected
    for t in data["turns"]:
        assert t["adversarial_injected"] is False
        assert t["action_text"] == "fallback action"


# ---------------------------------------------------------------------------
# Scripted + inject turns are unaffected (rate does NOT touch those paths)
# ---------------------------------------------------------------------------


def test_adversarial_rate_does_not_override_scripted_or_inject_turns(tmp_path: Path) -> None:
    """Even with rate=1.0, scripted/inject turns keep their original text."""
    engine = _make_fake_engine(4)
    agent = _make_fake_agent("unreachable")
    memory = _make_fake_memory()

    scenario = Scenario(
        name="mixed",
        description="scripted+inject+agent",
        adversarial_rate=1.0,  # would inject on every agent-decide turn
        seed=1,
        turns=[
            {"action": "scripted_first"},
            {"inject": "edge_case"},
            {"action": None},  # agent-decide -> auto-injected
            {"action": "scripted_last"},
        ],
    )

    runner = _build_runner(engine, agent, memory)
    runner.run(tmp_path, turns=4, scenario=scenario)

    data = _read_report(tmp_path)
    turns = data["turns"]
    assert turns[0]["action_text"] == "scripted_first"
    assert turns[0]["adversarial_injected"] is False

    # inject turn — the sampler produced an edge_case string. Flag must be
    # False (only auto-injection pathway sets it).
    assert turns[1]["adversarial_injected"] is False

    # agent-decide -> auto-injected
    assert turns[2]["adversarial_injected"] is True
    corpus = {e.text for e in AdversarialBank().list_all()}
    assert turns[2]["action_text"] in corpus

    assert turns[3]["action_text"] == "scripted_last"
    assert turns[3]["adversarial_injected"] is False


# ---------------------------------------------------------------------------
# Scenario YAML: invalid adversarial_categories entry is rejected at load
# ---------------------------------------------------------------------------


def test_scenario_load_rejects_invalid_adversarial_category(tmp_path: Path) -> None:
    """An unknown adversarial category must raise ValueError at load time."""
    import pytest
    import yaml

    data = {
        "name": "bad",
        "description": "d",
        "adversarial_rate": 0.5,
        "adversarial_categories": ["bogus_category"],
        "seed": 1,
        "turns": [{"action": None}],
    }
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ValueError, match="bogus_category"):
        Scenario.load(path)


def test_scenario_load_parses_adversarial_categories(tmp_path: Path) -> None:
    """A valid adversarial_categories list is parsed into the Scenario."""
    import yaml

    data = {
        "name": "ok",
        "description": "d",
        "adversarial_rate": 0.2,
        "adversarial_categories": ["nonsense", "role_break"],
        "seed": 0,
        "turns": [{"action": None}],
    }
    path = tmp_path / "ok.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")

    scenario = Scenario.load(path)
    assert scenario.adversarial_categories == ["nonsense", "role_break"]
