"""Parametrized integration harness over Phase-3 use-case manifests (TEST-02).

The harness is the end-to-end fitness function for Phase 4's seed mechanics:
it consumes every ``.planning/use-cases/**/UC-*.md`` manifest as a single
parametrized pytest case and branches explicitly on the manifest's
``expected_outcome`` (D-29b tri-state model):

    - ``blocked`` -> ``pytest.skip`` with the blocking framework-gap reason.
    - ``yield``   -> ``pytest.xfail`` when no voluntary mechanic matches
                     the classified verb (the common case for today's
                     pre-seed state). If a mechanic DID fire, the
                     assertion chain still runs: the UC is ready to flip
                     from ``yield`` to ``pass`` via a one-line frontmatter
                     edit.
    - ``pass``    -> ``pytest.fail`` when no mechanic matches;
                     otherwise run the full assertion chain.
    - missing     -> treated as ``pass`` (default).

Deferred-safety properties:

    - Import safety (W9): :func:`_discover_cases` is wrapped so a
      catastrophic discovery failure degrades to a single skipped param
      rather than an ``ImportError`` that poisons all other pytest
      collection.
    - Malformed manifests (W9): load or schema errors are turned into
      per-manifest ``pytest.mark.skip`` params so the remaining 34 cases
      still collect cleanly.
    - Diagnostics exercise (W2): every run opens a
      :meth:`DiagnosticsSink.open_tick` context and writes a summary with
      ``uc_id``, proving the Phase-4 consumer side of the D-23 API.

Matcher scope (downstream-review gate): this module intentionally keeps
:func:`match_mechanic_for_verb` as a *single, named, self-contained*
helper. Plan-local matcher extensions (alias lookup, tag fallback,
``blocked_by`` routing, refusal narratives) are out of scope for this
plan -- they belong in the post-plan centralized matcher gate
(``tests/test_mechanic/test_harness_matcher.py``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic import (
    ChainExecutionEngine,
    MechanicContext,
    MechanicInfo,
    MechanicRegistry,
)
from token_world.use_cases.loader import load_use_case, validate_frontmatter

from .conftest import CATEGORIES, SEEDS_DIR, USE_CASES_DIR


# ---------------------------------------------------------------------------
# Public helpers (stable import paths for the post-plan matcher gate)
# ---------------------------------------------------------------------------


def match_mechanic_for_verb(
    registry: MechanicRegistry,
    verb: str,
) -> MechanicInfo | None:
    """Naive verb -> voluntary-mechanic matcher for the v1 harness.

    Returns the first voluntary mechanic whose ``id`` equals *verb*, or
    ``None`` when no match exists. Phase 5 replaces this stub with a
    proper classifier-driven router.

    This helper is intentionally self-contained so the downstream
    centralized matcher gate (``tests/test_mechanic/test_harness_matcher.py``)
    can import it, document the contract, and test it in isolation
    without surgery on the harness body.

    Contract:
        - *verb* is NOT normalized (no case folding, no whitespace
          strip, no alias resolution). Callers are responsible for
          handing in a canonical verb string.
        - Returns the FIRST voluntary :class:`MechanicInfo` whose
          ``id`` equals *verb*, scanning ``registry.list_mechanics()``
          in its native sort order (sorted by id today).
        - Returns ``None`` when *verb* is empty/falsy.
        - Returns ``None`` when no voluntary mechanic's ``id`` equals
          *verb*.
        - Involuntary mechanics (``voluntary=False``) are NEVER
          returned, even if their ``id`` matches *verb*. Involuntary
          mechanics are driven by the ``ChainExecutionEngine``, not by
          classified-action routing.

    Extension Policy:
        Any future extension (alias lookup, tag fallback, ``blocked_by``
        routing, refusal-narrative synthesis, classifier-driven
        routing) MUST ship with a new test case in
        ``tests/test_mechanic/test_harness_matcher.py`` -- plan-local
        matcher changes in seed plans (04-06..04-11) are explicitly
        disallowed. This stops the accumulation of fragile,
        unreviewable matcher edits across clusters. See
        ``.planning/phases/04-llm-mechanic-generation/04-REVIEWS.md``
        HIGH #1 for the rationale and
        ``.planning/phases/04-llm-mechanic-generation/04-04-SUMMARY.md``
        "Harness Matcher -- Extension Contract" for the owner-plan
        table.

        When the v1 stub is replaced by Phase 5's classifier-driven
        router, retire this helper in favor of that router; keep the
        test file as the contract-regression guard.

    Args:
        registry: A populated :class:`MechanicRegistry`.
        verb: The classified verb from a use-case action.

    Returns:
        The matching :class:`MechanicInfo`, or ``None``.

    See also:
        ``tests/test_mechanic/test_harness_matcher.py`` -- the
        contract-regression guard. Every behavior described above is
        covered there; every future extension adds a case there FIRST.
    """
    if not verb:
        return None
    for info in registry.list_mechanics():
        if info.voluntary and info.id == verb:
            return info
    return None


# ---------------------------------------------------------------------------
# Outcome classification
# ---------------------------------------------------------------------------


def _classify_outcome(fm: dict) -> tuple[str, str | None]:
    """Return ``(outcome, blocked_reason)`` from a manifest's frontmatter.

    Default: ``"pass"`` when ``expected_outcome`` is absent. For the
    ``blocked`` branch the first engine-layer address-now gap summary
    is used as the skip reason, falling back to a generic string.
    """
    outcome = fm.get("expected_outcome") or "pass"
    if outcome == "blocked":
        for gap in fm.get("gaps", []) or []:
            if not isinstance(gap, dict):
                continue
            if gap.get("layer") == "engine" and gap.get("severity") == "address-now":
                return outcome, gap.get("summary", "engine-layer framework gap")
        return outcome, "framework gap"
    return outcome, None


# ---------------------------------------------------------------------------
# Collection-time discovery (W9: import-safe)
# ---------------------------------------------------------------------------


def _discover_cases() -> list:
    """Collect ``pytest.param`` entries for every manifest under USE_CASES_DIR.

    Called once at module import. Load or schema errors collapse to a
    single ``pytest.mark.skip`` param for that manifest rather than
    poisoning the whole collection. The caller additionally wraps this
    function in a try/except -- a catastrophic failure (e.g., missing
    USE_CASES_DIR) degrades to a single ``discovery-failed`` skip.
    """
    params: list[Any] = []
    for category in CATEGORIES:
        cat_dir = USE_CASES_DIR / category
        if not cat_dir.is_dir():
            continue
        for path in sorted(cat_dir.glob("UC-*.md")):
            try:
                fm, _body = load_use_case(path)
            except Exception as e:  # noqa: BLE001 -- intentional broad catch
                params.append(
                    pytest.param(
                        path,
                        id=f"{path.stem}-LOAD-ERROR",
                        marks=pytest.mark.skip(
                            reason=f"manifest load failed: {e!r}"
                        ),
                    )
                )
                continue
            errs = validate_frontmatter(fm, source=str(path))
            if errs:
                params.append(
                    pytest.param(
                        path,
                        id=f"{path.stem}-SCHEMA-ERROR",
                        marks=pytest.mark.skip(reason="; ".join(errs)),
                    )
                )
                continue
            uc_id = fm.get("id") or path.stem
            # Collection-time markers are a soft hint; the test body
            # does the authoritative outcome branching (W5).
            params.append(pytest.param(path, id=uc_id))
    return params


try:
    _PARAMS = _discover_cases()
    if not _PARAMS:
        _PARAMS = [
            pytest.param(
                Path("(no-manifests-found)"),
                id="no-manifests-found",
                marks=pytest.mark.skip(reason="no use-case manifests discovered"),
            )
        ]
except Exception as _disc_err:  # pragma: no cover -- defensive W9 outer wrap
    _PARAMS = [
        pytest.param(
            Path("(discovery-failed)"),
            id="discovery-failed",
            marks=pytest.mark.skip(reason=f"_discover_cases raised: {_disc_err!r}"),
        )
    ]


# ---------------------------------------------------------------------------
# Graph assertion dispatcher
# ---------------------------------------------------------------------------


def _edge_props(kg: KnowledgeGraph, src: str, dst: str) -> dict | None:
    """Return the edge's property dict, or ``None`` if absent.

    Reaches into ``kg._graph`` for *read-only* edge-attr access; the
    project convention "all mutations via the public API" applies to
    writes, not reads, and there is no public edge-property getter
    today. If a public accessor is added later, migrate this helper.
    """
    if not kg.has_edge(src, dst):
        return None
    return dict(kg._graph[src][dst])


def _run_graph_assertion(kg: KnowledgeGraph, assertion: dict, uc_id: str) -> None:
    """Dispatch a single ``graph_assertion`` entry against *kg*.

    Unknown ``kind`` values are ignored (forward-compat).
    """
    kind = assertion.get("kind")
    if kind == "has_node":
        node = assertion["node"]
        assert kg.has_node(node), f"{uc_id}: expected node {node!r} missing"
    elif kind == "has_edge":
        src = assertion["src"]
        dst = assertion["dst"]
        relation = assertion.get("relation")
        if relation is None:
            assert kg.has_edge(src, dst), (
                f"{uc_id}: expected edge {src}->{dst} missing"
            )
        else:
            props = _edge_props(kg, src, dst)
            assert props is not None, (
                f"{uc_id}: expected edge {src}-[{relation}]->{dst} missing"
            )
            assert props.get("relation") == relation, (
                f"{uc_id}: edge {src}->{dst} relation="
                f"{props.get('relation')!r} (expected {relation!r})"
            )
    elif kind == "not_has_edge":
        src = assertion["src"]
        dst = assertion["dst"]
        relation = assertion.get("relation")
        if relation is None:
            assert not kg.has_edge(src, dst), (
                f"{uc_id}: unexpected edge {src}->{dst} present"
            )
        else:
            props = _edge_props(kg, src, dst)
            if props is not None:
                assert props.get("relation") != relation, (
                    f"{uc_id}: unexpected edge "
                    f"{src}-[{relation}]->{dst} still present"
                )
    elif kind == "has_property":
        node = assertion["node"]
        prop = assertion["property"]
        expected = assertion.get("value")
        if not kg.has_node(node):
            raise AssertionError(
                f"{uc_id}: has_property asserted on missing node {node!r}"
            )
        props = kg.query(node)
        assert prop in props, (
            f"{uc_id}: property {prop!r} missing on {node!r}"
        )
        if expected is not None:
            assert props[prop] == expected, (
                f"{uc_id}: {node}.{prop}={props[prop]!r} != {expected!r}"
            )
    elif kind == "property_equals":
        node = assertion["node"]
        prop = assertion["property"]
        expected = assertion.get("value")
        props = kg.query(node)
        assert props.get(prop) == expected, (
            f"{uc_id}: {node}.{prop}={props.get(prop)!r} != {expected!r}"
        )
    elif kind == "not_has_property":
        node = assertion["node"]
        prop = assertion["property"]
        if kg.has_node(node):
            props = kg.query(node)
            assert prop not in props, (
                f"{uc_id}: property {prop!r} unexpectedly present on {node!r}"
            )
    # Unknown kinds: silently skip (schema validator already enforces the
    # 6-kind vocabulary at frontmatter-load time).


# ---------------------------------------------------------------------------
# The parametrized test
# ---------------------------------------------------------------------------


def _build_registry() -> MechanicRegistry:
    """Construct the stock seed registry (D-11 seeds live under SEEDS_DIR)."""
    # ``universe_dir`` must contain the mechanics dir for git-log to work;
    # SEEDS_DIR.parent points at src/token_world/mechanic/ which is fine
    # for this read-only harness (git log is not exercised here).
    return MechanicRegistry(SEEDS_DIR, universe_dir=SEEDS_DIR.parent)


@pytest.mark.parametrize("use_case_path", _PARAMS)
def test_use_case(
    use_case_path: Path,
    harness_kg: KnowledgeGraph,
    diagnostics_sink,
) -> None:
    """Run a single use case with explicit outcome branching (W5).

    The test body is the *authoritative* branch dispatcher; pytest
    collection markers (above) are only a soft hint used for load /
    schema errors.
    """
    fm, _body = load_use_case(use_case_path)
    uc_id = fm.get("id") or use_case_path.stem
    outcome, blocked_reason = _classify_outcome(fm)

    # Open a diagnostics tick BEFORE any work (W2). ``hash(uc_id)`` gives
    # a stable pseudo-tick within a single test run; the sink is rooted
    # at tmp_path so cross-test collisions are impossible.
    pseudo_tick = abs(hash(uc_id)) % 100000
    with diagnostics_sink.open_tick(pseudo_tick) as tick_ctx:
        tick_ctx.write_action(f"UC harness: {uc_id}")
        mechanics_fired: list[str] = []

        # Blocked cases skip BEFORE any engine work (no need to exec
        # graph_builder or load seeds when the outcome is predetermined).
        if outcome == "blocked":
            tick_ctx.set_summary(
                uc_id=uc_id,
                outcome="blocked",
                mechanics_fired=[],
                reason=blocked_reason or "framework gap",
            )
            pytest.skip(
                f"{uc_id}: blocked by {blocked_reason or 'framework gap'}"
            )

        # 1. Build the setup graph. Builder errors surface as pytest.fail
        # with the UC id + short error context (Pitfall 3).
        builder_src = (fm.get("setup") or {}).get("graph_builder", "")
        try:
            exec(
                compile(builder_src, str(use_case_path), "exec"),
                {"kg": harness_kg},
            )
        except Exception as e:  # noqa: BLE001 -- tests swallow to pytest.fail
            tick_ctx.set_summary(
                uc_id=uc_id,
                outcome="error",
                mechanics_fired=[],
            )
            pytest.fail(
                f"{uc_id}: setup.graph_builder invalid: "
                f"{type(e).__name__}: {e}"
            )

        # 2. Build the registry over the stock seed mechanics.
        registry = _build_registry()

        # 3. For each action, naive match on verb -> voluntary mechanic;
        # Phase 5 replaces this with classifier-driven routing.
        involuntary = [
            registry.get_mechanic(info.id)
            for info in registry.list_mechanics()
            if not info.voluntary
        ]
        engine = ChainExecutionEngine(involuntary)

        any_mechanic_fired = False
        for action in fm.get("actions") or []:
            if not isinstance(action, dict):
                continue
            actor = action.get("actor")
            classified = action.get("classified") or {}
            verb = classified.get("verb")
            target = classified.get("target") or classified.get("indirect_object")
            if not verb or not target or not actor:
                continue
            matched = match_mechanic_for_verb(registry, verb)
            if matched is None:
                continue
            mechanic_instance = registry.get_mechanic(matched.id)
            ctx = MechanicContext(harness_kg, actor=actor, target=target)
            try:
                trace = engine.execute(mechanic_instance, ctx)
            except Exception as e:  # noqa: BLE001
                tick_ctx.set_summary(
                    uc_id=uc_id,
                    outcome="error",
                    mechanics_fired=mechanics_fired,
                )
                pytest.fail(
                    f"{uc_id}: mechanic {matched.id!r} raised "
                    f"{type(e).__name__}: {e}"
                )
            if trace.root.check_result.passed:
                any_mechanic_fired = True
                mechanics_fired.append(matched.id)

        # 4. Record the final summary BEFORE the outcome branch (W2).
        tick_ctx.set_summary(
            uc_id=uc_id,
            outcome=outcome,
            mechanics_fired=mechanics_fired,
        )

        # 5. Explicit outcome branching (W5).
        if outcome == "yield":
            if not any_mechanic_fired:
                pytest.xfail(
                    f"{uc_id}: no matching mechanic - expected yield "
                    f"(resolve via authoring or Phase 5 classifier)"
                )
            # else fall through to assertions; a firing mechanic means
            # the UC is ready to flip from yield to pass.
        elif outcome == "pass":
            if not any_mechanic_fired:
                pytest.fail(
                    f"{uc_id}: expected mechanic to match but none did"
                )
            # fall through to assertions

        # 6. Assert graph expectations for any case that reached here.
        for obs in fm.get("expected_observations") or []:
            if not isinstance(obs, dict):
                continue
            for assertion in obs.get("graph_assertions") or []:
                if isinstance(assertion, dict):
                    _run_graph_assertion(harness_kg, assertion, uc_id)
