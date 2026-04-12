"""Graph event model and in-memory event storage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GraphEvent:
    """A single graph mutation event for the audit log.

    Attributes:
        tick_id: The simulation tick when this event occurred.
        event_type: One of "add_node", "add_edge", "set_property", "remove_node", "remove_edge".
        target_id: The node_id or "src->dst" for edges.
        property_name: Property name for set_property events, None otherwise.
        old_value_json: JSON-encoded previous value, or None.
        new_value_json: JSON-encoded new value, or None.
    """

    tick_id: int
    event_type: str
    target_id: str
    property_name: str | None
    old_value_json: str | None
    new_value_json: str | None


class EventStore:
    """In-memory store for graph mutation events."""

    def __init__(self) -> None:
        self._events: list[GraphEvent] = []

    def append(self, event: GraphEvent) -> None:
        """Add an event to the store."""
        self._events.append(event)

    def get_events(self, tick_id: int | None = None) -> list[GraphEvent]:
        """Get events, optionally filtered by tick_id."""
        if tick_id is None:
            return list(self._events)
        return [e for e in self._events if e.tick_id == tick_id]

    def clear_before(self, tick_id: int) -> None:
        """Remove all events before the given tick_id."""
        self._events = [e for e in self._events if e.tick_id >= tick_id]

    def clear(self) -> None:
        """Remove all events."""
        self._events.clear()

    def set_events(self, events: list[GraphEvent]) -> None:
        """Replace all events with the given list."""
        self._events = list(events)

    def __len__(self) -> int:
        return len(self._events)
