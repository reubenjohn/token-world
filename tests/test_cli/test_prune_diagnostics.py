"""CLI tests for ``token-world prune-diagnostics`` (04-03 Task 3)."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from token_world.cli import cli


def _init_universe(tmp_path: Path, slug: str = "test-universe") -> Path:
    """Create a minimal universe directory that passes ``UniverseManager.load``.

    Layout matches ``get_universes_dir() == $XDG_DATA_HOME/token_world/universes``:
    the universe directory is ``<data_dir>/token_world/universes/<slug>/``. Only
    the bits ``load()`` checks are needed: directory + ``universe.db`` with a
    ``metadata`` table.
    """
    universe_dir = tmp_path / "data" / "token_world" / "universes" / slug
    universe_dir.mkdir(parents=True)
    db_path = universe_dir / "universe.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            [
                ("display_name", "Test"),
                ("slug", slug),
                ("created_at", datetime.now(UTC).isoformat()),
                ("schema_version", "1"),
            ],
        )
    return universe_dir


def _make_tick_dir(universe_dir: Path, tick_id: int) -> Path:
    d = universe_dir / "diagnostics" / f"tick_{tick_id}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "summary.json").write_text(
        json.dumps({"schema_version": 1, "tick_id": tick_id, "status": "ok"})
    )
    return d


def _point_manager_at(monkeypatch, tmp_path: Path) -> None:
    """Redirect ``UniverseManager`` to a tmp data dir so we don't touch $HOME."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))


# ---------------------------------------------------------------------------
# Usage errors
# ---------------------------------------------------------------------------


def test_requires_exactly_one_cutoff(tmp_path: Path, monkeypatch) -> None:
    _point_manager_at(monkeypatch, tmp_path)
    _init_universe(tmp_path, slug="u")
    runner = CliRunner()

    # Neither flag supplied -> exit 2.
    r = runner.invoke(cli, ["prune-diagnostics", "u"])
    assert r.exit_code == 2, r.output
    assert "exactly one" in (r.output + (r.stderr or ""))

    # Both flags supplied -> also exit 2.
    r = runner.invoke(
        cli,
        ["prune-diagnostics", "u", "--before-tick", "3", "--before-date", "2026-01-01"],
    )
    assert r.exit_code == 2, r.output


def test_invalid_date_format_errors(tmp_path: Path, monkeypatch) -> None:
    _point_manager_at(monkeypatch, tmp_path)
    _init_universe(tmp_path, slug="u")
    runner = CliRunner()
    r = runner.invoke(cli, ["prune-diagnostics", "u", "--before-date", "2026-13-99"])
    assert r.exit_code == 2, r.output
    # CliRunner mixes stderr into output by default.
    combined = r.output + (r.stderr or "")
    assert "invalid" in combined.lower()


# ---------------------------------------------------------------------------
# Dry-run vs confirm
# ---------------------------------------------------------------------------


def test_dry_run_lists_candidates_without_deleting(tmp_path: Path, monkeypatch) -> None:
    _point_manager_at(monkeypatch, tmp_path)
    universe_dir = _init_universe(tmp_path, slug="dryrun")
    d1 = _make_tick_dir(universe_dir, 1)
    d5 = _make_tick_dir(universe_dir, 5)
    d10 = _make_tick_dir(universe_dir, 10)

    runner = CliRunner()
    r = runner.invoke(cli, ["prune-diagnostics", "dryrun", "--before-tick", "6"])
    assert r.exit_code == 0, r.output
    assert "Would delete 2" in r.output
    assert "dry-run" in r.output
    # Folders survive.
    assert d1.exists()
    assert d5.exists()
    assert d10.exists()


def test_confirm_actually_deletes(tmp_path: Path, monkeypatch) -> None:
    _point_manager_at(monkeypatch, tmp_path)
    universe_dir = _init_universe(tmp_path, slug="confirmed")
    d1 = _make_tick_dir(universe_dir, 1)
    d5 = _make_tick_dir(universe_dir, 5)
    d10 = _make_tick_dir(universe_dir, 10)

    runner = CliRunner()
    r = runner.invoke(
        cli,
        ["prune-diagnostics", "confirmed", "--before-tick", "6", "--confirm"],
    )
    assert r.exit_code == 0, r.output
    assert "Deleted 2" in r.output
    assert not d1.exists()
    assert not d5.exists()
    assert d10.exists()


# ---------------------------------------------------------------------------
# Missing universe
# ---------------------------------------------------------------------------


def test_missing_universe_exits_1(tmp_path: Path, monkeypatch) -> None:
    _point_manager_at(monkeypatch, tmp_path)
    # No universe created; load() will raise FileNotFoundError.
    (tmp_path / "universes").mkdir(parents=True, exist_ok=True)
    runner = CliRunner()
    r = runner.invoke(
        cli,
        ["prune-diagnostics", "nowhere", "--before-tick", "1"],
    )
    assert r.exit_code == 1, r.output


def test_help_mentions_confirm(tmp_path: Path) -> None:
    """Quick sanity: --help output documents --confirm."""
    runner = CliRunner()
    r = runner.invoke(cli, ["prune-diagnostics", "--help"])
    assert r.exit_code == 0
    assert "--confirm" in r.output
