"""Stats strip header panel.

Reads ``token_world.inspect.stats.aggregate`` directly (no shell-out) and
renders a compact always-visible header:

    Tick #42 | 3.2 ticks/min | yield 12% | 7 mechanics | $0.0241

Updates on every poll (default every 2s via ``ui.timer`` wired by the
owning page). Degrades to placeholders when the universe has no ticks yet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from token_world.inspect.stats import StatsReport, aggregate


def load_stats(universe_dir: Path, slug: str) -> StatsReport:
    """Return a fresh :class:`StatsReport` for the universe.

    Swallows all exceptions and returns a zero-filled report so the
    dashboard never crashes on a missing / corrupt universe.
    """
    try:
        return aggregate(universe_dir, slug=slug)
    except Exception:  # noqa: BLE001 — dashboard must degrade gracefully.
        return StatsReport(slug=slug)


def render_cells(report: StatsReport) -> list[dict[str, Any]]:
    """Return a list of ``{label, value}`` dicts for the strip cells.

    The returned shape is intentionally framework-agnostic so tests can
    assert on it without a live NiceGUI server.
    """
    throughput = (
        f"{report.ticks_per_minute:.2f} ticks/min" if report.ticks_per_minute else "— ticks/min"
    )
    yield_pct = f"{report.yield_rate * 100:.1f}%" if report.tick_count else "—"
    cost = f"${report.cost_total_usd:.4f}"
    return [
        {"label": "Universe", "value": report.slug},
        {"label": "Ticks", "value": str(report.tick_count)},
        {"label": "Latest tick", "value": report.tick_id_max or "—"},
        {"label": "Throughput", "value": throughput},
        {"label": "Yield rate", "value": yield_pct},
        {"label": "Mechanics used", "value": str(report.distinct_mechanics_used)},
        {"label": "Novel mechanics", "value": str(report.novel_mechanic_introductions)},
        {"label": "Cost", "value": cost},
        {"label": "Backend", "value": report.cost_backend},
    ]


def mount_stats_strip(universe_dir: Path, slug: str) -> Any:
    """Mount the stats strip row into the current NiceGUI page.

    Returns the container element so the caller can hold a reference for
    reactive updates.
    """
    # Local import keeps module import-time cheap for tests that only
    # exercise :func:`render_cells`.
    from nicegui import ui

    container = ui.row().classes(
        "w-full gap-4 px-4 py-3 bg-slate-800 text-slate-100 rounded-lg shadow-sm items-center"
    )

    def _rebuild() -> None:
        container.clear()
        report = load_stats(universe_dir, slug)
        cells = render_cells(report)
        with container:
            for cell in cells:
                with ui.column().classes("items-start gap-0"):
                    ui.label(cell["label"]).classes(
                        "text-xs uppercase tracking-wide text-slate-400"
                    )
                    ui.label(cell["value"]).classes("text-sm font-mono")

    _rebuild()
    # Re-read every 2s. NiceGUI ui.timer triggers on the page's reactive loop.
    ui.timer(2.0, _rebuild)
    return container
