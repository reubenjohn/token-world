"""Tests for append_decision_log() and overlap_report in prompts (SC-5/EMERGE-02)."""

from __future__ import annotations

import json
from pathlib import Path

from token_world.operator.subagent import append_decision_log, mechanic_author_prompt

# ---------------------------------------------------------------------------
# test_decision_log_entry_written
# ---------------------------------------------------------------------------


def test_decision_log_entry_written(tmp_path: Path) -> None:
    """Log entry is written on success with correct JSON shape."""
    outcome = {
        "success": True,
        "mechanic_id": "pet_cat",
        "attempts": 2,
        "overlap_score": 0.85,
        "decision": "edit_existing",
    }
    append_decision_log(tmp_path, "42", outcome)

    log_path = tmp_path / "operator-log.jsonl"
    assert log_path.exists()
    line = log_path.read_text(encoding="utf-8").strip()
    entry = json.loads(line)

    assert entry["event"] == "mechanic_decision"
    assert entry["tick_id"] == "42"
    assert entry["mechanic_id"] == "pet_cat"
    assert entry["success"] is True
    assert entry["attempts"] == 2
    assert "timestamp_iso" in entry


# ---------------------------------------------------------------------------
# test_decision_log_entry_on_failure
# ---------------------------------------------------------------------------


def test_decision_log_entry_on_failure(tmp_path: Path) -> None:
    """Log entry is written on failure with success=false."""
    outcome = {
        "success": False,
        "mechanic_id": None,
        "attempts": 3,
        "reason": "too complex",
    }
    append_decision_log(tmp_path, "99", outcome)

    log_path = tmp_path / "operator-log.jsonl"
    line = log_path.read_text(encoding="utf-8").strip()
    entry = json.loads(line)

    assert entry["success"] is False
    assert entry["mechanic_id"] is None
    assert entry["tick_id"] == "99"


# ---------------------------------------------------------------------------
# test_decision_log_append_not_overwrite
# ---------------------------------------------------------------------------


def test_decision_log_append_not_overwrite(tmp_path: Path) -> None:
    """Existing entries are preserved when appending new entries."""
    existing = json.dumps({"event": "prior_event", "tick_id": "1"}) + "\n"
    log_path = tmp_path / "operator-log.jsonl"
    log_path.write_text(existing, encoding="utf-8")

    append_decision_log(tmp_path, "2", {"success": True, "mechanic_id": "walk", "attempts": 1})

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["event"] == "prior_event"
    second = json.loads(lines[1])
    assert second["event"] == "mechanic_decision"


# ---------------------------------------------------------------------------
# test_overlap_in_prompt
# ---------------------------------------------------------------------------


def test_overlap_in_prompt(tmp_path: Path) -> None:
    """overlap_report content appears in mechanic_author_prompt when provided."""
    prompt = mechanic_author_prompt(
        universe=tmp_path,
        yield_json='{"classified_action": {"verb": "pet"}}',
        overlap_report="test overlap report content",
    )
    assert "test overlap report content" in prompt
