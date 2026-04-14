"""Planning-doc invariant: REQUIREMENTS.md <-> ROADMAP/Traceability stay aligned.

Guards against the v1.0 drift root cause — manual checkbox updates
diverging from phase completion. See
:mod:`scripts.check_requirements_traceability` for the CLI variant.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_requirements_traceability.py"


@pytest.mark.parametrize(
    "milestone",
    ["v1.0", "active"],
    ids=["archived-v1.0", "active-milestone"],
)
def test_no_traceability_drift(milestone: str) -> None:
    """Script exits 0 when there's no drift; non-zero otherwise.

    ``v1.0`` is the archived milestone and should remain auditable
    indefinitely. ``active`` is the currently-open milestone and is
    expected to pass whenever a planning change lands.
    """
    result = subprocess.run(
        ["uv", "run", "python", str(SCRIPT), "--milestone", milestone],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Requirements traceability drift for milestone={milestone}:\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
