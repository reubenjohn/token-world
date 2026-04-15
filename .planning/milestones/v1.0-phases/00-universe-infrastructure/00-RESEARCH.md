# Phase 0: Universe Infrastructure - Research

**Researched:** 2026-04-11
**Domain:** Python project scaffolding, CLI tooling, SQLite initialization, MCP configuration, git automation
**Confidence:** HIGH

## Summary

Phase 0 is a greenfield Python project setup phase. The codebase has zero Python files, no `pyproject.toml`, and no `src/` directory. The phase must produce: (1) a Python package with src-layout (`src/token_world/`), (2) a universe manager that creates self-contained universe folders at `$XDG_DATA_HOME/token_world/universes/`, and (3) each universe folder containing CLAUDE.md, AGENTS.md symlink, .mcp.json, universe.db, mechanics/, agents/, tick_summaries/, and .git/.

The technical challenge is modest -- this is file scaffolding, SQLite schema creation, and template generation. The key risk is getting the conventions right since every subsequent phase builds on these patterns. The `.mcp.json` format is well-documented (JSON with `mcpServers` key), AGENTS.md is just Markdown (symlink to CLAUDE.md works), and `uv init --package` produces the exact src-layout structure needed.

**Primary recommendation:** Use `uv init --package --python 3.12` as the project bootstrap, `click` for the CLI interface, `python-slugify` for name-to-folder conversion, and raw `sqlite3` for universe.db initialization. Keep it simple -- no framework overhead.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** src-layout -- Python package lives at `src/token_world/` with `pyproject.toml` at the project root. Standard `src/` layout to prevent accidental imports of uninstalled code.
- **D-02:** Full XDG base directories -- Universes stored in `$XDG_DATA_HOME/token_world/universes/` (defaults to `~/.local/share/token_world/universes/`). Config in `$XDG_CONFIG_HOME/token_world/` (defaults to `~/.config/token_world/`). Respect user overrides of XDG vars.
- **D-03:** Claude Code permissions added to `.claude/settings.json` for read/write access to the XDG data and config directories. (Already done -- settings.json exists with correct paths.)
- **D-04:** Operational template -- Per-universe CLAUDE.md is a structured template with sections for: world rules (empty placeholder for human/agent to fill), available MCP tools with usage docs, current state summary, and constraints (grounding, no hallucinated state). No LLM generation at creation time.
- **D-05:** AGENTS.md is a symlink to CLAUDE.md by default. Harnesses that read AGENTS.md (like Codex) get the same instructions. Can be re-pointed if harnesses diverge.
- **D-06:** User-provided name at creation, slugified for the folder name (e.g., "My Test World" -> `my-test-world/`). Must be unique within the data directory. Display name stored in universe.db metadata.
- **D-07:** Empty graph at creation -- no seed nodes, no edges. The world is a blank slate.

### Claude's Discretion
- **D-08:** MCP tool stubs -- Claude decides how to implement the .mcp.json tool declarations at Phase 0 (real stubs returning "not implemented", placeholder declarations, or minimal working skeletons). The tools are: resume_tick, rollback, list_mechanics, register_mechanic.
- **D-09:** Creation flow detail -- Universe creation is a tool call that produces a template, then the agent modifies files directly. Claude decides the exact tool interface and creation API shape.

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UNIV-01 | Universe scaffolding creates a self-contained folder with CLAUDE.md, AGENTS.md (symlink), .mcp.json, universe.db, mechanics/, agents/, and .git/ | Verified: `os.symlink()` for AGENTS.md, `git init` via subprocess, SQLite via stdlib, `.mcp.json` format documented by Claude Code docs |
| UNIV-02 | Generated CLAUDE.md per universe contains world rules, available tools documentation, and current state summary | Template approach per D-04; structured Markdown with placeholder sections |
| UNIV-03 | Generated .mcp.json per universe exposes minimal simulation tools (resume_tick, rollback, list_mechanics, register_mechanic) | `.mcp.json` format verified: `{"mcpServers": {"server-name": {"command": "...", "args": [...]}}}` |
| UNIV-04 | Universe manager supports create, load, list, and delete operations | Click CLI + Python API; XDG paths per D-02; slug uniqueness check per D-06 |
| UNIV-05 | Harness-agnostic design -- universe works with any agent coding harness that reads instruction files + MCP | AGENTS.md symlink to CLAUDE.md (D-05); .mcp.json is the standard MCP config format |
| UNIV-06 | Universe folder contains tick_summaries/ with hierarchical JSON summaries | Empty directory at creation; structure defined by architecture docs (tick -> batch -> epoch) |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Package manager:** `uv` (not pip/poetry)
- **Linting/formatting:** `ruff`
- **Type checking:** `mypy` on mechanic framework API
- **Pre-commit hooks:** `prek` (not `pre-commit`)
- **Diagrams:** Mermaid in Markdown, never rendered PNGs
- **Docs structure:** `docs/design/` and `docs/guides/`
- **Forbidden:** LangChain, MongoDB, Neo4j, FastAPI/Flask, ORM, pickle

