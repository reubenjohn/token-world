"""Tests for DeterministicMatcher and score_mechanic.

Verifies D-09: deterministic scoring formula (+3 verb, +2 target type, +1 actor type),
alphabetical tie-breaking, NoMatchResult on zero-score, and candidates list.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from token_world.engine.matcher import DeterministicMatcher, score_mechanic
from token_world.engine.models import (
    ClassifiedAction,
    MatchedResult,
    NoMatchResult,
)
from token_world.graph import KnowledgeGraph
from token_world.mechanic.matchers import VerbMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.graph import Mutation
    from token_world.mechanic.context import MechanicContext


# ---------------------------------------------------------------------------
# Minimal Mechanic stubs for tests
# ---------------------------------------------------------------------------


def _make_mechanic(
    mechanic_id: str,
    verb: str | None = None,
    actor_types: list[str] | None = None,
    target_types: list[str] | None = None,
    tags: list[str] | None = None,
) -> Mechanic:
    """Create a minimal concrete Mechanic subclass for testing."""

    class _Stub(Mechanic):
        id = mechanic_id
        description = f"stub mechanic {mechanic_id}"
        voluntary = True

        def check(self, ctx: MechanicContext) -> CheckResult:
            return CheckResult(passed=True)

        def apply(self, ctx: MechanicContext) -> list[Mutation]:
            return []

        def watches(self):
            watchers = []
            if verb is not None:
                watchers.append(VerbMatcher(verb))
            return watchers

    # Attach optional type hints as class attributes
    if actor_types is not None:
        _Stub.actor_types = actor_types  # type: ignore[attr-defined]
    if target_types is not None:
        _Stub.target_types = target_types  # type: ignore[attr-defined]
    if tags is not None:
        _Stub.tags = tags
    return _Stub()


def _make_registry(mechanics: list[Mechanic]) -> MagicMock:
    """Create a mock registry whose voluntary_mechanics() returns the given list."""
    registry = MagicMock()
    registry.voluntary_mechanics.return_value = mechanics
    return registry


def _make_graph(
    actor: str = "alice",
    target: str | None = None,
    actor_props: dict | None = None,
    target_props: dict | None = None,
) -> KnowledgeGraph:
    """Create a minimal graph for matcher tests."""
    kg = KnowledgeGraph(db_path=None)
    a_props = actor_props or {}
    kg.add_node(actor, node_type="agent", **a_props)
    if target is not None:
        t_props = target_props or {}
        kg.add_node(target, node_type="entity", **t_props)
    return kg


# ---------------------------------------------------------------------------
# score_mechanic tests
# ---------------------------------------------------------------------------


class TestScoreMechanic:
    """Tests for the score_mechanic helper."""

    def test_verb_match_scores_3(self) -> None:
        """Verb match contributes +3 to score."""
        mechanic = _make_mechanic("pickup", verb="pickup")
        classified = ClassifiedAction(verb="pickup", actor="alice")
        graph = _make_graph()
        assert score_mechanic(mechanic, classified, graph) == 3

    def test_no_verb_match_scores_0(self) -> None:
        """No verb match contributes 0."""
        mechanic = _make_mechanic("pickup", verb="pickup")
        classified = ClassifiedAction(verb="drop", actor="alice")
        graph = _make_graph()
        assert score_mechanic(mechanic, classified, graph) == 0

    def test_target_type_match_adds_2(self) -> None:
        """Target type match adds +2 when mechanic has target_types hint."""
        mechanic = _make_mechanic("open", verb="open", target_types=["container"])
        classified = ClassifiedAction(verb="open", actor="alice", target="chest")
        graph = _make_graph(target="chest", target_props={"subtype": "container"})
        # verb=3, target_type=2
        assert score_mechanic(mechanic, classified, graph) == 5

    def test_actor_type_match_adds_1(self) -> None:
        """Actor type match adds +1 when mechanic has actor_types hint.

        The graph stores node_type as 'type' on each node. alice is an agent
        node, so graph.query("alice")["type"] == "agent". The mechanic declares
        actor_types=["agent"] so this should score +1 in addition to verb +3.
        """
        mechanic = _make_mechanic("lift", verb="lift", actor_types=["agent"])
        classified = ClassifiedAction(verb="lift", actor="alice")
        # No extra actor_props — node_type="agent" already stores type="agent"
        graph = _make_graph()
        # verb=3, actor_type=1 (type="agent" matches actor_types=["agent"])
        assert score_mechanic(mechanic, classified, graph) == 4

    def test_no_target_skips_target_score(self) -> None:
        """When classified.target is None, no target score is awarded."""
        mechanic = _make_mechanic("rest", verb="rest", target_types=["bed"])
        classified = ClassifiedAction(verb="rest", actor="alice", target=None)
        graph = _make_graph()
        # verb=3 only; target skipped because classified.target is None
        assert score_mechanic(mechanic, classified, graph) == 3


# ---------------------------------------------------------------------------
# DeterministicMatcher.match tests
# ---------------------------------------------------------------------------


class TestDeterministicMatcher:
    """Tests for DeterministicMatcher.match()."""

    def test_single_mechanic_verb_match_returns_matched(self) -> None:
        """Single mechanic with matching verb returns MatchedResult with score 3."""
        mechanic = _make_mechanic("pickup", verb="pickup")
        registry = _make_registry([mechanic])
        graph = _make_graph()
        classified = ClassifiedAction(verb="pickup", actor="alice")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, MatchedResult)
        assert result.mechanic_id == "pickup"
        assert result.score == 3

    def test_two_mechanics_only_one_matches(self) -> None:
        """When two mechanics, only verb-matching one is selected."""
        m_pickup = _make_mechanic("pickup", verb="pickup")
        m_drop = _make_mechanic("drop", verb="drop")
        registry = _make_registry([m_pickup, m_drop])
        graph = _make_graph()
        classified = ClassifiedAction(verb="pickup", actor="alice")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, MatchedResult)
        assert result.mechanic_id == "pickup"

    def test_tie_broken_alphabetically(self) -> None:
        """When two mechanics score equally, alphabetically first id wins."""
        m_alpha = _make_mechanic("alpha_mechanic", verb="use")
        m_zulu = _make_mechanic("zulu_mechanic", verb="use")
        registry = _make_registry([m_zulu, m_alpha])  # reversed order to prove sort
        graph = _make_graph()
        classified = ClassifiedAction(verb="use", actor="alice")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, MatchedResult)
        assert result.mechanic_id == "alpha_mechanic"
        assert "tie-break" in result.reasoning

    def test_no_mechanic_matches_returns_no_match(self) -> None:
        """When no mechanic matches the verb, NoMatchResult is returned."""
        mechanic = _make_mechanic("pickup", verb="pickup")
        registry = _make_registry([mechanic])
        graph = _make_graph()
        classified = ClassifiedAction(verb="fly", actor="alice")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, NoMatchResult)

    def test_empty_registry_returns_no_match(self) -> None:
        """Empty registry returns NoMatchResult with empty candidates."""
        registry = _make_registry([])
        graph = _make_graph()
        classified = ClassifiedAction(verb="pickup", actor="alice")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, NoMatchResult)
        assert result.candidates == []

    def test_target_type_differentiates_tie(self) -> None:
        """Target type match (+2) breaks tie between two verb-matching mechanics."""
        # Both match verb "open" (score +3 each)
        # only "open_container" has target_types=["container"]
        m_generic = _make_mechanic("open_generic", verb="open")
        m_container = _make_mechanic("open_container", verb="open", target_types=["container"])
        registry = _make_registry([m_generic, m_container])
        graph = _make_graph(
            target="chest",
            target_props={"subtype": "container"},
        )
        classified = ClassifiedAction(verb="open", actor="alice", target="chest")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, MatchedResult)
        assert result.mechanic_id == "open_container"
        assert result.score == 5  # verb(3) + target_type(2)

    def test_three_mechanics_top_two_equal_reasoning_mentions_tiebreak(self) -> None:
        """When top two mechanics are tied, reasoning mentions tie-break."""
        m_alpha = _make_mechanic("aaa", verb="push")
        m_beta = _make_mechanic("bbb", verb="push")
        m_gamma = _make_mechanic("ccc", verb="pull")  # different verb — lower score
        registry = _make_registry([m_alpha, m_beta, m_gamma])
        graph = _make_graph()
        classified = ClassifiedAction(verb="push", actor="alice")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, MatchedResult)
        assert result.mechanic_id == "aaa"  # alphabetical winner
        assert "tie-break" in result.reasoning

    def test_classified_target_none_skips_target_scoring(self) -> None:
        """Verb-only action (target=None) works; target score skipped."""
        mechanic = _make_mechanic("rest", verb="rest", target_types=["bed"])
        registry = _make_registry([mechanic])
        graph = _make_graph()
        classified = ClassifiedAction(verb="rest", actor="alice", target=None)

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, MatchedResult)
        assert result.score == 3  # only verb match; no target score

    def test_classified_target_not_in_graph_skips_target_scoring(self) -> None:
        """When classified.target doesn't exist in graph, target score is skipped."""
        mechanic = _make_mechanic("touch", verb="touch", target_types=["entity"])
        registry = _make_registry([mechanic])
        graph = _make_graph()  # no "rock" node added
        classified = ClassifiedAction(verb="touch", actor="alice", target="rock")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, MatchedResult)
        assert result.score == 3  # only verb match

    def test_candidates_in_no_match_result(self) -> None:
        """NoMatchResult.candidates surfaces top-K closest mechanic IDs (D-11).

        When no mechanic matches verb "fly", the matcher returns NoMatchResult with
        ``candidates`` populated by verb-name similarity so the operator subagent
        has useful context. Ordering is deterministic (similarity desc, id asc).
        """
        m_pickup = _make_mechanic("pickup", verb="pickup")
        m_drop = _make_mechanic("drop", verb="drop")
        registry = _make_registry([m_pickup, m_drop])
        graph = _make_graph()
        classified = ClassifiedAction(verb="fly", actor="alice")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, NoMatchResult)
        # D-11: candidates populated with up to TOP_K_CANDIDATES mechanic IDs.
        assert len(result.candidates) >= 1
        assert set(result.candidates) <= {"pickup", "drop"}

    def test_winner_clear_with_positive_runner_up(self) -> None:
        """Winner score 5, runner-up score 3: MatchedResult returned with clear reasoning."""
        # m_best: verb=pickup(+3) + target_types=container → total 5 when target is container
        m_best = _make_mechanic("best", verb="pickup", target_types=["container"])
        # m_second: verb=pickup(+3) only → score 3
        m_second = _make_mechanic("second", verb="pickup")
        # m_zero: verb=drop → score 0
        m_zero = _make_mechanic("zero", verb="drop")
        registry = _make_registry([m_best, m_second, m_zero])
        graph = _make_graph(
            target="chest",
            target_props={"subtype": "container"},
        )
        classified = ClassifiedAction(verb="pickup", actor="alice", target="chest")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, MatchedResult)
        assert result.mechanic_id == "best"
        assert result.score == 5
        # Clear winner (score 5 vs 3) → reasoning says "clear winner"
        assert "clear winner" in result.reasoning


