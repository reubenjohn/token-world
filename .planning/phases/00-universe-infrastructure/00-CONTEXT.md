# Phase 0: Universe Infrastructure - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver universe scaffolding: a CLI/API that creates a self-contained universe folder (CLAUDE.md, AGENTS.md symlink, .mcp.json, universe.db, mechanics/, agents/, tick_summaries/, .git/) and a universe manager for create/load/list/delete. The creation flow is tool-driven: a human shapes the vision, the agent calls a creation tool to scaffold a template, then customizes it via file edits.

</domain>

<decisions>
## Implementation Decisions

### Project Structure
- **D-01:** src-layout — Python package lives at `src/token_world/` with `pyproject.toml` at the project root. Standard `src/` layout to prevent accidental imports of uninstalled code.
- **D-02:** Full XDG base directories — Universes stored in `$XDG_DATA_HOME/token_world/universes/` (defaults to `~/.local/share/token_world/universes/`). Config in `$XDG_CONFIG_HOME/token_world/` (defaults to `~/.config/token_world/`). Respect user overrides of XDG vars.
- **D-03:** Claude Code permissions added to `.claude/settings.json` for read/write access to the XDG data and config directories.

### CLAUDE.md Generation
- **D-04:** Operational template — Per-universe CLAUDE.md is a structured template with sections for: world rules (empty placeholder for human/agent to fill), available MCP tools with usage docs, current state summary, and constraints (grounding, no hallucinated state). No LLM generation at creation time.
- **D-05:** AGENTS.md is a symlink to CLAUDE.md by default. Harnesses that read AGENTS.md (like Codex) get the same instructions. Can be re-pointed if harnesses diverge.

### Universe Identity
- **D-06:** User-provided name at creation, slugified for the folder name (e.g., "My Test World" -> `my-test-world/`). Must be unique within the data directory. Display name stored in universe.db metadata.
- **D-07:** Empty graph at creation — no seed nodes, no edges. The world is a blank slate. First mechanics and agent actions create everything from scratch. Aligned with the "rules emerge on-the-fly" philosophy.

### Claude's Discretion
- **D-08:** MCP tool stubs — Claude decides how to implement the .mcp.json tool declarations at Phase 0 (real stubs returning "not implemented", placeholder declarations, or minimal working skeletons). The tools are: resume_tick, rollback, list_mechanics, register_mechanic.
- **D-09:** Creation flow detail — The user's vision is that everything should be exposed as tools the agent can call. Universe creation is a tool call that produces a template, then the agent modifies files directly. Claude decides the exact tool interface and creation API shape.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `docs/design/architecture.md` — System component diagrams, core simulation loop sequence diagram, universe folder structure
- `CLAUDE.md` §Technology Stack — Full recommended stack with versions, alternatives considered, and model selection strategy

### Requirements
- `.planning/REQUIREMENTS.md` §Universe Infrastructure — UNIV-01 through UNIV-06 defining the universe folder contents, manager operations, harness-agnostic design, and tick summaries

### Project Context
- `.planning/PROJECT.md` §Key Decisions — Universe instance as agent workspace, mechanics as git-versioned folders, hybrid SDK architecture, hierarchical tick summaries

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — completely greenfield. No Python files, no pyproject.toml, no src/ directory exist yet.

### Established Patterns
- None — this phase establishes the foundational patterns for the entire project.

### Integration Points
- Universe folders will be the workspace for all subsequent phases (graph, mechanics, engine, agent)
- The MCP tool stubs defined here will be implemented by Phases 1-6
- The CLAUDE.md template will be extended as new capabilities are added in later phases

</code_context>

<specifics>
## Specific Ideas

- Universe creation should be exposed as a tool the agent can call, producing a template that is then customizable via simple file edits
- The human shapes the vision, the agent scaffolds and customizes — this is the core workflow pattern for the entire project

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 00-universe-infrastructure*
*Context gathered: 2026-04-11*
