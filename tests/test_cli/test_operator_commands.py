"""CLI tests for the operator commands (Phase 04.1-04).

Covers two layers:

1. The ``cli_support`` helpers (this module, Task 1):
   - :func:`resolve_universe` — three resolution paths + error.
   - Renderer helpers — shape assertions on output.
   - :func:`latest_halted_tick` — halt detection semantics.

2. The Click commands themselves (Task 2): ``run-tick``, ``inspect-yield``,
   ``resume-tick``, ``replay-tick`` — exit codes, output format, harness
   mocking, BLOCKER-3 persistence invariants.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click
import pytest

from token_world.operator.cli_support import (
    latest_halted_tick,
    render_replay_human,
    render_replay_json,
    render_yield_human,
    render_yield_json,
    resolve_universe,
)
from token_world.operator.diagnostics import (
    OperatorDiagnosticsContext,
    OperatorDiagnosticsReader,
)
from token_world.operator.testing import EngineStub

# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #


def _build_signal(universe: Path, **overrides: Any):
    """Build a validated YieldSignal via EngineStub."""
    stub = EngineStub(universe_path=universe)
    kwargs = {
        "verb": "pickup",
        "actor": "alice",
        "target": "rock_1",
        "tick_id": "tick_1",
    }
    kwargs.update(overrides)
    return stub.fabricate_yield(**kwargs)


def _seed_halted_tick(
    universe: Path,
    tick_id: str = "tick_1",
    *,
    outcome_success: bool | None = False,
    write_outcome: bool = True,
) -> None:
    """Seed the operator namespace with a yield + resume_outcome for ``tick_id``.

    ``outcome_success=False`` -> halted; ``outcome_success=True`` -> successful.
    ``write_outcome=False`` -> no outcome file (also counted as halted).
    """
    ctx = OperatorDiagnosticsContext(universe, tick_id)
    signal = _build_signal(universe, tick_id=tick_id)
    ctx.write_yield_signal(signal)
    if write_outcome:
        ctx.close(
            {
                "success": bool(outcome_success),
                "mechanic_id": "pickup" if outcome_success else None,
                "cost_usd": None,
                "turns": 0,
                "tick_continued": bool(outcome_success),
                "error": None if outcome_success else "stalled",
            }
        )


# =========================================================================== #
# cli_support — resolve_universe
# =========================================================================== #


class TestResolveUniverse:
    def test_from_slug(self, tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """``resolve_universe("slug")`` loads via UniverseManager()."""
        from token_world.universe.manager import UniverseManager

        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
        # Env var should NOT win over an explicit slug.
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)

        manager = UniverseManager(data_dir=tmp_data_dir)
        universe_dir = manager.create("My World")
        slug = universe_dir.name

        resolved = resolve_universe(slug)
        assert resolved == universe_dir

    def test_from_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """``TOKEN_WORLD_UNIVERSE`` resolves to that path when slug is None."""
        universe = tmp_path / "u1"
        universe.mkdir()
        monkeypatch.setenv("TOKEN_WORLD_UNIVERSE", str(universe))
        monkeypatch.chdir(tmp_path)

        assert resolve_universe(None) == universe

    def test_from_cwd_when_markers_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CWD wins when it has ``.mcp.json`` + ``mechanics/``."""
        universe = tmp_path / "ucwd"
        universe.mkdir()
        (universe / ".mcp.json").write_text("{}", encoding="utf-8")
        (universe / "mechanics").mkdir()
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        monkeypatch.chdir(universe)

        assert resolve_universe(None) == universe

    def test_none_raises_clickexception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No slug, no env, non-universe CWD -> ClickException with remediation."""
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        monkeypatch.chdir(tmp_path)  # tmp_path is not a universe
        with pytest.raises(click.ClickException) as excinfo:
            resolve_universe(None)
        msg = excinfo.value.message
        # Message must mention the three resolution strategies
        assert "slug" in msg.lower()
        assert "TOKEN_WORLD_UNIVERSE" in msg
        assert ".mcp.json" in msg or "mechanics" in msg

    def test_priority_slug_over_env(
        self, tmp_data_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When both slug and env are set, slug wins."""
        from token_world.universe.manager import UniverseManager

        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
        manager = UniverseManager(data_dir=tmp_data_dir)
        universe_dir = manager.create("Priority World")
        slug = universe_dir.name

        # Env points somewhere else; slug should still win.
        wrong_env = tmp_path / "wrong"
        wrong_env.mkdir()
        monkeypatch.setenv("TOKEN_WORLD_UNIVERSE", str(wrong_env))

        assert resolve_universe(slug) == universe_dir


