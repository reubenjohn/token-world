"""Tests for the live tick stream panel (Plan 11-02)."""

from __future__ import annotations

from pathlib import Path

from token_world.dashboard.panels.tick_stream import (
    build_card,
    load_recent_tick_cards,
)


def test_build_card_exec_status() -> None:
    """A mechanic-matched tick yields ``exec`` status with mechanic_id detail."""
    tick = {
        "tick_id": "42",
        "timestamp_iso": "2026-04-14T00:00:05Z",
        "action_text": "open the chest",
        "matched_mechanic_id": "open_container",
        "observation_text": "The lid creaks.",
    }
    card = build_card(tick)
    assert card["tick_id"] == "42"
    assert card["status"] == "exec"
    assert card["status_detail"] == "open_container"
    assert card["action_text"] == "open the chest"
    assert card["observation"] == "The lid creaks."
    assert card["mechanic"] == "open_container"


def test_build_card_yield_status() -> None:
    tick = {
        "tick_id": "43",
        "yielded": True,
        "action_text": "summon a demigod",
    }
    card = build_card(tick)
    assert card["status"] == "yield"
    assert "operator" in card["status_detail"]


def test_build_card_refuse_status_with_reason() -> None:
    tick = {
        "tick_id": "44",
        "refused": True,
        "refusal_reason": "conservation_violation: hp cannot exceed max",
    }
    card = build_card(tick)
    assert card["status"] == "refuse"
    assert "conservation" in card["status_detail"]


def test_build_card_truncates_long_text() -> None:
    long_action = "a " * 200  # 400 chars
    long_obs = "b " * 200
    tick = {
        "tick_id": "45",
        "action_text": long_action,
        "observation_text": long_obs,
        "matched_mechanic_id": "noop",
    }
    card = build_card(tick)
    assert len(card["action_text"]) <= 80
    assert card["action_text"].endswith("...")
    assert len(card["observation"]) <= 120
    assert card["observation"].endswith("...")


def test_load_recent_tick_cards_empty(fake_universe: Path) -> None:
    """A universe with no ticks returns an empty list."""
    assert load_recent_tick_cards(fake_universe) == []


def test_load_recent_tick_cards_newest_first(fake_universe: Path, write_tick_dashboard) -> None:
    ticks_dir = fake_universe / "tick_summaries" / "ticks"
    write_tick_dashboard(ticks_dir, "1", action_text="one")
    write_tick_dashboard(ticks_dir, "2", action_text="two")
    write_tick_dashboard(ticks_dir, "10", action_text="ten")

    cards = load_recent_tick_cards(fake_universe)
    # Numeric sort — "10" is newer than "2".
    assert [c["tick_id"] for c in cards] == ["10", "2", "1"]
    assert cards[0]["action_text"] == "ten"


def test_load_recent_tick_cards_respects_max(fake_universe: Path, write_tick_dashboard) -> None:
    ticks_dir = fake_universe / "tick_summaries" / "ticks"
    for i in range(1, 15):
        write_tick_dashboard(ticks_dir, str(i), action_text=f"tick {i}")
    cards = load_recent_tick_cards(fake_universe, max_cards=5)
    assert len(cards) == 5
    # Highest-id ticks survive, newest-first.
    assert [c["tick_id"] for c in cards] == ["14", "13", "12", "11", "10"]
