"""Universe folder scaffolding: directories, CLAUDE.md, AGENTS.md, git init.

Creates the complete directory structure and files for a new universe folder,
including CLAUDE.md (per D-04), AGENTS.md symlink (per D-05), .gitignore,
and an initialized git repository with an initial commit.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from token_world.universe.templates.claude_md import render_claude_md
from token_world.universe.templates.mcp_config import render_mcp_json


def _copy_seed_mechanics(mechanics_dir: Path) -> None:
    """Copy bundled flat seed mechanic modules into a universe's mechanics/.

    Per D-10 (Phase 4), mechanics are flat ``<id>.py`` modules. This function
    copies every ``.py`` file from ``src/token_world/mechanic/seeds/`` except
    ``__init__.py``; underscore-prefixed files (helpers, e.g. ``_helpers.py``)
    ARE copied because the ``_`` prefix is the registry's skip signal, not
    the scaffold's. ``__init__.py`` is excluded because the destination is
    not a Python package.

    Args:
        mechanics_dir: The universe's mechanics/ directory.
    """
    seeds_dir = Path(__file__).resolve().parent.parent / "mechanic" / "seeds"
    if not seeds_dir.is_dir():
        return
    for entry in sorted(seeds_dir.iterdir()):
        if entry.is_file() and entry.suffix == ".py" and entry.name != "__init__.py":
            shutil.copy2(entry, mechanics_dir / entry.name)


def scaffold_universe(universe_dir: Path, *, name: str, slug: str) -> None:
    """Populate a universe directory with all required files and structure.

    Creates:
        - mechanics/ directory
        - agents/ directory
        - tick_summaries/{ticks,batches,epochs}/ directories
        - CLAUDE.md with world rules, tools, state, and constraints
        - AGENTS.md as a relative symlink to CLAUDE.md
        - .gitignore for SQLite WAL files
        - Initialized git repo with initial commit

    Args:
        universe_dir: Path to the universe folder (must already exist).
        name: Display name of the universe.
        slug: Slugified name for the universe.
    """
    # Create subdirectories and copy seed mechanics
    (universe_dir / "mechanics").mkdir(exist_ok=True)
    _copy_seed_mechanics(universe_dir / "mechanics")
    # Mirrored test tree (D-06): mechanic tests live outside mechanics/ so
    # pytest never imports mechanics as a package. Create the scaffold here;
    # authors drop test modules in later.
    tests_dir = universe_dir / "tests" / "test_mechanics"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (universe_dir / "agents").mkdir(exist_ok=True)
    (universe_dir / "tick_summaries" / "ticks").mkdir(parents=True, exist_ok=True)
    (universe_dir / "tick_summaries" / "batches").mkdir(exist_ok=True)
    (universe_dir / "tick_summaries" / "epochs").mkdir(exist_ok=True)

    # Generate CLAUDE.md from template
    claude_md = render_claude_md(name=name, slug=slug)
    (universe_dir / "CLAUDE.md").write_text(claude_md)

    # Create AGENTS.md as symlink to CLAUDE.md (per D-05)
    agents_md = universe_dir / "AGENTS.md"
    os.symlink("CLAUDE.md", str(agents_md))

    # Generate .mcp.json for MCP tool discovery
    mcp_json = render_mcp_json()
    (universe_dir / ".mcp.json").write_text(mcp_json)

    # Create .gitignore for SQLite WAL files
    gitignore_content = "*.db-wal\n*.db-shm\n"
    (universe_dir / ".gitignore").write_text(gitignore_content)

    # Initialize git repo and create initial commit
    _git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Token World",
        "GIT_AUTHOR_EMAIL": "token-world@localhost",
        "GIT_COMMITTER_NAME": "Token World",
        "GIT_COMMITTER_EMAIL": "token-world@localhost",
    }

    subprocess.run(
        ["git", "init"],
        cwd=universe_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "."],
        cwd=universe_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initialize universe"],
        cwd=universe_dir,
        check=True,
        capture_output=True,
        env=_git_env,
    )
