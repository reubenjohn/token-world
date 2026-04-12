<!-- generated-by: gsd-doc-writer -->
# theact Patterns — Reusable Architecture Reference

**Researched:** 2026-04-11
**Source:** Subagent exploration of `~/workspace/theact` codebase and git history
**Confidence:** HIGH (direct code inspection; commit hashes cited)

## Summary

`theact` is a text-RPG engine where an LLM narrator drives a persistent story session. Though it targets a different problem — narrative games driven by the OpenAI API — its save management, git-per-instance versioning, creator scaffolding, and playtest/quality infrastructure contain directly transferable patterns for Token World. This document catalogues what is worth reusing, how it maps to Token World concepts, and where the architectural goals diverge.

---

## Pattern 1: Game/Save Scaffolding

### What theact does

`theact` separates read-only **game templates** from mutable **save instances**:

```
games/<game-id>/          # Read-only template (committed to repo)
  game.yaml
  world.yaml
  characters/*.yaml
  chapters/*.yaml

saves/<save-id>/          # Mutable instance (created at runtime)
  game.yaml               # Copied from template
  world.yaml              # Copied from template
  characters/*.yaml       # Copied from template
  chapters/*.yaml         # Copied from template
  state.yaml              # Runtime state (mutable)
  conversation.yaml       # Chat history
  summaries.yaml          # Chapter summaries
  memory/                 # Per-character memory files
  .git/                   # Per-instance versioning (Pattern 2)
```

**Key code locations:**
- `create_save()` — `src/theact/io/save_manager.py` (commit `8b3d147`): copies the game template into a new save directory, then adds runtime-only files (`state.yaml`, `conversation.yaml`, `summaries.yaml`, `memory/`)
- `write_game_files()` — `src/theact/creator/writer.py` (commit `a2bc4a7`): creates game template folders from LLM-generated data
- Interactive creation flow — `src/theact/creator/session.py` (commit `a2bc4a7`): LLM-driven wizard that builds a game template through a conversation
- `THEACT_DATA_DIR` env var (commit `138274d`): makes the `games/` and `saves/` root relocatable for testing and deployment

### Token World mapping

| theact concept | Token World concept | Notes |
|---------------|---------------------|-------|
| game template | universe template (future) | Not needed in v1 — universes are generated, not instantiated from templates. Defer. |
| save instance | universe | Each universe is a self-contained simulation directory |
| `create_save()` | `create_universe()` in universe manager | Same pattern: allocate directory, write runtime files |
| `THEACT_DATA_DIR` | `TOKEN_WORLD_DATA_DIR` | Relocatable universe root for testing and deployment |
| creator session | universe creation wizard | LLM-driven interactive bootstrap of universe config and seed world |

### Token World universe directory structure

Derived from the theact save pattern, adapted for the Token World runtime:

```
universes/<universe-id>/
  CLAUDE.md               # Generated: world rules, tool docs, current state summary
  AGENTS.md               # Symlink → CLAUDE.md (harness portability)
  .mcp.json               # Simulation tools: resume_tick, rollback, list_mechanics
  universe.db             # SQLite: graph state, event log, snapshots
  mechanics/              # Flat Python modules (versioned with the universe git repo)
    pickup.py             # One Mechanic subclass with class attributes (id, description, voluntary, tags)
    temperature.py
    movement.py
    _helpers.py           # Shared helpers (underscore prefix = non-Mechanic content)
    _spatial.py
  agents/                 # Resident agent configs
    agent-001.yaml        # Personality, memory refs
  .git/                   # Per-universe versioning (Pattern 2)
```

**Key additions over theact's save structure:**
- `CLAUDE.md` / `AGENTS.md` — instruction files for agent harnesses; theact has no equivalent (it drives the API directly, not the other way around)
- `.mcp.json` — exposes simulation operations as MCP tools; theact has no tool layer
- `universe.db` — SQLite replaces theact's YAML files; better for graph queries and atomic multi-table writes
- `mechanics/` — flat Python modules with class attributes (id, description, voluntary, tags); shared helpers as `_*.py` modules; theact has no equivalent (its rules are in prompts, not executable code)

### What to port

- `create_save()` pattern → `create_universe()`: allocate UUID, create directory, initialize `universe.db`, generate `CLAUDE.md`, write `.mcp.json`, init git repo
- `list_saves()` / `load_save()` → `list_universes()` / `load_universe()`: index from directory listing + `universe.db` metadata
- `THEACT_DATA_DIR` → `TOKEN_WORLD_DATA_DIR`: env var to override the universe root; used in tests to point at a tmpdir

---

## Pattern 2: Git-Per-Instance Versioning

### What theact does

