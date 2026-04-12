"""Tests for snapshot/restore functionality on KnowledgeGraph."""

from __future__ import annotations

from pathlib import Path

import pytest

from token_world.graph.knowledge_graph import KnowledgeGraph
from token_world.graph.models import SnapshotInfo
from tests.test_graph.conftest import GraphBuilder


# --- Snapshot creation tests ---


class TestSnapshotCreation:
    """Tests for taking snapshots."""

    def test_snapshot_creation(self, kg: KnowledgeGraph) -> None:
        """Snapshot at tick 5 returns a positive snapshot_id."""
        kg.add_node("a", node_type="entity")
        kg.set_tick(5)
        snap_id = kg.snapshot(tick_id=5, summary="test")
        assert isinstance(snap_id, int)
        assert snap_id > 0

    def test_snapshot_linked_to_tick(self, kg: KnowledgeGraph) -> None:
        """Snapshot at tick 5 has tick_id=5 in SnapshotInfo."""
        kg.add_node("a", node_type="entity")
        kg.set_tick(5)
        kg.snapshot(tick_id=5, summary="tick five")
        infos = kg.list_snapshots()
        assert len(infos) == 1
        assert infos[0].tick_id == 5

    def test_snapshot_with_summary(self, kg: KnowledgeGraph) -> None:
        """Snapshot stores summary string (D-06)."""
        kg.add_node("a", node_type="agent")
        snap_id = kg.snapshot(tick_id=1, summary="Bob found sword")
        infos = kg.list_snapshots()
        assert infos[0].summary == "Bob found sword"

    def test_snapshot_node_count(self, kg: KnowledgeGraph) -> None:
        """Snapshot records correct node_count."""
        kg.add_node("a", node_type="entity")
        kg.add_node("b", node_type="agent")
        kg.add_node("c", node_type="entity")
        kg.snapshot(tick_id=1, summary="three nodes")
        infos = kg.list_snapshots()
        assert infos[0].node_count == 3

    def test_snapshot_edge_count(self, kg: KnowledgeGraph) -> None:
        """Snapshot records correct edge_count."""
        kg.add_node("a", node_type="entity")
        kg.add_node("b", node_type="entity")
        kg.add_node("c", node_type="entity")
        kg.add_edge("a", "b", relation="near")
        kg.add_edge("b", "c", relation="near")
        kg.snapshot(tick_id=1, summary="two edges")
        infos = kg.list_snapshots()
        assert infos[0].edge_count == 2


class TestListSnapshots:
    """Tests for listing snapshots."""

    def test_list_snapshots(self, kg: KnowledgeGraph) -> None:
        """After 3 snapshots, list_snapshots returns 3 SnapshotInfo objects."""
        kg.add_node("a", node_type="entity")
        kg.snapshot(tick_id=1, summary="first")
        kg.snapshot(tick_id=2, summary="second")
        kg.snapshot(tick_id=3, summary="third")
        infos = kg.list_snapshots()
        assert len(infos) == 3
        assert all(isinstance(i, SnapshotInfo) for i in infos)

    def test_list_snapshots_ordered(self, kg: KnowledgeGraph) -> None:
        """Snapshots returned in chronological order by tick_id."""
        kg.add_node("a", node_type="entity")
        # Insert in non-sequential tick order
        kg.snapshot(tick_id=10, summary="ten")
        kg.snapshot(tick_id=3, summary="three")
        kg.snapshot(tick_id=7, summary="seven")
        infos = kg.list_snapshots()
        tick_ids = [i.tick_id for i in infos]
        assert tick_ids == sorted(tick_ids)

    def test_list_snapshots_no_persistence(self) -> None:
        """KnowledgeGraph without db_path returns empty list."""
        kg = KnowledgeGraph(db_path=None)
        assert kg.list_snapshots() == []


# --- Restore tests ---


