"""NiceGUI application factory for the read-only dashboard.

The module exposes two entry points:

- :func:`create_app` wires all panels into the NiceGUI page decorator and
  returns the ``ui`` module for chaining. This is the testable seam — it
  touches NiceGUI but does not start a server.
- :func:`run_app` is the CLI entry point: calls :func:`create_app`, then
  ``ui.run``.

The dashboard is entirely read-only (D-01 constraint). It never writes to
the graph, mechanics dir, or tick summaries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from token_world.universe.manager import UniverseManager


def _resolve_universe(slug: str) -> Path:
    """Resolve a slug to a universe directory, raising on missing."""
    manager = UniverseManager()
    return manager.load(slug)


def create_app(slug: str, *, dark: bool = True) -> Any:
    """Build the NiceGUI page for ``slug``.

    Called by :func:`run_app` and by tests. Tests may pass a slug for
    a non-existent universe — the dashboard displays an error banner
    instead of crashing.
    """
    from nicegui import ui

    # Resolve once; panels downstream take a Path, not a slug.
    universe_dir: Path | None
    error: str | None
    try:
        universe_dir = _resolve_universe(slug)
        error = None
    except FileNotFoundError as exc:
        universe_dir = None
        error = str(exc)

    if dark:
        ui.dark_mode().enable()

    @ui.page("/")
    def index() -> None:  # noqa: D401 — NiceGUI page handler, not a docstring prop.
        ui.add_head_html(
            "<style>.token-world-main{max-width:1600px;margin:0 auto;padding:16px;}</style>"
        )
        with ui.column().classes("token-world-main gap-4 w-full"):
            ui.label(f"Token World Dashboard — {slug}").classes(
                "text-2xl font-semibold text-slate-200"
            )
            if error is not None or universe_dir is None:
                with ui.card().classes("w-full bg-red-900 text-slate-100"):
                    ui.label("Universe not found").classes("text-lg font-semibold")
                    ui.label(error or "(unknown error)").classes("text-sm font-mono")
                    ui.label(
                        "Check `token-world list` for available slugs, or "
                        "`token-world create <name>` to scaffold one."
                    ).classes("text-xs text-slate-300")
                return

            # --- Active yield banner (sticky, hidden when no pending yields) -
            from token_world.dashboard.panels.active_yield import mount_active_yield_banner

            mount_active_yield_banner(universe_dir, ui.column().classes("w-full"))

            # --- Quality scorecard strip (above stats) --------------------------------
            from token_world.dashboard.panels.quality import mount_quality_panel

            mount_quality_panel(universe_dir, slug)

            # --- Header strip -------------------------------------------------
            from token_world.dashboard.panels.stats import mount_stats_strip

            mount_stats_strip(universe_dir, slug)

            # --- Mechanics registry panel (SC-2b) -----------------------------
            from token_world.dashboard.panels.mechanics_panel import mount_mechanics_panel

            mount_mechanics_panel(universe_dir, slug)

            # --- Main body (tick stream | graph | property history) ----------
            _mount_main_body(ui, universe_dir, slug)

    return ui


def _mount_main_body(ui: Any, universe_dir: Path, slug: str) -> None:
    """Mount the main split pane (tick stream / graph / property history).

    Layout at 1280px+:

        +-----------------+-----------------+
        |                 |  Graph canvas   |
        |  Tick stream    |                 |
        |  (live)         +-----------------+
        |                 | Property history|
        +-----------------+-----------------+

    Below 1024px the columns flex-wrap to a single column.
    """
    from token_world.dashboard.panels.graph_canvas import mount_graph_panel
    from token_world.dashboard.panels.property_history import mount_property_history_panel
    from token_world.dashboard.panels.tick_stream import mount_tick_stream_panel
    from token_world.inspect.agents import aggregate as agents_aggregate

    # Reactive selected_agent state (mutable dict as closure-safe ref)
    selected_agent: dict[str, str] = {"value": ""}

    # Agent selector state
    agent_state: dict[str, Any] = {"options": [""], "select_elem": None}

    def _refresh_agent_options() -> None:
        try:
            report = agents_aggregate(universe_dir, slug=slug)
            ids = sorted(a.id for a in report.agents)
        except Exception:  # noqa: BLE001
            ids = []
        options = [""] + ids  # "" = All agents
        agent_state["options"] = options
        sel = agent_state.get("select_elem")
        if sel is not None:
            sel.options = options

    with ui.row().classes("w-full gap-4 items-stretch flex-wrap"):
        with ui.column().classes("flex-1 min-w-[360px] max-w-[560px] gap-2"):
            ui.label("Tick stream").classes("text-lg font-semibold text-slate-200")

            # Agent selector (above tick stream)
            _refresh_agent_options()
            options = agent_state["options"]

            def _on_agent_select(e: Any) -> None:
                selected_agent["value"] = e.value if e.value else ""

            sel_elem = (
                ui.select(
                    options,
                    value="",
                    label="Agent",
                    on_change=_on_agent_select,
                )
                .classes("w-full bg-slate-800 text-slate-100")
                .props("dense dark")
            )
            agent_state["select_elem"] = sel_elem
            ui.timer(2.0, _refresh_agent_options)

            mount_tick_stream_panel(universe_dir, slug, selected_agent=selected_agent)
        with ui.column().classes("flex-1 min-w-[480px] gap-2"):
            ui.label("Graph canvas").classes("text-lg font-semibold text-slate-200")
            mount_graph_panel(universe_dir, slug, selected_agent=selected_agent)
            ui.separator()
            ui.label("Property history").classes("text-lg font-semibold text-slate-200")
            mount_property_history_panel(universe_dir, slug)


def run_app(slug: str, *, port: int = 8080, dark: bool = True, show: bool = True) -> None:
    """CLI entry: build the app and start the server."""
    ui = create_app(slug, dark=dark)
    # reload=False: we never want the NiceGUI reloader picking up stale modules
    # in a CLI run. show opens the browser; callers disable it in tests.
    ui.run(
        title=f"Token World — {slug}",
        port=port,
        reload=False,
        show=show,
        dark=dark,
    )
