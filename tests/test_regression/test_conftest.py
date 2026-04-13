"""RED-phase tests for regression-suite scaffolding fixtures.

Tests 1-4 verify: exec_graph_builder isolation, FakeClassifier, FakeObserver,
and build_engine fixture. These run before conftest.py is fully authored to
confirm the RED state, then go GREEN once conftest.py is written.
"""

from __future__ import annotations

import pytest


def test_conftest_exposes_build_engine_fixture(build_engine) -> None:
    """build_engine fixture returns a callable that constructs a SimulationEngine."""
    from token_world.graph import KnowledgeGraph

    kg = KnowledgeGraph()
    classified_dict = {"verb": "look", "target": None}
    engine = build_engine(kg, classified_dict)

    # Must be a SimulationEngine instance
    from token_world.engine.engine import SimulationEngine

    assert isinstance(engine, SimulationEngine)
    # Must have fake classifier and observer wired (not real Anthropic ones)
    from tests.test_regression.conftest import FakeClassifier, FakeObserver

    assert isinstance(engine._classifier, FakeClassifier)
    assert isinstance(engine._observer, FakeObserver)


def test_conftest_exec_graph_builder_isolated_namespace() -> None:
    """exec_graph_builder runs code against kg with restricted namespace."""
    from tests.test_regression.conftest import exec_graph_builder
    from token_world.graph import KnowledgeGraph

    kg = KnowledgeGraph()
    exec_graph_builder('kg.add_node("a", node_type="entity")', kg)
    assert kg.has_node("a")


def test_conftest_exec_graph_builder_no_import() -> None:
    """exec_graph_builder raises NameError when code tries __import__."""
    from tests.test_regression.conftest import exec_graph_builder
    from token_world.graph import KnowledgeGraph

    kg = KnowledgeGraph()
    with pytest.raises((NameError, AttributeError)):
        exec_graph_builder('__import__("os").getcwd()', kg)


def test_fake_classifier_returns_manifest_classified(build_engine) -> None:
    """FakeClassifier.classify returns VerdictOk with the classified_dict fields."""
    from tests.test_regression.conftest import FakeClassifier
    from token_world.engine.models import VerdictOk

    classified_dict = {"verb": "look", "target": "room", "actor": "alice"}
    fake = FakeClassifier(classified_dict)
    result = fake.classify(
        "look around",
        "alice",
        available_verbs=["look"],
        known_node_ids=["alice", "room"],
        min_confidence=0.5,
    )
    assert isinstance(result, VerdictOk)
    assert result.classified.verb == "look"
    assert result.classified.actor == "alice"
    assert result.confidence == 0.99


def test_fake_observer_returns_fixed_string() -> None:
    """FakeObserver.synthesize returns 'Action succeeded.' regardless of inputs."""
    from tests.test_regression.conftest import FakeObserver

    fake = FakeObserver()
    result = fake.synthesize(
        projection={},
        trace=None,
        refusal_narrative=None,
        actor_id="alice",
        action_text="walk east",
    )
    assert result == "Action succeeded."


def test_fake_observer_returns_refusal_narrative_when_provided() -> None:
    """FakeObserver returns the refusal_narrative verbatim when provided."""
    from tests.test_regression.conftest import FakeObserver

    fake = FakeObserver()
    result = fake.synthesize(
        projection={},
        trace=None,
        refusal_narrative="You cannot do that.",
        actor_id="alice",
        action_text="walk east",
    )
    assert result == "You cannot do that."
