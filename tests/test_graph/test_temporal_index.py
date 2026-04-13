"""Tests for GRAPH-07 TemporalIndex."""

from __future__ import annotations

import sqlite3

import pytest

from token_world.graph.knowledge_graph import KnowledgeGraph
from token_world.graph.temporal import TemporalIndex, TemporalQueryOutOfRange


def test_query_history_returns_events_for_node(kg) -> None:
    kg.add_node("alice", node_type="agent")
    kg.set("alice", "hp", 100)
    idx = TemporalIndex(kg)
    events = idx.query_history("alice")
    assert len(events) >= 2  # add_node + set_property
    assert all(e.target_id == "alice" for e in events)


def test_query_history_tick_range(kg) -> None:
    kg.add_node("alice", node_type="agent")  # tick 0
    kg.set_tick(1)
    kg.set("alice", "hp", 50)  # tick 1
    idx = TemporalIndex(kg)
    events = idx.query_history("alice", tick_range=(1, 1))
    assert len(events) >= 1
    assert all(e.tick_id == 1 for e in events)


def test_query_changes_for_property(kg) -> None:
    kg.add_node("a", node_type="entity")
    kg.set("a", "temp", 20)
    kg.set("a", "temp", 22)
    idx = TemporalIndex(kg)
    changes = idx.query_changes("temp")
    assert len(changes) >= 2
    assert all(e.event_type == "set_property" and e.property_name == "temp" for e in changes)


def test_find_state_at_tick_reconstructs(kg) -> None:
    kg.add_node("a", node_type="entity")
    kg.set("a", "hp", 100)  # tick 0
    kg.set_tick(1)
    kg.set("a", "hp", 50)  # tick 1
    idx = TemporalIndex(kg)
    state_at_0 = idx.find_state_at_tick("a", 0)
    assert state_at_0.get("hp") == 100


def test_find_state_at_tick_remove_then_readd_clears_stale_props(kg) -> None:
    # REVIEW H-01 regression: add_node after remove_node must reset state to {}
    # so stale pre-remove properties don't leak into the re-added node's state.
    kg.add_node("item", node_type="entity")
    kg.set("item", "owner", "alice")  # tick 0
    kg.set_tick(1)
    kg.remove_node("item")  # tick 1 — pickup cycle step 1
    kg.set_tick(2)
    kg.add_node("item", node_type="entity")  # tick 2 — pickup cycle step 2 (fresh state)
    idx = TemporalIndex(kg)
    state_at_2 = idx.find_state_at_tick("item", 2)
    assert "owner" not in state_at_2, f"expected fresh state after re-add, got {state_at_2}"


def test_find_state_at_tick_readd_with_initial_props_seeds_state(kg) -> None:
    # REVIEW H-01 regression: when a node is re-added with initial properties
    # inside the add_node event itself, find_state_at_tick must seed state from
    # that event's new_value_json — not silently drop the payload.
    kg.add_node("item", node_type="entity", weight=5)
    kg.set("item", "owner", "alice")  # tick 0
    kg.set_tick(1)
    kg.remove_node("item")
    kg.set_tick(2)
    # Re-add with a fresh set of initial props baked into add_node
    kg.add_node("item", node_type="entity", weight=10, fresh=True)
    idx = TemporalIndex(kg)
    state_at_2 = idx.find_state_at_tick("item", 2)
    assert state_at_2.get("weight") == 10, f"expected weight=10, got {state_at_2}"
    assert state_at_2.get("fresh") is True, f"expected fresh=True, got {state_at_2}"
    assert "owner" not in state_at_2, f"stale owner leaked: {state_at_2}"


