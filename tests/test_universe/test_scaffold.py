"""Tests for universe scaffolding: directories, CLAUDE.md, AGENTS.md, .mcp.json, git init.

Plan 04.1-05 additions:
    - :class:`TestScaffoldMechanicAuthorAgent` — the filesystem-based subagent
      markdown written to ``<universe>/.claude/agents/mechanic-author.md``.
    - :class:`TestRenderMechanicAuthorMd` — unit tests for the renderer
      function itself (frontmatter shape, shared-prompt invariant, tools
      whitelist).
    - :class:`TestClaudeMdOperatorFlow` — CLAUDE.md template additions
      (Operator Flow section, accurate 3-tool surface, subagent pointer).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from token_world.universe.manager import UniverseManager
from token_world.universe.scaffold import scaffold_universe
from token_world.universe.templates.claude_md import render_claude_md
from token_world.universe.templates.mechanic_author_agent import render_mechanic_author_md


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

    def test_creates_mirrored_test_mechanics_dir(self, tmp_data_dir: Path) -> None:
        """D-06: scaffold creates tests/test_mechanics/__init__.py as the
        mirrored test tree root."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        assert (universe_dir / "tests" / "test_mechanics").is_dir()
        assert (universe_dir / "tests" / "test_mechanics" / "__init__.py").is_file()

    def test_copies_flat_seed_mechanics(self, tmp_data_dir: Path) -> None:
        """D-10: seeds are copied as flat ``<id>.py`` modules, not subfolders."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        mechanics_dir = universe_dir / "mechanics"
        assert (mechanics_dir / "movement.py").is_file()
        assert (mechanics_dir / "observation.py").is_file()
        assert (mechanics_dir / "environmental_reaction.py").is_file()
        # Folder-based layout must NOT exist post-flatten.
        assert not (mechanics_dir / "movement").exists()
        assert not (mechanics_dir / "observation").exists()
        assert not (mechanics_dir / "environmental_reaction").exists()
        # Helpers copied through (underscore prefix is registry signal, not
        # scaffold signal); __init__.py excluded (destination is not a pkg).
        assert (mechanics_dir / "_helpers.py").is_file()
        assert not (mechanics_dir / "__init__.py").exists()


class TestScaffoldAuthoringGuide:
    """Tests for the D-31 universe-local authoring-guide copy."""

    def test_scaffold_copies_authoring_guide(self, tmp_data_dir: Path) -> None:
        """D-31: scaffold copies docs/guides/authoring-mechanics.md into
        <universe>/docs/authoring-mechanics.md (byte-identical)."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        dest = universe_dir / "docs" / "authoring-mechanics.md"
        assert dest.is_file(), f"guide not copied to {dest}"
        # Source-of-truth path: framework-repo docs/guides/authoring-mechanics.md
        src = Path(__file__).resolve().parents[2] / "docs" / "guides" / "authoring-mechanics.md"
        assert src.is_file(), f"source guide missing: {src}"
        assert dest.read_bytes() == src.read_bytes(), (
            "copied guide must be byte-identical to docs/guides/authoring-mechanics.md"
        )


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
        """CLAUDE.md contains '## Available Tools' section with the three MCP tools
        (register_mechanic was dropped per D-10)."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        content = (universe_dir / "CLAUDE.md").read_text()
        assert "## Available Tools" in content
        assert "resume_tick" in content
        assert "rollback" in content
        assert "list_mechanics" in content

    def test_claude_md_does_not_reference_register_mechanic(self, tmp_data_dir: Path) -> None:
        """D-10: register_mechanic is not an MCP tool; the authoring guide pointer
        replaces it."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        content = (universe_dir / "CLAUDE.md").read_text()
        assert "register_mechanic" not in content

    def test_claude_md_contains_mechanic_authoring_section(self, tmp_data_dir: Path) -> None:
        """CLAUDE.md contains the '## Mechanic Authoring' pointer section."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        content = (universe_dir / "CLAUDE.md").read_text()
        assert "## Mechanic Authoring" in content
        assert "scaffold-mechanic test-world" in content
        assert "docs/authoring-mechanics.md" in content

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


class TestScaffoldMcpJson:
    """Tests for .mcp.json creation within scaffold_universe()."""

    def test_creates_mcp_json(self, tmp_data_dir: Path) -> None:
        """scaffold_universe() creates .mcp.json in the universe dir."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        assert (universe_dir / ".mcp.json").is_file()

    def test_mcp_json_is_valid_json(self, tmp_data_dir: Path) -> None:
        """.mcp.json is valid JSON."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        content = (universe_dir / ".mcp.json").read_text()
        data = json.loads(content)
        assert isinstance(data, dict)

    def test_mcp_json_has_mcp_servers_key(self, tmp_data_dir: Path) -> None:
        """.mcp.json has mcpServers key."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        data = json.loads((universe_dir / ".mcp.json").read_text())
        assert "mcpServers" in data

    def test_mcp_json_has_token_world_server(self, tmp_data_dir: Path) -> None:
        """.mcp.json has token-world server entry."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        data = json.loads((universe_dir / ".mcp.json").read_text())
        assert "token-world" in data["mcpServers"]

    def test_mcp_json_server_uses_uvx(self, tmp_data_dir: Path) -> None:
        """.mcp.json server entry uses uvx command."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        data = json.loads((universe_dir / ".mcp.json").read_text())
        server = data["mcpServers"]["token-world"]
        assert server["command"] == "uvx"
        assert "token-world-mcp" in server["args"]


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

        # .mcp.json
        assert (path / ".mcp.json").is_file()
        mcp_data = json.loads((path / ".mcp.json").read_text())
        assert "mcpServers" in mcp_data
        assert "token-world" in mcp_data["mcpServers"]

        # Directories
        assert (path / "mechanics").is_dir()
        assert (path / "agents").is_dir()
        assert (path / "tick_summaries" / "ticks").is_dir()
        assert (path / "tick_summaries" / "batches").is_dir()
        assert (path / "tick_summaries" / "epochs").is_dir()

        # Git
        assert (path / ".git").exists()
        assert (path / ".gitignore").is_file()


