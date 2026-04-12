"""Data models for graph mutations and snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ALLOWED_PROPERTY_TYPES = (str, int, float, bool, type(None), list, dict)
"""Types that can be stored as node/edge property values (JSON-serializable)."""


@dataclass(frozen=True)
class Mutation:
    """A single graph mutation. Immutable for safety.

    Attributes:
        type: One of "add_node", "add_edge", "set_property", "remove_node", "remove_edge".
        target: node_id or "src->dst" for edges.
        property: Property name for set_property, None otherwise.
        old_value: Previous value (None for add operations).
        new_value: New value (None for remove operations).
    """

    type: str
    target: str
    property: str | None
    old_value: Any
    new_value: Any


@dataclass(frozen=True)
class SnapshotInfo:
    """Summary information about a graph snapshot.

    Attributes:
        snapshot_id: Unique ID for this snapshot.
        tick_id: The tick this snapshot was taken at.
        summary: Human-readable summary of what happened.
        node_count: Number of nodes at snapshot time.
        edge_count: Number of edges at snapshot time.
        created_at: ISO timestamp of snapshot creation.
    """

    snapshot_id: int
    tick_id: int
    summary: str
    node_count: int
    edge_count: int
    created_at: str
