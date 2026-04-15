"""Backfill pre-REQ-V12-ENGINE-01 false-EXECUTED tick summaries.

Before ENGINE-01, the engine would execute a mechanic whose check() failed and
return a 0-mutation observation instead of refusing the action. These ticks were
recorded as executed (refused=false, mutations.count=0) but are semantically
refusals — the mechanic's precondition wasn't met.

The quality scorer's Groundedness dimension penalises such ticks as "ungrounded"
because they lack mutations, a refusal flag, or a yield flag. This script backfills
them with refused=true, refusal_reason="mechanic_check_failed" so the scorer treats
them correctly (mechanic_check_failed refusals are scored like OK per §E6).

Usage:
    uv run python scripts/migrate_tick_summaries.py <slug> --dry-run
    uv run python scripts/migrate_tick_summaries.py <slug> --apply
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap: ensure project src is importable when run without `uv run`
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))


def _is_false_executed(tick: dict[str, Any]) -> bool:
    """Return True if this tick is a pre-ENGINE-01 false-EXECUTED record.

    Criteria (all must hold):
    - status field absent OR not "refused"/"yielded"  (old ticks have no status field)
    - refused == False (or absent)
    - yielded == False (or absent)
    - mutations.count == 0
    - mechanic_check_failed absent or False in refusal_reason
    """
    refused = tick.get("refused", False)
    yielded = tick.get("yielded", False)
    mutations_count = tick.get("mutations", {}).get("count", 0)
    refusal_reason = tick.get("refusal_reason") or ""

    if refused:
        return False  # already marked refused — idempotent skip
    if yielded:
        return False
    if mutations_count > 0:
        return False
    return "mechanic_check_failed" not in refusal_reason


def _apply_fix(tick: dict[str, Any]) -> dict[str, Any]:
    """Return a new tick dict with the false-EXECUTED fields corrected."""
    fixed = dict(tick)
    fixed["refused"] = True
    fixed["refusal_reason"] = "mechanic_check_failed"
    # Keep status field as-is for backward compat; scorer uses refused flag not status
    return fixed


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically via temp file in same directory."""
    dir_ = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=str(dir_), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, str(path))
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def run(slug: str, *, dry_run: bool, universe_dir: Path | None = None) -> int:
    """Main migration logic. Returns count of affected ticks.

    Args:
        slug: Universe slug passed to UniverseManager.load().
        dry_run: If True, print table but do not write files.
        universe_dir: Override universe directory (used in tests to skip UniverseManager).
    """
    from token_world.inspect._shared import iter_tick_files, read_json_file

    if universe_dir is None:
        from token_world.universe.manager import UniverseManager

        universe_dir = UniverseManager().load(slug)

    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    files = iter_tick_files(ticks_dir)

    if not files:
        print(f"No tick files found in {ticks_dir}")
        return 0

    affected: list[tuple[Path, dict[str, Any]]] = []
    for f in files:
        data = read_json_file(f)
        if data is None:
            continue
        if _is_false_executed(data):
            affected.append((f, data))

    if not affected:
        print("No false-EXECUTED ticks found — nothing to migrate.")
        return 0

    # Print table header
    col_w = 10
    print(f"{'Tick ID':<{col_w}}  {'Mechanic':<20}  {'Action (truncated)':<40}  {'Proposed fix'}")
    print("-" * 95)
    for path, tick in affected:
        tick_id = tick.get("tick_id", path.stem)
        mechanic = tick.get("matched_mechanic_id") or "(none)"
        action = (tick.get("action_text") or "")[:40].replace("\n", " ")
        fix = "refused=true, refusal_reason=mechanic_check_failed"
        print(f"{tick_id:<{col_w}}  {mechanic:<20}  {action:<40}  {fix}")

    print()
    if dry_run:
        print(f"[dry-run] Would rewrite {len(affected)} tick(s). Pass --apply to commit changes.")
    else:
        for path, tick in affected:
            fixed = _apply_fix(tick)
            _atomic_write(path, fixed)
            print(f"  Rewrote {path.name}")
        print(f"\nMigration complete: {len(affected)} tick(s) updated.")

    return len(affected)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Backfill pre-ENGINE-01 false-EXECUTED tick summaries."
    )
    parser.add_argument("slug", help="Universe slug (e.g. willowbrook)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Show affected ticks without writing any files.",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Atomically rewrite affected tick files.",
    )
    args = parser.parse_args()

    count = run(args.slug, dry_run=args.dry_run)
    sys.exit(0 if count >= 0 else 1)


if __name__ == "__main__":
    main()
