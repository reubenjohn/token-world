"""Tests for VisibilityProjector (D-14) — engine/visibility.py.

Tests are grouped by stage:
  - Containment walk (basic / walk)
  - Illumination filter (illumin / dark / light)
  - Property visibility classes (hidden / secret)
  - Belief overlay (belief / deception / partial)
"""

from __future__ import annotations

import networkx as nx
import pytest

from token_world.engine.visibility import VisibilityProjector
from token_world.graph import KnowledgeGraph

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_kg(*args, **kwargs) -> KnowledgeGraph:
    """Return a fresh in-memory KnowledgeGraph."""
    return KnowledgeGraph(db_path=None)


# ---------------------------------------------------------------------------
# Containment walk (Task 1)
# ---------------------------------------------------------------------------


class TestContainmentWalkBasic:
    """Basic / containment-walk tests."""

    def test_unknown_actor_returns_empty(self) -> None:
        """Unknown actor_id → empty dict (no crash)."""
        kg = make_kg()
        proj = VisibilityProjector(kg)
        assert proj.project_for("ghost") == {}

    def test_actor_alone_no_location(self) -> None:
        """Actor with no location edge → projection contains only the actor."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert set(result.keys()) == {"alice"}

    def test_actor_in_room_included(self) -> None:
        """Actor in room via 'location' edge → actor + room both in projection."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", name="Common Room", illumination=1.0)
        kg.add_edge("alice", "room_1", type="location")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert "alice" in result
        assert "room_1" in result

    def test_actor_in_room_with_contained_entities(self) -> None:
        """Actor in room with 2 contained entities → 4 nodes total."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", name="Common Room", illumination=1.0)
        kg.add_node("chair", node_type="entity", name="Chair")
        kg.add_node("table", node_type="entity", name="Table")
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("room_1", "chair", type="contains")
        kg.add_edge("room_1", "table", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert set(result.keys()) == {"alice", "room_1", "chair", "table"}

    def test_actor_holding_item_included(self) -> None:
        """Actor holding 1 item → projection includes the held item."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("sword", node_type="entity", name="Sword")
        kg.add_edge("alice", "sword", type="holds")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert "sword" in result
        assert "alice" in result

    def test_actor_holding_item_and_in_populated_room(self) -> None:
        """Actor holding item + in room with entities → all nodes included."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", name="Common Room", illumination=1.0)
        kg.add_node("chair", node_type="entity", name="Chair")
        kg.add_node("sword", node_type="entity", name="Sword")
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("alice", "sword", type="holds")
        kg.add_edge("room_1", "chair", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert set(result.keys()) == {"alice", "room_1", "chair", "sword"}

    def test_projected_entry_has_required_keys(self) -> None:
        """Each projected entry has keys: type, properties, edges."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", illumination=1.0)
        kg.add_edge("alice", "room_1", type="location")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        for node_id, entry in result.items():
            assert "type" in entry, f"Missing 'type' for {node_id}"
            assert "properties" in entry, f"Missing 'properties' for {node_id}"
            assert "edges" in entry, f"Missing 'edges' for {node_id}"

    def test_properties_are_copies(self) -> None:
        """Mutating projection properties doesn't affect graph state."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice", hp=10)
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        result["alice"]["properties"]["hp"] = 999
        # Graph should be unchanged
        assert kg.query("alice", "hp") == 10

    def test_no_duplicate_entries(self) -> None:
        """Same node appearing in multiple containment paths → only one entry."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", illumination=1.0)
        kg.add_node("chest", node_type="entity", name="Chest")
        # chest is both contained by room AND held by alice (unusual but possible)
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("alice", "chest", type="holds")
        kg.add_edge("room_1", "chest", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        # chest should appear exactly once
        assert "chest" in result
        assert list(result.keys()).count("chest") == 1

    def test_actor_location_uses_first_location_edge(self) -> None:
        """When multiple location edges exist, uses the first one found."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", illumination=1.0, name="Room 1")
        kg.add_node("room_2", node_type="entity", illumination=1.0, name="Room 2")
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("alice", "room_2", type="location")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        # Should only follow one location edge — both rooms should NOT both be fully traversed
        # At minimum alice must be there
        assert "alice" in result
        # The projection counts rooms via containment — at least one room present
        assert "room_1" in result or "room_2" in result

    def test_edges_in_projection_correct(self) -> None:
        """Edge entries in projection list are correct type/target pairs."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", illumination=1.0)
        kg.add_edge("alice", "room_1", type="location")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        alice_edges = result["alice"]["edges"]
        # Should have at least the location edge
        location_edges = [e for e in alice_edges if e["type"] == "location"]
        assert len(location_edges) >= 1
        assert location_edges[0]["target"] == "room_1"


# ---------------------------------------------------------------------------
# Illumination filter (Task 2)
# ---------------------------------------------------------------------------


