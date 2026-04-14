"""Aggregate metrics report (``token-world stats <slug>``).

Composes signals from three sources:

- **Tick stream** (``tick_summaries/ticks/``): tick count, throughput
  (ticks/min from timestamps), yield rate, novel-mechanic rate per 10
  ticks (when a tick references a mechanic id never seen before in the
  scanned window), distinct subtype count over time (a proxy for the
  novel-concept growth rate).
- **Cost** — composes with :mod:`token_world.playtest.cost` so the same
  totals appear under the ``cost`` block (``$total``, ``input/output``
  tokens, backend label).
- **Conservation events** — best-effort scan of ``tick_summaries/`` for
  refusal_reason values that match ``conservation_violation`` or any
  ``ConservationChecker``-style structured payload.

The ``--since N`` flag scopes EVERYTHING to the last N ticks. The
``--stream`` flag is wired through the CLI (it polls and re-emits) but
this module exposes only the one-shot :func:`aggregate` — the CLI
implements the streaming loop itself.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from token_world.inspect._shared import iter_tick_files, read_json_file


@dataclass(slots=True)
class StatsReport:
    """Aggregate metrics report for a universe."""

    slug: str
    since: int | None = None
    # Tick metrics
    tick_count: int = 0
    tick_id_min: str | None = None
    tick_id_max: str | None = None
    timestamp_min: str | None = None
    timestamp_max: str | None = None
    duration_seconds: float = 0.0
    ticks_per_minute: float = 0.0
    yield_count: int = 0
    yield_rate: float = 0.0
    refuse_count: int = 0
    refuse_rate: float = 0.0
    executed_count: int = 0
    executed_rate: float = 0.0
    distinct_mechanics_used: int = 0
    novel_mechanics_per_10_ticks: float = 0.0
    novel_mechanic_introductions: int = 0
    # Subtype proxy for novel-concept growth.
    distinct_subtypes_seen: int = 0
    distinct_subtype_history: list[str] = field(default_factory=list)
    # Conservation
    conservation_violation_count: int = 0
    # Cost summary (composes with playtest.cost)
    cost_total_usd: float = 0.0
    cost_total_input_tokens: int = 0
    cost_total_output_tokens: int = 0
    cost_backend: str = "no-data"


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _scan_subtype_proxies(mutations_list: list[Any]) -> set[str]:
    """Look at mutation entries and pull out any ``subtype`` value seen.

    Mutation rows in tick summaries are ``[target, property, old, new]``.
    Distinct ``subtype`` values are a cheap proxy for novel-concept growth
    because mechanics that introduce new concepts almost always tag them
    via a ``subtype`` property.
    """
    out: set[str] = set()
    for entry in mutations_list:
        if not isinstance(entry, list) or len(entry) != 4:
            continue
        _target, prop, _old, new = entry
        if prop == "subtype" and isinstance(new, str):
            out.add(new)
    return out


def aggregate(
    universe_dir: Path,
    *,
    slug: str,
    since: int | None = None,
) -> StatsReport:
    """Build a :class:`StatsReport` for the universe.

    Args:
        universe_dir: Universe root directory.
        slug: Universe slug (display only).
        since: When set, restrict ALL metrics to the last N ticks
            (chronologically). Cost composition uses the same window.

    Returns:
        A populated report. Empty universes degrade to zero-filled fields
        without raising.
    """
    report = StatsReport(slug=slug, since=since)

    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    files = iter_tick_files(ticks_dir, since)
    tick_payloads: list[dict[str, Any]] = []
    for path in files:
        data = read_json_file(path)
        if data is None:
            continue
        tick_payloads.append(data)

    report.tick_count = len(tick_payloads)
    if not tick_payloads:
        # Still surface cost composition (will be empty for an empty universe).
        _populate_cost(universe_dir, report, slug=slug, since=since)
        return report

    # Tick-id range.
    ids = [str(d.get("tick_id") or "") for d in tick_payloads]
    report.tick_id_min = ids[0]
    report.tick_id_max = ids[-1]

    # Timestamps + throughput.
    timestamps = [_parse_iso(d.get("timestamp_iso")) for d in tick_payloads]
    valid_ts = [ts for ts in timestamps if ts is not None]
    if valid_ts:
        report.timestamp_min = valid_ts[0].isoformat()
        report.timestamp_max = valid_ts[-1].isoformat()
        delta = (valid_ts[-1] - valid_ts[0]).total_seconds()
        report.duration_seconds = max(delta, 0.0)
        if delta > 0:
            report.ticks_per_minute = (report.tick_count - 1) / (delta / 60.0)

    # Status counts + rates.
    seen_mechanics: set[str] = set()
    novel_intros = 0
    distinct_subtypes: set[str] = set()
    subtype_history: list[str] = []
    conservation_violations = 0

    for data in tick_payloads:
        if data.get("yielded"):
            report.yield_count += 1
        elif data.get("refused"):
            report.refuse_count += 1
            reason = (data.get("refusal_reason") or "").lower()
            if "conservation" in reason:
                conservation_violations += 1
        else:
            report.executed_count += 1

        mech = data.get("matched_mechanic_id")
        if isinstance(mech, str) and mech and mech not in seen_mechanics:
            novel_intros += 1
            seen_mechanics.add(mech)

        mut_list = ((data.get("mutations") or {}).get("list")) or []
        for sub in _scan_subtype_proxies(mut_list):
            if sub not in distinct_subtypes:
                distinct_subtypes.add(sub)
                subtype_history.append(sub)

    report.distinct_mechanics_used = len(seen_mechanics)
    report.novel_mechanic_introductions = novel_intros
    if report.tick_count > 0:
        report.yield_rate = report.yield_count / report.tick_count
        report.refuse_rate = report.refuse_count / report.tick_count
        report.executed_rate = report.executed_count / report.tick_count
        report.novel_mechanics_per_10_ticks = novel_intros / report.tick_count * 10.0

    report.distinct_subtypes_seen = len(distinct_subtypes)
    report.distinct_subtype_history = subtype_history
    report.conservation_violation_count = conservation_violations

    _populate_cost(universe_dir, report, slug=slug, since=since)

    return report


def _populate_cost(
    universe_dir: Path,
    report: StatsReport,
    *,
    slug: str,
    since: int | None,
) -> None:
    """Compose with ``token_world.playtest.cost.aggregate`` for the cost block."""
    # Local import keeps this aggregator import-cheap when callers only
    # need the tick-stream metrics (e.g. tests).
    from token_world.playtest.cost import aggregate as cost_aggregate

    cost_report = cost_aggregate(universe_dir, slug=slug, since=since)
    report.cost_total_usd = cost_report.total_cost_usd
    report.cost_total_input_tokens = cost_report.total_input_tokens
    report.cost_total_output_tokens = cost_report.total_output_tokens
    report.cost_backend = cost_report.backend_label


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_table(report: StatsReport) -> str:
    """Compact text table."""
    out: list[str] = []
    title = f"=== Stats: {report.slug} ==="
    if report.since:
        title += f" (last {report.since} ticks)"
    out.append(title)

    if report.tick_count == 0:
        out.append("No ticks have been recorded.")
        return "\n".join(out) + "\n"

    out.append("")
    out.append("Tick stream")
    out.append(f"  Ticks:               {report.tick_count}")
    if report.tick_id_min and report.tick_id_max:
        out.append(f"  Tick range:          {report.tick_id_min}..{report.tick_id_max}")
    if report.duration_seconds > 0:
        out.append(f"  Wall duration:       {report.duration_seconds:.1f} s")
        out.append(f"  Throughput:          {report.ticks_per_minute:.2f} ticks/min")
    out.append(
        f"  Executed / Yielded / Refused: "
        f"{report.executed_count} / {report.yield_count} / {report.refuse_count}"
    )
    out.append(f"  Yield rate:          {report.yield_rate * 100:.1f}%")
    out.append(f"  Refuse rate:         {report.refuse_rate * 100:.1f}%")
    out.append("")

    out.append("Mechanics")
    out.append(f"  Distinct used:       {report.distinct_mechanics_used}")
    out.append(f"  Novel intros:        {report.novel_mechanic_introductions}")
    out.append(f"  Novel / 10 ticks:    {report.novel_mechanics_per_10_ticks:.2f}")
    out.append("")

    out.append("Emergent concepts")
    out.append(f"  Distinct subtypes:   {report.distinct_subtypes_seen}")
    out.append("")

    out.append("Conservation")
    out.append(f"  Violations seen:     {report.conservation_violation_count}")
    out.append("")

    out.append("Cost")
    out.append(f"  Total USD:           ${report.cost_total_usd:.4f}")
    out.append(f"  Input tokens:        {report.cost_total_input_tokens:,}")
    out.append(f"  Output tokens:       {report.cost_total_output_tokens:,}")
    out.append(f"  Backend:             {report.cost_backend}")

    return "\n".join(out) + "\n"


def render_json(report: StatsReport, *, indent: int | None = 2) -> str:
    """Stable JSON contract — flat dataclass dump."""
    payload: dict[str, Any] = asdict(report)
    return json.dumps(payload, indent=indent, sort_keys=True) + "\n"