# ---------------------------------------------------------------------------
# D-11 tech-debt closure (IN-01): NoMatchResult.candidates populated with top-K
# closest-matching mechanic IDs by verb-name similarity. See matcher module
# docstring for full design rationale.
# ---------------------------------------------------------------------------


class TestNoMatchCandidates:
    """D-11: NoMatchResult.candidates surfaces top-K closest mechanic IDs."""

    def test_empty_registry_candidates_is_empty(self) -> None:
        """No mechanics in registry → candidates is empty (no crash)."""
        registry = _make_registry([])
        graph = _make_graph()
        classified = ClassifiedAction(verb="fly", actor="alice")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, NoMatchResult)
        assert result.candidates == []

    def test_candidates_ranked_by_verb_similarity(self) -> None:
        """When no exact match, candidates ordered by verb-name similarity desc.

        Classified verb "pickup" has no match, but "picku" (typo-close) should
        outrank "drop" (very different) purely by SequenceMatcher ratio.
        """
        m_typo = _make_mechanic("typo_mech", verb="picku")
        m_far = _make_mechanic("far_mech", verb="drop")
        registry = _make_registry([m_far, m_typo])  # reversed input order
        graph = _make_graph()
        classified = ClassifiedAction(verb="pickup", actor="alice")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, NoMatchResult)
        # "picku" is 5/6 character overlap with "pickup" → higher similarity
        assert result.candidates[0] == "typo_mech"
        assert "far_mech" in result.candidates

    def test_candidates_truncated_to_top_k(self) -> None:
        """When registry has more than K mechanics, only top-K are returned."""
        from token_world.engine.matcher import TOP_K_CANDIDATES

        # Five mechanics, all with different verbs — none match "fly"
        mechs = [_make_mechanic(f"m{i}", verb=f"verb{i}") for i in range(5)]
        registry = _make_registry(mechs)
        graph = _make_graph()
        classified = ClassifiedAction(verb="fly", actor="alice")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, NoMatchResult)
        assert len(result.candidates) == TOP_K_CANDIDATES

    def test_candidates_deterministic_ordering_on_tie(self) -> None:
        """When similarity scores tie, mechanics sort alphabetically by id.

        All three mechanics declare the same verb "ski", so the similarity
        to "fly" is identical for each — ties must be broken by id asc.
        """
        m_c = _make_mechanic("c_mech", verb="ski")
        m_a = _make_mechanic("a_mech", verb="ski")
        m_b = _make_mechanic("b_mech", verb="ski")
        # Registry returns in non-alphabetical order to prove the sort.
        registry = _make_registry([m_c, m_a, m_b])
        graph = _make_graph()
        classified = ClassifiedAction(verb="fly", actor="alice")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, NoMatchResult)
        assert result.candidates == ["a_mech", "b_mech", "c_mech"]

    def test_candidates_fallback_when_no_verbmatcher(self) -> None:
        """When no mechanic declares a VerbMatcher, fall back to alphabetical top-K.

        Design: a trivial similarity metric that scores everything equally at
        0.0 adds no operator value; surfacing an alphabetical menu at least
        gives them a starting point.
        """
        # verb=None → _make_mechanic emits no VerbMatcher
        m_z = _make_mechanic("z_mech")
        m_a = _make_mechanic("a_mech")
        m_b = _make_mechanic("b_mech")
        registry = _make_registry([m_z, m_a, m_b])
        graph = _make_graph()
        classified = ClassifiedAction(verb="fly", actor="alice")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, NoMatchResult)
        # Fallback: alphabetical order, truncated to K (here K=3).
        assert result.candidates == ["a_mech", "b_mech", "z_mech"]

    def test_candidates_empty_when_match_succeeds(self) -> None:
        """Sanity: MatchedResult path does not populate candidates (separate model)."""
        mechanic = _make_mechanic("pickup", verb="pickup")
        registry = _make_registry([mechanic])
        graph = _make_graph()
        classified = ClassifiedAction(verb="pickup", actor="alice")

        result = DeterministicMatcher().match(classified, registry, graph)

        assert isinstance(result, MatchedResult)
        # MatchedResult has no candidates field — this is just confirming the
        # successful-match path doesn't accidentally route through the D-11 branch.
        assert result.mechanic_id == "pickup"
