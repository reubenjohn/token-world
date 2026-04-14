"""Tests for ``token_world.inspect.watch`` and the ``token-world watch`` CLI."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from click.testing import CliRunner

from token_world.cli import cli
from token_world.inspect.watch import _format_tick_line, watch_loop
from token_world.universe.manager import UniverseManager

# ---------------------------------------------------------------------------
# _format_tick_line unit tests
# ---------------------------------------------------------------------------


def test_format_tick_line_yielded() -> None:
    line = _format_tick_line(
        {
            "tick_id": "1",
            "timestamp_iso": "2026-04-14T00:00:00Z",
            "yielded": True,
            "mutations": {"count": 0, "list": []},
            "observation_text": "you wonder",
        }
    )
    assert "yield" in line
    assert "1" in line
    assert "(0 mut)" in line


def test_format_tick_line_executed() -> None:
    line = _format_tick_line(
        {
            "tick_id": "5",
            "timestamp_iso": "2026-04-14T00:00:00Z",
            "matched_mechanic_id": "walk",
            "mutations": {"count": 1, "list": []},
            "observation_text": "x" * 200,
        }
    )
    assert "walk" in line
    assert "(1 mut)" in line
    # Long obs gets truncated.
    assert "..." in line


def test_format_tick_line_refused_includes_reason() -> None:
    line = _format_tick_line(
        {
            "tick_id": "3",
            "timestamp_iso": "",
            "refused": True,
            "refusal_reason": "no_viable_action",
            "mutations": {"count": 0, "list": []},
            "observation_text": None,
        }
    )
    assert "refuse(no_viable_action)" in line


# ---------------------------------------------------------------------------
# watch_loop unit tests (synthetic clock — never actually sleeps)
# ---------------------------------------------------------------------------


def test_watch_loop_initial_files_not_re_emitted(fake_universe: Path, write_tick) -> None:
    """Files present at startup should NOT be emitted again."""
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(ticks, "1")
    write_tick(ticks, "2")
    buf = io.StringIO()
    seen = watch_loop(
        fake_universe,
        out=buf,
        max_iterations=1,
        sleep=lambda _s: None,
    )
    assert buf.getvalue() == ""
    assert seen == {"1", "2"}


def test_watch_loop_emits_new_files(fake_universe: Path, write_tick) -> None:
    """New files between polls are emitted."""
    ticks = fake_universe / "tick_summaries" / "ticks"
    write_tick(ticks, "1")  # already present at startup
    new_files_written = [False]

    def _maybe_write(_seconds: float) -> None:
        if not new_files_written[0]:
            write_tick(ticks, "2", matched_mechanic_id="walk")
            write_tick(ticks, "3", yielded=True)
            new_files_written[0] = True

    buf = io.StringIO()
    seen = watch_loop(
        fake_universe,
        out=buf,
        max_iterations=2,
        sleep=_maybe_write,  # writes the new files between iterations 1 and 2
    )
    output = buf.getvalue()
    assert "2" in output
    assert "3" in output
    assert "walk" in output
    assert "yield" in output
    assert seen >= {"1", "2", "3"}


def test_watch_loop_skips_malformed_but_marks_seen(fake_universe: Path, write_tick) -> None:
    ticks = fake_universe / "tick_summaries" / "ticks"
    (ticks).mkdir(parents=True, exist_ok=True)
    (ticks / "tick_1.json").write_text("{not json", encoding="utf-8")
    buf = io.StringIO()
    seen = watch_loop(
        fake_universe,
        out=buf,
        max_iterations=1,
        sleep=lambda _s: None,
        initial_seen=set(),  # force re-scan to test the malformed branch
    )
    assert buf.getvalue() == ""  # malformed file produces no output
    assert "1" in seen


# ---------------------------------------------------------------------------
# CLI integration (end early via KeyboardInterrupt — simulated by patching)
# ---------------------------------------------------------------------------


def test_cli_unknown_universe_exits_1(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    runner = CliRunner()
    result = runner.invoke(cli, ["watch", "nope"])
    assert result.exit_code == 1


def test_cli_help_lists_interval_flag() -> None:
    """The watch command exposes ``--interval``."""
    runner = CliRunner()
    result = runner.invoke(cli, ["watch", "--help"])
    assert result.exit_code == 0
    assert "--interval" in result.output


def test_cli_handles_keyboard_interrupt(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ctrl-C exits cleanly with a stopped message on stderr."""

    def _raise(*_a, **_kw):
        raise KeyboardInterrupt

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    monkeypatch.setattr("token_world.inspect.watch.watch_loop", _raise)
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create("watch ki")
    runner = CliRunner()
    result = runner.invoke(cli, ["watch", universe_dir.name])
    # Click runs the command; KeyboardInterrupt is caught and we exit 0.
    assert result.exit_code == 0
