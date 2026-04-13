"""Invariant: every use-case manifest has a valid ``expected_outcome``.

This is the AUTHORITATIVE check for 04-04 Task 3 (W7 fix). Grep-based
acceptance criteria can miss trailing whitespace, case variations, or
Windows line endings; this pytest invariant cannot. Runs once per
manifest:

    1. ``load_use_case`` reloads the manifest without error.
    2. ``expected_outcome`` is present on every manifest (D-29b).
    3. The value is in ``VALID_EXPECTED_OUTCOMES``.
    4. ``validate_frontmatter`` returns zero errors (full schema still OK).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from token_world.use_cases.loader import (
    VALID_EXPECTED_OUTCOMES,
    load_use_case,
    validate_frontmatter,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
USE_CASES_DIR = REPO_ROOT / ".planning" / "use-cases"


def _all_manifests() -> list[Path]:
    return sorted(USE_CASES_DIR.rglob("UC-*.md"))


@pytest.mark.parametrize(
    "path",
    [pytest.param(p, id=p.stem) for p in _all_manifests()],
)
def test_every_manifest_has_valid_outcome(path: Path) -> None:
    fm, _body = load_use_case(path)
    assert "expected_outcome" in fm, f"{path}: missing expected_outcome field"
    assert fm["expected_outcome"] in VALID_EXPECTED_OUTCOMES, (
        f"{path}: expected_outcome={fm['expected_outcome']!r} "
        f"not in {sorted(VALID_EXPECTED_OUTCOMES)}"
    )
    errs = validate_frontmatter(fm, source=str(path))
    assert errs == [], f"{path}: schema errors: {errs}"
