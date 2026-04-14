"""Tests for ``token_world.inspect.yields`` and the ``token-world yield`` CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from token_world.cli import cli
from token_world.inspect.yields import (
    aggregate,
    find_pending_yields,
    render_json,
    render_table,
)
from token_world.universe.manager import UniverseManager


def _write_yield_file(
    inbox: Path,
    tick_id: str,
    *,
    verb: str = "pickup",
    actor: str = "alice",
    target: str | None = "rock_1",
    action_text: str = "pick up the rock",
    reason: str = "no_mechanic_for_action",
) -> Path:
    """Write a minimal ``<tick>.yield.json`` payload matching YieldSignal shape."""
    inbox.mkdir(parents=True, exist_ok=True)
    payload = {
        "tick_id": tick_id,
        "universe_path": str(inbox.parent),
        "schema_version": 1,
        "reason": reason,
        "action_text": action_text,
        "classified_action": {
            "verb": verb,
            "actor": actor,
            "target": target,
            "params": {},
        },
        "actor_state": {},
        "candidate_mechanic_ids": [],
    }
    path = inbox / f"{tick_id}.yield.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# aggregate() / find_pending_yields() unit tests
# ---------------------------------------------------------------------------


def test_aggregate_no_inbox(fake_universe: Path) -> None:
    """No operator_inbox dir → empty report (graceful)."""
    report = aggregate(fake_universe, slug="t")
    assert report.pending == []
    assert report.not_found_tick is None


def test_aggregate_empty_inbox(fake_universe: Path) -> None:
    """Inbox exists but has no yield files → empty report."""
    (fake_universe / "operator_inbox").mkdir()
    report = aggregate(fake_universe, slug="t")
    assert report.pending == []


def test_aggregate_one_pending_yield(fake_universe: Path) -> None:
    """A solo ``.yield.json`` with no sibling markers → one entry."""
    inbox = fake_universe / "operator_inbox"
    _write_yield_file(inbox, "42")
    report = aggregate(fake_universe, slug="t")
    assert len(report.pending) == 1
    py = report.pending[0]
    assert py.tick_id == "42"
    assert py.verb == "pickup"
    assert py.actor == "alice"
    assert py.target == "rock_1"
    assert py.hint == "no_mechanic_for_action"


def test_aggregate_resolved_yield_ignored(fake_universe: Path) -> None:
    """A ``.yield.json`` with a sibling ``.resolved`` is NOT pending."""
    inbox = fake_universe / "operator_inbox"
    _write_yield_file(inbox, "10", verb="pickup", actor="alice")
    _write_yield_file(inbox, "11", verb="move", actor="bob")
    (inbox / "10.resolved").write_text('{"mechanic_id":"pickup_v1"}', encoding="utf-8")
    report = aggregate(fake_universe, slug="t")
    tick_ids = [p.tick_id for p in report.pending]
    assert "10" not in tick_ids
    assert "11" in tick_ids


def test_aggregate_rejected_yield_ignored(fake_universe: Path) -> None:
    """A ``.yield.json`` with a sibling ``.rejected`` is NOT pending."""
    inbox = fake_universe / "operator_inbox"
    _write_yield_file(inbox, "99")
    (inbox / "99.rejected").write_text('{"reason":"incoherent"}', encoding="utf-8")
    report = aggregate(fake_universe, slug="t")
    assert report.pending == []


def test_aggregate_specific_tick(fake_universe: Path) -> None:
    """``--tick N`` surfaces one yield by tick id."""
    inbox = fake_universe / "operator_inbox"
    _write_yield_file(inbox, "7", verb="speak", actor="carol", target=None)
    report = aggregate(fake_universe, slug="t", tick_id="7")
    assert len(report.pending) == 1
    assert report.pending[0].verb == "speak"
    assert report.pending[0].target is None


def test_aggregate_specific_tick_missing(fake_universe: Path) -> None:
    """``--tick N`` for a nonexistent yield sets not_found_tick."""
    report = aggregate(fake_universe, slug="t", tick_id="999")
    assert report.not_found_tick == "999"
    assert report.pending == []


def test_find_pending_yields_malformed_json(fake_universe: Path) -> None:
    """Malformed yield files are skipped, not fatal."""
    inbox = fake_universe / "operator_inbox"
    inbox.mkdir()
    (inbox / "bad.yield.json").write_text("{not valid json", encoding="utf-8")
    _write_yield_file(inbox, "good")
    pending = find_pending_yields(fake_universe)
    assert [p.tick_id for p in pending] == ["good"]


# ---------------------------------------------------------------------------
# Renderer unit tests
# ---------------------------------------------------------------------------


def test_render_table_empty(fake_universe: Path) -> None:
    out = render_table(aggregate(fake_universe, slug="demo"))
    assert "Pending yields: demo" in out
    assert "inbox empty" in out


def test_render_table_pending_lists_action(fake_universe: Path) -> None:
    inbox = fake_universe / "operator_inbox"
    _write_yield_file(inbox, "42", verb="pickup", actor="alice", target="rock_1")
    out = render_table(aggregate(fake_universe, slug="demo"))
    assert "tick 42" in out
    assert "pickup alice -> rock_1" in out
    assert "hint:" in out


def test_render_table_not_found_tick(fake_universe: Path) -> None:
    out = render_table(aggregate(fake_universe, slug="demo", tick_id="missing"))
    assert "no yield file for tick" in out


def test_render_json_is_valid(fake_universe: Path) -> None:
    inbox = fake_universe / "operator_inbox"
    _write_yield_file(inbox, "42")
    payload = json.loads(render_json(aggregate(fake_universe, slug="demo")))
    assert payload["slug"] == "demo"
    assert payload["not_found_tick"] is None
    assert len(payload["pending"]) == 1
    entry = payload["pending"][0]
    assert entry["tick_id"] == "42"
    assert entry["verb"] == "pickup"


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_unknown_universe_exits_1(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    runner = CliRunner()
    result = runner.invoke(cli, ["yield", "nope"])
    assert result.exit_code == 1


def test_cli_pending_empty_exits_0(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("yield empty")
    runner = CliRunner()
    result = runner.invoke(cli, ["yield", universe_dir.name])
    assert result.exit_code == 0, result.output
    assert "inbox empty" in result.output or "no pending" in result.output


def test_cli_pending_one_yield(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("yield one")
    _write_yield_file(universe_dir / "operator_inbox", "42")
    runner = CliRunner()
    result = runner.invoke(cli, ["yield", universe_dir.name, "--pending"])
    assert result.exit_code == 0, result.output
    assert "tick 42" in result.output
    assert "pickup alice -> rock_1" in result.output


def test_cli_specific_tick(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("yield specific")
    _write_yield_file(universe_dir / "operator_inbox", "42", verb="move")
    runner = CliRunner()
    result = runner.invoke(cli, ["yield", universe_dir.name, "--tick", "42"])
    assert result.exit_code == 0, result.output
    assert "tick 42" in result.output
    assert "move alice" in result.output


def test_cli_specific_tick_missing_exits_4(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("yield missing")
    runner = CliRunner()
    result = runner.invoke(cli, ["yield", universe_dir.name, "--tick", "missing"])
    assert result.exit_code == 4


def test_cli_resolved_yield_hidden(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A resolved yield should not appear in --pending output."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("yield resolved")
    inbox = universe_dir / "operator_inbox"
    _write_yield_file(inbox, "42")
    (inbox / "42.resolved").write_text('{"mechanic_id":"pickup_v1"}', encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["yield", universe_dir.name])
    assert result.exit_code == 0, result.output
    assert "inbox empty" in result.output


def test_cli_json_format_is_valid(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("yield json")
    _write_yield_file(universe_dir / "operator_inbox", "42", verb="speak", target=None)
    runner = CliRunner()
    result = runner.invoke(cli, ["yield", universe_dir.name, "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["slug"] == universe_dir.name
    assert len(payload["pending"]) == 1
    entry = payload["pending"][0]
    assert entry["tick_id"] == "42"
    assert entry["verb"] == "speak"
    assert entry["target"] is None


def test_cli_help_lists_flags() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["yield", "--help"])
    assert result.exit_code == 0
    assert "--pending" in result.output
    assert "--tick" in result.output
    assert "--format" in result.output


def test_cli_pending_and_tick_mutually_exclusive(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("yield clash")
    runner = CliRunner()
    result = runner.invoke(cli, ["yield", universe_dir.name, "--pending", "--tick", "1"])
    assert result.exit_code == 2
    assert "mutually exclusive" in result.output