## Standard Stack

### Core (Phase 0 only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12+ | Runtime | Required by CLAUDE.md. uv can install 3.12.12 (verified on this machine). [VERIFIED: `uv run --python 3.12`] |
| click | 8.x | CLI framework | Locked in CLAUDE.md stack. Simple, well-documented, standard for Python CLIs. [ASSUMED -- version 8.x from CLAUDE.md stack table] |
| python-slugify | 8.0.4 | Name-to-folder slug conversion | Handles unicode, customizable separators, well-maintained. [VERIFIED: PyPI shows 8.0.4 as latest] |
| Pydantic | 2.12+ | Data validation for universe metadata, structured configs | Locked in CLAUDE.md stack. Rust-backed validation. [ASSUMED -- version from CLAUDE.md] |

### Development Tools

| Tool | Version | Purpose | Available |
|------|---------|---------|-----------|
| uv | 0.9.24 | Package management | [VERIFIED: installed] |
| ruff | 0.15.10 | Linting + formatting | [VERIFIED: available via `uv tool run`] |
| mypy | installed | Type checking | [VERIFIED: in existing venv] |
| prek | 0.3.8 | Git hooks | [VERIFIED: just installed via pip] |
| pytest | 8.x | Testing | [ASSUMED -- will be installed as dev dependency] |

### Not Needed Yet (defer to later phases)
- NetworkX (Phase 1)
- Anthropic SDK (Phase 4+)
- loguru, rich, deepdiff (later phases)

**Installation (Phase 0):**
```bash
uv init --package --python 3.12 .
uv add click python-slugify pydantic
uv add --dev pytest ruff mypy prek
```

Note: `uv init` in an existing directory with a `.git/` will need care -- may need to create `pyproject.toml` manually or use `uv init` flags. The project root already has a git repo.

## Architecture Patterns

### Project Structure
```
token_world/                    # project root (already exists)
├── pyproject.toml              # NEW - package config
├── src/
│   └── token_world/
│       ├── __init__.py
│       ├── cli.py              # click CLI entry point
│       ├── universe/
│       │   ├── __init__.py
│       │   ├── manager.py      # create/load/list/delete operations
│       │   ├── scaffold.py     # folder + file generation
│       │   ├── paths.py        # XDG path resolution
│       │   └── templates/      # CLAUDE.md template, .mcp.json template
│       │       ├── CLAUDE.md.j2  # or plain string template
│       │       └── mcp.json     # static MCP stub config
│       └── models.py           # Pydantic models for universe metadata
├── tests/
│   ├── conftest.py
│   └── test_universe/
│       ├── test_manager.py
│       └── test_scaffold.py
├── docs/
│   ├── design/
│   │   └── architecture.md    # already exists
│   └── guides/
├── .claude/
│   └── settings.json          # already exists with XDG permissions
└── .git/                       # already exists
```

### Universe Folder Structure (created by scaffold)
```
~/.local/share/token_world/universes/my-test-world/
├── CLAUDE.md                  # generated template
├── AGENTS.md                  # symlink -> CLAUDE.md
├── .mcp.json                  # MCP tool declarations
├── universe.db                # SQLite database
├── mechanics/                 # empty dir (populated by Phase 2+)
├── agents/                    # empty dir (populated by Phase 6+)
├── tick_summaries/            # empty dir (populated by Phase 5+)
│   ├── ticks/                 # individual tick JSONs
│   ├── batches/               # batch summaries (every ~100 ticks)
│   └── epochs/                # epoch summaries (every ~100 batches)
└── .git/                      # initialized git repo
```

