"""Direct tests for the CLI helper ``_load_or_create_agent``.

This helper is shared by ``token-world agent-turn`` and ``token-world playtest``
(see cli.py). End-to-end behavior is exercised by
``tests/test_resident/test_cli_agent_turn.py`` and
``tests/test_playtest/test_runner.py``; these tests lock the helper's
explicit-agent-id branch, which was folded in during the
``agent-turn``/``playtest`` dedup refactor.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from token_world.cli import _load_or_create_agent
from token_world.resident.memory import AgentMemory, ensure_memory_tables
from token_world.resident.session import SessionManager

_VALID_PERSONALITY_JSON = (
    '{"name":"Elara","archetype":"curious wanderer",'
    '"traits":["inquisitive","brave","kind"],'
    '"backstory":"She grew up exploring the misty caves.",'
    '"speech_style":"speaks in clipped sentences"}'
)


def _make_universe(tmp_path: Path) -> Path:
    universe_dir = tmp_path / "universes" / "test-universe"
    universe_dir.mkdir(parents=True)
    (universe_dir / "CLAUDE.md").write_text("# World rules\nThis is a test world.")
    (universe_dir / "universe.db").touch()
    return universe_dir


def _seed_session(db_path: Path, *, agent_id: str, session_id: str) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        ensure_memory_tables(conn)
        conn.execute(
            "INSERT INTO agent_sessions (session_id, agent_id, started_at, agent_personality) "
            "VALUES (?,?,?,?)",
            (session_id, agent_id, "2026-01-01T00:00:00+00:00", _VALID_PERSONALITY_JSON),
        )


def test_helper_explicit_agent_id_loads_existing_session(tmp_path: Path) -> None:
    """When agent_id is given and has sessions, helper returns that agent's most-recent session."""
    universe_dir = _make_universe(tmp_path)
    db_path = universe_dir / "universe.db"
    _seed_session(db_path, agent_id="alice", session_id="sess_1")

    memory = AgentMemory(db_path)
    sessions = SessionManager(db_path)
    client = MagicMock()

    kg = MagicMock()

    # Patch ResidentAgent to avoid constructing a real agent (no LLM call)
    with patch("token_world.cli.ResidentAgent") as MockAgent:
        MockAgent.return_value = MagicMock(name="ResidentAgentInstance")
        agent, agent_id_out, session_id_out = _load_or_create_agent(
            universe_dir,
            kg,
            memory,
            sessions,
            client,
            world_rules="# world",
            agent_id="alice",
        )

    assert agent_id_out == "alice"
    assert session_id_out == "sess_1"
    MockAgent.assert_called_once()
    # kg.claim_id must NOT have been called — no auto-create path
    kg.claim_id.assert_not_called()


def test_helper_explicit_agent_id_without_sessions_raises_lookup_error(tmp_path: Path) -> None:
    """When agent_id is given but has no sessions, helper raises LookupError."""
    universe_dir = _make_universe(tmp_path)
    db_path = universe_dir / "universe.db"
    # Ensure tables exist but DO NOT seed any sessions for this agent.
    with sqlite3.connect(str(db_path)) as conn:
        ensure_memory_tables(conn)

    memory = AgentMemory(db_path)
    sessions = SessionManager(db_path)
    client = MagicMock()
    kg = MagicMock()

    with pytest.raises(LookupError, match="nonexistent"):
        _load_or_create_agent(
            universe_dir,
            kg,
            memory,
            sessions,
            client,
            world_rules="# world",
            agent_id="nonexistent",
        )


def test_helper_no_agent_id_auto_creates_when_universe_is_empty(tmp_path: Path) -> None:
    """agent_id=None + no existing sessions -> auto-create via PersonalityGenerator."""
    universe_dir = _make_universe(tmp_path)
    db_path = universe_dir / "universe.db"
    with sqlite3.connect(str(db_path)) as conn:
        ensure_memory_tables(conn)

    memory = AgentMemory(db_path)
    sessions = SessionManager(db_path)
    client = MagicMock()

    kg = MagicMock()
    kg.claim_id.return_value = "resident_new"
    # PersonalityBundle validation needs a plausible dict
    kg.query.return_value = {}

    fake_personality = MagicMock()
    fake_personality.model_dump_json.return_value = _VALID_PERSONALITY_JSON

    with (
        patch("token_world.cli.PersonalityGenerator") as MockGen,
        patch("token_world.cli.create_agent_node") as mock_create_node,
        patch("token_world.cli.ResidentAgent") as MockAgent,
    ):
        MockGen.return_value.generate.return_value = fake_personality
        MockAgent.return_value = MagicMock()
        agent, agent_id_out, session_id_out = _load_or_create_agent(
            universe_dir,
            kg,
            memory,
            sessions,
            client,
            world_rules="# world rules first line\nsecond",
            agent_id=None,
        )

    assert agent_id_out == "resident_new"
    assert isinstance(session_id_out, str) and session_id_out
    MockGen.return_value.generate.assert_called_once()
    mock_create_node.assert_called_once_with(kg, "resident_new", fake_personality)


def test_helper_no_agent_id_reuses_most_recent_session(tmp_path: Path) -> None:
    """agent_id=None + existing agent -> reuse most-recent session, skip generation."""
    universe_dir = _make_universe(tmp_path)
    db_path = universe_dir / "universe.db"
    _seed_session(db_path, agent_id="bob", session_id="sess_old")
    _seed_session(db_path, agent_id="bob", session_id="sess_newest")

    memory = AgentMemory(db_path)
    sessions = SessionManager(db_path)
    client = MagicMock()
    kg = MagicMock()

    with (
        patch("token_world.cli.PersonalityGenerator") as MockGen,
        patch("token_world.cli.ResidentAgent") as MockAgent,
    ):
        MockAgent.return_value = MagicMock()
        agent, agent_id_out, session_id_out = _load_or_create_agent(
            universe_dir,
            kg,
            memory,
            sessions,
            client,
            world_rules="# world",
            agent_id=None,
        )

    assert agent_id_out == "bob"
    # Most-recent = last inserted
    assert session_id_out == "sess_newest"
    # Personality generation must be skipped on the fast path
    MockGen.return_value.generate.assert_not_called()
    kg.claim_id.assert_not_called()
