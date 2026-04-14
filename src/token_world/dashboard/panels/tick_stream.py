"""Live tick stream panel (Plan 11-02).

Polls ``<universe>/tick_summaries/ticks/`` every 2s and renders a
newest-first card list. Each card shows

    tick_id | action_text (trunc) | mechanic / yield / refuse | observation (trunc)

Click a card to expand the full JSON payload beneath it.

Design:

- We reuse :func:`token_world.inspect._shared.iter_tick_files` + the same
  JSON reader so the dashboard never parses tick files differently from
  the CLI.
- We avoid re-reading every tick on each poll — the directory's mtime
  gates whether we refresh, and even then we only re-read files with
  changed mtime.
- DOM cap: we show the most recent 50 ticks. The full history is still
  on disk; the dashboard is a window, not an archive.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from token_world.inspect._shared import iter_tick_files, read_json_file, tick_id_sort_key

MAX_CARDS = 50


def load_recent_tick_cards(
    universe_dir: Path, *, max_cards: int = MAX_CARDS
) -> list[dict[str, Any]]:
    """Return a newest-first list of compact card dicts for the tick stream.

    Each dict has keys: ``tick_id, action_text, mechanic, observation,
    status, raw``. ``raw`` is the full tick payload (so the expand drawer
    can show it without re-reading the disk).
    """
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    files = iter_tick_files(ticks_dir)
    # Keep the last N files; oldest-first inside the window.
    window = files[-max_cards:] if max_cards and len(files) > max_cards else files
    cards: list[dict[str, Any]] = []
    for path in window:
        data = read_json_file(path)
        if data is None:
            continue
        cards.append(build_card(data))
    # Newest-first display.
    cards.sort(key=lambda c: tick_id_sort_key(str(c["tick_id"])), reverse=True)
    return cards


def build_card(tick: dict[str, Any]) -> dict[str, Any]:
    """Compact a tick payload into the card dict.

    Isolated from :func:`load_recent_tick_cards` so unit tests can assert on
    the shape without any filesystem.
    """
    action = _truncate(tick.get("action_text"), max_len=80)
    mechanic = tick.get("matched_mechanic_id")
    observation = _truncate(tick.get("observation_text"), max_len=120)

    if tick.get("yielded"):
        status = "yield"
        status_detail = "to operator"
    elif tick.get("refused"):
        status = "refuse"
        status_detail = tick.get("refusal_reason") or "(no reason)"
    elif mechanic:
        status = "exec"
        status_detail = str(mechanic)
    else:
        status = "unmatched"
        status_detail = "(no mechanic)"

    return {
        "tick_id": str(tick.get("tick_id") or "?"),
        "timestamp_iso": str(tick.get("timestamp_iso") or ""),
        "action_text": action,
        "mechanic": mechanic,
        "status": status,
        "status_detail": status_detail,
        "observation": observation,
        "raw": tick,
    }


def _truncate(text: str | None, *, max_len: int) -> str:
    if text is None:
        return ""
    flat = " ".join(text.split())
    if len(flat) <= max_len:
        return flat
    return flat[: max_len - 3] + "..."


def mount_tick_stream_panel(universe_dir: Path, slug: str) -> Any:
    """Mount the live tick stream into the current NiceGUI page."""
    from nicegui import ui

    outer = ui.column().classes("w-full gap-1 max-h-[70vh] overflow-auto")
    status_label = ui.label("").classes("text-xs text-slate-400 px-1")

    # We hold the last seen set of tick_ids so we only rebuild on change.
    state: dict[str, Any] = {"last_ids": tuple[str, ...]()}

    def _rebuild() -> None:
        cards = load_recent_tick_cards(universe_dir)
        ids_tuple = tuple(c["tick_id"] for c in cards)
        if ids_tuple == state["last_ids"] and outer.default_slot.children:
            return  # no change + already rendered once
        state["last_ids"] = ids_tuple
        outer.clear()
        if not cards:
            with outer, ui.card().classes("w-full bg-slate-900 text-slate-400"):
                ui.label("No ticks written yet.").classes("text-sm")
                ui.label(
                    "The stream will populate as run_unattended.py writes to tick_summaries/ticks/."
                ).classes("text-xs")
            status_label.text = f"{slug}: 0 ticks"
            return
        status_label.text = f"{slug}: {len(cards)} recent ticks (newest first)"
        with outer:
            for card in cards:
                _render_card(ui, card)

    _rebuild()
    ui.timer(2.0, _rebuild)
    return outer


def _render_card(ui: Any, card: dict[str, Any]) -> None:
    """Render a single tick card with a click-to-expand JSON body."""
    status = card["status"]
    palette = {
        "yield": "bg-amber-900 border-amber-700",
        "refuse": "bg-rose-900 border-rose-700",
        "exec": "bg-slate-800 border-slate-700",
        "unmatched": "bg-slate-900 border-slate-800",
    }.get(status, "bg-slate-800 border-slate-700")

    header = f"tick {card['tick_id']}  ·  {status}  ·  {card['status_detail']}"
    with (
        ui.expansion(header).classes(f"w-full rounded-md border text-slate-100 {palette}"),
        ui.column().classes("gap-1 px-2 py-2"),
    ):
        if card["timestamp_iso"]:
            ui.label(card["timestamp_iso"]).classes("text-xs text-slate-400 font-mono")
        if card["action_text"]:
            ui.label(f"action: {card['action_text']}").classes("text-sm")
        if card["mechanic"]:
            ui.label(f"mechanic: {card['mechanic']}").classes("text-sm font-mono")
        if card["observation"]:
            ui.label(f"obs: {card['observation']}").classes(
                "text-sm text-slate-300 whitespace-normal"
            )
        ui.separator()
        ui.label("Full tick JSON:").classes("text-xs text-slate-400")
        pretty = json.dumps(card["raw"], indent=2, sort_keys=True)
        ui.code(pretty, language="json").classes("w-full text-xs max-h-[320px] overflow-auto")
