"""Tests for ConservationChecker and ConservationVerdict (D-16, GAP-ENG06, Plan 05-06).

TDD order: tests written before implementation. Run RED first (no conservation.py yet),
then GREEN after implementation.

Test structure:
 1-3   Disabled checker behaviour (empty conserved_properties)
 4-7   Core verification logic
 8-11  Soft-fail / defensive loader tests
12     Integration shape with RefusalTemplate
13-15  Scaffold integration (Task 2)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from token_world.graph.models import Mutation

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mutation(
    *,
    type: str = "set_property",
    target: str = "alice",
    property: str | None = "coin",
    old_value=0,
    new_value=10,
) -> Mutation:
    return Mutation(
        type=type,
        target=target,
        property=property,
        old_value=old_value,
        new_value=new_value,
    )


# ---------------------------------------------------------------------------
# Tests 1-3: Disabled checker behaviour
# ---------------------------------------------------------------------------


def test_disabled_checker_returns_ok_for_empty_yaml_file(tmp_path: Path) -> None:
    """A conservation.yaml with conserved_properties: [] yields a disabled checker."""
    from token_world.engine.conservation import ConservationChecker

    config = tmp_path / "conservation.yaml"
    config.write_text("conserved_properties: []\n", encoding="utf-8")

    checker = ConservationChecker.from_yaml(config)
    verdict = checker.verify([_make_mutation()])
    assert not verdict.is_violation


def test_disabled_checker_returns_ok_when_yaml_missing(tmp_path: Path) -> None:
    """Missing conservation.yaml yields a disabled checker — no enforcement."""
    from token_world.engine.conservation import ConservationChecker

    checker = ConservationChecker.from_yaml(tmp_path / "nonexistent.yaml")
    assert checker.conserved_properties == frozenset()
    verdict = checker.verify([_make_mutation()])
    assert not verdict.is_violation


def test_disabled_checker_short_circuits_o1(tmp_path: Path) -> None:
    """Disabled checker must return ok() in O(1) — it must NOT iterate mutations.

    This is the D-16 zero-cost guarantee for universes that don't opt-in to
    conservation. We don't time this (flaky), but we document the intent and
    verify the result with a large mutation list so any accidental O(n)
    iteration would at least not crash.
    """
    from token_world.engine.conservation import ConservationChecker

    config = tmp_path / "conservation.yaml"
    config.write_text("conserved_properties: []\n", encoding="utf-8")

    checker = ConservationChecker.from_yaml(config)
    big_mutations = [_make_mutation(target=f"node_{i}") for i in range(1000)]
    verdict = checker.verify(big_mutations)
    assert not verdict.is_violation


# ---------------------------------------------------------------------------
# Tests 4-7: Core verification logic
# ---------------------------------------------------------------------------


def test_violation_when_increment_with_no_decrement(tmp_path: Path) -> None:
    """Net non-zero delta on a conserved property triggers a violation."""
    from token_world.engine.conservation import ConservationChecker

    config = tmp_path / "conservation.yaml"
    config.write_text("conserved_properties: [coin]\n", encoding="utf-8")

    checker = ConservationChecker.from_yaml(config)
    mutations = [_make_mutation(target="alice", property="coin", old_value=10, new_value=15)]
    verdict = checker.verify(mutations)

    assert verdict.is_violation is True
    assert verdict.violations == {"coin": 5.0}


def test_no_violation_when_increment_and_decrement_cancel(tmp_path: Path) -> None:
    """Balanced increment + decrement on the same property within a tick is OK."""
    from token_world.engine.conservation import ConservationChecker

    config = tmp_path / "conservation.yaml"
    config.write_text("conserved_properties: [coin]\n", encoding="utf-8")

    checker = ConservationChecker.from_yaml(config)
    mutations = [
        _make_mutation(target="alice", property="coin", old_value=10, new_value=15),  # +5
        _make_mutation(target="bob", property="coin", old_value=5, new_value=0),  # -5
    ]
    verdict = checker.verify(mutations)
    assert not verdict.is_violation


def test_unrelated_property_changes_ignored(tmp_path: Path) -> None:
    """Mutations to non-conserved properties do not affect the verdict."""
    from token_world.engine.conservation import ConservationChecker

    config = tmp_path / "conservation.yaml"
    config.write_text("conserved_properties: [coin]\n", encoding="utf-8")

    checker = ConservationChecker.from_yaml(config)
    # health changes — not conserved
    mutations = [_make_mutation(target="alice", property="health", old_value=100, new_value=90)]
    verdict = checker.verify(mutations)
    assert not verdict.is_violation


def test_non_setproperty_mutations_ignored(tmp_path: Path) -> None:
    """Structural mutations (add_edge, add_node, etc.) are not conservation events."""
    from token_world.engine.conservation import ConservationChecker

    config = tmp_path / "conservation.yaml"
    config.write_text("conserved_properties: [coin]\n", encoding="utf-8")

    checker = ConservationChecker.from_yaml(config)
    mutations = [
        Mutation(
            type="add_edge",
            target="alice->rock",
            property=None,
            old_value=None,
            new_value=None,
        )
    ]
    verdict = checker.verify(mutations)
    assert not verdict.is_violation


# ---------------------------------------------------------------------------
# Tests 8-11: Soft-fail / defensive loader
# ---------------------------------------------------------------------------


def test_malformed_yaml_disables_enforcement_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Unparseable YAML logs a warning and returns a disabled checker."""
    import logging

    from token_world.engine.conservation import ConservationChecker

    config = tmp_path / "conservation.yaml"
    config.write_text(": invalid: yaml: ::\n", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="token_world.engine.conservation"):
        checker = ConservationChecker.from_yaml(config)

    assert checker.conserved_properties == frozenset()
    assert caplog.records, "Expected a WARNING log about malformed YAML"


