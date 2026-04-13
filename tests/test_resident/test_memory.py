"""Tests for AgentMemory SQLite adapter (Task 2 TDD)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tests.test_resident.conftest import MockAnthropicClient
from token_world.resident.memory import AgentMemory


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "universe.db"


@pytest.fixture
def memory(db_path: Path) -> AgentMemory:
    return AgentMemory(db_path)


def test_agent_memory_creates_tables_lazily(memory: AgentMemory, db_path: Path) -> None:
    """Tables are created on first use, not on instantiation."""
    # Before any method call, just the object exists — no table creation yet
    # (We can't easily verify the "before" state without opening the DB ourselves,
    # but we can verify that after a method call the tables exist.)
    memory.store_turn(
        agent_id="alice",
        session_id="s1",
        turn_number=0,
        action_text="look",
        observation_text="you see a room",
        tick_id="1",
    )
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {r[0] for r in rows}
    assert "agent_memory" in table_names
    assert "agent_sessions" in table_names


def test_store_turn_persists_row(memory: AgentMemory, db_path: Path) -> None:
    """store_turn inserts a row with correct values."""
    # agent_sessions row must exist for FK-like consistency (no FK enforced, but good practice)
    with sqlite3.connect(str(db_path)) as conn:
        memory._ensure_tables(conn)
        conn.execute(
            "INSERT INTO agent_sessions (session_id, agent_id, started_at) VALUES (?,?,?)",
            ("s1", "alice", "2026-01-01T00:00:00"),
        )

    memory.store_turn(
        agent_id="alice",
        session_id="s1",
        turn_number=0,
        action_text="look",
        observation_text="you see a room",
        tick_id="1",
    )

    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT agent_id, session_id, turn_number, action_text, observation_text, tick_id "
            "FROM agent_memory WHERE session_id='s1'"
        ).fetchone()
    assert row is not None
    assert row[0] == "alice"
    assert row[1] == "s1"
    assert row[2] == 0
    assert row[3] == "look"
    assert row[4] == "you see a room"
    assert row[5] == "1"


def test_get_context_returns_rolling_window_in_chronological_order(
    memory: AgentMemory, db_path: Path
) -> None:
    """get_context returns the last N turns in chronological order."""
    # Pre-create session
    with sqlite3.connect(str(db_path)) as conn:
        memory._ensure_tables(conn)
        conn.execute(
            "INSERT INTO agent_sessions (session_id, agent_id, started_at) VALUES (?,?,?)",
            ("s1", "alice", "2026-01-01T00:00:00"),
        )

    for i in range(12):
        memory.store_turn(
            agent_id="alice",
            session_id="s1",
            turn_number=i,
            action_text=f"action_{i}",
            observation_text=f"obs_{i}",
            tick_id=str(i),
        )

    turns, summary = memory.get_context("s1", window=10)

    # Should have exactly 10 turns (turns 2-11)
    assert len(turns) == 10
    # Chronological: first item is turn 2 (action_2), last is turn 11 (action_11)
    assert turns[0][0] == "action_2"
    assert turns[-1][0] == "action_11"


def test_get_context_returns_memory_summary(memory: AgentMemory, db_path: Path) -> None:
    """get_context returns the persisted memory_summary from agent_sessions."""
    with sqlite3.connect(str(db_path)) as conn:
        memory._ensure_tables(conn)
        conn.execute(
            "INSERT INTO agent_sessions (session_id, agent_id, started_at, memory_summary) "
            "VALUES (?,?,?,?)",
            ("s1", "alice", "2026-01-01T00:00:00", "Alice explored the forest."),
        )

    turns, summary = memory.get_context("s1")
    assert summary == "Alice explored the forest."


def test_maybe_compact_summary_triggers_haiku_every_10_turns(
    memory: AgentMemory, db_path: Path
) -> None:
    """maybe_compact_summary calls Haiku exactly once when turn count hits multiples of 10."""
    haiku_summary = "Alice found a key and met a trader."
    mock_client = MockAnthropicClient([haiku_summary])

    with sqlite3.connect(str(db_path)) as conn:
        memory._ensure_tables(conn)
        conn.execute(
            "INSERT INTO agent_sessions (session_id, agent_id, started_at) VALUES (?,?,?)",
            ("s1", "alice", "2026-01-01T00:00:00"),
        )

    # Store 10 turns
    for i in range(10):
        memory.store_turn("alice", "s1", i, f"act_{i}", f"obs_{i}", str(i))

    memory.maybe_compact_summary("s1", client=mock_client)

    assert len(mock_client.messages.calls) == 1

    # Verify summary was written to agent_sessions
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT memory_summary FROM agent_sessions WHERE session_id='s1'"
        ).fetchone()
    assert row is not None
    assert row[0] == haiku_summary

    # 9 more turns (total 19) → should NOT trigger again
    mock_client2 = MockAnthropicClient(["should not be called"])
    for i in range(10, 19):
        memory.store_turn("alice", "s1", i, f"act_{i}", f"obs_{i}", str(i))
    memory.maybe_compact_summary("s1", client=mock_client2)
    assert len(mock_client2.messages.calls) == 0


def test_store_turn_is_parameterized_and_safe_from_injection(
    memory: AgentMemory, db_path: Path
) -> None:
    """SQL injection in action_text is safely stored verbatim via parameterized query."""
    evil = "'; DROP TABLE agent_memory; --"
    with sqlite3.connect(str(db_path)) as conn:
        memory._ensure_tables(conn)
        conn.execute(
            "INSERT INTO agent_sessions (session_id, agent_id, started_at) VALUES (?,?,?)",
            ("s1", "alice", "2026-01-01T00:00:00"),
        )

    memory.store_turn("alice", "s1", 0, evil, "obs", "1")

    # Table still exists and row is stored verbatim
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT action_text FROM agent_memory WHERE session_id='s1'").fetchone()
    assert row is not None
    assert row[0] == evil


def test_indexes_exist_on_tables(memory: AgentMemory, db_path: Path) -> None:
    """Both required indexes exist after table creation."""
    memory.store_turn("alice", "s1", 0, "look", "obs", "1")  # trigger table creation

    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    index_names = {r[0] for r in rows}
    assert "idx_memory_session" in index_names
    assert "idx_memory_agent" in index_names
