"""Universe-at-a-glance aggregator (``token-world inspect <slug>``).

Collects four classes of signal from a universe directory:

1. **Graph shape** — node counts split by type (agent / entity), edge count.
   Source: ``<universe>/universe.db`` via :class:`KnowledgeGraph`.
2. **Mechanic registry** — total count plus a seed-vs-operator-authored
   split. Author classification heuristic: a mechanic counts as
   "operator-authored" when its module sets ``__author__ = "operator"``
   OR when its git history's *first* commit message starts with
   ``"operator:"``. Everything else is treated as seed (shipped with the
   universe template / hand-authored by the human).
3. **Recent ticks** — last N tick summaries, each rendered as a single
   line: ``tick_id  status  matched_mechanic  → observation_excerpt``.
4. **Active long-running actions** — actor nodes whose
   ``current_long_action`` property is set (from
   ``token_world.engine.long_running``).
5. **Recent yield events** — last 5 ticks where ``yielded == True``.
6. **Operator log presence** — last entry from ``operator-log.jsonl`` if
   the file exists; entirely optional (it does not exist in v1 universes).

The ``InspectReport`` shape is the JSON contract the dashboard consumes.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from token_world.inspect._shared import iter_tick_files, read_json_file


@dataclass(slots=True)
class TickLine:
    """One row of the recent-ticks table."""

    tick_id: str
    timestamp_iso: str
    matched_mechanic_id: str | None
    yielded: bool
    refused: bool
    refusal_reason: str | None
    mutation_count: int
    observation_excerpt: str | None


@dataclass(slots=True)
class ActiveLRA:
    """One active long-running action attached to an actor node."""

    actor_id: str
    action_text: str
    turns_elapsed: int
    turns_total: int | None


@dataclass(slots=True)
class YieldEvent:
    """A single yielded tick (compact form for the recent-yields list)."""

    tick_id: str
    timestamp_iso: str
    action_text_excerpt: str


@dataclass(slots=True)
class MechanicAuthorSplit:
    """Counts of mechanics by authorship classification."""

    seed: int = 0
    operator: int = 0

    @property
    def total(self) -> int:
        return self.seed + self.operator


@dataclass(slots=True)
class InspectReport:
    """Aggregate universe-state report rendered by ``token-world inspect``."""

    slug: str
    universe_dir: str
    # Graph shape
    node_count_total: int = 0
    node_count_by_type: dict[str, int] = field(default_factory=dict)
    edge_count: int = 0
    graph_loaded: bool = False
    graph_load_error: str | None = None
    # Mechanic registry
    mechanic_count: int = 0
    mechanic_authors: MechanicAuthorSplit = field(default_factory=MechanicAuthorSplit)
    # Tick stream
    tick_count_total: int = 0
    recent_ticks: list[TickLine] = field(default_factory=list)
    # Active long-running actions
    active_lras: list[ActiveLRA] = field(default_factory=list)
    # Recent yield events (cap = 5 by contract)
    recent_yields: list[YieldEvent] = field(default_factory=list)
    # Operator log
    operator_log_exists: bool = False
    operator_log_entry_count: int = 0
    operator_log_last_entry: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Aggregators
# ---------------------------------------------------------------------------


def _excerpt(text: str | None, *, max_len: int = 80) -> str | None:
    """Truncate a multi-line string for table output."""
    if text is None:
        return None
    flat = " ".join(text.split())
    if len(flat) <= max_len:
        return flat
    return flat[: max_len - 3] + "..."


def _aggregate_graph(universe_dir: Path, report: InspectReport) -> None:
    """Walk universe.db's graph_state row and populate node/edge counts."""
    db_path = universe_dir / "universe.db"
    if not db_path.is_file():
        return
    # Local import keeps inspect command import-time cheap.
    from token_world.graph import KnowledgeGraph

    kg = KnowledgeGraph(db_path=db_path)
    try:
        kg.load()
    except (ValueError, OSError) as exc:
        report.graph_load_error = f"{type(exc).__name__}: {exc}"
        return

    report.graph_loaded = True
    nodes = kg.nodes()
    report.node_count_total = len(nodes)
    by_type: dict[str, int] = {}
    for node_id in nodes:
        props = kg.query(node_id)
        ntype = props.get("type", "unknown")
        by_type[ntype] = by_type.get(ntype, 0) + 1
        # Also collect active LRAs (actor nodes with current_long_action set)
        lra = props.get("current_long_action")
        if isinstance(lra, dict) and lra:
            report.active_lras.append(
                ActiveLRA(
                    actor_id=node_id,
                    action_text=str(lra.get("action_text", ""))[:120],
                    turns_elapsed=int(lra.get("turns_elapsed", 0) or 0),
                    turns_total=lra.get("turns_total"),
                )
            )
    report.node_count_by_type = dict(sorted(by_type.items()))
    # Edge count via NetworkX through a thin shim (read-only inspection).
    # We deliberately reach into the private graph here because the public
    # API has no edge-count accessor — this is read-only and limited to
    # inspection tooling.
    report.edge_count = int(kg._graph.number_of_edges())  # noqa: SLF001


