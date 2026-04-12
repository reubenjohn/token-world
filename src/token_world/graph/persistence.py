"""SQLite persistence adapter for the knowledge graph.

Stub module -- full implementation in Task 2.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import networkx as nx

from token_world.graph.events import GraphEvent


class GraphPersistence:
    """Persist graph state and events to SQLite."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _ensure_tables(self, conn: sqlite3.Connection) -> None:
        """Create tables if they don't exist."""
        raise NotImplementedError("Persistence not yet implemented")

    def save(
        self,
        graph: nx.DiGraph,
        events: list[GraphEvent],
        current_tick: int,
    ) -> None:
        """Save graph state and events to SQLite."""
        raise NotImplementedError("Persistence not yet implemented")

    def load(self) -> tuple[nx.DiGraph, list[GraphEvent], int]:
        """Load graph state and events from SQLite."""
        raise NotImplementedError("Persistence not yet implemented")

    def has_data(self) -> bool:
        """Check if the database has any saved graph state."""
        return False
