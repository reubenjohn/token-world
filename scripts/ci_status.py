#!/usr/bin/env python3
"""CI run summary — list runs since a SHA / tag with green/red + failure links.

Replaces the manual ``gh run list -L 20`` then-eyeball-each-row dance.
Calls into ``gh run list`` and ``gh run view`` and emits a compact
multi-row report with per-job pass/fail and links to failing job logs.

Usage:
    uv run python scripts/ci_status.py                # since latest tag (v1.0)
    uv run python scripts/ci_status.py --since v1.0   # since explicit ref
    uv run python scripts/ci_status.py --since HEAD~5 # since SHA / ref
    uv run python scripts/ci_status.py --branch master --limit 10
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass


def _run_gh(args: list[str]) -> str:
    """Run a gh command, return stdout as a string. Exits 2 on failure."""
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(
            f"ERROR: `gh {' '.join(args)}` failed (exit {proc.returncode}):\n{proc.stderr}",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return proc.stdout


@dataclass
class RunRow:
    """One row from `gh run list`."""

    run_id: str
    workflow: str
    status: str
    conclusion: str
    sha: str
    headline: str
    url: str


def list_runs(branch: str, limit: int) -> list[RunRow]:
    """Return up to ``limit`` recent CI runs for ``branch``."""
    raw = _run_gh(
        [
            "run",
            "list",
            "--branch",
            branch,
            "--limit",
            str(limit),
            "--json",
            "databaseId,workflowName,status,conclusion,headSha,displayTitle,url",
        ]
    )
    data = json.loads(raw)
    rows = []
    for r in data:
        rows.append(
            RunRow(
                run_id=str(r.get("databaseId", "?")),
                workflow=r.get("workflowName", "?"),
                status=r.get("status", "?"),
                conclusion=r.get("conclusion") or "—",
                sha=str(r.get("headSha", "?"))[:7],
                headline=r.get("displayTitle", "")[:60],
                url=r.get("url", ""),
            )
        )
    return rows


def filter_since(rows: list[RunRow], since_ref: str | None) -> list[RunRow]:
    """Filter rows to commits in ``git rev-list since_ref..HEAD``.

    When ``since_ref`` is None, return all rows.
    """
    if since_ref is None:
        return rows
    proc = subprocess.run(
        ["git", "rev-list", f"{since_ref}..HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(
            f"WARNING: `git rev-list {since_ref}..HEAD` failed; returning all rows",
            file=sys.stderr,
        )
        return rows
    keep_shas = {sha[:7] for sha in proc.stdout.split() if sha}
    if not keep_shas:
        # `since_ref` may BE the head — return only rows for HEAD
        head_proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if head_proc.returncode == 0:
            keep_shas = {head_proc.stdout.strip()}
    return [r for r in rows if r.sha in keep_shas]


def per_run_failed_jobs(run_id: str) -> list[tuple[str, str]]:
    """Return (job_name, job_url) for each failed job in the run."""
    raw = _run_gh(
        [
            "run",
            "view",
            run_id,
            "--json",
            "jobs",
        ]
    )
    data = json.loads(raw)
    return [
        (j.get("name", "?"), j.get("url", ""))
        for j in data.get("jobs", [])
        if j.get("conclusion") == "failure"
    ]


def render(rows: Iterable[RunRow]) -> None:
    print(f"{'workflow':18}  {'sha':8}  {'status':10}  {'conclusion':10}  headline")
    print("-" * 100)
    for r in rows:
        print(f"{r.workflow:18}  {r.sha:8}  {r.status:10}  {r.conclusion:10}  {r.headline}")

    print()
    failed = [r for r in rows if r.conclusion == "failure"]
    if not failed:
        print("All shown runs are green.")
        return
    print("Failed jobs:")
    for r in failed:
        print(f"\n  {r.workflow} ({r.sha}) — {r.url}")
        for name, url in per_run_failed_jobs(r.run_id):
            print(f"    [{name}] {url}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--since",
        default=None,
        help="Show runs for commits in `since..HEAD` (default: all in --limit window)",
    )
    parser.add_argument("--branch", default="master", help="Branch to query (default: master)")
    parser.add_argument("--limit", type=int, default=20, help="Max runs to list (default: 20)")
    args = parser.parse_args()

    rows = list_runs(args.branch, args.limit)
    rows = filter_since(rows, args.since)

    if not rows:
        print(f"No CI runs found for branch={args.branch} since={args.since!r}")
        return 0

    render(rows)
    failed_runs = [r for r in rows if r.conclusion == "failure"]
    return 1 if failed_runs else 0


if __name__ == "__main__":
    raise SystemExit(main())