def _classify_author(module_path: Path, universe_dir: Path) -> str:
    """Return ``"operator"`` or ``"seed"`` for a single mechanic module.

    Heuristic (cheap, no LLM):

    1. If the module source contains ``__author__ = "operator"`` (anywhere
       on a line starting with ``__author__``), mark operator.
    2. Else, look at the *first* git commit that introduced the file. If
       that commit's subject starts with ``operator:`` (case-insensitive),
       mark operator.
    3. Else seed.

    Git failures (no repo, command unavailable) silently degrade to seed.
    """
    try:
        text = module_path.read_text(encoding="utf-8")
    except OSError:
        return "seed"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("__author__") and "operator" in stripped.lower():
            return "operator"

    try:
        rel = module_path.relative_to(universe_dir)
    except ValueError:
        return "seed"

    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "--diff-filter=A",
                "--format=%s",
                "--",
                str(rel),
            ],
            cwd=universe_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return "seed"

    if result.returncode != 0:
        return "seed"
    first_subject = (result.stdout.splitlines() or [""])[0].strip().lower()
    if first_subject.startswith("operator:"):
        return "operator"
    return "seed"


def _aggregate_mechanics(universe_dir: Path, report: InspectReport) -> None:
    """Count mechanic modules and split by authorship."""
    mechanics_dir = universe_dir / "mechanics"
    if not mechanics_dir.is_dir():
        return
    # Use the registry's discover helper for consistency with list-mechanics.
    from token_world.mechanic.loader import discover_mechanic_modules

    try:
        modules = list(discover_mechanic_modules(mechanics_dir))
    except (OSError, ValueError):
        return

    report.mechanic_count = len(modules)
    for module_path in modules:
        author = _classify_author(module_path, universe_dir)
        if author == "operator":
            report.mechanic_authors.operator += 1
        else:
            report.mechanic_authors.seed += 1


def _aggregate_ticks(universe_dir: Path, report: InspectReport, *, last_n: int) -> None:
    """Populate tick_count_total + recent_ticks + recent_yields."""
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    all_files = iter_tick_files(ticks_dir)
    report.tick_count_total = len(all_files)
    if not all_files:
        return

    # Recent N (highest tick IDs).
    recent = all_files[-last_n:] if last_n > 0 else all_files
    for path in recent:
        data = read_json_file(path)
        if data is None:
            continue
        tick_id = str(data.get("tick_id") or path.stem.removeprefix("tick_"))
        mutations = data.get("mutations") or {}
        report.recent_ticks.append(
            TickLine(
                tick_id=tick_id,
                timestamp_iso=str(data.get("timestamp_iso") or ""),
                matched_mechanic_id=data.get("matched_mechanic_id"),
                yielded=bool(data.get("yielded", False)),
                refused=bool(data.get("refused", False)),
                refusal_reason=data.get("refusal_reason"),
                mutation_count=int(mutations.get("count", 0) or 0),
                observation_excerpt=_excerpt(data.get("observation_text")),
            )
        )

    # Recent yield events (scan all files in reverse, take 5 yielded).
    yields: list[YieldEvent] = []
    for path in reversed(all_files):
        if len(yields) >= 5:
            break
        data = read_json_file(path)
        if data is None or not data.get("yielded"):
            continue
        tick_id = str(data.get("tick_id") or path.stem.removeprefix("tick_"))
        yields.append(
            YieldEvent(
                tick_id=tick_id,
                timestamp_iso=str(data.get("timestamp_iso") or ""),
                action_text_excerpt=_excerpt(data.get("action_text")) or "",
            )
        )
    report.recent_yields = list(reversed(yields))


def _aggregate_operator_log(universe_dir: Path, report: InspectReport) -> None:
    """Populate operator-log fields if ``operator-log.jsonl`` exists."""
    log_path = universe_dir / "operator-log.jsonl"
    if not log_path.is_file():
        return
    report.operator_log_exists = True
    last_entry: dict[str, Any] | None = None
    count = 0
    try:
        with log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                count += 1
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    last_entry = parsed
    except OSError:
        return
    report.operator_log_entry_count = count
    report.operator_log_last_entry = last_entry


