"""Tests for WorldPropertyMatcher, DecayMatcher, and TickMatcher primitives.

Validates that:
- WorldPropertyMatcher matches set_property events on _world with correct property.
- DecayMatcher is not event-driven but checks node properties.
- TickMatcher is not event-driven (returns False on any event).
"""

from __future__ import annotations

from token_world.graph import Mutation
from token_world.mechanic.matchers import DecayMatcher, TickMatcher, WorldPropertyMatcher

# ---------------------------------------------------------------------------
# Helper Mutations
# ---------------------------------------------------------------------------


def _world_set_prop(property_name: str) -> Mutation:
    """A set_property mutation on the _world sentinel node."""
    return Mutation(
        type="set_property",
        target="_world",
        property=property_name,
        old_value=None,
        new_value="summer",
    )


def _non_world_set_prop(property_name: str, node_id: str = "some_node") -> Mutation:
    """A set_property mutation on a non-_world node."""
    return Mutation(
        type="set_property",
        target=node_id,
        property=property_name,
        old_value=None,
        new_value="value",
    )


def _remove_node_mutation(node_id: str = "_world") -> Mutation:
    """A remove_node mutation."""
    return Mutation(
        type="remove_node",
        target=node_id,
        property=None,
        old_value={"type": "entity"},
        new_value=None,
    )


# ---------------------------------------------------------------------------
# WorldPropertyMatcher tests
# ---------------------------------------------------------------------------


class TestWorldPropertyMatcher:
    """Tests for WorldPropertyMatcher."""

    def test_matches_world_set_property_correct_property(self) -> None:
        """WorldPropertyMatcher('season') matches set_property on _world with property=season."""
        matcher = WorldPropertyMatcher("season")
        event = _world_set_prop("season")
        assert matcher.match(event) is True

    def test_no_match_different_property(self) -> None:
        """Does NOT match set_property on _world with a different property name."""
        matcher = WorldPropertyMatcher("season")
        event = _world_set_prop("weather")
        assert matcher.match(event) is False

    def test_no_match_non_world_node(self) -> None:
        """Does NOT match set_property on a non-_world node."""
        matcher = WorldPropertyMatcher("season")
        event = _non_world_set_prop("season", node_id="forest")
        assert matcher.match(event) is False

    def test_no_match_remove_node_event(self) -> None:
        """Does NOT match a remove_node event even on _world."""
        matcher = WorldPropertyMatcher("season")
        event = _remove_node_mutation("_world")
        assert matcher.match(event) is False

    def test_no_match_add_node_event(self) -> None:
        """Does NOT match an add_node event."""
        matcher = WorldPropertyMatcher("season")
        event = Mutation(
            type="add_node",
            target="_world",
            property=None,
            old_value=None,
            new_value={"type": "entity"},
        )
        assert matcher.match(event) is False

    def test_different_world_property_instances_are_independent(self) -> None:
        """Two WorldPropertyMatchers with different property_names work independently."""
        m_season = WorldPropertyMatcher("season")
        m_weather = WorldPropertyMatcher("weather")
        season_event = _world_set_prop("season")
        weather_event = _world_set_prop("weather")

        assert m_season.match(season_event) is True
        assert m_season.match(weather_event) is False
        assert m_weather.match(weather_event) is True
        assert m_weather.match(season_event) is False


# ---------------------------------------------------------------------------
# DecayMatcher tests
# ---------------------------------------------------------------------------


class TestDecayMatcher:
    """Tests for DecayMatcher."""

    def test_match_returns_false_for_any_event(self) -> None:
        """DecayMatcher.match(event) returns False — it is not event-driven."""
        matcher = DecayMatcher()
        event = _world_set_prop("season")
        assert matcher.match(event) is False

    def test_match_returns_false_for_add_node_event(self) -> None:
        """DecayMatcher.match returns False even for add_node events."""
        matcher = DecayMatcher()
        event = Mutation(
            type="add_node",
            target="tree",
            property=None,
            old_value=None,
            new_value={"type": "entity"},
        )
        assert matcher.match(event) is False

    def test_matches_node_with_decay_period(self) -> None:
        """matches_node({decay_period: 100}) returns True."""
        matcher = DecayMatcher()
        assert matcher.matches_node({"decay_period": 100}) is True

    def test_matches_node_without_decay_period(self) -> None:
        """matches_node({}) returns False — no decay_period property."""
        matcher = DecayMatcher()
        assert matcher.matches_node({}) is False

    def test_matches_node_with_other_properties(self) -> None:
        """matches_node with other properties but no decay_period returns False."""
        matcher = DecayMatcher()
        assert matcher.matches_node({"health": 50, "stamina": 80}) is False

    def test_matches_node_decay_period_can_be_zero(self) -> None:
        """matches_node({decay_period: 0}) still returns True — key presence matters."""
        matcher = DecayMatcher()
        assert matcher.matches_node({"decay_period": 0}) is True


# ---------------------------------------------------------------------------
# TickMatcher tests
# ---------------------------------------------------------------------------


class TestTickMatcher:
    """Tests for TickMatcher."""

    def test_match_returns_false_for_any_event(self) -> None:
        """TickMatcher.match(event) returns False — it fires unconditionally via passive sweep."""
        matcher = TickMatcher()
        event = _world_set_prop("season")
        assert matcher.match(event) is False

    def test_match_returns_false_for_remove_node(self) -> None:
        """TickMatcher.match returns False for remove_node events too."""
        matcher = TickMatcher()
        event = _remove_node_mutation("somenode")
        assert matcher.match(event) is False
