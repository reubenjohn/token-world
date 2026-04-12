<!-- generated-by: gsd-doc-writer -->
# Decision Log: Token World

This file is a chronological record of key architectural and design decisions made during
project initialization. Future agents MUST read this before making changes that touch any
of the areas covered here. Do not simplify or second-guess these decisions without
understanding the reasoning and rejected alternatives recorded below.

---

## Session: 2026-04-11 (Project Initialization)

### 1. Language: Python

**Decision:** Python for engine, framework, and generated mechanics.

**Rationale:** Rich AI/ML ecosystem, easy LLM code generation, `networkx` for graph
operations. The combination of mature tooling and low friction for LLM-generated code
outweighed other options.

**Alternatives rejected:**
- TypeScript — considered for dashboard integration but adds cross-language friction
- Both (Python engine + TS dashboard) — split-language adds operational complexity for a
  v1 hobby project

---

### 2. Knowledge Graph: NetworkX + SQLite

**Decision:** Schema-less NetworkX in-memory graph, persisted to SQLite.

**Rationale:** Flexibility over speed. New concepts must emerge dynamically without schema
migrations. In-memory graph is fine for v1 scale (hundreds to low thousands of nodes).
SQLite persistence avoids a running database server.

**Alternatives rejected:**
- Neo4j — server overhead, operational complexity
- SpacetimeDB — mentioned in ideation but overkill for v1 scope
- Typed schema with migrations — would block dynamic concept emergence, the core design goal

---

### 3. Agent Framework: Hybrid SDK

**This decision evolved through three iterations. Future agents must NOT simplify back to
either extreme — the hybrid is deliberate.**

**Final decision:** Agent SDK (any harness: Claude Code, Codex, etc.) operates at the
OPERATOR layer, orchestrating the simulation via tools. Raw Anthropic API powers the
deterministic pipeline INSIDE those tools.

**Iteration 1:** Claude Code SDK chosen for session persistence, resumption, and
fork-based rollback.

**Iteration 2:** Reverted to raw Anthropic Python SDK after analysis revealed:
- Subprocess overhead per call
- Opaque token spend (compaction/retries hidden)
- Per-call model routing fights the framework (Haiku for classification, Opus for
  generation in the same tick)
- Autonomous agent loop conflicts with deterministic engine pipeline
- System prompt layering conflicts
- Custom tool indirection via MCP wrappers

**Iteration 3 (current):** Hybrid approach. Key insight: mechanic generation IS an
iterative coding loop (write → test → fail → fix → repeat), which is exactly what agent
harnesses are built for. The operator implements mechanics using its native capabilities
(file writes, subagents), not a `generate_mechanic` tool.

**Why the hybrid boundary matters:**
- Agent SDK layer: mechanic authoring, session management, operator orchestration
- Raw API layer: deterministic engine pipeline, action classification, observation formatting
- Mixing them at the wrong layer introduces the problems discovered in Iteration 2

---

### 4. Mechanics as Flat Python Modules (Normal SDLC)

**Decision:** Each mechanic is a flat Python module (`mechanics/<id>.py`) containing a
`Mechanic` subclass with class-level attributes: `id: str`, `description: str`,
`voluntary: bool` (default True), `tags: list[str]` (default []). Shared helpers live as
normal Python modules with an underscore prefix (`mechanics/_helpers.py`,
`mechanics/_spatial.py`). Tests mirror in the project test tree
(`tests/test_mechanics/test_<id>.py`). The registry discovers mechanics by importing each
non-underscore `.py` file in `mechanics/` and collecting `Mechanic` subclasses.

**Rationale:** Authoring feels like a normal codebase — refactoring, code reuse, and
test-driven development work naturally. Class attributes replace a separate `meta.yaml`.
Git gives clean per-mechanic history via `git log -- mechanics/<id>.py`. Multi-per-file is
allowed when mechanics tightly share code, but 1:1 is the default.

**Alternatives rejected:**
- Folder-per-mechanic (`mechanics/<id>/mechanic.py` + `tests/` + `meta.yaml`) — originally
  chosen, but added ceremony without leverage; meta.yaml duplicates class attributes; test
  colocation fights the rest of the project's test layout.

**Key insight from user:** A separate git repo for mechanics inside a universe is overkill.
Mechanics are part of the universe folder, versioned together with the world state.

---

### 5. Universe as Self-Contained Agent Workspace

**Decision:** Each universe is a folder with the following structure:

```
universe_name/
  CLAUDE.md          # world operating system — instructions for the operator
  AGENTS.md          # symlink (harness portability)
  .mcp.json          # MCP tool configuration
  universe.db        # SQLite persistence
  mechanics/         # flat Python modules (`<id>.py`) + `_*.py` helpers; versioned with the universe
  agents/            # agent state
  tick_summaries/    # hierarchical memory
  .git/
```

**Rationale:** Harness-agnostic. Works with any agent coding harness that reads instruction
files and MCP. Inspired by the `theact` game/save pattern. The `CLAUDE.md` becomes the
world's operating system.

