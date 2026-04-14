"""Planning-doc invariant: ROADMAP Progress matches phase PLAN/SUMMARY counts.

Guards against the v1.0 drift root cause — manual ``Plans Complete``
counts diverging from the actual checklist state. See
:mod:`scripts.check_roadmap_progress` for the CLI variant.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_roadmap_progress.py"


@pytest.mark.parametrize(
    "milestone",
    ["v1.0", "active"],
    ids=["archived-v1.0", "active-milestone"],
)
def test_no_progress_drift(milestone: str) -> None:
    """Script exits 0 when there's no progress-table drift; non-zero otherwise.

    ``v1.0`` is the archived milestone; ``active`` is the currently-open
    milestone. Both are expected to be clean at every commit.
    """
    result = subprocess.run(
        ["uv", "run", "python", str(SCRIPT), "--milestone", milestone],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Roadmap progress drift for milestone={milestone}:\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