def aggregate(
    universe_dir: Path,
    *,
    slug: str,
    last_n: int = 10,
) -> InspectReport:
    """Build a complete :class:`InspectReport` for a universe directory.

    Args:
        universe_dir: Root of the universe directory.
        slug: Universe slug (used only for display).
        last_n: How many most-recent ticks to include in ``recent_ticks``.

    Returns:
        A populated report; missing data degrades to empty fields.
    """
    report = InspectReport(slug=slug, universe_dir=str(universe_dir))
    _aggregate_graph(universe_dir, report)
    _aggregate_mechanics(universe_dir, report)
    _aggregate_ticks(universe_dir, report, last_n=last_n)
    _aggregate_operator_log(universe_dir, report)
    return report


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_table(report: InspectReport) -> str:
    """Human-readable inspect output."""
    out: list[str] = []
    out.append(f"=== Universe: {report.slug} ===")
    out.append(f"Path: {report.universe_dir}")
    out.append("")

    out.append("Graph")
    if report.graph_load_error:
        out.append(f"  (load failed: {report.graph_load_error})")
    elif not report.graph_loaded:
        out.append("  (no universe.db yet)")
    else:
        out.append(f"  Nodes: {report.node_count_total}")
        for ntype, count in report.node_count_by_type.items():
            out.append(f"    {ntype:<10} {count}")
        out.append(f"  Edges: {report.edge_count}")
    out.append("")

    out.append("Mechanics")
    if report.mechanic_count == 0:
        out.append("  (no mechanics directory or empty)")
    else:
        out.append(f"  Total: {report.mechanic_count}")
        out.append(f"    seed:     {report.mechanic_authors.seed}")
        out.append(f"    operator: {report.mechanic_authors.operator}")
    out.append("")

    out.append(f"Ticks ({report.tick_count_total} total, last {len(report.recent_ticks)}):")
    if not report.recent_ticks:
        out.append("  (no tick summaries found)")
    else:
        # Header row matches the data-row column widths in the loop below:
        # tick_id:>4  status:<6  mech:<24  "(N mut)" (rendered as 7-wide
        # "MUT    " here so columns align with e.g. "(0 mut)")  observation.
        out.append(f"  {'TICK':>4}  {'STATUS':<6}  {'MECHANIC':<24}  {'MUT':<7}  OBSERVATION")
        out.append(f"  {'-' * 4}  {'-' * 6}  {'-' * 24}  {'-' * 7}  {'-' * 11}")
        for line in report.recent_ticks:
            status = "yield" if line.yielded else ("refuse" if line.refused else "exec")
            mech = line.matched_mechanic_id or "-"
            obs = line.observation_excerpt or ""
            out.append(
                f"  {line.tick_id:>4}  {status:<6}  {mech:<24}  ({line.mutation_count} mut)  {obs}"
            )
    out.append("")

    out.append("Active Long-Running Actions")
    if not report.active_lras:
        out.append("  (none)")
    else:
        for lra in report.active_lras:
            duration = (
                f"{lra.turns_elapsed}/{lra.turns_total}"
                if lra.turns_total is not None
                else f"{lra.turns_elapsed}/-"
            )
            out.append(f"  {lra.actor_id:<20} [{duration}]  {lra.action_text}")
    out.append("")

    out.append("Recent Yields (last 5)")
    if not report.recent_yields:
        out.append("  (none)")
    else:
        for y in report.recent_yields:
            out.append(f"  tick {y.tick_id} @ {y.timestamp_iso}: {y.action_text_excerpt}")
    out.append("")

    out.append("Operator Log")
    if not report.operator_log_exists:
        out.append("  (operator-log.jsonl not present)")
    else:
        out.append(f"  Entries: {report.operator_log_entry_count}")
        last = report.operator_log_last_entry
        if last is not None:
            ts = last.get("timestamp") or last.get("ts") or ""
            kind = last.get("kind") or last.get("event") or ""
            out.append(f"  Last:    {ts} {kind}")

    return "\n".join(out) + "\n"


def render_json(report: InspectReport, *, indent: int | None = 2) -> str:
    """Machine-readable inspect output (stable contract)."""
    payload: dict[str, Any] = {
        "slug": report.slug,
        "universe_dir": report.universe_dir,
        "graph": {
            "loaded": report.graph_loaded,
            "load_error": report.graph_load_error,
            "node_count_total": report.node_count_total,
            "node_count_by_type": report.node_count_by_type,
            "edge_count": report.edge_count,
        },
        "mechanics": {
            "count": report.mechanic_count,
            "by_author": {
                "seed": report.mechanic_authors.seed,
                "operator": report.mechanic_authors.operator,
            },
        },
        "ticks": {
            "total": report.tick_count_total,
            "recent": [
                {
                    "tick_id": t.tick_id,
                    "timestamp_iso": t.timestamp_iso,
                    "matched_mechanic_id": t.matched_mechanic_id,
                    "yielded": t.yielded,
                    "refused": t.refused,
                    "refusal_reason": t.refusal_reason,
                    "mutation_count": t.mutation_count,
                    "observation_excerpt": t.observation_excerpt,
                }
                for t in report.recent_ticks
            ],
        },
        "active_lras": [
            {
                "actor_id": lra.actor_id,
                "action_text": lra.action_text,
                "turns_elapsed": lra.turns_elapsed,
                "turns_total": lra.turns_total,
            }
            for lra in report.active_lras
        ],
        "recent_yields": [
            {
                "tick_id": y.tick_id,
                "timestamp_iso": y.timestamp_iso,
                "action_text_excerpt": y.action_text_excerpt,
            }
            for y in report.recent_yields
        ],
        "operator_log": {
            "exists": report.operator_log_exists,
            "entry_count": report.operator_log_entry_count,
            "last_entry": report.operator_log_last_entry,
        },
    }
    return json.dumps(payload, indent=indent, sort_keys=True) + "\n"
