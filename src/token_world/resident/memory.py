"""AgentMemory — SQLite-backed memory adapter for resident agents (D-05, D-06, D-07).

Two tables in universe.db:
  - agent_memory: per-turn action/observation pairs
  - agent_sessions: session registry with rolling memory summary

Both are created lazily on first use (CREATE TABLE IF NOT EXISTS pattern
matching graph/persistence.py convention).
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# DDL helpers (shared with session.py via this module)
# ---------------------------------------------------------------------------

_CREATE_AGENT_MEMORY_SQL = """
CREATE TABLE IF NOT EXISTS agent_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    action_text TEXT NOT NULL,
    observation_text TEXT NOT NULL,
    timestamp_iso TEXT NOT NULL,
    tick_id TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_session
    ON agent_memory(session_id, turn_number);

CREATE INDEX IF NOT EXISTS idx_memory_agent
    ON agent_memory(agent_id, session_id);
"""

_CREATE_AGENT_SESSIONS_SQL = """
CREATE TABLE IF NOT EXISTS agent_sessions (
    session_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    forked_from_session_id TEXT,
    snapshot_id INTEGER,
    memory_summary TEXT,
    agent_personality TEXT
);
"""

_D27_SUMMARY_PROMPT = (
    "Summarize this character's recent experiences as a compact first-person narrative. "
    "Focus on discoveries, inventory changes, and relationships. "
    "Include any important facts the character should remember (items found, people met, "
    "places visited). Be concise (2-4 sentences). "
    "Write as if the character is recalling their own memories.\n\n"
    "Recent turns:\n{turns_text}"
)


def ensure_memory_tables(conn: sqlite3.Connection) -> None:
    """Create agent_memory and agent_sessions tables if they don't exist.

    Idempotent — uses CREATE TABLE IF NOT EXISTS. Called at the top of
    every public method in AgentMemory and SessionManager.
    """
    conn.executescript(_CREATE_AGENT_MEMORY_SQL)
    conn.executescript(_CREATE_AGENT_SESSIONS_SQL)


# ---------------------------------------------------------------------------
# AgentMemory
# ---------------------------------------------------------------------------


class AgentMemory:
    """SQLite adapter for agent turn memory (D-05, D-06, D-07).

    Lazy table creation on first use. Raw sqlite3 with parameterized queries.
    No ORM. Context manager pattern: ``with sqlite3.connect(str(path)) as conn:``.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _ensure_tables(self, conn: sqlite3.Connection) -> None:
        """Delegate to module-level helper so SessionManager can reuse."""
        ensure_memory_tables(conn)

    def store_turn(
        self,
        agent_id: str,
        session_id: str,
        turn_number: int,
        action_text: str,
        observation_text: str,
        tick_id: str,
    ) -> None:
        """Insert one turn row into agent_memory."""
        timestamp = datetime.now(UTC).isoformat()
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            conn.execute(
                """
                INSERT INTO agent_memory
                    (agent_id, session_id, turn_number, action_text,
                     observation_text, timestamp_iso, tick_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent_id,
                    session_id,
                    turn_number,
                    action_text,
                    observation_text,
                    timestamp,
                    tick_id,
                ),
            )

    def get_context(
        self,
        session_id: str,
        window: int = 10,
    ) -> tuple[list[tuple[str, str]], str]:
        """Return the last ``window`` turns (chronological) plus the memory summary.

        Returns:
            Tuple of (turns, memory_summary):
              - turns: list of (action_text, observation_text) in chronological order
              - memory_summary: the persisted summary string, or "" if none
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)

            # Fetch last `window` turns ordered by turn_number DESC, then reverse
            rows = conn.execute(
                """
                SELECT action_text, observation_text
                FROM agent_memory
                WHERE session_id = ?
                ORDER BY turn_number DESC
                LIMIT ?
                """,
                (session_id, window),
            ).fetchall()
            # Reverse to get chronological order (oldest first)
            turns = [(r[0], r[1]) for r in reversed(rows)]

            # Fetch memory summary from session
            row = conn.execute(
                "SELECT memory_summary FROM agent_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            summary = (row[0] or "") if row and row[0] else ""

        return turns, summary

    def maybe_compact_summary(
        self,
        session_id: str,
        client: Any,
        model: str = "claude-haiku-4-5",
    ) -> None:
        """Regenerate the memory summary via Haiku at every 10-turn boundary (D-07, D-27).

        Called after every store_turn. Only invokes the LLM when total rows
        for session is a positive multiple of 10.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)

            count_row = conn.execute(
                "SELECT COUNT(*) FROM agent_memory WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            count = count_row[0] if count_row else 0

            if count == 0 or count % 10 != 0:
                return

            # Fetch all turns for prompt construction
            rows = conn.execute(
                """
                SELECT turn_number, action_text, observation_text
                FROM agent_memory
                WHERE session_id = ?
                ORDER BY turn_number ASC
                """,
                (session_id,),
            ).fetchall()

        turns_text = "\n".join(f"Turn {r[0]}: Action: {r[1]} | Observation: {r[2]}" for r in rows)
        prompt = _D27_SUMMARY_PROMPT.format(turns_text=turns_text)

        response = client.messages.create(
            model=model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content
        if not content:
            raise ValueError("LLM returned empty response in maybe_compact_summary()")
        new_summary = str(content[0].text).strip()

        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            conn.execute(
                "UPDATE agent_sessions SET memory_summary = ? WHERE session_id = ?",
                (new_summary, session_id),
            )
