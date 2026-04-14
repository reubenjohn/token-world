"""Tests for ``token_world.inspect.diff`` and the ``token-world diff`` CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from token_world.cli import cli
from token_world.inspect.diff import diff, render_json, render_table
from token_world.universe.manager import UniverseManager


def _seed_history(universe_dir: Path) -> None:
    from token_world.graph import KnowledgeGraph

    kg = KnowledgeGraph(db_path=universe_dir / "universe.db")
    # Tick 1: alice + chest, alice located_in room
    kg.set_tick(1)
    kg.add_node("alice", node_type="agent", health=10)
    kg.add_node("room", node_type="entity")
    kg.add_node("chest", node_type="entity")
    kg.add_edge("alice", "room", relation="located_in")
    kg.save()

    # Tick 2: alice loses health, picks up sword
    kg.set_tick(2)
    kg.set("alice", "health", 7)
    kg.add_node("sword", node_type="entity", subtype="weapon")
    kg.save()

    # Tick 3: alice loses more health (multi update on health)
    kg.set_tick(3)
    kg.set("alice", "health", 5)
    kg.save()


# ---------------------------------------------------------------------------
# diff() unit tests
# ---------------------------------------------------------------------------


def test_diff_db_missing(fake_universe: Path) -> None:
    report = diff(fake_universe, slug="t", tick_a="0", tick_b="5")
    assert report.db_missing is True


def test_diff_node_added(fake_universe: Path) -> None:
    _seed_history(fake_universe)
    report = diff(fake_universe, slug="t", tick_a="1", tick_b="2")
    assert "sword" in report.nodes_added
    assert "alice" not in report.nodes_added  # added at tick 1, before window


def test_diff_property_change_old_new(fake_universe: Path) -> None:
    _seed_history(fake_universe)
    report = diff(fake_universe, slug="t", tick_a="1", tick_b="3")
    health_change = next(
        c for c in report.property_changes if c.target == "alice" and c.property == "health"
    )
    # The window starts AFTER tick 1 (alice was created with health=10 there);
    # tick 2 sets 10 -> 7, tick 3 sets 7 -> 5. The diff report keeps the
    # original "old" (10 from the first event in window) and the latest
    # "new" (5), marking the change as intermediate=True.
    assert health_change.old_value == 10
    assert health_change.new_value == 5
    assert health_change.intermediate is True


def test_diff_swap_ticks(fake_universe: Path) -> None:
    """tick_a > tick_b is silently swapped to a forward chronological diff."""
    _seed_history(fake_universe)
    forward = diff(fake_universe, slug="t", tick_a="1", tick_b="3")
    backward = diff(fake_universe, slug="t", tick_a="3", tick_b="1")
    assert forward.nodes_added == backward.nodes_added
    assert forward.tick_a == backward.tick_a == 1
    assert forward.tick_b == backward.tick_b == 3


def test_diff_empty_window(fake_universe: Path) -> None:
    _seed_history(fake_universe)
    report = diff(fake_universe, slug="t", tick_a="3", tick_b="3")
    assert report.nodes_added == []
    assert report.nodes_removed == []
    assert report.property_changes == []


# ---------------------------------------------------------------------------
# Renderer unit tests
# ---------------------------------------------------------------------------


def test_render_table_smoke(fake_universe: Path) -> None:
    _seed_history(fake_universe)
    report = diff(fake_universe, slug="t", tick_a="1", tick_b="3")
    out = render_table(report)
    assert "Diff: t ticks 1..3" in out
    assert "Nodes added" in out
    assert "Property changes" in out
    assert "alice.health" in out


def test_render_json_valid(fake_universe: Path) -> None:
    _seed_history(fake_universe)
    payload = json.loads(render_json(diff(fake_universe, slug="t", tick_a="1", tick_b="3")))
    assert payload["slug"] == "t"
    assert payload["tick_a"] == 1
    assert payload["tick_b"] == 3


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_unknown_universe_exits_1(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    runner = CliRunner()
    result = runner.invoke(cli, ["diff", "nope", "1", "2"])
    assert result.exit_code == 1


def test_cli_table_smoke(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("diff smoke")
    _seed_history(universe_dir)
    runner = CliRunner()
    result = runner.invoke(cli, ["diff", universe_dir.name, "1", "3"])
    assert result.exit_code == 0, result.output
    assert "Diff:" in result.output
    assert "alice.health" in result.output


def test_cli_json_is_valid(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("diff json")
    _seed_history(universe_dir)
    runner = CliRunner()
    result = runner.invoke(cli, ["diff", universe_dir.name, "1", "3", "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["tick_a"] == 1
    assert payload["tick_b"] == 3