Each save gets its own git repository. The versioning layer is in `src/theact/versioning/git_save.py` (commit `882b8a5`) and exposes three operations:

| Function | Effect |
|----------|--------|
| `init_repo()` | `git init` inside the save directory |
| `commit_turn()` | `git add -A && git commit -m "Turn N"` after each narrative turn |
| `undo()` | `git reset --hard HEAD~1` to revert the last turn |
| `get_history()` | `git log --oneline` to list all turns |

This gives undo, history, and diff for free with no custom infrastructure.

### Token World mapping

The same pattern applies to universes, with per-tick commits rather than per-turn commits. Git tracks everything inside `universes/<universe-id>/` including mechanic code changes, agent config changes, and the database file.

**Commit strategy for Token World:**

```
universes/<universe-id>/.git/
  Commit: "Init universe <id>"         # create_universe()
  Commit: "Tick 1 — agent moved north" # after each simulation tick
  Commit: "Mechanic: pickup added"     # when a new mechanic is generated
  Commit: "Snapshot: tick-42"          # explicit rollback point
```

**Rollback:** `git reset --hard <commit-hash>` to restore universe state (including `universe.db`) to any prior tick. This covers both mechanic code and graph state in a single operation.

**Note on `universe.db` and git:** SQLite `.db` files are binary. Git stores them as blobs — diffs are meaningless but the file is correctly versioned. If diff readability matters later, consider committing a JSON export of the graph alongside the DB. Not needed for v1.

### What to port

- `init_repo()` pattern: call `git init` at end of `create_universe()`
- `commit_turn()` pattern: call after every simulation tick, with message `"Tick {n} — {action_summary}"`
- `undo()` pattern: expose as `rollback_universe(n_ticks=1)` in the universe manager
- `get_history()` pattern: expose as `universe_history()` returning list of (tick, commit_hash, message)

---

## Pattern 3: Creator Session (LLM-Driven Setup Wizard)

### What theact does

`src/theact/creator/session.py` (commit `a2bc4a7`) runs an interactive LLM conversation that builds a game template. The user describes the world they want; the LLM proposes structure; the session writes the resulting YAML files via `write_game_files()`.

### Token World mapping

A universe creation wizard follows the same shape: the user (or orchestrating agent) describes the kind of world to simulate; the wizard generates initial graph nodes (locations, objects, characters), seed mechanics, and the resident agent's personality, then writes them into `universe.db` and commits.

This maps to a `create_universe()` flow that accepts either:
- **Guided mode:** interactive prompts to the operator
- **Automated mode:** a single description string passed programmatically (used by orchestrating agents)

Not needed for v1's core loop, but the theact implementation is a low-effort starting point when the creation wizard is built.

---

## Pattern 4: Playtest and Quality Infrastructure

`theact` has a comprehensive playtest and quality system that addresses a real problem in LLM-driven simulations: you cannot tell if the system is working correctly without running it end-to-end at scale and measuring the output.

### Components (all in `src/theact/playtest/` and `tests/`)

| Component | theact location | What it does |
|-----------|----------------|--------------|
| `PlaytestRunner` | `src/theact/playtest/runner.py` | Runs N turns of a game, produces structured JSON reports |
| `PlayerAgent` | `src/theact/playtest/player_agent.py` | LLM player with adversarial injection: 15% edge cases, 3% nonsense, 3% repeated actions |
| Quality scoring | `src/theact/playtest/scoring.py` | Per-turn composite score (coherence, grounding, novelty) |
| Golden scenarios | `tests/golden_scenarios/*.yaml` | Scripted multi-turn sequences with structural assertions on output |
| A/B testing | `scripts/ab_test.py` | Compare prompt variants using seeded inputs |
| Turn debugger | (hot-reload mode) | Sub-second prompt iteration with live reloading |
| Fixture capture | (debug pipeline) | Debug failures automatically become regression test fixtures |
| Diagnostics filesystem | (per-run dumps) | Per-turn dumps: system prompts, raw responses, parsed output |
| Prompt lint tests | (CI) | Enforce token budget limits per agent type |
| Context profiler | (tooling) | Compute token usage and headroom per agent |
| Dev server manager | (tooling) | PID-file-managed server; agents can self-serve a live inspection UI |
| Scoped bash permissions | `.claude/settings.json` | Allowlist for agent-driven bash commands (agent autonomy) |

### Why this matters for Token World

Token World's central risk (documented in SUMMARY.md) is **mechanic incoherence** and **ungrounded observation drift** — two failure modes that are invisible without automated multi-turn testing. A playtest harness running 50-100 ticks with an adversarial player agent is the only practical way to catch:

