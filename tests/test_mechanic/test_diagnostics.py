"""Tests for DiagnosticsSink + TickDiagnostics (AUTO-02).

Per 04-03-PLAN Task 2: cover the sink lifecycle, schema, atomic writes,
boot-time cleanup, and every security-relevant code path
(T-04-DIAG-PATH-TRAVERSAL, T-04-PRUNE-DESTRUCTION, T-04-TMP-LEAK).
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from token_world.mechanic.diagnostics import (
    SCHEMA_VERSION,
    DiagnosticsSink,
    TickDiagnostics,
)

# ---------------------------------------------------------------------------
# Lifecycle + schema
# ---------------------------------------------------------------------------


def test_sink_creates_diagnostics_root_on_init(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    assert (tmp_path / "diagnostics").is_dir()
    assert sink.root == (tmp_path / "diagnostics").resolve()


def test_open_tick_context_manager_writes_summary(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    with sink.open_tick(5) as ctx:
        ctx.set_summary(status="ok")
    summary_path = tmp_path / "diagnostics" / "tick_5" / "summary.json"
    assert summary_path.is_file()
    data = json.loads(summary_path.read_text())
    assert data["schema_version"] == SCHEMA_VERSION == 1
    assert data["tick_id"] == 5
    assert data["status"] == "ok"


def test_atomic_summary_write_has_no_temp_leftovers(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    with sink.open_tick(5) as ctx:
        ctx.write_action("hello")
    tick_dir = tmp_path / "diagnostics" / "tick_5"
    # Any *.tmp leftovers would indicate a torn atomic write.
    leftovers = list(tick_dir.rglob("*.tmp"))
    assert leftovers == []


def test_mutations_jsonl_is_append_only(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    with sink.open_tick(1) as ctx:
        ctx.append_mutation({"type": "set_property", "target": "alice", "value": 1})
        ctx.append_mutation({"type": "set_property", "target": "alice", "value": 2})
        ctx.append_mutation({"type": "add_edge", "target": "bob"})
    p = tmp_path / "diagnostics" / "tick_1" / "execution" / "mutations.jsonl"
    assert p.is_file()
    lines = p.read_text().splitlines()
    assert len(lines) == 3
    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["value"] == 1
    assert parsed[1]["value"] == 2
    assert parsed[2]["type"] == "add_edge"


def test_write_classification_creates_subfolder_and_files(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    with sink.open_tick(2) as ctx:
        ctx.write_classification(
            prompt="classify me",
            response="raw",
            parsed={"intent": "move"},
        )
    d = tmp_path / "diagnostics" / "tick_2" / "classification"
    assert (d / "prompt.txt").read_text() == "classify me"
    assert (d / "response.txt").read_text() == "raw"
    assert json.loads((d / "parsed.json").read_text()) == {"intent": "move"}


def test_write_observation_creates_subfolder_and_files(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    with sink.open_tick(3) as ctx:
        ctx.write_observation(
            prompt="observe",
            response="you see X",
            parsed={"observation": "X"},
        )
    d = tmp_path / "diagnostics" / "tick_3" / "observation"
    assert (d / "prompt.txt").read_text() == "observe"
    assert (d / "response.txt").read_text() == "you see X"
    assert json.loads((d / "parsed.json").read_text()) == {"observation": "X"}


def test_write_matching_and_execution_trace(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    with sink.open_tick(4) as ctx:
        ctx.write_matching([{"mechanic_id": "movement", "score": 0.8}])
        ctx.write_execution_trace({"root": {"mechanic": "movement", "children": []}})
    matching = json.loads((tmp_path / "diagnostics" / "tick_4" / "matching.json").read_text())
    trace = json.loads(
        (tmp_path / "diagnostics" / "tick_4" / "execution" / "trace.json").read_text()
    )
    assert matching[0]["mechanic_id"] == "movement"
    assert trace["root"]["mechanic"] == "movement"


# ---------------------------------------------------------------------------
# open_validation
# ---------------------------------------------------------------------------


def test_open_validation_path_contains_timestamp_and_safe_id(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    folder = sink.open_validation("movement")
    assert folder.is_dir()
    # Parent is diagnostics/validation/
    assert folder.parent == (tmp_path / "diagnostics" / "validation").resolve()
    assert re.fullmatch(r"\d{8}T\d{6}Z_movement", folder.name)


def test_open_validation_sanitizes_dangerous_mechanic_id(tmp_path: Path) -> None:
    """T-04-DIAG-PATH-TRAVERSAL: caller-supplied id cannot escape root."""
    sink = DiagnosticsSink(tmp_path)
    folder = sink.open_validation("../../../etc/passwd")
    resolved = folder.resolve()
    # Key guarantee: resolved path is under the diagnostics root.
    resolved.relative_to((tmp_path / "diagnostics").resolve())
    # Path separators must have been sanitised so the id cannot be used to
    # climb directories on the filesystem.
    assert "/" not in folder.name
    assert "\\" not in folder.name
    # And we definitely aren't at the attacker's target.
    assert folder != Path("/etc/passwd")
    assert folder.parent == (tmp_path / "diagnostics" / "validation").resolve()


def test_open_validation_empty_id_falls_back_to_unknown(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    folder = sink.open_validation("")
    assert folder.name.endswith("_unknown")


# ---------------------------------------------------------------------------
# Boot-time tmp cleanup
# ---------------------------------------------------------------------------


def test_boot_time_cleanup_removes_stale_tmp_files(tmp_path: Path) -> None:
    """T-04-TMP-LEAK: next boot sweeps leftover .tmp files."""
    # Seed a leftover tmp file as if a prior write had crashed mid-flight.
    diag = tmp_path / "diagnostics" / "tick_1"
    diag.mkdir(parents=True)
    leftover = diag / "summary.json.abc123.tmp"
    leftover.write_text("{partial:")
    assert leftover.exists()

    # New sink on this universe must sweep it.
    DiagnosticsSink(tmp_path)
    assert not leftover.exists()


def test_boot_time_cleanup_does_not_follow_symlinks(tmp_path: Path) -> None:
    """Sweep must NOT follow symlinks whose target lies outside the root."""
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "precious.tmp"
    victim.write_text("keep me")

    diag = tmp_path / "diagnostics" / "tick_1"
    diag.mkdir(parents=True)
    link = diag / "summary.json.xyz.tmp"
    link.symlink_to(victim)

    DiagnosticsSink(tmp_path)

    # The victim outside the root must still exist.
    assert victim.exists()
    assert victim.read_text() == "keep me"


# ---------------------------------------------------------------------------
# prune()
# ---------------------------------------------------------------------------


def _make_tick_folder(tmp_path: Path, tick_id: int) -> Path:
    d = tmp_path / "diagnostics" / f"tick_{tick_id}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "summary.json").write_text(
        json.dumps({"schema_version": 1, "tick_id": tick_id, "status": "ok"})
    )
    return d


def test_prune_requires_cutoff(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    with pytest.raises(ValueError, match="before_tick or before_date"):
        sink.prune()


def test_prune_dry_run_returns_candidates_without_deleting(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    d1 = _make_tick_folder(tmp_path, 1)
    d5 = _make_tick_folder(tmp_path, 5)
    d10 = _make_tick_folder(tmp_path, 10)

    candidates = sink.prune(before_tick=6)

    # tick_1 and tick_5 qualify; tick_10 does not.
    names = sorted(p.name for p in candidates)
    assert names == ["tick_1", "tick_5"]
    # Dry-run: all three folders still exist on disk.
    assert d1.exists()
    assert d5.exists()
    assert d10.exists()


def test_prune_confirm_true_actually_deletes(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    d1 = _make_tick_folder(tmp_path, 1)
    d5 = _make_tick_folder(tmp_path, 5)
    d10 = _make_tick_folder(tmp_path, 10)

    deleted = sink.prune(before_tick=6, confirm=True)
    names = sorted(p.name for p in deleted)
    assert names == ["tick_1", "tick_5"]
    assert not d1.exists()
    assert not d5.exists()
    assert d10.exists()


def test_prune_refuses_to_follow_symlinks(tmp_path: Path) -> None:
    """T-04-PRUNE-DESTRUCTION: symlinks in diagnostics are skipped."""
    sink = DiagnosticsSink(tmp_path)
    _make_tick_folder(tmp_path, 1)

    # Real directory outside the diagnostics tree (must survive).
    outside = tmp_path / "outside_precious"
    outside.mkdir()
    precious = outside / "precious.txt"
    precious.write_text("keep me safe")

    # Plant a symlink named tick_99 pointing at the outside directory.
    link = tmp_path / "diagnostics" / "tick_99"
    link.symlink_to(outside)

    candidates = sink.prune(before_tick=100, confirm=True)

    # The symlink must NOT appear as a candidate.
    assert all(c.name != "tick_99" for c in candidates)
    # The outside directory and its file must remain intact.
    assert outside.exists()
    assert precious.exists()
    assert precious.read_text() == "keep me safe"


def test_prune_refuses_path_outside_root_when_symlinked(tmp_path: Path) -> None:
    """A symlinked tick directory pointing outside root must not be deleted."""
    sink = DiagnosticsSink(tmp_path)

    outside = tmp_path / "escape_target"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("do not delete")

    # tick_1 is a real folder (should be a candidate).
    _make_tick_folder(tmp_path, 1)
    # tick_2 is a symlink to the outside dir.
    (tmp_path / "diagnostics" / "tick_2").symlink_to(outside)

    sink.prune(before_tick=100, confirm=True)

    # The escape target and its file still exist.
    assert outside.exists()
    assert sentinel.exists()


def test_prune_by_date_filters_validation_folders(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    vroot = tmp_path / "diagnostics" / "validation"
    vroot.mkdir(parents=True)
    # Old folder (name-embedded timestamp 2020).
    old = vroot / "20200101T120000Z_movement"
    old.mkdir()
    (old / "report.json").write_text("{}")
    # Future folder (name-embedded timestamp 3000).
    future = vroot / "30000101T120000Z_movement"
    future.mkdir()
    (future / "report.json").write_text("{}")

    cutoff = date(2021, 1, 1)
    candidates = sink.prune(before_date=cutoff, confirm=True)

    names = [p.name for p in candidates]
    assert "20200101T120000Z_movement" in names
    assert "30000101T120000Z_movement" not in names
    assert not old.exists()
    assert future.exists()


def test_prune_by_date_ignores_tick_folder_when_newer(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    _make_tick_folder(tmp_path, 7)
    # A date in the far past means no tick folder qualifies.
    cutoff = date(1999, 1, 1)
    candidates = sink.prune(before_date=cutoff)
    tick_candidates = [p for p in candidates if p.name.startswith("tick_")]
    assert tick_candidates == []


# ---------------------------------------------------------------------------
# finalize semantics
# ---------------------------------------------------------------------------


def test_finalize_is_idempotent(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    with sink.open_tick(2) as ctx:
        ctx.set_summary(status="ok", mechanics_fired=["movement"])
        ctx.finalize()
        # Second finalize must not raise nor rewrite.
        ctx.finalize()
    data = json.loads((tmp_path / "diagnostics" / "tick_2" / "summary.json").read_text())
    assert data["status"] == "ok"
    assert data["mechanics_fired"] == ["movement"]


def test_status_defaults_to_ok_when_unset(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    with sink.open_tick(3) as _ctx:
        pass  # no set_summary call
    data = json.loads((tmp_path / "diagnostics" / "tick_3" / "summary.json").read_text())
    assert data["status"] == "ok"


def test_finalize_is_implicit_on_context_exit_even_on_error(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)

    class Boom(Exception):
        pass

    with pytest.raises(Boom):  # noqa: SIM117
        with sink.open_tick(4) as ctx:
            ctx.set_summary(status="error")
            raise Boom
    # summary.json must have been flushed despite the exception.
    data = json.loads((tmp_path / "diagnostics" / "tick_4" / "summary.json").read_text())
    assert data["status"] == "error"


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


def test_tick_diagnostics_exposes_dir(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    with sink.open_tick(99) as ctx:
        assert isinstance(ctx, TickDiagnostics)
        assert ctx.tick_id == 99
        assert ctx.dir == tmp_path / "diagnostics" / "tick_99"


def test_schema_version_constant_is_one() -> None:
    assert SCHEMA_VERSION == 1


def test_prune_returns_empty_list_when_nothing_qualifies(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    _make_tick_folder(tmp_path, 100)
    candidates = sink.prune(before_tick=50)
    assert candidates == []


def test_prune_by_date_with_future_cutoff_catches_everything(tmp_path: Path) -> None:
    sink = DiagnosticsSink(tmp_path)
    _make_tick_folder(tmp_path, 1)
    far_future = date.today() + timedelta(days=365 * 10)
    candidates = sink.prune(before_date=far_future)
    assert any(p.name == "tick_1" for p in candidates)
