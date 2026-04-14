#!/usr/bin/env python3
"""Extract the source-file scope for a GSD phase.

Reads `key_files.created` and `key_files.modified` from every `*-SUMMARY.md`
in the phase directory, applies the gsd-code-review exclusions (planning
artifacts, lockfiles, top-level docs/), and emits a deduplicated, sorted list
of *existing* source files — one per line on stdout.

If no SUMMARY.md provides files, falls back to `git diff --name-only` between
the parent of the earliest phase commit and HEAD.

Usage:
    python scripts/gsd_phase_files.py 04.1
    python scripts/gsd_phase_files.py 05 --include-docs

Designed to be the single source of truth for "what changed in this phase"
across review/audit/security flows. Replaces ad-hoc inline node parsing in
gsd-code-review and gsd-secure-phase workflows.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PHASES_DIR = Path(".planning/phases")

# File-path patterns to exclude from review scope (orchestrator artifacts).
EXCLUDE_PREFIXES = (".planning/",)
EXCLUDE_SUFFIXES = (
    "-SUMMARY.md",
    "-VERIFICATION.md",
    "-PLAN.md",
    "-REVIEW.md",
    "-CONTEXT.md",
    "-RESEARCH.md",
    "-VALIDATION.md",
)
EXCLUDE_EXACT = {
    "ROADMAP.md",
    "STATE.md",
    "package-lock.json",
    "yarn.lock",
    "Gemfile.lock",
    "poetry.lock",
    "uv.lock",
}


def find_phase_dir(phase_arg: str) -> Path:
    """Locate the phase directory whose name starts with the phase prefix."""
    candidates = sorted(PHASES_DIR.glob(f"{phase_arg}-*"))
    if not candidates:
        sys.exit(f"Error: no phase directory matching '{phase_arg}-*' in {PHASES_DIR}")
    if len(candidates) > 1:
        sys.exit(f"Error: multiple phase directories matched '{phase_arg}-*': {candidates}")
    return candidates[0]


def extract_files_from_summary(summary_path: Path) -> list[str]:
    """Pull `key_files.created` + `key_files.modified` lists from YAML frontmatter.

    Uses PyYAML for parsing so multi-line strings, quoted values, and nested
    structures don't trip up the extractor. Looks under `key_files`, with a
    fallback to top-level `created`/`modified` keys if the schema differs.
    """
    import yaml

    text = summary_path.read_text()
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return []
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return []

    files: list[str] = []
    # Schema variants seen in the wild: `key_files`, `key-files`, or
    # bare top-level `created`/`modified` (legacy). All accepted.
    for parent_key in ("key_files", "key-files"):
        bucket = data.get(parent_key)
        if isinstance(bucket, dict):
            for sub in ("created", "modified"):
                entries = bucket.get(sub)
                if isinstance(entries, list):
                    files.extend(str(e) for e in entries if isinstance(e, str))
    for sub in ("created", "modified"):
        entries = data.get(sub)
        if isinstance(entries, list):
            files.extend(str(e) for e in entries if isinstance(e, str))
    return files


def git_diff_fallback(phase_arg: str) -> list[str]:
    """Find files changed in commits whose message contains the padded phase number."""
    log = subprocess.run(
        ["git", "log", "--all", f"--grep={phase_arg}", "--format=%H"],
        capture_output=True,
        text=True,
        check=False,
    )
    commits = [c for c in log.stdout.splitlines() if c.strip()]
    if not commits:
        return []
    base = commits[-1] + "^"
    # Verify base exists; fall back to first commit itself if root.
    rev = subprocess.run(["git", "rev-parse", base], capture_output=True, text=True, check=False)
    if rev.returncode != 0:
        base = commits[-1]
    diff = subprocess.run(
        ["git", "diff", "--name-only", f"{base}..HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return [f for f in diff.stdout.splitlines() if f.strip()]


def filter_scope(paths: list[str], include_docs: bool) -> list[str]:
    """Apply exclusion rules and keep only files that still exist on disk."""
    seen: set[str] = set()
    kept: list[str] = []
    for path in paths:
        if path in EXCLUDE_EXACT:
            continue
        if any(path.startswith(p) for p in EXCLUDE_PREFIXES):
            continue
        if any(path.endswith(s) for s in EXCLUDE_SUFFIXES):
            continue
        if not include_docs and path.startswith("docs/"):
            continue
        if path in seen:
            continue
        if not Path(path).is_file():
            continue
        seen.add(path)
        kept.append(path)
    return sorted(kept)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", help="Phase number prefix (e.g. '04.1', '05')")
    parser.add_argument(
        "--include-docs",
        action="store_true",
        help="Include docs/ paths (default: excluded — they're prose, not source)",
    )
    args = parser.parse_args()

    phase_dir = find_phase_dir(args.phase)
    summaries = sorted(phase_dir.glob("*-SUMMARY.md"))

    collected: list[str] = []
    for summary in summaries:
        collected.extend(extract_files_from_summary(summary))

    if not collected:
        collected = git_diff_fallback(args.phase)

    for path in filter_scope(collected, args.include_docs):
        print(path)


if __name__ == "__main__":
    main()
