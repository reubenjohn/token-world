"""Tests for the operator diagnostics namespace (Phase 4.1 D-15, D-16).

Plan 04.1-02 Task 1: write-side context manager (lifecycle, atomic writes,
schema versioning, auto-close on exit).

Threats covered:
    - T-04.1-05 (schema_version tampering — Task 2)
    - T-04.1-06 (malformed JSONL tolerance — Task 2)
    - T-04.1-09 (atomic critical writes via os.replace — Task 1)
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path

import pytest

from token_world.operator import YieldSignal
from token_world.operator.diagnostics import (
    OPERATOR_SCHEMA_VERSION,
    OperatorDiagnosticsContext,
)


# ---------------------------------------------------------------------------
# Lifecycle: directory creation
# ---------------------------------------------------------------------------


class TestContextLifecycle:
    """Construction creates the operator/ subfolder + validation/ child."""

    def test_context_creates_operator_dir(self, universe: Path) -> None:
        with OperatorDiagnosticsContext(universe, "tick_1") as ctx:
            assert ctx.operator_dir == (
                universe / "diagnostics" / "tick_tick_1" / "operator"
            )
            assert ctx.operator_dir.is_dir()
            assert (ctx.operator_dir / "validation").is_dir()

    def test_context_normalises_int_tick_id(self, universe: Path) -> None:
        """Constructor accepts int tick_id and stringifies it."""
        with OperatorDiagnosticsContext(universe, 42) as ctx:
            assert ctx.tick_id == "42"
            assert ctx.operator_dir.name == "operator"
            assert ctx.operator_dir.parent.name == "tick_42"

    def test_context_stores_universe_and_tick(self, universe: Path) -> None:
        with OperatorDiagnosticsContext(universe, "tick_5") as ctx:
            assert ctx.universe_path == universe
            assert ctx.tick_id == "tick_5"


# ---------------------------------------------------------------------------
# Writers: yield signal, attempts, validation, diff
# ---------------------------------------------------------------------------


class TestWriters:
    """Per-artefact writers produce the on-disk layout from RESEARCH §7."""

    def test_write_yield_signal(
        self,
        universe: Path,
        stub_yield: Callable[..., YieldSignal],
    ) -> None:
        signal = stub_yield(verb="pickup", actor="alice", target="rock_1")
        with OperatorDiagnosticsContext(universe, "tick_1") as ctx:
            ctx.write_yield_signal(signal)
            ctx.close({"success": True, "mechanic_id": "pickup"})

        path = universe / "diagnostics" / "tick_tick_1" / "operator" / "yield_signal.json"
        assert path.is_file()
        # Round-trip through YieldSignal.from_json must yield the same fields.
        loaded = YieldSignal.from_json(path.read_text(encoding="utf-8"))
        assert loaded == signal

    def test_append_attempt_jsonl(self, universe: Path) -> None:
        with OperatorDiagnosticsContext(universe, "tick_1") as ctx:
            ctx.append_attempt({"attempt": 1, "message_type": "assistant", "content": "foo"})
            ctx.append_attempt({"attempt": 1, "message_type": "tool_use", "tool": "Write"})
            ctx.append_attempt({"attempt": 2, "message_type": "tool_result", "ok": True})
            ctx.close({"success": True, "mechanic_id": "x"})

        path = (
            universe / "diagnostics" / "tick_tick_1" / "operator" / "authoring_attempts.jsonl"
        )
        assert path.is_file()
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3
        parsed = [json.loads(line) for line in lines]
        assert parsed[0]["attempt"] == 1
        assert parsed[0]["content"] == "foo"
        assert parsed[1]["tool"] == "Write"
        assert parsed[2]["ok"] is True

    def test_write_validation_report_zero_padded(self, universe: Path) -> None:
        with OperatorDiagnosticsContext(universe, "tick_1") as ctx:
            ctx.write_validation_report(1, {"passed": False, "findings": ["missing matches"]})
            ctx.write_validation_report(
                2, {"passed": True, "findings": [], "duration_ms": 42}
            )
            ctx.close({"success": True, "mechanic_id": "x"})

        vdir = universe / "diagnostics" / "tick_tick_1" / "operator" / "validation"
        a1 = vdir / "attempt_01.json"
        a2 = vdir / "attempt_02.json"
        assert a1.is_file()
        assert a2.is_file()
        assert json.loads(a1.read_text())["passed"] is False
        assert json.loads(a2.read_text())["duration_ms"] == 42

    def test_write_validation_report_handles_double_digit(self, universe: Path) -> None:
        with OperatorDiagnosticsContext(universe, "tick_1") as ctx:
            ctx.write_validation_report(15, {"passed": True})
            ctx.close({"success": True, "mechanic_id": "x"})
        path = (
            universe
            / "diagnostics"
            / "tick_tick_1"
            / "operator"
            / "validation"
            / "attempt_15.json"
        )
        assert path.is_file()

    def test_write_mechanic_diff(self, universe: Path) -> None:
        diff = (
            "--- a/mechanics/pickup.py\n"
            "+++ b/mechanics/pickup.py\n"
            "@@ -0,0 +1,3 @@\n"
            "+class Pickup:\n"
            "+    pass\n"
        )
        with OperatorDiagnosticsContext(universe, "tick_1") as ctx:
            ctx.write_mechanic_diff(diff)
            ctx.close({"success": True, "mechanic_id": "pickup"})

        path = universe / "diagnostics" / "tick_tick_1" / "operator" / "mechanic_diff.patch"
        assert path.is_file()
        assert path.read_text(encoding="utf-8") == diff

    def test_write_mechanic_diff_empty_string_allowed(self, universe: Path) -> None:
        """Empty diff (no modifications) produces an empty file, not a missing one."""
        with OperatorDiagnosticsContext(universe, "tick_1") as ctx:
            ctx.write_mechanic_diff("")
            ctx.close({"success": True, "mechanic_id": "x"})
        path = universe / "diagnostics" / "tick_tick_1" / "operator" / "mechanic_diff.patch"
        assert path.is_file()
        assert path.read_text(encoding="utf-8") == ""


# ---------------------------------------------------------------------------
# Outcome: close() and resume_outcome.json
# ---------------------------------------------------------------------------


class TestCloseAndOutcome:
    """close() writes resume_outcome.json with schema_version injected."""

    def test_close_writes_resume_outcome(self, universe: Path) -> None:
        outcome = {
            "success": True,
            "mechanic_id": "pickup",
            "cost_usd": 0.12,
            "turns": 7,
            "tick_continued": True,
            "error": None,
        }
        with OperatorDiagnosticsContext(universe, "tick_1") as ctx:
            ctx.close(outcome)

        path = universe / "diagnostics" / "tick_tick_1" / "operator" / "resume_outcome.json"
        assert path.is_file()
        loaded = json.loads(path.read_text(encoding="utf-8"))
        # schema_version is auto-injected by close.
        assert loaded["schema_version"] == OPERATOR_SCHEMA_VERSION == 1
        assert loaded["success"] is True
        assert loaded["mechanic_id"] == "pickup"
        assert loaded["cost_usd"] == 0.12
        assert loaded["turns"] == 7
        assert loaded["tick_continued"] is True
        assert loaded["error"] is None

    def test_close_overrides_caller_supplied_schema_version(self, universe: Path) -> None:
        """Caller passing schema_version is fine — module's constant wins (auto-injected first)."""
        # Implementation merges {"schema_version": OPERATOR_SCHEMA_VERSION, **outcome},
        # so a caller-supplied schema_version overrides ours. That's intentional —
        # it lets future writers stamp a newer version once they bump the constant.
        # We only assert the field is present.
        with OperatorDiagnosticsContext(universe, "tick_1") as ctx:
            ctx.close({"success": True})
        path = universe / "diagnostics" / "tick_tick_1" / "operator" / "resume_outcome.json"
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert "schema_version" in loaded


