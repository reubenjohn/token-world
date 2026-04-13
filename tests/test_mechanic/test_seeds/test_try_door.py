"""Tests for MECH27 try_door seed mechanic."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds._helpers import _find_matching_key
from token_world.mechanic.seeds.try_door import TryDoorMechanic


@pytest.fixture
def uc_e06_graph() -> KnowledgeGraph:
    """UC-E06 shape: alice, door_1 locked, no key."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", position=[0, 0], stamina=10)
    kg.add_node(
        "room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5]
    )
    kg.add_node(
        "room_b", node_type="entity", subtype="room", bbox=[5, -5, 15, 5]
    )
    kg.add_node(
        "door_1",
        node_type="entity",
        subtype="door",
        locked=True,
        direction="east",
    )
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("room_a", "door_1", relation="connects")
    kg.add_edge("door_1", "room_b", relation="connects")
    return kg


@pytest.fixture
def mechanic() -> TryDoorMechanic:
    return TryDoorMechanic()


# ---------------------------------------------------------------------------
# Metadata contract
# ---------------------------------------------------------------------------


class TestTryDoorMetadata:
    def test_id(self, mechanic: TryDoorMechanic) -> None:
        assert mechanic.id == "try_door"

    def test_voluntary(self, mechanic: TryDoorMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: TryDoorMechanic) -> None:
        for tag in ("spatial", "interaction", "passage"):
            assert tag in mechanic.tags


# ---------------------------------------------------------------------------
# _find_matching_key helper (lives in _helpers.py)
# ---------------------------------------------------------------------------


class TestFindMatchingKey:
    def test_returns_held_key_by_id(self) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("brass_key", node_type="entity", key_id="oak_door")
        kg.add_edge("alice", "brass_key", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="brass_key")
        assert _find_matching_key(ctx, "alice", "oak_door") == "brass_key"

    def test_returns_none_when_no_match(self) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("iron_key", node_type="entity", key_id="iron_chest")
        kg.add_edge("alice", "iron_key", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="iron_key")
        assert _find_matching_key(ctx, "alice", "oak_door") is None

    def test_returns_none_when_no_holdings(self) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        ctx = MechanicContext(kg, actor="alice", target="alice")
        assert _find_matching_key(ctx, "alice", "any") is None


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestTryDoorCheck:
    def test_passes_for_door_target(
        self, uc_e06_graph: KnowledgeGraph, mechanic: TryDoorMechanic
    ) -> None:
        ctx = MechanicContext(uc_e06_graph, actor="alice", target="door_1")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_target_not_a_door(self, mechanic: TryDoorMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("rock", node_type="entity", subtype="rock")
        ctx = MechanicContext(kg, actor="alice", target="rock")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("door" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# apply() — three branches (unlocked / locked+key / locked+no-key)
# ---------------------------------------------------------------------------


class TestTryDoorApply:
    def test_unlocked_door_yields_no_mutation(
        self, mechanic: TryDoorMechanic
    ) -> None:
        """Door already unlocked — nothing to do."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("door_open", node_type="entity", subtype="door", locked=False)
        ctx = MechanicContext(kg, actor="alice", target="door_open")
        assert mechanic.apply(ctx) == []

    def test_locked_door_with_matching_key_unlocks(
        self, mechanic: TryDoorMechanic
    ) -> None:
        """Locked door + held key with matching key_id → door.locked = False."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node(
            "door_oak",
            node_type="entity",
            subtype="door",
            locked=True,
            required_key_id="oak",
        )
        kg.add_node("oak_key", node_type="entity", key_id="oak")
        kg.add_edge("alice", "oak_key", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="door_oak")
        mechanic.apply(ctx)
        assert kg.query("door_oak").get("locked") is False

    def test_uc_e06_locked_no_key_writes_refusal_narrative(
        self, uc_e06_graph: KnowledgeGraph, mechanic: TryDoorMechanic
    ) -> None:
        """UC-E06: alice without a key — door stays locked, refusal narrative set."""
        ctx = MechanicContext(uc_e06_graph, actor="alice", target="door_1")
        mechanic.apply(ctx)
        # Refusal narrative recorded on actor.
        alice_props = uc_e06_graph.query("alice")
        assert alice_props.get("last_refusal_narrative") == "the door is locked"
        assert alice_props.get("last_refusal_target") == "door_1"
        # Door stayed locked.
        assert uc_e06_graph.query("door_1").get("locked") is True
        # Alice did not move and stamina is unchanged.
        assert alice_props.get("stamina") == 10
        assert uc_e06_graph.has_edge("alice", "room_a")
        assert not uc_e06_graph.has_edge("alice", "room_b")

    def test_locked_door_without_required_key_id_refuses(
        self, mechanic: TryDoorMechanic
    ) -> None:
        """Locked door that declares no required_key_id → always refuses."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        # locked but no required_key_id — impossible to open by key.
        kg.add_node("door_sealed", node_type="entity", subtype="door", locked=True)
        # Even holding a key with some key_id, there's nothing to match.
        kg.add_node("some_key", node_type="entity", key_id="random")
        kg.add_edge("alice", "some_key", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="door_sealed")
        mechanic.apply(ctx)
        assert kg.query("door_sealed").get("locked") is True
        assert (
            kg.query("alice").get("last_refusal_narrative")
            == "the door is locked"
        )
