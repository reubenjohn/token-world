#!/usr/bin/env python3
"""Phase information dumper — print CONTEXT, PLAN titles, SUMMARY headlines, VERIFICATION status.

Replaces the manual "ls then cat each file" dance for inspecting a phase
directory. Handles both integer phase IDs (``5``, ``07``) and decimal
inserted phases (``04.1``, ``07.1``).

Usage:
    uv run python scripts/phase_show.py 04.1
    uv run python scripts/phase_show.py 5

Output sections:
    1. CONTEXT.md (full body, headers visible)
    2. <phase>-NN-PLAN.md titles (h1 / h2 only, no body)
    3. <phase>-NN-SUMMARY.md headlines (h1 / h2 only, no body)
    4. VERIFICATION.md status (frontmatter status: line + score)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PHASES_DIR = REPO_ROOT / ".planning" / "phases"


def find_phase_dir(phase_id: str) -> Path | None:
    """Locate the phase directory matching ``<phase_id>-*``.

    Tries the exact id first, then a zero-padded form for single-digit
    integer ids (``5`` -> ``05``).
    """
    candidates = [phase_id] if "." in phase_id else [phase_id, phase_id.zfill(2)]
    for cand in candidates:
        hits = sorted(PHASES_DIR.glob(f"{cand}-*"))
        if hits:
            return hits[0]
    return None


def _print_section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def render_context(phase_dir: Path, phase_id: str) -> None:
    _print_section(f"CONTEXT — {phase_id}")
    ctx_files = sorted(phase_dir.glob("*-CONTEXT.md"))
    if not ctx_files:
        print(f"(no CONTEXT.md found in {phase_dir.name})")
        return
    for ctx in ctx_files:
        print(ctx.read_text(encoding="utf-8"))


def render_plan_titles(phase_dir: Path, phase_id: str) -> None:
    _print_section(f"PLAN titles — {phase_id}")
    plans = sorted(phase_dir.glob("*-PLAN.md"))
    if not plans:
        print("(no PLAN files)")
        return
    for plan in plans:
        text = plan.read_text(encoding="utf-8")
        # First h1 / h2 lines
        lines = text.splitlines()[:50]
        h1 = next((line for line in lines if line.startswith("# ")), None)
        h2s = [line for line in lines if line.startswith("## ")][:5]
        print(f"\n[{plan.name}]")
        if h1:
            print(f"  {h1}")
        for h in h2s:
            print(f"    {h}")


def render_summary_headlines(phase_dir: Path, phase_id: str) -> None:
    _print_section(f"SUMMARY headlines — {phase_id}")
    summaries = sorted(phase_dir.glob("*-SUMMARY.md"))
    if not summaries:
        print("(no SUMMARY files yet — phase not executed)")
        return
    for summary in summaries:
        text = summary.read_text(encoding="utf-8")
        lines = text.splitlines()[:80]
        h1 = next((line for line in lines if line.startswith("# ")), None)
        h2s = [line for line in lines if line.startswith("## ")][:5]
        print(f"\n[{summary.name}]")
        if h1:
            print(f"  {h1}")
        for h in h2s:
            print(f"    {h}")


def render_verification(phase_dir: Path, phase_id: str) -> None:
    _print_section(f"VERIFICATION — {phase_id}")
    vf_files = sorted(phase_dir.glob("*-VERIFICATION.md"))
    if not vf_files:
        print("(no VERIFICATION.md — phase not yet verified)")
        return
    for vf in vf_files:
        text = vf.read_text(encoding="utf-8")
        # Pull the frontmatter block (between two `---` lines at top).
        fm_match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        print(f"\n[{vf.name}]")
        if fm_match:
            for line in fm_match.group(1).splitlines():
                line_strip = line.strip()
                if line_strip.startswith(("status:", "score:", "verified:", "resolved:")):
                    print(f"  {line_strip}")
        else:
            print("  (no YAML frontmatter)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase_id", help="Phase id (e.g. 5, 07.1, 04.1)")
    args = parser.parse_args()

    phase_dir = find_phase_dir(args.phase_id)
    if phase_dir is None:
        print(f"ERROR: no phase directory matches {args.phase_id!r}", file=sys.stderr)
        print("Available phases:", file=sys.stderr)
        for p in sorted(PHASES_DIR.iterdir()):
            if p.is_dir():
                print(f"  {p.name}", file=sys.stderr)
        return 2

    print(f"Phase directory: {phase_dir.relative_to(REPO_ROOT)}")
    render_context(phase_dir, args.phase_id)
    render_plan_titles(phase_dir, args.phase_id)
    render_summary_headlines(phase_dir, args.phase_id)
    render_verification(phase_dir, args.phase_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
