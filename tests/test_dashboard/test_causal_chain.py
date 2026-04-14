"""Tests for the causal chain panel (Plan 11-04)."""

from __future__ import annotations

from pathlib import Path

from token_world.dashboard.panels.causal_chain import (
    _hop_summary,
    report_to_view_model,
    run_trace,
)
from token_world.inspect.trace import TraceHop, TraceReport


def test_run_trace_db_missing(fake_universe: Path) -> None:
    """A universe without a DB yields ``db_missing=True`` without raising."""
    report = run_trace(fake_universe, slug="empty", node_id="alice", property="hp")
    assert report.db_missing is True
    assert report.hops == []


def test_report_to_view_model_shape() -> None:
    """View model flattens the dataclass and keeps the metadata flags."""
    report = TraceReport(
        slug="demo",
        node_id="alice",
        property="hp",
        hops=[
            TraceHop(
                tick_id="5",
                event_type="set",
                target_id="alice",
                property_name="hp",
                old_value=10,
                new_value=7,
                matched_mechanic_id="take_damage",
                timestamp_iso="2026-04-14T00:00:01Z",
                action_text="goblin attacks",
            )
        ],
        truncated=False,
        not_found=False,
        db_missing=False,
    )
    vm = report_to_view_model(report)
    assert vm["slug"] == "demo"
    assert vm["hop_count"] == 1
    assert vm["hops"][0]["tick_id"] == "5"
    assert vm["hops"][0]["matched_mechanic_id"] == "take_damage"
    assert vm["hops"][0]["new_value"] == 7


def test_hop_summary_formats_mutation() -> None:
    hop = {
        "tick_id": "7",
        "matched_mechanic_id": "heal",
        "property_name": "hp",
        "old_value": 7,
        "new_value": 10,
    }
    s = _hop_summary(hop)
    assert "tick 7" in s
    assert "heal" in s
    assert "hp" in s
    assert "7" in s and "10" in s


def test_hop_summary_missing_mechanic() -> None:
    """Hops without a matched mechanic render a dash placeholder."""
    hop = {
        "tick_id": "3",
        "matched_mechanic_id": None,
        "property_name": None,
        "old_value": None,
        "new_value": 42,
    }
    s = _hop_summary(hop)
    assert "-" in s


def test_report_to_view_model_not_found_passes_through() -> None:
    report = TraceReport(
        slug="demo",
        node_id="alice",
        property="nonexistent",
        not_found=True,
    )
    vm = report_to_view_model(report)
    assert vm["not_found"] is True
    assert vm["hops"] == []
