"""Report phase wave structure and detect files_modified overlap across plans.

Usage:
    uv run python scripts/phase_waves.py <phase>

Shells out to `gsd-tools phase-plan-index` and summarises:
  - wave → plan IDs
  - incomplete plans
  - intra-wave files_modified overlap (plans in same wave that touch the
    same file cannot run in parallel without worktree conflicts)

This exists because /gsd-execute-phase's orchestrator needs a reviewable,
reproducible check instead of one-off bash pipelines. See CLAUDE.md
"ad-hoc bash is a missing-tool signal".
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

GSD_TOOLS = Path.home() / ".claude/get-shit-done/bin/gsd-tools.cjs"


def load_index(phase: str) -> dict:
    result = subprocess.run(
        ["node", str(GSD_TOOLS), "phase-plan-index", phase],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def report_wave_overlap(plans_in_wave: list[dict]) -> dict[str, list[str]]:
    """Return {file_path: [plan_ids]} for files touched by 2+ plans in the wave."""
    file_to_plans: dict[str, list[str]] = defaultdict(list)
    for plan in plans_in_wave:
        for path in plan["files_modified"]:
            file_to_plans[path].append(plan["id"])
    return {f: ids for f, ids in file_to_plans.items() if len(ids) > 1}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: phase_waves.py <phase>", file=sys.stderr)
        return 2
    phase = sys.argv[1]
    index = load_index(phase)

    plans_by_id = {p["id"]: p for p in index["plans"]}
    waves: dict[str, list[str]] = index["waves"]
    incomplete = set(index["incomplete"])

    print(f"# Phase {index['phase']} — wave structure")
    print()
    for wave_num in sorted(waves.keys(), key=int):
        plan_ids = waves[wave_num]
        todo = [pid for pid in plan_ids if pid in incomplete]
        print(f"## Wave {wave_num} — {len(plan_ids)} plan(s), {len(todo)} incomplete")
        for pid in plan_ids:
            mark = " " if pid in incomplete else "x"
            plan = plans_by_id[pid]
            print(
                f"  [{mark}] {pid}: {plan['task_count']} tasks, {len(plan['files_modified'])} files"
            )
        if len(plan_ids) > 1:
            overlap = report_wave_overlap(
                [plans_by_id[pid] for pid in plan_ids if pid in incomplete]
            )
            if overlap:
                print(f"  OVERLAP: wave must run SEQUENTIALLY — {len(overlap)} shared file(s):")
                for path, ids in sorted(overlap.items()):
                    print(f"    - {path}  ({', '.join(sorted(ids))})")
            else:
                print("  OK: no files_modified overlap — safe to run in parallel")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
