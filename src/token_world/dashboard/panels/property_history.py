"""Property history viewer panel (Plan 11-04 + §A5a rename).

# Renamed from ``panels/causal_chain.py`` on 2026-04-14 (§A5a handoff).
# The dashboard UI label is now "Property history". The ``token-world
# trace`` CLI intentionally keeps its name — same underlying walker,
# different surface. The sibling panel ``side_effect_chain.py`` shows
# the forward, within-tick side-effect tree; this one walks *backward*
# in time through mutations on a single property.

Input: a node id + a property name. Output: a vertical tree of hops
showing which tick / mechanic / action mutated the property, oldest first.

Reuses :func:`token_world.inspect.trace.trace` directly so the dashboard
and the ``token-world trace`` CLI return the exact same data.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from token_world.inspect.trace import TraceReport, trace


def run_trace(
    universe_dir: Path, *, slug: str, node_id: str, property: str, hop_limit: int = 10
) -> TraceReport:
    """Wrapper around :func:`token_world.inspect.trace.trace` with safe defaults."""
    return trace(universe_dir, slug=slug, node_id=node_id, property=property, hop_limit=hop_limit)


def report_to_view_model(report: TraceReport) -> dict[str, Any]:
    """Flatten a :class:`TraceReport` into a UI-agnostic dict.

    Returns a shape the panel can bind to without touching dataclasses
    directly — easier to test + easier to shape-shift later.
    """
    return {
        "slug": report.slug,
        "node_id": report.node_id,
        "property": report.property,
        "truncated": report.truncated,
        "not_found": report.not_found,
        "db_missing": report.db_missing,
        "hop_count": len(report.hops),
        "hops": [asdict(hop) for hop in report.hops],
    }


def _hop_summary(hop: dict[str, Any]) -> str:
    """One-line summary used as the expansion header for a hop."""
    mech = hop.get("matched_mechanic_id") or "-"
    old = hop.get("old_value")
    new = hop.get("new_value")
    return (
        f"tick {hop['tick_id']}  ·  {mech}  ·  "
        f"{hop.get('property_name') or '-'} : {old!r} → {new!r}"
    )


def mount_property_history_panel(universe_dir: Path, slug: str) -> Any:
    """Mount the property-history input + result tree.

    Renamed from ``mount_causal_chain_panel`` (§A5a). The walker direction
    is *backward in time* — given a ``(node, property)`` pair, trace every
    tick that mutated it, oldest hop first.
    """
    from nicegui import ui

    container = ui.column().classes("w-full gap-2")
    state: dict[str, Any] = {"view_model": None}

    with container:
        with ui.row().classes("w-full gap-2 items-end"):
            node_input = ui.input("Node id", placeholder="e.g. alice").classes("flex-1")
            prop_input = ui.input("Property", placeholder="e.g. hp").classes("flex-1")
            hop_input = ui.number("Hops", value=10, min=1, max=50).classes("w-24")
            ui.button("Trace", on_click=lambda: _on_trace()).props("color=primary")

        status_label = ui.label("Enter a node + property then click Trace.").classes(
            "text-xs text-slate-400"
        )
        results_col = ui.column().classes("w-full gap-2")

    def _on_trace() -> None:
        node = (node_input.value or "").strip()
        prop = (prop_input.value or "").strip()
        hops = int(hop_input.value or 10)
        if not node or not prop:
            status_label.text = "Both node id and property are required."
            return
        report = run_trace(universe_dir, slug=slug, node_id=node, property=prop, hop_limit=hops)
        vm = report_to_view_model(report)
        state["view_model"] = vm
        _render_results(vm)

    def _render_results(vm: dict[str, Any]) -> None:
        results_col.clear()
        if vm["db_missing"]:
            status_label.text = "No universe.db — has the universe ever ticked?"
            return
        if vm["not_found"]:
            status_label.text = (
                f"No graph events have ever touched {vm['node_id']}.{vm['property']}."
            )
            return
        status_label.text = f"{vm['hop_count']} hop(s)" + (
            " (truncated — raise --hops)" if vm["truncated"] else ""
        )
        with results_col:
            for idx, hop in enumerate(vm["hops"]):
                _render_hop(ui, idx + 1, hop)

    return container


def _render_hop(ui: Any, index: int, hop: dict[str, Any]) -> None:
    """Render one hop as an expansion block with full tick context."""
    header = f"[{index}] " + _hop_summary(hop)
    palette = (
        "bg-amber-900 border-amber-700"
        if hop.get("tick_missing")
        else "bg-slate-800 border-slate-700"
    )
    with (
        ui.expansion(header).classes(f"w-full rounded-md border text-slate-100 {palette}"),
        ui.column().classes("gap-1 px-2 py-2"),
    ):
        if hop.get("tick_missing"):
            ui.label("(tick file missing on disk)").classes("text-xs text-amber-300")
            return
        if hop.get("timestamp_iso"):
            ui.label(f"timestamp: {hop['timestamp_iso']}").classes(
                "text-xs text-slate-400 font-mono"
            )
        if hop.get("event_type"):
            ui.label(f"event: {hop['event_type']}").classes("text-xs text-slate-400")
        if hop.get("matched_mechanic_id"):
            ui.label(f"mechanic: {hop['matched_mechanic_id']}").classes("text-sm font-mono")
        ca = hop.get("classified_action") or {}
        if ca:
            ui.label(f"classified: verb={ca.get('verb')!r}  object={ca.get('object')!r}").classes(
                "text-xs text-slate-300"
            )
        if hop.get("action_text"):
            ui.label(f"action: {hop['action_text']}").classes("text-sm")
        if hop.get("observation_text"):
            ui.label(f"observation: {hop['observation_text']}").classes(
                "text-sm text-slate-300 whitespace-normal"
            )
