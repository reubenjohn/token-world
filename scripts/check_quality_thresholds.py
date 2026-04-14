#!/usr/bin/env python3
"""Simulation quality threshold gate.

Loads quality scores for the last --window ticks of a universe and exits
non-zero if any dimension is in the FAIL (red) range.

Usage:
    uv run python scripts/check_quality_thresholds.py <slug>
    uv run python scripts/check_quality_thresholds.py <slug> --window 50

Exit 0: all dimensions OK or WARN (HEALTHY or DEGRADED verdict).
Exit 0: INSUFFICIENT_DATA verdict (not enough ticks — skip gate).
Exit 1: any dimension FAIL or universe not found.

Wired into pytest via tests/test_meta/test_quality_thresholds.py.
See docs/quality/sim-quality-rubric.md for threshold values.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Quality threshold gate for Token World simulation runs."
    )
    parser.add_argument("slug", help="Universe slug to score.")
    parser.add_argument(
        "--window",
        type=int,
        default=50,
        help="Number of most-recent ticks to score (default 50).",
    )
    args = parser.parse_args()

    # Import here so the script stays importable even before the quality
    # subpackage is installed (import error → exit 1 with clear message).
    try:
        from token_world.quality import score
        from token_world.universe.manager import UniverseManager
    except ImportError as exc:
        print(f"ERROR: cannot import token_world.quality — {exc}", file=sys.stderr)
        return 1

    manager = UniverseManager()
    try:
        universe_dir = manager.load(args.slug)
    except FileNotFoundError as exc:
        print(f"ERROR: universe not found — {exc}", file=sys.stderr)
        return 1

    report = score(universe_dir, slug=args.slug, last=args.window)

    # Print the full scorecard to stdout regardless of verdict.
    from token_world.quality.report import render_table

    print(render_table(report))

    if report.verdict == "INSUFFICIENT_DATA":
        print(
            "WARNING: insufficient tick data for quality scoring — skipping gate.",
            file=sys.stderr,
        )
        return 0  # don't fail CI on empty universes

    failing = [d for d in report.dimensions if d.status == "FAIL"]
    if failing:
        print(
            f"\nQUALITY GATE FAILED — {len(failing)} dimension(s) in red range:",
            file=sys.stderr,
        )
        for dim in failing:
            print(f"  [{dim.status}] {dim.name}: {dim.detail}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