### Pattern 1: XDG Path Resolution
**What:** Centralized path resolution respecting XDG environment variable overrides
**When to use:** Every time the code needs to find universe or config directories

```python
# Source: XDG Base Directory Specification
import os
from pathlib import Path

def get_data_dir() -> Path:
    """Return the token_world data directory, respecting XDG_DATA_HOME."""
    base = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(base) / "token_world"

def get_universes_dir() -> Path:
    """Return the universes directory."""
    return get_data_dir() / "universes"

def get_config_dir() -> Path:
    """Return the token_world config directory, respecting XDG_CONFIG_HOME."""
    base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(base) / "token_world"
```

### Pattern 2: Universe Creation as Atomic Operation
**What:** Create a universe folder with all required files, or fail cleanly with no partial state
**When to use:** `create_universe()` call

```python
# Pseudocode for creation flow
import shutil
import tempfile
from pathlib import Path

def create_universe(name: str) -> Path:
    slug = slugify(name)
    target = get_universes_dir() / slug

    if target.exists():
        raise ValueError(f"Universe '{slug}' already exists")

    # Create in a temp dir first, then move atomically
    with tempfile.TemporaryDirectory(dir=get_universes_dir()) as tmp:
        tmp_path = Path(tmp) / slug
        tmp_path.mkdir()
        _scaffold_universe(tmp_path, name, slug)
        # Atomic move
        shutil.move(str(tmp_path), str(target))

    return target
```

### Pattern 3: .mcp.json for Simulation Tools
**What:** Per-universe MCP configuration pointing to the token_world MCP server
**When to use:** Generated in each universe folder at creation time

```json
{
  "mcpServers": {
    "token-world": {
      "command": "uv",
      "args": ["run", "--directory", "${PARENT_DIR}", "token-world-mcp"],
      "env": {
        "UNIVERSE_PATH": "${UNIVERSE_DIR}"
      }
    }
  }
}
```

