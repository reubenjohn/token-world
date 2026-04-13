"""Tests for MECH09 persuade FRAMEWORK-GAP STUB.

Per D-38 the persuade mechanic ships as a stub blocked on GAP-ENG03
(``llm_adjudicated`` mechanic category lands in Phase 5). The stub
must:

    - declare a class-level ``blocked_by = "GAP-ENG03"`` attribute,
    - validate cleanly through the Phase-4 pipeline,
    - be discoverable by :class:`MechanicRegistry`,
    - refuse on ``check`` with a reason mentioning the gap id,
    - be a no-op on ``apply`` (returns ``[]``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.registry import MechanicRegistry
from token_world.mechanic.seeds.persuade import PersuadeMechanic

SEEDS_DIR = Path(__file__).resolve().parents[3] / "src" / "token_world" / "mechanic" / "seeds"


@pytest.fixture
def registry() -> MechanicRegistry:
    return MechanicRegistry(SEEDS_DIR, universe_dir=SEEDS_DIR.parent)


@pytest.fixture
def mechanic() -> PersuadeMechanic:
    return PersuadeMechanic()


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestPersuadeMetadata:
    def test_id(self, mechanic: PersuadeMechanic) -> None:
        assert mechanic.id == "persuade"

    def test_blocked_by_class_attribute(self) -> None:
        """The class itself (not just an instance) carries blocked_by."""
        assert getattr(PersuadeMechanic, "blocked_by", None) == "GAP-ENG03"

    def test_tags_present(self, mechanic: PersuadeMechanic) -> None:
        assert "social" in mechanic.tags
        assert "llm_adjudicated" in mechanic.tags


# ---------------------------------------------------------------------------
# Registry discovery (D-38 contract)
# ---------------------------------------------------------------------------


class TestPersuadeStubRegistration:
    def test_persuade_stub_is_discoverable_by_registry(
        self, registry: MechanicRegistry
    ) -> None:
        info = registry.get_info("persuade")
        assert info.id == "persuade"

    def test_persuade_class_blocked_by_via_get_class(
        self, registry: MechanicRegistry
    ) -> None:
        """The harness reads blocked_by via the public get_class accessor."""
        cls = registry.get_class("persuade")
        assert getattr(cls, "blocked_by", None) == "GAP-ENG03"


# ---------------------------------------------------------------------------
# check + apply contract
# ---------------------------------------------------------------------------


class TestPersuadeCheckApply:
    def test_check_refuses_with_blocked_by_reason(
        self, mechanic: PersuadeMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("bob", node_type="agent")
        ctx = MechanicContext(kg, actor="alice", target="bob")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("GAP-ENG03" in r for r in result.reasons)

    def test_apply_is_noop(self, mechanic: PersuadeMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("bob", node_type="agent")
        ctx = MechanicContext(kg, actor="alice", target="bob")
        assert mechanic.apply(ctx) == []
