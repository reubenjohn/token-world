# Phase 0: Universe Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 0-universe-infrastructure
**Areas discussed:** Project structure, CLAUDE.md generation, Universe identity

---

## Project Structure

### Python Package Layout

| Option | Description | Selected |
|--------|-------------|----------|
| src/token_world/ | Standard src-layout. Prevents accidental imports of uninstalled code. pyproject.toml at root, all source under src/token_world/. | ✓ |
| token_world/ (flat) | Simpler layout. Package at root level. Easier for quick iteration but can cause import issues. | |

**User's choice:** src/token_world/ (Recommended)
**Notes:** None

### Universe Folder Location

| Option | Description | Selected |
|--------|-------------|----------|
| universes/ in project root | Universes live alongside the source code in a top-level universes/ directory. Easy to find, git-ignored by default. | |
| Configurable path | Default to ~/token_worlds/ or respect an env var (TOKEN_WORLD_DIR). Universes are fully decoupled from the source repo. | ✓ |
| Inside project, tracked | Universes live in universes/ and are tracked by the parent git repo. | |

**User's choice:** Configurable path, with default at ~/.local/share/token_world (XDG convention)
**Notes:** User corrected the default location to follow XDG conventions

### XDG Base Directories

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, full XDG | Universes in $XDG_DATA_HOME/token_world, config in $XDG_CONFIG_HOME/token_world. Follows Linux convention. | ✓ |
| Simple default + env override | Default to ~/.local/share/token_world, override with TOKEN_WORLD_DIR env var only. | |

**User's choice:** Yes, full XDG (Recommended)
**Notes:** None

---

## CLAUDE.md Generation

### Per-Universe CLAUDE.md Content

| Option | Description | Selected |
|--------|-------------|----------|
| Operational template | Structured template with world rules (empty), MCP tools + usage, current state, constraints. Agent/human fills in content after creation. | ✓ |
| LLM-generated seed | LLM generates initial world-building content based on name/theme. Costs an API call per universe. | |
| Minimal skeleton | Just tool docs and constraints. No world rules section. | |

**User's choice:** Operational template (Recommended)
**Notes:** None

### AGENTS.md Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Symlink to CLAUDE.md | AGENTS.md -> CLAUDE.md by default. Harnesses that read AGENTS.md get same instructions. | ✓ |
| Separate file, shared template | AGENTS.md is its own file with harness-agnostic instructions. | |

**User's choice:** Symlink to CLAUDE.md (Recommended)
**Notes:** None

---

## Universe Identity

### Naming/Identification

| Option | Description | Selected |
|--------|-------------|----------|
| User-provided name | User gives a name at creation, slugified for folder. Must be unique. | ✓ |
| Auto-generated + optional name | UUID/timestamp ID for folder, optional display name in metadata. | |

**User's choice:** User-provided name (Recommended)
**Notes:** None

### Initial Graph State

| Option | Description | Selected |
|--------|-------------|----------|
| Empty graph | No nodes, no edges. Blank slate. First mechanics create everything. | ✓ |
| Minimal seed node | One 'world' root node as anchor point. | |
| You decide | Claude picks best approach. | |

**User's choice:** Empty graph (Recommended)
**Notes:** None

---

## Claude's Discretion

- MCP tool stubs (.mcp.json) — Claude decides implementation approach at Phase 0
- Creation flow API design — exposed as tools, template-based, customizable via file edits

## Deferred Ideas

None — discussion stayed within phase scope