def test_find_state_at_tick_handles_remove_then_readd(kg) -> None:
    """H-01 regression (Pitfall 7): after add_node, subsequent set_property
    events must refine the state seeded from add_node's payload — they must
    NOT be masked by the ``state = {}`` reset that predated the H-01 fix.
    """
    kg.add_node("apple", node_type="entity", color="red", weight=1)  # tick 0
    kg.set_tick(1)
    kg.remove_node("apple")  # tick 1
    kg.set_tick(2)
    kg.add_node("apple", node_type="entity", color="green", weight=2)  # tick 2
    kg.set("apple", "weight", 3)  # tick 2 (refines the re-add)
    idx = TemporalIndex(kg)
    state = idx.find_state_at_tick("apple", 2)
    assert state.get("color") == "green", state
    assert state.get("weight") == 3, state  # refined after add_node, not reset


def test_out_of_range_raises(kg) -> None:
    kg.add_node("a", node_type="entity")
    idx = TemporalIndex(kg)
    with pytest.raises(TemporalQueryOutOfRange):
        idx.find_state_at_tick("a", -999)


def test_query_changes_node_id_filter(kg) -> None:
    """query_changes(property, node_id=X) returns only X's events."""
    kg.add_node("a", node_type="entity")
    kg.add_node("b", node_type="entity")
    kg.set("a", "hp", 10)
    kg.set("b", "hp", 20)
    kg.set("a", "hp", 30)

    idx = TemporalIndex(kg)
    a_changes = idx.query_changes("hp", node_id="a")
    assert all(e.target_id == "a" for e in a_changes)
    assert len(a_changes) == 2


def test_last_change_returns_none_when_absent(kg) -> None:
    """last_change for a nonexistent (node, property) pair is None."""
    idx = TemporalIndex(kg)
    assert idx.last_change("ghost", "whatever") is None


def test_last_change_returns_most_recent(kg) -> None:
    """last_change returns the most recent set_property event."""
    kg.add_node("a", node_type="entity")
    kg.set("a", "hp", 100)
    kg.set_tick(5)
    kg.set("a", "hp", 50)
    idx = TemporalIndex(kg)
    last = idx.last_change("a", "hp")
    assert last is not None
    assert last.tick_id == 5


def test_find_state_at_tick_uses_snapshot(kg) -> None:
    """Snapshot provides baseline; later set_property replays on top."""
    kg.add_node("a", node_type="entity")
    kg.set("a", "hp", 100)  # tick 0
    # Snapshot at tick 2 — state is {type: 'entity', hp: 100}
    kg.snapshot(2, summary="after hp=100")
    kg.set_tick(3)
    kg.set("a", "hp", 50)

    idx = TemporalIndex(kg)
    # State as of end of tick 2 — snapshot value, before the tick-3 set
    state = idx.find_state_at_tick("a", 2)
    assert state.get("hp") == 100


def test_query_history_merges_mem_and_disk(tmp_path) -> None:
    """After save+reopen, temporal query sees both persisted and fresh events."""
    db = tmp_path / "t.db"
    kg1 = KnowledgeGraph(db_path=db)
    kg1.add_node("a", node_type="entity")
    kg1.set("a", "hp", 100)
    kg1.save()  # events flushed to disk

    # Reopen — session EventStore is empty until load()
    kg2 = KnowledgeGraph(db_path=db)
    kg2.load()
    kg2.set_tick(1)
    kg2.set("a", "hp", 50)  # fresh session event

    idx = TemporalIndex(kg2)
    events = idx.query_history("a")
    # Expect the original add_node + set (hp=100) from disk, plus the fresh set
    assert len(events) >= 3
    hp_events = [e for e in events if e.property_name == "hp"]
    assert len(hp_events) == 2


def test_parameterized_queries_no_injection(tmp_path) -> None:
    """SQL injection attempt via node_id must not affect the DB."""
    db = tmp_path / "t.db"
    kg = KnowledgeGraph(db_path=db)
    kg.add_node("safe", node_type="entity")
    kg.save()

    idx = TemporalIndex(kg)
    # Malicious node_id — should return [] (no matching target_id) and NOT
    # drop or alter the graph_events table.
    result = idx.query_history("alice'; DROP TABLE graph_events; --")
    assert result == []

    # Verify graph_events table still exists
    with sqlite3.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='graph_events'"
        ).fetchone()
        assert row is not None
