"""Tests for SessionManager with fork/restore via graph snapshot (Task 3 TDD)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from token_world.graph import KnowledgeGraph
from token_world.resident.personality import PersonalityBundle
from token_world.resident.session import SessionManager

_BUNDLE = PersonalityBundle(
    name="Elara",
    archetype="wanderer",
    traits=["brave", "curious", "kind"],
    backstory="She roams the world.",
    speech_style="speaks in clipped sentences",
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "universe.db"


@pytest.fixture
def sessions(db_path: Path) -> SessionManager:
    return SessionManager(db_path)


def test_create_session_inserts_row_with_new_uuid(sessions: SessionManager, db_path: Path) -> None:
    """create_session returns a UUID string and inserts the session row."""
    session_id = sessions.create_session(agent_id="alice", personality=_BUNDLE)

    assert isinstance(session_id, str)
    assert len(session_id) == 36  # UUID4 format

    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT session_id, agent_id, forked_from_session_id, snapshot_id, agent_personality "
            "FROM agent_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == session_id
    assert row[1] == "alice"
    assert row[2] is None  # forked_from_session_id
    assert row[3] is None  # snapshot_id

    # agent_personality should be valid JSON matching the bundle
    import json

    personality_data = json.loads(row[4])
    assert personality_data["name"] == "Elara"


def test_fork_session_calls_graph_snapshot_and_links(
    sessions: SessionManager, db_path: Path
) -> None:
    """fork_session calls graph.snapshot and creates a linked session row."""
    # Create parent session
    parent_id = sessions.create_session(agent_id="alice", personality=_BUNDLE)

    # Mock KnowledgeGraph
    mock_graph = MagicMock(spec=KnowledgeGraph)
    mock_graph.current_tick = 5
    mock_graph.snapshot.return_value = 42

    new_id = sessions.fork_session(parent_session_id=parent_id, graph=mock_graph)

    assert isinstance(new_id, str)
    assert new_id != parent_id

    # Verify snapshot was called with current_tick and a summary mentioning parent_id
    mock_graph.snapshot.assert_called_once()
    call_args = mock_graph.snapshot.call_args
    assert call_args[0][0] == 5  # tick_id
    assert parent_id in call_args[1]["summary"]

    # Verify the new session row
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT forked_from_session_id, snapshot_id FROM agent_sessions WHERE session_id = ?",
            (new_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == parent_id
    assert row[1] == 42


def test_restore_session_calls_graph_restore_when_snapshot_present(
    sessions: SessionManager, db_path: Path
) -> None:
    """restore_session delegates to graph.restore when snapshot_id is present."""
    # Create a session with snapshot_id=42
    session_id = sessions.create_session(agent_id="alice", personality=_BUNDLE)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE agent_sessions SET snapshot_id = 42 WHERE session_id = ?",
            (session_id,),
        )

    mock_graph = MagicMock(spec=KnowledgeGraph)
    sessions.restore_session(session_id, graph=mock_graph)
    mock_graph.restore.assert_called_once_with(42)

    # Without snapshot_id → no call
    session_id2 = sessions.create_session(agent_id="bob", personality=_BUNDLE)
    mock_graph2 = MagicMock(spec=KnowledgeGraph)
    sessions.restore_session(session_id2, graph=mock_graph2)
    mock_graph2.restore.assert_not_called()


def test_get_session_returns_row_as_dict(sessions: SessionManager, db_path: Path) -> None:
    """get_session returns a dict with expected keys; None if not found."""
    session_id = sessions.create_session(agent_id="alice", personality=_BUNDLE)

    row = sessions.get_session(session_id)
    assert row is not None
    assert row["session_id"] == session_id
    assert row["agent_id"] == "alice"
    assert "started_at" in row
    assert "forked_from_session_id" in row
    assert "snapshot_id" in row
    assert "memory_summary" in row
    assert "agent_personality" in row

    assert sessions.get_session("nonexistent-id") is None


def test_list_sessions_for_agent_returns_all(sessions: SessionManager, db_path: Path) -> None:
    """list_sessions returns all session_ids for the given agent."""
    ids = [sessions.create_session(agent_id="alice", personality=_BUNDLE) for _ in range(3)]
    sessions.create_session(agent_id="bob", personality=_BUNDLE)

    alice_sessions = sessions.list_sessions("alice")
    assert len(alice_sessions) == 3
    for sid in ids:
        assert sid in alice_sessions


def test_fork_from_real_graph_preserves_state(tmp_path: Path) -> None:
    """Integration: fork session then restore returns graph to fork-point state."""
    db_path = tmp_path / "universe.db"
    kg = KnowledgeGraph(db_path=db_path)
    kg.add_node("item_a", node_type="entity", color="red")
    kg.save()

    sessions = SessionManager(db_path)
    parent_id = sessions.create_session(agent_id="alice", personality=_BUNDLE)

    # Fork at this point (color="red")
    fork_id = sessions.fork_session(parent_session_id=parent_id, graph=kg)

    # Mutate graph after fork
    kg.set("item_a", "color", "blue")
    assert kg.query("item_a")["color"] == "blue"

    # Restore fork → should revert to "red"
    sessions.restore_session(fork_id, graph=kg)
    assert kg.query("item_a")["color"] == "red"
