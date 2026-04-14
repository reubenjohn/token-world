"""Side-effect chain panel — forward propagation within a single tick (§A5).

Renders the ``ExecutionTrace`` tree emitted by
:class:`~token_world.mechanic.engine.ChainExecutionEngine` as an indented
tree inside a tick-card expansion. A mechanic's mutations can trigger
downstream involuntary mechanics (bounded by ``engine.max_chain_depth``);
this view shows *which* mechanics fired, in *what* order, and *what*
mutations each one emitted.

Naming note (§A5a): this is distinct from the "property history" panel
(file ``property_history.py``). That one is a *backward* walk through the
lifetime of a single property on a single node; this one is a *forward*
walk within a single tick. The CLI ``token-world trace`` still targets
the backward-walk behaviour and is intentionally unchanged.

The trace data lives at
``<universe>/diagnostics/tick_<id>/execution/trace.json`` (written by the
engine via :meth:`TickDiagnostics.write_execution_trace`). The on-disk
schema is:

    {
      "root": {
        "mechanic_id": str, "actor": str, "target": str,
        "check_passed": bool, "check_reasons": [str, ...],
        "mutations": [{...}, ...],
        "children": [<same shape, recursively>]
      },
      "total_mechanics_executed": int,
      "max_depth_reached": int,
      "truncated": bool,
    }

For tick-stream cards, we only have the tick_summary JSON (no trace
data) — so when no trace is available we render a placeholder. When a
tick was refused or yielded (no mechanic fired), we render a different
placeholder.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_execution_trace(universe_dir: Path, tick_id: str) -> dict[str, Any] | None:
    """Return the parsed execution trace dict for a tick, or ``None``.

    Reads ``<universe>/diagnostics/tick_<id>/execution/trace.json``. If
    the file is missing or unreadable as JSON, returns ``None`` rather
    than raising — callers treat "no trace" as a UI state, not an error.
    """
    path = universe_dir / "diagnostics" / f"tick_{tick_id}" / "execution" / "trace.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(data, dict):
        return data
    return None


def render_side_effect_tree(
    tick_or_trace: dict[str, Any],
    parent: Any,
    *,
    universe_dir: Path | None = None,
) -> None:
    """Render an :class:`ExecutionTrace` tree inside ``parent``.

    Accepts either a tick_summary dict or a trace dict directly.

    When given a tick_summary dict and an optional ``universe_dir``, this
    tries to load the trace from
    ``<universe_dir>/diagnostics/tick_<id>/execution/trace.json`` — the
    engine writes the full tree there via
    :meth:`TickDiagnostics.write_execution_trace`, but the tick_summary
    JSON itself only carries the flattened mutations list. A pre-loaded
    trace can also be embedded in the tick_summary under the key
    ``exec_trace``; that takes precedence over disk lookup.

    Args:
        tick_or_trace: Either a tick_summary dict (with keys ``tick_id``,
            ``matched_mechanic_id``, ``yielded``, ``refused``, and
            optionally ``exec_trace``) or a trace dict (with keys
            ``root``, ``total_mechanics_executed``, ``max_depth_reached``,
            ``truncated``).
        parent: The NiceGUI container in which to render. (Currently
            unused because the NiceGUI ``with`` context is opened by
            the caller, but kept as an explicit arg per the task spec.)
        universe_dir: Optional universe root. When supplied with a
            tick_summary input, the panel will load the trace from disk.
    """
    from nicegui import ui

    _ = parent  # parent container already acts as the ``with`` context

    # Distinguish tick_summary vs trace by the presence of the "root" key.
    trace: dict[str, Any] | None = None
    refused = False
    yielded = False
    if "root" in tick_or_trace and "total_mechanics_executed" in tick_or_trace:
        trace = tick_or_trace
    else:
        # Tick-summary shape.
        yielded = bool(tick_or_trace.get("yielded"))
        refused = bool(tick_or_trace.get("refused"))
        trace = tick_or_trace.get("exec_trace") or None
        if trace is None and universe_dir is not None:
            tick_id = str(tick_or_trace.get("tick_id") or "")
            if tick_id:
                trace = load_execution_trace(universe_dir, tick_id)

    # No execution happened: yield / refuse / unmatched tick.
    if trace is None:
        if yielded or refused:
            ui.label("— no execution trace (refused/yielded tick)").classes(
                "text-xs italic text-slate-400"
            )
        else:
            ui.label("— no execution trace available").classes("text-xs italic text-slate-400")
        return

    root = trace.get("root")
    if not isinstance(root, dict):
        ui.label("— trace malformed (no root)").classes("text-xs italic text-slate-400")
        return

    # Warning chips for truncation / depth.
    if trace.get("truncated"):
        ui.label("⚠ truncated — chain exceeded max_depth").classes(
            "text-xs text-amber-300 font-semibold"
        )
    max_depth = trace.get("max_depth_reached")
    if isinstance(max_depth, int) and max_depth > 0:
        ui.label(f"max_depth_reached: {max_depth}").classes("text-xs text-slate-400 font-mono")

    _render_node(ui, root, depth=0)


def _render_node(ui: Any, node: dict[str, Any], *, depth: int) -> None:
    """Render a single TraceNode row, then recurse into children.

    Each node shows:

        <mechanic_id>(<check>) → N mutations → [children]

    Indent is ``depth * 16px`` via an inline ``margin-left`` style. We
    use a left border on the row so the tree shape is visible without
    box-drawing characters.
    """
    indent_px = depth * 16
    mech = node.get("mechanic_id") or "?"
    actor = node.get("actor") or "?"
    target = node.get("target") or "-"
    check_passed = node.get("check_passed")
    check_text = "check_pass" if check_passed else "check_fail"
    mut_count = len(node.get("mutations") or [])
    children = node.get("children") or []

    check_colour = "text-emerald-300" if check_passed else "text-rose-300"
    border_colour = "border-slate-600" if depth == 0 else "border-slate-700"

    header_line = f"{mech}({check_text})  →  {mut_count} mutation(s)  →  {len(children)} triggered"
    # Row container — left border + indent renders the tree shape.
    row = ui.column().classes(f"gap-0 pl-2 border-l-2 {border_colour}")
    row.style(f"margin-left: {indent_px}px;")
    with row:
        ui.label(header_line).classes(f"text-sm font-mono {check_colour} whitespace-pre-wrap")
        ui.label(f"actor={actor} target={target}").classes("text-xs text-slate-400 font-mono")
        reasons = node.get("check_reasons") or []
        if reasons:
            ui.label("reasons: " + "; ".join(str(r) for r in reasons)).classes(
                "text-xs text-slate-400 font-mono whitespace-pre-wrap"
            )
        # Brief summary of each mutation on a single line.
        for m in node.get("mutations") or []:
            prop = m.get("property")
            target_n = m.get("target")
            old = m.get("old_value")
            new = m.get("new_value")
            ui.label(f"  · {target_n}.{prop}: {old!r} → {new!r}").classes(
                "text-xs text-slate-300 font-mono whitespace-pre-wrap"
            )

    # Recurse — children rendered as siblings of the parent's row so the
    # indent stack reads as a tree (not nested expansions).
    for child in children:
        if isinstance(child, dict):
            _render_node(ui, child, depth=depth + 1)
