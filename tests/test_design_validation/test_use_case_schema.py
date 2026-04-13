"""Every authored use case must parse and validate. Empty library → skip."""

from __future__ import annotations

from pathlib import Path

import pytest

from token_world.use_cases import load_use_case, validate_frontmatter
from token_world.use_cases.loader import (
    VALID_ASSERTION_KINDS,
    VALID_EXPECTED_OUTCOMES,
)


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


def test_load_use_case_accepts_crlf_frontmatter(tmp_path: Path) -> None:
    """M-04 regression: files saved with CRLF line endings must load cleanly.

    Windows/VSCode authors typically produce CRLF-delimited markdown. The
    loader's framing check (``text.startswith('---\\n')``) is strict, so
    the loader pre-normalises line endings before inspecting them. Without
    that normalisation, a CRLF-encoded use-case would raise 'missing YAML
    frontmatter' even though the YAML itself is valid.
    """
    content_lf = (
        "---\n"
        "id: UC-S01\n"
        "category: spatial\n"
        "title: test\n"
        "status: draft\n"
        "setup:\n"
        "  graph_builder: \"\"\n"
        "actions: []\n"
        "expected_observations: []\n"
        "gaps: []\n"
        "---\n"
        "body\n"
    )
    path = tmp_path / "UC-S01-crlf.md"
    path.write_bytes(content_lf.replace("\n", "\r\n").encode("utf-8"))
    fm, body = load_use_case(path)
    assert fm["id"] == "UC-S01"
    assert "body" in body


def test_load_use_case_accepts_legacy_mac_cr_frontmatter(tmp_path: Path) -> None:
    """M-04 regression (bonus): bare ``\\r`` line endings (legacy Mac) are also
    normalised before the framing check."""
    content_lf = (
        "---\n"
        "id: UC-S02\n"
        "category: spatial\n"
        "title: test\n"
        "status: draft\n"
        "setup:\n"
        "  graph_builder: \"\"\n"
        "actions: []\n"
        "expected_observations: []\n"
        "gaps: []\n"
        "---\n"
        "body\n"
    )
    path = tmp_path / "UC-S02-cr.md"
    path.write_bytes(content_lf.replace("\n", "\r").encode("utf-8"))
    fm, body = load_use_case(path)
    assert fm["id"] == "UC-S02"
    assert "body" in body


# ----------------------------------------------------------------------
# 04-04 Task 1: optional expected_outcome schema extension
# ----------------------------------------------------------------------


def _minimal_fm(**overrides: object) -> dict[str, object]:
    """Return a minimal valid frontmatter dict; overrides add/replace keys."""
    fm: dict[str, object] = {
        "id": "UC-S01",
        "category": "spatial",
        "title": "test",
        "status": "draft",
        "setup": {"graph_builder": ""},
        "actions": [],
        "expected_observations": [],
        "gaps": [],
    }
    fm.update(overrides)
    return fm


def test_expected_outcome_is_optional() -> None:
    """Manifests without ``expected_outcome`` must still validate (backward compat)."""
    fm = _minimal_fm()  # no expected_outcome key
    errors = validate_frontmatter(fm, source="<optional>")
    assert errors == [], errors


@pytest.mark.parametrize("value", sorted({"pass", "yield", "blocked"}))
def test_expected_outcome_valid_values_pass(value: str) -> None:
    """Every value in VALID_EXPECTED_OUTCOMES must validate cleanly."""
    fm = _minimal_fm(expected_outcome=value)
    errors = validate_frontmatter(fm, source="<valid>")
    assert errors == [], errors
    assert value in VALID_EXPECTED_OUTCOMES


def test_expected_outcome_invalid_value_errors() -> None:
    """Invalid outcome values must surface exactly one error mentioning the field."""
    fm = _minimal_fm(expected_outcome="fail")
    errors = validate_frontmatter(fm, source="<invalid>")
    assert len(errors) == 1, errors
    msg = errors[0]
    assert "expected_outcome" in msg
    assert "fail" in msg