def test_yaml_root_not_mapping_disables_enforcement(tmp_path: Path) -> None:
    """YAML root that is a list disables enforcement."""
    from token_world.engine.conservation import ConservationChecker

    config = tmp_path / "conservation.yaml"
    config.write_text("- just\n- a list\n", encoding="utf-8")

    checker = ConservationChecker.from_yaml(config)
    assert checker.conserved_properties == frozenset()


def test_yaml_conserved_properties_not_list_disables_enforcement(tmp_path: Path) -> None:
    """conserved_properties: 'coin' (string not list) disables enforcement."""
    from token_world.engine.conservation import ConservationChecker

    config = tmp_path / "conservation.yaml"
    config.write_text('conserved_properties: "coin"\n', encoding="utf-8")

    checker = ConservationChecker.from_yaml(config)
    assert checker.conserved_properties == frozenset()


def test_non_numeric_property_value_warns_and_skips(tmp_path: Path) -> None:
    """String-valued conserved-property mutation issues UserWarning and is skipped."""
    from token_world.engine.conservation import ConservationChecker

    config = tmp_path / "conservation.yaml"
    config.write_text("conserved_properties: [coin]\n", encoding="utf-8")

    checker = ConservationChecker.from_yaml(config)
    mutations = [
        Mutation(
            type="set_property",
            target="alice",
            property="coin",
            old_value="ten",
            new_value="fifteen",
        )
    ]

    with pytest.warns(UserWarning, match="non-numeric"):
        verdict = checker.verify(mutations)

    # Skipped, not a violation
    assert not verdict.is_violation


# ---------------------------------------------------------------------------
# Test 12: Integration shape with RefusalTemplate
# ---------------------------------------------------------------------------


def test_violation_dict_used_with_refusal_template() -> None:
    """Prove ConservationVerdict.violations integrates with the refusal template (Plan 05-08 shape).

    This test documents the exact call pattern the orchestrator will use.
    """
    from token_world.engine.conservation import ConservationVerdict
    from token_world.engine.refusal import RefusalTemplate

    verdict = ConservationVerdict.violation({"coin": 5.0})
    narrative = RefusalTemplate.render(
        "conservation_violation",
        {"violated_property": next(iter(verdict.violations))},
    )
    assert "coin" in narrative
    assert verdict.is_violation is True
    assert verdict.violations == {"coin": 5.0}


# ---------------------------------------------------------------------------
# Tests 13-15: Scaffold integration (Task 2 — conservation_yaml template)
# ---------------------------------------------------------------------------


def test_scaffold_creates_conservation_yaml(tmp_path: Path) -> None:
    """scaffold_universe creates conservation.yaml in the universe folder."""
    from token_world.universe.scaffold import scaffold_universe

    universe_dir = tmp_path / "my_universe"
    universe_dir.mkdir()
    scaffold_universe(universe_dir, name="My Universe", slug="my_universe")

    conservation_path = universe_dir / "conservation.yaml"
    assert conservation_path.exists(), "conservation.yaml not created by scaffold"

    content = yaml.safe_load(conservation_path.read_text(encoding="utf-8"))
    assert content is not None
    assert "conserved_properties" in content
    assert content["conserved_properties"] == []


def test_scaffold_does_not_overwrite_existing_conservation_yaml(tmp_path: Path) -> None:
    """scaffold_universe is idempotent — never overwrites existing conservation.yaml."""
    from token_world.universe.scaffold import scaffold_universe

    universe_dir = tmp_path / "my_universe"
    universe_dir.mkdir()

    # Pre-write a customised conservation.yaml
    conservation_path = universe_dir / "conservation.yaml"
    conservation_path.write_text("conserved_properties: [coin]\n", encoding="utf-8")

    scaffold_universe(universe_dir, name="My Universe", slug="my_universe")

    content = yaml.safe_load(conservation_path.read_text(encoding="utf-8"))
    assert content["conserved_properties"] == ["coin"], (
        "scaffold_universe must not overwrite an existing conservation.yaml"
    )


def test_scaffold_conservation_yaml_loads_into_disabled_checker(tmp_path: Path) -> None:
    """Round-trip: fresh scaffold → from_yaml → disabled checker (conserved_properties empty)."""
    from token_world.engine.conservation import ConservationChecker
    from token_world.universe.scaffold import scaffold_universe

    universe_dir = tmp_path / "my_universe"
    universe_dir.mkdir()
    scaffold_universe(universe_dir, name="My Universe", slug="my_universe")

    checker = ConservationChecker.from_yaml(universe_dir / "conservation.yaml")
    assert checker.conserved_properties == frozenset(), (
        "A freshly scaffolded universe should have no conserved properties — opt-in design"
    )
