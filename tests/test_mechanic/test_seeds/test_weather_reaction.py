"""Tests for MECH21 weather_reaction FRAMEWORK-GAP STUB.

Per D-38 + the 04-11 PLAN, weather_reaction ships as a framework-gap
stub blocked on GAP-ENG09 (the ``WorldPropertyMatcher`` mechanic-matcher
primitive lands in Phase 5). The stub must:

    - declare a class-level ``blocked_by = "GAP-ENG09"`` attribute,
    - validate cleanly through the Phase-4 six-stage pipeline,
    - be discoverable by :class:`MechanicRegistry`,
    - refuse on ``check`` with a reason string containing "GAP-ENG09",
    - be a no-op on ``apply`` (returns ``[]``).

The stub routes UC-V02 / UC-V04 to ``pytest.skip`` with the gap id in
the reason via the existing D-38 stub-probe harness in
``tests/test_integration/test_use_cases.py`` (04-09's
``_resolve_blocked_by`` helper + probe block).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.registry import MechanicRegistry
from token_world.mechanic.seeds.weather_reaction import WeatherReactionMechanic

SEEDS_DIR = Path(__file__).resolve().parents[3] / "src" / "token_world" / "mechanic" / "seeds"


@pytest.fixture
def registry() -> MechanicRegistry:
    return MechanicRegistry(SEEDS_DIR, universe_dir=SEEDS_DIR.parent)


@pytest.fixture
def mechanic() -> WeatherReactionMechanic:
    return WeatherReactionMechanic()


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestWeatherReactionMetadata:
    def test_id(self, mechanic: WeatherReactionMechanic) -> None:
        assert mechanic.id == "weather_reaction"

    def test_blocked_by_class_attribute(self) -> None:
        """The class itself (not just an instance) carries blocked_by per D-38."""
        assert getattr(WeatherReactionMechanic, "blocked_by", None) == "GAP-ENG09"

    def test_tags_present(self, mechanic: WeatherReactionMechanic) -> None:
        assert "environmental" in mechanic.tags
        assert "weather" in mechanic.tags

    def test_is_voluntary_for_routing(self, mechanic: WeatherReactionMechanic) -> None:
        """Phase-4 routing requires voluntary=True so the D-38 stub-probe
        in test_use_cases.py can find the stub via
        match_mechanic_for_verb (which only returns voluntary mechanics).
        Semantic intent remains involuntary; the 'involuntary_intent'
        tag records that. voluntary flips to False when GAP-ENG09 lands
        in Phase 5 along with the WorldPropertyMatcher wiring.
        """
        assert mechanic.voluntary is True
        assert "involuntary_intent" in mechanic.tags


# ---------------------------------------------------------------------------
# Registry discovery (D-38 contract)
# ---------------------------------------------------------------------------


class TestWeatherReactionStubRegistration:
    def test_weather_reaction_stub_is_discoverable_by_registry(
        self, registry: MechanicRegistry
    ) -> None:
        info = registry.get_info("weather_reaction")
        assert info.id == "weather_reaction"

    def test_weather_reaction_class_blocked_by_via_get_class(
        self, registry: MechanicRegistry
    ) -> None:
        """The harness reads blocked_by via the public get_class accessor."""
        cls = registry.get_class("weather_reaction")
        assert getattr(cls, "blocked_by", None) == "GAP-ENG09"


# ---------------------------------------------------------------------------
# check + apply contract
# ---------------------------------------------------------------------------


class TestWeatherReactionCheckApply:
    def test_check_refuses_with_blocked_by_reason(
        self, mechanic: WeatherReactionMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("world", node_type="entity")
        ctx = MechanicContext(kg, actor="world", target="world")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("GAP-ENG09" in r for r in result.reasons)

    def test_apply_is_noop(self, mechanic: WeatherReactionMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("world", node_type="entity")
        ctx = MechanicContext(kg, actor="world", target="world")
        assert mechanic.apply(ctx) == []
