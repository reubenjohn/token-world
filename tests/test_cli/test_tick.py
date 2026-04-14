"""Tests for ``token_world.inspect.tick`` and the ``token-world tick`` CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from token_world.cli import cli
from token_world.inspect.tick import (
    TickNotFoundError,
    load_tick,
    render_json,
    render_tree,
)
from token_world.universe.manager import UniverseManager


def test_load_tick_returns_payload(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(ticks, "1", action_text="open chest")
    payload = load_tick(fake_universe, "1")
    assert payload["tick_id"] == "1"
    assert payload["action_text"] == "open chest"


def test_load_tick_raises_for_missing(fake_universe: Path) -> None:
    with pytest.raises(TickNotFoundError):
        load_tick(fake_universe, "999")


def test_render_tree_includes_all_sections(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(
        ticks,
        "7",
        action_text="walk north",
        classified_action={
            "verb": "walk",
            "subject": "alice",
            "object": "north",
            "modifier": None,
            "confidence": 0.92,
        },
        matched_mechanic_id="movement",
        mutations=[["alice", "location", "room_a", "room_b"]],
        observation_text="You walk north.",
        classifier_in=20,
        classifier_out=10,
        classifier_cost=0.0001,
    )
    payload = load_tick(fake_universe, "7")
    out = render_tree(payload)
    assert "Tick 7" in out
    assert "action_text:" in out
    assert "walk north" in out
    assert "classification:" in out
    assert "verb: 'walk'" in out
    assert "confidence: 0.92" in out
    assert "decision:" in out
    assert "EXECUTED" in out
    assert "movement" in out
    assert "mutations:" in out
    assert "alice.location" in out
    assert "'room_a' -> 'room_b'" in out
    assert "observation:" in out
    assert "metadata:" in out
    assert "duration_ms" in out
    assert "llm[classifier]" in out


def test_render_tree_yielded_status(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(ticks, "3", yielded=True)
    payload = load_tick(fake_universe, "3")
    out = render_tree(payload)
    assert "YIELDED" in out


def test_render_tree_refused_status(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(
        ticks,
        "4",
        refused=True,
        refusal_reason="no_viable_action",
        matched_mechanic_id=None,
    )
    payload = load_tick(fake_universe, "4")
    out = render_tree(payload)
    assert "REFUSED" in out
    assert "no_viable_action" in out


def test_render_tree_handles_no_mutations(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(ticks, "1")
    out = render_tree(load_tick(fake_universe, "1"))
    assert "mutations:" in out
    assert "(none)" in out


def test_render_tree_long_running_action(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(
        ticks,
        "5",
        long_running_action={"action_text": "sleeping", "turns_elapsed": 3},
    )
    out = render_tree(load_tick(fake_universe, "5"))
    assert "long_running_action:" in out
    assert "sleeping" in out


def test_render_json_passthrough(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(ticks, "1", matched_mechanic_id="foo")
    payload = load_tick(fake_universe, "1")
    out = render_json(payload)
    parsed = json.loads(out)
    assert parsed["tick_id"] == "1"
    assert parsed["matched_mechanic_id"] == "foo"


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def _make_universe_with_tick(
    tmp_data_dir: Path, slug_name: str, tick_id: str, write_tick
) -> tuple[str, Path]:
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create(slug_name)
    write_tick(
        universe_dir / "tick_summaries" / "ticks",
        tick_id,
        matched_mechanic_id="walk",
        mutations=[["alice", "loc", "a", "b"]],
    )
    return universe_dir.name, universe_dir


def test_cli_unknown_universe_exits_1(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    runner = CliRunner()
    result = runner.invoke(cli, ["tick", "no-such", "1"])
    assert result.exit_code == 1


def test_cli_missing_tick_exits_2(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch, write_tick
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, _ = _make_universe_with_tick(tmp_data_dir, "tick missing", "1", write_tick)
    runner = CliRunner()
    result = runner.invoke(cli, ["tick", slug, "999"])
    assert result.exit_code == 2
    assert "no tick summary" in result.output.lower()


def test_cli_tree_output_smoke(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch, write_tick
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, _ = _make_universe_with_tick(tmp_data_dir, "tick tree", "1", write_tick)
    runner = CliRunner()
    result = runner.invoke(cli, ["tick", slug, "1"])
    assert result.exit_code == 0, result.output
    assert "Tick 1" in result.output
    assert "EXECUTED" in result.output


def test_cli_json_is_valid_json(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch, write_tick
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, _ = _make_universe_with_tick(tmp_data_dir, "tick json", "1", write_tick)
    runner = CliRunner()
    result = runner.invoke(cli, ["tick", slug, "1", "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["tick_id"] == "1"
