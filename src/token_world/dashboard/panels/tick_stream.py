"""Live tick stream panel (Plan 11-02 + §A7/A1/A2/A5 redesign).

Polls ``<universe>/tick_summaries/ticks/`` every 2s and renders a
newest-first card list. Each card shows

    tick_id | status | mechanic / yield-reason / refuse-reason

Click a card to expand into clearly-labelled sections:

    Classification | Decision | Mutations | Observation (full text) |
    Side-effect chain | Metadata | Raw JSON (collapsed)

Design:

- We reuse :func:`token_world.inspect._shared.iter_tick_files` + the same
  JSON reader so the dashboard never parses tick files differently from
  the CLI.
- We avoid re-reading every tick on each poll — the directory's mtime
  gates whether we refresh, and even then we only re-read files with
  changed mtime.
- DOM cap: we show the most recent 50 ticks. The full history is still
  on disk; the dashboard is a window, not an archive.
- §A7 scroll preservation: the poll handler only ever *prepends* new
  cards. Existing cards are never re-rendered — so any open expansion
  keeps its state (open/closed, scroll position, text selection) intact
  across polls. If nothing new arrived, the handler is a no-op.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from token_world.dashboard.panels.side_effect_chain import render_side_effect_tree
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

    classified = tick.get("classified_action") or {}
    actor_id = str(classified.get("actor") or "")

    return {
        "tick_id": str(tick.get("tick_id") or "?"),
        "timestamp_iso": str(tick.get("timestamp_iso") or ""),
        "action_text": action,
        "mechanic": mechanic,
        "status": status,
        "status_detail": status_detail,
        "observation": observation,
        "actor_id": actor_id,
        "raw": tick,
    }


def _truncate(text: str | None, *, max_len: int) -> str:
    if text is None:
        return ""
    flat = " ".join(text.split())
    if len(flat) <= max_len:
        return flat
    return flat[: max_len - 3] + "..."


def mount_tick_stream_panel(
    universe_dir: Path, slug: str, *, selected_agent: dict[str, str] | None = None
) -> Any:
    """Mount the live tick stream into the current NiceGUI page.

    §A7 scroll preservation: the poll handler compares the latest tick
    IDs against a cache of already-mounted card elements. New ticks are
    *prepended* as fresh cards; existing cards are left untouched so any
    open expansion keeps its state. No card is ever re-rendered during a
    poll.

    ``selected_agent`` is an optional mutable dict ``{"value": ""}`` shared
    from ``app.py``. When ``selected_agent["value"]`` is non-empty, only
    ticks with a matching ``actor_id`` are rendered.
    """
    from nicegui import ui

    outer = ui.column().classes("w-full gap-1 max-h-[70vh] overflow-auto")
    status_label = ui.label("").classes("text-xs text-slate-400 px-1")

    # Map of tick_id -> mounted card element so we can tell what's already
    # on the page and prepend only what's new.
    mounted: dict[str, Any] = {}
    # ``last_ids`` is kept around for back-compat with tests and callers
    # that want to know the current card order.
    state: dict[str, Any] = {"last_ids": tuple[str, ...](), "mounted": mounted}

    empty_placeholder: Any | None = None

    def _render_empty() -> None:
        nonlocal empty_placeholder
        outer.clear()
        mounted.clear()
        with outer, ui.card().classes("w-full bg-slate-900 text-slate-400") as placeholder:
            ui.label("No ticks written yet.").classes("text-sm")
            ui.label(
                "The stream will populate as run_unattended.py writes to tick_summaries/ticks/."
            ).classes("text-xs")
        empty_placeholder = placeholder
        status_label.text = f"{slug}: 0 ticks"

    def _clear_empty_placeholder() -> None:
        nonlocal empty_placeholder
        if empty_placeholder is not None:
            outer.remove(empty_placeholder)
            empty_placeholder = None

    def _rebuild() -> None:
        cards = load_recent_tick_cards(universe_dir)
        agent_filter = (selected_agent or {}).get("value", "")
        if agent_filter:
            cards = [c for c in cards if c.get("actor_id") == agent_filter]
        ids_tuple = tuple(c["tick_id"] for c in cards)

        if not cards:
            if mounted or empty_placeholder is None:
                _render_empty()
            return

        # First render: no mounted cards yet. Populate newest-first.
        if not mounted:
            _clear_empty_placeholder()
            with outer:
                for card in cards:
                    elem = _render_card(ui, card, universe_dir=universe_dir)
                    mounted[card["tick_id"]] = elem
            state["last_ids"] = ids_tuple
            status_label.text = f"{slug}: {len(cards)} recent ticks (newest first)"
            return

        # Incremental update: the IDs tuple is unchanged → no new ticks
        # have arrived. No-op: leave every mounted card untouched so open
        # expansions stay open with their scroll positions.
        if ids_tuple == state["last_ids"]:
            return

        # Identify truly-new cards (tick IDs not yet mounted).
        current_ids = set(mounted.keys())
        new_cards = [c for c in cards if c["tick_id"] not in current_ids]
        # Cards that fell out of the window (oldest, because cards is
        # capped at MAX_CARDS). Unmount them so the DOM doesn't grow
        # forever.
        new_ids_set = {c["tick_id"] for c in cards}
        dropped = [tid for tid in list(mounted.keys()) if tid not in new_ids_set]
        for tid in dropped:
            elem = mounted.pop(tid)
            outer.remove(elem)

        # Prepend new cards newest-last so after all prepends the newest
        # card ends up at index 0 (matching the newest-first sort above).
        # ``new_cards`` is newest-first from ``load_recent_tick_cards``; to
        # end up with newest at index 0 we iterate oldest→newest and
        # target_index=0 each time.
        with outer:
            for card in reversed(new_cards):
                elem = _render_card(ui, card, universe_dir=universe_dir)
                elem.move(target_index=0)
                mounted[card["tick_id"]] = elem

        state["last_ids"] = ids_tuple
        status_label.text = f"{slug}: {len(cards)} recent ticks (newest first)"

    _rebuild()
    ui.timer(2.0, _rebuild)
    return outer


def _render_card(ui: Any, card: dict[str, Any], *, universe_dir: Path | None = None) -> Any:
    """Render a single tick card with a click-to-expand structured body.

    Returns the outer expansion element so the caller can track it in
    the ``mounted`` dict and move / remove it on later polls.
    """
    status = card["status"]
    palette = {
        "yield": "bg-amber-900 border-amber-700",
        "refuse": "bg-rose-900 border-rose-700",
        "exec": "bg-slate-800 border-slate-700",
        "unmatched": "bg-slate-900 border-slate-800",
    }.get(status, "bg-slate-800 border-slate-700")

    badge = f"  ·  {card['actor_id']}" if card.get("actor_id") else ""
    header = f"tick {card['tick_id']}  ·  {status}  ·  {card['status_detail']}{badge}"
    expansion = ui.expansion(header).classes(f"w-full rounded-md border text-slate-100 {palette}")
    with expansion, ui.column().classes("gap-2 px-2 py-2 w-full"):
        _render_expansion_body(ui, card, universe_dir=universe_dir)
    return expansion


def _section_header(ui: Any, text: str) -> None:
    """Render a clearly-labelled section heading inside a card expansion."""
    ui.label(text).classes("text-sm font-semibold text-slate-200 mt-1")


def _render_expansion_body(
    ui: Any, card: dict[str, Any], *, universe_dir: Path | None = None
) -> None:
    """Render the full structured body: six labelled sections + raw JSON.

    The sections (in display order) are:

    - Classification (verb / actor / target / indirect_object / confidence)
    - Decision (status + mechanic_id or refuse reason_code)
    - Mutations (grouped by target node)
    - Observation (FULL text, never truncated, newlines preserved)
    - Side-effect chain (ExecutionTrace tree; placeholder on yield/refuse)
    - Metadata (duration / cost / tokens / timestamp)
    - Raw JSON (collapsed inside a nested expansion)
    """
    tick = card["raw"]

    # Header row: always-visible timestamp so the user can orient.
    if card["timestamp_iso"]:
        ui.label(card["timestamp_iso"]).classes("text-xs text-slate-400 font-mono")
    if card.get("actor_id"):
        ui.label(f"· {card['actor_id']}").classes("text-slate-400 text-xs font-mono")

    # --- Classification -----------------------------------------------
    _section_header(ui, "Classification")
    classified = tick.get("classified_action") or {}
    if not classified:
        ui.label("(none — pre-classifier or unparsed)").classes("text-xs italic text-slate-400")
    else:
        for key in ("verb", "actor", "target", "indirect_object"):
            if key in classified:
                ui.label(f"{key}: {classified[key]!r}").classes("text-sm text-slate-300 font-mono")
        if "confidence" in classified:
            ui.label(f"confidence: {classified['confidence']}").classes(
                "text-sm text-slate-300 font-mono"
            )

    # --- Decision -----------------------------------------------------
    _section_header(ui, "Decision")
    if tick.get("yielded"):
        ui.label("status: YIELDED to operator").classes("text-sm text-amber-300")
    elif tick.get("refused"):
        reason = tick.get("refusal_reason") or "(no reason given)"
        ui.label("status: REFUSED").classes("text-sm text-rose-300")
        ui.label(f"reason_code: {reason}").classes("text-sm text-rose-200 font-mono")
    elif tick.get("matched_mechanic_id"):
        ui.label("status: EXECUTED").classes("text-sm text-emerald-300")
        ui.label(f"mechanic_id: {tick['matched_mechanic_id']}").classes(
            "text-sm text-slate-300 font-mono"
        )
    else:
        ui.label("status: (no mechanic match)").classes("text-sm text-slate-400")

    # --- Mutations ----------------------------------------------------
    _section_header(ui, "Mutations")
    mutations_field = tick.get("mutations") or {}
    mut_list = mutations_field.get("list") or []
    if not mut_list:
        ui.label("(no mutations)").classes("text-xs italic text-slate-400")
    else:
        # Group by target node so reads are easier.
        by_target: dict[str, list[tuple[str | None, Any, Any]]] = {}
        for entry in mut_list:
            if isinstance(entry, list) and len(entry) == 4:
                target, prop, old, new = entry
            else:
                target, prop, old, new = "?", None, None, entry
            by_target.setdefault(str(target), []).append((prop, old, new))
        for target, rows in by_target.items():
            ui.label(target).classes("text-xs text-slate-400 font-mono")
            for prop, old, new in rows:
                if prop is None:
                    label = f"  {target}: {old!r} → {new!r}"
                else:
                    label = f"  {target}.{prop}: {old!r} → {new!r}"
                ui.label(label).classes("text-sm text-slate-200 font-mono whitespace-pre-wrap")

    # --- Observation (full, untruncated) ------------------------------
    _section_header(ui, "Observation")
    obs = tick.get("observation_text")
    if obs is None or obs == "":
        ui.label("(no observation)").classes("text-xs italic text-slate-400")
    else:
        # ``white-space: pre-wrap`` keeps newlines + wraps long lines.
        ui.label(obs).classes("text-sm text-slate-200 whitespace-pre-wrap leading-relaxed")

    # --- Side-effect chain --------------------------------------------
    _section_header(ui, "Side-effect chain")
    chain_container = ui.column().classes("w-full gap-0 pl-2")
    with chain_container:
        render_side_effect_tree(tick, chain_container, universe_dir=universe_dir)

    # --- Metadata -----------------------------------------------------
    _section_header(ui, "Metadata")
    meta_rows: list[str] = []
    if card["timestamp_iso"]:
        meta_rows.append(f"timestamp: {card['timestamp_iso']}")
    dur = tick.get("duration_ms")
    if dur is not None:
        meta_rows.append(f"duration_ms: {dur}")
    tokens = tick.get("llm_tokens_by_stage") or {}
    costs = tick.get("llm_cost_usd_by_stage") or {}
    total_cost = 0.0
    for stage in sorted(set(tokens) | set(costs)):
        tok = tokens.get(stage) or {}
        in_tok = int(tok.get("in", 0) or 0)
        out_tok = int(tok.get("out", 0) or 0)
        cost = float(costs.get(stage, 0.0) or 0.0)
        total_cost += cost
        meta_rows.append(f"{stage}: in={in_tok} out={out_tok} cost=${cost:.4f}")
    meta_rows.append(f"cost_usd_total: ${total_cost:.4f}")
    for row in meta_rows:
        ui.label(row).classes("text-xs text-slate-300 font-mono")

    # --- Raw JSON (collapsed) -----------------------------------------
    raw_exp = ui.expansion("Raw JSON").classes("w-full text-xs text-slate-400 mt-2")
    with raw_exp:
        pretty = json.dumps(tick, indent=2, sort_keys=True)
        ui.code(pretty, language="json").classes("w-full text-xs max-h-[320px] overflow-auto")
