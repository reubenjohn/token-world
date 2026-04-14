"""Tests for ``token_world.inspect.universe`` and ``token-world inspect``.

Coverage:

- Empty universe (no graph, no ticks, no mechanics) returns a valid
  zero-filled report and renders without crashing.
- Populated graph counts nodes by type and edges.
- Populated mechanics directory counts modules and applies the
  seed-vs-operator authorship heuristic (``__author__`` marker).
- Recent ticks: ``--last N`` controls the window; mutation count flows
  through; observation excerpts are truncated.
- Active LRAs: nodes with ``current_long_action`` show up.
- Recent yields: capped at 5, returned in chronological order.
- Operator log: gracefully absent vs. present + last entry surfaced.
- CLI: ``--format json`` is parseable JSON; table mode contains the
  section headers; nonexistent slug exits 1.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from token_world.cli import cli
from token_world.inspect.universe import (
    InspectReport,
    aggregate,
    render_json,
    render_table,
)
from token_world.universe.manager import UniverseManager

# ---------------------------------------------------------------------------
# aggregate() unit tests
# ---------------------------------------------------------------------------


def test_aggregate_empty_universe(fake_universe: Path) -> None:
    """A universe with empty mechanics/ + no ticks + no db yields an empty report."""
    report = aggregate(fake_universe, slug="empty")
    assert report.slug == "empty"
    assert report.node_count_total == 0
    assert report.edge_count == 0
    assert report.graph_loaded is False
    assert report.mechanic_count == 0
    assert report.tick_count_total == 0
    assert report.recent_ticks == []
    assert report.active_lras == []
    assert report.recent_yields == []
    assert report.operator_log_exists is False


def test_aggregate_graph_counts(fake_universe_with_graph: Path) -> None:
    """Graph node/edge counts are surfaced from the persisted graph."""
    report = aggregate(fake_universe_with_graph, slug="g")
    assert report.graph_loaded is True
    assert report.node_count_total == 4
    assert report.node_count_by_type == {"agent": 2, "entity": 2}
    assert report.edge_count == 3


def test_aggregate_active_lra_detected(fake_universe: Path) -> None:
    """Actor nodes with ``current_long_action`` show up under active_lras."""
    from token_world.graph import KnowledgeGraph

    kg = KnowledgeGraph(db_path=fake_universe / "universe.db")
    kg.add_node("alice", node_type="agent")
    kg.set(
        "alice",
        "current_long_action",
        {
            "action_text": "sleeping",
            "turns_total": 8,
            "turns_elapsed": 3,
            "thresholds": [],
            "payload": {},
        },
    )
    kg.save()

    report = aggregate(fake_universe, slug="g")
    assert len(report.active_lras) == 1
    lra = report.active_lras[0]
    assert lra.actor_id == "alice"
    assert lra.action_text == "sleeping"
    assert lra.turns_elapsed == 3
    assert lra.turns_total == 8


def test_aggregate_tick_recent_window(fake_universe: Path, write_tick) -> None:
    """``last_n`` keeps the last N ticks (numerically)."""
    ticks = fake_universe / "tick_summaries" / "ticks"
    for i in range(1, 6):
        write_tick(ticks, i, action_text=f"act {i}")
    report = aggregate(fake_universe, slug="t", last_n=2)
    assert report.tick_count_total == 5
    assert [t.tick_id for t in report.recent_ticks] == ["4", "5"]


def test_aggregate_tick_mutation_count_flows(fake_universe: Path, write_tick) -> None:
    """Mutation counts and matched mechanic ID make it into TickLine."""
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(
        ticks,
        "1",
        matched_mechanic_id="open_chest",
        mutations=[["chest", "is_open", False, True], ["chest", "loot", None, "gold"]],
    )
    report = aggregate(fake_universe, slug="t")
    assert len(report.recent_ticks) == 1
    tl = report.recent_ticks[0]
    assert tl.matched_mechanic_id == "open_chest"
    assert tl.mutation_count == 2


def test_aggregate_recent_yields_capped_at_5(fake_universe: Path, write_tick) -> None:
    """``recent_yields`` returns at most 5 entries, in chronological order."""
    ticks = fake_universe / "tick_summaries" / "ticks"
    for i in range(1, 11):
        write_tick(ticks, i, yielded=(i % 2 == 0), action_text=f"act {i}")
    # Yielded ticks: 2, 4, 6, 8, 10 -> exactly 5; chronological order kept.
    report = aggregate(fake_universe, slug="t")
    assert [y.tick_id for y in report.recent_yields] == ["2", "4", "6", "8", "10"]


def test_aggregate_observation_excerpt_truncated(fake_universe: Path, write_tick) -> None:
    """Long observations get truncated with an ellipsis."""
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(ticks, "1", observation_text="x" * 500)
    report = aggregate(fake_universe, slug="t")
    line = report.recent_ticks[0]
    assert line.observation_excerpt is not None
    assert line.observation_excerpt.endswith("...")
    assert len(line.observation_excerpt) <= 80


def test_aggregate_operator_log_absent(fake_universe: Path) -> None:
    """No ``operator-log.jsonl`` => operator_log_exists is False (no crash)."""
    report = aggregate(fake_universe, slug="t")
    assert report.operator_log_exists is False
    assert report.operator_log_entry_count == 0
    assert report.operator_log_last_entry is None


def test_aggregate_operator_log_present(fake_universe: Path) -> None:
    """``operator-log.jsonl`` is parsed and the LAST line is surfaced."""
    log = fake_universe / "operator-log.jsonl"
    log.write_text(
        '{"timestamp":"2026-04-14T01:00Z","kind":"propose","mechanic":"a"}\n'
        "\n"  # blank line is fine
        '{"timestamp":"2026-04-14T02:00Z","kind":"refuse","reason":"x"}\n',
        encoding="utf-8",
    )
    report = aggregate(fake_universe, slug="t")
    assert report.operator_log_exists is True
    assert report.operator_log_entry_count == 2
    assert report.operator_log_last_entry is not None
    assert report.operator_log_last_entry["kind"] == "refuse"


def test_aggregate_mechanic_author_classification_via_marker(
    fake_universe: Path,
) -> None:
    """``__author__ = "operator"`` marker classifies a module as operator."""
    mech_dir = fake_universe / "mechanics"
    (mech_dir / "seed_one.py").write_text('"""Seed mechanic."""\n', encoding="utf-8")
    (mech_dir / "operator_one.py").write_text(
        '"""Operator-authored mechanic."""\n__author__ = "operator"\n',
        encoding="utf-8",
    )
    report = aggregate(fake_universe, slug="t")
    assert report.mechanic_count == 2
    assert report.mechanic_authors.seed == 1
    assert report.mechanic_authors.operator == 1


# ---------------------------------------------------------------------------
# Renderer unit tests
# ---------------------------------------------------------------------------


def test_render_table_smoke(fake_universe_with_graph: Path) -> None:
    report = aggregate(fake_universe_with_graph, slug="rg")
    out = render_table(report)
    assert "=== Universe: rg ===" in out
    assert "Graph" in out
    assert "Mechanics" in out
    assert "Ticks" in out
    assert "Active Long-Running Actions" in out
    assert "Recent Yields" in out
    assert "Operator Log" in out


def test_render_json_is_valid_and_has_expected_shape() -> None:
    report = InspectReport(slug="x", universe_dir="/tmp/x")
    payload = json.loads(render_json(report))
    assert payload["slug"] == "x"
    assert "graph" in payload
    assert "mechanics" in payload
    assert "ticks" in payload
    assert "active_lras" in payload
    assert "recent_yields" in payload
    assert "operator_log" in payload


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


def _make_universe(tmp_data_dir: Path, name: str) -> tuple[str, Path]:
    """Create a real universe via UniverseManager so ``cli`` can resolve it."""
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create(name)
    return universe_dir.name, universe_dir


def test_cli_unknown_universe_exits_1(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    runner = CliRunner()
    result = runner.invoke(cli, ["inspect", "does-not-exist"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_cli_table_smoke(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, _udir = _make_universe(tmp_data_dir, "inspect smoke")
    runner = CliRunner()
    result = runner.invoke(cli, ["inspect", slug])
    assert result.exit_code == 0, result.output
    assert "Universe:" in result.output
    assert "Graph" in result.output
    assert "Mechanics" in result.output


def test_cli_json_returns_valid_json(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, _ = _make_universe(tmp_data_dir, "inspect json")
    runner = CliRunner()
    result = runner.invoke(cli, ["inspect", slug, "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["slug"] == slug
    assert "graph" in payload
    assert "ticks" in payload
