"""Tests for compute_overlap() and compute_overlap_report() (SC-5/EMERGE-01)."""

from __future__ import annotations

from types import SimpleNamespace

from token_world.operator.overlap import compute_overlap, compute_overlap_report


def _mech(id: str, verb: str | None = None, watches: list[str] | None = None):
    """Create a mock mechanic info object."""
    return SimpleNamespace(id=id, verb=verb, watches=watches)


# ---------------------------------------------------------------------------
# test_exact_verb_match
# ---------------------------------------------------------------------------


def test_exact_verb_match() -> None:
    registry = [_mech("pet_animal", verb="pet")]
    score = compute_overlap("pet", [], registry)
    assert score == 1.0


# ---------------------------------------------------------------------------
# test_no_overlap
# ---------------------------------------------------------------------------


def test_no_overlap() -> None:
    registry = [_mech("look_around", verb="look")]
    score = compute_overlap("explode", [], registry)
    assert score < 0.1


# ---------------------------------------------------------------------------
# test_partial_verb_overlap
# ---------------------------------------------------------------------------


def test_partial_verb_overlap() -> None:
    # "pick up" vs "pick item" — shares "pick" token
    registry = [_mech("pickup", verb="pick item")]
    score = compute_overlap("pick up", [], registry)
    # Jaccard of {"pick","up"} vs {"pick","item"} = 1/3
    assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# test_watches_overlap
# ---------------------------------------------------------------------------


def test_watches_overlap() -> None:
    registry = [_mech("examine_obj", verb="examine", watches=["located_in", "description"])]
    score = compute_overlap("examine", ["located_in", "description"], registry)
    assert score == 1.0


# ---------------------------------------------------------------------------
# test_empty_registry
# ---------------------------------------------------------------------------


def test_empty_registry() -> None:
    score = compute_overlap("pet", ["located_in"], [])
    assert score == 0.0


# ---------------------------------------------------------------------------
# test_overlap_report_contains_mechanic_id
# ---------------------------------------------------------------------------


def test_overlap_report_contains_mechanic_id() -> None:
    registry = [
        _mech("pet_animal", verb="pet"),
        _mech("look_around", verb="look"),
    ]
    report = compute_overlap_report("pet", [], registry)
    assert "pet_animal" in report
    # Should recommend editing since score >= 0.7
    assert "RECOMMENDATION" in report or "edit" in report.lower()
