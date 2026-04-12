"""Tests for universe scaffolding: directories, CLAUDE.md, AGENTS.md, git init."""

from __future__ import annotations

from pathlib import Path

import pytest

from token_world.universe.manager import UniverseManager
from token_world.universe.scaffold import scaffold_universe


class TestScaffoldDirectories:
    """Tests for directory creation within scaffold_universe()."""

    def test_creates_mechanics_dir(self, tmp_data_dir: Path) -> None:
        """scaffold_universe() creates a mechanics/ directory."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        assert (universe_dir / "mechanics").is_dir()

    def test_creates_agents_dir(self, tmp_data_dir: Path) -> None:
        """scaffold_universe() creates an agents/ directory."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        assert (universe_dir / "agents").is_dir()

    def test_creates_tick_summaries_ticks(self, tmp_data_dir: Path) -> None:
        """scaffold_universe() creates tick_summaries/ticks/ directory."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        assert (universe_dir / "tick_summaries" / "ticks").is_dir()

    def test_creates_tick_summaries_batches(self, tmp_data_dir: Path) -> None:
        """scaffold_universe() creates tick_summaries/batches/ directory."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        assert (universe_dir / "tick_summaries" / "batches").is_dir()

    def test_creates_tick_summaries_epochs(self, tmp_data_dir: Path) -> None:
        """scaffold_universe() creates tick_summaries/epochs/ directory."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        assert (universe_dir / "tick_summaries" / "epochs").is_dir()


class TestScaffoldClaudeMd:
    """Tests for CLAUDE.md generation within scaffold_universe()."""

    def test_creates_claude_md(self, tmp_data_dir: Path) -> None:
        """scaffold_universe() creates CLAUDE.md in the universe dir."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        assert (universe_dir / "CLAUDE.md").is_file()

    def test_claude_md_contains_world_rules(self, tmp_data_dir: Path) -> None:
        """CLAUDE.md contains '## World Rules' section."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        content = (universe_dir / "CLAUDE.md").read_text()
        assert "## World Rules" in content

    def test_claude_md_contains_available_tools(self, tmp_data_dir: Path) -> None:
        """CLAUDE.md contains '## Available Tools' section with all four tools."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        content = (universe_dir / "CLAUDE.md").read_text()
        assert "## Available Tools" in content
        assert "resume_tick" in content
        assert "rollback" in content
        assert "list_mechanics" in content
        assert "register_mechanic" in content

    def test_claude_md_contains_current_state(self, tmp_data_dir: Path) -> None:
        """CLAUDE.md contains '## Current State' section."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        content = (universe_dir / "CLAUDE.md").read_text()
        assert "## Current State" in content

    def test_claude_md_contains_constraints(self, tmp_data_dir: Path) -> None:
        """CLAUDE.md contains '## Constraints' section with grounding requirement."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        content = (universe_dir / "CLAUDE.md").read_text()
        assert "## Constraints" in content
        assert "grounded in knowledge graph" in content

    def test_claude_md_contains_universe_name(self, tmp_data_dir: Path) -> None:
        """CLAUDE.md contains the universe display name in the title."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        content = (universe_dir / "CLAUDE.md").read_text()
        assert "# Universe: Test World" in content


class TestScaffoldAgentsMd:
    """Tests for AGENTS.md symlink within scaffold_universe()."""

    def test_creates_agents_md_symlink(self, tmp_data_dir: Path) -> None:
        """scaffold_universe() creates AGENTS.md as a symlink."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        agents_md = universe_dir / "AGENTS.md"
        assert agents_md.is_symlink()

    def test_agents_md_symlink_target_is_claude_md(self, tmp_data_dir: Path) -> None:
        """AGENTS.md symlink target is 'CLAUDE.md' (relative symlink)."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        agents_md = universe_dir / "AGENTS.md"
        assert agents_md.resolve().name == "CLAUDE.md"
        # Check it's a relative symlink
        import os

        assert os.readlink(str(agents_md)) == "CLAUDE.md"


class TestScaffoldGitignore:
    """Tests for .gitignore creation within scaffold_universe()."""

    def test_creates_gitignore(self, tmp_data_dir: Path) -> None:
        """scaffold_universe() creates .gitignore with SQLite WAL entries."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        gitignore = universe_dir / ".gitignore"
        assert gitignore.is_file()
        content = gitignore.read_text()
        assert "*.db-wal" in content
        assert "*.db-shm" in content


class TestScaffoldGitInit:
    """Tests for git initialization within scaffold_universe()."""

    def test_initializes_git_repo(self, tmp_data_dir: Path) -> None:
        """scaffold_universe() initializes a git repo (.git/ exists)."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        assert (universe_dir / ".git").exists()

    def test_creates_initial_commit(self, tmp_data_dir: Path) -> None:
        """scaffold_universe() creates an initial git commit."""
        import subprocess

        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=universe_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Initialize universe" in result.stdout


class TestManagerIntegrationWithScaffold:
    """Tests for full flow: manager.create() produces all scaffold output."""

    def test_create_produces_all_expected_files(self, tmp_data_dir: Path) -> None:
        """Full flow via manager.create() produces all expected files and directories."""
        manager = UniverseManager(data_dir=tmp_data_dir)
        path = manager.create("Integration World")

        # Database
        assert (path / "universe.db").is_file()

        # CLAUDE.md and AGENTS.md
        assert (path / "CLAUDE.md").is_file()
        assert (path / "AGENTS.md").is_symlink()

        # Directories
        assert (path / "mechanics").is_dir()
        assert (path / "agents").is_dir()
        assert (path / "tick_summaries" / "ticks").is_dir()
        assert (path / "tick_summaries" / "batches").is_dir()
        assert (path / "tick_summaries" / "epochs").is_dir()

        # Git
        assert (path / ".git").exists()
        assert (path / ".gitignore").is_file()