class TestRestore:
    """Tests for restoring from snapshots."""

    def test_restore_basic(self, kg: KnowledgeGraph) -> None:
        """Snapshot -> mutate -> restore -> graph matches snapshot state."""
        kg.add_node("a", node_type="entity", hp=100)
        kg.set_tick(1)
        snap_id = kg.snapshot(tick_id=1, summary="baseline")
        # Mutate
        kg.set("a", "hp", 50)
        kg.add_node("b", node_type="entity")
        # Restore
        kg.restore(snap_id)
        assert kg.query("a", "hp") == 100

    def test_restore_nodes(self, kg: KnowledgeGraph) -> None:
        """After restore, only nodes from snapshot exist."""
        kg.add_node("a", node_type="entity")
        snap_id = kg.snapshot(tick_id=1, summary="one node")
        kg.add_node("b", node_type="entity")
        kg.add_node("c", node_type="entity")
        kg.restore(snap_id)
        assert kg.has_node("a")
        assert not kg.has_node("b")
        assert not kg.has_node("c")

    def test_restore_edges(self, kg: KnowledgeGraph) -> None:
        """After restore, only edges from snapshot exist."""
        kg.add_node("a", node_type="entity")
        kg.add_node("b", node_type="entity")
        kg.add_edge("a", "b", relation="friend")
        snap_id = kg.snapshot(tick_id=1, summary="one edge")
        kg.add_node("c", node_type="entity")
        kg.add_edge("a", "c", relation="enemy")
        kg.restore(snap_id)
        assert kg.has_edge("a", "b")
        assert not kg.has_node("c")

    def test_restore_properties(self, kg: KnowledgeGraph) -> None:
        """After restore, all node/edge properties match snapshot values."""
        kg.add_node("a", node_type="agent", hp=100, name="Alice")
        kg.add_node("b", node_type="entity", weight=5.5)
        kg.add_edge("a", "b", relation="holds", strength=3)
        snap_id = kg.snapshot(tick_id=1, summary="with props")
        # Mutate everything
        kg.set("a", "hp", 1)
        kg.set("a", "name", "Bob")
        kg.set("b", "weight", 999.9)
        kg.restore(snap_id)
        assert kg.query("a", "hp") == 100
        assert kg.query("a", "name") == "Alice"
        assert kg.query("b", "weight") == 5.5

    def test_restore_directed(self, kg: KnowledgeGraph) -> None:
        """After restore, edge direction preserved (A->B exists, B->A does not)."""
        kg.add_node("a", node_type="entity")
        kg.add_node("b", node_type="entity")
        kg.add_edge("a", "b", relation="points_to")
        snap_id = kg.snapshot(tick_id=1, summary="directed")
        # Add reverse edge before restore to ensure it doesn't persist
        kg.add_edge("b", "a", relation="reverse")
        kg.restore(snap_id)
        assert kg.has_edge("a", "b")
        assert not kg.has_edge("b", "a")

    def test_restore_resets_tick(self, kg: KnowledgeGraph) -> None:
        """After restore, current_tick set back to snapshot's tick_id."""
        kg.add_node("a", node_type="entity")
        kg.set_tick(5)
        snap_id = kg.snapshot(tick_id=5, summary="at five")
        kg.set_tick(20)
        kg.restore(snap_id)
        assert kg.current_tick == 5

    def test_restore_no_persistence(self) -> None:
        """Restore without persistence raises RuntimeError."""
        kg = KnowledgeGraph(db_path=None)
        with pytest.raises(RuntimeError, match="persistence"):
            kg.restore(1)

    def test_snapshot_no_persistence(self) -> None:
        """Snapshot without persistence raises RuntimeError."""
        kg = KnowledgeGraph(db_path=None)
        with pytest.raises(RuntimeError, match="persistence"):
            kg.snapshot(tick_id=1, summary="fail")


# --- Round-trip integrity ---


class TestRoundtripIntegrity:
    """Comprehensive round-trip integrity test (TEST-03)."""

    def test_roundtrip_integrity(self, kg: KnowledgeGraph) -> None:
        """Complex graph survives snapshot/restore with full fidelity."""
        # Build complex graph: 5+ nodes, 5+ edges, mixed property types
        kg.add_node("alice", node_type="agent", hp=100, name="Alice",
                     is_alive=True, inventory=["sword", "shield"],
                     stats={"str": 10, "dex": 14})
        kg.add_node("bob", node_type="agent", hp=80, name="Bob",
                     is_alive=True, inventory=[], stats={"str": 15, "dex": 8})
        kg.add_node("tavern", node_type="entity", name="Rusty Nail",
                     capacity=50, open=True)
        kg.add_node("sword", node_type="entity", damage=10, magic=False,
                     enchantments=["fire"])
        kg.add_node("shield", node_type="entity", defense=5, magic=True,
                     enchantments=[])
        kg.add_node("npc_vendor", node_type="agent", gold=500,
                     prices={"sword": 100, "shield": 50})

        kg.add_edge("alice", "tavern", relation="located_in")
        kg.add_edge("bob", "tavern", relation="located_in")
        kg.add_edge("alice", "sword", relation="holds")
        kg.add_edge("alice", "shield", relation="holds")
        kg.add_edge("bob", "alice", relation="talking_to")
        kg.add_edge("npc_vendor", "tavern", relation="located_in")

        # Record original state
        original_nodes = sorted(kg.nodes())
        original_node_data = {}
        for nid in original_nodes:
            original_node_data[nid] = kg.query(nid)
        original_edges = set()
        for nid in original_nodes:
            for neighbor in kg.neighbors(nid):
                original_edges.add((nid, neighbor))

        # Take snapshot at tick 10
        kg.set_tick(10)
        snap_id = kg.snapshot(tick_id=10, summary="complex state")

        # Mutate heavily
        kg.add_node("dragon", node_type="entity", hp=500, fear=True)
        kg.add_node("cave", node_type="entity", dark=True)
        kg.add_node("gem", node_type="entity", value=1000)
        kg.remove_node("shield")
        kg.remove_node("npc_vendor")
        kg.set("alice", "hp", 1)
        kg.set("alice", "is_alive", False)
        kg.set("bob", "hp", 999)
        kg.set("tavern", "open", False)
        kg.set("sword", "damage", 99)
        kg.add_edge("dragon", "cave", relation="lives_in")
        kg.add_edge("alice", "dragon", relation="fighting")
        kg.remove_edge("alice", "tavern")

        # Restore
        kg.restore(snap_id)

        # Deep equality check
        restored_nodes = sorted(kg.nodes())
        assert restored_nodes == original_nodes, (
            f"Node sets differ: {set(restored_nodes) ^ set(original_nodes)}"
        )

        for nid in original_nodes:
            restored_data = kg.query(nid)
            orig_data = original_node_data[nid]
            assert restored_data == orig_data, (
                f"Node '{nid}' properties differ.\n"
                f"  Original: {orig_data}\n"
                f"  Restored: {restored_data}"
            )

        restored_edges = set()
        for nid in restored_nodes:
            for neighbor in kg.neighbors(nid):
                restored_edges.add((nid, neighbor))
        assert restored_edges == original_edges, (
            f"Edge sets differ: {restored_edges ^ original_edges}"
        )