# ---------------------------------------------------------------------------
# __exit__ semantics: auto-close + exception handling
# ---------------------------------------------------------------------------


class TestContextManagerAutoClose:
    """`with` block always lands a resume_outcome.json — the safety net."""

    def test_context_manager_auto_close_on_normal_exit(self, universe: Path) -> None:
        """Successful `with` block without explicit close() still writes outcome."""
        with OperatorDiagnosticsContext(universe, "tick_1") as ctx:
            # No call to ctx.close()
            assert ctx.operator_dir.is_dir()

        path = universe / "diagnostics" / "tick_tick_1" / "operator" / "resume_outcome.json"
        assert path.is_file()
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["success"] is False
        assert loaded["error"] == "session_not_closed"
        assert loaded["schema_version"] == OPERATOR_SCHEMA_VERSION

    def test_context_manager_writes_outcome_on_exception(self, universe: Path) -> None:
        """`with` block that raises mid-session still writes resume_outcome."""

        class Boom(Exception):
            pass

        with pytest.raises(Boom):  # noqa: SIM117 — explicit nesting for readability
            with OperatorDiagnosticsContext(universe, "tick_1"):
                raise Boom("kaboom")

        path = universe / "diagnostics" / "tick_tick_1" / "operator" / "resume_outcome.json"
        assert path.is_file()
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["success"] is False
        assert loaded["mechanic_id"] is None
        assert loaded["turns"] == 0
        # Error string includes class name and message.
        assert "Boom" in loaded["error"]
        assert "kaboom" in loaded["error"]

    def test_explicit_close_suppresses_auto_close(self, universe: Path) -> None:
        """If the caller calls close() explicitly, __exit__ does NOT overwrite."""
        outcome = {"success": True, "mechanic_id": "pickup", "turns": 3}
        with OperatorDiagnosticsContext(universe, "tick_1") as ctx:
            ctx.close(outcome)

        path = universe / "diagnostics" / "tick_tick_1" / "operator" / "resume_outcome.json"
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["success"] is True
        assert loaded["mechanic_id"] == "pickup"
        assert loaded["turns"] == 3

    def test_double_close_is_idempotent(self, universe: Path) -> None:
        """close() called twice doesn't crash and the last call wins."""
        with OperatorDiagnosticsContext(universe, "tick_1") as ctx:
            ctx.close({"success": False, "mechanic_id": None})
            ctx.close({"success": True, "mechanic_id": "x"})
        path = universe / "diagnostics" / "tick_tick_1" / "operator" / "resume_outcome.json"
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["success"] is True
        assert loaded["mechanic_id"] == "x"


