#!/usr/bin/env python3
"""annotate_use_case_outcomes -- insert ``expected_outcome`` into every
.planning/use-cases/**/UC-*.md manifest per Phase-4 Plan 04-04 Task 3.

Heuristic (from 04-04-PLAN):

* If the UC's ``gaps`` list contains ANY gap with
  ``layer: engine`` AND ``severity: address-now`` -> ``blocked``.
* Else -> ``yield``.
* A hard-coded allowlist of UC ids is unconditionally marked ``blocked``
  per GAP-ANALYSIS + D-38 (see BLOCKED_OVERRIDES below).

Idempotent: if ``expected_outcome`` already matches the intended value
the manifest is not rewritten. Otherwise the field is inserted on the
line immediately after ``status:`` (or replaced in-place if already
present there).

Usage:
    uv run python scripts/annotate_use_case_outcomes.py [--dry-run]

Exits 0 and prints a one-line-per-manifest summary.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
USE_CASES_DIR = REPO_ROOT / ".planning" / "use-cases"

# Unconditional blocked overrides: UCs whose primary dependency is a
# Phase-5 engine-layer framework extension (per 04-04-PLAN Step A step 3
# and GAP-ANALYSIS cross-references).
BLOCKED_OVERRIDES = {"UC-E01", "UC-E02", "UC-E04", "UC-E05", "UC-O06"}


def _classify(fm: dict) -> str:
    uc_id = fm.get("id")
    if uc_id in BLOCKED_OVERRIDES:
        return "blocked"
    for gap in fm.get("gaps") or []:
        if not isinstance(gap, dict):
            continue
        if gap.get("layer") == "engine" and gap.get("severity") == "address-now":
            return "blocked"
    return "yield"


def _rewrite(path: Path, outcome: str) -> str:
    """Insert or replace ``expected_outcome`` in *path*'s frontmatter.

    Returns one of ``'unchanged' | 'inserted' | 'replaced'``.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("status:"):
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            if next_line.strip().lower().startswith("expected_outcome:"):
                existing = next_line.split(":", 1)[1].strip()
                if existing == outcome:
                    return "unchanged"
                lines[i + 1] = f"expected_outcome: {outcome}"
                path.write_text("\n".join(lines), encoding="utf-8")
                return "replaced"
            lines.insert(i + 1, f"expected_outcome: {outcome}")
            path.write_text("\n".join(lines), encoding="utf-8")
            return "inserted"
    raise ValueError(f"{path}: no 'status:' line in frontmatter")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify but do not rewrite manifests.",
    )
    args = parser.parse_args()

    # Deferred import so the script prints a sensible error if the
    # project isn't installed.
    from token_world.use_cases.loader import load_use_case

    counts = {"yield": 0, "blocked": 0, "unchanged": 0, "inserted": 0, "replaced": 0}
    for path in sorted(USE_CASES_DIR.rglob("UC-*.md")):
        fm, _body = load_use_case(path)
        outcome = _classify(fm)
        counts[outcome] += 1
        if args.dry_run:
            print(f"DRY  {path.relative_to(REPO_ROOT)}: -> {outcome}")
            continue
        action = _rewrite(path, outcome)
        counts[action] += 1
        print(f"{action:9s} {path.relative_to(REPO_ROOT)} -> {outcome}")

    print(
        f"\nSummary: yield={counts['yield']} blocked={counts['blocked']} "
        f"(unchanged={counts['unchanged']} "
        f"inserted={counts['inserted']} replaced={counts['replaced']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
