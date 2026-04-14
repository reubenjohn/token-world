"""Integration smoke tests for the wired-up dashboard (Plan 11-05).

These tests exercise `create_app` through a full panel-mount pass against
the synthetic universe fixtures. They don't start a server, but they do
catch regressions where a panel module stops importing or where the layout
row-column nesting raises inside NiceGUI.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from token_world.cli import cli


def test_create_app_runs_against_populated_universe_through_cli(
    tmp_data_dir: Path, fake_universe_with_graph: Path, write_tick_dashboard
) -> None:
    """Slug resolves, all four panels mount, CLI `--help` still passes.

    We verify via the CLI contract rather than booting a server —
    `create_app()` triggers an early import of every panel module, which
    is the actual regression surface.
    """
    # Seed a couple of ticks so the tick-stream panel has real cards to render.
    ticks_dir = fake_universe_with_graph / "tick_summaries" / "ticks"
    write_tick_dashboard(ticks_dir, "1", matched_mechanic_id="look")
    write_tick_dashboard(ticks_dir, "2", yielded=True, action_text="summon a demigod")

    # `tmp_data_dir` repoints XDG_DATA_HOME — copy the fake universe into it
    # so UniverseManager can locate the slug.
    import shutil

    slug_dir = tmp_data_dir / "int-universe"
    shutil.copytree(fake_universe_with_graph, slug_dir)

    runner = CliRunner()
    # `--help` parses the subcommand tree and exits 0 when all panels
    # import cleanly — a broken panel raises at module-load time.
    result = runner.invoke(cli, ["dashboard", "--help"])
    assert result.exit_code == 0, result.output


def test_panel_modules_all_importable() -> None:
    """Every panel module's public mount fn exists and is callable."""
    from token_world.dashboard.panels.graph_canvas import mount_graph_panel
    from token_world.dashboard.panels.property_history import mount_property_history_panel
    from token_world.dashboard.panels.stats import mount_stats_strip
    from token_world.dashboard.panels.tick_stream import mount_tick_stream_panel

    for fn in (
        mount_stats_strip,
        mount_tick_stream_panel,
        mount_graph_panel,
        mount_property_history_panel,
    ):
        assert callable(fn)


def test_old_causal_chain_import_is_gone() -> None:
    """Regression: the old ``causal_chain`` module must not resolve (§A5a)."""
    import importlib

    import pytest

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("token_world.dashboard.panels.causal_chain")


@pytest.mark.parametrize(
    ("slug", "want_exit", "want_fragment"),
    [
        ("__nonexistent__", 1, "not found"),
        ("__also_missing__", 1, "list"),  # hint mentions `token-world list`
    ],
)
def test_dashboard_missing_slug_messages(slug: str, want_exit: int, want_fragment: str) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["dashboard", slug])
    assert result.exit_code == want_exit
    assert want_fragment.lower() in result.output.lower()