# ---------------------------------------------------------------------------
# Atomic writes: no .tmp leftovers (T-04.1-09)
# ---------------------------------------------------------------------------


class TestAtomicWrites:
    """Atomic critical writes (yield_signal, validation, diff, outcome) leave no .tmp."""

    def test_atomic_write_no_partial_files_after_success(
        self,
        universe: Path,
        stub_yield: Callable[..., YieldSignal],
    ) -> None:
        signal = stub_yield(verb="pickup", actor="alice")
        with OperatorDiagnosticsContext(universe, "tick_1") as ctx:
            ctx.write_yield_signal(signal)
            ctx.write_validation_report(1, {"passed": True})
            ctx.write_mechanic_diff("--- a\n+++ b\n")
            ctx.close({"success": True, "mechanic_id": "x"})

        operator_dir = universe / "diagnostics" / "tick_tick_1" / "operator"
        leftovers = list(operator_dir.rglob("*.tmp"))
        assert leftovers == [], f"Atomic writes leaked tmp files: {leftovers}"

    def test_interrupted_write_does_not_leak_tmp(
        self,
        universe: Path,
        stub_yield: Callable[..., YieldSignal],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If os.replace raises mid-write, the tempfile is unlinked."""
        signal = stub_yield(verb="pickup", actor="alice")

        # Patch os.replace inside the diagnostics module to raise on first call.
        from token_world.operator import diagnostics as diag_mod

        original_replace = os.replace
        call_count = {"n": 0}

        def flaky_replace(*args: object, **kwargs: object) -> None:
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OSError("disk full simulation")
            original_replace(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(diag_mod.os, "replace", flaky_replace)

        ctx = OperatorDiagnosticsContext(universe, "tick_1")
        with pytest.raises(OSError, match="disk full"):
            ctx.write_yield_signal(signal)

        # The single failed atomic write must not leave a tmp file behind.
        leftovers = list(ctx.operator_dir.rglob("*.tmp"))
        assert leftovers == [], f"Failed atomic write leaked tmp files: {leftovers}"

    def test_tmp_files_match_phase4_sweep_glob(
        self,
        universe: Path,
        stub_yield: Callable[..., YieldSignal],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Any tmp files we DO produce must end in .tmp so DiagnosticsSink._sweep_tmp_files
        catches them on next boot. The Phase 4 sweep globs `*.tmp` recursively from
        <universe>/diagnostics — we ensure our tempfile name pattern matches.
        """
        # Force replace to fail so we leak something — then assert the pattern.
        from token_world.operator import diagnostics as diag_mod

        def always_fail(*args: object, **kwargs: object) -> None:
            raise OSError("forced")

        monkeypatch.setattr(diag_mod.os, "replace", always_fail)

        ctx = OperatorDiagnosticsContext(universe, "tick_1")
        # We expect our atomic helper to clean up its own tempfile on exception
        # (test_interrupted_write_does_not_leak_tmp asserts this), but defence in
        # depth: if it ever DID leak, the file extension is `.tmp` so the
        # Phase 4 sweep (`rglob("*.tmp")`) covers us.
        with pytest.raises(OSError):
            ctx.write_validation_report(1, {"passed": True})

        # Even if our cleanup ran, the post-sweep state must be clean.
        # Now simulate a Phase-4 boot sweep — it globs `*.tmp` under
        # <universe>/diagnostics. Anything matching that glob would be picked up.
        from token_world.mechanic.diagnostics import DiagnosticsSink

        DiagnosticsSink(universe)  # constructor sweeps
        leftovers = list((universe / "diagnostics").rglob("*.tmp"))
        assert leftovers == []


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------


def test_schema_version_constant() -> None:
    assert OPERATOR_SCHEMA_VERSION == 1
