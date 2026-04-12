"""Test fixtures for graph module tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from token_world.graph.knowledge_graph import KnowledgeGraph


class GraphBuilder:
    """Fluent builder for constructing KnowledgeGraph instances in tests.

    Usage:
        graph = (GraphBuilder()
            .node("bob", node_type="agent", hp=100)
            .node("sword", node_type="entity", damage=10)
            .edge("bob", "sword", relation="holds")
            .build())
    """

    def __init__(self) -> None:
        self._nodes: list[tuple[str, str, dict]] = []
        self._edges: list[tuple[str, str, dict]] = []

    def node(
        self, id: str, *, node_type: str = "entity", **props: object
    ) -> GraphBuilder:
        """Add a node spec to the builder."""
        self._nodes.append((id, node_type, props))
        return self

    def edge(self, src: str, dst: str, **props: object) -> GraphBuilder:
        """Add an edge spec to the builder."""
        self._edges.append((src, dst, props))
        return self

    def build(self) -> KnowledgeGraph:
        """Construct and return a populated KnowledgeGraph."""
        kg = KnowledgeGraph()
        for node_id, node_type, props in self._nodes:
            kg.add_node(node_id, node_type=node_type, **props)
        for src, dst, props in self._edges:
            kg.add_edge(src, dst, **props)
        return kg


@pytest.fixture
def kg(tmp_path: Path) -> KnowledgeGraph:
    """A fresh KnowledgeGraph with a tmp SQLite path."""
    return KnowledgeGraph(db_path=tmp_path / "test.db")


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """A temporary database path for persistence tests."""
    return tmp_path / "test.db"


@pytest.fixture
def graph_builder() -> GraphBuilder:
    """A fresh GraphBuilder instance."""
    return GraphBuilder()
