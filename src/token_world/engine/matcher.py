"""Deterministic matcher (D-09).

Iterates voluntary mechanics, scores each against a classified action, returns
the highest-scoring mechanic or NoMatchResult if no mechanic scores above zero.

Scoring formula:
    +3 if mechanic's VerbMatcher verb matches classified.verb
    +2 if target node type is acceptable to the mechanic (via target_types attr or tags)
    +1 if actor node type is acceptable (via actor_types attr or tags)

Ties broken alphabetically by mechanic id (stable, deterministic).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from token_world.engine.models import (
    ClassifiedAction,
    MatchedResult,
    MatchResult,
    NoMatchResult,
)
from token_world.mechanic.matchers import VerbMatcher
from token_world.mechanic.protocol import Mechanic


def score_mechanic(mechanic: Mechanic, classified: ClassifiedAction, graph: Any) -> int:
    """Score a single voluntary mechanic against a classified action.

    Args:
        mechanic: The mechanic to evaluate.
        classified: The structured action from the classifier.
        graph: KnowledgeGraph instance (used for node property lookups).

    Returns:
        Integer score: +3 verb match, +2 target type match, +1 actor type match.
    """
    score = 0

    # Verb match (+3): inspect watches() for a VerbMatcher whose verb equals classified.verb
    for matcher in mechanic.watches():
        if isinstance(matcher, VerbMatcher) and matcher.verb == classified.verb:
            score += 3
            break

    # Target type match (+2): only when classified.target is set and exists in graph
    if classified.target is not None and graph.has_node(classified.target):
        target_props = graph.query(classified.target) or {}
        if _node_type_matches(mechanic, target_props, "target"):
            score += 2

    # Actor type match (+1)
    if graph.has_node(classified.actor):
        actor_props = graph.query(classified.actor) or {}
        if _node_type_matches(mechanic, actor_props, "actor"):
            score += 1

    return score


def _node_type_matches(mechanic: Mechanic, node_props: dict, role: str) -> bool:
    """Check whether any type tag on *node_props* is accepted by *mechanic* for *role*.

    Checks both ``type`` and ``subtype`` properties independently against the
    mechanic's ``{role}_types`` attribute and ``tags``.  This avoids the
    short-circuit bug where ``type="entity"`` shadows a more specific
    ``subtype="container"``.

    Args:
        mechanic: The mechanic to inspect.
        node_props: Property dict returned by ``graph.query(node_id)``.
        role: Either ``"target"`` or ``"actor"``.

    Returns:
        True if any type tag from the node is in the mechanic's accepted types.
    """
    tags: list[str] = getattr(mechanic, "tags", []) or []
    hints: list[str] = getattr(mechanic, f"{role}_types", []) or []
    accepted = set(tags) | set(hints)
    if not accepted:
        return False
    # Check both node type and subtype independently
    for key in ("type", "subtype"):
        val = node_props.get(key)
        if val and val in accepted:
            return True
    return False


@dataclass(slots=True)
class DeterministicMatcher:
    """D-09 matcher: scores voluntary mechanics against a classified action.

    Returns the highest-scoring mechanic or NoMatchResult when all mechanics
    score zero.
    """

    def match(
        self,
        classified: ClassifiedAction,
        registry: Any,
        graph: Any,
    ) -> MatchResult:
        """Select the best voluntary mechanic for the classified action.

        Args:
            classified: The structured action from the classifier.
            registry: MechanicRegistry (must expose ``voluntary_mechanics()``).
            graph: KnowledgeGraph instance for node property lookups.

        Returns:
            MatchedResult with the winning mechanic id, score, and reasoning;
            or NoMatchResult when no mechanic scores above zero.
        """
        voluntary = registry.voluntary_mechanics()
        if not voluntary:
            return NoMatchResult(classified=classified, candidates=[])

        # Score all mechanics; sort descending by score then ascending by id (tie-break)
        scored: list[tuple[str, int]] = [
            (m.id, score_mechanic(m, classified, graph)) for m in voluntary
        ]
        scored.sort(key=lambda t: (-t[1], t[0]))

        top_id, top_score = scored[0]
        if top_score == 0:
            return NoMatchResult(classified=classified, candidates=[])

        # Reasoning: note when the winner was settled by tie-breaking
        if len(scored) >= 2 and scored[1][1] == top_score:
            reasoning = f"tie-break vs {scored[1][0]} (both score {top_score})"
        else:
            reasoning = f"clear winner (score {top_score})"

        return MatchedResult(
            mechanic_id=top_id,
            score=top_score,
            reasoning=reasoning,
        )
