"""Dashboard mechanics registry panel (SC-2b).

Renders a table of all mechanics with First authored and Last invoked columns.
Refreshes on a 10-second timer — registry changes less frequently than ticks.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from token_world.inspect.mechanics import MechanicsReport, aggregate


def load_mechanics_history(universe_dir: Path, slug: str) -> MechanicsReport:
    """Return a :class:`MechanicsReport` with git history populated.

    Calls ``inspect.mechanics.aggregate`` directly (no subprocess) with
    ``history=True`` so ``first_authored_commit`` and
    ``first_authored_timestamp`` are populated.

    Never raises — returns an empty report on any error so the dashboard
    degrades gracefully.
    """
    try:
        return aggregate(universe_dir, slug=slug, history=True)
    except Exception:  # noqa: BLE001
        return MechanicsReport(slug=slug)


def render_mechanics_rows(report: MechanicsReport) -> list[dict[str, Any]]:
    """Return a list of row dicts suitable for a NiceGUI table.

    Each dict has keys: ``id``, ``author``, ``call_count``,
    ``last_invoked_tick``, ``first_authored_commit``,
    ``first_authored_timestamp``.

    Pure function — no NiceGUI imports; fully testable in isolation.
    """
    rows: list[dict[str, Any]] = []
    for m in report.mechanics:
        d = asdict(m)
        rows.append(
            {
                "id": d.get("id", ""),
                "author": d.get("author", ""),
                "call_count": d.get("call_count", 0),
                "last_invoked_tick": d.get("last_invoked_tick") or "-",
                "first_authored_commit": (d.get("first_authored_commit") or "")[:8] or "-",
                "first_authored_timestamp": (d.get("first_authored_timestamp") or "")[:10] or "-",
            }
        )
    return rows


def mount_mechanics_panel(universe_dir: Path, slug: str) -> Any:
    """Mount a NiceGUI mechanics registry table.

    Columns: ID, Author, Calls, Last tick, First authored (date + commit).
    Refreshes every 10 seconds.

    Returns the container element for test introspection.
    """
    from nicegui import ui

    columns = [
        {"name": "id", "label": "ID", "field": "id", "align": "left", "sortable": True},
        {"name": "author", "label": "Author", "field": "author", "align": "left"},
        {
            "name": "call_count",
            "label": "Calls",
            "field": "call_count",
            "align": "right",
            "sortable": True,
        },
        {
            "name": "last_invoked_tick",
            "label": "Last tick",
            "field": "last_invoked_tick",
            "align": "right",
        },
        {
            "name": "first_authored_timestamp",
            "label": "First authored",
            "field": "first_authored_timestamp",
            "align": "left",
        },
        {
            "name": "first_authored_commit",
            "label": "Commit",
            "field": "first_authored_commit",
            "align": "left",
        },
    ]

    container = ui.column().classes("w-full gap-1")

    def _rebuild() -> None:
        container.clear()
        report = load_mechanics_history(universe_dir, slug)
        rows = render_mechanics_rows(report)
        with container:
            ui.label(f"Mechanics registry ({len(rows)} total)").classes(
                "text-sm text-slate-400 font-semibold"
            )
            if not rows:
                ui.label("No mechanics found.").classes("text-xs text-slate-500 font-mono")
            else:
                tbl = ui.table(columns=columns, rows=rows, row_key="id")
                tbl.classes("w-full text-xs font-mono bg-slate-900 text-slate-200")
                tbl.props("dense dark flat")

    _rebuild()
    ui.timer(10.0, _rebuild)
    return container
