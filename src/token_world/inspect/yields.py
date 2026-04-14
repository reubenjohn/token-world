"""Pending-yield inspector (``token-world yield <slug>``).

Reads the operator inbox (``<universe>/operator_inbox/``) and surfaces
every yield file that has not yet been resolved — i.e. a ``<tick>.yield.json``
exists but neither a sibling ``.resolved`` nor ``.rejected`` marker does.

Design notes
------------

- Pure read-only. Never mutates inbox files. (The ``operator`` subpackage is
  the sole writer; this module is a passive consumer.)
- Pure-stdlib aggregation. No Anthropic SDK import — consistent with the rest
  of ``inspect/``.
- Graceful degradation — a missing ``operator_inbox/`` directory produces an
  empty report, never a crash (universes that have never yielded won't have
  one).
- Dual rendering — ``render_table`` / ``render_json`` siblings (uniform with
  every other inspect module).
- The on-disk shape is ``YieldSignal.to_json()`` (see
  :mod:`token_world.operator.yield_signal`); we parse with the same loader so
  any schema drift surfaces loudly rather than silently.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

__all__ = [
    "PendingYield",
    "YieldsReport",
    "aggregate",
    "find_pending_yields",
    "load_yield_file",
    "render_json",
    "render_table",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PendingYield:
    """One unresolved yield in the operator inbox."""

    tick_id: str
    verb: str | None
    actor: str | None
    target: str | None
    action_text: str
    hint: str
    mtime_iso: str
    path: str  # absolute path to the .yield.json file


@dataclass(slots=True)
class YieldsReport:
    """Aggregate report for pending (and optionally single-tick) yields."""

    slug: str
    pending: list[PendingYield] = field(default_factory=list)
    not_found_tick: str | None = None  # set when --tick T passed but no such yield


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


def _inbox_dir(universe_dir: Path) -> Path:
    return universe_dir / "operator_inbox"


def _is_resolved(inbox: Path, tick_id: str) -> bool:
    """True iff a ``.resolved`` or ``.rejected`` sibling marker exists."""
    return (inbox / f"{tick_id}.resolved").exists() or (inbox / f"{tick_id}.rejected").exists()


def load_yield_file(path: Path) -> PendingYield | None:
    """Parse a single ``<tick>.yield.json`` into a :class:`PendingYield`.

    Returns ``None`` on malformed JSON or an unexpected top-level shape.
    The tick id is pulled from the filename (not from the payload) so that a
    payload with a mismatching ``tick_id`` field still shows up under the
    filename the operator is staring at on disk.
    """
    if not path.is_file():
        return None
    tick_id = path.name.removesuffix(".yield.json")
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    classified = data.get("classified_action")
    if not isinstance(classified, dict):
        classified = {}
    verb = classified.get("verb") if isinstance(classified.get("verb"), str) else None
    actor = classified.get("actor") if isinstance(classified.get("actor"), str) else None
    target_val = classified.get("target")
    target = target_val if isinstance(target_val, str) else None

    action_text_val = data.get("action_text", "")
    action_text = action_text_val if isinstance(action_text_val, str) else ""

    # Hint: prefer an explicit "hint" field if the emitter ever adds one;
    # otherwise fall back to the yield `reason`. Keeps the banner useful today
    # while leaving room for the engine to enrich the payload later.
    hint_raw = data.get("hint")
    if isinstance(hint_raw, str) and hint_raw.strip():
        hint: str = hint_raw
    else:
        reason = data.get("reason")
        hint = reason if isinstance(reason, str) else "no_mechanic_for_action"

    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    mtime_iso = datetime.fromtimestamp(mtime, tz=UTC).isoformat()

    return PendingYield(
        tick_id=tick_id,
        verb=verb,
        actor=actor,
        target=target,
        action_text=action_text,
        hint=hint,
        mtime_iso=mtime_iso,
        path=str(path),
    )


def find_pending_yields(universe_dir: Path) -> list[PendingYield]:
    """Return every unresolved yield in ``<universe>/operator_inbox``.

    Ordered by file mtime ascending (oldest first) — this matches the order
    the external orchestrator would work through them. The dashboard banner
    re-sorts by "most recent" for its "latest pending" display.

    A missing inbox directory returns an empty list.
    """
    inbox = _inbox_dir(universe_dir)
    if not inbox.is_dir():
        return []
    pending: list[PendingYield] = []
    for entry in sorted(inbox.glob("*.yield.json")):
        tick_id = entry.name.removesuffix(".yield.json")
        if _is_resolved(inbox, tick_id):
            continue
        py = load_yield_file(entry)
        if py is not None:
            pending.append(py)
    pending.sort(key=lambda p: p.mtime_iso)
    return pending


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


def aggregate(
    universe_dir: Path,
    *,
    slug: str,
    tick_id: str | None = None,
) -> YieldsReport:
    """Build a :class:`YieldsReport`.

    Args:
        universe_dir: Universe root directory.
        slug: Universe slug (display only).
        tick_id: When set, return only that single yield (pending or not).
            Populates ``not_found_tick`` when the yield file doesn't exist.
    """
    report = YieldsReport(slug=slug)
    inbox = _inbox_dir(universe_dir)

    if tick_id is not None:
        y_path = inbox / f"{tick_id}.yield.json"
        if not y_path.is_file():
            report.not_found_tick = tick_id
            return report
        py = load_yield_file(y_path)
        if py is not None:
            report.pending.append(py)
        else:
            report.not_found_tick = tick_id
        return report

    report.pending = find_pending_yields(universe_dir)
    return report


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _fmt_action(py: PendingYield) -> str:
    verb = py.verb or "?"
    actor = py.actor or "?"
    target = py.target or "-"
    return f"{verb} {actor} -> {target}"


def render_table(report: YieldsReport) -> str:
    out: list[str] = []
    out.append(f"=== Pending yields: {report.slug} ===")
    if report.not_found_tick is not None:
        out.append(f"(no yield file for tick {report.not_found_tick!r})")
        return "\n".join(out) + "\n"
    if not report.pending:
        out.append("(inbox empty — no pending yields)")
        return "\n".join(out) + "\n"

    out.append(f"({len(report.pending)} pending)")
    for py in report.pending:
        out.append("")
        out.append(f"  tick {py.tick_id}")
        out.append(f"    action: {_fmt_action(py)}")
        if py.action_text:
            text = py.action_text.strip().split("\n", 1)[0]
            if len(text) > 80:
                text = text[:77] + "..."
            out.append(f"    text:   {text!r}")
        out.append(f"    hint:   {py.hint}")
        out.append(f"    mtime:  {py.mtime_iso}")
    return "\n".join(out) + "\n"


def render_json(report: YieldsReport, *, indent: int | None = 2) -> str:
    payload: dict[str, Any] = {
        "slug": report.slug,
        "not_found_tick": report.not_found_tick,
        "pending": [asdict(p) for p in report.pending],
    }
    return json.dumps(payload, indent=indent, sort_keys=True, default=str) + "\n"