**D-08 Recommendation (Claude's Discretion):** Use `"command": "uv", "args": ["run", "token-world-mcp"]` pointing to a Python entry point that returns "not implemented" for all four tools. This is a real stdio MCP server stub -- minimal but functional. Claude Code will discover and load it, showing the tools as available. The stub can be ~30 lines using the `mcp` Python package or even simpler with raw JSON-RPC over stdio. The alternative (just declaring tools in .mcp.json without a server) is not how MCP works -- the JSON only configures how to _launch_ the server, not what tools it exposes. The server itself declares its tools.

**Revised D-08 Recommendation:** At Phase 0, the `.mcp.json` should contain a valid server entry pointing to the token_world package's MCP entry point. The server binary will exist but tools will return "not implemented" responses. This gives Claude Code real tool discovery while making it obvious the tools aren't functional yet.

### Pattern 4: Universe Database Schema
**What:** Minimal SQLite schema for universe metadata at creation time
**When to use:** universe.db initialization

```sql
-- Universe metadata
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Pre-populate with creation metadata
INSERT INTO metadata (key, value) VALUES
    ('display_name', ?),
    ('slug', ?),
    ('created_at', ?),
    ('schema_version', '1');
```

The database will be extended in Phase 1 (graph tables, event log). Phase 0 only needs the metadata table.

### Anti-Patterns to Avoid
- **Over-engineering the template:** CLAUDE.md is a static template with placeholders, not a Jinja2 monstrosity. Use Python string formatting or simple `str.replace()`. [ASSUMED -- Jinja2 would add a dependency for minimal benefit]
- **Nested git repos within project git:** Universe folders are outside the project tree (XDG data dir), so they get their own independent git repos. This is correct by design.
- **Hardcoding paths:** Always use the XDG path resolution functions. Never hardcode `~/.local/share/`.
- **Creating universe folders inside the project:** Universes live in XDG_DATA_HOME, not in the source tree. The project tree is for the engine code.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slug generation | Custom regex/replace | `python-slugify` 8.0.4 | Unicode handling, edge cases (consecutive dashes, leading/trailing), battle-tested |
| CLI argument parsing | argparse boilerplate | `click` 8.x | Decorators, type coercion, help generation, subcommands |
| Data validation | Manual dict checking | `Pydantic` models | Type safety, serialization, error messages |
| Path construction | String concatenation | `pathlib.Path` | Cross-platform, operator overloading, `.mkdir(parents=True)` |

**Key insight:** Phase 0 is infrastructure -- the libraries are small, well-understood, and eliminate entire categories of bugs.

## Common Pitfalls

### Pitfall 1: Symlink on Windows
**What goes wrong:** `os.symlink()` requires developer mode or admin privileges on Windows
**Why it happens:** Windows treats symlinks as a security feature
**How to avoid:** Use `os.symlink()` and catch `OSError`. Fall back to file copy with a comment noting it's a copy, not a symlink. Or just document "Linux/macOS only" for v1.
**Warning signs:** Tests pass on Linux, fail on Windows CI

### Pitfall 2: Race Condition on Universe Creation
**What goes wrong:** Two concurrent `create_universe("same-name")` calls both check existence, both proceed, one overwrites the other
**Why it happens:** TOCTOU (time-of-check-time-of-use) between exists() check and mkdir()
**How to avoid:** Use atomic operations -- `mkdir()` raises `FileExistsError` if the directory already exists. Don't check-then-create; just create and handle the error.
**Warning signs:** Intermittent test failures in parallel test runs

### Pitfall 3: Git Init in Existing Repo
**What goes wrong:** Running `uv init` in a directory that already has `.git/` may behave unexpectedly
**Why it happens:** `uv init --package` creates its own `.git/`. The project root already has one.
**How to avoid:** Since `pyproject.toml` doesn't exist yet but `.git/` does, manually create `pyproject.toml` with the correct src-layout config rather than running `uv init`. Or run `uv init` and let it detect the existing git repo (uv handles this gracefully -- verified it does NOT create a new `.git/` if one exists).
**Warning signs:** Unexpected git status changes after init

### Pitfall 4: SQLite WAL Mode in Universe Folders
**What goes wrong:** WAL mode creates `-wal` and `-shm` files that git tracks as noise
**Why it happens:** WAL mode is recommended for concurrent reads but creates extra files
**How to avoid:** Add `*.db-wal` and `*.db-shm` to the universe's `.gitignore`. Or use journal_mode=DELETE for universe.db (simpler, sufficient for single-writer).
**Warning signs:** Git shows unexpected modified files after database operations

### Pitfall 5: MCP Server Discovery
**What goes wrong:** `.mcp.json` is present but Claude Code doesn't find the tools
**Why it happens:** The `.mcp.json` must be at the project root that Claude Code is opened in. If the agent is working inside the universe folder, `.mcp.json` is correctly placed. If working from the engine project root, it won't see universe-level `.mcp.json`.
**How to avoid:** Understand that `.mcp.json` is scoped to the directory Claude Code opens as a project. Universe folders are designed to be opened as standalone projects by the operator.
**Warning signs:** Tools don't appear in Claude Code's tool list

## Code Examples

### Universe Manager API
```python
# Source: project architecture decisions D-02, D-04, D-06
from pathlib import Path
from slugify import slugify

class UniverseManager:
    """Manages universe lifecycle: create, load, list, delete."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or get_universes_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def create(self, name: str) -> Path:
        """Create a new universe with the given display name."""
        slug = slugify(name)
        universe_dir = self.data_dir / slug
        universe_dir.mkdir()  # raises FileExistsError if exists
        scaffold_universe(universe_dir, name=name, slug=slug)
        return universe_dir

    def list(self) -> list[dict]:
        """List all universes with metadata."""
        universes = []
        for path in sorted(self.data_dir.iterdir()):
            if path.is_dir() and (path / "universe.db").exists():
                universes.append(load_universe_metadata(path))
        return universes

    def load(self, slug: str) -> Path:
        """Load an existing universe by slug. Raises if not found."""
        path = self.data_dir / slug
        if not path.exists() or not (path / "universe.db").exists():
            raise FileNotFoundError(f"Universe '{slug}' not found")
        return path

    def delete(self, slug: str) -> None:
        """Delete a universe and all its data."""
        path = self.load(slug)  # validates existence
        shutil.rmtree(path)
```

### Click CLI Entry Point
```python
# Source: CLAUDE.md stack recommendations
import click
from token_world.universe.manager import UniverseManager

@click.group()
def cli():
    """Token World - Universe Simulator"""
    pass

@cli.command()
@click.argument("name")
def create(name: str):
    """Create a new universe with the given name."""
    manager = UniverseManager()
    path = manager.create(name)
    click.echo(f"Universe created at {path}")

@cli.command()
def list():
    """List all universes."""
    manager = UniverseManager()
    for u in manager.list():
        click.echo(f"  {u['slug']}  ({u['display_name']})")

@cli.command()
@click.argument("slug")
def delete(slug: str):
    """Delete a universe by slug."""
    manager = UniverseManager()
    manager.delete(slug)
    click.echo(f"Universe '{slug}' deleted")
```

### CLAUDE.md Template Structure
```markdown
# Universe: {display_name}

## World Rules

> No rules yet. The world is a blank slate.
> Rules emerge as mechanics are created during simulation.

## Available Tools

### resume_tick
Resume or start a new simulation tick. The engine interprets the resident
agent's action, matches it to a mechanic, executes the mechanic, and
returns an observation grounded in the knowledge graph.

**Status:** Not yet implemented (Phase 5)

### rollback
Roll back the universe to a previous snapshot.

**Status:** Not yet implemented (Phase 1)

### list_mechanics
List all registered mechanics with their descriptions and preconditions.

**Status:** Not yet implemented (Phase 2)

### register_mechanic
Register a new mechanic from a mechanics/ subfolder.

**Status:** Not yet implemented (Phase 2)

## Current State

Empty universe. No nodes, no edges, no mechanics.

## Constraints

- All observations MUST be grounded in knowledge graph state
- Never hallucinate state that doesn't exist in the graph
- Mechanics are the only way to modify the knowledge graph
- Every mutation is logged and reversible
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pip install -e .` for dev installs | `uv sync` (handles editable installs automatically) | uv 0.4+ (2024) | Faster, no manual editable install step |
| `setup.py` + `setup.cfg` | `pyproject.toml` only | PEP 621 (2021), widely adopted 2023+ | Single config file |
| `pre-commit` for git hooks | `prek` | Recent | Lighter, faster, Rust-based |
| `black` + `isort` + `flake8` | `ruff` (all-in-one) | 2023+ | Single tool, 10-100x faster |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | click 8.x is the current major version | Standard Stack | Low -- click is very stable, 8.x has been current for years |
| A2 | Pydantic 2.12+ is current | Standard Stack | Low -- Pydantic 2.x is stable, minor version doesn't matter for Phase 0 usage |
| A3 | pytest 8.x is current | Standard Stack | Low -- any recent pytest works |
| A4 | Jinja2 is overkill for CLAUDE.md template | Anti-Patterns | Low -- Python f-strings or str.format() suffice for a handful of variable substitutions |
| A5 | `prek` integrates with `ruff` and `mypy` out of the box | Development Tools | Medium -- if prek doesn't support the hook pattern needed, may need custom configuration |

## Open Questions (RESOLVED)

1. **MCP Server Stub Implementation**
   - What we know: `.mcp.json` points to a server process; the server declares its tools via the MCP protocol
   - What's unclear: Should Phase 0 include a minimal MCP server (using the `mcp` Python package) or just the `.mcp.json` file pointing to a not-yet-existing binary?
   - RESOLVED: Include a minimal MCP stdio server (~30-50 lines) using raw JSON-RPC over stdin/stdout (no external MCP library) that declares the 4 tools and returns "not implemented" for each. This validates the full Claude Code integration immediately while keeping dependencies minimal. Implemented in 00-02 Task 2.

2. **pyproject.toml Bootstrap in Existing Git Repo**
   - What we know: `uv init --package` handles existing `.git/` gracefully (does not re-init)
   - What's unclear: Whether `uv init` will conflict with existing files (CLAUDE.md, docs/, .planning/)
   - RESOLVED: Manually create pyproject.toml with the correct src-layout content rather than running `uv init`. This avoids any conflict with existing files in the repo. Implemented in 00-01 Task 1.

3. **Template Rendering Approach**
   - What we know: CLAUDE.md template needs ~3 variable substitutions (display_name, slug, created_at)
   - What's unclear: Whether to use Python f-strings, `str.format()`, `string.Template`, or Jinja2
   - RESOLVED: Use `string.Template` (stdlib) -- safe substitution, no dependency, clear `$variable` syntax. Implemented in 00-02 Task 1.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | Runtime (D-01) | Yes (via uv) | 3.12.12 | -- |
| uv | Package management | Yes | 0.9.24 | -- |
| ruff | Linting/formatting | Yes (via uv tool) | 0.15.10 | -- |
| mypy | Type checking | Yes | installed | -- |
| prek | Git hooks | Yes | 0.3.8 | -- |
| git | Universe version control | Yes | installed | -- |
| SQLite | universe.db | Yes (Python stdlib) | bundled | -- |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x (to be installed as dev dependency) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] section (Wave 0) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UNIV-01 | create_universe() produces folder with all required files | integration | `uv run pytest tests/test_universe/test_scaffold.py -x` | Wave 0 |
| UNIV-02 | Generated CLAUDE.md contains world rules, tools docs, state summary | unit | `uv run pytest tests/test_universe/test_scaffold.py::test_claude_md_content -x` | Wave 0 |
| UNIV-03 | Generated .mcp.json declares 4 simulation tools | unit | `uv run pytest tests/test_universe/test_scaffold.py::test_mcp_json -x` | Wave 0 |
| UNIV-04 | Universe manager create/load/list/delete | unit + integration | `uv run pytest tests/test_universe/test_manager.py -x` | Wave 0 |
| UNIV-05 | AGENTS.md is a symlink to CLAUDE.md | unit | `uv run pytest tests/test_universe/test_scaffold.py::test_agents_md_symlink -x` | Wave 0 |
| UNIV-06 | tick_summaries/ with ticks/, batches/, epochs/ subdirs | unit | `uv run pytest tests/test_universe/test_scaffold.py::test_tick_summaries_dir -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `pyproject.toml` with `[tool.pytest.ini_options]` -- test config
- [ ] `tests/conftest.py` -- shared fixtures (tmp universe dir, cleanup)
- [ ] `tests/test_universe/test_manager.py` -- covers UNIV-04
- [ ] `tests/test_universe/test_scaffold.py` -- covers UNIV-01, UNIV-02, UNIV-03, UNIV-05, UNIV-06
- [ ] Framework install: `uv add --dev pytest`

## Security Domain

Security enforcement is enabled (default). However, Phase 0 has minimal security surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A -- local CLI tool |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A -- single user |
| V5 Input Validation | Yes | Pydantic for universe name validation; slugify for safe filesystem names |
| V6 Cryptography | No | N/A |

### Known Threat Patterns for Phase 0

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via universe name | Tampering | `python-slugify` strips path separators; validate slug contains no `/`, `..`, or null bytes |
| Symlink following on delete | Tampering | `shutil.rmtree` on resolved path; verify path is under universes dir before delete |

## Sources

### Primary (HIGH confidence)
- [Claude Code MCP docs](https://code.claude.com/docs/en/mcp) -- `.mcp.json` format, project scope, env var expansion [VERIFIED: WebFetch]
- [uv project docs](https://docs.astral.sh/uv/guides/projects/) -- src-layout, `uv init --package` [VERIFIED: tested locally]
- [python-slugify PyPI](https://pypi.org/project/python-slugify/) -- v8.0.4 [VERIFIED: `pip index versions`]
- [AGENTS.md specification](https://developers.openai.com/codex/guides/agents-md) -- just standard Markdown, no special format required [CITED: OpenAI Codex docs]

### Secondary (MEDIUM confidence)
- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/) -- `XDG_DATA_HOME`, `XDG_CONFIG_HOME` defaults [ASSUMED -- well-known standard]

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified, versions confirmed, greenfield project with no compatibility concerns
- Architecture: HIGH -- patterns are straightforward file/folder operations with well-understood tools
- Pitfalls: MEDIUM -- symlink and MCP discovery pitfalls are based on general knowledge, not project-specific experience

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (stable domain, 30-day validity)
