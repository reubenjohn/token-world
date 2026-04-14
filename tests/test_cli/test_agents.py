"""Tests for ``token_world.inspect.agents`` and the ``token-world agents`` CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from token_world.cli import cli
from token_world.inspect.agents import aggregate, render_json, render_table
from token_world.universe.manager import UniverseManager


def _seed_two_agents(universe_dir: Path) -> None:
    from token_world.graph import KnowledgeGraph

    kg = KnowledgeGraph(db_path=universe_dir / "universe.db")
    kg.add_node(
        "alice",
        node_type="agent",
        personality={"trait": "curious", "loyalty": 0.8},
        persona_text="Alice is a curious child.",
        memory=["entered the room", "saw a chest"],
    )
    kg.add_node(
        "bob",
        node_type="agent",
        persona_text="Bob is a cautious elder.",
    )
    kg.set(
        "bob",
        "current_long_action",
        {
            "action_text": "sleeping",
            "turns_total": 8,
            "turns_elapsed": 2,
            "thresholds": [],
            "payload": {"attention_state": {"focus": "dreams"}},
        },
    )
    kg.add_node("chest", node_type="entity")  # non-agent — must be filtered out
    kg.save()


# ---------------------------------------------------------------------------
# aggregate() unit tests
# ---------------------------------------------------------------------------


def test_aggregate_no_db(fake_universe: Path) -> None:
    report = aggregate(fake_universe, slug="t")
    assert report.agents == []


def test_aggregate_lists_only_agents(fake_universe: Path) -> None:
    _seed_two_agents(fake_universe)
    report = aggregate(fake_universe, slug="t")
    ids = sorted(a.id for a in report.agents)
    assert ids == ["alice", "bob"]


def test_aggregate_buckets_personality_persona_memory(fake_universe: Path) -> None:
    _seed_two_agents(fake_universe)
    report = aggregate(fake_universe, slug="t")
    alice = next(a for a in report.agents if a.id == "alice")
    assert alice.personality == {"trait": "curious", "loyalty": 0.8}
    assert alice.persona_text == "Alice is a curious child."
    assert alice.memory_entries == ["entered the room", "saw a chest"]


def test_aggregate_surfaces_lra_and_attention(fake_universe: Path) -> None:
    _seed_two_agents(fake_universe)
    report = aggregate(fake_universe, slug="t")
    bob = next(a for a in report.agents if a.id == "bob")
    assert bob.active_lra is not None
    assert bob.active_lra["action_text"] == "sleeping"
    assert bob.attention_state == {"focus": "dreams"}


def test_aggregate_filters_by_id_not_found(fake_universe: Path) -> None:
    _seed_two_agents(fake_universe)
    report = aggregate(fake_universe, slug="t", agent_id="ghost")
    assert report.not_found_id == "ghost"
    assert report.agents == []


def test_aggregate_filters_by_id_hit(fake_universe: Path) -> None:
    _seed_two_agents(fake_universe)
    report = aggregate(fake_universe, slug="t", agent_id="alice")
    assert [a.id for a in report.agents] == ["alice"]
    assert report.not_found_id is None


# ---------------------------------------------------------------------------
# Renderer unit tests
# ---------------------------------------------------------------------------


def test_render_table_smoke(fake_universe: Path) -> None:
    _seed_two_agents(fake_universe)
    out = render_table(aggregate(fake_universe, slug="t"))
    assert "Agents: t" in out
    assert "alice" in out
    assert "bob" in out
    assert "LRA:" in out
    assert "sleeping" in out


def test_render_table_not_found(fake_universe: Path) -> None:
    _seed_two_agents(fake_universe)
    out = render_table(aggregate(fake_universe, slug="t", agent_id="ghost"))
    assert "no agent with id" in out


def test_render_json_valid(fake_universe: Path) -> None:
    _seed_two_agents(fake_universe)
    payload = json.loads(render_json(aggregate(fake_universe, slug="t")))
    assert payload["slug"] == "t"
    assert isinstance(payload["agents"], list)


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_unknown_universe_exits_1(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    runner = CliRunner()
    result = runner.invoke(cli, ["agents", "nope"])
    assert result.exit_code == 1


def test_cli_table_smoke(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("agents smoke")
    _seed_two_agents(universe_dir)
    runner = CliRunner()
    result = runner.invoke(cli, ["agents", universe_dir.name])
    assert result.exit_code == 0, result.output
    assert "alice" in result.output
    assert "bob" in result.output


def test_cli_json_is_valid(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("agents json")
    _seed_two_agents(universe_dir)
    runner = CliRunner()
    result = runner.invoke(cli, ["agents", universe_dir.name, "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["slug"] == universe_dir.name
    assert any(a["id"] == "alice" for a in payload["agents"])


def test_cli_id_filter_not_found_exits_4(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("agents notfound")
    _seed_two_agents(universe_dir)
    runner = CliRunner()
    result = runner.invoke(cli, ["agents", universe_dir.name, "--id", "ghost"])
    assert result.exit_code == 4
