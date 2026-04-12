"""SQLite persistence adapter for the knowledge graph."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph

from token_world.graph.events import GraphEvent


class GraphPersistence:
    """Persist graph state and events to SQLite.

    Tables are created lazily on first save(), not on __init__.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._tables_created = False

    def _ensure_tables(self, conn: sqlite3.Connection) -> None:
        """Create tables if they don't exist."""
        if self._tables_created:
            return
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS graph_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                graph_json TEXT NOT NULL,
                current_tick INTEGER NOT NULL DEFAULT 0,
                node_count INTEGER NOT NULL DEFAULT 0,
                edge_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS graph_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                property_name TEXT,
                old_value_json TEXT,
                new_value_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_events_tick ON graph_events(tick_id);

            CREATE TABLE IF NOT EXISTS graph_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id INTEGER NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                graph_json TEXT NOT NULL,
                node_count INTEGER NOT NULL,
                edge_count INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(tick_id)
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_tick ON graph_snapshots(tick_id);
            """
        )
        self._tables_created = True

    def save(
        self,
        graph: nx.DiGraph,
        events: list[GraphEvent],
        current_tick: int,
    ) -> None:
        """Save graph state and events to SQLite.

        Serializes the full graph as a JSON blob and inserts/replaces the
        single graph_state row. New events are appended to graph_events.
        """
        graph_json = json.dumps(
            json_graph.node_link_data(graph),
            ensure_ascii=False,
            allow_nan=False,
        )

        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            conn.execute(
                """
                INSERT OR REPLACE INTO graph_state
                    (id, graph_json, current_tick, node_count, edge_count, updated_at)
                VALUES (1, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    graph_json,
                    current_tick,
                    graph.number_of_nodes(),
                    graph.number_of_edges(),
                ),
            )
            if events:
                conn.executemany(
                    """
                    INSERT INTO graph_events
                        (tick_id, event_type, target_id, property_name,
                         old_value_json, new_value_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            e.tick_id,
                            e.event_type,
                            e.target_id,
                            e.property_name,
                            e.old_value_json,
                            e.new_value_json,
                        )
                        for e in events
                    ],
                )

    def load(self) -> tuple[nx.DiGraph, list[GraphEvent], int]:
        """Load graph state and events from SQLite.

        Returns:
            Tuple of (graph, events, current_tick).

        Raises:
            ValueError: If no saved state exists.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            row = conn.execute(
                "SELECT graph_json, current_tick FROM graph_state WHERE id = 1"
            ).fetchone()
            if row is None:
                raise ValueError("No saved graph state found")

            graph_json, current_tick = row
            graph = json_graph.node_link_graph(
                json.loads(graph_json),
                directed=True,
                multigraph=False,
            )

            event_rows = conn.execute(
                """
                SELECT tick_id, event_type, target_id, property_name,
                       old_value_json, new_value_json
                FROM graph_events
                ORDER BY event_id ASC
                """
            ).fetchall()

            events = [
                GraphEvent(
                    tick_id=r[0],
                    event_type=r[1],
                    target_id=r[2],
                    property_name=r[3],
                    old_value_json=r[4],
                    new_value_json=r[5],
                )
                for r in event_rows
            ]

        return graph, events, current_tick

    def has_data(self) -> bool:
        """Check if the database has any saved graph state."""
        if not self._db_path.exists():
            return False
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                row = conn.execute("SELECT COUNT(*) FROM graph_state WHERE id = 1").fetchone()
                return row is not None and row[0] > 0
        except sqlite3.OperationalError:
            return False
