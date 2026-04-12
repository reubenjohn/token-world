"""Tests for CLI commands: list-mechanics, run-mechanic, query-graph."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from token_world.cli import cli
from token_world.graph import KnowledgeGraph
from token_world.universe.manager import UniverseManager


@pytest.fixture
def cli_universe(tmp_path: Path) -> tuple[CliRunner, str, Path]:
    """Create a universe with seed mechanics and a populated graph.

    Returns a tuple of (CliRunner, universe_slug, universe_dir).
    """
    manager = UniverseManager(data_dir=tmp_path)
    universe_dir = manager.create("Test World")

    # Populate graph with nodes and edges for testing
    kg = KnowledgeGraph(db_path=universe_dir / "universe.db")
    kg.add_node("room_a", node_type="entity", subtype="room", name="Room A")
    kg.add_node("room_b", node_type="entity", subtype="room", name="Room B")
    kg.add_node("alice", node_type="agent", location="room_a", name="Alice")
    kg.add_edge("room_a", "room_b", relation="path")
    kg.add_edge("room_b", "room_a", relation="path")
    kg.save()

    runner = CliRunner()
    return runner, "test-world", universe_dir


@pytest.fixture
def runner_and_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    """CliRunner with UniverseManager pointing to tmp_path."""
    monkeypatch.setattr(
        "token_world.universe.manager.get_universes_dir",
        lambda: tmp_path,
    )
    return CliRunner()


# ---------------------------------------------------------------------------
# list-mechanics
# ---------------------------------------------------------------------------


class TestListMechanics:
    def test_list_mechanics_shows_seeds(
        self, cli_universe: tuple[CliRunner, str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runner, slug, universe_dir = cli_universe
        monkeypatch.setattr(
            "token_world.universe.manager.get_universes_dir",
            lambda: universe_dir.parent,
        )
        result = runner.invoke(cli, ["list-mechanics", slug])
        assert result.exit_code == 0
        assert "movement" in result.output
        assert "observation" in result.output
        assert "environmental_reaction" in result.output

    def test_list_mechanics_invalid_universe(
        self, runner_and_manager: CliRunner
    ) -> None:
        result = runner_and_manager.invoke(cli, ["list-mechanics", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "not found" in (result.output + (result.output or "")).lower()


# ---------------------------------------------------------------------------
# run-mechanic
# ---------------------------------------------------------------------------


class TestRunMechanic:
    def test_run_mechanic_movement(
        self, cli_universe: tuple[CliRunner, str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runner, slug, universe_dir = cli_universe
        monkeypatch.setattr(
            "token_world.universe.manager.get_universes_dir",
            lambda: universe_dir.parent,
        )
        result = runner.invoke(
            cli, ["run-mechanic", slug, "movement", "--actor", "alice", "--target", "room_b"]
        )
        assert result.exit_code == 0
        assert "Check PASSED" in result.output
        assert "Mutations:" in result.output
        assert "Graph saved" in result.output

    def test_run_mechanic_failing_check(
        self, cli_universe: tuple[CliRunner, str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runner, slug, universe_dir = cli_universe
        monkeypatch.setattr(
            "token_world.universe.manager.get_universes_dir",
            lambda: universe_dir.parent,
        )
        result = runner.invoke(
            cli,
            ["run-mechanic", slug, "movement", "--actor", "alice", "--target", "nonexistent"],
        )
        assert result.exit_code == 1
        assert "Check FAILED" in result.output


# ---------------------------------------------------------------------------
# query-graph
# ---------------------------------------------------------------------------


class TestQueryGraph:
    def test_query_graph_all_nodes(
        self, cli_universe: tuple[CliRunner, str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runner, slug, universe_dir = cli_universe
        monkeypatch.setattr(
            "token_world.universe.manager.get_universes_dir",
            lambda: universe_dir.parent,
        )
        result = runner.invoke(cli, ["query-graph", slug])
        assert result.exit_code == 0
        assert "alice" in result.output
        assert "room_a" in result.output

    def test_query_graph_type_agent(
        self, cli_universe: tuple[CliRunner, str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runner, slug, universe_dir = cli_universe
        monkeypatch.setattr(
            "token_world.universe.manager.get_universes_dir",
            lambda: universe_dir.parent,
        )
        result = runner.invoke(cli, ["query-graph", slug, "--type", "agent"])
        assert result.exit_code == 0
        assert "alice" in result.output
        # room_a appears as alice's location value, but not as a node entry
        assert "room_a:" not in result.output

    def test_query_graph_stats(
        self, cli_universe: tuple[CliRunner, str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runner, slug, universe_dir = cli_universe
        monkeypatch.setattr(
            "token_world.universe.manager.get_universes_dir",
            lambda: universe_dir.parent,
        )
        result = runner.invoke(cli, ["query-graph", slug, "--stats"])
        assert result.exit_code == 0
        assert "Total nodes:" in result.output
        assert "Agents:" in result.output

    def test_query_graph_json(
        self, cli_universe: tuple[CliRunner, str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runner, slug, universe_dir = cli_universe
        monkeypatch.setattr(
            "token_world.universe.manager.get_universes_dir",
            lambda: universe_dir.parent,
        )
        result = runner.invoke(cli, ["query-graph", slug, "--json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert isinstance(parsed, list)

    def test_query_graph_has_property(
        self, cli_universe: tuple[CliRunner, str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runner, slug, universe_dir = cli_universe
        monkeypatch.setattr(
            "token_world.universe.manager.get_universes_dir",
            lambda: universe_dir.parent,
        )
        result = runner.invoke(cli, ["query-graph", slug, "--has-property", "location"])
        assert result.exit_code == 0
        assert "alice" in result.output
