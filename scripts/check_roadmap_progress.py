#!/usr/bin/env python3
"""ROADMAP Progress table <-> phase PLAN/SUMMARY drift check.

Parses the ``## Progress`` table in `.planning/ROADMAP.md` and compares
each row against the actual state under `.planning/phases/<N>-<name>/`:

- Number of plans ``<X>/<Y>`` should match the PLAN file count.
- Status ``Complete`` should match — every PLAN file has a SUMMARY sibling.
- Status ``In Progress`` should match — at least one PLAN exists but at
  least one SUMMARY is missing.
- Status ``Planning`` should match — no SUMMARY files at all
  (or PLAN count ``0/—`` / ``—/N``).

Exit code 0 on clean, 1 on drift.

Usage:
    uv run python scripts/check_roadmap_progress.py
    uv run python scripts/check_roadmap_progress.py --milestone v1.0

The v1.0 mode runs against `.planning/milestones/v1.0-ROADMAP.md` for
regression checking.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIVE_ROADMAP = REPO_ROOT / ".planning" / "ROADMAP.md"
V1_ROADMAP = REPO_ROOT / ".planning" / "milestones" / "v1.0-ROADMAP.md"
PHASES_DIR = REPO_ROOT / ".planning" / "phases"


@dataclass
class RoadmapRow:
    """One row of the Progress table."""

    phase_id: str
    name: str
    milestone: str
    plans_claimed: tuple[int | None, int | None]  # (complete, total)
    status: str


@dataclass
class DriftReport:
    """Accumulated drift findings."""

    roadmap_path: Path
    count_mismatch: list[tuple[str, str]] = field(default_factory=list)
    status_mismatch: list[tuple[str, str]] = field(default_factory=list)
    phase_dir_missing: list[str] = field(default_factory=list)
    unmentioned_phase_dirs: list[str] = field(default_factory=list)

    def has_drift(self) -> bool:
        return bool(
            self.count_mismatch
            or self.status_mismatch
            or self.phase_dir_missing
            or self.unmentioned_phase_dirs
        )

    def render(self) -> str:
        lines = [
            "=" * 72,
            "ROADMAP Progress table <-> phase directory drift report",
            f"Roadmap:     {self.roadmap_path.relative_to(REPO_ROOT)}",
            f"Phases dir:  {PHASES_DIR.relative_to(REPO_ROOT)}",
            "=" * 72,
        ]
        if not self.has_drift():
            lines.append("OK — no drift detected.")
            return "\n".join(lines)

        if self.count_mismatch:
            lines.append("")
            lines.append("Plan counts in Progress table don't match phase directory:")
            for phase, msg in self.count_mismatch:
                lines.append(f"  - phase {phase}: {msg}")

        if self.status_mismatch:
            lines.append("")
            lines.append("Status in Progress table doesn't match phase directory state:")
            for phase, msg in self.status_mismatch:
                lines.append(f"  - phase {phase}: {msg}")

        if self.phase_dir_missing:
            lines.append("")
            lines.append("Progress table references phase directories that don't exist:")
            for phase in self.phase_dir_missing:
                lines.append(f"  - phase {phase}")

        if self.unmentioned_phase_dirs:
            lines.append("")
            lines.append("Phase directories not mentioned in the Progress table:")
            for name in self.unmentioned_phase_dirs:
                lines.append(f"  - {name}")

        lines.append("")
        lines.append("FAIL — drift detected. Fix the mismatches above.")
        return "\n".join(lines)


# Row examples (both the active and v1.0 flavours):
#   | 0. Universe Infrastructure | v1.0 | 2/2 | Complete | 2026-04-11 |
#   | 08. Emergence Substrate | v1.1 | 3/— | In Progress | ... |
#   | 11. NiceGUI Dashboard | v1.1 | 0/6 | Planning | GSD phase-plan pending |
_ROW_PATTERN = re.compile(
    r"""^\|\s*(?P<id>[\d.]+)\.\s*(?P<name>[^|]+?)\s*\|
        \s*(?P<milestone>[^|]+?)\s*\|
        \s*(?P<plans>[^|]+?)\s*\|
        \s*(?P<status>[^|]+?)\s*\|""",
    re.VERBOSE | re.MULTILINE,
)


def _parse_count(raw: str) -> tuple[int | None, int | None]:
    """``"2/2"`` -> ``(2, 2)``; ``"3/—"`` -> ``(3, None)``; ``"—/6"`` -> ``(None, 6)``.

    The em-dash ``—`` and the en-dash ``–`` and the plain ``-`` are all
    treated as "unknown".
    """
    raw = raw.strip()
    parts = raw.split("/")
    if len(parts) != 2:
        return (None, None)

    def _one(s: str) -> int | None:
        s = s.strip()
        if s in ("—", "–", "-", "", "?"):
            return None
        try:
            return int(s)
        except ValueError:
            return None

    return (_one(parts[0]), _one(parts[1]))


def parse_roadmap(path: Path) -> list[RoadmapRow]:
    """Parse roadmap rows.

    Supports two formats:

    1. **Progress table** (active ROADMAP.md) — rows under ``## Progress``
       with columns: phase | milestone | plans | status | notes.
    2. **Phases section** (v1.0 archive) — ``### Phase N: Name`` blocks
       each with a ``Plans:`` checklist and a ``**Plans:** N`` line.
       Status is inferred from the checklist marks (all [x] = Complete,
       any [x] but not all = In Progress, none = Planning).
    """
    text = path.read_text(encoding="utf-8")
    rows: list[RoadmapRow] = []

    # Format 1: Progress table.
    marker = text.find("## Progress")
    if marker != -1:
        end = text.find("\n## ", marker + 1)
        section = text[marker : end if end != -1 else len(text)]
        for m in _ROW_PATTERN.finditer(section):
            phase_id = m.group("id").rstrip(".")
            rows.append(
                RoadmapRow(
                    phase_id=phase_id,
                    name=m.group("name").strip(),
                    milestone=m.group("milestone").strip(),
                    plans_claimed=_parse_count(m.group("plans")),
                    status=m.group("status").strip(),
                )
            )

    if rows:
        return rows

    # Format 2: Phases section with per-phase checklists (v1.0 archive).
    phase_pattern = re.compile(
        r"^###\s+Phase\s+([\w.]+)\s*[:\-]\s*([^\n]+)$",
        re.MULTILINE,
    )
    matches = list(phase_pattern.finditer(text))
    for idx, head in enumerate(matches):
        phase_id = head.group(1)
        name = head.group(2).strip().rstrip(" *")
        start = head.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[start:end]

        plan_marks = re.findall(
            r"^\s*-\s*\[([ xX])\]\s+[^\s]+-PLAN\.md",
            block,
            re.MULTILINE,
        )
        if not plan_marks:
            continue
        completed = sum(1 for mark in plan_marks if mark.lower() == "x")
        total = len(plan_marks)

        if completed == 0:
            status = "Planning"
        elif completed == total:
            status = "Complete"
        else:
            status = "In Progress"

        rows.append(
            RoadmapRow(
                phase_id=phase_id,
                name=name,
                milestone="(archive)",
                plans_claimed=(completed, total),
                status=status,
            )
        )

    return rows


def _find_phase_dir(phase_id: str) -> Path | None:
    """Locate the phase directory matching ``<phase_id>-*``.

    Returns ``None`` if no directory matches.
    """
    # Normalise: "0" and "00" both map to "00-*" dirs; "04.1" keeps the dot.
    candidates: list[str] = [phase_id] if "." in phase_id else [phase_id, phase_id.zfill(2)]
    for cand in candidates:
        hits = sorted(PHASES_DIR.glob(f"{cand}-*"))
        if hits:
            return hits[0]
    return None


def _phase_plan_summary(dir_path: Path) -> tuple[int, int]:
    """Return ``(summary_count, plan_count)`` for the phase dir."""
    plans = sorted(dir_path.glob("*-PLAN.md"))
    summaries = sorted(dir_path.glob("*-SUMMARY.md"))
    return (len(summaries), len(plans))


def _inferred_status(summary_count: int, plan_count: int) -> str:
    if plan_count == 0:
        return "Planning"
    if summary_count == 0:
        return "Planning"
    if summary_count < plan_count:
        return "In Progress"
    return "Complete"


def build_report(roadmap_path: Path) -> DriftReport:
    rows = parse_roadmap(roadmap_path)
    report = DriftReport(roadmap_path=roadmap_path)
    is_archive = "milestones" in roadmap_path.parts

    mentioned_phase_ids: set[str] = set()
    for row in rows:
        mentioned_phase_ids.add(row.phase_id)
        # Also register the zero-padded form for unmentioned-dir matching
        mentioned_phase_ids.add(row.phase_id.zfill(2) if "." not in row.phase_id else row.phase_id)
        dir_path = _find_phase_dir(row.phase_id)
        if dir_path is None:
            # Retroactive-phasing tolerance: a row whose phase dir doesn't
            # exist yet is the known-acceptable "ship in direct mode,
            # scaffold dir later" pattern (e.g. v1.1 phase 09/10/12 rows
            # land before any PLAN.md is written). Only flag when the row
            # claims Complete progress.
            if row.status.lower() in ("in progress", "planning"):
                continue
            report.phase_dir_missing.append(row.phase_id)
            continue

        summary_count, plan_count = _phase_plan_summary(dir_path)
        claimed_complete, claimed_total = row.plans_claimed

        # Retroactive-phasing tolerance: if the row says "In Progress"
        # but the dir has zero PLANs / zero SUMMARYs, this is the
        # known-acceptable "ship in direct mode, scaffold phase later"
        # pattern. Don't flag — the v1.1 ROADMAP rows for phases 08/09/10
        # were committed before the phase plans were retroactively landed.
        is_retroactive_skeleton = (
            plan_count == 0
            and summary_count == 0
            and row.status.lower() in ("in progress", "planning")
        )
        if is_retroactive_skeleton:
            continue

        # Planning-stage tolerance: a phase whose row says "Planning"
        # may have 1+ PLAN files in flight (planning underway). Skip
        # the count + status checks while in this transient state. Only
        # SUMMARY count > 0 would mean the row is actually wrong.
        if row.status.lower() == "planning" and summary_count == 0:
            continue

        # Count mismatch: compare when both sides are known.
        if claimed_complete is not None and claimed_complete != summary_count:
            report.count_mismatch.append(
                (
                    row.phase_id,
                    f"row says {claimed_complete}/{claimed_total} complete; "
                    f"dir has {summary_count} SUMMARY files",
                )
            )
        if claimed_total is not None and claimed_total != plan_count:
            report.count_mismatch.append(
                (
                    row.phase_id,
                    f"row says total={claimed_total} plans; dir has {plan_count} PLAN files",
                )
            )

        # Status mismatch.
        inferred = _inferred_status(summary_count, plan_count)
        if row.status.lower() != inferred.lower():
            # Tolerate "In Progress" rows for phases whose plan count
            # doesn't yet reach claimed_total (retroactive phasing).
            if (
                inferred == "Complete"
                and row.status.lower() == "in progress"
                and (claimed_total is None or claimed_complete != claimed_total)
            ):
                continue
            report.status_mismatch.append(
                (
                    row.phase_id,
                    f"row says {row.status!r}; dir implies {inferred!r} "
                    f"({summary_count}/{plan_count})",
                )
            )

    # Archive mode only checks phases mentioned in the archive — newer
    # phases (08+) are not the archive's concern. Active mode checks all
    # non-skeleton phase dirs.
    if not is_archive:
        all_dirs = sorted(p for p in PHASES_DIR.iterdir() if p.is_dir())
        for d in all_dirs:
            m = re.match(r"^(\d+(?:\.\d+)?)-", d.name)
            if not m:
                continue
            phase_id = m.group(1)
            normalised = phase_id.lstrip("0") or "0"
            if phase_id in mentioned_phase_ids or normalised in mentioned_phase_ids:
                continue
            # Skip empty/skeleton dirs (no PLAN/SUMMARY files yet)
            summary_count, plan_count = _phase_plan_summary(d)
            if summary_count == 0 and plan_count == 0:
                continue
            report.unmentioned_phase_dirs.append(d.name)

    return report


def run(milestone: str) -> int:
    if milestone == "active":
        roadmap_path = ACTIVE_ROADMAP
    elif milestone == "v1.0":
        roadmap_path = V1_ROADMAP
    else:
        raise SystemExit(f"unknown milestone: {milestone}")

    if not roadmap_path.exists():
        print(f"ROADMAP file not found: {roadmap_path}", file=sys.stderr)
        return 2
    if not PHASES_DIR.exists():
        print(f"phases directory missing: {PHASES_DIR}", file=sys.stderr)
        return 2

    report = build_report(roadmap_path)
    print(report.render())
    return 1 if report.has_drift() else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--milestone",
        default="active",
        choices=["active", "v1.0"],
        help="Which ROADMAP to check (default: active)",
    )
    args = parser.parse_args()
    return run(args.milestone)


if __name__ == "__main__":
    raise SystemExit(main())
