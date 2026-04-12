"""GAP-ANALYSIS.md must have layer sections and a disposition summary."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


def test_gap_analysis_exists_and_has_required_sections(gap_analysis_path: Path) -> None:
    if not gap_analysis_path.exists():
        pytest.skip("GAP-ANALYSIS.md not written yet (Wave 4 pending)")
    text = gap_analysis_path.read_text(encoding="utf-8")
    for heading in (
        "# Phase 3: Gap Analysis",
        "## Gaps by Architecture Layer",
        "### Graph Layer",
        "### Mechanic Framework Layer",
        "### Engine Pipeline Layer",
        "## Dispositions",
        "### Address Now",
        "### Defer",
        "### Out of Scope",
    ):
        assert heading in text, f"GAP-ANALYSIS.md missing heading: {heading!r}"


def test_gap_ids_follow_scheme(gap_analysis_path: Path) -> None:
    if not gap_analysis_path.exists():
        pytest.skip("GAP-ANALYSIS.md not written yet (Wave 4 pending)")
    text = gap_analysis_path.read_text(encoding="utf-8")
    ids = re.findall(r"GAP-[GMEX]\d{2}", text)
    assert ids, "No GAP-<layer><NN> IDs found"
    assert all(re.match(r"^GAP-[GMEX]\d{2}$", i) for i in ids)
