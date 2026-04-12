"""Fixtures for design validation tests (use-case loading, gap-analysis parsing)."""

from __future__ import annotations

from pathlib import Path

import pytest

USE_CASES_ROOT = Path(__file__).resolve().parents[2] / ".planning" / "use-cases"
GAP_ANALYSIS_PATH = (
    Path(__file__).resolve().parents[2]
    / ".planning"
    / "phases"
    / "03-design-validation"
    / "GAP-ANALYSIS.md"
)


@pytest.fixture(scope="session")
def use_case_files() -> list[Path]:
    if not USE_CASES_ROOT.exists():
        return []
    return sorted(p for p in USE_CASES_ROOT.rglob("UC-*.md") if p.is_file())


@pytest.fixture(scope="session")
def gap_analysis_path() -> Path:
    return GAP_ANALYSIS_PATH
