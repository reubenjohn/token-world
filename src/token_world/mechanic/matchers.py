"""Declarative matcher primitives for involuntary mechanic triggering.

Phase 2 matchers (PropertyChangeMatcher, EdgeMatcher, NodeMatcher) are
struct-style frozen dataclasses evaluated by the standalone :func:`matches`
helper.

Phase 5 adds four more matchers that expose a ``match(mutation)`` instance
method directly (consumed by the deterministic engine pipeline):

- :class:`VerbMatcher` — matches by verb (voluntary mechanic dispatch, D-09).
- :class:`WorldPropertyMatcher` — matches world-level property mutations (D-10,
  GAP-ENG09).
- :class:`DecayMatcher` — per-tick sweep for nodes with ``decay_period`` (D-17).
- :class:`TickMatcher` — unconditional per-tick passive invocation (D-17).
"""

from __future__ import annotations

from dataclasses import dataclass

from token_world.graph import KnowledgeGraph, Mutation


@dataclass(frozen=True)
class PropertyChangeMatcher:
    """Matches mutations that set a specific property.

    Attributes:
        property_name: The property name to watch for changes.
        node_type: If set, only match if the target node has this type
            (e.g. "agent" or "entity").
    """

    property_name: str
    node_type: str | None = None


@dataclass(frozen=True)
class EdgeMatcher:
    """Matches edge addition or removal mutations.

    Attributes:
        event_type: Must be "add_edge" or "remove_edge".
        edge_label: If set, only match edges with this label in their properties.
    """

    event_type: str
    edge_label: str | None = None

    def __post_init__(self) -> None:
        if self.event_type not in ("add_edge", "remove_edge"):
            raise ValueError(
                f"EdgeMatcher event_type must be 'add_edge' or 'remove_edge', "
                f"got '{self.event_type}'"
            )


@dataclass(frozen=True)
class NodeMatcher:
    """Matches node addition or removal mutations.

    Attributes:
        event_type: Must be "add_node" or "remove_node".
        node_type: If set, only match nodes with this type.
    """

    event_type: str
    node_type: str | None = None

    def __post_init__(self) -> None:
        if self.event_type not in ("add_node", "remove_node"):
            raise ValueError(
                f"NodeMatcher event_type must be 'add_node' or 'remove_node', "
                f"got '{self.event_type}'"
            )


# ---------------------------------------------------------------------------
# Phase 5 matchers — expose match(mutation) instance method
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerbMatcher:
    """Matches when a classified action's verb equals the declared verb.

    Used by voluntary mechanics to declare what verb they handle (D-09).
    The :class:`~token_world.engine.matcher.DeterministicMatcher` inspects
    each voluntary mechanic's ``watches()`` list for ``VerbMatcher`` instances
    to compute the verb-match component of the scoring formula.

    ``match()`` is intentionally a no-op here — the deterministic matcher reads
    the ``.verb`` attribute directly.  The method is provided for interface
    consistency with the other Phase-5 matchers.

    Attributes:
        verb: The verb string this mechanic handles (e.g. ``"pickup"``).
    """

    verb: str

    def match(self, mutation: Mutation) -> bool:
        """Always False in event-matching context (verb comparison is done by caller)."""
        return False


@dataclass(frozen=True)
class WorldPropertyMatcher:
    """Involuntary-mechanic matcher: triggers on world-level property changes.

    Closes GAP-ENG09.  The ``_world`` sentinel node holds universe-scoped
    properties (season, weather, day_of_year).  Mechanics that react to such
    changes declare this matcher in their ``watches()`` method.

    Attributes:
        property_name: The world property to watch (e.g. ``"season"``).
    """

    property_name: str

    def match(self, mutation: Mutation) -> bool:
        """Return True if *mutation* is a set_property event on _world for this property."""
        if mutation.type != "set_property":
            return False
        if mutation.target != "_world":
            return False
        return mutation.property == self.property_name


@dataclass(frozen=True)
class DecayMatcher:
    """Per-tick decay matcher: identifies nodes eligible for decay.

    Consumed by the Phase 5 passive sweep (D-17).  Unlike event-based matchers,
    this matcher is not driven by graph mutations — ``match()`` always returns
    ``False``.  Instead, the passive sweep iterates the graph directly and uses
    :meth:`matches_node` to decide whether a node should be decayed.
    """

    def match(self, mutation: Mutation) -> bool:
        """Always False — DecayMatcher is not event-driven."""
        return False

    def matches_node(self, node_props: dict) -> bool:
        """Return True if *node_props* contains a ``decay_period`` key."""
        return "decay_period" in node_props


@dataclass(frozen=True)
class TickMatcher:
    """Fires once per tick unconditionally.

    Consumed by the Phase 5 passive sweep (D-17).  Used for world-state
    reactions that must run every tick (e.g. weather sampling via GAP-ENG09
    hooks).  ``match()`` returns False because the passive sweep dispatches
    these mechanics directly rather than via event filtering.
    """

    def match(self, mutation: Mutation) -> bool:
        """Always False — TickMatcher is dispatched unconditionally by passive sweep."""
        return False


Matcher = (
    PropertyChangeMatcher
    | EdgeMatcher
    | NodeMatcher
    | VerbMatcher
    | WorldPropertyMatcher
    | DecayMatcher
    | TickMatcher
)
"""Union type for all matcher primitives."""


def matches(matcher: Matcher, mutation: Mutation, graph: KnowledgeGraph) -> bool:
    """Evaluate whether a matcher matches a given mutation.

    Args:
        matcher: The matcher to evaluate.
        mutation: The mutation to test against.
        graph: The knowledge graph (needed for node_type lookups).

    Returns:
        True if the matcher matches the mutation.
    """
    if isinstance(matcher, PropertyChangeMatcher):
        if mutation.type != "set_property":
            return False
        if mutation.property != matcher.property_name:
            return False
        if matcher.node_type is not None:
            # Check target node's type in the graph
            if not graph.has_node(mutation.target):
                return False
            node_props = graph.query(mutation.target)
            if node_props.get("type") != matcher.node_type:
                return False
        return True

    if isinstance(matcher, EdgeMatcher):
        if mutation.type != matcher.event_type:
            return False
        if matcher.edge_label is not None:
            # Edge properties are stored in new_value (add) or old_value (remove)
            props = mutation.new_value or mutation.old_value
            if not isinstance(props, dict) or props.get("relation") != matcher.edge_label:
                return False
        return True

    if isinstance(matcher, NodeMatcher):
        if mutation.type != matcher.event_type:
            return False
        if matcher.node_type is not None:
            # For add_node, new_value is a dict with "type" key
            if mutation.type == "add_node":
                if not isinstance(mutation.new_value, dict):
                    return False
                if mutation.new_value.get("type") != matcher.node_type:
                    return False
            # For remove_node, old_value is a dict with "type" key
            elif mutation.type == "remove_node":
                if not isinstance(mutation.old_value, dict):
                    return False
                if mutation.old_value.get("type") != matcher.node_type:
                    return False
        return True

    return False
