"""Regression: src/token_world/graph/ must be mypy-clean.

UAT gap 03-UAT#3: `save_snapshot` and `list_snapshots` leaked Any-typed
sqlite returns; this test fails fast if a new Any leaks in.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest


@pytest.mark.skipif(shutil.which("mypy") is None, reason="mypy not installed")
def test_graph_module_is_mypy_clean() -> None:
    result = subprocess.run(
        ["mypy", "src/token_world/graph/"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"mypy failed on src/token_world/graph/:\n"
        f"--- STDOUT ---\n{result.stdout}\n"
        f"--- STDERR ---\n{result.stderr}"
    )
