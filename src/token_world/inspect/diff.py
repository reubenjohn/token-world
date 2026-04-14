"""Tick-to-tick diff aggregator (``token-world diff <slug> <tick_a> <tick_b>``).

Walks the universe's ``graph_events`` table for the open interval
``(tick_a, tick_b]`` and reports the net effect on the graph: added /
removed nodes, added / removed edges, property changes (with old -> new
when a single mutation; ``...`` when multiple intermediate values).

This implementation deliberately avoids loading two full snapshots from
SQLite in favour of an event replay — it's cheaper, works without
explicit snapshot management, and surfaces the same information the
trace command consumes. Future enhancement: when both ticks have
matching ``graph_snapshots`` rows, materialise both graphs and produce
a structural diff (caught: edge attribute changes, which the event
replay misses).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class PropertyChange:
    """One node-property change across the diff window."""

    target: str
    property: str
    old_value: Any = None
    new_value: Any = None
    intermediate: bool = False  # True if multiple set events squashed


@dataclass(slots=True)
class EdgeChange:
    """One edge mutation across the diff window."""

    target: str  # "src->dst" string per graph_events convention


@dataclass(slots=True)
class DiffReport:
    """Aggregate diff between two ticks."""

    slug: str
    tick_a: int
    tick_b: int
    db_missing: bool = False
    nodes_added: list[str] = field(default_factory=list)
    nodes_removed: list[str] = field(default_factory=list)
    edges_added: list[EdgeChange] = field(default_factory=list)
    edges_removed: list[EdgeChange] = field(default_factory=list)
    property_changes: list[PropertyChange] = field(default_factory=list)


def _coerce_int(tick_id: str | int) -> int:
    if isinstance(tick_id, int):
        return tick_id
    try:
        return int(str(tick_id))
    except ValueError:
        return 0


def _decode(blob: str | None) -> Any:
    if blob is None:
        return None
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return blob


def diff(
    universe_dir: Path,
    *,
    slug: str,
    tick_a: str | int,
    tick_b: str | int,
) -> DiffReport:
    """Compute the diff between two ticks via event replay.

    The half-open interval ``(tick_a, tick_b]`` is scanned; events with
    ``tick_id <= tick_a`` are ignored, and events with ``tick_id > tick_b``
    are ignored. ``tick_a`` may be greater than ``tick_b`` — values are
    swapped so the report always reflects a forward chronological diff.

    Args:
        universe_dir: Universe root directory.
        slug: Universe slug (display only).
        tick_a, tick_b: Tick IDs (strings or ints).

    Returns:
        Populated :class:`DiffReport`. Empty fields when no events were
        recorded in the window.
    """
    a = _coerce_int(tick_a)
    b = _coerce_int(tick_b)
    if a > b:
        a, b = b, a
    report = DiffReport(slug=slug, tick_a=a, tick_b=b)

    db_path = universe_dir / "universe.db"
    if not db_path.is_file():
        report.db_missing = True
        return report

    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT tick_id, event_type, target_id, property_name,
                   old_value_json, new_value_json
            FROM graph_events
            WHERE tick_id > ? AND tick_id <= ?
            ORDER BY event_id ASC
            """,
            (a, b),
        ).fetchall()

    # Fold the event stream.
    nodes_added: dict[str, bool] = {}  # node_id -> still added at end
    nodes_removed: list[str] = []
    edges_added: list[str] = []
    edges_removed: list[str] = []
    # property changes: (target, prop) -> [old_value, new_value, count]
    prop_state: dict[tuple[str, str], list[Any]] = {}

    for _tick, event_type, target_id, prop_name, old_blob, new_blob in rows:
        if event_type == "add_node":
            nodes_added[target_id] = True
        elif event_type == "remove_node":
            if target_id in nodes_added:
                # Net effect: didn't exist before, doesn't exist after — drop.
                nodes_added.pop(target_id, None)
            else:
                nodes_removed.append(target_id)
        elif event_type == "add_edge":
            edges_added.append(target_id)
        elif event_type == "remove_edge":
            edges_removed.append(target_id)
        elif event_type == "set_property" and prop_name is not None:
            key = (target_id, prop_name)
            old = _decode(old_blob)
            new = _decode(new_blob)
            if key not in prop_state:
                prop_state[key] = [old, new, 1]
            else:
                # Keep original "old", update "new", bump count.
                prop_state[key][1] = new
                prop_state[key][2] += 1

    report.nodes_added = sorted(nodes_added)
    report.nodes_removed = sorted(set(nodes_removed))
    report.edges_added = [EdgeChange(target=e) for e in sorted(set(edges_added))]
    report.edges_removed = [EdgeChange(target=e) for e in sorted(set(edges_removed))]
    report.property_changes = sorted(
        (
            PropertyChange(
                target=t,
                property=p,
                old_value=state[0],
                new_value=state[1],
                intermediate=state[2] > 1,
            )
            for (t, p), state in prop_state.items()
        ),
        key=lambda c: (c.target, c.property),
    )
    return report


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_table(report: DiffReport) -> str:
    out: list[str] = []
    out.append(f"=== Diff: {report.slug} ticks {report.tick_a}..{report.tick_b} ===")
    if report.db_missing:
        out.append("(no universe.db at this slug)")
        return "\n".join(out) + "\n"

    out.append("")
    out.append(f"Nodes added ({len(report.nodes_added)})")
    for n in report.nodes_added:
        out.append(f"  + {n}")

    out.append("")
    out.append(f"Nodes removed ({len(report.nodes_removed)})")
    for n in report.nodes_removed:
        out.append(f"  - {n}")

    out.append("")
    out.append(f"Edges added ({len(report.edges_added)})")
    for e in report.edges_added:
        out.append(f"  + {e.target}")

    out.append("")
    out.append(f"Edges removed ({len(report.edges_removed)})")
    for e in report.edges_removed:
        out.append(f"  - {e.target}")

    out.append("")
    out.append(f"Property changes ({len(report.property_changes)})")
    for c in report.property_changes:
        marker = " (multi)" if c.intermediate else ""
        out.append(f"  {c.target}.{c.property}: {c.old_value!r} -> {c.new_value!r}{marker}")

    return "\n".join(out) + "\n"


def render_json(report: DiffReport, *, indent: int | None = 2) -> str:
    payload: dict[str, Any] = asdict(report)
    return json.dumps(payload, indent=indent, sort_keys=True, default=str) + "\n"
