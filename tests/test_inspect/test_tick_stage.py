"""Tests for load_stage_data() and render_stage_* in tick.py (SC-1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from token_world.inspect.tick import (
    StageNotFoundError,
    load_stage_data,
    render_stage_json,
    render_stage_table,
)


def _make_classification_dir(base: Path) -> Path:
    """Create a synthetic classification diagnostics directory."""
    d = base / "classification"
    d.mkdir(parents=True)
    (d / "prompt.txt").write_text("You are a classifier. Action: open chest", encoding="utf-8")
    (d / "response.txt").write_text('{"verb": "open", "subject": "player"}', encoding="utf-8")
    (d / "parsed.json").write_text(
        json.dumps({"verb": "open", "subject": "player", "confidence": 0.95}), encoding="utf-8"
    )
    return d


def _make_observation_dir(base: Path) -> Path:
    """Create a synthetic observation diagnostics directory."""
    d = base / "observation"
    d.mkdir(parents=True)
    (d / "prompt.txt").write_text("Describe the result of opening the chest.", encoding="utf-8")
    (d / "response.txt").write_text("The chest creaks open.", encoding="utf-8")
    (d / "parsed.json").write_text(
        json.dumps({"observation": "The chest creaks open.", "success": True}), encoding="utf-8"
    )
    return d


def _make_matching_file(base: Path) -> Path:
    """Create a synthetic matching.json file."""
    p = base / "matching.json"
    p.write_text(json.dumps([{"mechanic_id": "open_chest", "score": 0.9}]), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# test_classification_stage
# ---------------------------------------------------------------------------


def test_classification_stage(tmp_path: Path) -> None:
    tick_dir = tmp_path / "diagnostics" / "tick_42"
    tick_dir.mkdir(parents=True)
    _make_classification_dir(tick_dir)

    data = load_stage_data(tmp_path, "42", "classification")

    assert data["stage"] == "classification"
    assert isinstance(data["parsed"], dict)
    assert data["parsed"]["verb"] == "open"
    out = render_stage_table(data, raw=False)
    assert "classification" in out
    assert "open" in out


# ---------------------------------------------------------------------------
# test_classification_raw
# ---------------------------------------------------------------------------


def test_classification_raw(tmp_path: Path) -> None:
    tick_dir = tmp_path / "diagnostics" / "tick_42"
    tick_dir.mkdir(parents=True)
    _make_classification_dir(tick_dir)

    data = load_stage_data(tmp_path, "42", "classification")
    out = render_stage_table(data, raw=True)

    assert "prompt" in out.lower()
    assert "You are a classifier" in out
    assert "response" in out.lower()


# ---------------------------------------------------------------------------
# test_matcher_stage
# ---------------------------------------------------------------------------


def test_matcher_stage(tmp_path: Path) -> None:
    tick_dir = tmp_path / "diagnostics" / "tick_7"
    tick_dir.mkdir(parents=True)
    _make_matching_file(tick_dir)

    data = load_stage_data(tmp_path, "7", "matcher")

    assert data["stage"] == "matcher"
    assert isinstance(data["candidates"], list)
    assert data["candidates"][0]["mechanic_id"] == "open_chest"
    out = render_stage_table(data, raw=False)
    assert "matcher" in out
    assert "open_chest" in out


# ---------------------------------------------------------------------------
# test_observer_stage
# ---------------------------------------------------------------------------


def test_observer_stage(tmp_path: Path) -> None:
    tick_dir = tmp_path / "diagnostics" / "tick_5"
    tick_dir.mkdir(parents=True)
    _make_observation_dir(tick_dir)

    data = load_stage_data(tmp_path, "5", "observer")

    assert data["stage"] == "observer"
    assert isinstance(data["parsed"], dict)
    out = render_stage_table(data, raw=False)
    assert "observer" in out


# ---------------------------------------------------------------------------
# test_stage_not_found
# ---------------------------------------------------------------------------


def test_stage_not_found(tmp_path: Path) -> None:
    tick_dir = tmp_path / "diagnostics" / "tick_99"
    tick_dir.mkdir(parents=True)
    # No classification dir created

    with pytest.raises(StageNotFoundError):
        load_stage_data(tmp_path, "99", "classification")


def test_matcher_not_found(tmp_path: Path) -> None:
    tick_dir = tmp_path / "diagnostics" / "tick_99"
    tick_dir.mkdir(parents=True)
    # No matching.json created

    with pytest.raises(StageNotFoundError):
        load_stage_data(tmp_path, "99", "matcher")


def test_unknown_stage_raises_value_error(tmp_path: Path) -> None:
    tick_dir = tmp_path / "diagnostics" / "tick_1"
    tick_dir.mkdir(parents=True)

    with pytest.raises(ValueError, match="Unknown stage"):
        load_stage_data(tmp_path, "1", "bogus")


# ---------------------------------------------------------------------------
# test_format_json_respects_stage
# ---------------------------------------------------------------------------


def test_format_json_respects_stage(tmp_path: Path) -> None:
    tick_dir = tmp_path / "diagnostics" / "tick_3"
    tick_dir.mkdir(parents=True)
    _make_classification_dir(tick_dir)

    data = load_stage_data(tmp_path, "3", "classification")
    out = render_stage_json(data)
    payload = json.loads(out)

    # Should contain only stage data, not full tick
    assert payload["stage"] == "classification"
    assert "parsed" in payload
    # Should NOT have top-level tick keys like tick_id, action_text
    assert "tick_id" not in payload
    assert "action_text" not in payload
