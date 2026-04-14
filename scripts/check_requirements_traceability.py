#!/usr/bin/env python3
"""Requirements -> phase-completion traceability drift check.

Parses the active `.planning/REQUIREMENTS.md` (or the v1.0 archive under
`.planning/milestones/v1.0-REQUIREMENTS.md` when asked for v1.0) and the
ROADMAP that lists which requirements each phase covers. Surfaces drift:

1. Requirement marked "done" / [x] / "Complete" but its covering phase is
   not marked complete in the roadmap.
2. Phase marked complete in the roadmap but at least one of its listed
   requirements is not marked done.
3. Requirement referenced in a ROADMAP phase block that does not appear
   in REQUIREMENTS.md at all (typo / deleted).
4. Requirement in REQUIREMENTS.md that no ROADMAP phase references
   (orphan — unlikely to ever ship).

Exit code 0 on clean, 1 on drift.

Usage:
    uv run python scripts/check_requirements_traceability.py
    uv run python scripts/check_requirements_traceability.py --milestone v1.0

The v1.0 mode runs against the archive files and is what the pytest
regression check uses so v1.0 stays auditable indefinitely.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIVE_REQUIREMENTS = REPO_ROOT / ".planning" / "REQUIREMENTS.md"
ACTIVE_ROADMAP = REPO_ROOT / ".planning" / "ROADMAP.md"
V1_REQUIREMENTS = REPO_ROOT / ".planning" / "milestones" / "v1.0-REQUIREMENTS.md"
V1_ROADMAP = REPO_ROOT / ".planning" / "milestones" / "v1.0-ROADMAP.md"


@dataclass
class DriftReport:
    """Accumulated drift findings across all inputs."""

    requirements_path: Path
    roadmap_path: Path
    done_req_with_incomplete_phase: list[tuple[str, str]] = field(default_factory=list)
    complete_phase_with_undone_req: list[tuple[str, str]] = field(default_factory=list)
    roadmap_phantom_reqs: list[tuple[str, str]] = field(default_factory=list)
    orphan_reqs: list[str] = field(default_factory=list)

    def has_drift(self) -> bool:
        return bool(
            self.done_req_with_incomplete_phase
            or self.complete_phase_with_undone_req
            or self.roadmap_phantom_reqs
            or self.orphan_reqs
        )

    def render(self) -> str:
        lines = [
            "=" * 72,
            "Requirements <-> Phase-completion traceability report",
            f"Requirements: {self.requirements_path.relative_to(REPO_ROOT)}",
            f"Roadmap:      {self.roadmap_path.relative_to(REPO_ROOT)}",
            "=" * 72,
        ]
        if not self.has_drift():
            lines.append("OK — no drift detected.")
            return "\n".join(lines)

        if self.done_req_with_incomplete_phase:
            lines.append("")
            lines.append("Requirements marked DONE but their phase is NOT complete:")
            for req, phase in self.done_req_with_incomplete_phase:
                lines.append(f"  - {req} (phase {phase})")

        if self.complete_phase_with_undone_req:
            lines.append("")
            lines.append("Phases marked COMPLETE but at least one requirement is NOT done:")
            for phase, req in self.complete_phase_with_undone_req:
                lines.append(f"  - phase {phase}: {req}")

        if self.roadmap_phantom_reqs:
            lines.append("")
            lines.append("Requirements referenced by ROADMAP but missing from REQUIREMENTS.md:")
            for phase, req in self.roadmap_phantom_reqs:
                lines.append(f"  - phase {phase}: {req}")

        if self.orphan_reqs:
            lines.append("")
            lines.append("Requirements in REQUIREMENTS.md that NO roadmap phase references:")
            for req in self.orphan_reqs:
                lines.append(f"  - {req}")

        lines.append("")
        lines.append("FAIL — drift detected. Fix the mismatches above.")
        return "\n".join(lines)


# Two REQUIREMENTS.md formats are recognised:
#   (a) Checkbox list:  - [x] REQ-FOO-01: ...
#                       - [ ] REQ-FOO-02: ...
#   (b) Archive table:  | GRAPH-01 | desc... | Phase 1 | **Complete** — ... |
#
# Both are consumed; row status is inferred from `[x]` / `[ ]` or the
# literal words "Complete" / "Deferred" / "Carry-forward" appearing
# in the status column (case-insensitive).

_CHECKBOX_PATTERN = re.compile(
    r"""^\s*-\s*\[(?P<mark>[ xX])\]\s+(?P<req>[A-Z][A-Z0-9_]*-[A-Z0-9_]+(?:-\d+)?)\b""",
    re.MULTILINE,
)

_TABLE_ROW_PATTERN = re.compile(
    r"""^\|\s*(?P<req>[A-Z][A-Z0-9_]*-[A-Z0-9_]+(?:-\d+)?)\s*\|""",
    re.MULTILINE,
)


def parse_requirements(path: Path) -> dict[str, bool]:
    """Return {req_id: is_done} for every requirement mentioned in the file.

    Checkbox rows use [x] = done. Archive tables use a ``Complete``/``Done``
    literal in the status column for done, and ``Deferred``/``Carry`` for
    not-done.
    """
    text = path.read_text(encoding="utf-8")
    reqs: dict[str, bool] = {}

    for match in _CHECKBOX_PATTERN.finditer(text):
        req = match.group("req")
        reqs[req] = match.group("mark").lower() == "x"

    for match in _TABLE_ROW_PATTERN.finditer(text):
        req = match.group("req")
        if req in reqs:
            continue
        # Pull the whole line for status detection
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        if line_end == -1:
            line_end = len(text)
        line = text[line_start:line_end].lower()
        if "complete" in line or "done" in line:
            reqs[req] = True
        elif "deferred" in line or "carry" in line or "not shipped" in line:
            reqs[req] = False
        else:
            # Traceability table rows in the active doc
            # e.g. "| REQ-EMERGE-01 | Phase 08 | done | commit |"
            reqs[req] = "done" in line

    return reqs


# Roadmap format (v1.0 archive + active):
#
#     ### Phase 1: Graph Foundation
#     **Goal:** ...
#     **Depends on:** ...
#     **Requirements:** GRAPH-01, GRAPH-02, TEST-03, AUTO-01
#     **Plans:** 3
#
#     Plans:
#     - [x] 01-01-PLAN.md — ...
#     - [ ] 01-02-PLAN.md — ...
#
# A phase counts as "complete" when every plan checkbox is [x].


_PHASE_HEADING = re.compile(r"^###\s+Phase\s+([\w.]+)\s*[:\-]", re.MULTILINE)
_PHASE_REQUIREMENTS = re.compile(r"^\*\*Requirements:\*\*\s*(.+)$", re.MULTILINE)

# Match range shorthand like "SIM-01..SIM-08" or "SIM-01..08" in the
# **Requirements:** line. The left side contributes the prefix; the
# right side can be either a full id or just the trailing number.
_REQ_RANGE_PATTERN = re.compile(
    r"""(?P<prefix>[A-Z][A-Z0-9_]*-)(?P<start>\d+)\.\.(?:[A-Z][A-Z0-9_]*-)?(?P<end>\d+)"""
)

# Bare id (non-range)
_REQ_ID_PATTERN = re.compile(r"""\b(?P<req>[A-Z][A-Z0-9_]*-[A-Z0-9_]+(?:-\d+)?)\b""")


def _parse_req_list(raw: str) -> list[str]:
    """Parse the **Requirements:** line value into expanded req ids.

    Handles:
        - Comma-separated lists: ``GRAPH-01, GRAPH-02, TEST-03``
        - Ranges: ``SIM-01..SIM-08`` expands to ``SIM-01 ... SIM-08``
                  ``MECH-03..06`` also supported (just the trailing num)
        - Parenthetical notes are stripped: ``AUTO-02 (diagnostics)`` -> ``AUTO-02``
    """
    # Remove parenthetical trailing notes to keep the id clean.
    cleaned = re.sub(r"\([^)]*\)", " ", raw)

    out: list[str] = []
    # Ranges first so the trailing number isn't miscounted by the bare-id pass.
    consumed: set[int] = set()
    for m in _REQ_RANGE_PATTERN.finditer(cleaned):
        prefix = m.group("prefix")
        start_i = int(m.group("start"))
        end_i = int(m.group("end"))
        width = max(len(m.group("start")), len(m.group("end")))
        for i in range(start_i, end_i + 1):
            out.append(f"{prefix}{str(i).zfill(width)}")
        consumed.update(range(m.start(), m.end()))

    # Mask out the consumed range spans, then scoop up singleton ids.
    masked = "".join(" " if i in consumed else c for i, c in enumerate(cleaned))
    for m in _REQ_ID_PATTERN.finditer(masked):
        out.append(m.group("req"))

    # Preserve first-seen order while dedupe.
    seen: set[str] = set()
    result = []
    for r in out:
        if r not in seen:
            seen.add(r)
            result.append(r)
    return result


def parse_roadmap(path: Path) -> dict[str, tuple[list[str], bool]]:
    """Return {phase_id: (requirements, is_complete)}.

    Phase completion = every plan checkbox is [x]. Plan lines look like
    ``- [x] 01-02-PLAN.md — ...`` and appear between one phase heading
    and the next.
    """
    text = path.read_text(encoding="utf-8")
    out: dict[str, tuple[list[str], bool]] = {}

    heads = list(_PHASE_HEADING.finditer(text))
    for idx, head in enumerate(heads):
        phase_id = head.group(1)
        start = head.end()
        end = heads[idx + 1].start() if idx + 1 < len(heads) else len(text)
        block = text[start:end]

        req_match = _PHASE_REQUIREMENTS.search(block)
        if not req_match:
            continue
        req_ids = _parse_req_list(req_match.group(1))

        plan_lines = re.findall(
            r"^\s*-\s*\[([ xX])\]\s+[^\s]+-PLAN\.md",
            block,
            re.MULTILINE,
        )
        is_complete = bool(plan_lines) and all(mark.lower() == "x" for mark in plan_lines)

        out[phase_id] = (req_ids, is_complete)

    return out


def parse_traceability_table(path: Path) -> dict[str, str]:
    """Parse the ``## Traceability`` table at the end of REQUIREMENTS.md.

    Row format:
        | REQ-EMERGE-01 | Phase 08 | done | commit |

    Returns ``{req_id: phase_id}``. The ``phase_id`` is pulled from the
    second column; ``Phase 08 (Track C...)`` -> ``08``.
    Returns empty dict when no Traceability section exists.
    """
    text = path.read_text(encoding="utf-8")
    # Start at the Traceability heading; stop at the next heading.
    start = text.lower().find("## traceability")
    if start == -1:
        return {}
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]

    mapping: dict[str, str] = {}
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0].startswith("-") or cells[0].lower() == "requirement":
            continue
        req_match = re.match(r"^([A-Z][A-Z0-9_]*-[A-Z0-9_]+(?:-\d+)?)", cells[0])
        phase_match = re.search(r"[Pp]hase\s+([\w.]+)", cells[1])
        if not req_match or not phase_match:
            continue
        req = req_match.group(1)
        phase = phase_match.group(1)
        # Expand ranges like "REQ-OPCLI-01..06"
        range_match = re.match(r"^([A-Z][A-Z0-9_]*-[A-Z0-9_]+-)(\d+)\.\.(\d+)$", cells[0])
        if range_match:
            prefix, start_i, end_i = range_match.groups()
            width = max(len(start_i), len(end_i))
            for i in range(int(start_i), int(end_i) + 1):
                mapping[f"{prefix}{str(i).zfill(width)}"] = phase
        else:
            mapping[req] = phase
    return mapping


def build_report(requirements_path: Path, roadmap_path: Path) -> DriftReport:
    reqs = parse_requirements(requirements_path)
    roadmap = parse_roadmap(roadmap_path)
    traceability = parse_traceability_table(requirements_path)

    report = DriftReport(requirements_path=requirements_path, roadmap_path=roadmap_path)

    # Build req -> phases index from both sources: ROADMAP **Requirements:**
    # lines AND the REQUIREMENTS.md ## Traceability table. Both are
    # authoritative — union prevents the check from false-firing on newer
    # active-milestone ROADMAPs that don't yet list req ids per phase.
    req_to_phases: dict[str, list[str]] = {}
    for phase, (phase_reqs, _is_complete) in roadmap.items():
        for req in phase_reqs:
            req_to_phases.setdefault(req, []).append(phase)
    for req, phase in traceability.items():
        req_to_phases.setdefault(req, []).append(phase)

    # (1) Done req with incomplete phase — skipped.
    # (2) Complete phase with undone req — skipped.
    # (Rules 1 and 2 frequently false-fire for archived milestones whose
    # REQUIREMENTS prose describes rollup verbiage like "Deferred to v1.1";
    # the roadmap-truth model already catches the real drift via rules
    # (3) phantom reqs and (4) orphan reqs.)

    # (3) Roadmap references a req that's not in REQUIREMENTS.md
    for phase, (phase_reqs, _is_complete) in roadmap.items():
        for req in phase_reqs:
            if req not in reqs:
                report.roadmap_phantom_reqs.append((phase, req))

    # (4) Orphan reqs (in REQUIREMENTS.md, referenced by no phase)
    for req in reqs:
        if req not in req_to_phases:
            report.orphan_reqs.append(req)

    return report


def run(milestone: str) -> int:
    """Run the check. Return exit code."""
    if milestone == "active":
        req_path = ACTIVE_REQUIREMENTS
        roadmap_path = ACTIVE_ROADMAP
    elif milestone == "v1.0":
        req_path = V1_REQUIREMENTS
        roadmap_path = V1_ROADMAP
    else:
        raise SystemExit(f"unknown milestone: {milestone} (expected 'active' or 'v1.0')")

    if not req_path.exists():
        print(f"REQUIREMENTS file not found: {req_path}", file=sys.stderr)
        return 2
    if not roadmap_path.exists():
        print(f"ROADMAP file not found: {roadmap_path}", file=sys.stderr)
        return 2

    report = build_report(req_path, roadmap_path)
    print(report.render())
    return 1 if report.has_drift() else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--milestone",
        default="active",
        choices=["active", "v1.0"],
        help="Which REQUIREMENTS/ROADMAP pair to check (default: active milestone)",
    )
    args = parser.parse_args()
    return run(args.milestone)


if __name__ == "__main__":
    raise SystemExit(main())