# --- Persistence tests ---


class TestSnapshotPersistence:
    """Tests for snapshot persistence across process restarts."""

    def test_snapshot_persists_to_sqlite(self, tmp_path: Path) -> None:
        """Snapshot survives process restart (new KnowledgeGraph instance)."""
        db = tmp_path / "test.db"
        kg1 = KnowledgeGraph(db_path=db)
        kg1.add_node("a", node_type="entity", val=42)
        kg1.snapshot(tick_id=1, summary="persisted")

        # New instance from same db
        kg2 = KnowledgeGraph(db_path=db)
        infos = kg2.list_snapshots()
        assert len(infos) == 1
        assert infos[0].summary == "persisted"
        assert infos[0].tick_id == 1

    def test_restore_from_persisted_snapshot(self, tmp_path: Path) -> None:
        """Save, reload, restore to snapshot -- graph matches."""
        db = tmp_path / "test.db"
        kg1 = KnowledgeGraph(db_path=db)
        kg1.add_node("a", node_type="entity", val=42)
        snap_id = kg1.snapshot(tick_id=1, summary="before mutation")
        kg1.set("a", "val", 999)
        kg1.save()

        # New instance, load, restore
        kg2 = KnowledgeGraph(db_path=db)
        kg2.load()
        kg2.restore(snap_id)
        assert kg2.query("a", "val") == 42


class TestMultipleSnapshots:
    """Tests for multiple snapshot restore targeting."""

    def test_multiple_snapshots_restore_any(self, kg: KnowledgeGraph) -> None:
        """Take snapshots at tick 1, 5, 10. Restore to tick 5 -- matches tick 5 state."""
        # Tick 1 state
        kg.add_node("a", node_type="entity", val=1)
        kg.set_tick(1)
        snap1 = kg.snapshot(tick_id=1, summary="tick one")

        # Tick 5 state
        kg.set("a", "val", 5)
        kg.add_node("b", node_type="entity", val=50)
        kg.set_tick(5)
        snap5 = kg.snapshot(tick_id=5, summary="tick five")

        # Tick 10 state
        kg.set("a", "val", 10)
        kg.set("b", "val", 100)
        kg.add_node("c", node_type="entity", val=1000)
        kg.set_tick(10)
        snap10 = kg.snapshot(tick_id=10, summary="tick ten")

        # Restore to tick 5
        kg.restore(snap5)
        assert kg.query("a", "val") == 5
        assert kg.query("b", "val") == 50
        assert not kg.has_node("c")
        assert kg.current_tick == 5


# --- Event compaction and retention ---


class TestEventCompaction:
    """Tests for event compaction on snapshot."""

    def test_event_compaction_on_snapshot(self, kg: KnowledgeGraph) -> None:
        """After snapshot, events before oldest retained snapshot are cleaned."""
        # Generate events at tick 1
        kg.set_tick(1)
        kg.add_node("a", node_type="entity")
        # Snapshot at tick 5
        kg.set_tick(5)
        kg.add_node("b", node_type="entity")
        snap5 = kg.snapshot(tick_id=5, summary="at five")
        # Generate more events at tick 10
        kg.set_tick(10)
        kg.add_node("c", node_type="entity")
        kg.snapshot(tick_id=10, summary="at ten")

        # Events before tick 5 should have been compacted from both
        # in-memory EventStore and persistence
        events = kg._events.get_events()
        for e in events:
            assert e.tick_id >= 5, f"Found event at tick {e.tick_id}, expected >= 5"


class TestSnapshotRetention:
    """Tests for count-based snapshot retention."""

    def test_snapshot_retention(self, kg: KnowledgeGraph) -> None:
        """When retention limit (50) is reached, oldest snapshot is pruned."""
        kg.add_node("a", node_type="entity")
        # Create 51 snapshots
        for i in range(51):
            kg.snapshot(tick_id=i + 1, summary=f"snap {i+1}")

        infos = kg.list_snapshots()
        assert len(infos) <= 50
        # Oldest should have been pruned
        tick_ids = [i.tick_id for i in infos]
        assert 1 not in tick_ids  # tick 1 should be pruned
