"""Validate all seed mechanics pass the AST + contract pipeline.

Usage: uv run python scripts/check_seed_mechanics.py
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

from token_world.mechanic.validation import validate


def main() -> int:
    paths = glob.glob("src/token_world/mechanic/seeds/*.py")
    paths = [
        p
        for p in paths
        if not Path(p).name.startswith("_") and Path(p).name != "__init__.py"
    ]
    reports = [validate(Path(p)) for p in paths]
    bad = [(p, r) for p, r in zip(paths, reports) if not r.passed]
    if bad:
        for path, report in bad:
            print(f"FAIL: {path}", file=sys.stderr)
            for finding in report.findings:
                if finding.severity == "error":
                    print(f"  {finding.stage}: {finding.message}", file=sys.stderr)
        return 1
    print(f"all {len(paths)} seeds pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
