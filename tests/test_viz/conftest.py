"""Small GraphBuilder-based fixtures for viz tests."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph


@pytest.fixture
def small_graph(tmp_path) -> KnowledgeGraph:
    kg = KnowledgeGraph(db_path=tmp_path / "viz.db")
    kg.add_node("alice", node_type="agent", position=[0.0, 0.0])
    kg.add_node("room_a", node_type="entity", subtype="room")
    kg.add_node("sword", node_type="entity", subtype="weapon")
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("sword", "alice", relation="held_by")
    return kg
