"""Tests for scripts/migrate_tick_summaries.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Import the script module directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import migrate_tick_summaries as mts

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_BASE_TICK = {
    "schema_version": 1,
    "tick_id": "1",
    "timestamp_iso": "2026-01-01T00:00:00Z",
    "action_text": "I try to do something.",
    "classified_action": {
        "actor": "mira",
        "verb": "do",
        "target": "thing",
        "indirect_object": None,
        "params": {},
    },
    "matched_mechanic_id": "do_thing",
    "yielded": False,
    "refused": False,
    "refusal_reason": None,
    "mutations": {"count": 0, "list": []},
    "observation_text": "Nothing happens.",
    "long_running_action": None,
    "classified_actions": [],
    "duration_ms": 1000,
    "llm_tokens_by_stage": {"classifier": {"in": 0, "out": 0}, "observer": {"in": 100, "out": 10}},
    "llm_cost_usd_by_stage": {"classifier": 0.0, "observer": 0.001},
}


def _make_tick(tick_id: str, **overrides: object) -> dict:
    t = dict(_BASE_TICK)
    t["tick_id"] = tick_id
    t.update(overrides)
    return t


@pytest.fixture()
def ticks_dir(tmp_path: Path) -> Path:
    """Create a temp ticks directory with 3 false-EXECUTED + 1 legitimate tick."""
    d = tmp_path / "tick_summaries" / "ticks"
    d.mkdir(parents=True)

    false_executed = [
        _make_tick("1"),  # 0-mutation, not refused, not yielded
        _make_tick("2", action_text="I lift the lid.", matched_mechanic_id="lift"),
        _make_tick("3", matched_mechanic_id="water"),
    ]
    legitimate = [
        _make_tick("4", mutations={"count": 1, "list": [["obj", "prop", None, "val"]]}),
        _make_tick("5", refused=True, refusal_reason="mechanic_check_failed"),
        _make_tick("6", yielded=True),
    ]

    for tick in false_executed + legitimate:
        path = d / f"tick_{tick['tick_id']}.json"
        path.write_text(json.dumps(tick, indent=2), encoding="utf-8")

    return d


@pytest.fixture()
def universe_dir(ticks_dir: Path) -> Path:
    """Return the universe root (parent of tick_summaries/)."""
    return ticks_dir.parent.parent


# ---------------------------------------------------------------------------
# is_false_executed
# ---------------------------------------------------------------------------


def test_is_false_executed_detects_zero_mutation_tick() -> None:
    tick = _make_tick("1")
    assert mts._is_false_executed(tick) is True


def test_is_false_executed_ignores_already_refused() -> None:
    tick = _make_tick("1", refused=True, refusal_reason="mechanic_check_failed")
    assert mts._is_false_executed(tick) is False


def test_is_false_executed_ignores_yielded() -> None:
    tick = _make_tick("1", yielded=True)
    assert mts._is_false_executed(tick) is False


def test_is_false_executed_ignores_tick_with_mutations() -> None:
    tick = _make_tick("1", mutations={"count": 2, "list": [[], []]})
    assert mts._is_false_executed(tick) is False


# ---------------------------------------------------------------------------
# apply_fix
# ---------------------------------------------------------------------------


def test_apply_fix_sets_refused_and_reason() -> None:
    tick = _make_tick("1")
    fixed = mts._apply_fix(tick)
    assert fixed["refused"] is True
    assert fixed["refusal_reason"] == "mechanic_check_failed"
    # Original not mutated
    assert tick["refused"] is False


def test_apply_fix_preserves_other_fields() -> None:
    tick = _make_tick("99", action_text="Custom action")
    fixed = mts._apply_fix(tick)
    assert fixed["action_text"] == "Custom action"
    assert fixed["tick_id"] == "99"


# ---------------------------------------------------------------------------
# run() — integration passing universe_dir directly (no UniverseManager needed)
# ---------------------------------------------------------------------------


def test_dry_run_lists_affected_ticks(universe_dir: Path, capsys: pytest.CaptureFixture) -> None:
    count = mts.run("test_slug", dry_run=True, universe_dir=universe_dir)

    assert count == 3  # 3 false-executed ticks

    out = capsys.readouterr().out
    assert "1" in out
    assert "dry-run" in out.lower()

    # Files must NOT be modified
    for tid in ("1", "2", "3"):
        data = json.loads(
            (universe_dir / "tick_summaries" / "ticks" / f"tick_{tid}.json").read_text()
        )
        assert data["refused"] is False


def test_apply_rewrites_false_executed_ticks(universe_dir: Path) -> None:
    count = mts.run("test_slug", dry_run=False, universe_dir=universe_dir)

    assert count == 3

    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    for tid in ("1", "2", "3"):
        data = json.loads((ticks_dir / f"tick_{tid}.json").read_text())
        assert data["refused"] is True, f"tick {tid} should be refused"
        assert data["refusal_reason"] == "mechanic_check_failed", f"tick {tid} reason"

    # Legitimate ticks unchanged
    data4 = json.loads((ticks_dir / "tick_4.json").read_text())
    assert data4["refused"] is False
    data5 = json.loads((ticks_dir / "tick_5.json").read_text())
    assert data5["refused"] is True
    assert data5["refusal_reason"] == "mechanic_check_failed"


def test_apply_is_idempotent(universe_dir: Path) -> None:
    count1 = mts.run("test_slug", dry_run=False, universe_dir=universe_dir)
    count2 = mts.run("test_slug", dry_run=False, universe_dir=universe_dir)

    assert count1 == 3
    assert count2 == 0  # second run finds nothing to migrate


def test_empty_ticks_dir(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    empty_universe = tmp_path / "empty_universe"
    count = mts.run("test_slug", dry_run=True, universe_dir=empty_universe)
    assert count == 0
