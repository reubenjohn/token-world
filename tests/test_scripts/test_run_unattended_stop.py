"""Tests for .stop startup check and PID file in run_unattended.py (SC-3/OPS-01)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch


def _run_main_with_universe(universe_dir: Path, extra_args: list[str] | None = None) -> int:
    """Invoke run_unattended.main() with a mocked UniverseManager returning universe_dir."""

    args = ["--slug", "test-slug"] + (extra_args or [])

    with (
        patch("scripts.run_unattended.UniverseManager") as mock_mgr_cls,
        patch("scripts.run_unattended.KnowledgeGraph") as mock_kg_cls,
        patch("scripts.run_unattended._load_or_create_agent") as mock_load_agent,
        patch("scripts.run_unattended.anthropic.Anthropic"),
        patch("scripts.run_unattended.AgentMemory"),
        patch("scripts.run_unattended.SessionManager"),
        patch("scripts.run_unattended.SimulationEngine"),
        patch("scripts.run_unattended.PlaytestRunner") as mock_runner_cls,
        patch("sys.argv", ["run_unattended.py"] + args),
    ):
        mock_mgr = MagicMock()
        mock_mgr.load.return_value = universe_dir
        mock_mgr_cls.return_value = mock_mgr

        mock_kg = MagicMock()
        mock_kg_cls.return_value = mock_kg

        mock_load_agent.return_value = (MagicMock(), "agent_1", "session_1")

        mock_runner = MagicMock()
        mock_runner.progress_fn = lambda msg: None
        # Make runner.run return a Path so the success path is taken
        mock_runner.run.return_value = universe_dir / "report.json"
        mock_runner_cls.return_value = mock_runner

        # Create minimal CLAUDE.md so the script doesn't crash
        claude_md = universe_dir / "CLAUDE.md"
        if not claude_md.exists():
            claude_md.write_text("", encoding="utf-8")

        from scripts.run_unattended import main

        return main()


# ---------------------------------------------------------------------------
# test_stop_file_exits_nonzero
# ---------------------------------------------------------------------------


def test_stop_file_exits_nonzero(tmp_path: Path, capsys) -> None:
    """When .stop exists at startup, main() returns non-zero."""
    (tmp_path / ".stop").write_text("", encoding="utf-8")
    result = _run_main_with_universe(tmp_path)
    assert result != 0


# ---------------------------------------------------------------------------
# test_stop_file_message_names_path
# ---------------------------------------------------------------------------


def test_stop_file_message_names_path(tmp_path: Path, capsys) -> None:
    """stderr output must contain the actual .stop file path."""
    stop_path = tmp_path / ".stop"
    stop_path.write_text("", encoding="utf-8")
    _run_main_with_universe(tmp_path)
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert ".stop" in captured.err


# ---------------------------------------------------------------------------
# test_pid_file_written_and_removed
# ---------------------------------------------------------------------------


def test_pid_file_written_and_removed(tmp_path: Path) -> None:
    """.run-pid exists during run and is absent after clean exit."""
    pid_path = tmp_path / ".run-pid"
    pid_written_during_run = []

    def check_pid_during_run(*args, **kwargs):
        pid_written_during_run.append(pid_path.exists())
        return tmp_path / "report.json"

    with (
        patch("scripts.run_unattended.UniverseManager") as mock_mgr_cls,
        patch("scripts.run_unattended.KnowledgeGraph"),
        patch("scripts.run_unattended._load_or_create_agent") as mock_load_agent,
        patch("scripts.run_unattended.anthropic.Anthropic"),
        patch("scripts.run_unattended.AgentMemory"),
        patch("scripts.run_unattended.SessionManager"),
        patch("scripts.run_unattended.SimulationEngine"),
        patch("scripts.run_unattended.PlaytestRunner") as mock_runner_cls,
        patch("sys.argv", ["run_unattended.py", "--slug", "test"]),
    ):
        mock_mgr = MagicMock()
        mock_mgr.load.return_value = tmp_path
        mock_mgr_cls.return_value = mock_mgr

        mock_load_agent.return_value = (MagicMock(), "agent_1", "session_1")

        mock_runner = MagicMock()
        mock_runner.progress_fn = lambda msg: None
        mock_runner.run.side_effect = check_pid_during_run
        mock_runner_cls.return_value = mock_runner

        (tmp_path / "CLAUDE.md").write_text("", encoding="utf-8")

        from scripts.run_unattended import main

        result = main()

    assert result == 0
    # PID file existed during run
    assert True in pid_written_during_run
    # PID file removed after exit
    assert not pid_path.exists()


# ---------------------------------------------------------------------------
# test_pid_file_json_shape
# ---------------------------------------------------------------------------


def test_pid_file_json_shape(tmp_path: Path) -> None:
    """.run-pid JSON has 'pid' (int) and 'started_at' (str) keys."""
    pid_content: list[dict] = []

    def capture_pid_content(*args, **kwargs):
        pid_path = tmp_path / ".run-pid"
        if pid_path.exists():
            data = json.loads(pid_path.read_text(encoding="utf-8"))
            pid_content.append(data)
        return tmp_path / "report.json"

    with (
        patch("scripts.run_unattended.UniverseManager") as mock_mgr_cls,
        patch("scripts.run_unattended.KnowledgeGraph"),
        patch("scripts.run_unattended._load_or_create_agent") as mock_load_agent,
        patch("scripts.run_unattended.anthropic.Anthropic"),
        patch("scripts.run_unattended.AgentMemory"),
        patch("scripts.run_unattended.SessionManager"),
        patch("scripts.run_unattended.SimulationEngine"),
        patch("scripts.run_unattended.PlaytestRunner") as mock_runner_cls,
        patch("sys.argv", ["run_unattended.py", "--slug", "test"]),
    ):
        mock_mgr = MagicMock()
        mock_mgr.load.return_value = tmp_path
        mock_mgr_cls.return_value = mock_mgr

        mock_load_agent.return_value = (MagicMock(), "agent_1", "session_1")

        mock_runner = MagicMock()
        mock_runner.progress_fn = lambda msg: None
        mock_runner.run.side_effect = capture_pid_content
        mock_runner_cls.return_value = mock_runner

        (tmp_path / "CLAUDE.md").write_text("", encoding="utf-8")

        from scripts.run_unattended import main

        main()

    assert len(pid_content) >= 1
    data = pid_content[0]
    assert "pid" in data
    assert isinstance(data["pid"], int)
    assert "started_at" in data
    assert isinstance(data["started_at"], str)
