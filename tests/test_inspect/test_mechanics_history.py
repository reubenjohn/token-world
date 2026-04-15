"""Tests for MechanicRow git history fields and --history flag (SC-2)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from token_world.inspect.mechanics import MechanicRow, aggregate, render_json, render_table

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MECHANIC_MODULE = '''"""test mechanic"""
from __future__ import annotations
from typing import TYPE_CHECKING
from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class TestMech_walk(Mechanic):
    id = "walk"
    description = "walk somewhere"
    voluntary = True
    tags: list[str] = []

    def check(self, ctx: "MechanicContext") -> CheckResult:
        return CheckResult(passed=True)

    def apply(self, ctx: "MechanicContext") -> list[Mutation]:
        return []
'''


def _init_git_repo(repo_dir: Path) -> None:
    """Create a minimal git repo with user identity."""
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=repo_dir, check=True, capture_output=True
    )


def _git_commit(repo_dir: Path, message: str, files: list[Path]) -> str:
    """Stage files and create a commit. Returns full commit hash."""
    for f in files:
        subprocess.run(["git", "add", str(f)], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", message],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# test_history_fields_populated
# ---------------------------------------------------------------------------


def test_history_fields_populated(tmp_path: Path) -> None:
    """Git history fields are populated when history=True and commits exist."""
    # Set up a universe directory structure inside a git repo
    universe_dir = tmp_path
    _init_git_repo(universe_dir)

    mechanics_dir = universe_dir / "mechanics"
    mechanics_dir.mkdir()

    mech_file = mechanics_dir / "walk.py"
    mech_file.write_text(_MECHANIC_MODULE, encoding="utf-8")

    # First (older) commit
    first_hash = _git_commit(universe_dir, "add walk mechanic", [mech_file])

    # Second (newer) commit — modify the file
    mech_file.write_text(_MECHANIC_MODULE + "\n# updated\n", encoding="utf-8")
    _git_commit(universe_dir, "update walk mechanic", [mech_file])

    report = aggregate(universe_dir, slug="t", history=True)
    assert len(report.mechanics) == 1
    row = report.mechanics[0]

    assert row.first_authored_commit is not None
    # Should be the older (first) commit
    assert row.first_authored_commit == first_hash[:40]
    assert row.first_authored_timestamp is not None


# ---------------------------------------------------------------------------
# test_no_history_flag_no_subprocess
# ---------------------------------------------------------------------------


def test_no_history_flag_no_subprocess(tmp_path: Path) -> None:
    """When history=False (default), no subprocess.run call is made."""
    mechanics_dir = tmp_path / "mechanics"
    mechanics_dir.mkdir()
    (mechanics_dir / "walk.py").write_text(_MECHANIC_MODULE, encoding="utf-8")

    with patch("token_world.inspect.mechanics.subprocess") as mock_sp:
        aggregate(tmp_path, slug="t", history=False)
        mock_sp.run.assert_not_called()


# ---------------------------------------------------------------------------
# test_missing_git_graceful
# ---------------------------------------------------------------------------


def test_missing_git_graceful(tmp_path: Path) -> None:
    """No git repo → fields are None, no exception raised."""
    mechanics_dir = tmp_path / "mechanics"
    mechanics_dir.mkdir()
    (mechanics_dir / "walk.py").write_text(_MECHANIC_MODULE, encoding="utf-8")

    # tmp_path has no git repo, so git log returns empty
    report = aggregate(tmp_path, slug="t", history=True)
    assert len(report.mechanics) == 1
    row = report.mechanics[0]
    assert row.first_authored_commit is None
    assert row.first_authored_timestamp is None


# ---------------------------------------------------------------------------
# test_render_table_shows_columns_when_populated
# ---------------------------------------------------------------------------


def test_render_table_shows_columns_when_populated() -> None:
    """Extra columns appear in render_table when history fields are populated."""
    from token_world.inspect.mechanics import MechanicsReport

    row = MechanicRow(
        id="walk",
        description="walk somewhere",
        voluntary=True,
        tags=[],
        source_path="/fake/mechanics/walk.py",
        author="seed",
        call_count=3,
        last_invoked_tick="5",
        first_authored_commit="abcdef1234567890",
        first_authored_timestamp="2026-01-15T10:00:00+00:00",
    )
    report = MechanicsReport(slug="t", mechanics=[row])
    out = render_table(report)
    assert "2026-01-15" in out
    assert "abcdef12" in out


# ---------------------------------------------------------------------------
# test_render_json_includes_null_fields
# ---------------------------------------------------------------------------


def test_render_json_includes_null_fields(tmp_path: Path) -> None:
    """render_json always includes first_authored_commit/timestamp (null when history=False)."""
    mechanics_dir = tmp_path / "mechanics"
    mechanics_dir.mkdir()
    (mechanics_dir / "walk.py").write_text(_MECHANIC_MODULE, encoding="utf-8")

    report = aggregate(tmp_path, slug="t", history=False)
    payload = json.loads(render_json(report))

    assert len(payload["mechanics"]) == 1
    mech = payload["mechanics"][0]
    assert "first_authored_commit" in mech
    assert mech["first_authored_commit"] is None
    assert "first_authored_timestamp" in mech
    assert mech["first_authored_timestamp"] is None
