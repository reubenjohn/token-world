"""Tests for stats panel per-agent rollup (SC-3)."""

from __future__ import annotations

from token_world.dashboard.panels.stats import StatsReport, render_cells


def test_render_cells_no_per_agent_rollup_for_single_agent() -> None:
    report = StatsReport(slug="test", tick_count=5, yield_count=1)
    per_agent = {"alice": {"ticks": 5, "yields": 1}}
    cells = render_cells(report, per_agent_yield=per_agent)
    labels = [c["label"] for c in cells]
    # Single actor -> no per-agent breakdown rows
    assert not any(label.startswith("Yield (") for label in labels)


def test_render_cells_per_agent_rollup_shown_for_two_agents() -> None:
    report = StatsReport(slug="test", tick_count=10, yield_count=3)
    per_agent = {
        "alice": {"ticks": 6, "yields": 2},
        "bob": {"ticks": 4, "yields": 1},
    }
    cells = render_cells(report, per_agent_yield=per_agent)
    labels = [c["label"] for c in cells]
    assert "Yield (alice)" in labels
    assert "Yield (bob)" in labels
    alice_cell = next(c for c in cells if c["label"] == "Yield (alice)")
    assert alice_cell["value"] == "33.3%"


def test_render_cells_per_agent_rollup_hidden_when_none() -> None:
    report = StatsReport(slug="test")
    cells = render_cells(report, per_agent_yield=None)
    labels = [c["label"] for c in cells]
    assert not any(label.startswith("Yield (") for label in labels)


def test_render_cells_per_agent_zero_ticks_shows_dash() -> None:
    report = StatsReport(slug="test", tick_count=2)
    per_agent = {
        "alice": {"ticks": 0, "yields": 0},
        "bob": {"ticks": 2, "yields": 1},
    }
    cells = render_cells(report, per_agent_yield=per_agent)
    alice_cell = next(c for c in cells if c["label"] == "Yield (alice)")
    assert alice_cell["value"] == "—"


def test_render_cells_standard_cells_still_present_with_per_agent() -> None:
    """Core cells (Universe, Ticks, etc.) are always present even with per-agent data."""
    report = StatsReport(slug="myworld", tick_count=4)
    per_agent = {
        "alice": {"ticks": 2, "yields": 0},
        "bob": {"ticks": 2, "yields": 1},
    }
    cells = render_cells(report, per_agent_yield=per_agent)
    labels = [c["label"] for c in cells]
    for required in ("Universe", "Ticks", "Yield rate", "Mechanics used", "Cost"):
        assert required in labels, f"missing required cell: {required}"
