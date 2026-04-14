#!/usr/bin/env python3
"""Phase 6 UAT harness — runs all 3 live UAT items end-to-end.

Encapsulates the manual UAT flow documented in
`.planning/phases/06-resident-agent-end-to-end-loop/06-VERIFICATION.md`
(§Live UAT Results) so it is one command instead of an error-prone
seven-step manual sequence:

    1. Create test universe if it doesn't exist
    2. Live playtest, write report, print verdict
    3. Edit classifier prompt by 1 char, replay, assert regression triggers,
       revert classifier, restore prompt-hash baseline
    4. Live playtest with --judge, assert judge block populated
    5. Print pass/fail per item + overall verdict

All runs route through the Phase 07.1 ``ClaudeCLIBackend``
(``TOKEN_WORLD_BACKEND=claude-cli``) for zero marginal LLM cost.

Usage:
    uv run python scripts/run_uat.py <slug>
    uv run python scripts/run_uat.py uatworld
    uv run python scripts/run_uat.py uatworld --turns 5

Exit code 0 if all 3 pass; 1 if any fail.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Where token-world stores universes (XDG-style under ~/.local/share)
UNIVERSE_HOME = Path.home() / ".local" / "share" / "token_world" / "universes"


@dataclass
class ItemResult:
    """One UAT item outcome."""

    name: str
    passed: bool
    detail: str


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with text mode, capturing stdout/stderr."""
    return subprocess.run(
        cmd,
        cwd=kwargs.pop("cwd", REPO_ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TOKEN_WORLD_BACKEND": "claude-cli", **kwargs.pop("env_extra", {})},
        **kwargs,
    )


def ensure_universe(slug: str) -> None:
    """Create the test universe if it does not already exist."""
    universe_dir = UNIVERSE_HOME / slug
    if universe_dir.exists():
        print(f"[setup] universe {slug!r} exists at {universe_dir}")
        return
    print(f"[setup] creating universe {slug!r}")
    result = _run(["uv", "run", "token-world", "create", slug])
    if result.returncode != 0:
        raise RuntimeError(
            f"failed to create universe {slug!r}:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )


def item1_playtest(slug: str, turns: int, output: Path) -> ItemResult:
    """UAT 1 — vanilla 5-turn playtest with personality-coherent text."""
    print(f"[item1] playtest {slug} --turns {turns}")
    result = _run(
        [
            "uv",
            "run",
            "token-world",
            "playtest",
            slug,
            "--turns",
            str(turns),
            "--no-operator",
            "--output",
            str(output),
        ]
    )
    if result.returncode != 0:
        return ItemResult(
            name="item1_playtest",
            passed=False,
            detail=(
                f"playtest exited {result.returncode}\n"
                f"STDOUT: {result.stdout[-500:]}\n"
                f"STDERR: {result.stderr[-500:]}"
            ),
        )
    if not output.exists():
        return ItemResult(name="item1_playtest", passed=False, detail=f"no report at {output}")
    report = json.loads(output.read_text(encoding="utf-8"))
    turn_count = len(report.get("turns", []))
    if turn_count < 1:
        return ItemResult(
            name="item1_playtest",
            passed=False,
            detail=f"report has {turn_count} turns; expected >= 1",
        )
    return ItemResult(
        name="item1_playtest",
        passed=True,
        detail=f"{turn_count} turns; aggregate composite "
        f"{report.get('aggregate_scores', {}).get('composite', '?')}",
    )


def item2_prompt_change(slug: str, turns: int) -> ItemResult:
    """UAT 2 — modify classifier prompt, expect regression trigger, then revert."""
    classifier_path = REPO_ROOT / "src" / "token_world" / "engine" / "classifier.py"
    print(f"[item2] mutating {classifier_path.name} to trigger prompt-hash change")
    original = classifier_path.read_text(encoding="utf-8")
    sentinel = "no prose."

    if sentinel not in original:
        return ItemResult(
            name="item2_prompt_change",
            passed=False,
            detail=f"sentinel {sentinel!r} not found in classifier.py — re-anchor the test",
        )

    mutated = original.replace(sentinel, sentinel + " ", 1)
    try:
        classifier_path.write_text(mutated, encoding="utf-8")
        result = _run(
            [
                "uv",
                "run",
                "token-world",
                "playtest",
                slug,
                "--turns",
                str(turns),
                "--no-operator",
            ]
        )
    finally:
        classifier_path.write_text(original, encoding="utf-8")
        # Restore baseline hash so subsequent runs aren't tripped by the revert
        update_script = REPO_ROOT / "scripts" / "update_prompt_hashes.py"
        if update_script.exists():
            _run(["uv", "run", "python", str(update_script), slug])

    if "Prompt change detected" in result.stdout or "Prompt change detected" in result.stderr:
        return ItemResult(
            name="item2_prompt_change",
            passed=True,
            detail="prompt-hash regression trigger fired and prompt was reverted",
        )
    return ItemResult(
        name="item2_prompt_change",
        passed=False,
        detail=(
            "expected 'Prompt change detected' in playtest output; not seen.\n"
            f"STDOUT tail: {result.stdout[-500:]}\n"
            f"STDERR tail: {result.stderr[-500:]}"
        ),
    )


def item3_judge(slug: str, turns: int, output: Path) -> ItemResult:
    """UAT 3 — playtest with --judge; expect a populated judge block in the report."""
    print(f"[item3] playtest {slug} --turns {turns} --judge")
    result = _run(
        [
            "uv",
            "run",
            "token-world",
            "playtest",
            slug,
            "--turns",
            str(turns),
            "--no-operator",
            "--judge",
            "--output",
            str(output),
        ]
    )
    if result.returncode != 0:
        return ItemResult(
            name="item3_judge",
            passed=False,
            detail=(
                f"playtest --judge exited {result.returncode}\n"
                f"STDOUT: {result.stdout[-500:]}\nSTDERR: {result.stderr[-500:]}"
            ),
        )
    if not output.exists():
        return ItemResult(name="item3_judge", passed=False, detail=f"no report at {output}")
    report = json.loads(output.read_text(encoding="utf-8"))
    judge = report.get("judge")
    if not isinstance(judge, dict):
        return ItemResult(name="item3_judge", passed=False, detail="report has no 'judge' block")
    scores = judge.get("scores")
    if not isinstance(scores, dict) or not scores:
        return ItemResult(
            name="item3_judge",
            passed=False,
            detail=f"judge.scores missing or empty: {scores!r}",
        )
    return ItemResult(
        name="item3_judge",
        passed=True,
        detail=f"judge model={judge.get('model', '?')}; scores={list(scores.keys())}",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="Universe slug (created if missing)")
    parser.add_argument(
        "--turns",
        type=int,
        default=3,
        help="Turns per playtest (default: 3 — fast UAT)",
    )
    parser.add_argument(
        "--keep-universe",
        action="store_true",
        help="Don't delete the universe after the run",
    )
    args = parser.parse_args()

    if not shutil.which("claude"):
        print(
            "ERROR: `claude` CLI not found on PATH — required for claude-cli backend",
            file=sys.stderr,
        )
        return 2

    try:
        ensure_universe(args.slug)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    out_dir = Path("/tmp")
    results = [
        item1_playtest(args.slug, args.turns, out_dir / f"uat1_{args.slug}.json"),
        item2_prompt_change(args.slug, args.turns),
        item3_judge(args.slug, args.turns, out_dir / f"uat3_{args.slug}.json"),
    ]

    print("\n" + "=" * 72)
    print("Phase 6 UAT — Verdict")
    print("=" * 72)
    for r in results:
        flag = "PASS" if r.passed else "FAIL"
        print(f"  [{flag}] {r.name}: {r.detail}")
    print("=" * 72)

    overall_pass = all(r.passed for r in results)
    verdict = "PASS — all 3 items green" if overall_pass else "FAIL — at least one item red"
    print(f"Overall: {verdict}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
