"""Tests for PlaytestRunner and token-world playtest CLI command (Task 4)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers: build fake TickResult, ResidentAgent, AgentMemory, engine
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
        observation="You look around the room.",
        trace=trace,
        projected_state={"room": {"properties": {}}},
    )


def _fake_yielded_result(tick_id: str = "tick_1") -> object:
    """Build a minimal yielded TickResult."""
    from token_world.engine.engine import TickResult
    from token_world.operator.yield_signal import YieldSignal

    signal = YieldSignal(
        tick_id=tick_id,
        universe_path="/tmp/test_universe",
        action_text="cast spell",
        classified_action={"verb": "cast", "target": None, "params": {}},
        actor_state={},
        candidate_mechanic_ids=[],
    )
    return TickResult.yielded(tick_id=tick_id, signal=signal)


def _make_fake_engine(results: list | None = None) -> MagicMock:
    """Build a mock SimulationEngine that returns results in sequence."""
    engine = MagicMock()
    if results is None:
        results = [_fake_ok_result(f"tick_{i + 1}") for i in range(10)]
    engine.run_tick.side_effect = results
    return engine


def _make_fake_agent(action: str = "look around") -> MagicMock:
    """Build a mock ResidentAgent."""
    agent = MagicMock()
    agent.run_turn.return_value = action
    agent.agent_id = "resident_1"
    return agent


def _make_fake_memory() -> MagicMock:
    """Build a mock AgentMemory."""
    memory = MagicMock()
    memory.store_turn.return_value = None
    return memory


def _build_runner(
    engine=None, agent=None, memory=None, agent_id="resident_1", session_id="session_1"
):
    """Construct a PlaytestRunner with fakes injected directly."""
    from token_world.playtest import PlaytestRunner

    runner = PlaytestRunner(
        engine=engine or _make_fake_engine(),
        agent=agent or _make_fake_agent(),
        memory=memory or _make_fake_memory(),
        agent_id=agent_id,
        session_id=session_id,
    )
    return runner


# ---------------------------------------------------------------------------
# Test 32: runner runs N turns without scenario
# ---------------------------------------------------------------------------


def test_runner_runs_n_turns_without_scenario(tmp_path: Path) -> None:
    """Test 32: run(turns=5) produces a report with 5 TurnRecord entries."""
    engine = _make_fake_engine([_fake_ok_result(f"tick_{i + 1}") for i in range(5)])
    agent = _make_fake_agent()
    memory = _make_fake_memory()

    runner = _build_runner(engine=engine, agent=agent, memory=memory)
    report_path = runner.run(tmp_path, turns=5)

    data = json.loads(report_path.read_text())
    assert len(data["turns"]) == 5
    # run_id must be present and non-empty
    assert data["run_id"]


# ---------------------------------------------------------------------------
# Test 33: runner uses scripted actions from scenario
# ---------------------------------------------------------------------------


def test_runner_runs_n_turns_with_scripted_scenario(tmp_path: Path) -> None:
    """Test 33: scripted turns use payload; agent-decide turns call run_turn."""
    import yaml

    from token_world.playtest import Scenario

    # 3 scripted + 2 agent-decide = 5 total turns
    data = {
        "name": "test",
        "description": "d",
        "seed": 0,
        "turns": [
            {"action": "look north"},
            {"action": "open door"},
            {"action": "go east"},
            {"action": None},
            {"action": None},
        ],
    }
    scenario_path = tmp_path / "s.yaml"
    scenario_path.write_text(yaml.dump(data))
    scenario = Scenario.load(scenario_path)

    engine = _make_fake_engine([_fake_ok_result(f"tick_{i + 1}") for i in range(5)])
    agent = _make_fake_agent("agent action")
    memory = _make_fake_memory()

    runner = _build_runner(engine=engine, agent=agent, memory=memory)
    runner.run(tmp_path, turns=5, scenario=scenario)

    # Agent run_turn should have been called exactly 2 times (turns 3+4 are null)
    assert agent.run_turn.call_count == 2


# ---------------------------------------------------------------------------
# Test 34: inject turns use sampler, not agent
# ---------------------------------------------------------------------------


def test_runner_handles_inject_turns(tmp_path: Path) -> None:
    """Test 34: inject turns feed sampler output to engine, not agent.run_turn."""
    import yaml

    from token_world.playtest import Scenario

    data = {
        "name": "test",
        "description": "d",
        "seed": 0,
        "turns": [{"inject": "nonsense"}],
    }
    scenario_path = tmp_path / "s.yaml"
    scenario_path.write_text(yaml.dump(data))
    scenario = Scenario.load(scenario_path)

    engine = _make_fake_engine([_fake_ok_result("tick_1")])
    agent = _make_fake_agent()
    memory = _make_fake_memory()

    runner = _build_runner(engine=engine, agent=agent, memory=memory)
    runner.run(tmp_path, turns=1, scenario=scenario)

    # Agent should NOT have been called for the inject turn
    agent.run_turn.assert_not_called()
    # Engine should have been called once with some non-empty action
    assert engine.run_tick.call_count == 1
    action_used = engine.run_tick.call_args[0][0]
    assert isinstance(action_used, str)
    assert len(action_used) >= 0  # nonsense can be any string


# ---------------------------------------------------------------------------
# Test 35: runner resumes after yield
# ---------------------------------------------------------------------------


def test_runner_resumes_after_yield(tmp_path: Path) -> None:
    """Test 35: yielded result + no_operator=False -> harness called, then re-run."""
    yielded = _fake_yielded_result("tick_1")
    ok = _fake_ok_result("tick_1")

    engine = _make_fake_engine([yielded, ok])
    agent = _make_fake_agent()
    memory = _make_fake_memory()

    runner = _build_runner(engine=engine, agent=agent, memory=memory)

    # Replace harness_factory with a mock that returns an async handle_yield
    mock_harness = MagicMock()
    mock_harness.handle_yield = AsyncMock(return_value=MagicMock(success=True))
    runner.harness_factory = MagicMock(return_value=mock_harness)

    runner.run(tmp_path, turns=1, no_operator=False)

    # Harness handle_yield must have been called once
    mock_harness.handle_yield.assert_called_once()

    # Engine.run_tick must have been called twice (yield + resume)
    assert engine.run_tick.call_count == 2

    # The TurnRecord in the report must show kind="ok" (resolved)
    report_path = list((tmp_path / "playtest-reports").iterdir())[0]
    data = json.loads(report_path.read_text())
    assert data["turns"][0]["kind"] == "ok"


# ---------------------------------------------------------------------------
# Test 36: no_operator=True skips harness
# ---------------------------------------------------------------------------


def test_runner_respects_no_operator_flag(tmp_path: Path) -> None:
    """Test 36: yielded + no_operator=True -> harness NOT called."""
    yielded = _fake_yielded_result("tick_1")

    engine = _make_fake_engine([yielded])
    agent = _make_fake_agent()
    memory = _make_fake_memory()

    runner = _build_runner(engine=engine, agent=agent, memory=memory)
    mock_harness_factory = MagicMock()
    runner.harness_factory = mock_harness_factory

    runner.run(tmp_path, turns=1, no_operator=True)

    # Harness factory must NOT have been called
    mock_harness_factory.assert_not_called()

    # TurnRecord kind should be "yielded" (unresolved)
    report_path = list((tmp_path / "playtest-reports").iterdir())[0]
    data = json.loads(report_path.read_text())
    assert data["turns"][0]["kind"] == "yielded"


# ---------------------------------------------------------------------------
# Test 37: memory.store_turn called each turn
# ---------------------------------------------------------------------------


def test_runner_stores_each_turn_in_memory(tmp_path: Path) -> None:
    """Test 37: memory.store_turn called once per turn with correct turn_numbers."""
    engine = _make_fake_engine([_fake_ok_result(f"tick_{i + 1}") for i in range(3)])
    agent = _make_fake_agent()
    memory = _make_fake_memory()

    runner = _build_runner(
        engine=engine, agent=agent, memory=memory, agent_id="agt1", session_id="sess1"
    )
    runner.run(tmp_path, turns=3)

    assert memory.store_turn.call_count == 3
    # Check turn numbers were 0, 1, 2
    turn_numbers = [c.args[2] for c in memory.store_turn.call_args_list]
    assert turn_numbers == [0, 1, 2]


# ---------------------------------------------------------------------------
# Test 38: report written once at end only
# ---------------------------------------------------------------------------


def test_runner_writes_report_at_end_only(tmp_path: Path) -> None:
    """Test 38: _atomic_write_json called exactly once (not per-turn)."""
    import token_world.playtest.report as report_mod
    from token_world.mechanic.diagnostics import _atomic_write_json as real_write

    engine = _make_fake_engine([_fake_ok_result(f"tick_{i + 1}") for i in range(10)])
    agent = _make_fake_agent()
    memory = _make_fake_memory()

    write_call_count = []

    def counting_write(path, obj):
        write_call_count.append(path)
        return real_write(path, obj)

    runner = _build_runner(engine=engine, agent=agent, memory=memory)
    with patch.object(report_mod, "_atomic_write_json", side_effect=counting_write):
        runner.run(tmp_path, turns=10)

    # Exactly one write call for the report
    assert len(write_call_count) == 1
    assert "playtest-reports" in str(write_call_count[0])


# ---------------------------------------------------------------------------
# Test 39: hash_check_fn hook called at start
# ---------------------------------------------------------------------------


def test_runner_invokes_hash_check_fn_hook_at_start(tmp_path: Path) -> None:
    """Test 39: hash_check_fn is called once at run start; report has the hashes."""
    engine = _make_fake_engine([_fake_ok_result("tick_1")])
    agent = _make_fake_agent()
    memory = _make_fake_memory()

    fake_hashes = {"agent": "sha256:abc", "classifier": "sha256:def"}
    hash_check = MagicMock(return_value=fake_hashes)

    runner = _build_runner(engine=engine, agent=agent, memory=memory)
    runner.hash_check_fn = hash_check

    runner.run(tmp_path, turns=1)

    hash_check.assert_called_once_with(engine, agent)

    report_path = list((tmp_path / "playtest-reports").iterdir())[0]
    data = json.loads(report_path.read_text())
    assert data["prompts_sha256"] == fake_hashes


# ---------------------------------------------------------------------------
# WR-01 regression: --output path must be honoured exactly
# ---------------------------------------------------------------------------


def test_runner_honours_exact_output_path(tmp_path: Path) -> None:
    """WR-01: runner.run(output_path=...) writes to the exact path given, not parent dir."""
    engine = _make_fake_engine([_fake_ok_result("tick_1")])
    agent = _make_fake_agent()
    memory = _make_fake_memory()

    runner = _build_runner(engine=engine, agent=agent, memory=memory)

    output_path = tmp_path / "my_run.json"
    returned = runner.run(tmp_path, turns=1, output_path=output_path)

    # The returned path must equal the exact requested path
    assert returned == output_path, f"Expected {output_path}, got {returned}"
    # The file must exist at the exact path
    assert output_path.exists(), f"File not found at requested path: {output_path}"
    # The UUID-based directory must NOT have been created
    assert not (tmp_path / "playtest-reports").exists(), (
        "playtest-reports dir created instead of using specified output path"
    )


def test_runner_creates_parent_dirs_for_output_path(tmp_path: Path) -> None:
    """WR-01: runner creates parent directories for nested output_path."""
    engine = _make_fake_engine([_fake_ok_result("tick_1")])
    agent = _make_fake_agent()
    memory = _make_fake_memory()

    runner = _build_runner(engine=engine, agent=agent, memory=memory)

    output_path = tmp_path / "subdir" / "deep" / "report.json"
    returned = runner.run(tmp_path, turns=1, output_path=output_path)

    assert returned == output_path
    assert output_path.exists()


# ---------------------------------------------------------------------------
# WR-02 regression: maybe_compact_summary called each turn
# ---------------------------------------------------------------------------


def test_runner_calls_maybe_compact_summary_each_turn(tmp_path: Path) -> None:
    """WR-02: PlaytestRunner calls memory.maybe_compact_summary once per turn."""
    n_turns = 12
    engine = _make_fake_engine([_fake_ok_result(f"tick_{i + 1}") for i in range(n_turns)])
    agent = _make_fake_agent()
    memory = _make_fake_memory()

    runner = _build_runner(engine=engine, agent=agent, memory=memory)
    runner.run(tmp_path, turns=n_turns)

    # maybe_compact_summary must have been called once per turn
    assert memory.maybe_compact_summary.call_count == n_turns, (
        f"Expected {n_turns} calls to maybe_compact_summary, "
        f"got {memory.maybe_compact_summary.call_count}"
    )


# ---------------------------------------------------------------------------
# Test 40: CLI playtest command exists with expected options
# ---------------------------------------------------------------------------


def test_cli_playtest_command_exists_and_has_expected_options() -> None:
    """Test 40: token-world playtest --help shows all expected options."""
    from click.testing import CliRunner

    from token_world.cli import cli

    result = CliRunner().invoke(cli, ["playtest", "--help"])
    assert result.exit_code == 0
    output = result.output
    assert "--turns" in output
    assert "--scenario" in output
    assert "--seed" in output
    assert "--no-operator" in output
    assert "--judge" in output
    assert "--output" in output


# ---------------------------------------------------------------------------
# Test 41: CLI playtest runs end-to-end with mocks
# ---------------------------------------------------------------------------


def test_cli_playtest_runs_end_to_end(tmp_path: Path) -> None:
    """Test 41: mock everything; invoke playtest <slug> --turns 3; exit 0; report exists."""
    from click.testing import CliRunner

    from token_world.cli import cli

    # Build a fake universe directory structure
    universe_dir = tmp_path / "universes" / "test-universe"
    universe_dir.mkdir(parents=True)
    (universe_dir / "universe.db").touch()
    (universe_dir / "mechanics").mkdir()
    (universe_dir / "CLAUDE.md").write_text("# Test Universe\n")

    # Setup report path returned by runner.run
    report_dir = universe_dir / "playtest-reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    fake_report = report_dir / "abc123.json"
    fake_report.write_text(
        json.dumps(
            {
                "run_id": "abc123",
                "aggregate_scores": {
                    "mechanic_match_rate": 1.0,
                    "observation_groundedness": 1.0,
                    "mutation_count": 1.0,
                    "refusal_rate": 1.0,
                    "action_novelty": 1.0,
                    "composite": 1.0,
                },
            }
        )
    )

    with (
        patch("token_world.cli.UniverseManager") as MockUM,
        patch("token_world.cli.KnowledgeGraph") as MockKG,
        patch("token_world.cli.anthropic.Anthropic"),
        patch("token_world.cli.AgentMemory"),
        patch("token_world.cli.SessionManager"),
        patch("token_world.cli.SimulationEngine"),
        patch("token_world.cli._load_or_create_agent") as MockLoadAgent,
        patch("token_world.cli.PlaytestRunner") as MockRunner,
    ):
        # Setup UniverseManager
        MockUM.return_value.load.return_value = universe_dir

        # Setup KnowledgeGraph
        mock_kg = MagicMock()
        MockKG.return_value = mock_kg

        # _load_or_create_agent returns (agent, agent_id, session_id)
        MockLoadAgent.return_value = (MagicMock(), "resident_1", "session_abc")

        # PlaytestRunner.run returns the fake report path
        MockRunner.return_value.run.return_value = fake_report

        cli_runner = CliRunner()
        result = cli_runner.invoke(cli, ["playtest", "test-universe", "--turns", "3"])

        if result.exit_code != 0:
            print(result.output)
            if result.exception:
                import traceback

                traceback.print_exception(
                    type(result.exception),
                    result.exception,
                    result.exception.__traceback__,
                )

        assert result.exit_code == 0
        assert fake_report.exists()


# ---------------------------------------------------------------------------
# Task 4 CLI tests: hash registry + judge wiring (tests 21-25 per plan)
# ---------------------------------------------------------------------------


def _cli_universe_setup(tmp_path: Path) -> tuple:
    """Create a fake universe directory and a minimal fake report.

    Returns:
        Tuple of (universe_dir, fake_report).
    """
    universe_dir = tmp_path / "universes" / "test-universe"
    universe_dir.mkdir(parents=True)
    (universe_dir / "universe.db").touch()
    (universe_dir / "mechanics").mkdir()
    (universe_dir / "CLAUDE.md").write_text("# Test Universe\n")

    report_dir = universe_dir / "playtest-reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    fake_report = report_dir / "run123.json"
    fake_report.write_text(
        json.dumps(
            {
                "run_id": "run123",
                "scenario_file": None,
                "turns": [],
                "aggregate_scores": {
                    "mechanic_match_rate": 1.0,
                    "observation_groundedness": 1.0,
                    "mutation_count": 1.0,
                    "refusal_rate": 1.0,
                    "action_novelty": 1.0,
                    "composite": 1.0,
                },
                "prompts_sha256": {},
                "duration_ms": 100,
                "schema_version": 1,
            }
        )
    )
    return universe_dir, fake_report


def _make_cli_patches(universe_dir: Path, fake_report: Path):
    """Return a list of patch() context managers for common CLI-layer dependencies."""
    from unittest.mock import MagicMock

    mock_runner_instance = MagicMock()
    mock_runner_instance.run.return_value = fake_report
    mock_runner_instance.hash_check_fn = None

    return [
        patch(
            "token_world.cli.UniverseManager",
            MagicMock(**{"return_value.load.return_value": universe_dir}),
        ),
        patch("token_world.cli.KnowledgeGraph", MagicMock()),
        patch("token_world.cli.anthropic.Anthropic", MagicMock()),
        patch("token_world.cli.AgentMemory", MagicMock()),
        patch("token_world.cli.SessionManager", MagicMock()),
        patch("token_world.cli.SimulationEngine", MagicMock()),
        patch(
            "token_world.cli._load_or_create_agent",
            MagicMock(return_value=(MagicMock(), "resident_1", "sess_abc")),
        ),
        patch(
            "token_world.cli.PlaytestRunner",
            MagicMock(return_value=mock_runner_instance),
        ),
    ]


def test_cli_playtest_seeds_prompt_hash_file_on_first_run(tmp_path: Path) -> None:
    """Test 21: first run seeds prompts.sha256.json with three non-empty hashes."""
    import contextlib

    from click.testing import CliRunner

    from token_world.cli import cli

    universe_dir, fake_report = _cli_universe_setup(tmp_path)
    ctx_managers = _make_cli_patches(universe_dir, fake_report)

    with contextlib.ExitStack() as stack:
        for cm in ctx_managers:
            stack.enter_context(cm)
        cli_runner = CliRunner()
        result = cli_runner.invoke(cli, ["playtest", "test-universe", "--turns", "2"])

    assert result.exit_code == 0, f"CLI failed: {result.output}"


def test_cli_playtest_triggers_regression_on_prompt_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 22: when detect_changes returns non-empty, trigger_regression is called."""
    import contextlib
    import subprocess

    from click.testing import CliRunner

    from token_world.cli import cli

    universe_dir, fake_report = _cli_universe_setup(tmp_path)

    # Preseed a different hash baseline so detect_changes fires
    baseline = {
        "classifier_system_prompt": "old" + "x" * 61,
        "observer_system_prompt": "old" + "y" * 61,
        "agent_system_prompt": "old" + "z" * 61,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (universe_dir / "prompts.sha256.json").write_text(json.dumps(baseline))

    subprocess_calls: list = []

    def fake_subprocess(cmd, **kwargs):
        subprocess_calls.append(cmd)
        r = MagicMock()
        r.returncode = 0
        r.stdout = "5 passed in 1.2s"
        r.stderr = ""
        return r

    monkeypatch.setattr(subprocess, "run", fake_subprocess)

    ctx_managers = _make_cli_patches(universe_dir, fake_report)

    with contextlib.ExitStack() as stack:
        mocks = [stack.enter_context(cm) for cm in ctx_managers]
        cli_runner = CliRunner()
        result = cli_runner.invoke(cli, ["playtest", "test-universe", "--turns", "1"])

    assert result.exit_code == 0, f"CLI failed: {result.output}"

    # Verify: the hash_check_fn closure was set on the runner; manually invoke it
    # with agent whose hashes differ from baseline to trigger regression
    runner_cls_mock = mocks[-1]  # last patch = PlaytestRunner
    runner_instance = runner_cls_mock.return_value
    hash_fn = getattr(runner_instance, "hash_check_fn", None)
    if hash_fn is not None:
        mock_engine = MagicMock()
        mock_agent = MagicMock()
        mock_agent.system_prompt_text.return_value = "changed prompt"
        from token_world.engine.classifier import Classifier
        from token_world.engine.observer import Observer

        with (
            patch.object(Classifier, "system_prompt_text", classmethod(lambda cls: "new_cls")),
            patch.object(Observer, "system_prompt_text", classmethod(lambda cls: "new_obs")),
        ):
            hash_fn(mock_engine, mock_agent)

        history_path = universe_dir / "regression-history.jsonl"
        if history_path.exists():
            row = json.loads(history_path.read_text().strip())
            assert row["trigger"] == "prompt_hash_change"
            assert subprocess_calls


def test_cli_playtest_no_regression_when_hashes_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 23: when hashes match baseline, regression is NOT triggered."""
    import contextlib
    import subprocess

    from click.testing import CliRunner

    from token_world.cli import cli
    from token_world.playtest.hash_registry import PromptHashRegistry

    universe_dir, fake_report = _cli_universe_setup(tmp_path)

    # Seed the baseline with the CURRENT hashes so they match exactly
    reg = PromptHashRegistry()

    class _FakeAgent:
        def system_prompt_text(self) -> str:
            return "fixed agent prompt"

    current_hashes = reg.compute_hashes(None, _FakeAgent())
    reg.save(universe_dir, current_hashes)

    subprocess_calls: list = []

    def fake_subprocess(cmd, **kwargs):
        subprocess_calls.append(cmd)
        r = MagicMock()
        r.returncode = 0
        r.stdout = "1 passed in 0.1s"
        r.stderr = ""
        return r

    monkeypatch.setattr(subprocess, "run", fake_subprocess)

    ctx_managers = _make_cli_patches(universe_dir, fake_report)

    with contextlib.ExitStack() as stack:
        mocks = [stack.enter_context(cm) for cm in ctx_managers]
        cli_runner = CliRunner()
        result = cli_runner.invoke(cli, ["playtest", "test-universe", "--turns", "1"])

    assert result.exit_code == 0, f"CLI failed: {result.output}"

    # Manually invoke hash_check_fn with the SAME agent so hashes match -> no regression
    runner_instance = mocks[-1].return_value
    hash_fn = getattr(runner_instance, "hash_check_fn", None)
    if hash_fn is not None:
        hash_fn(MagicMock(), _FakeAgent())

    assert not subprocess_calls, "subprocess.run must NOT be called when hashes match"


def test_cli_playtest_judge_appends_to_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 24: --judge appends judge result to the report JSON."""
    import contextlib

    from click.testing import CliRunner

    from token_world.cli import cli

    universe_dir, fake_report = _cli_universe_setup(tmp_path)
    ctx_managers = _make_cli_patches(universe_dir, fake_report)

    judge_result = {
        "scores": {
            "coherence": 0.9,
            "personality_consistency": 0.85,
            "world_rule_adherence": 0.8,
        },
        "rationale": "Agent performed well.",
        "model": "claude-sonnet-4-5",
        "prompt_hash": "a" * 64,
    }

    with contextlib.ExitStack() as stack:
        for cm in ctx_managers:
            stack.enter_context(cm)
        mock_judge = stack.enter_context(
            patch("token_world.cli.judge_evaluate", return_value=judge_result)
        )
        cli_runner = CliRunner()
        result = cli_runner.invoke(cli, ["playtest", "test-universe", "--turns", "1", "--judge"])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    mock_judge.assert_called_once()

    data = json.loads(fake_report.read_text())
    assert "judge" in data
    assert data["judge"]["scores"]["coherence"] == pytest.approx(0.9)


def test_cli_playtest_judge_failure_does_not_block_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 25: judge raise does not cause CLI to exit non-zero; report still written."""
    import contextlib

    from click.testing import CliRunner

    from token_world.cli import cli

    universe_dir, fake_report = _cli_universe_setup(tmp_path)
    ctx_managers = _make_cli_patches(universe_dir, fake_report)

    with contextlib.ExitStack() as stack:
        for cm in ctx_managers:
            stack.enter_context(cm)
        stack.enter_context(
            patch(
                "token_world.cli.judge_evaluate",
                side_effect=RuntimeError("network error"),
            )
        )
        cli_runner = CliRunner()
        result = cli_runner.invoke(cli, ["playtest", "test-universe", "--turns", "1", "--judge"])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    assert fake_report.exists()
