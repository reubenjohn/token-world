"""Tests for ``token_world.inspect.trace`` and the ``token-world trace`` CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from token_world.cli import cli
from token_world.inspect.trace import render_json, render_table, trace
from token_world.universe.manager import UniverseManager


def _seed_graph_with_history(universe_dir: Path) -> None:
    """Persist a tiny graph and apply property mutations across multiple ticks.

    Produces graph_events rows the trace walker can pick up.
    """
    from token_world.graph import KnowledgeGraph

    kg = KnowledgeGraph(db_path=universe_dir / "universe.db")
    kg.set_tick(1)
    kg.add_node("alice", node_type="agent", health=10)
    kg.save()

    kg.set_tick(2)
    kg.set("alice", "health", 8)
    kg.save()

    kg.set_tick(3)
    kg.set("alice", "health", 5)
    kg.save()


# ---------------------------------------------------------------------------
# trace() unit tests
# ---------------------------------------------------------------------------


def test_trace_db_missing(fake_universe: Path) -> None:
    report = trace(fake_universe, slug="t", node_id="alice", property="health")
    assert report.db_missing is True
    assert report.hops == []


def test_trace_property_not_found(fake_universe_with_graph: Path) -> None:
    """A graph with no events for the requested property returns not_found=True."""
    report = trace(
        fake_universe_with_graph,
        slug="t",
        node_id="alice",
        property="health",
    )
    # graph_events for fake_universe_with_graph contain add_node / add_edge
    # rows but no set_property('health'); the walker also surfaces the
    # add_node row (NULL property_name), so we explicitly target a property
    # that was never touched and never appeared in any add_node either.
    nonexistent = trace(
        fake_universe_with_graph,
        slug="t",
        node_id="ghost",
        property="health",
    )
    assert nonexistent.not_found is True
    # The 'alice' add_node row has property_name=NULL so it WILL match
    # via the OR clause; assert we got at least one hop.
    assert len(report.hops) >= 1


def test_trace_walks_property_history(fake_universe: Path) -> None:
    _seed_graph_with_history(fake_universe)
    report = trace(fake_universe, slug="t", node_id="alice", property="health")
    # alice was created at tick 1 with health=10, then mutated at ticks 2, 3.
    # Hops are emitted oldest-first.
    tick_ids = [h.tick_id for h in report.hops]
    assert tick_ids == sorted(tick_ids, key=int)
    # We should have at least the two set_property hops.
    set_hops = [h for h in report.hops if h.event_type == "set_property"]
    assert len(set_hops) >= 2
    last = set_hops[-1]
    assert last.new_value == 5


def test_trace_hop_limit_truncates(fake_universe: Path) -> None:
    """Walking with ``hop_limit < total events`` flips the truncated flag."""
    from token_world.graph import KnowledgeGraph

    kg = KnowledgeGraph(db_path=fake_universe / "universe.db")
    kg.set_tick(1)
    kg.add_node("alice", node_type="agent", hp=100)
    kg.save()
    for t in range(2, 8):
        kg.set_tick(t)
        kg.set("alice", "hp", 100 - t)
        kg.save()

    report = trace(fake_universe, slug="t", node_id="alice", property="hp", hop_limit=2)
    assert report.truncated is True
    assert len(report.hops) == 2


def test_trace_enriches_with_tick_context(fake_universe: Path, write_tick) -> None:
    """When a tick file exists for an event, action/observation are surfaced."""
    _seed_graph_with_history(fake_universe)
    ticks_dir = fake_universe / "tick_summaries" / "ticks"
    write_tick(
        ticks_dir,
        "3",
        action_text="alice takes a hit",
        matched_mechanic_id="combat",
        observation_text="alice winces in pain",
        classified_action={"verb": "attack", "object": "alice", "confidence": 0.9},
    )
    report = trace(fake_universe, slug="t", node_id="alice", property="health")
    last = next(h for h in report.hops if h.tick_id == "3")
    assert last.action_text == "alice takes a hit"
    assert last.matched_mechanic_id == "combat"
    assert last.observation_text == "alice winces in pain"
    assert last.classified_action == {
        "verb": "attack",
        "object": "alice",
        "confidence": 0.9,
    }


def test_trace_marks_missing_tick_file(fake_universe: Path) -> None:
    """Events whose tick file is absent still appear with tick_missing=True."""
    _seed_graph_with_history(fake_universe)
    report = trace(fake_universe, slug="t", node_id="alice", property="health")
    assert all(h.tick_missing for h in report.hops)


# ---------------------------------------------------------------------------
# Renderer unit tests
# ---------------------------------------------------------------------------


def test_render_table_db_missing(fake_universe: Path) -> None:
    report = trace(fake_universe, slug="t", node_id="alice", property="health")
    out = render_table(report)
    assert "no universe.db" in out


def test_render_table_not_found(fake_universe_with_graph: Path) -> None:
    report = trace(fake_universe_with_graph, slug="t", node_id="ghost", property="x")
    out = render_table(report)
    assert "No graph events" in out


def test_render_table_smoke(fake_universe: Path, write_tick) -> None:
    _seed_graph_with_history(fake_universe)
    write_tick(
        fake_universe / "tick_summaries" / "ticks",
        "3",
        action_text="hit alice",
        matched_mechanic_id="combat",
    )
    report = trace(fake_universe, slug="t", node_id="alice", property="health")
    out = render_table(report)
    assert "Trace:" in out
    assert "alice.health" in out
    assert "tick 3" in out
    assert "combat" in out


def test_render_json_valid(fake_universe: Path) -> None:
    _seed_graph_with_history(fake_universe)
    report = trace(fake_universe, slug="t", node_id="alice", property="health")
    payload = json.loads(render_json(report))
    assert payload["node_id"] == "alice"
    assert payload["property"] == "health"
    assert isinstance(payload["hops"], list)


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_unknown_universe_exits_1(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    runner = CliRunner()
    result = runner.invoke(cli, ["trace", "nope", "alice", "health"])
    assert result.exit_code == 1


def test_cli_table_smoke(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("trace smoke")
    _seed_graph_with_history(universe_dir)
    runner = CliRunner()
    result = runner.invoke(cli, ["trace", universe_dir.name, "alice", "health"])
    assert result.exit_code == 0, result.output
    assert "Trace:" in result.output
    assert "alice.health" in result.output


def test_cli_json_is_valid(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("trace json")
    _seed_graph_with_history(universe_dir)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["trace", universe_dir.name, "alice", "health", "--format", "json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["node_id"] == "alice"
