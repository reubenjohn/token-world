"""Deterministic matcher (D-09).

Iterates voluntary mechanics, scores each against a classified action, returns
the highest-scoring mechanic or NoMatchResult if no mechanic scores above zero.

Scoring formula:
    +3 if mechanic's VerbMatcher verb matches classified.verb
    +2 if target node type is acceptable to the mechanic (via target_types attr or tags)
    +1 if actor node type is acceptable (via actor_types attr or tags)

Ties broken alphabetically by mechanic id (stable, deterministic).

When no mechanic scores above zero, NoMatchResult.candidates (D-11) is populated
with up to ``TOP_K_CANDIDATES`` mechanic IDs ranked by verb-name similarity
(``difflib.SequenceMatcher.ratio``) so the operator has useful context when
authoring a new mechanic to handle a yielded action. If every candidate scores
zero similarity (e.g. no mechanic declares a VerbMatcher), we fall back to the
first K mechanic IDs in alphabetical order so the list is never empty when
mechanics exist — per 2026-04-14 tech-debt closure guidance for IN-01.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from token_world.engine.models import (
    ClassifiedAction,
    MatchedResult,
    MatchResult,
    NoMatchResult,
)
from token_world.mechanic.matchers import VerbMatcher
from token_world.mechanic.protocol import Mechanic

# D-11: top-K closest-matching mechanic IDs surfaced on NoMatchResult.candidates
# so the operator has a menu when authoring a new mechanic for a yielded action.
# K=3 chosen to keep subagent prompts short while still presenting a useful menu.
TOP_K_CANDIDATES = 3


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


def _mechanic_verbs(mechanic: Mechanic) -> list[str]:
    """Extract the verb(s) a mechanic responds to via its VerbMatcher watchers.

    A mechanic may declare zero, one, or many :class:`VerbMatcher` instances;
    we return every verb in declaration order. Mechanics without any
    VerbMatcher return an empty list, which the ranking helper treats as
    zero similarity (they fall back to alphabetical tie-break).

    Args:
        mechanic: The mechanic to inspect.

    Returns:
        List of verb strings from the mechanic's VerbMatcher watchers.
    """
    verbs: list[str] = []
    for matcher in mechanic.watches():
        if isinstance(matcher, VerbMatcher):
            verbs.append(matcher.verb)
    return verbs


def _verb_similarity(candidate_verb: str, target_verb: str) -> float:
    """Return a similarity score in [0.0, 1.0] between two verb strings.

    Uses :class:`difflib.SequenceMatcher` on the lowercased forms so "Open" and
    "open" are treated identically. Kept deliberately simple — this is a
    developer-experience hint for the operator subagent, not a classifier.

    Args:
        candidate_verb: The verb declared by a mechanic's VerbMatcher.
        target_verb: The verb the classifier produced (no matching mechanic).

    Returns:
        Similarity ratio in [0.0, 1.0]; 1.0 is an exact match.
    """
    a = candidate_verb.lower()
    b = target_verb.lower()
    return SequenceMatcher(a=a, b=b).ratio()


def _rank_candidates(
    mechanics: list[Mechanic], classified_verb: str, k: int = TOP_K_CANDIDATES
) -> list[str]:
    """Rank mechanics by verb-name similarity to ``classified_verb`` and return top-K IDs.

    For each mechanic, the score is the maximum similarity across all its
    VerbMatcher verbs (via :func:`_verb_similarity`). Mechanics with no
    VerbMatcher score 0.0. Results are sorted by ``(-score, id)`` so ties
    break alphabetically and ordering is fully deterministic.

    Fallback: if every mechanic scores 0.0 (e.g. the registry holds only
    non-voluntary mechanics or mechanics without VerbMatchers), we return the
    first K mechanic IDs in alphabetical order. This guarantees candidates is
    never empty when mechanics exist, giving the operator a menu even when
    similarity provides no useful signal (per the design note in the module
    docstring).

    Args:
        mechanics: The voluntary mechanics to rank.
        classified_verb: The verb the classifier produced for which no
            mechanic scored above zero.
        k: Maximum number of IDs to return (defaults to :data:`TOP_K_CANDIDATES`).

    Returns:
        Up to ``k`` mechanic IDs, deterministically ordered.
    """
    if not mechanics:
        return []

    scored: list[tuple[str, float]] = []
    for m in mechanics:
        verbs = _mechanic_verbs(m)
        if not verbs:
            scored.append((m.id, 0.0))
            continue
        best = max(_verb_similarity(v, classified_verb) for v in verbs)
        scored.append((m.id, best))

    # Deterministic sort: highest similarity first, alphabetical id on tie.
    scored.sort(key=lambda t: (-t[1], t[0]))

    # Fallback when no similarity signal exists at all: alphabetical first K.
    if scored[0][1] == 0.0:
        return sorted(m.id for m in mechanics)[:k]

    return [mid for mid, _ in scored[:k]]


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
            # D-11: no definitive match — surface top-K closest mechanic IDs by
            # verb-name similarity so the operator has useful context when
            # authoring a new mechanic for the yielded action.
            candidates = _rank_candidates(voluntary, classified.verb)
            return NoMatchResult(classified=classified, candidates=candidates)

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
