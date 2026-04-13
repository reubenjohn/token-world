"""Tests for `token-world agent-turn` CLI command (Task 5 TDD)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from token_world.cli import cli
from token_world.resident.memory import ensure_memory_tables

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_PERSONALITY_JSON = (
    '{"name":"Elara","archetype":"curious wanderer",'
    '"traits":["inquisitive","brave","kind"],'
    '"backstory":"She grew up exploring the misty caves.",'
    '"speech_style":"speaks in clipped sentences"}'
)


def _make_universe(tmp_path: Path) -> Path:
    """Create a minimal universe directory structure."""
    universe_dir = tmp_path / "universes" / "test-universe"
    universe_dir.mkdir(parents=True)
    (universe_dir / "CLAUDE.md").write_text("# World rules\nThis is a test world.")
    (universe_dir / "universe.db").touch()
    (universe_dir / "mechanics").mkdir()
    (universe_dir / "conservation.yaml").write_text("{}")
    (universe_dir / "tick_summaries").mkdir()
    return universe_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_agent_turn_loads_universe_or_errors(tmp_path: Path) -> None:
    """CLI exits non-zero and prints error for nonexistent universe slug."""
    with patch("token_world.cli.UniverseManager") as MockMgr:
        MockMgr.return_value.load.side_effect = FileNotFoundError("Universe not found")
        runner = CliRunner()
        result = runner.invoke(cli, ["agent-turn", "nonexistent-universe"])

    assert result.exit_code != 0
    assert "Error" in result.output or "Error" in (result.exception and str(result.exception) or "")


def test_agent_turn_auto_creates_agent_when_none_exists(tmp_path: Path) -> None:
    """When no agent_sessions exist, auto-creates agent node + session."""
    universe_dir = _make_universe(tmp_path)
    db_path = universe_dir / "universe.db"

    # Pre-create agent_sessions table so list_agents returns empty
    with sqlite3.connect(str(db_path)) as conn:
        ensure_memory_tables(conn)

    mock_tick_result = MagicMock()
    mock_tick_result.kind = "ok"
    mock_tick_result.observation = "You see a misty cavern."
    mock_tick_result.tick_id = "1"

    with (
        patch("token_world.cli.UniverseManager") as MockMgr,
        patch("token_world.cli.KnowledgeGraph") as MockKG,
        patch("token_world.cli.anthropic"),
        patch("token_world.cli.PersonalityGenerator") as MockGen,
        patch("token_world.cli.SimulationEngine") as MockEngine,
        patch("token_world.cli.ResidentAgent") as MockAgent,
    ):
        MockMgr.return_value.load.return_value = universe_dir
        mock_kg = MagicMock()
        mock_kg.claim_id.return_value = "resident_abc"
        MockKG.return_value = mock_kg

        mock_personality = MagicMock()
        mock_personality.model_dump_json.return_value = _VALID_PERSONALITY_JSON
        mock_personality.model_dump.return_value = {
            "name": "Elara",
            "archetype": "curious wanderer",
            "traits": ["inquisitive", "brave", "kind"],
            "backstory": "She grew up exploring the misty caves.",
            "speech_style": "speaks in clipped sentences",
        }
        MockGen.return_value.generate.return_value = mock_personality

        MockEngine.return_value.run_tick.return_value = mock_tick_result
        MockAgent.return_value.run_turn.return_value = "look around"

        runner = CliRunner()
        result = runner.invoke(cli, ["agent-turn", "test-universe"])

    assert result.exit_code == 0, result.output
    # Generator was called (auto-create path)
    MockGen.return_value.generate.assert_called_once()


def test_agent_turn_runs_one_tick_and_prints_observation(tmp_path: Path) -> None:
    """agent-turn runs one tick and prints observation to stdout."""
    universe_dir = _make_universe(tmp_path)
    db_path = universe_dir / "universe.db"

    with sqlite3.connect(str(db_path)) as conn:
        ensure_memory_tables(conn)
        # Pre-create a session so auto-create is skipped
        conn.execute(
            "INSERT INTO agent_sessions (session_id, agent_id, started_at, agent_personality) "
            "VALUES (?,?,?,?)",
            ("s1", "alice", "2026-01-01T00:00:00+00:00", _VALID_PERSONALITY_JSON),
        )

    mock_tick_result = MagicMock()
    mock_tick_result.kind = "ok"
    mock_tick_result.observation = "you see the room"
    mock_tick_result.tick_id = "1"
    mock_tick_result.yield_signal = None

    with (
        patch("token_world.cli.UniverseManager") as MockMgr,
        patch("token_world.cli.KnowledgeGraph") as MockKG,
        patch("token_world.cli.anthropic"),
        patch("token_world.cli.SimulationEngine") as MockEngine,
        patch("token_world.cli.ResidentAgent") as MockAgent,
    ):
        MockMgr.return_value.load.return_value = universe_dir
        mock_kg = MagicMock()
        MockKG.return_value = mock_kg

        MockEngine.return_value.run_tick.return_value = mock_tick_result
        MockAgent.return_value.run_turn.return_value = "look around"

        runner = CliRunner()
        result = runner.invoke(cli, ["agent-turn", "test-universe"])

    assert result.exit_code == 0, result.output
    assert "you see the room" in result.output


def test_agent_turn_handles_yield_via_operator_harness(tmp_path: Path) -> None:
    """When engine yields, OperatorHarness.handle_yield is called, then tick resumes."""
    universe_dir = _make_universe(tmp_path)
    db_path = universe_dir / "universe.db"

    with sqlite3.connect(str(db_path)) as conn:
        ensure_memory_tables(conn)
        conn.execute(
            "INSERT INTO agent_sessions (session_id, agent_id, started_at, agent_personality) "
            "VALUES (?,?,?,?)",
            ("s1", "alice", "2026-01-01T00:00:00+00:00", _VALID_PERSONALITY_JSON),
        )

    mock_yield_signal = MagicMock()
    mock_yield_result = MagicMock()
    mock_yield_result.kind = "yielded"
    mock_yield_result.yield_signal = mock_yield_signal
    mock_yield_result.observation = None
    mock_yield_result.tick_id = "1"

    mock_ok_result = MagicMock()
    mock_ok_result.kind = "ok"
    mock_ok_result.observation = "mechanic authored, action succeeded"
    mock_ok_result.tick_id = "2"
    mock_ok_result.yield_signal = None

    with (
        patch("token_world.cli.UniverseManager") as MockMgr,
        patch("token_world.cli.KnowledgeGraph") as MockKG,
        patch("token_world.cli.anthropic"),
        patch("token_world.cli.SimulationEngine") as MockEngine,
        patch("token_world.cli.ResidentAgent") as MockAgent,
        patch("token_world.cli.OperatorHarness") as MockHarness,
        patch("token_world.cli.asyncio") as mock_asyncio,
    ):
        MockMgr.return_value.load.return_value = universe_dir
        MockKG.return_value = MagicMock()
        # First call yields, second call returns ok
        MockEngine.return_value.run_tick.side_effect = [mock_yield_result, mock_ok_result]
        MockAgent.return_value.run_turn.return_value = "open the chest"
        mock_asyncio.run.return_value = None

        runner = CliRunner()
        result = runner.invoke(cli, ["agent-turn", "test-universe"])

    assert result.exit_code == 0, result.output
    # OperatorHarness was constructed and handle_yield was invoked via asyncio.run
    MockHarness.assert_called_once_with(universe_dir)
    mock_asyncio.run.assert_called_once()
    # Engine was called twice (yield + resume)
    assert MockEngine.return_value.run_tick.call_count == 2
    assert "mechanic authored" in result.output


def test_agent_turn_persists_turn_to_memory(tmp_path: Path) -> None:
    """After a turn, agent_memory table has one row with correct values."""
    universe_dir = _make_universe(tmp_path)
    db_path = universe_dir / "universe.db"

    with sqlite3.connect(str(db_path)) as conn:
        ensure_memory_tables(conn)
        conn.execute(
            "INSERT INTO agent_sessions (session_id, agent_id, started_at, agent_personality) "
            "VALUES (?,?,?,?)",
            ("s1", "alice", "2026-01-01T00:00:00+00:00", _VALID_PERSONALITY_JSON),
        )

    mock_tick_result = MagicMock()
    mock_tick_result.kind = "ok"
    mock_tick_result.observation = "you see the room"
    mock_tick_result.tick_id = "1"
    mock_tick_result.yield_signal = None

    with (
        patch("token_world.cli.UniverseManager") as MockMgr,
        patch("token_world.cli.KnowledgeGraph") as MockKG,
        patch("token_world.cli.anthropic"),
        patch("token_world.cli.SimulationEngine") as MockEngine,
        patch("token_world.cli.ResidentAgent") as MockAgent,
    ):
        MockMgr.return_value.load.return_value = universe_dir
        MockKG.return_value = MagicMock()
        MockEngine.return_value.run_tick.return_value = mock_tick_result
        MockAgent.return_value.run_turn.return_value = "look around"

        runner = CliRunner()
        result = runner.invoke(cli, ["agent-turn", "test-universe"])

    assert result.exit_code == 0, result.output

    # Verify the memory row was written
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT agent_id, action_text, observation_text, turn_number "
            "FROM agent_memory WHERE session_id = 's1'"
        ).fetchone()

    assert row is not None
    assert row[0] == "alice"
    assert row[1] == "look around"
    assert row[2] == "you see the room"
    assert row[3] == 0  # first turn