class TestIlluminationFilter:
    """Illumination / dark room / light source tests."""

    def test_bright_room_everything_visible(self) -> None:
        """Room with illumination >= 0.2 → all entities detailed."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", illumination=1.0)
        kg.add_node("chest", node_type="entity", name="Chest", content="gold")
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("room_1", "chest", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert result["chest"]["properties"].get("name") == "Chest"
        assert result["chest"]["properties"].get("content") == "gold"

    def test_dark_room_no_light_dims_contained(self) -> None:
        """Dark room with no light source → contained entities have empty properties."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", illumination=0.0)
        kg.add_node("chest", node_type="entity", name="Chest", content="gold")
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("room_1", "chest", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert result["chest"]["properties"] == {}

    def test_dark_room_held_light_source_via_tags(self) -> None:
        """Dark room + actor holds item with tags=['light_source'] → full details."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", illumination=0.0)
        kg.add_node("chest", node_type="entity", name="Chest", content="gold")
        kg.add_node("torch", node_type="entity", name="Torch", tags=["light_source"])
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("alice", "torch", type="holds")
        kg.add_edge("room_1", "chest", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert result["chest"]["properties"].get("name") == "Chest"

    def test_dark_room_held_light_source_via_property_flag(self) -> None:
        """Dark room + actor holds item with light_source=True property → full details."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", illumination=0.0)
        kg.add_node("chest", node_type="entity", name="Chest")
        kg.add_node("candle", node_type="entity", name="Candle", light_source=True)
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("alice", "candle", type="holds")
        kg.add_edge("room_1", "chest", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert result["chest"]["properties"].get("name") == "Chest"

    def test_dark_room_held_non_light_item_still_dim(self) -> None:
        """Dark room + actor holds non-light item → contained entities still dimmed."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", illumination=0.0)
        kg.add_node("chest", node_type="entity", name="Chest")
        kg.add_node("rock", node_type="entity", name="Rock")
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("alice", "rock", type="holds")
        kg.add_edge("room_1", "chest", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert result["chest"]["properties"] == {}

    def test_dark_room_multiple_held_items_one_is_light(self) -> None:
        """Dark room + actor holds multiple items including a light source → visible."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", illumination=0.0)
        kg.add_node("chest", node_type="entity", name="Chest", content="gold")
        kg.add_node("torch", node_type="entity", name="Torch", tags=["light_source"])
        kg.add_node("rock", node_type="entity", name="Rock")
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("alice", "torch", type="holds")
        kg.add_edge("alice", "rock", type="holds")
        kg.add_edge("room_1", "chest", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert result["chest"]["properties"].get("content") == "gold"

    def test_room_entry_marked_dimmed(self) -> None:
        """Room entry has dimmed=True marker when illumination filter applies."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", illumination=0.0)
        kg.add_edge("alice", "room_1", type="location")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert result["room_1"].get("dimmed") is True

    def test_actor_properties_always_visible_in_dark(self) -> None:
        """Actor's own properties are always visible even in a dark room."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice", hp=100)
        kg.add_node("room_1", node_type="entity", illumination=0.0)
        kg.add_edge("alice", "room_1", type="location")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert result["alice"]["properties"].get("hp") == 100
        assert result["alice"]["properties"].get("name") == "Alice"


# ---------------------------------------------------------------------------
# Property visibility classes — hidden_properties (Task 3)
# ---------------------------------------------------------------------------


class TestHiddenProperties:
    """Hidden / secret property filtering tests."""

    def test_hidden_property_removed(self) -> None:
        """Node with hidden_properties=['secret'] → secret removed from projection."""
        kg = make_kg()
        kg.add_node(
            "alice",
            node_type="agent",
            name="Alice",
            hidden_properties=["secret"],
            secret="password123",
        )
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert "secret" not in result["alice"]["properties"]

    def test_hidden_properties_key_itself_removed(self) -> None:
        """hidden_properties key is itself removed from the projection."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice", hidden_properties=["secret"])
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert "hidden_properties" not in result["alice"]["properties"]

    def test_non_hidden_properties_retained(self) -> None:
        """Properties not in hidden_properties list are retained."""
        kg = make_kg()
        kg.add_node(
            "alice",
            node_type="agent",
            name="Alice",
            hp=100,
            hidden_properties=["secret"],
            secret="password123",
        )
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert result["alice"]["properties"].get("name") == "Alice"
        assert result["alice"]["properties"].get("hp") == 100

    def test_empty_hidden_properties_no_change(self) -> None:
        """Node with hidden_properties=[] → no properties removed."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice", hp=100, hidden_properties=[])
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert result["alice"]["properties"].get("name") == "Alice"
        assert result["alice"]["properties"].get("hp") == 100

    def test_hidden_properties_multiple_keys(self) -> None:
        """Multiple hidden properties all removed."""
        kg = make_kg()
        kg.add_node(
            "chest",
            node_type="entity",
            name="Chest",
            hidden_properties=["secret_code", "durability"],
            secret_code="1234",
            durability=100,
            contents="gold",
        )
        proj = VisibilityProjector(kg)
        result = proj.project_for("chest")
        assert "secret_code" not in result["chest"]["properties"]
        assert "durability" not in result["chest"]["properties"]
        assert result["chest"]["properties"].get("contents") == "gold"


# ---------------------------------------------------------------------------
# Belief overlay (Task 4)
# ---------------------------------------------------------------------------


