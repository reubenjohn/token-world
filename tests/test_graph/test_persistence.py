"""Tests for SQLite graph persistence."""

from __future__ import annotations

from pathlib import Path

from token_world.graph.knowledge_graph import KnowledgeGraph


class TestSaveEmpty:
    def test_save_empty_graph(self, tmp_db: Path) -> None:
        """save() on empty graph creates SQLite tables without error."""
        kg = KnowledgeGraph(db_path=tmp_db)
        kg.save()  # Should not raise
        assert tmp_db.exists()


class TestRoundtrip:
    def test_save_load_roundtrip(self, tmp_db: Path) -> None:
        """Nodes and edges survive save/load cycle."""
        kg = KnowledgeGraph(db_path=tmp_db)
        kg.add_node("bob", node_type="agent", hp=100)
        kg.add_node("sword", node_type="entity", damage=10)
        kg.add_edge("bob", "sword", relation="holds")
        kg.save()

        kg2 = KnowledgeGraph(db_path=tmp_db)
        kg2.load()
        assert kg2.has_node("bob")
        assert kg2.query("bob", "hp") == 100
        assert kg2.has_node("sword")
        assert kg2.query("sword", "damage") == 10
        assert kg2.has_edge("bob", "sword")

    def test_persist_arbitrary_properties(self, tmp_db: Path) -> None:
        """All JSON-serializable property types survive save/load."""
        kg = KnowledgeGraph(db_path=tmp_db)
        kg.add_node("bob", node_type="agent")
        kg.set("bob", "s", "hello")
        kg.set("bob", "i", 42)
        kg.set("bob", "f", 3.14)
        kg.set("bob", "b", True)
        kg.set("bob", "n", None)
        kg.set("bob", "l", [1, 2, 3])
        kg.set("bob", "d", {"key": "value"})
        kg.save()

        kg2 = KnowledgeGraph(db_path=tmp_db)
        kg2.load()
        assert kg2.query("bob", "s") == "hello"
        assert kg2.query("bob", "i") == 42
        assert kg2.query("bob", "f") == 3.14
        assert kg2.query("bob", "b") is True
        assert kg2.query("bob", "n") is None
        assert kg2.query("bob", "l") == [1, 2, 3]
        assert kg2.query("bob", "d") == {"key": "value"}

    def test_persist_edge_properties(self, tmp_db: Path) -> None:
        """Edge properties survive save/load."""
        kg = KnowledgeGraph(db_path=tmp_db)
        kg.add_node("bob", node_type="agent")
        kg.add_node("sword", node_type="entity")
        kg.add_edge("bob", "sword", relation="holds", strength=5)
        kg.save()

        kg2 = KnowledgeGraph(db_path=tmp_db)
        kg2.load()
        assert kg2._graph.edges["bob", "sword"]["relation"] == "holds"
        assert kg2._graph.edges["bob", "sword"]["strength"] == 5

    def test_persist_survives_restart(self, tmp_db: Path) -> None:
        """Simulates process restart: save, destroy object, create new, load."""
        kg = KnowledgeGraph(db_path=tmp_db)
        kg.add_node("bob", node_type="agent", hp=100)
        kg.add_node("sword", node_type="entity")
        kg.add_edge("bob", "sword", relation="holds")
        kg.save()

        # Destroy the original object
        del kg

        # Create a completely new KnowledgeGraph
        kg2 = KnowledgeGraph(db_path=tmp_db)
        kg2.load()
        assert kg2.has_node("bob")
        assert kg2.query("bob", "hp") == 100
        assert kg2.has_edge("bob", "sword")


class TestEventPersistence:
    def test_events_persisted(self, tmp_db: Path) -> None:
        """Events are written to SQLite on save and restored on load."""
        kg = KnowledgeGraph(db_path=tmp_db)
        kg.add_node("bob", node_type="agent")
        kg.set("bob", "hp", 100)
        kg.save()

        kg2 = KnowledgeGraph(db_path=tmp_db)
        kg2.load()
        events = kg2._events.get_events()
        assert len(events) == 2
        assert events[0].event_type == "add_node"
        assert events[1].event_type == "set_property"


class TestTableCreation:
    def test_tables_created_lazily(self, tmp_db: Path) -> None:
        """Tables are created on first save(), not on __init__."""
        kg = KnowledgeGraph(db_path=tmp_db)
        # Database file should not exist yet (no save called)
        assert not tmp_db.exists()
        kg.save()
        assert tmp_db.exists()


class TestDirectedness:
    def test_directed_graph_preserved(self, tmp_db: Path) -> None:
        """Edge directionality is preserved across save/load (Pitfall 1)."""
        kg = KnowledgeGraph(db_path=tmp_db)
        kg.add_node("a", node_type="agent")
        kg.add_node("b", node_type="entity")
        kg.add_edge("a", "b", relation="follows")
        kg.save()

        kg2 = KnowledgeGraph(db_path=tmp_db)
        kg2.load()
        assert kg2.has_edge("a", "b")
        assert not kg2.has_edge("b", "a")  # Direction preserved
