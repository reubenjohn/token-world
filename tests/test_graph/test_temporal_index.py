"""Stubs for GRAPH-07 TemporalIndex."""

from __future__ import annotations

import pytest

temporal = pytest.importorskip("token_world.graph.temporal")


def test_query_history_returns_events_for_node(kg) -> None:
    kg.add_node("alice", node_type="agent")
    kg.set("alice", "hp", 100)
    idx = temporal.TemporalIndex(kg)
    events = idx.query_history("alice")
    assert len(events) >= 2  # add_node + set_property


def test_query_history_tick_range(kg) -> None:
    kg.add_node("alice", node_type="agent")
    kg.advance_tick()
    kg.set("alice", "hp", 50)
    idx = temporal.TemporalIndex(kg)
    events = idx.query_history("alice", tick_range=(1, 1))
    assert all(e.tick_id == 1 for e in events)


def test_query_changes_for_property(kg) -> None:
    kg.add_node("a", node_type="entity")
    kg.set("a", "temp", 20)
    kg.set("a", "temp", 22)
    idx = temporal.TemporalIndex(kg)
    changes = idx.query_changes("temp")
    assert len(changes) >= 2


def test_find_state_at_tick_reconstructs(kg) -> None:
    kg.add_node("a", node_type="entity")
    kg.set("a", "hp", 100)
    kg.advance_tick()
    kg.set("a", "hp", 50)
    idx = temporal.TemporalIndex(kg)
    state_at_0 = idx.find_state_at_tick("a", 0)
    assert state_at_0.get("hp") == 100


def test_out_of_range_raises(kg) -> None:
    kg.add_node("a", node_type="entity")
    idx = temporal.TemporalIndex(kg)
    with pytest.raises(temporal.TemporalQueryOutOfRange):
        idx.find_state_at_tick("a", -999)
