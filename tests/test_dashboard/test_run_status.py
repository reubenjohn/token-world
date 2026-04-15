"""Tests for load_run_status() and render_cells() run-status cell (SC-3/DASHBOARD-07)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from token_world.dashboard.panels.stats import load_run_status, render_cells
from token_world.inspect.stats import StatsReport


def _minimal_report(slug: str = "t") -> StatsReport:
    return StatsReport(slug=slug)


# ---------------------------------------------------------------------------
# test_load_run_status_running
# ---------------------------------------------------------------------------


def test_load_run_status_running(tmp_path: Path) -> None:
    """State is 'running' when .run-pid has the current PID."""
    pid_path = tmp_path / ".run-pid"
    pid_path.write_text(
        json.dumps({"pid": os.getpid(), "started_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    result = load_run_status(tmp_path)
    assert result["state"] == "running"
    assert result["pid"] == os.getpid()
    assert result["started_at"] == "2026-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# test_load_run_status_stale
# ---------------------------------------------------------------------------


def test_load_run_status_stale(tmp_path: Path) -> None:
    """State is 'stale' when .run-pid has a nonexistent PID."""
    pid_path = tmp_path / ".run-pid"
    # PID 999999999 is extremely unlikely to exist
    pid_path.write_text(
        json.dumps({"pid": 999999999, "started_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    result = load_run_status(tmp_path)
    assert result["state"] == "stale"
    assert result["pid"] == 999999999


# ---------------------------------------------------------------------------
# test_load_run_status_idle
# ---------------------------------------------------------------------------


def test_load_run_status_idle(tmp_path: Path) -> None:
    """State is 'idle' when .run-pid does not exist."""
    result = load_run_status(tmp_path)
    assert result["state"] == "idle"
    assert result["pid"] is None
    assert result["started_at"] is None


# ---------------------------------------------------------------------------
# test_render_cells_includes_run_cell
# ---------------------------------------------------------------------------


def test_render_cells_includes_run_cell(tmp_path: Path) -> None:
    """render_cells includes a Run cell as first element when run_status is given."""
    run_status = {"state": "running", "pid": os.getpid(), "started_at": "2026-01-01T00:00:00Z"}
    report = _minimal_report()
    cells = render_cells(report, run_status=run_status)
    assert cells[0]["label"] == "Run"
    assert cells[0]["value"] == "running"


# ---------------------------------------------------------------------------
# test_load_run_status_corrupted_json
# ---------------------------------------------------------------------------


def test_load_run_status_corrupted_json(tmp_path: Path) -> None:
    """Corrupted .run-pid degrades to idle gracefully."""
    pid_path = tmp_path / ".run-pid"
    pid_path.write_text("not valid json {{{", encoding="utf-8")
    result = load_run_status(tmp_path)
    assert result["state"] == "idle"
    assert result["pid"] is None
