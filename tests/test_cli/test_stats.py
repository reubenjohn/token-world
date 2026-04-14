"""Tests for ``token_world.inspect.stats`` and the ``token-world stats`` CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from token_world.cli import cli
from token_world.inspect.stats import aggregate, render_json, render_table
from token_world.universe.manager import UniverseManager

# ---------------------------------------------------------------------------
# aggregate() unit tests
# ---------------------------------------------------------------------------


def test_aggregate_empty_universe(fake_universe: Path) -> None:
    report = aggregate(fake_universe, slug="t")
    assert report.tick_count == 0
    assert report.cost_total_usd == 0.0
    assert report.cost_backend == "no-data"


def test_aggregate_executed_yielded_refused_counts(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(ticks, "1", matched_mechanic_id="walk")  # executed
    write_tick(ticks, "2", matched_mechanic_id="walk")  # executed (no novel)
    write_tick(ticks, "3", yielded=True)  # yielded
    write_tick(ticks, "4", refused=True, refusal_reason="no_viable_action")  # refused
    write_tick(ticks, "5", matched_mechanic_id="look")  # executed (novel)
    report = aggregate(fake_universe, slug="t")
    assert report.tick_count == 5
    assert report.executed_count == 3
    assert report.yield_count == 1
    assert report.refuse_count == 1
    assert abs(report.yield_rate - 0.2) < 1e-9
    assert report.distinct_mechanics_used == 2
    assert report.novel_mechanic_introductions == 2
    assert abs(report.novel_mechanics_per_10_ticks - 4.0) < 1e-9


def test_aggregate_throughput_from_timestamps(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(ticks, "1", timestamp_iso="2026-04-14T00:00:00Z")
    write_tick(ticks, "2", timestamp_iso="2026-04-14T00:01:00Z")
    write_tick(ticks, "3", timestamp_iso="2026-04-14T00:02:00Z")
    report = aggregate(fake_universe, slug="t")
    assert abs(report.duration_seconds - 120.0) < 1e-6
    # (3 - 1) / (120 / 60) = 1.0 ticks per minute
    assert abs(report.ticks_per_minute - 1.0) < 1e-6


def test_aggregate_subtype_proxy(fake_universe: Path, write_tick) -> None:
    """Distinct ``subtype`` values introduced by mutations are tracked."""
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(
        ticks,
        "1",
        mutations=[["chest", "subtype", None, "container"]],
    )
    write_tick(
        ticks,
        "2",
        mutations=[
            ["chest", "subtype", "container", "container"],  # repeat
            ["sword", "subtype", None, "weapon"],
        ],
    )
    report = aggregate(fake_universe, slug="t")
    assert report.distinct_subtypes_seen == 2
    assert sorted(report.distinct_subtype_history) == ["container", "weapon"]


def test_aggregate_conservation_violation_detected(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(
        ticks,
        "1",
        refused=True,
        refusal_reason="conservation_violation: mass not balanced",
    )
    write_tick(ticks, "2", refused=True, refusal_reason="no_viable_action")
    report = aggregate(fake_universe, slug="t")
    assert report.conservation_violation_count == 1


def test_aggregate_since_window(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    for i in range(1, 6):
        write_tick(ticks, i, matched_mechanic_id=f"mech_{i}")
    report = aggregate(fake_universe, slug="t", since=2)
    assert report.tick_count == 2
    assert report.tick_id_min == "4"
    assert report.tick_id_max == "5"


def test_aggregate_composes_with_cost(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(
        ticks,
        "1",
        classifier_in=10,
        classifier_out=5,
        classifier_cost=0.001,
        observer_in=20,
        observer_out=10,
        observer_cost=0.002,
    )
    report = aggregate(fake_universe, slug="t")
    assert abs(report.cost_total_usd - 0.003) < 1e-9
    assert report.cost_total_input_tokens == 30
    assert report.cost_total_output_tokens == 15
    assert report.cost_backend == "anthropic-sdk"


# ---------------------------------------------------------------------------
# Renderer unit tests
# ---------------------------------------------------------------------------


def test_render_table_empty(fake_universe: Path) -> None:
    out = render_table(aggregate(fake_universe, slug="t"))
    assert "No ticks" in out


def test_render_table_smoke(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(ticks, "1", matched_mechanic_id="walk")
    out = render_table(aggregate(fake_universe, slug="t"))
    assert "Stats: t" in out
    assert "Tick stream" in out
    assert "Mechanics" in out
    assert "Cost" in out


def test_render_json_valid(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(ticks, "1", matched_mechanic_id="walk")
    payload = json.loads(render_json(aggregate(fake_universe, slug="t")))
    assert payload["slug"] == "t"
    assert payload["tick_count"] == 1


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_unknown_universe_exits_1(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    runner = CliRunner()
    result = runner.invoke(cli, ["stats", "nope"])
    assert result.exit_code == 1


def test_cli_table_smoke(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch, write_tick) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("stats smoke")
    write_tick(universe_dir / "tick_summaries" / "ticks", "1", matched_mechanic_id="walk")
    runner = CliRunner()
    result = runner.invoke(cli, ["stats", universe_dir.name])
    assert result.exit_code == 0, result.output
    assert "Stats:" in result.output
    assert "Tick stream" in result.output


def test_cli_json_is_valid(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch, write_tick) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("stats json")
    write_tick(universe_dir / "tick_summaries" / "ticks", "1")
    runner = CliRunner()
    result = runner.invoke(cli, ["stats", universe_dir.name, "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["slug"] == universe_dir.name


def test_cli_help_lists_stream_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["stats", "--help"])
    assert result.exit_code == 0
    assert "--stream" in result.output
    assert "--since" in result.output
