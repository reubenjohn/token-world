"""Regression suite: 35 Phase-3 UC manifests run through the real engine pipeline.

DVAL-03. Each manifest is one parametrized test case that exercises:
    classify (FakeClassifier) -> match (deterministic) -> execute (real mechanics)
    -> conservation -> passive_sweep -> observe (FakeObserver) -> tick summary

Run with: ``uv run pytest -m regression``
Run verbose: ``uv run pytest -m regression -v``

Failures indicate missing mechanics or UC gaps (see manifest's gaps: block).
They are NOT marked xfail — each failure is an actionable signal for future
mechanic authoring or UC revision.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_regression.conftest import exec_graph_builder
from token_world.graph import KnowledgeGraph
from token_world.use_cases.loader import load_use_case

pytestmark = pytest.mark.regression

# ---------------------------------------------------------------------------
# Manifest discovery
# ---------------------------------------------------------------------------

_UC_ROOT = Path(__file__).resolve().parents[2] / ".planning" / "use-cases"
_UC_PATHS = sorted(p for p in _UC_ROOT.rglob("UC-*.md") if p.is_file())


# ---------------------------------------------------------------------------
# Main parametrized test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("manifest_path", _UC_PATHS, ids=lambda p: p.stem)
def test_use_case_regression(manifest_path: Path, build_engine, tmp_path: Path) -> None:
    """Drive one UC manifest through the full engine pipeline and assert outcome.

    For each UC:
    1. Load frontmatter via load_use_case().
    2. Build KnowledgeGraph by exec-ing setup.graph_builder.
    3. Construct SimulationEngine with FakeClassifier + FakeObserver.
    4. Call run_tick with actions[0].intent and actor=actions[0].actor.
    5. Assert result.kind matches expected_outcome mapping.
    6. For "pass" UCs: evaluate graph_assertions against post-tick graph.
    """
    fm, _body = load_use_case(manifest_path)

    if not fm.get("actions"):
        pytest.skip(f"{fm.get('id')}: no actions declared")

    first_action = fm["actions"][0]
    if "classified" not in first_action:
        pytest.skip(f"{fm.get('id')}: missing classified block — add it for regression coverage")

    # Build graph
    kg_db_path = tmp_path / "regression_universe.db"
    kg = KnowledgeGraph(db_path=kg_db_path)
    graph_builder_code = fm["setup"]["graph_builder"]
    exec_graph_builder(graph_builder_code, kg)
    kg.save()

    # Build engine with fake LLM clients and seed mechanics
    classified_dict = first_action["classified"]
    engine = build_engine(kg, classified_dict)

    # Run tick
    actor = first_action["actor"]
    intent = first_action["intent"]
    result = engine.run_tick(intent, actor=actor)

    # Assert outcome
    expected_outcome = fm.get("expected_outcome", "pass")
    kind_map = {"pass": "ok", "yield": "yielded", "blocked": "refused"}
    expected_kind = kind_map[expected_outcome]

    assert result.kind == expected_kind, (
        f"{fm['id']}: expected_outcome={expected_outcome!r} "
        f"→ expected kind={expected_kind!r}, "
        f"got kind={result.kind!r} "
        f"refusal_reason={result.refusal_reason!r}"
    )

    # Graph assertions — only evaluated for "pass" outcomes where the graph
    # was mutated; yield/blocked paths either didn't run or rolled back.
    if expected_kind != "ok":
        return

    observations = fm.get("expected_observations") or []
    if not observations:
        return

    for assertion in observations[0].get("graph_assertions") or []:
        _verify_assertion(assertion, kg, fm["id"])


# ---------------------------------------------------------------------------
# Assertion evaluator
# ---------------------------------------------------------------------------


def _verify_assertion(assertion: dict, kg: KnowledgeGraph, uc_id: str) -> None:
    """Evaluate one graph_assertion dict against the post-tick graph.

    Supports the six VALID_ASSERTION_KINDS from use_cases.loader:
    has_node, has_edge, has_property, property_equals, not_has_edge, not_has_property.
    """
    kind = assertion["kind"]

    if kind == "has_node":
        node = assertion["node"]
        assert kg.has_node(node), f"{uc_id}: missing node {node!r}"

    elif kind == "has_edge":
        src, dst = assertion["src"], assertion["dst"]
        assert kg.has_edge(src, dst), f"{uc_id}: missing edge {src!r}→{dst!r}"

    elif kind == "has_property":
        node = assertion["node"]
        prop = assertion["property"]
        props = kg.query(node)
        assert prop in props, f"{uc_id}: node {node!r} missing property {prop!r}"

    elif kind == "property_equals":
        node = assertion["node"]
        prop = assertion["property"]
        expected = assertion["value"]
        props = kg.query(node)
        actual = props.get(prop)
        assert actual == expected, (
            f"{uc_id}: {node!r}.{prop!r} expected {expected!r}, got {actual!r}"
        )

    elif kind == "not_has_edge":
        src, dst = assertion["src"], assertion["dst"]
        assert not kg.has_edge(src, dst), (
            f"{uc_id}: unexpected edge {src!r}→{dst!r} (should not exist)"
        )

    elif kind == "not_has_property":
        node = assertion["node"]
        prop = assertion["property"]
        props = kg.query(node)
        assert prop not in props, f"{uc_id}: node {node!r} unexpectedly has property {prop!r}"

    else:
        pytest.fail(f"{uc_id}: unsupported assertion kind {kind!r}")
