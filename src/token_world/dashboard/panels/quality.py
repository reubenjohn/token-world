"""Quality scorecard panel.

Imports from ``token_world.quality`` directly (no subprocess).
Refreshes every 10 seconds — quality is a slower-moving signal than stats.
Degrades to placeholder cells when the universe has no ticks yet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from token_world.quality import QualityReport, score


def load_quality(universe_dir: Path, slug: str, last: int = 50) -> QualityReport:
    """Return a fresh QualityReport; swallows all exceptions."""
    try:
        return score(universe_dir, slug=slug, last=last)
    except Exception:  # noqa: BLE001
        return QualityReport(slug=slug)


def render_cells(report: QualityReport) -> list[dict[str, Any]]:
    """Return [{label, value, status}] for each dimension + verdict.

    Framework-agnostic; testable without a live NiceGUI server.
    """
    cells = []
    for dim in report.dimensions:
        cells.append(
            {
                "label": dim.name,
                "value": dim.detail,
                "status": dim.status,
            }
        )
    cells.append(
        {
            "label": "Verdict",
            "value": report.verdict,
            "status": _verdict_to_status(report.verdict),
        }
    )
    return cells


def _verdict_to_status(verdict: str) -> str:
    return {"HEALTHY": "OK", "DEGRADED": "WARN", "FAILED": "FAIL"}.get(verdict, "UNKNOWN")


_STATUS_COLOUR = {
    "OK": "bg-green-900 text-green-300",
    "WARN": "bg-yellow-900 text-yellow-300",
    "FAIL": "bg-red-900 text-red-300",
    "UNKNOWN": "bg-slate-800 text-slate-400",
}


def mount_quality_panel(universe_dir: Path, slug: str) -> Any:
    """Mount a horizontal quality strip above the stats strip.

    Each rubric dimension gets a coloured cell. Refreshes every 10s.
    Returns the container element for test introspection.
    """
    from nicegui import ui

    container = ui.row().classes("w-full gap-2 flex-wrap items-center p-2 rounded")

    def _rebuild() -> None:
        container.clear()
        report = load_quality(universe_dir, slug)
        with container:
            ui.label("Quality").classes("text-xs text-slate-400 font-semibold mr-2")
            for cell in render_cells(report):
                colour = _STATUS_COLOUR.get(cell["status"], _STATUS_COLOUR["UNKNOWN"])
                with ui.element("div").classes(f"px-2 py-1 rounded text-xs font-mono {colour}"):
                    ui.label(f"{cell['label']}: {cell['value']}")

    _rebuild()
    ui.timer(10.0, _rebuild)
    return container
