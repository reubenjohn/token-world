"""Causal-chain walker (``token-world trace <slug> <node_id> <property>``).

Given a node + property, walks the universe's ``graph_events`` log
backward in time and, for each mutation, surfaces the surrounding tick
context — classified action, matched mechanic, observation.

The walker stops at one of three boundaries:

- **Origin**: the chain reaches the property's original ``add_node`` or
  the first observed value (no earlier event).
- **Hop limit** (configurable, default 10): prevents pathological walks
  on hot properties (e.g. an ``hp`` ticker mutated 200 times).
- **Missing tick**: when a graph event references a tick whose summary
  file no longer exists on disk, the walker emits a synthetic
  "tick missing" hop and stops.

The output JSON shape lists hops oldest-to-newest (the reverse of the
walk order) so the dashboard can render the causal arrow naturally.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from token_world.inspect._shared import iter_tick_files, read_json_file, tick_id_sort_key


@dataclass(slots=True)
class TraceHop:
    """One mutation -> tick step in the causal chain."""

    tick_id: str
    event_type: str
    target_id: str
    property_name: str | None
    old_value: Any = None
    new_value: Any = None
    # Tick context (None when the corresponding tick file is missing).
    timestamp_iso: str | None = None
    action_text: str | None = None
    classified_action: dict[str, Any] | None = None
    matched_mechanic_id: str | None = None
    observation_text: str | None = None
    # When True, the tick file referenced by the event is missing.
    tick_missing: bool = False


@dataclass(slots=True)
class TraceReport:
    """Causal-trace report for a single node-property pair."""

    slug: str
    node_id: str
    property: str
    hops: list[TraceHop] = field(default_factory=list)
    truncated: bool = False  # True iff hop_limit was reached
    not_found: bool = False  # True iff no events touched the property
    db_missing: bool = False  # True iff universe.db is absent


# ---------------------------------------------------------------------------
# Walker
# ---------------------------------------------------------------------------


def _query_events(
    db_path: Path, node_id: str, property: str, *, limit: int
) -> list[tuple[int, str, str, str | None, str | None, str | None]]:
    """Fetch the most-recent ``limit`` events touching ``node_id.property``.

    Returns rows in DESCENDING tick order (newest first); the caller
    reverses for chronological output.
    """
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT tick_id, event_type, target_id, property_name,
                   old_value_json, new_value_json
            FROM graph_events
            WHERE target_id = ?
              AND (property_name = ? OR property_name IS NULL)
            ORDER BY event_id DESC
            LIMIT ?
            """,
            (node_id, property, limit),
        ).fetchall()
    return list(rows)


def _index_tick_files(universe_dir: Path) -> dict[str, dict[str, Any]]:
    """Build a one-shot in-memory index of tick_id -> tick payload."""
    index: dict[str, dict[str, Any]] = {}
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    for path in iter_tick_files(ticks_dir):
        data = read_json_file(path)
        if data is None:
            continue
        tick_id = str(data.get("tick_id") or path.stem.removeprefix("tick_"))
        index[tick_id] = data
    return index


def _decode_value(blob: str | None) -> Any:
    if blob is None:
        return None
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return blob


def trace(
    universe_dir: Path,
    *,
    slug: str,
    node_id: str,
    property: str,
    hop_limit: int = 10,
) -> TraceReport:
    """Build a :class:`TraceReport` for ``node_id.property``.

    Args:
        universe_dir: Universe root directory.
        slug: Universe slug (display only).
        node_id: Graph node id (e.g. ``"alice"``).
        property: Property name (e.g. ``"hp"``).
        hop_limit: Maximum number of hops to walk before truncating.

    Returns:
        A :class:`TraceReport`. Hops are returned oldest-first; an empty
        ``hops`` list with ``not_found=True`` indicates the property was
        never mutated.
    """
    report = TraceReport(slug=slug, node_id=node_id, property=property)
    db_path = universe_dir / "universe.db"
    if not db_path.is_file():
        report.db_missing = True
        return report

    rows = _query_events(db_path, node_id, property, limit=hop_limit + 1)
    if not rows:
        report.not_found = True
        return report

    truncated = len(rows) > hop_limit
    rows = rows[:hop_limit]

    tick_index = _index_tick_files(universe_dir)

    hops: list[TraceHop] = []
    for tick_id_int, event_type, target_id, prop_name, old_blob, new_blob in rows:
        tick_id = str(tick_id_int)
        tick_data = tick_index.get(tick_id)
        hop = TraceHop(
            tick_id=tick_id,
            event_type=event_type,
            target_id=target_id,
            property_name=prop_name,
            old_value=_decode_value(old_blob),
            new_value=_decode_value(new_blob),
        )
        if tick_data is None:
            hop.tick_missing = True
        else:
            hop.timestamp_iso = tick_data.get("timestamp_iso")
            hop.action_text = tick_data.get("action_text")
            hop.classified_action = tick_data.get("classified_action")
            hop.matched_mechanic_id = tick_data.get("matched_mechanic_id")
            hop.observation_text = tick_data.get("observation_text")
        hops.append(hop)

    # Emit oldest-first so a reader walks forward in time.
    hops.sort(key=lambda h: tick_id_sort_key(h.tick_id))
    report.hops = hops
    report.truncated = truncated
    return report


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _excerpt(text: str | None, *, max_len: int = 100) -> str:
    if not text:
        return ""
    flat = " ".join(text.split())
    if len(flat) <= max_len:
        return flat
    return flat[: max_len - 3] + "..."


def render_table(report: TraceReport) -> str:
    """Render the chain as a series of indent cards."""
    out: list[str] = []
    out.append(f"=== Trace: {report.slug} :: {report.node_id}.{report.property} ===")

    if report.db_missing:
        out.append("(no universe.db at this slug — has the universe ever ticked?)")
        return "\n".join(out) + "\n"
    if report.not_found:
        out.append(f"No graph events have ever touched {report.node_id}.{report.property}.")
        return "\n".join(out) + "\n"

    out.append(f"{len(report.hops)} hop(s){' (truncated)' if report.truncated else ''}")
    for i, hop in enumerate(report.hops):
        out.append("")
        out.append(f"  [{i + 1}] tick {hop.tick_id}  ({hop.event_type})")
        if hop.tick_missing:
            out.append("      (tick file missing on disk)")
        else:
            out.append(f"      timestamp: {hop.timestamp_iso}")
            mech = hop.matched_mechanic_id or "-"
            out.append(f"      mechanic:  {mech}")
            if hop.classified_action:
                ca = hop.classified_action
                out.append(f"      classified: verb={ca.get('verb')!r} object={ca.get('object')!r}")
            if hop.action_text:
                out.append(f"      action:    {_excerpt(hop.action_text)}")
            if hop.observation_text:
                out.append(f"      observation: {_excerpt(hop.observation_text)}")
        out.append(
            f"      mutation: {hop.target_id}"
            f"{'.' + hop.property_name if hop.property_name else ''} : "
            f"{hop.old_value!r} -> {hop.new_value!r}"
        )
    return "\n".join(out) + "\n"


def render_json(report: TraceReport, *, indent: int | None = 2) -> str:
    """Stable JSON contract."""
    payload: dict[str, Any] = {
        "slug": report.slug,
        "node_id": report.node_id,
        "property": report.property,
        "db_missing": report.db_missing,
        "not_found": report.not_found,
        "truncated": report.truncated,
        "hops": [asdict(hop) for hop in report.hops],
    }
    return json.dumps(payload, indent=indent, sort_keys=True, default=str) + "\n"