class TestRenderMechanicAuthorMd:
    """Unit tests for the :func:`render_mechanic_author_md` renderer itself
    (Plan 04.1-05 Task 1). No filesystem required — these exercise the
    string-shaping logic in isolation."""

    def test_render_mechanic_author_md_has_yaml_frontmatter(self, tmp_data_dir: Path) -> None:
        """Output starts with ``---\\n`` and contains the three required
        frontmatter keys (description / tools / model)."""
        text = render_mechanic_author_md(tmp_data_dir)
        assert text.startswith("---\n")
        assert "description:" in text
        assert "tools:" in text
        assert "model: opus" in text

    def test_render_mechanic_author_md_body_contains_shared_prompt(
        self, tmp_data_dir: Path
    ) -> None:
        """The body section (after frontmatter) contains a stable sentinel
        phrase from :func:`mechanic_author_prompt` — confirming the shared
        prompt source (T-04.1-22 mitigation)."""
        text = render_mechanic_author_md(tmp_data_dir)
        # Sentinel is from mechanic_author_prompt's opening line.
        assert "Token World Mechanic Author" in text

    def test_render_mechanic_author_md_tools_exclude_Agent(self, tmp_data_dir: Path) -> None:
        """YAML ``tools:`` line does NOT include ``Agent`` — Pitfall 5 / T-04.1-23
        (filesystem subagent must not spawn sub-subagents)."""
        text = render_mechanic_author_md(tmp_data_dir)
        # Extract the frontmatter block and check tools line specifically.
        parts = text.split("---", 2)
        assert len(parts) >= 3, "expected YAML frontmatter delimiters"
        frontmatter_yaml = parts[1]
        frontmatter = yaml.safe_load(frontmatter_yaml)
        tools_line = frontmatter["tools"]
        tool_names = {t.strip() for t in tools_line.split(",")}
        assert "Agent" not in tool_names

    def test_render_mechanic_author_md_tools_include_validate_mechanic(
        self, tmp_data_dir: Path
    ) -> None:
        """``tools:`` mentions ``mcp__validation__validate_mechanic`` — the
        authoring subagent must be able to call the validator."""
        text = render_mechanic_author_md(tmp_data_dir)
        parts = text.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        tools_line = frontmatter["tools"]
        assert "mcp__validation__validate_mechanic" in tools_line

    def test_render_mechanic_author_md_tools_include_list_mechanics(
        self, tmp_data_dir: Path
    ) -> None:
        """``tools:`` mentions ``mcp__token-world__list_mechanics`` for pre-
        authoring existing-coverage checks (mirrors programmatic subagent)."""
        text = render_mechanic_author_md(tmp_data_dir)
        parts = text.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        assert "mcp__token-world__list_mechanics" in frontmatter["tools"]

    def test_render_mechanic_author_md_contains_yield_placeholder(self, tmp_data_dir: Path) -> None:
        """The filesystem-agent form embeds ``<YIELD_SIGNAL_JSON>`` as a
        placeholder (live yield pasted at invocation time)."""
        text = render_mechanic_author_md(tmp_data_dir)
        assert "<YIELD_SIGNAL_JSON>" in text


