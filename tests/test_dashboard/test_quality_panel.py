"""Unit tests for the Quality dashboard panel.

Tests exercise render_cells and load_quality without a live NiceGUI server.
"""

from __future__ import annotations

from pathlib import Path

from token_world.dashboard.panels.quality import load_quality, render_cells
from token_world.quality.report import DimensionResult, QualityReport


def test_render_cells_all_ok() -> None:
    report = QualityReport(
        slug="test",
        tick_count=10,
        verdict="HEALTHY",
        dimensions=[
            DimensionResult(name="Groundedness", status="OK", score=0.96, detail="48/50 grounded")
        ],
    )
    cells = render_cells(report)
    assert cells[0]["label"] == "Groundedness"
    assert cells[0]["status"] == "OK"
    # Verdict cell appended
    assert cells[-1]["label"] == "Verdict"
    assert cells[-1]["value"] == "HEALTHY"
    assert cells[-1]["status"] == "OK"


def test_render_cells_failed_verdict() -> None:
    report = QualityReport(
        slug="test",
        tick_count=10,
        verdict="FAILED",
        dimensions=[
            DimensionResult(name="Groundedness", status="FAIL", score=0.6, detail="30/50 grounded")
        ],
    )
    cells = render_cells(report)
    assert cells[-1]["status"] == "FAIL"


def test_render_cells_degraded_verdict() -> None:
    report = QualityReport(
        slug="test",
        tick_count=10,
        verdict="DEGRADED",
        dimensions=[
            DimensionResult(name="Action coherence", status="WARN", score=3.0, detail="streak=3")
        ],
    )
    cells = render_cells(report)
    assert cells[-1]["label"] == "Verdict"
    assert cells[-1]["status"] == "WARN"


def test_render_cells_insufficient_data_verdict() -> None:
    report = QualityReport(slug="test", tick_count=0, verdict="INSUFFICIENT_DATA")
    cells = render_cells(report)
    # No dimension cells, only verdict
    assert len(cells) == 1
    assert cells[0]["label"] == "Verdict"
    assert cells[0]["status"] == "UNKNOWN"


def test_render_cells_includes_all_dimensions() -> None:
    dims = [DimensionResult(name=f"Dim{i}", status="OK", score=1.0, detail="ok") for i in range(8)]
    report = QualityReport(slug="test", tick_count=50, verdict="HEALTHY", dimensions=dims)
    cells = render_cells(report)
    # 8 dimensions + 1 verdict
    assert len(cells) == 9
    assert cells[-1]["label"] == "Verdict"


def test_load_quality_degrades_on_missing_universe(tmp_path: Path) -> None:
    report = load_quality(tmp_path / "nonexistent", "ghost")
    assert report.verdict == "INSUFFICIENT_DATA"
    assert report.tick_count == 0


def test_load_quality_degrades_on_empty_universe(tmp_path: Path) -> None:
    """Universe dir exists but has no tick files."""
    universe_dir = tmp_path / "empty_universe"
    universe_dir.mkdir()
    report = load_quality(universe_dir, "empty_universe")
    assert report.verdict == "INSUFFICIENT_DATA"
    assert report.tick_count == 0
