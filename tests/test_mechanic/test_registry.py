"""Tests for mechanic loader and registry."""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from token_world.mechanic.protocol import Mechanic

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_universe(tmp_path: Path) -> Path:
    """Create a temporary universe directory with seed mechanics and a git repo.

    Copies seed mechanic folders from the package into a ``mechanics/``
    subdirectory, initialises a git repo, and creates an initial commit.
    """
    mechanics_dir = tmp_path / "mechanics"
    mechanics_dir.mkdir()

    seeds_dir = (
        Path(__file__).resolve().parent.parent.parent / "src" / "token_world" / "mechanic" / "seeds"
    )
    for entry in sorted(seeds_dir.iterdir()):
        if entry.is_dir() and (entry / "mechanic.py").exists():
            shutil.copytree(entry, mechanics_dir / entry.name)

    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@localhost",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@localhost",
    }
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env=git_env,
    )
    return tmp_path


@pytest.fixture
def non_git_universe(tmp_path: Path) -> Path:
    """Universe dir with mechanics but no git repo."""
    mechanics_dir = tmp_path / "mechanics"
    mechanics_dir.mkdir()

    seeds_dir = (
        Path(__file__).resolve().parent.parent.parent / "src" / "token_world" / "mechanic" / "seeds"
    )
    for entry in sorted(seeds_dir.iterdir()):
        if entry.is_dir() and (entry / "mechanic.py").exists():
            shutil.copytree(entry, mechanics_dir / entry.name)

    return tmp_path


# ---------------------------------------------------------------------------
# Registry / Scan Tests
# ---------------------------------------------------------------------------


class TestRegistryScan:
    def test_scan_discovers_mechanics(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        mechanics = registry.list_mechanics()
        assert len(mechanics) == 3

    def test_list_mechanics_sorted(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        mechanics = registry.list_mechanics()
        ids = [m.id for m in mechanics]
        assert ids == sorted(ids)

    def test_get_mechanic_returns_instance(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        mechanic = registry.get_mechanic("movement")
        assert isinstance(mechanic, Mechanic)
        assert mechanic.id == "movement"

    def test_get_mechanic_unknown_raises(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        with pytest.raises(KeyError, match="nonexistent"):
            registry.get_mechanic("nonexistent")

    def test_mechanic_info_has_correct_fields(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        info = registry.get_info("movement")
        assert info.id == "movement"
        assert "move" in info.description.lower()
        assert info.voluntary is True
        assert "spatial" in info.tags


# ---------------------------------------------------------------------------
# Query by Tag
# ---------------------------------------------------------------------------


class TestQueryByTag:
    def test_query_by_tag_core(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        results = registry.query_by_tag("core")
        assert len(results) == 3

    def test_query_by_tag_spatial(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        results = registry.query_by_tag("spatial")
        assert len(results) == 1
        assert results[0].id == "movement"


# ---------------------------------------------------------------------------
# Git History
# ---------------------------------------------------------------------------


class TestGitHistory:
    def test_get_history_returns_commits(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        history = registry.get_history("movement")
        assert len(history) >= 1
        assert history[0].commit_hash
        assert history[0].date
        assert history[0].message

    def test_get_history_not_git_repo(self, non_git_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(non_git_universe / "mechanics", universe_dir=non_git_universe)
        history = registry.get_history("movement")
        assert history == []


# ---------------------------------------------------------------------------
# Loader Error Cases
# ---------------------------------------------------------------------------


class TestLoaderErrors:
    def test_loader_missing_mechanic_py(self, tmp_path: Path) -> None:
        from token_world.mechanic.loader import load_mechanic_class

        empty_dir = tmp_path / "empty_mechanic"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            load_mechanic_class(empty_dir)

    def test_loader_no_subclass(self, tmp_path: Path) -> None:
        from token_world.mechanic.loader import load_mechanic_class

        bad_dir = tmp_path / "bad_mechanic"
        bad_dir.mkdir()
        (bad_dir / "mechanic.py").write_text(
            textwrap.dedent("""\
                # No Mechanic subclass here
                class NotAMechanic:
                    pass
            """)
        )
        with pytest.raises(ValueError, match="No Mechanic subclass"):
            load_mechanic_class(bad_dir)
