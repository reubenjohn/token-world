"""Every authored use case must parse and validate. Empty library → skip."""

from __future__ import annotations

from pathlib import Path

import pytest

from token_world.use_cases import load_use_case, validate_frontmatter
from token_world.use_cases.loader import VALID_ASSERTION_KINDS


def test_library_has_use_cases(use_case_files: list[Path]) -> None:
    """Phase 3 must produce at least 30 use cases (target 35)."""
    if not use_case_files:
        pytest.skip("No use-case files authored yet (Wave 2 pending)")
    assert len(use_case_files) >= 30, f"Only {len(use_case_files)} use cases found (target 35)"


def test_each_use_case_has_valid_frontmatter(use_case_files: list[Path]) -> None:
    if not use_case_files:
        pytest.skip("No use-case files authored yet (Wave 2 pending)")
    all_errors: list[str] = []
    for path in use_case_files:
        fm, _ = load_use_case(path)
        errors = validate_frontmatter(fm, source=str(path))
        all_errors.extend(errors)
    assert not all_errors, "Frontmatter errors:\n" + "\n".join(all_errors)


def test_use_case_ids_are_unique(use_case_files: list[Path]) -> None:
    if not use_case_files:
        pytest.skip("No use-case files authored yet (Wave 2 pending)")
    ids = []
    for path in use_case_files:
        fm, _ = load_use_case(path)
        ids.append(fm.get("id"))
    assert len(set(ids)) == len(ids), f"Duplicate UC IDs: {ids}"


def test_every_authored_assertion_uses_a_valid_kind(use_case_files: list[Path]) -> None:
    """Cross-check: scan all authored UCs, every graph_assertion.kind must be whitelisted."""
    if not use_case_files:
        pytest.skip("No use-case files authored yet")
    bad: list[str] = []
    for path in use_case_files:
        fm, _ = load_use_case(path)
        for obs in fm.get("expected_observations", []) or []:
            for assertion in obs.get("graph_assertions", []) or []:
                kind = assertion.get("kind")
                if kind not in VALID_ASSERTION_KINDS:
                    bad.append(f"{path.name}: {kind!r}")
    assert not bad, "Assertions with invalid kinds in authored UCs:\n" + "\n".join(bad)
