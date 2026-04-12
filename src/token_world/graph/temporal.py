"""Temporal query facade over EventStore + graph_events SQLite table.

Read-only. Derived view — never a source of truth. Queries combine the
in-memory session :class:`~token_world.graph.events.EventStore` with the
persisted ``graph_events`` SQLite table so mechanics can reason about
history that predates the current process.

No new storage: this module owns no tables, only reads existing ones.

Security (T-03-03): every SQL statement uses ``?`` placeholders; ``where``
fragments are static strings. No f-string SQL anywhere.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

from token_world.graph.events import GraphEvent

if TYPE_CHECKING:
    from token_world.graph.knowledge_graph import KnowledgeGraph


class TemporalQueryOutOfRange(Exception):
    """Raised when a temporal query asks for state before reachable history.

    "Reachable" means: before the oldest retained snapshot AND before any
    retained ``add_node`` event for the node. Event compaction (linked to
    snapshot retention) may prune older events, so very old ticks become
    unreconstructable.
    """


class TemporalIndex:
    """Read-only temporal query facade over the graph event log.

    Combines in-memory EventStore (this session) with the persisted
    ``graph_events`` SQLite table (prior sessions). Owns no storage.

    Args:
        graph: KnowledgeGraph to query. Internal attributes ``_events`` and
            ``_db_path`` are accessed by design — Phase 1 has not yet
            exposed public accessors for them. Migrate when it does.
    """

    def __init__(self, graph: KnowledgeGraph) -> None:
        self._graph = graph

    # --- public query API ---

    def query_history(
        self,
        node_id: str,
        *,
        tick_range: tuple[int, int] | None = None,
    ) -> list[GraphEvent]:
        """All events targeting ``node_id``, ordered by tick_id ascending.

        Args:
            node_id: Target to filter by (matches ``event.target_id``).
            tick_range: Optional inclusive ``(lo, hi)`` tick bounds.
        """
        mem = [e for e in self._graph._events.get_events() if e.target_id == node_id]
        disk = self._query_disk(
            "target_id = ?",
            (node_id,),
            tick_range=tick_range,
        )
        merged = self._merge(mem, disk)
        if tick_range is not None:
            lo, hi = tick_range
            merged = [e for e in merged if lo <= e.tick_id <= hi]
        return merged

    def query_changes(
        self,
        property_name: str,
        *,
        tick_range: tuple[int, int] | None = None,
        node_id: str | None = None,
    ) -> list[GraphEvent]:
        """All ``set_property`` events for ``property_name``.

        Args:
            property_name: Property to filter by.
            tick_range: Optional inclusive ``(lo, hi)`` tick bounds.
            node_id: Optional restrict to a single node.
        """
        mem = [
            e
            for e in self._graph._events.get_events()
            if e.event_type == "set_property"
            and e.property_name == property_name
            and (node_id is None or e.target_id == node_id)
        ]
        where = "event_type = 'set_property' AND property_name = ?"
        params: tuple[Any, ...] = (property_name,)
        if node_id is not None:
            where += " AND target_id = ?"
            params = (*params, node_id)
        disk = self._query_disk(where, params, tick_range=tick_range)
        merged = self._merge(mem, disk)
        if tick_range is not None:
            lo, hi = tick_range
            merged = [e for e in merged if lo <= e.tick_id <= hi]
        return merged

    def last_change(self, node_id: str, property_name: str) -> GraphEvent | None:
        """Most recent ``set_property`` event for ``(node_id, property_name)``.

        Returns None if the pair has no recorded change.
        """
        events = self.query_changes(property_name, node_id=node_id)
        return events[-1] if events else None

    def find_state_at_tick(self, node_id: str, tick_id: int) -> dict[str, Any]:
        """Reconstruct ``node_id``'s property dict as of end of ``tick_id``.

        Strategy:
          1. Find most recent snapshot at or before ``tick_id``.
          2. If none and the add_node event is also out of reach, raise
             :class:`TemporalQueryOutOfRange`.
          3. Replay ``set_property`` events from snapshot tick (exclusive)
             up through ``tick_id`` (inclusive).

        Args:
            node_id: Node to reconstruct.
            tick_id: Target tick (inclusive).

        Returns:
            Property dict as it was at end of ``tick_id``. Empty dict if the
            node was removed by that tick.

        Raises:
            TemporalQueryOutOfRange: If ``tick_id`` is before any reachable
                snapshot or add_node event (compacted history).
        """
        if tick_id < 0:
            raise TemporalQueryOutOfRange(f"tick_id must be non-negative, got {tick_id}")

        base_state, base_tick = self._load_baseline(node_id, tick_id)
        history = self.query_history(node_id, tick_range=(base_tick + 1, tick_id))
        state = dict(base_state)
        for e in history:
            if e.event_type == "set_property" and e.property_name:
                state[e.property_name] = (
                    json.loads(e.new_value_json) if e.new_value_json is not None else None
                )
            elif e.event_type == "remove_node":
                state = {}
        return state

    # --- internals ---

    def _load_baseline(self, node_id: str, tick_id: int) -> tuple[dict[str, Any], int]:
        """Return ``(state_dict, base_tick)`` for ``node_id`` as of some tick <= tick_id."""
        db_path = getattr(self._graph, "_db_path", None)
        if db_path is None:
            add_event = self._first_add_event(node_id)
            if add_event is None or add_event.tick_id > tick_id:
                raise TemporalQueryOutOfRange(f"node {node_id!r} did not exist at tick {tick_id}")
            return ({}, add_event.tick_id - 1)

        try:
            with sqlite3.connect(str(db_path)) as conn:
                row = conn.execute(
                    "SELECT tick_id, graph_json FROM graph_snapshots "
                    "WHERE tick_id <= ? ORDER BY tick_id DESC LIMIT 1",
                    (tick_id,),
                ).fetchone()
        except sqlite3.OperationalError:
            # graph_snapshots table hasn't been created yet (no save/snapshot run).
            row = None

        if row is not None:
            base_tick, graph_json = row
            from networkx.readwrite import json_graph

            data = json.loads(graph_json)
            g = json_graph.node_link_graph(data, directed=True, multigraph=False)
            if not g.has_node(node_id):
                add = self._first_add_event(node_id, tick_upper=tick_id)
                if add is None:
                    raise TemporalQueryOutOfRange(
                        f"node {node_id!r} not in snapshot at tick "
                        f"{base_tick} and no add_node found up to {tick_id}"
                    )
                return ({}, add.tick_id - 1)
            props = dict(g.nodes[node_id])
            return (props, base_tick)

        # No snapshot at or before tick_id — fall back to add_node event.
        add_event = self._first_add_event(node_id, tick_upper=tick_id)
        if add_event is None:
            raise TemporalQueryOutOfRange(
                f"no snapshot at or before tick {tick_id} and no "
                f"add_node event for {node_id!r} is retained"
            )
        return ({}, add_event.tick_id - 1)

    def _first_add_event(self, node_id: str, tick_upper: int | None = None) -> GraphEvent | None:
        """Earliest ``add_node`` event for ``node_id``, bounded above by tick_upper."""
        candidates = [e for e in self.query_history(node_id) if e.event_type == "add_node"]
        if tick_upper is not None:
            candidates = [e for e in candidates if e.tick_id <= tick_upper]
        return candidates[0] if candidates else None

    def _query_disk(
        self,
        where: str,
        params: tuple[Any, ...],
        *,
        tick_range: tuple[int, int] | None,
    ) -> list[GraphEvent]:
        """Run a parameterized SELECT against graph_events; ``where`` is static.

        Every call goes through ``conn.execute(sql, params)`` with ``?``
        placeholders (T-03-03 mitigation).
        """
        db_path = getattr(self._graph, "_db_path", None)
        if db_path is None:
            return []
        sql = (
            "SELECT tick_id, event_type, target_id, property_name, "
            "old_value_json, new_value_json "
            "FROM graph_events WHERE " + where
        )
        full_params: tuple[Any, ...] = params
        if tick_range is not None:
            sql += " AND tick_id BETWEEN ? AND ?"
            full_params = (*params, tick_range[0], tick_range[1])
        sql += " ORDER BY tick_id ASC, event_id ASC"
        try:
            with sqlite3.connect(str(db_path)) as conn:
                rows = conn.execute(sql, full_params).fetchall()
        except sqlite3.OperationalError:
            # Table not yet created (no save() has run against this db_path).
            return []
        return [
            GraphEvent(
                tick_id=r[0],
                event_type=r[1],
                target_id=r[2],
                property_name=r[3],
                old_value_json=r[4],
                new_value_json=r[5],
            )
            for r in rows
        ]

    @staticmethod
    def _merge(mem: list[GraphEvent], disk: list[GraphEvent]) -> list[GraphEvent]:
        """Union of mem+disk events deduped on (tick, type, target, prop, new_value)."""
        seen = {
            (e.tick_id, e.event_type, e.target_id, e.property_name, e.new_value_json) for e in disk
        }
        extra = [
            e
            for e in mem
            if (e.tick_id, e.event_type, e.target_id, e.property_name, e.new_value_json) not in seen
        ]
        return sorted(disk + extra, key=lambda e: e.tick_id)
