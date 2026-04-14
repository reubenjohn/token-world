"""Smoke tests for :mod:`token_world.dashboard.app` (Plan 11-01).

Bare-minimum bar: the module imports, the CLI subcommand is registered,
and :func:`create_app` runs without raising on a valid universe dir.

A full end-to-end page render (via Playwright) would start a server and
is deliberately out of scope here — it belongs in Plan 11-05.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from token_world.cli import cli


def test_dashboard_command_registered() -> None:
    """``token-world dashboard`` is a real Click subcommand."""
    runner = CliRunner()
    result = runner.invoke(cli, ["dashboard", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output
    assert "--no-show" in result.output
    assert "dashboard" in result.output.lower()


def test_dashboard_missing_universe_exits_1() -> None:
    """Non-existent slug fails cleanly without booting NiceGUI."""
    runner = CliRunner()
    result = runner.invoke(cli, ["dashboard", "__does_not_exist__"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_dashboard_module_imports() -> None:
    """The app module (including NiceGUI) imports cleanly."""
    from token_world.dashboard import app as dashboard_app  # noqa: F401

    assert hasattr(dashboard_app, "create_app")
    assert hasattr(dashboard_app, "run_app")


def test_stats_panel_render_cells_empty(fake_universe: Path) -> None:
    """Empty universe yields a full cell set without raising."""
    from token_world.dashboard.panels.stats import load_stats, render_cells

    report = load_stats(fake_universe, slug="empty")
    cells = render_cells(report)
    labels = {c["label"] for c in cells}
    assert "Universe" in labels
    assert "Ticks" in labels
    assert "Cost" in labels
    # Empty-universe throughput is zero → placeholder dash.
    throughput = next(c for c in cells if c["label"] == "Throughput")
    assert "—" in throughput["value"]


def test_stats_panel_render_cells_populated(fake_universe: Path, write_tick_dashboard) -> None:
    """Populated universe surfaces tick count + latest tick id."""
    from token_world.dashboard.panels.stats import load_stats, render_cells

    ticks_dir = fake_universe / "tick_summaries" / "ticks"
    write_tick_dashboard(ticks_dir, "1", timestamp_iso="2026-04-14T00:00:00Z")
    write_tick_dashboard(ticks_dir, "2", timestamp_iso="2026-04-14T00:00:30Z")

    report = load_stats(fake_universe, slug="populated")
    cells = render_cells(report)
    by_label = {c["label"]: c["value"] for c in cells}
    assert by_label["Ticks"] == "2"
    assert by_label["Latest tick"] == "2"