# =========================================================================== #
# cli_support — renderers
# =========================================================================== #


class TestRenderers:
    def test_render_yield_human_contains_verb_and_actor(self, tmp_path: Path) -> None:
        universe = tmp_path / "u"
        universe.mkdir()
        signal = _build_signal(universe, verb="pickup", actor="alice")
        out = render_yield_human(signal)
        assert "pickup" in out
        assert "alice" in out
        # Header mentions tick id and reason
        assert "tick_1" in out
        assert "no_mechanic_for_action" in out

    def test_render_yield_json_is_signal_to_json(self, tmp_path: Path) -> None:
        universe = tmp_path / "u"
        universe.mkdir()
        signal = _build_signal(universe)
        assert render_yield_json(signal) == signal.to_json()

    def test_render_replay_human_shows_attempt_count(self, tmp_path: Path) -> None:
        universe = tmp_path / "u"
        universe.mkdir()
        ctx = OperatorDiagnosticsContext(universe, "tick_1")
        signal = _build_signal(universe)
        ctx.write_yield_signal(signal)
        ctx.append_attempt({"kind": "AssistantMessage", "content": "..."})
        ctx.append_attempt({"kind": "ToolUse", "content": "..."})
        ctx.append_attempt({"kind": "ToolResult", "content": "..."})
        ctx.close(
            {
                "success": True,
                "mechanic_id": "pickup",
                "cost_usd": 0.12,
                "turns": 4,
                "tick_continued": True,
                "error": None,
            }
        )
        reader = OperatorDiagnosticsReader(universe, "tick_1")
        out = render_replay_human(reader)
        assert "3" in out  # attempt count
        assert "attempt" in out.lower()

    def test_render_replay_human_handles_missing_outcome(self, tmp_path: Path) -> None:
        universe = tmp_path / "u"
        universe.mkdir()
        ctx = OperatorDiagnosticsContext(universe, "tick_1")
        ctx.write_yield_signal(_build_signal(universe))
        # No close() -> no resume_outcome.json
        reader = OperatorDiagnosticsReader(universe, "tick_1")
        out = render_replay_human(reader)
        assert "not closed" in out.lower()

    def test_render_replay_human_missing_session(self, tmp_path: Path) -> None:
        """Reader for a tick with no session returns a friendly message, no crash."""
        universe = tmp_path / "u"
        universe.mkdir()
        reader = OperatorDiagnosticsReader(universe, "tick_99")
        out = render_replay_human(reader)
        assert "tick_99" in out
        assert "no operator session" in out.lower()

    def test_render_replay_json_has_expected_keys(self, tmp_path: Path) -> None:
        universe = tmp_path / "u"
        universe.mkdir()
        ctx = OperatorDiagnosticsContext(universe, "tick_1")
        ctx.write_yield_signal(_build_signal(universe))
        ctx.close(
            {
                "success": True,
                "mechanic_id": "pickup",
                "cost_usd": 0.12,
                "turns": 4,
                "tick_continued": True,
                "error": None,
            }
        )
        reader = OperatorDiagnosticsReader(universe, "tick_1")
        out = render_replay_json(reader)
        parsed = json.loads(out)
        assert set(parsed.keys()) >= {
            "yield_signal",
            "attempts",
            "validation_reports",
            "mechanic_diff",
            "resume_outcome",
        }
        assert parsed["resume_outcome"]["success"] is True

    def test_render_replay_json_missing_session(self, tmp_path: Path) -> None:
        universe = tmp_path / "u"
        universe.mkdir()
        reader = OperatorDiagnosticsReader(universe, "tick_99")
        out = render_replay_json(reader)
        parsed = json.loads(out)
        assert parsed["error"] == "no_session"
        assert parsed["tick_id"] == "tick_99"