- Mechanics that silently fail their precondition check (agent can never pick anything up)
- Observation drift (LLM describes world state not present in the graph)
- Mechanic generation loops (same mechanic regenerated each tick)
- Agent memory explosion (context window fills and agent starts repeating actions)

### Token World playtest plan

Adapt the theact pattern with the following Token World specifics:

**`SimPlaytestRunner`** — run N simulation ticks, produce a structured report with:
- Per-tick: action text, classified mechanic, graph mutations applied, observation returned
- Summary: unique mechanics generated, graph node count, avg observation length, grounding score

**`SimPlayerAgent`** — adversarial resident agent with injection:
- 10% physically impossible actions (e.g., "fly to the moon") — tests precondition rejection
- 5% nonsense actions (e.g., "glorfindel the wazzock") — tests action classifier fallback
- 5% repeated actions — tests mechanic idempotency

**Golden scenarios** — scripted multi-tick YAML:
```yaml
scenario: basic_pickup
ticks:
  - action: "pick up the apple"
    assert:
      mechanic_name: pickup
      graph_mutations:
        - type: remove_edge
          from: location:forest
          to: object:apple
        - type: add_edge
          from: agent:alice
          to: object:apple
          label: has
```

**Grounding score metric** — after each observation, verify every factual claim against the graph. Count verified / total claims. Target: > 0.90.

**Diagnostics filesystem** — per-tick dumps at `universes/<id>/diagnostics/tick-<n>/`:
- `action.txt` — raw agent output
- `classification.json` — classifier structured output
- `mechanic.py` — copy of the mechanic module file executed (e.g. `mechanics/<id>.py`)
- `mutations.json` — graph mutations applied
- `observation.txt` — final observation returned to agent

### When to build it

Defer until Phase 4 (Simulation Engine) is complete and the loop runs end-to-end. The playtest harness is most valuable after there are real mechanics to test and real observations to score. Building it in Phase 6 (Observability) as planned in SUMMARY.md is correct.

---

## Key Differences: theact vs Token World

| Dimension | theact | Token World |
|-----------|--------|-------------|
| Runtime | Python code drives OpenAI API | Agent SDK IS the runtime; simulation is tools |
| Control direction | Code → LLM | Agent → tools → LLM |
| State format | YAML files | SQLite (graph queries, atomic writes) |
| World rules | In LLM prompts | Executable Python mechanics in versioned folders |
| Per-instance config | No CLAUDE.md or .mcp.json | CLAUDE.md + .mcp.json generated per universe |
| Harness portability | No — tied to OpenAI SDK | Yes — any agent that reads CLAUDE.md + MCP works |
| Mechanic versioning | Not applicable | Git file-level history per mechanic module; class attributes replace meta.yaml |

The single most important architectural inversion: **theact is a program that calls an LLM**. Token World is a set of tools that an LLM calls. The game loop, state management, and rule execution all live in theact's Python code. In Token World, the simulation engine exposes those operations as MCP tools, and the resident agent (an LLM) invokes them. theact's save manager and git versioning patterns transfer cleanly across this inversion — they are infrastructure concerns, not control-flow concerns.

---

## Relevant Commits in theact

| Commit | Description |
|--------|-------------|
| `8b3d147` | Save manager: `create_save()`, `load_save()`, `list_saves()` |
| `882b8a5` | Git-based save versioning: `init_repo()`, `commit_turn()`, `undo()` |
| `e2164b0` | Lost Island example game definition (template structure reference) |
| `a2bc4a7` | Creator agent: `write_game_files()`, interactive creation session |
| `138274d` | `THEACT_DATA_DIR` env var for relocatable data |
| `081df76` | Agent prompt templates |
| `e773f01` | Context assembly |

---

## Implementation Priority for Token World

| Pattern | When | Notes |
|---------|------|-------|
| Universe manager (`create`, `load`, `list`) | Phase 1 | Foundation — needed before any simulation work |
| `TOKEN_WORLD_DATA_DIR` env var | Phase 1 | Needed for test isolation from the start |
| Git per universe (`init_repo`, `commit_tick`, `rollback`) | Phase 1 | Per PROJECT.md: "reversibility enables boldness"; invest early |
| Diagnostics filesystem | Phase 4 | Needed once the loop runs end-to-end |
| Playtest harness (runner, player agent, scoring) | Phase 6 | Per SUMMARY.md roadmap; builds on diagnostics |
| Golden scenarios | Phase 6 | Scripted regression tests for the full loop |
| Universe creation wizard | Post-v1 | Useful for onboarding; not needed for core loop |

---

*Research date: 2026-04-11*
*Valid until: codebase diverges significantly — recheck before Phase 1 implementation*
