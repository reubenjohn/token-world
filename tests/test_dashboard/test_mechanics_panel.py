"""Tests for the dashboard mechanics registry panel (SC-2b)."""

from __future__ import annotations

from token_world.dashboard.panels.mechanics_panel import render_mechanics_rows
from token_world.inspect.mechanics import MechanicRow, MechanicsReport


def _make_report(*rows: MechanicRow) -> MechanicsReport:
    return MechanicsReport(slug="test", mechanics=list(rows))


def test_render_mechanics_rows_empty() -> None:
    rows = render_mechanics_rows(_make_report())
    assert rows == []


def test_render_mechanics_rows_basic() -> None:
    report = _make_report(
        MechanicRow(
            id="pet_cat",
            description="Pet a cat",
            voluntary=True,
            author="operator",
            call_count=5,
            last_invoked_tick="42",
            first_authored_commit="abcdef1234567890",
            first_authored_timestamp="2024-03-01T10:00:00+00:00",
        )
    )
    rows = render_mechanics_rows(report)
    assert len(rows) == 1
    r = rows[0]
    assert r["id"] == "pet_cat"
    assert r["author"] == "operator"
    assert r["call_count"] == 5
    assert r["last_invoked_tick"] == "42"
    # First authored columns present
    assert "first_authored_commit" in r
    assert "first_authored_timestamp" in r


def test_render_mechanics_rows_first_authored_columns_present() -> None:
    """Assert 'First authored' and 'Last invoked' columns are in every row."""
    report = _make_report(
        MechanicRow(
            id="walk",
            description="Walk somewhere",
            voluntary=True,
            author="seed",
            call_count=3,
            last_invoked_tick="7",
            first_authored_commit="deadbeef00000000",
            first_authored_timestamp="2024-01-15T08:30:00+00:00",
        )
    )
    rows = render_mechanics_rows(report)
    assert len(rows) == 1
    r = rows[0]
    # Both required columns present
    assert "first_authored_timestamp" in r
    assert "last_invoked_tick" in r
    # Commit truncated to 8 chars
    assert r["first_authored_commit"] == "deadbeef"
    # Timestamp truncated to date
    assert r["first_authored_timestamp"] == "2024-01-15"


def test_render_mechanics_rows_none_history_fields() -> None:
    """Rows with no git history degrade to '-' placeholders."""
    report = _make_report(
        MechanicRow(
            id="jump",
            description="Jump",
            voluntary=True,
            author="seed",
            call_count=0,
            last_invoked_tick=None,
            first_authored_commit=None,
            first_authored_timestamp=None,
        )
    )
    rows = render_mechanics_rows(report)
    r = rows[0]
    assert r["last_invoked_tick"] == "-"
    assert r["first_authored_commit"] == "-"
    assert r["first_authored_timestamp"] == "-"


def test_render_mechanics_rows_multiple() -> None:
    report = _make_report(
        MechanicRow(id="a", description="A", voluntary=True, call_count=1),
        MechanicRow(id="b", description="B", voluntary=False, call_count=10),
    )
    rows = render_mechanics_rows(report)
    assert len(rows) == 2
    assert rows[0]["id"] == "a"
    assert rows[1]["id"] == "b"
