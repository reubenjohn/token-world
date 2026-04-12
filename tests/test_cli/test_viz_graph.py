"""CLI-level smoke tests for `token-world viz-graph`."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from token_world.cli import cli


@pytest.fixture
def populated_universe(tmp_path, monkeypatch):
    """Create a universe with a small graph on disk and return its slug."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    from token_world.graph import KnowledgeGraph
    from token_world.universe.manager import UniverseManager

    mgr = UniverseManager()
    path = mgr.create("viz-smoke")

    kg = KnowledgeGraph(db_path=path / "universe.db")
    kg.add_node("alice", node_type="agent")
    kg.add_node("room_a", node_type="entity", subtype="room")
    kg.add_node("sword", node_type="entity", subtype="weapon")
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("sword", "alice", relation="held_by")
    kg.save()
    return "viz-smoke"


def test_requires_anchor(populated_universe) -> None:
    result = CliRunner().invoke(cli, ["viz-graph", populated_universe])
    assert result.exit_code != 0
    assert "anchor" in result.output.lower() or "--node" in result.output


def test_help_lists_anchor_flags() -> None:
    result = CliRunner().invoke(cli, ["viz-graph", "--help"])
    assert result.exit_code == 0
    assert "--node" in result.output
    assert "--seed-query" in result.output
    assert "--all-agents" in result.output


def test_node_anchor_emits_flowchart(populated_universe) -> None:
    result = CliRunner().invoke(
        cli, ["viz-graph", populated_universe, "--node", "alice", "--depth", "1"]
    )
    assert result.exit_code == 0, result.output
    assert result.output.lstrip().startswith("flowchart"), result.output[:100]
    assert "alice" in result.output
    assert "room_a" in result.output


def test_max_nodes_cap(populated_universe) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "viz-graph",
            populated_universe,
            "--node",
            "alice",
            "--depth",
            "3",
            "--max-nodes",
            "1",
        ],
    )
    assert result.exit_code != 0
    # Error message should guide the user
    combined = (result.output + (result.stderr or "")).lower()
    assert "max" in combined or "tighten" in combined


def test_output_file(populated_universe, tmp_path) -> None:
    out = tmp_path / "out.mmd"
    result = CliRunner().invoke(
        cli,
        ["viz-graph", populated_universe, "--node", "alice", "--output", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert out.read_text().lstrip().startswith("flowchart")


def test_type_filter(populated_universe) -> None:
    result = CliRunner().invoke(
        cli,
        ["viz-graph", populated_universe, "--node", "alice", "--type", "entity"],
    )
    assert result.exit_code == 0, result.output
    # Entities are included; anchor alice always kept
    assert "room_a" in result.output


def test_seed_query(populated_universe) -> None:
    result = CliRunner().invoke(
        cli,
        ["viz-graph", populated_universe, "--seed-query", "subtype=room"],
    )
    assert result.exit_code == 0, result.output
    assert "room_a" in result.output


def test_all_agents(populated_universe) -> None:
    result = CliRunner().invoke(cli, ["viz-graph", populated_universe, "--all-agents"])
    assert result.exit_code == 0, result.output
    assert "alice" in result.output


def test_missing_universe_exits_non_zero() -> None:
    result = CliRunner().invoke(cli, ["viz-graph", "does-not-exist", "--node", "alice"])
    assert result.exit_code != 0


def test_no_style_flag(populated_universe) -> None:
    result = CliRunner().invoke(
        cli,
        ["viz-graph", populated_universe, "--node", "alice", "--no-style"],
    )
    assert result.exit_code == 0, result.output
    assert "classDef" not in result.output
