"""SessionManager — session registry for resident agents (D-06, D-08).

Manages agent_sessions rows in universe.db. Session forking uses the
existing graph snapshot mechanism (graph.snapshot / graph.restore).
Table creation is delegated to the shared ensure_memory_tables() helper
in memory.py to avoid DDL duplication.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from token_world.resident.memory import ensure_memory_tables
from token_world.resident.personality import PersonalityBundle

if TYPE_CHECKING:
    from token_world.graph import KnowledgeGraph


class SessionManager:
    """Session registry backed by the agent_sessions SQLite table (D-06, D-08).

    Methods:
        create_session: Start a new session for an agent.
        fork_session:   Fork an existing session via graph snapshot.
        restore_session: Restore graph state to the fork point.
        get_session:    Fetch a single session row as a dict.
        list_sessions:  List all session IDs for an agent.
        get_next_turn_number: Return the next turn number for a session.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _ensure_tables(self, conn: sqlite3.Connection) -> None:
        """Delegate to shared DDL helper."""
        ensure_memory_tables(conn)

    def create_session(
        self,
        agent_id: str,
        personality: PersonalityBundle,
    ) -> str:
        """Insert a new session row and return the session_id UUID (D-06).

        Args:
            agent_id: Graph node ID of the agent.
            personality: PersonalityBundle stored as JSON in agent_personality column.

        Returns:
            A fresh UUID4 string as the session_id.
        """
        session_id = str(uuid.uuid4())
        started_at = datetime.now(UTC).isoformat()
        personality_json = personality.model_dump_json()

        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            conn.execute(
                """
                INSERT INTO agent_sessions
                    (session_id, agent_id, started_at,
                     forked_from_session_id, snapshot_id,
                     memory_summary, agent_personality)
                VALUES (?, ?, ?, NULL, NULL, NULL, ?)
                """,
                (session_id, agent_id, started_at, personality_json),
            )
        return session_id

    def fork_session(
        self,
        parent_session_id: str,
        graph: KnowledgeGraph,
    ) -> str:
        """Fork a session using a graph snapshot (D-08).

        Calls graph.snapshot(current_tick, summary=...) to capture the
        current graph state, then inserts a new session row pointing at
        the parent and the snapshot_id.

        Args:
            parent_session_id: The session to fork from.
            graph: The KnowledgeGraph whose state is snapshotted.

        Returns:
            The new session_id for the forked session.

        Raises:
            KeyError: If the parent session does not exist.
        """
        parent = self.get_session(parent_session_id)
        if parent is None:
            raise KeyError(f"Parent session not found: {parent_session_id!r}")

        snapshot_id = graph.snapshot(
            graph.current_tick,
            summary=f"fork from {parent_session_id}",
        )

        new_session_id = str(uuid.uuid4())
        started_at = datetime.now(UTC).isoformat()

        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            conn.execute(
                """
                INSERT INTO agent_sessions
                    (session_id, agent_id, started_at,
                     forked_from_session_id, snapshot_id,
                     memory_summary, agent_personality)
                VALUES (?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    new_session_id,
                    parent["agent_id"],
                    started_at,
                    parent_session_id,
                    snapshot_id,
                    parent["agent_personality"],
                ),
            )
        return new_session_id

    def restore_session(
        self,
        session_id: str,
        graph: KnowledgeGraph,
    ) -> None:
        """Restore graph state to the fork point of the session (D-08).

        If the session has a snapshot_id, calls graph.restore(snapshot_id).
        If snapshot_id is None (fresh session), this is a no-op.
        """
        session = self.get_session(session_id)
        if session is None:
            return
        snapshot_id = session.get("snapshot_id")
        if snapshot_id is not None:
            graph.restore(snapshot_id)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Fetch a session row as a dict, or None if not found.

        Returns keys: session_id, agent_id, started_at, forked_from_session_id,
        snapshot_id, memory_summary, agent_personality.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            row = conn.execute(
                """
                SELECT session_id, agent_id, started_at,
                       forked_from_session_id, snapshot_id,
                       memory_summary, agent_personality
                FROM agent_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "session_id": row[0],
            "agent_id": row[1],
            "started_at": row[2],
            "forked_from_session_id": row[3],
            "snapshot_id": row[4],
            "memory_summary": row[5],
            "agent_personality": row[6],
        }

    def list_sessions(self, agent_id: str) -> list[str]:
        """List all session_ids for an agent, ordered chronologically by started_at."""
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT session_id FROM agent_sessions
                WHERE agent_id = ?
                ORDER BY started_at ASC
                """,
                (agent_id,),
            ).fetchall()
        return [r[0] for r in rows]

    def list_agents(self) -> list[str]:
        """Return a deduplicated list of all agent_ids that have sessions."""
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            rows = conn.execute(
                "SELECT DISTINCT agent_id FROM agent_sessions ORDER BY agent_id ASC"
            ).fetchall()
        return [r[0] for r in rows]

    def get_next_turn_number(self, session_id: str) -> int:
        """Return the next turn_number for a session (max existing + 1, or 0 if none)."""
        with sqlite3.connect(str(self._db_path)) as conn:
            ensure_memory_tables(conn)
            row = conn.execute(
                "SELECT MAX(turn_number) FROM agent_memory WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None or row[0] is None:
            return 0
        return int(row[0]) + 1