class TestBeliefOverlay:
    """Belief / deception / partial knowledge tests."""

    def test_no_beliefs_projection_unchanged(self) -> None:
        """Actor with no beliefs → projection unchanged."""
        kg = make_kg()
        kg.add_node("alice", node_type="agent", name="Alice")
        kg.add_node("room_1", node_type="entity", illumination=1.0)
        kg.add_node("chest", node_type="entity", name="Chest", locked=True)
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("room_1", "chest", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert result["chest"]["properties"].get("locked") is True

    def test_belief_overrides_ground_truth(self) -> None:
        """Actor believes chest is unlocked but ground truth is locked → shows unlocked."""
        kg = make_kg()
        kg.add_node(
            "alice",
            node_type="agent",
            name="Alice",
            beliefs={"chest": {"locked": False}},
        )
        kg.add_node("room_1", node_type="entity", illumination=1.0)
        kg.add_node("chest", node_type="entity", name="Chest", locked=True)
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("room_1", "chest", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert result["chest"]["properties"].get("locked") is False

    def test_belief_for_node_not_in_projection_ignored(self) -> None:
        """Belief entry for node not in projection → ignored (no phantom nodes)."""
        kg = make_kg()
        kg.add_node(
            "alice",
            node_type="agent",
            name="Alice",
            beliefs={"phantom_node": {"name": "Phantom"}},
        )
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        assert "phantom_node" not in result

    def test_belief_overlays_only_specified_properties(self) -> None:
        """Belief overlays only specified properties; others retained from ground truth."""
        kg = make_kg()
        kg.add_node(
            "alice",
            node_type="agent",
            name="Alice",
            beliefs={"chest": {"locked": False}},
        )
        kg.add_node("room_1", node_type="entity", illumination=1.0)
        kg.add_node("chest", node_type="entity", name="Chest", locked=True, weight=10)
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("room_1", "chest", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        # Only locked was in beliefs — weight should still be ground truth
        assert result["chest"]["properties"].get("weight") == 10

    def test_belief_non_dict_type_silently_ignored(self) -> None:
        """Belief value that is not a dict is silently ignored."""
        kg = make_kg()
        kg.add_node(
            "alice",
            node_type="agent",
            name="Alice",
            beliefs={"chest": "some_string"},  # type: ignore[dict-item]
        )
        kg.add_node("room_1", node_type="entity", illumination=1.0)
        kg.add_node("chest", node_type="entity", name="Chest", locked=True)
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("room_1", "chest", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        # Should not crash; locked stays at ground truth
        assert result["chest"]["properties"].get("locked") is True

    def test_ground_truth_unchanged_for_nodes_without_beliefs(self) -> None:
        """Nodes not mentioned in beliefs retain ground truth values."""
        kg = make_kg()
        kg.add_node(
            "alice",
            node_type="agent",
            name="Alice",
            beliefs={"chest": {"locked": False}},
        )
        kg.add_node("room_1", node_type="entity", illumination=1.0, name="Common Room")
        kg.add_node("chest", node_type="entity", name="Chest", locked=True)
        kg.add_node("chair", node_type="entity", name="Chair", hp=100)
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("room_1", "chest", type="contains")
        kg.add_edge("room_1", "chair", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        # Room and chair not in beliefs — ground truth
        assert result["room_1"]["properties"].get("name") == "Common Room"
        assert result["chair"]["properties"].get("hp") == 100


# ---------------------------------------------------------------------------
# WR-04 regression: _outgoing_edges error handling
# ---------------------------------------------------------------------------


class TestOutgoingEdgesErrorHandling:
    """WR-04: bare except Exception in _outgoing_edges must be narrowed.

    NetworkXError (corrupted graph) should propagate; only NodeNotFound
    (TOCTOU race after has_node guard) should be swallowed silently.
    """

    def test_node_not_found_returns_empty_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """NodeNotFound from ego_subgraph is caught and returns [] (TOCTOU safety)."""
        kg = KnowledgeGraph(db_path=None)
        kg.add_node("alice", node_type="agent", name="Alice")
        proj = VisibilityProjector(kg)

        # Simulate TOCTOU: has_node passes but ego_subgraph raises NodeNotFound
        def _raise_node_not_found(*args, **kwargs):
            raise nx.NodeNotFound("alice")

        monkeypatch.setattr(kg, "ego_subgraph", _raise_node_not_found)
        result = proj._outgoing_edges("alice")
        assert result == []

    def test_networkx_error_propagates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """NetworkXError (corrupted graph) must NOT be silently swallowed.

        WR-04: the old bare 'except Exception' would hide corrupted-graph
        errors. After the fix, only NodeNotFound is caught; NetworkXError
        propagates to the caller as a genuine error signal.
        """
        kg = KnowledgeGraph(db_path=None)
        kg.add_node("alice", node_type="agent", name="Alice")
        proj = VisibilityProjector(kg)

        def _raise_networkx_error(*args, **kwargs):
            raise nx.NetworkXError("corrupted graph state")

        monkeypatch.setattr(kg, "ego_subgraph", _raise_networkx_error)
        with pytest.raises(nx.NetworkXError):
            proj._outgoing_edges("alice")
