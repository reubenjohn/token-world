"""Mechanic registry browser (``token-world mechanics <slug>``).

Walks the universe's mechanics directory through
:class:`~token_world.mechanic.registry.MechanicRegistry`, then enriches
each mechanic with two derived signals:

- **call_count** — how many times the mechanic appears as
  ``matched_mechanic_id`` across the universe's ``tick_summaries/ticks/``.
  Computed by a single pass over all tick files.
- **last_invoked_tick** — the highest (numerically) tick ID where this
  mechanic was the matched mechanic, or ``None`` if never invoked.

Author classification reuses the same heuristic as
:func:`token_world.inspect.universe._classify_author` to keep the two
commands consistent. The ``--author seed|operator`` filter is applied
after enrichment so call counts always reflect the unfiltered registry.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from token_world.inspect._shared import iter_tick_files, read_json_file, tick_id_sort_key


@dataclass(slots=True)
class MechanicRow:
    """One row of the mechanics-registry table."""

    id: str
    description: str
    voluntary: bool
    tags: list[str] = field(default_factory=list)
    source_path: str = ""
    author: str = "seed"  # "seed" or "operator"
    call_count: int = 0
    last_invoked_tick: str | None = None
    first_authored_commit: str | None = None
    first_authored_timestamp: str | None = None


@dataclass(slots=True)
class MechanicsReport:
    """Aggregate registry browser report."""

    slug: str
    mechanics: list[MechanicRow] = field(default_factory=list)
    author_filter: str | None = None  # mirrors the --author flag for traceability


# ---------------------------------------------------------------------------
# Git history helper
# ---------------------------------------------------------------------------


def _git_first_commit(universe_dir: Path, source_path: str) -> tuple[str | None, str | None]:
    """Return (commit_hash, timestamp) of the oldest git commit for source_path.

    Uses ``git log --follow`` so renames are tracked. Returns ``(None, None)``
    on any error (no git, no history, timeout, etc.) — graceful degradation.
    """
    try:
        rel_path = Path(source_path).relative_to(universe_dir)
    except ValueError:
        rel_path = Path(source_path).name  # type: ignore[assignment]
    try:
        result = subprocess.run(
            ["git", "log", "--follow", "--format=%H %aI", "--", str(rel_path)],
            capture_output=True,
            text=True,
            cwd=str(universe_dir),
            timeout=5,
        )
        lines = result.stdout.strip().splitlines()
        if not lines:
            return (None, None)
        # Last line = oldest commit
        oldest = lines[-1].strip()
        commit_hash, timestamp = oldest.split(" ", 1)
        return (commit_hash[:40], timestamp)
    except Exception:  # noqa: BLE001
        return (None, None)


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


def _scan_call_counts(universe_dir: Path) -> dict[str, tuple[int, str | None]]:
    """Scan all tick summaries and return ``{mechanic_id: (count, last_tick_id)}``.

    Numerically-sortable tick IDs are preferred when multiple ticks match;
    we still record the lexicographically-greatest as a fallback for any
    non-numeric IDs that happen to slip through.
    """
    counts: dict[str, int] = {}
    last_tick: dict[str, str] = {}
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    for path in iter_tick_files(ticks_dir):
        data = read_json_file(path)
        if data is None:
            continue
        mech_id = data.get("matched_mechanic_id")
        if not mech_id:
            continue
        tick_id = str(data.get("tick_id") or path.stem.removeprefix("tick_"))
        counts[mech_id] = counts.get(mech_id, 0) + 1
        prior = last_tick.get(mech_id)
        if prior is None or tick_id_sort_key(tick_id) > tick_id_sort_key(prior):
            last_tick[mech_id] = tick_id
    return {mid: (counts[mid], last_tick.get(mid)) for mid in counts}


def aggregate(
    universe_dir: Path,
    *,
    slug: str,
    author_filter: str | None = None,
    history: bool = False,
) -> MechanicsReport:
    """Build a :class:`MechanicsReport`.

    Args:
        universe_dir: Universe root directory.
        slug: Universe slug (display only).
        author_filter: ``None`` (default), ``"seed"`` or ``"operator"``.
            When set, mechanics that don't match are dropped from the
            output. The author classification still runs for all mechanics
            so call counts remain comparable across filters.

    Returns:
        A populated report. Empty registry => empty mechanics list.
    """
    report = MechanicsReport(slug=slug, author_filter=author_filter)
    mechanics_dir = universe_dir / "mechanics"
    if not mechanics_dir.is_dir():
        return report

    # Local imports keep CLI startup cheap.
    from token_world.inspect.universe import _classify_author
    from token_world.mechanic.registry import MechanicRegistry

    try:
        registry = MechanicRegistry(mechanics_dir, universe_dir=universe_dir)
    except (OSError, ValueError):
        return report

    counts = _scan_call_counts(universe_dir)

    for info in registry.list_mechanics():
        author = _classify_author(info.path, universe_dir)
        call_count, last_tick = counts.get(info.id, (0, None))
        first_commit: str | None = None
        first_ts: str | None = None
        if history:
            first_commit, first_ts = _git_first_commit(universe_dir, str(info.path))
        row = MechanicRow(
            id=info.id,
            description=info.description,
            voluntary=info.voluntary,
            tags=list(info.tags),
            source_path=str(info.path),
            author=author,
            call_count=call_count,
            last_invoked_tick=last_tick,
            first_authored_commit=first_commit,
            first_authored_timestamp=first_ts,
        )
        if author_filter is not None and author != author_filter:
            continue
        report.mechanics.append(row)

    return report


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_table(report: MechanicsReport) -> str:
    """Compact table for terminal viewing."""
    out: list[str] = []
    title = f"=== Mechanics Registry: {report.slug} ==="
    if report.author_filter:
        title += f" (filter: author={report.author_filter})"
    out.append(title)
    if not report.mechanics:
        out.append("(no mechanics matched)")
        return "\n".join(out) + "\n"

    show_history = any(r.first_authored_commit is not None for r in report.mechanics)

    if show_history:
        header = (
            f"{'id':<28} {'voluntary':<10} {'author':<9} {'calls':>6} {'last':>6}"
            f"  {'first_authored':<12} {'commit':<8}  tags  -- description"
        )
    else:
        header = (
            f"{'id':<28} {'voluntary':<10} {'author':<9} {'calls':>6} {'last':>6}"
            "  tags  -- description"
        )
    out.append(header)
    out.append("-" * len(header))
    for row in report.mechanics:
        vol = "yes" if row.voluntary else "no"
        last = row.last_invoked_tick or "-"
        tags = ",".join(row.tags) if row.tags else "-"
        if show_history:
            date_str = (row.first_authored_timestamp or "")[:10] or "-"
            commit_str = (row.first_authored_commit or "")[:8] or "-"
            out.append(
                f"{row.id:<28} {vol:<10} {row.author:<9} "
                f"{row.call_count:>6} {last:>6}"
                f"  {date_str:<12} {commit_str:<8}  {tags}  -- {row.description}"
            )
        else:
            out.append(
                f"{row.id:<28} {vol:<10} {row.author:<9} "
                f"{row.call_count:>6} {last:>6}  {tags}  -- {row.description}"
            )
    return "\n".join(out) + "\n"


def render_json(report: MechanicsReport, *, indent: int | None = 2) -> str:
    """Stable JSON contract."""
    payload: dict[str, Any] = {
        "slug": report.slug,
        "author_filter": report.author_filter,
        "mechanics": [asdict(row) for row in report.mechanics],
    }
    return json.dumps(payload, indent=indent, sort_keys=True) + "\n"
