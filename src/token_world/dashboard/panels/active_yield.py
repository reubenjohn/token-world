"""Active-yield banner — surfaces pending operator yields at the top of the page.

Reads :func:`token_world.inspect.yields.find_pending_yields` directly (no
shell-out). When at least one yield is pending, renders a sticky amber-accent
banner summarising the *most recent* one plus a count of any additional
siblings. When nothing is pending, the banner collapses to zero vertical
footprint (``visible = False``) so the rest of the dashboard isn't shoved
downward.

Poll cadence: 5s — matches the ``operator_inbox`` protocol's filesystem-
polling contract (see :mod:`token_world.operator.external`).

Design notes
------------

- Pure read-only. The dashboard never writes ``.resolved`` / ``.rejected``.
- The yield protocol is owned by :mod:`token_world.operator`; this panel
  only consumes the :class:`PendingYield` dataclass surface from
  :mod:`token_world.inspect.yields`.
- Degrades gracefully on a missing inbox (e.g., universe has never yielded)
  — ``find_pending_yields`` returns an empty list and the banner hides.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from token_world.inspect.yields import PendingYield, find_pending_yields

__all__ = [
    "format_banner_text",
    "load_pending_yields",
    "mount_active_yield_banner",
]


def load_pending_yields(universe_dir: Path) -> list[PendingYield]:
    """Return every unresolved yield for ``universe_dir``.

    Swallows all exceptions and returns ``[]`` so the dashboard never crashes
    on a missing / corrupt inbox.
    """
    try:
        return find_pending_yields(universe_dir)
    except Exception:  # noqa: BLE001 — dashboard must degrade gracefully.
        return []


def format_banner_text(pending: list[PendingYield]) -> str:
    """Compose the single-line banner label from a pending-yield list.

    Surfaces the *most recent* yield (last by mtime) with a count suffix
    when multiple are queued. Shape:

        Pending yield on tick 42: pickup alice -> rock · hint: no_mechanic_for_action

    With N>1 queued:

        [+2 more] Pending yield on tick 42: pickup alice -> rock · hint: ...

    Returns the empty string when ``pending`` is empty (caller should hide).
    """
    if not pending:
        return ""
    latest = pending[-1]  # mtime-ascending, so last is newest
    verb = latest.verb or "?"
    actor = latest.actor or "?"
    target = latest.target or "-"
    hint = latest.hint or ""
    prefix = f"[+{len(pending) - 1} more] " if len(pending) > 1 else ""
    return (
        f"{prefix}Pending yield on tick {latest.tick_id}: {verb} {actor} -> {target} · hint: {hint}"
    )


def mount_active_yield_banner(universe_dir: Path, parent: Any) -> None:
    """Mount the active-yield banner into the current NiceGUI page.

    The banner is created hidden and only becomes visible on the first poll
    tick that observes at least one pending yield. Mounts directly into
    ``parent`` (a NiceGUI column/row), so the caller controls placement.
    """
    from nicegui import ui

    with parent:
        # Amber-accent sticky banner. `visible=False` at creation so the
        # no-yield case occupies zero vertical space.
        banner = ui.row().classes(
            "w-full px-4 py-2 bg-amber-900 text-amber-100 border-l-4 "
            "border-amber-400 rounded-md items-center gap-3 sticky top-0 z-50"
        )
        banner.visible = False
        with banner:
            label = ui.label("").classes("text-sm font-mono")

    def _refresh() -> None:
        pending = load_pending_yields(universe_dir)
        if not pending:
            banner.visible = False
            return
        label.text = format_banner_text(pending)
        banner.visible = True

    _refresh()
    ui.timer(5.0, _refresh)