class TestScaffoldMechanicAuthorAgent:
    """Tests for the filesystem subagent scaffolded by
    :func:`scaffold_universe` (Plan 04.1-05 Task 1)."""

    def test_scaffold_dot_claude_dir_created(self, tmp_data_dir: Path) -> None:
        """``<universe>/.claude/agents/`` directory exists after scaffold."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        assert (universe_dir / ".claude").is_dir()
        assert (universe_dir / ".claude" / "agents").is_dir()

    def test_scaffold_writes_mechanic_author_md(self, tmp_data_dir: Path) -> None:
        """After scaffold, ``.claude/agents/mechanic-author.md`` exists and is
        non-empty."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        path = universe_dir / ".claude" / "agents" / "mechanic-author.md"
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert len(text) > 500, "mechanic-author.md should be substantial"

    def test_scaffold_mechanic_author_md_roundtrips_frontmatter(self, tmp_data_dir: Path) -> None:
        """YAML frontmatter parses and contains ``model: opus``."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        text = (universe_dir / ".claude" / "agents" / "mechanic-author.md").read_text()
        parts = text.split("---", 2)
        assert len(parts) >= 3, "expected ---...--- frontmatter delimiters"
        frontmatter = yaml.safe_load(parts[1])
        assert frontmatter["model"] == "opus"

    def test_scaffold_mechanic_author_md_included_in_initial_commit(
        self, tmp_data_dir: Path
    ) -> None:
        """Initial git commit includes the mechanic-author markdown (must be
        written BEFORE git init commit per plan Step B)."""
        import subprocess

        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=universe_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        assert ".claude/agents/mechanic-author.md" in result.stdout

    def test_scaffold_mechanic_author_md_tools_do_not_include_Agent(
        self, tmp_data_dir: Path
    ) -> None:
        """End-to-end: scaffold output's tools line excludes ``Agent``
        (T-04.1-23 mitigation — no sub-subagents)."""
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        text = (universe_dir / ".claude" / "agents" / "mechanic-author.md").read_text()
        parts = text.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        tool_names = {t.strip() for t in frontmatter["tools"].split(",")}
        assert "Agent" not in tool_names


class TestClaudeMdOperatorFlow:
    """Plan 04.1-05 CLAUDE.md template additions — Operator Flow section,
    accurate 3-tool surface, mechanic-author subagent pointer."""

    def test_claude_md_contains_operator_flow_section(self) -> None:
        """``render_claude_md`` output contains the H2 heading for the
        Operator Flow section."""
        content = render_claude_md(name="X", slug="x")
        assert "## Operator Flow: When a Tick Yields" in content

    def test_claude_md_mentions_three_mcp_tools_accurately(self) -> None:
        """Available Tools section mentions all 3 Phase-4 tools
        (``resume_tick``, ``rollback``, ``list_mechanics``)."""
        content = render_claude_md(name="X", slug="x")
        assert "resume_tick" in content
        assert "rollback" in content
        assert "list_mechanics" in content

    def test_claude_md_does_not_mention_register_mechanic(self) -> None:
        """``register_mechanic`` is absent (Phase 4 D-19 dropped it from the
        MCP surface)."""
        content = render_claude_md(name="X", slug="x")
        assert "register_mechanic" not in content

    def test_claude_md_does_not_declare_tools_unimplemented(self) -> None:
        """Stale ``Not yet implemented`` stamps are gone — the 3 tools are
        shipped as of Phase 4 / Phase 4.1."""
        content = render_claude_md(name="X", slug="x")
        assert "Not yet implemented" not in content

    def test_claude_md_mentions_mechanic_author_subagent(self) -> None:
        """Body references ``.claude/agents/mechanic-author.md`` so the
        interactive operator knows the subagent exists."""
        content = render_claude_md(name="X", slug="x")
        assert ".claude/agents/mechanic-author.md" in content

    def test_claude_md_operator_flow_references_cli_commands(self) -> None:
        """Operator Flow section references the three dev-UX CLI commands
        (``inspect-yield``, ``resume-tick``, ``replay-tick``)."""
        content = render_claude_md(name="X", slug="x")
        assert "inspect-yield" in content
        assert "resume-tick" in content
        assert "replay-tick" in content


class TestScaffoldClaudeMdOperatorFlowEndToEnd:
    """Belt-and-braces: scaffold end-to-end assertions that the operator
    flow additions reach the written CLAUDE.md on disk."""

    def test_scaffold_claude_md_has_operator_flow_section(self, tmp_data_dir: Path) -> None:
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        content = (universe_dir / "CLAUDE.md").read_text()
        assert "## Operator Flow: When a Tick Yields" in content

    def test_scaffold_claude_md_points_at_mechanic_author(self, tmp_data_dir: Path) -> None:
        universe_dir = tmp_data_dir / "test-world"
        universe_dir.mkdir()
        scaffold_universe(universe_dir, name="Test World", slug="test-world")
        content = (universe_dir / "CLAUDE.md").read_text()
        assert ".claude/agents/mechanic-author.md" in content
