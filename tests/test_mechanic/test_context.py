"""Tests for MechanicContext DSL wrapper."""

from __future__ import annotations

from token_world.mechanic import MechanicContext


class TestMechanicContext:
    """Tests for MechanicContext delegation to KnowledgeGraph."""

    def test_query_node_returns_dict(self, mechanic_ctx: MechanicContext) -> None:
        """query_node returns node properties dict."""
        props = mechanic_ctx.query_node("alice")
        assert isinstance(props, dict)
        assert props["type"] == "agent"
        assert props["location"] == "room_a"

    def test_query_node_single_property(self, mechanic_ctx: MechanicContext) -> None:
        """query_node with property returns single value."""
        location = mechanic_ctx.query_node("alice", "location")
        assert location == "room_a"

    def test_query_neighbors(self, mechanic_ctx: MechanicContext) -> None:
        """query_neighbors returns neighbor IDs."""
        neighbors = mechanic_ctx.query_neighbors("room_a")
        assert "room_b" in neighbors

    def test_has_node_exists(self, mechanic_ctx: MechanicContext) -> None:
        """has_node returns True for existing node."""
        assert mechanic_ctx.has_node("alice") is True

    def test_has_node_nonexistent(self, mechanic_ctx: MechanicContext) -> None:
        """has_node returns False for nonexistent node."""
        assert mechanic_ctx.has_node("nonexistent") is False

    def test_has_edge(self, mechanic_ctx: MechanicContext) -> None:
        """has_edge returns True for existing edge."""
        assert mechanic_ctx.has_edge("room_a", "room_b") is True

    def test_has_edge_nonexistent(self, mechanic_ctx: MechanicContext) -> None:
        """has_edge returns False for nonexistent edge."""
        assert mechanic_ctx.has_edge("alice", "rock") is False

    def test_mutate_returns_mutation(self, mechanic_ctx: MechanicContext) -> None:
        """mutate sets property and returns Mutation."""
        m = mechanic_ctx.mutate("alice", "location", "room_b")
        assert m.type == "set_property"
        assert m.target == "alice"
        assert m.property == "location"
        assert m.new_value == "room_b"

    def test_add_node_returns_mutation(self, mechanic_ctx: MechanicContext) -> None:
        """add_node creates node and returns Mutation."""
        m = mechanic_ctx.add_node("sword", node_type="entity", damage=10)
        assert m.type == "add_node"
        assert m.target == "sword"
        assert mechanic_ctx.has_node("sword") is True

    def test_remove_node_returns_mutation(self, mechanic_ctx: MechanicContext) -> None:
        """remove_node removes node and returns Mutation."""
        m = mechanic_ctx.remove_node("rock")
        assert m.type == "remove_node"
        assert mechanic_ctx.has_node("rock") is False

    def test_add_edge_returns_mutation(self, mechanic_ctx: MechanicContext) -> None:
        """add_edge creates edge and returns Mutation."""
        m = mechanic_ctx.add_edge("alice", "rock", relation="holds")
        assert m.type == "add_edge"
        assert mechanic_ctx.has_edge("alice", "rock") is True

    def test_remove_edge_returns_mutation(self, mechanic_ctx: MechanicContext) -> None:
        """remove_edge removes edge and returns Mutation."""
        mechanic_ctx.remove_edge("room_a", "room_b")
        assert mechanic_ctx.has_edge("room_a", "room_b") is False

    def test_find_nodes_with_filters(self, mechanic_ctx: MechanicContext) -> None:
        """find_nodes with filters returns matching IDs."""
        agents = mechanic_ctx.find_nodes(type="agent")
        assert agents == ["alice"]

    def test_actor_and_target(self, mechanic_ctx: MechanicContext) -> None:
        """actor and target are set correctly."""
        assert mechanic_ctx.actor == "alice"
        assert mechanic_ctx.target == "room_b"
