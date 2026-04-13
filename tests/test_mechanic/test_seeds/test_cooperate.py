"""Tests for MECH12 cooperate FRAMEWORK-GAP STUB.

Per D-38 the cooperate mechanic ships as a stub blocked on GAP-ENG05
(intent-fusion pre-pass for multi-actor mechanics — Phase 5). The
stub mirrors the persuade stub's contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.registry import MechanicRegistry
from token_world.mechanic.seeds.cooperate import CooperateMechanic

SEEDS_DIR = Path(__file__).resolve().parents[3] / "src" / "token_world" / "mechanic" / "seeds"


@pytest.fixture
def registry() -> MechanicRegistry:
    return MechanicRegistry(SEEDS_DIR, universe_dir=SEEDS_DIR.parent)


@pytest.fixture
def mechanic() -> CooperateMechanic:
    return CooperateMechanic()


class TestCooperateMetadata:
    def test_id(self, mechanic: CooperateMechanic) -> None:
        assert mechanic.id == "cooperate"

    def test_blocked_by_class_attribute(self) -> None:
        assert getattr(CooperateMechanic, "blocked_by", None) == "GAP-ENG05"

    def test_tags_present(self, mechanic: CooperateMechanic) -> None:
        assert "social" in mechanic.tags
        assert "multi_actor" in mechanic.tags


class TestCooperateStubRegistration:
    def test_cooperate_stub_is_discoverable_by_registry(self, registry: MechanicRegistry) -> None:
        info = registry.get_info("cooperate")
        assert info.id == "cooperate"

    def test_cooperate_class_blocked_by_via_get_class(self, registry: MechanicRegistry) -> None:
        cls = registry.get_class("cooperate")
        assert getattr(cls, "blocked_by", None) == "GAP-ENG05"


class TestCooperateCheckApply:
    def test_check_refuses_with_blocked_by_reason(self, mechanic: CooperateMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("boulder", node_type="entity")
        ctx = MechanicContext(kg, actor="alice", target="boulder")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("GAP-ENG05" in r for r in result.reasons)

    def test_apply_is_noop(self, mechanic: CooperateMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("boulder", node_type="entity")
        ctx = MechanicContext(kg, actor="alice", target="boulder")
        assert mechanic.apply(ctx) == []
