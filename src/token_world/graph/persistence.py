"""SQLite persistence adapter for the knowledge graph."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph

from token_world.graph.events import GraphEvent
from token_world.graph.models import SnapshotInfo


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
            CREATE INDEX IF NOT EXISTS idx_events_target ON graph_events(target_id, tick_id);
            CREATE INDEX IF NOT EXISTS idx_events_property ON graph_events(property_name, tick_id);

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

    def save_snapshot(
        self,
        graph: nx.DiGraph,
        tick_id: int,
        summary: str,
    ) -> int:
        """Save a graph snapshot to SQLite.

        Args:
            graph: The NetworkX DiGraph to snapshot.
            tick_id: The simulation tick this snapshot represents.
            summary: Human-readable summary of what changed.

        Returns:
            The snapshot_id of the new snapshot.
        """
        graph_json = json.dumps(
            json_graph.node_link_data(graph),
            ensure_ascii=False,
            allow_nan=False,
        )
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO graph_snapshots
                    (tick_id, summary, graph_json, node_count, edge_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    tick_id,
                    summary,
                    graph_json,
                    graph.number_of_nodes(),
                    graph.number_of_edges(),
                ),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def load_snapshot(self, snapshot_id: int) -> tuple[nx.DiGraph, int]:
        """Load a graph snapshot from SQLite.

        Args:
            snapshot_id: The snapshot to load.

        Returns:
            Tuple of (restored graph, tick_id).

        Raises:
            ValueError: If snapshot_id does not exist.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            row = conn.execute(
                "SELECT graph_json, tick_id FROM graph_snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"No snapshot with id {snapshot_id}")
            graph_json, tick_id = row
            graph = json_graph.node_link_graph(
                json.loads(graph_json),
                directed=True,
                multigraph=False,
            )
        return graph, tick_id

    def list_snapshots(self) -> list[SnapshotInfo]:
        """List all snapshots ordered by tick_id ascending.

        Returns:
            List of SnapshotInfo dataclass instances.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT snapshot_id, tick_id, summary, node_count, edge_count, created_at
                FROM graph_snapshots
                ORDER BY tick_id ASC
                """
            ).fetchall()
        return [
            SnapshotInfo(
                snapshot_id=r[0],
                tick_id=r[1],
                summary=r[2],
                node_count=r[3],
                edge_count=r[4],
                created_at=r[5],
            )
            for r in rows
        ]

    def prune_snapshots(self, max_count: int = 50) -> list[int]:
        """Prune oldest snapshots if count exceeds max_count.

        Args:
            max_count: Maximum number of snapshots to retain.

        Returns:
            List of deleted snapshot_ids.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            count = conn.execute("SELECT COUNT(*) FROM graph_snapshots").fetchone()[0]
            if count <= max_count:
                return []
            excess = count - max_count
            rows = conn.execute(
                "SELECT snapshot_id FROM graph_snapshots ORDER BY snapshot_id ASC LIMIT ?",
                (excess,),
            ).fetchall()
            deleted_ids = [r[0] for r in rows]
            placeholders = ",".join("?" * len(deleted_ids))
            conn.execute(
                f"DELETE FROM graph_snapshots WHERE snapshot_id IN ({placeholders})",
                deleted_ids,
            )
        return deleted_ids

    def delete_events_before(self, tick_id: int) -> int:
        """Delete events before the given tick_id.

        Args:
            tick_id: Delete events with tick_id strictly less than this.

        Returns:
            Number of deleted rows.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM graph_events WHERE tick_id < ?",
                (tick_id,),
            )
            return cursor.rowcount

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
