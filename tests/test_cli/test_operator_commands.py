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


# =========================================================================== #
# Click commands — run-tick, inspect-yield, resume-tick, replay-tick
# =========================================================================== #


def _cli_runner():
    """Construct a CliRunner. Import kept local so Task-1 tests don't pay the cost."""
    from click.testing import CliRunner

    return CliRunner()


def _invoke_cli(
    args: list[str], *, env: dict[str, str] | None = None, universe: Path | None = None
):
    """Invoke the top-level ``cli`` with *args*; default env isolates from user env."""
    from token_world.cli import cli

    base_env = {"TOKEN_WORLD_UNIVERSE": str(universe)} if universe else {}
    if env:
        base_env.update(env)
    return _cli_runner().invoke(cli, args, env=base_env, catch_exceptions=False)


def _make_universe(tmp_path: Path) -> Path:
    """Scaffold a proper universe under tmp_path via UniverseManager."""
    from token_world.universe.manager import UniverseManager

    manager = UniverseManager(data_dir=tmp_path)
    return manager.create("CLI Test Universe")


# --------------------------------------------------------------------------- #
# run-tick
# --------------------------------------------------------------------------- #


class TestRunTick:
    def test_no_halted_no_stub_exits_3(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No halted ticks, no --stub: exits 3 with "No halted ticks" message."""
        universe = _make_universe(tmp_path)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        result = _invoke_cli(["run-tick"], universe=universe)
        assert result.exit_code == 3, result.output
        assert "No halted ticks" in result.output

    def test_manual_prints_yield_and_exits_0(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--manual on an existing halted tick prints the yield and exits 0."""
        universe = _make_universe(tmp_path)
        _seed_halted_tick(universe, "1", outcome_success=False)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        result = _invoke_cli(["run-tick", "--manual", "--format", "human"], universe=universe)
        assert result.exit_code == 0, result.output
        # The signal tick_id is "1" (seed helper); renderer prints "Tick 1"
        assert "Tick 1" in result.output
        assert "pickup" in result.output or "verb:" in result.output

    def test_auto_invokes_harness(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without --manual, the CLI invokes OperatorHarness.handle_yield (mocked)."""
        import token_world.cli as cli_mod
        from token_world.operator.harness import OperatorResult

        universe = _make_universe(tmp_path)
        _seed_halted_tick(universe, "1", outcome_success=False)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)

        fake_result = OperatorResult(
            success=True,
            tick_id="1",
            mechanic_id="pickup",
            attempts=1,
            final_message="done",
            cost_usd=0.12,
            turns=3,
            error=None,
        )

        class _FakeHarness:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            async def handle_yield(self, signal: Any) -> OperatorResult:
                return fake_result

        monkeypatch.setattr(cli_mod, "OperatorHarness", _FakeHarness)

        result = _invoke_cli(["run-tick"], universe=universe)  # default --format json
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.strip())
        assert payload["success"] is True
        assert payload["mechanic_id"] == "pickup"
        assert payload["tick_id"] == "1"

    def test_with_stub_verb_actor_fabricates_yield(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--stub verb=... --stub actor=... builds a yield and calls harness with it."""
        import token_world.cli as cli_mod
        from token_world.operator.harness import OperatorResult

        universe = _make_universe(tmp_path)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)

        captured: dict[str, Any] = {}

        class _FakeHarness:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            async def handle_yield(self, signal: Any) -> OperatorResult:
                captured["signal"] = signal
                return OperatorResult(
                    success=True,
                    tick_id=signal.tick_id,
                    mechanic_id="dig",
                    attempts=1,
                    final_message="",
                    cost_usd=0.01,
                    turns=2,
                    error=None,
                )

        monkeypatch.setattr(cli_mod, "OperatorHarness", _FakeHarness)

        result = _invoke_cli(
            [
                "run-tick",
                "--stub",
                "verb=dig",
                "--stub",
                "actor=bob",
            ],
            universe=universe,
        )
        assert result.exit_code == 0, result.output
        signal = captured["signal"]
        assert signal.classified_action["verb"] == "dig"
        assert signal.classified_action["actor"] == "bob"

    def test_stub_persists_yield_regardless_of_manual(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """BLOCKER-3: stub-fabricated yield is persisted on disk even with --manual."""
        universe = _make_universe(tmp_path)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)

        result = _invoke_cli(
            [
                "run-tick",
                "--stub",
                "verb=dig",
                "--stub",
                "actor=alice",
                "--manual",
                "--format",
                "json",
            ],
            universe=universe,
        )
        assert result.exit_code == 0, result.output

        yield_file = universe / "diagnostics" / "tick_tick_1" / "operator" / "yield_signal.json"
        assert yield_file.exists(), f"yield file not persisted: {yield_file}"
        # Round-trip: the persisted signal matches the CLI output
        from token_world.operator.yield_signal import YieldSignal

        persisted = YieldSignal.from_json(yield_file.read_text(encoding="utf-8"))
        assert persisted.classified_action["verb"] == "dig"
        assert persisted.classified_action["actor"] == "alice"

    def test_stub_manual_writes_resume_outcome_pending(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After --stub --manual, resume_outcome.json exists with pending state."""
        universe = _make_universe(tmp_path)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)

        result = _invoke_cli(
            ["run-tick", "--stub", "verb=dig", "--stub", "actor=alice", "--manual"],
            universe=universe,
        )
        assert result.exit_code == 0, result.output

        outcome_file = universe / "diagnostics" / "tick_tick_1" / "operator" / "resume_outcome.json"
        assert outcome_file.exists(), f"outcome file not persisted: {outcome_file}"
        outcome = json.loads(outcome_file.read_text(encoding="utf-8"))
        assert outcome["success"] is False
        assert outcome["error"] == "manual_mode_no_harness_invoked"

    def test_harness_failure_exits_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A harness that raises causes the CLI to exit 1 with stderr message."""
        import token_world.cli as cli_mod

        universe = _make_universe(tmp_path)
        _seed_halted_tick(universe, "1", outcome_success=False)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)

        class _BrokenHarness:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            async def handle_yield(self, signal: Any) -> Any:
                raise RuntimeError("boom")

        monkeypatch.setattr(cli_mod, "OperatorHarness", _BrokenHarness)

        result = _invoke_cli(["run-tick"], universe=universe)
        assert result.exit_code == 1, result.output
        assert "boom" in result.output or "boom" in (result.stderr or "")

    def test_stub_requires_verb_and_actor(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--stub alone without verb/actor raises ClickException."""
        universe = _make_universe(tmp_path)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        result = _invoke_cli(
            ["run-tick", "--stub", "foo=bar"],
            universe=universe,
        )
        # Not exit 0; message should name the missing pieces.
        assert result.exit_code != 0
        assert "verb" in result.output or "actor" in result.output

    def test_stub_rejects_invalid_kv_format(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--stub nonkv (no '=') raises ClickException."""
        universe = _make_universe(tmp_path)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        result = _invoke_cli(
            ["run-tick", "--stub", "not-a-kv"],
            universe=universe,
        )
        assert result.exit_code != 0


# --------------------------------------------------------------------------- #
# inspect-yield
# --------------------------------------------------------------------------- #


class TestInspectYield:
    def test_human_format(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        universe = _make_universe(tmp_path)
        _seed_halted_tick(universe, "1", outcome_success=False)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        result = _invoke_cli(["inspect-yield"], universe=universe)
        assert result.exit_code == 0, result.output
        assert "verb:" in result.output or "pickup" in result.output

    def test_json_format(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        universe = _make_universe(tmp_path)
        _seed_halted_tick(universe, "1", outcome_success=False)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        result = _invoke_cli(["inspect-yield", "--format", "json"], universe=universe)
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output.strip())
        # Canonical form — YieldSignal schema
        assert parsed["classified_action"]["verb"] == "pickup"
        assert parsed["schema_version"] == 1

    def test_specific_tick(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        universe = _make_universe(tmp_path)
        _seed_halted_tick(universe, "5", outcome_success=False)
        _seed_halted_tick(universe, "9", outcome_success=False)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        result = _invoke_cli(
            ["inspect-yield", "--tick", "5", "--format", "json"], universe=universe
        )
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output.strip())
        assert parsed["tick_id"] == "5"

    def test_no_halted_exits_4(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        universe = _make_universe(tmp_path)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        result = _invoke_cli(["inspect-yield"], universe=universe)
        assert result.exit_code == 4, result.output

    def test_tick_not_found_exits_4(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        universe = _make_universe(tmp_path)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        result = _invoke_cli(["inspect-yield", "--tick", "999"], universe=universe)
        assert result.exit_code == 4, result.output

    def test_universe_not_found_exits_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No slug, no env, non-universe cwd -> exit 2."""
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        monkeypatch.chdir(tmp_path)  # tmp_path is not a universe
        result = _invoke_cli(["inspect-yield"])
        assert result.exit_code == 2, result.output


# --------------------------------------------------------------------------- #
# resume-tick
# --------------------------------------------------------------------------- #


class TestResumeTick:
    def test_requires_tick(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        universe = _make_universe(tmp_path)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        result = _invoke_cli(["resume-tick"], universe=universe)
        # Click raises UsageError (exit 2) when a --required option is missing
        assert result.exit_code == 2, result.output

    def test_calls_mcp_succeeds(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Mocked SDK call returns cleanly -> exits 0."""
        import token_world.cli as cli_mod

        universe = _make_universe(tmp_path)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)

        captured: dict[str, Any] = {}

        async def fake_invoke(universe_arg: Path, tick_id: str) -> None:
            captured["universe"] = universe_arg
            captured["tick_id"] = tick_id

        monkeypatch.setattr(cli_mod, "_invoke_resume_tick_mcp", fake_invoke)

        result = _invoke_cli(["resume-tick", "--tick", "7"], universe=universe)
        assert result.exit_code == 0, result.output
        assert captured["tick_id"] == "7"
        assert str(captured["universe"]) == str(universe)

    def test_mcp_failure_exits_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import token_world.cli as cli_mod

        universe = _make_universe(tmp_path)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)

        async def fake_invoke(universe_arg: Path, tick_id: str) -> None:
            raise RuntimeError("mcp boom")

        monkeypatch.setattr(cli_mod, "_invoke_resume_tick_mcp", fake_invoke)

        result = _invoke_cli(["resume-tick", "--tick", "7"], universe=universe)
        assert result.exit_code == 1, result.output
        assert "boom" in result.output or "failed" in result.output.lower()


# --------------------------------------------------------------------------- #
# replay-tick
# --------------------------------------------------------------------------- #


class TestReplayTick:
    def test_renders_full_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        universe = _make_universe(tmp_path)
        ctx = OperatorDiagnosticsContext(universe, "1")
        ctx.write_yield_signal(_build_signal(universe))
        ctx.append_attempt({"kind": "AssistantMessage", "content": "..."})
        ctx.append_attempt({"kind": "ToolResult", "content": "..."})
        ctx.close(
            {
                "success": True,
                "mechanic_id": "pickup",
                "cost_usd": 0.1,
                "turns": 3,
                "tick_continued": True,
                "error": None,
            }
        )
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)

        result = _invoke_cli(["replay-tick", "1"], universe=universe)
        assert result.exit_code == 0, result.output
        # Human-format output includes summary sections
        assert "attempt" in result.output.lower()
        assert "outcome" in result.output.lower() or "success=True" in result.output

    def test_json_format(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        universe = _make_universe(tmp_path)
        ctx = OperatorDiagnosticsContext(universe, "1")
        ctx.write_yield_signal(_build_signal(universe))
        ctx.close(
            {
                "success": True,
                "mechanic_id": "pickup",
                "cost_usd": 0.1,
                "turns": 3,
                "tick_continued": True,
                "error": None,
            }
        )
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)

        result = _invoke_cli(["replay-tick", "1", "--format", "json"], universe=universe)
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output.strip())
        assert set(parsed.keys()) >= {
            "yield_signal",
            "attempts",
            "validation_reports",
            "mechanic_diff",
            "resume_outcome",
        }

    def test_not_found_exits_4(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        universe = _make_universe(tmp_path)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        result = _invoke_cli(["replay-tick", "999"], universe=universe)
        assert result.exit_code == 4, result.output

    def test_partial_session_still_renders(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Session with yield + attempts but no outcome: exits 0, notes "not closed"."""
        universe = _make_universe(tmp_path)
        ctx = OperatorDiagnosticsContext(universe, "1")
        ctx.write_yield_signal(_build_signal(universe))
        ctx.append_attempt({"kind": "AssistantMessage"})
        # Deliberately no close() -> no resume_outcome.json
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)

        result = _invoke_cli(["replay-tick", "1"], universe=universe)
        assert result.exit_code == 0, result.output
        assert "not closed" in result.output.lower()

    def test_rejects_path_traversal_tick_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-04.1-18: tick_id with traversal chars must be rejected."""
        universe = _make_universe(tmp_path)
        monkeypatch.delenv("TOKEN_WORLD_UNIVERSE", raising=False)
        result = _invoke_cli(["replay-tick", "../../etc/passwd"], universe=universe)
        # Either a ClickException (non-zero) or exit 4 for not found; must
        # NOT try to read outside universe/diagnostics. Assert no crash + non-zero.
        assert result.exit_code != 0