**Key insight from user:** The industry is standardizing on agent coding harnesses. The
universe folder should work with Claude Code, Codex, or any future harness. The `AGENTS.md`
symlink provides portability across harnesses.

---

### 6. Minimal MCP Tools (3 only)

**Decision:** Expose exactly three MCP tools: `resume_tick`, `rollback`, `list_mechanics`.

**Rationale:** The operator accesses universe state directly via filesystem and SQLite.
No wrapper tools are needed for inspection — good `CLAUDE.md` instructions plus
convenience CLI scripts provide more leverage than bespoke MCP wrappers.

**Key insight:** `generate_mechanic` was removed because the operator IS the mechanic
generator. It uses its native coding capabilities (file writes, subagents) to author
mechanics as normal Python modules. `resume_tick` auto-scans `mechanics/` and validates
on each tick; a CLI `validate-mechanic <id-or-file>` gives fast pre-tick feedback using
the same validation pipeline.

**Note on `register_mechanic`:** Originally planned as a 4th MCP tool; superseded by
auto-scan + CLI in Phase 4 reframe. Wrapping registration in a tool obscured the process
and added indirection with no benefit once mechanics became flat importable modules.

**Fewer tools, more leverage** is the guiding principle here.

---

### 7. Hierarchical Tick Summaries

**Decision:** Per-tick JSON summaries, compressed hierarchically:
- Level 1: individual tick
- Level 2: batch of 100 ticks
- Level 3: epoch of 100 batches (10,000 ticks)

**Rationale:** Agent-resilient memory. Survives context compaction, enables operator
handoff, and is readable by any tool. Analogous to commit messages at different scales.

If the top-level agent compacts or a new agent takes over, it reads the latest summaries
and catches up without needing to replay raw tick data.

---

### 8. Model Routing

**Decision:**
- Opus — mechanic generation
- Sonnet — engine/observation formatting
- Haiku — action classification

**Rationale:** Mechanic generation is the core value of the system. Code quality justifies
Opus cost. Action classification is structurally simple — Haiku is sufficient. Engine
observation formatting is moderate complexity — Sonnet balances quality and cost.

**Important note:** Research docs (`STACK.md`, `ARCHITECTURE.md`) recommend Sonnet for
mechanic generation. This was overridden by explicit user decision. Those research docs
are stale on this point. Do not revert to Sonnet for mechanic generation based on those
docs alone.

---

### 9. No Sandboxing for v1

**Decision:** Generated mechanic code runs with direct `exec()`.

**Rationale:** Hobby project. Mechanics operate on a controlled API surface with a known
call graph. The risk is acceptable at this scale.

**Future path:** Add `RestrictedPython` when scaling or if issues arise in practice.

---

### 10. Testing Philosophy: Small / Medium / Large

**Decision:** Tests are sized and run at different frequencies.

| Size | Scope | Frequency |
|------|-------|-----------|
| Small (unit) | Mechanic preconditions/side effects against mock graphs | Every change |
| Medium (integration) | Multi-mechanic chains, persistence round-trips | Per-phase |
| Large (LLM-verified) | Full agent-in-the-loop with rubric-based verification | Milestone boundaries |

**Key insight from user:** LLM-verifier regression tests with pre-defined rubrics catch
grounding drift. System prompt changes should trigger Large tests. The rubric approach
allows asserting semantic correctness, not just structural output validity.

---

### 11. Use Case Library Before Engine

**Decision:** Phase 3 (Design Validation) comes before Phase 5 (Simulation Engine).

**Rationale:** Building a library of use cases surfaces architectural gaps that would
otherwise be discovered too late in implementation.

**Example that motivated this decision:** The walking-to-park use case revealed the need
for action duration and attention thresholds — concepts entirely absent from requirements
until the use case was explored. Discovering this after the engine was built would require
expensive rework.

---

## Meta-Principles (from user)

These apply to every future agent session in this project.

### "Don't Take Documentation for Granted"

Future agents must VERIFY that documentation is correct, not just read and trust it.
Research docs can be stale. `CLAUDE.md` can have contradictions. Requirements can be
incomplete. Every agent session should include a consistency check between what the docs
say and what the code does.

Specific known staleness: `STACK.md` and `ARCHITECTURE.md` recommend Sonnet for mechanic
generation. The actual decision (Decision 8 above) is Opus.

### Operating Principles (also persisted in PROJECT.md)

1. **Aggressive subagent delegation** — break work into parallel subagent tasks where possible
2. **ROI awareness** — choose models, tools, and approaches proportional to the value they
   deliver; do not use Opus for classification tasks
3. **Self-improving infrastructure** — context engineering, dogfooding, and continuous
   retrospective are first-class work, not optional polish
4. **Composition over specialization** — small composable mechanics beat a single monolithic
   simulation; small composable tools beat a single complex tool
5. **Reversibility enables boldness** — prefer designs that can be rolled back; this is why
   git versioning of mechanics matters
6. **Ground truth obsession** — always check the actual code, not just the docs; run the
   tests, not just read them
