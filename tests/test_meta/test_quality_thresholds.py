"""Quality threshold gate: pytest-wired CI invariant.

Invokes scripts/check_quality_thresholds.py against synthetic fixture
universes. Script must exit 0 on a healthy fixture (all dimensions OK or
WARN with no FAILs), and exit 1 on a fixture engineered to breach a
threshold.

This test does NOT run against real universe data (SC-4 is verified
manually before merge). It uses fixture universes written to tmp_path,
isolated via XDG_DATA_HOME so UniverseManager resolves to tmp_path.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_quality_thresholds.py"


def _init_universe_db(universe_dir: Path) -> None:
    """Create a minimal universe.db so UniverseManager.load() accepts the slug."""
    db_path = universe_dir / "universe.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )


def _write_tick(
    path: Path,
    tick_num: int,
    *,
    refused: bool = False,
    mutations_count: int = 1,
    action_text: str = "pick up apple",
    refusal_reason: str | None = None,
    mechanic_id: str | None = None,
) -> None:
    """Write a synthetic tick summary JSON to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "tick_id": f"tick_{tick_num}",
        "timestamp_iso": "2026-01-01T00:00:00Z",
        "action_text": action_text,
        "classified_action": None,
        "matched_mechanic_id": mechanic_id or f"mechanic_{tick_num % 3}",
        "yielded": False,
        "refused": refused,
        "refusal_reason": refusal_reason,
        "mutations": {
            "count": 0 if refused else mutations_count,
            "list": [["chest", "locked", True, False]] * (0 if refused else mutations_count),
        },
        "observation_text": "You open the chest.",
        "duration_ms": 100,
        "llm_tokens_by_stage": {},
        "llm_cost_usd_by_stage": {},
    }
    path.write_text(json.dumps(payload))


@pytest.fixture()
def healthy_universe(tmp_path: Path) -> tuple[Path, str]:
    """Fixture: 20 clean ticks — should produce exit 0."""
    xdg_home = tmp_path / "xdg_home"
    slug = "healthy_test"
    universe_dir = xdg_home / "token_world" / "universes" / slug
    universe_dir.mkdir(parents=True)
    _init_universe_db(universe_dir)
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    for i in range(1, 21):
        _write_tick(
            ticks_dir / f"tick_{i}.json",
            i,
            mutations_count=1,
            mechanic_id=f"m_{i % 5}",
        )
    return xdg_home, slug


@pytest.fixture()
def failing_universe(tmp_path: Path) -> tuple[Path, str]:
    """Fixture: all refused ticks — should produce exit 1 (action coherence FAIL)."""
    xdg_home = tmp_path / "xdg_home"
    slug = "failing_test"
    universe_dir = xdg_home / "token_world" / "universes" / slug
    universe_dir.mkdir(parents=True)
    _init_universe_db(universe_dir)
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    for i in range(1, 21):
        _write_tick(ticks_dir / f"tick_{i}.json", i, refused=True)
    return xdg_home, slug


def _run_script(xdg_home: Path, slug: str, window: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "python", str(SCRIPT), slug, "--window", str(window)],
        cwd=REPO_ROOT,
        env={**os.environ, "XDG_DATA_HOME": str(xdg_home)},
        capture_output=True,
        text=True,
    )


def test_healthy_fixture_exits_zero(healthy_universe: tuple[Path, str]) -> None:
    """A well-behaved fixture universe passes the CI gate."""
    xdg_home, slug = healthy_universe
    result = _run_script(xdg_home, slug)
    assert result.returncode == 0, (
        f"Expected exit 0 for healthy fixture:\n{result.stdout}\n{result.stderr}"
    )


def test_failing_fixture_exits_nonzero(failing_universe: tuple[Path, str]) -> None:
    """A degenerate fixture universe fails the CI gate with a named dimension."""
    xdg_home, slug = failing_universe
    result = _run_script(xdg_home, slug)
    assert result.returncode == 1, (
        f"Expected exit 1 for failing fixture:\n{result.stdout}\n{result.stderr}"
    )
    # Must name the failing dimension(s) in stderr (case-insensitive)
    stderr_lower = result.stderr.lower()
    assert "action coherence" in stderr_lower or "action_coherence" in stderr_lower, (
        f"Expected named dimension in stderr:\n{result.stderr}"
    )


def test_missing_universe_exits_nonzero(tmp_path: Path) -> None:
    """Non-existent slug exits 1 with an error message."""
    xdg_home = tmp_path / "xdg_home"
    xdg_home.mkdir()
    result = subprocess.run(
        ["uv", "run", "python", str(SCRIPT), "ghost_universe_that_does_not_exist"],
        cwd=REPO_ROOT,
        env={**os.environ, "XDG_DATA_HOME": str(xdg_home)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    stderr_lower = result.stderr.lower()
    assert "not found" in stderr_lower or "error" in stderr_lower
