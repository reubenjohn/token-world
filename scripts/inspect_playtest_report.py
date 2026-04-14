#!/usr/bin/env python3
"""Inspect a playtest report JSON for key fields: turns, personality, scores, judge.

Usage: uv run python scripts/inspect_playtest_report.py <path/to/report.json>

Used during Phase 6 live UAT to validate PlaytestReport structure from
claude-cli backend runs. Prints a compact summary suitable for human review.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def inspect(report_path: Path) -> int:
    if not report_path.exists():
        print(f"Report not found: {report_path}", file=sys.stderr)
        return 1

    data = json.loads(report_path.read_text())

    print(f"=== Playtest Report: {report_path} ===")
    print(f"schema_version:        {data.get('schema_version', 'MISSING')}")
    print(f"run_id:                {data.get('run_id', 'MISSING')}")
    turns = data.get("turns") or []
    print(f"turns:                 {len(turns)}")
    print(f"duration_ms:           {data.get('duration_ms', 'N/A')}")
    print(f"scenario_file:         {data.get('scenario_file', 'None')}")
    print(f"prompts_sha256 keys:   {sorted((data.get('prompts_sha256') or {}).keys())}")

    agg = data.get("aggregate_scores") or {}
    if agg:
        print("aggregate_scores:")
        for k, v in agg.items():
            if isinstance(v, float):
                print(f"  {k:28s} {v:.3f}")
            else:
                print(f"  {k:28s} {v}")

    if turns:
        first = turns[0]
        print("\n-- First turn preview --")
        print(f"first turn keys:       {sorted(first.keys())}")
        action_text = first.get("action_text") or first.get("action") or ""
        print(f"action_text (first 200 chars): {action_text[:200]!r}")
        classification = first.get("classification") or {}
        if classification:
            print(f"classification.kind:   {classification.get('kind', 'N/A')}")
        obs = first.get("observation") or ""
        print(f"observation (first 200 chars): {obs[:200]!r}")
        scores = first.get("scores") or {}
        if scores:
            print("first turn scores:")
            for k, v in scores.items():
                if isinstance(v, float):
                    print(f"  {k:28s} {v:.3f}")
                else:
                    print(f"  {k:28s} {v}")

    judge = data.get("judge")
    if judge is not None:
        print("\n-- Judge block --")
        print(f"judge.model:           {judge.get('model', 'N/A')}")
        j_scores = judge.get("scores") or {}
        if j_scores:
            print("judge.scores:")
            for k, v in j_scores.items():
                print(f"  {k:28s} {v}")
        rationale = judge.get("rationale", "")
        if rationale:
            print(f"judge.rationale (first 200): {rationale[:200]!r}")
    else:
        print("\n-- No judge block (run without --judge) --")

    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: inspect_playtest_report.py <path>", file=sys.stderr)
        sys.exit(2)
    sys.exit(inspect(Path(sys.argv[1])))