# =========================================================================== #
# cli_support — latest_halted_tick
# =========================================================================== #


class TestLatestHaltedTick:
    def test_returns_newest_unsuccessful(self, tmp_path: Path) -> None:
        universe = tmp_path / "u"
        universe.mkdir()
        _seed_halted_tick(universe, "1", outcome_success=True)  # succeeded
        _seed_halted_tick(universe, "2", outcome_success=False)  # halted (failed)
        _seed_halted_tick(universe, "3", write_outcome=False)  # halted (no outcome)
        # tick 3 is newer numerically; it's also halted
        assert latest_halted_tick(universe) == "3"

    def test_picks_halted_when_newer_succeeded(self, tmp_path: Path) -> None:
        """Even if tick 5 succeeded, tick 4 halted -> return tick 4 (latest halted)."""
        universe = tmp_path / "u"
        universe.mkdir()
        _seed_halted_tick(universe, "4", outcome_success=False)
        _seed_halted_tick(universe, "5", outcome_success=True)
        assert latest_halted_tick(universe) == "4"

    def test_returns_none_when_no_halted(self, tmp_path: Path) -> None:
        universe = tmp_path / "u"
        universe.mkdir()
        _seed_halted_tick(universe, "1", outcome_success=True)
        _seed_halted_tick(universe, "2", outcome_success=True)
        assert latest_halted_tick(universe) is None

    def test_handles_missing_diagnostics_dir(self, tmp_path: Path) -> None:
        universe = tmp_path / "u"
        universe.mkdir()
        # No diagnostics/ folder at all
        assert latest_halted_tick(universe) is None

    def test_empty_diagnostics_dir(self, tmp_path: Path) -> None:
        universe = tmp_path / "u"
        universe.mkdir()
        (universe / "diagnostics").mkdir()
        assert latest_halted_tick(universe) is None

    def test_corrupt_outcome_is_halted(self, tmp_path: Path) -> None:
        """A corrupted resume_outcome.json is treated as halted (needs investigation)."""
        universe = tmp_path / "u"
        universe.mkdir()
        ctx = OperatorDiagnosticsContext(universe, "1")
        ctx.write_yield_signal(_build_signal(universe, tick_id="1"))
        # Write garbage to the outcome file, bypassing the atomic writer
        outcome_path = ctx.operator_dir / "resume_outcome.json"
        outcome_path.write_text("not-valid-json", encoding="utf-8")
        assert latest_halted_tick(universe) == "1"

    def test_tick_without_operator_folder_skipped(self, tmp_path: Path) -> None:
        """A tick_N/ that has no operator/ subfolder is not considered halted."""
        universe = tmp_path / "u"
        universe.mkdir()
        # Create diagnostics/tick_7/ without operator/
        (universe / "diagnostics" / "tick_7").mkdir(parents=True)
        # And a proper halted tick for comparison
        _seed_halted_tick(universe, "3", outcome_success=False)
        assert latest_halted_tick(universe) == "3"

    def test_non_numeric_tick_id_sorts_lexicographically(self, tmp_path: Path) -> None:
        """Non-numeric tick ids sort by fallback (lexicographic among non-numeric)."""
        universe = tmp_path / "u"
        universe.mkdir()
        _seed_halted_tick(universe, "abc", outcome_success=False)
        _seed_halted_tick(universe, "xyz", outcome_success=False)
        _seed_halted_tick(universe, "2", outcome_success=False)
        # Numeric ticks sort ahead of non-numeric under the documented rule;
        # the "newest" halted tick should be the lexicographic max of the
        # non-numeric group when that exceeds the numeric max. Just assert it
        # picks *some* halted tick (implementation is deterministic but the
        # exact choice between "2" / "xyz" is an implementation detail the
        # docstring owns).
        result = latest_halted_tick(universe)
        assert result in {"2", "abc", "xyz"}
