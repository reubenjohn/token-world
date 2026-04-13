# Phase 4: Mechanic Authoring & Validation Infrastructure - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

> **Reframe note:** The roadmap title for this phase is "LLM Mechanic Generation". Under the inversion-of-control model clarified in this discussion (see D-01), Phase 4 does NOT build a bespoke generation pipeline. It delivers the authoring infrastructure + validation gate + diagnostics + test harness that lets the top-level coding agent (Claude Code + Opus, via the Agent SDK operator layer) author mechanics as normal Python code. The phase is informally titled "Mechanic Authoring & Validation Infrastructure" in this context; the roadmap name is retained for numeric identity.

<domain>
## Phase Boundary

Deliver everything required for the top-level coding agent to author mechanics as an ordinary Python codebase that the simulation can safely execute:

1. A **flat mechanic layout** (supersedes Phase 2 D-15) that enables code reuse, normal SDLC, and clean per-file git history.
2. A **validation pipeline** — syntax, AST rules, import, class contract, tests, and dry-execute smoke — exposed via CLI and invoked automatically by registry scan on every `resume_tick`.
3. A **diagnostics filesystem substrate** (AUTO-02) — per-tick folders capturing prompts, raw LLM responses, parsed output, execution traces, mutations, and observations. Phase 4 builds the sinks and schema; Phase 5 wires the actual simulation-tool LLM calls into it.
4. An **integration test harness** (TEST-02) built on Phase 3's use-case action-observation manifests, exercising multi-mechanic chain execution.
5. **Authoring guides** (framework-level in `docs/guides/` plus universe-local in scaffolded CLAUDE.md) so the operator can author mechanics effectively.

Explicitly OUT of scope for this phase:
- The simulation engine itself (Phase 5): action classification, mechanic matching from text, observation synthesis, conservation enforcement.
- Agent runtime / end-to-end loop (Phase 6).
- Runtime sandboxing / RestrictedPython (v2).
- Multi-agent coordination (v2).

</domain>

<decisions>
## Implementation Decisions

### Generation Model — Inversion of Control
- **D-01:** The top-level coding agent (Claude Code + Opus, via Agent SDK operator layer per PROJECT.md Hybrid SDK decision) authors mechanics using normal file-writing tools. No bespoke LLM code-generation pipeline is built. When the simulation engine (Phase 5) encounters an unmatched action, it halts the tick and yields to the operator, which authors the needed mechanic as Python code, then resumes the tick.
- **D-02:** "MECH-03: LLM generates valid Python mechanics" is satisfied by the operator (Opus via Claude Code) writing mechanics, validated by Phase 4's pipeline. "Generation" = ordinary SDLC by a capable coding agent.

### Mechanic Layout — Supersedes Phase 2 D-15
- **D-03:** Mechanics live as flat Python modules. Default: one mechanic per file at `mechanics/<id>.py`, containing exactly one `Mechanic` subclass. Multi-mechanic files allowed only when two or more mechanics tightly share code/intent (judgement call during authoring; not enforced).
- **D-04:** Class attributes replace `meta.yaml` entirely. The `Mechanic` base class declares defaults for:
  - `id: str` (required; no default)
  - `description: str` (required; no default)
  - `voluntary: bool = True`
  - `tags: list[str] = []`
  `meta.yaml` files are deleted from seeds and never created by the scaffold.
- **D-05:** Shared helpers live as underscore-prefixed Python modules alongside mechanics: `mechanics/_helpers.py`, `mechanics/_spatial.py`, etc. The underscore prefix is the registry's cue to skip them during discovery. Mechanics may freely import from sibling `_*.py` modules.
- **D-06:** Tests live in the project's test tree, mirroring module layout: `tests/test_mechanic/test_seeds/test_<id>.py` for built-in seeds; `tests/test_mechanics/test_<id>.py` inside each universe for universe-local mechanics. Tests are NOT colocated with mechanic files.
- **D-07:** Registry discovery (replaces folder walker): loader imports every `<name>.py` in the mechanics directory where `<name>` does not start with `_` and is not `__init__.py`. For each imported module, it collects classes that subclass `Mechanic` (excluding `Mechanic` itself) and indexes them by their class-level `id`.
- **D-08:** Per-mechanic git history: `git log -- mechanics/<id>.py` gives clean history for single-mechanic files. No commit-message convention required. For rare multi-mechanic files, history is shared across the mechanics in that file (acceptable tradeoff).

### Seed Migration
- **D-09:** Flatten seeds:
  ```
  src/token_world/mechanic/seeds/
  ├── __init__.py
  ├── movement.py                    # class Movement(Mechanic)
  ├── observation.py                 # class Observation(Mechanic)
  ├── environmental_reaction.py      # class EnvironmentalReaction(Mechanic)
  └── _helpers.py                    # (empty at first; for shared utilities as duplication emerges)
  ```
  Tests migrate to `tests/test_mechanic/test_seeds/test_movement.py` etc.
- **D-10:** Universe scaffolding (`universe/scaffold.py`) copies the flat seed `.py` files (and `_helpers.py`) into `universe/mechanics/`. It also creates `universe/tests/test_mechanics/` with mirrored starter tests. Scaffolding never creates subfolders inside `mechanics/`.

### Code-Reuse Style — Claude's Discretion
- **D-11:** Default to free functions in `_*.py` helper modules over base-class inheritance. Base classes (e.g. `SpatialMechanic(Mechanic)`) are only introduced when a clear shared pattern emerges across ≥3 mechanics and the inheritance pays for itself. Refactor opportunistically as the mechanic library grows.

### Validation Pipeline (MECH-04)
- **D-12:** A single validation implementation at `token_world.mechanic.validation.validate(module_path: Path) -> ValidationReport`. All entry points call it; the checks are identical regardless of invocation path.
- **D-13:** Validation stages (atomic; stop at first hard failure and surface all accumulated issues):
  1. **Syntax** — `ast.parse` on the module source
  2. **Static AST rules** (see D-14)
  3. **Import** — `importlib.import_module(...)` succeeds without raising
  4. **Class contract** — module contains ≥1 `Mechanic` subclass with required attrs (`id: str`, `description: str`), `check` method, `apply` method, correct signatures (`check(self, ctx) -> CheckResult`, `apply(self, ctx) -> list[Mutation]`)
  5. **Own tests pass** — if `tests/test_mechanics/test_<id>.py` exists, run it via pytest; must pass
  6. **Dry-execute smoke** — instantiate the class; call `check(ctx)` with a minimal fixture context (empty graph + claimable actor/target); no exceptions
- **D-14:** AST rules enforced on mechanic modules:
  - **Required:** module has at least one class that subclasses `Mechanic` (directly or transitively); each such class has class-level `id: str` and `description: str`.
  - **Forbidden imports:** `networkx`, `networkx.*`, any `_KnowledgeGraph`-internal module, `token_world.graph.knowledge_graph` direct import (must go through `MechanicContext`).
  - **Forbidden calls:** `eval`, `exec`, `__import__`, `compile`, `globals`, bare `open` (pathlib wrapping allowed for pytest fixtures).
  - **Allowed imports:** `token_world.mechanic.*` public API (`Mechanic`, `MechanicContext`, `CheckResult`, `Mutation`, matcher primitives), sibling `_*.py` helpers within the same mechanics directory, Python stdlib.
- **D-15:** Entry points:
  - **CLI:** `validate-mechanic <universe> <id-or-path>` — prints structured report; exit code 0 on pass, non-zero on fail. Fast feedback without running a tick.
  - **Registry auto-scan:** on every `resume_tick`, the registry re-scans `mechanics/`; invalid mechanics are excluded from the live index, and validation failures are logged to `diagnostics/validation/<timestamp>_<mechanic-id>/report.json`. Valid mechanics load silently.
- **D-16:** On pipeline failure, `ValidationReport` includes: stage that failed, rule that triggered, file:line:column (for AST stages), message, and accumulated non-blocking warnings. The CLI prints them; the registry auto-scan writes them to diagnostics.

### Retry / Repair — Explicitly Not a Pipeline
- **D-17:** No retry loop, no prompt-repair plumbing. The operator iterates naturally: reads validation errors (or test failures), edits the code, re-runs validation. This is the expected behavior of a coding agent doing SDLC; no additional infrastructure required.

### Prompt Context Assembly — Replaced by High-Quality Docs
- **D-18:** No prompt-assembly pipeline. The operator reads the codebase (framework API, DSL reference, existing mechanics) to orient itself. Phase 4's job is to make that reading high-quality via authoring guides (see D-26..D-28).

### MCP Tool Surface — Supersedes Prior "register_mechanic" Scope
- **D-19:** Drop `register_mechanic` from the MCP tool set. The minimal MCP tools become: `resume_tick`, `rollback`, `list_mechanics`. The operator writes mechanic files with its own coding tools; `resume_tick` auto-scans and validates; `validate-mechanic` CLI provides fast pre-tick feedback. This simplifies the tool surface and matches the "universe = codebase" model.
- **D-20:** Update references across the codebase (MCP stub server, universe CLAUDE.md template, tests) to reflect the three-tool surface. This is part of plan 04-01.

### Diagnostics Filesystem (AUTO-02)
- **D-21:** Per-tick diagnostics directory layout:
  ```
  universe/diagnostics/tick_<tick_id>/
  ├── action.txt                  # raw resident agent action
  ├── classification/
  │   ├── prompt.txt              # full system + user prompt sent to Haiku
  │   ├── response.txt            # raw response
  │   └── parsed.json             # structured action
  ├── matching.json               # which mechanic(s) matched, match reasons
  ├── execution/
  │   ├── trace.json              # chain execution tree (from Phase 2's ExecutionTrace)
  │   └── mutations.jsonl         # one Mutation per line
  ├── observation/
  │   ├── prompt.txt              # observer prompt to Sonnet
  │   ├── response.txt            # raw response
  │   └── parsed.json             # filtered observation text + metadata
  └── summary.json                # tick_id, action, mechanics fired, tokens, duration, status
  ```
- **D-22:** Validation diagnostics layout:
  ```
  universe/diagnostics/validation/<iso_timestamp>_<mechanic-id>/
  ├── report.json                 # full ValidationReport
  ├── ast_errors.json             # if AST stage failed
  └── test_output.txt             # pytest output if tests ran
  ```
- **D-23:** Diagnostics sink API: a `DiagnosticsSink` class with methods like `sink.open_tick(tick_id)`, `ctx.write_prompt(...)`, `ctx.write_response(...)`, `sink.close_tick(summary)`. Phase 5 wires the classifier/observer calls into this sink; Phase 4 exercises it via validation runs and integration-test runs.
- **D-24:** Schema versioning: `summary.json` carries `"schema_version": 1`. Future increments bump this; tooling that reads diagnostics checks compatibility.
- **D-25:** Retention: no automatic rotation in v1. CLI `prune-diagnostics <universe> [--before-tick N | --before-date YYYY-MM-DD]` for manual pruning. Explicit, operator-controlled.

### Integration Test Harness (TEST-02)
- **D-26:** pytest-based harness at `tests/test_integration/test_use_cases.py`. Loads Phase 3's use-case manifests (structured action-observation pairs) and parametrizes tests across them.
- **D-27:** Each parametrized test:
  1. Constructs a `KnowledgeGraph` from the use case's precondition state (using `GraphBuilder` from `tests/test_graph/conftest.py` or an equivalent).
  2. Invokes the mechanic chain execution engine (Phase 2) with the action payload.
  3. Asserts: mutations match the use case's expected mutations (or superset, if non-determinism exists); observation-relevant state matches; any expected involuntary chain fires.
- **D-28:** Use-case manifest loader ALREADY EXISTS at `src/token_world/use_cases/loader.py` (built in Phase 3). Phase 4 consumes it directly — does NOT reimplement it. Phase 4 fixes the CRLF bug (M-04 in 03-REVIEW.md) so Windows-authored manifests load correctly; this is prep work for plan 04-04.
- **D-29:** Failing tests include the use case ID, path, and a minimal repro instruction. The harness is the foundation for Phase 6's DVAL-03 regression suite; Phase 4 ships just the harness + use-case-driven tests, not the full agent-loop regression.
- **D-29b:** Use-case coverage expectation: some use cases will PASS (those backed by existing or Phase-4-authored seed mechanics); others will yield a "no matching mechanic" signal until Phase 5 classifier routing is built OR the missing mechanic is authored here. The harness marks both as valid outcomes based on the use case's declared expected result. A use case is only a FAILURE when its expected mechanic fires but produces wrong mutations/observations.

### Authoring Guides
- **D-30:** `docs/guides/authoring-mechanics.md` — developer-facing reference. Contents: Mechanic class contract, DSL reference (`MechanicContext` methods), common patterns (voluntary vs involuntary, matcher declaration, chain triggering), anti-patterns (no raw graph access, no forbidden imports), worked examples referencing the seed mechanics.
- **D-31:** Universe-local authoring: the scaffolded universe CLAUDE.md gets a "Mechanic Authoring" section that links to a copied `docs/authoring-mechanics.md` inside the universe (keeping universes self-contained per PROJECT.md). The universe CLAUDE.md template (`src/token_world/universe/templates/claude_md.py`) is updated accordingly.
- **D-32:** `scaffold-mechanic <universe> --id <id> [--voluntary|--involuntary]` — thin CLI helper that emits a skeleton module (class with empty `check`/`apply`) and a test stub. Purely a convenience; the operator can also write files directly.

### Phase 3 Code Fixes — Prerequisite Work
- **D-33:** Phase 4's first plan absorbs two Phase 3 code review findings that directly affect Phase 4 deliverables:
  - **H-01 (HIGH)** — `TemporalIndex.find_state_at_tick` ignores `add_node` events during replay, producing empty state on remove-then-readd sequences. Fix per 03-REVIEW.md line 71: add an `add_node` branch that seeds state from the event payload; add a regression test covering add → remove → add across a snapshot boundary. Required before integration tests exercise resource/crafting use cases.
  - **M-04 (MEDIUM)** — `src/token_world/use_cases/loader.py` rejects CRLF-encoded frontmatter. Fix to accept both `---\n` and `---\r\n` delimiters. Required before plan 04-04 parametrization works cross-platform.
  These fixes land in plan 04-01 (alongside the flatten) so the rest of the phase operates on a clean base.

### Interpretation of GAP-HANDOFF.md Entries Under Inversion of Control
- **D-34:** `GAP-ENG16` (nonsense-verb mechanic-generation pollution) — under inversion of control, the registry only accepts mechanics the operator writes as files. Garbage isn't auto-generated. This gap splits:
  - **Phase 5 responsibility** — the classifier must return `no_viable_action` for obvious nonsense rather than signaling "no matching mechanic" and yielding to the operator. Belongs with GAP-ENG15.
  - **Phase 4 responsibility** — the validation gate (D-12..D-16) rejects any authored mechanic that fails contract/AST checks. The "manual-review queue" from the original gap description is unnecessary: the operator IS the review step, in real time.
- **D-35:** `GAP-MECH19` (trust boundary for `source='llm_generated'`) — under inversion of control there is no trust distinction; all mechanics are operator-authored. The validation gate runs on every mechanic regardless of origin. `source` and `reviewed` metadata fields are not introduced; the gap's original framing is obsolete.

### Seed Mechanic Authoring — Scope Addition
- **D-36:** Phase 4 authors the 27 seed mechanics (MECH01–MECH27) identified in GAP-HANDOFF.md as part of the phase, not as deferred work. Rationale:
  - Integration tests become meaningful (use cases exercise real mechanics rather than yield signals).
  - Dogfoods the authoring experience end-to-end: validation gate, authoring guide, `_helpers.py` reuse patterns, `scaffold-mechanic` CLI. Surfaces friction before Phase 5 depends on the loop.
  - Phase 5 (simulation engine) can assume a baseline of seed mechanics exists, simplifying its own plan.
  - Adds ~1500–3000 LOC across 27 files. Natural parallelization: groups of thematically-related mechanics can be authored in waves by subagents, following the Phase-3 wave model.
- **D-37:** Authoring approach — each seed mechanic plan authors a small thematically-related cluster (e.g., "object interaction seeds" for MECH07/MECH08/MECH14/MECH15; "environmental family" for MECH20/MECH21/MECH22/MECH24; "spatial movement extensions" for MECH01/MECH05/MECH06). Clustering allows shared `_helpers.py` to grow organically. Planner decides the exact groupings.
- **D-38:** Gating on framework extensions — some MECH gaps depend on engine/framework extensions routed to Phase 5 (e.g., MECH09 needs GAP-ENG03 `llm_adjudicated` category; MECH12 needs `actors: list[NodeId]`). These seed mechanics ship with stub implementations that declare their framework prerequisite and are skipped with a clear message until Phase 5 delivers the extension. The integration test harness records these as "blocked by framework gap", distinguishing them from correctness failures.


### AUTO-03 Absorption into Phase 4
- **D-39:** AUTO-03 ("CLI scripts for common operations so agents don't need to compose commands") is ABSORBED into Phase 4. Rationale: the CLIs that Phase 4 ships — `validate-mechanic` (04-02), `scaffold-mechanic` (04-05), and `prune-diagnostics` (04-03) — are exactly the operator-facing SDLC tooling that AUTO-03 intended. These commands collectively:
  - Let the operator validate an authored mechanic without running a tick (`validate-mechanic`).
  - Let the operator bootstrap a new mechanic module + test stub in one command (`scaffold-mechanic`).
  - Let the operator manage diagnostics filesystem growth safely (`prune-diagnostics` dry-run + --confirm).
  Plus `token-world create` / `list` / `delete` (already shipped in Phase 0) covers the universe-management portion of AUTO-03.

  Action items triggered by this decision:
  - REQUIREMENTS.md Traceability row for AUTO-03 flips from `Phase 2 | Pending` to `Phase 4 | Pending` (completion flip happens in 04-12 Task 2).
  - Plan 04-05 and 04-12 already list `AUTO-03` in their `requirements:` frontmatter; those references are retained under this decision.

  Alternative considered: silently drop AUTO-03 from 04-05/04-12 frontmatter and leave the requirement mapped to Phase 2. Rejected — the Phase 4 CLIs genuinely satisfy the requirement; accurate traceability beats a silent re-queue.
### Claude's Discretion
- **D-11:** Code-reuse style (free functions vs base classes vs mixins)
- **D-32:** Whether `scaffold-mechanic` emits a full test stub or just the class skeleton
- **D-37:** Exact seed-mechanic clustering per plan (thematic grouping is the guideline; planner picks cluster boundaries)
- Exact CLI output format for `validate-mechanic` (human-readable vs JSON vs both via `--format` flag)
- Whether the test-execution stage of validation runs the mechanic's tests or just verifies they exist (default: run them)
- Whether `_helpers.py` is scaffolded empty by default or omitted until needed

### Proposed Plan Decomposition (informative; planner has final say)
1. **04-01 — Flatten mechanic layout + Phase 3 fixes** (supersedes Phase 2 D-15; absorbs D-33 H-01 and M-04). Rewrite loader.py and registry.py for module-based discovery; migrate seeds to flat modules; drop meta.yaml; add `tags` as `Mechanic` class attribute; update scaffold.py; move tests to mirrored test tree; update CLI commands that referenced folder paths; update MCP stub server to drop `register_mechanic`; update universe CLAUDE.md template. Fix temporal index H-01 and use-case loader M-04 CRLF as part of this plan.
2. **04-02 — Validation pipeline**. Implement `token_world.mechanic.validation.validate`; AST walker for D-14 rules; wire as CLI `validate-mechanic`; integrate with registry auto-scan so `resume_tick` validates before loading.
3. **04-03 — Diagnostics substrate**. Define schema (D-21, D-22); implement `DiagnosticsSink`; wire into validation runs and (stub) per-tick hooks ready for Phase 5 to populate; add `prune-diagnostics` CLI.
4. **04-04 — Integration test harness**. Consume the existing `src/token_world/use_cases/loader.py` (Phase 3 artifact); pytest parametrization from `.planning/use-cases/` manifests; coverage model per D-29b (pass / yield / block-by-framework-gap / fail).
5. **04-05 — Authoring guides + scaffold-mechanic**. `docs/guides/authoring-mechanics.md`; universe CLAUDE.md template update; `scaffold-mechanic` CLI.
6. **04-06..04-NN — Seed mechanic authoring waves** (per D-36..D-38). Author MECH01–MECH27 in thematic clusters. Each plan authors a cluster, adds tests, validates via the pipeline, and flips the corresponding integration tests from "yield/blocked" to "pass". Planner decides cluster boundaries and wave count. Suggested grouping:
   - Spatial extensions (MECH01, MECH05, MECH06)
   - Spatial queries & AoE (MECH02, MECH03, MECH04, MECH27)
   - Object interaction (MECH07, MECH08, MECH14, MECH15, MECH16)
   - Social / belief (MECH09, MECH10, MECH11, MECH13, MECH25)
   - Cooperation (MECH12 — blocked on GAP-ENG05; ships as framework-gap stub)
   - Resource depletion / fungibility (MECH17, MECH18)
   - Framework review gate enforcement (MECH19 — absorbed into D-35; no dedicated mechanic needed)
   - Environmental family (MECH20, MECH21, MECH22, MECH23, MECH24)
   - Authoring lint (MECH26 — part of 04-05 authoring guide, not a standalone mechanic)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Vision & Decisions
- `docs/IdeationRant.txt` — original vision; explicitly positions the simulation engine as an LLM agent and anticipates the inversion-of-control model
- `.planning/PROJECT.md` §Key Decisions — Hybrid SDK (operator/tool-layer split), model roles, mechanic layout (**revised in this phase**)
- `.planning/DECISIONS.md` — chronological decision log, updated alongside this CONTEXT.md to reflect the revised mechanic layout and MCP tool surface

### Requirements (revised by this phase)
- `.planning/REQUIREMENTS.md` §Mechanic Framework — MECH-03, MECH-04 (this phase); MECH-05, MECH-06 revised to reflect flat layout
- `.planning/REQUIREMENTS.md` §Testing — TEST-02 (integration tests)
- `.planning/REQUIREMENTS.md` §Agent Autonomy — AUTO-02 (diagnostics filesystem)
- `.planning/REQUIREMENTS.md` §Universe Infrastructure — UNIV-03 revised to drop `register_mechanic`

### Stack & Architecture
- `.planning/research/STACK.md` — model selection (Opus operator, Sonnet observer, Haiku classifier), MCP tool list (revised)
- `.planning/research/ARCHITECTURE.md` — architecture considerations
- `.planning/research/THEACT-PATTERNS.md` — universe-as-codebase pattern; revised for flat mechanic layout
- `docs/design/architecture.md` — system component diagrams (revised)

### Prior Phase Context
- `.planning/phases/00-universe-infrastructure/00-CONTEXT.md` — universe structure, MCP stub server, scaffolding templates
- `.planning/phases/01-graph-foundation/01-CONTEXT.md` — KnowledgeGraph API, EventStore, claim_id, JSON-serializable properties
- `.planning/phases/02-mechanic-framework/02-CONTEXT.md` — mechanic protocol, MechanicContext DSL, voluntary/involuntary, chain execution, registry. **D-15 (folder structure) and D-16 (meta.yaml content) are SUPERSEDED by this phase's D-03..D-08.** All other Phase 2 decisions remain in force.
- `.planning/phases/03-design-validation/03-CONTEXT.md` — use-case library format (consumed by integration test harness)

### Phase 3 Outputs — Primary Inputs to Phase 4
- `.planning/GAP-ANALYSIS.md` — canonical gap synthesis across 35 use cases; 68 gaps (52 address-now, 16 defer)
- `.planning/GAP-HANDOFF.md` — address-now gaps routed by target phase; **28 items route to Phase 4** (27 seed mechanics MECH01–MECH27 + GAP-ENG16 validation-gate enforcement). Phase 4 planner MUST cite these gap IDs in plan frontmatter.
- `.planning/use-cases/` — 35 use-case manifests across 5 categories (spatial, social, resource, environmental, edge-case). YAML-frontmatter format with `setup.graph_builder`, `actions`, `expected_observations` (including `graph_assertions`), and per-case `gaps`. Directly consumable by pytest parametrization.
- `.planning/phases/03-design-validation/deferred-items.md` — 16 deferred gaps (v2 scope: multi-agent, vocabulary consistency, hardening)
- `.planning/phases/03-design-validation/03-REVIEW.md` — code review findings. **H-01 (temporal index remove-then-readd bug) and M-04 (use_cases/loader.py CRLF handling) MUST be fixed before plan 04-04 runs.** See D-34.

### Existing Code (revised by this phase)
- `src/token_world/mechanic/loader.py` — rewritten for module-based discovery
- `src/token_world/mechanic/registry.py` — scans modules, reads class attributes, drops meta.yaml loading
- `src/token_world/mechanic/seeds/` — flattened from folders to `<id>.py` modules
- `src/token_world/mechanic/protocol.py` — `Mechanic` base class gains `tags: list[str] = []` default
- `src/token_world/universe/scaffold.py` — copies flat seed modules; creates mirrored test tree
- `src/token_world/universe/templates/claude_md.py` — updated for 3-tool MCP surface and mechanic authoring guidance
- `src/token_world/mcp_server.py` — drops `register_mechanic` stub
- `src/token_world/cli.py` — adds `validate-mechanic`, `scaffold-mechanic`, `prune-diagnostics`
- `tests/test_mechanic/` — tests adjusted for module-based discovery; seed tests moved to mirrored layout
- `tests/test_mcp_server.py`, `tests/test_universe/test_scaffold.py` — assertions updated for 3-tool surface

### Existing Code (already built by Phase 3 — consumed by this phase)
- `src/token_world/use_cases/loader.py` — manifest loader built in Phase 3. Phase 4 fixes the CRLF bug (M-04) and consumes it in plan 04-04. **Do not reimplement.**
- `src/token_world/graph/temporal.py` — temporal index with H-01 bug on `find_state_at_tick` after remove-then-readd. Phase 4 fixes this before integration tests exercise remove/re-add sequences (resource/crafting use cases).

### New Code (this phase creates)
- `src/token_world/mechanic/validation.py` — validation pipeline (D-12..D-16)
- `src/token_world/mechanic/diagnostics.py` — DiagnosticsSink and schema (D-21..D-25)
- `tests/test_integration/test_use_cases.py` — parametrized integration tests (D-26..D-29)
- `docs/guides/authoring-mechanics.md` — developer-facing authoring guide (D-30)
- `src/token_world/mechanic/seeds/*.py` — new seed mechanics authored per GAP-HANDOFF.md MECH01–MECH27 (D-35)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **KnowledgeGraph + EventStore** (Phase 1) — untouched; diagnostics schema piggybacks on tick IDs that already exist in the event stream.
- **Mechanic base class, MechanicContext, chain execution engine, matchers, ExecutionTrace** (Phase 2) — all reused; `Mechanic` base class gains `tags` default; everything else stable.
- **Click CLI at `cli.py`** — extends with `validate-mechanic`, `scaffold-mechanic`, `prune-diagnostics`.
- **GraphBuilder at `tests/test_graph/conftest.py`** — fluent graph construction; reused by integration-test fixtures.
- **ExecutionTrace** (Phase 2 D-10) — already produces the tree the diagnostics substrate captures under `execution/trace.json`.

### Established Patterns
- All graph mutations through `KnowledgeGraph` API (enforced by `MechanicContext` and by AST validation rules).
- JSON-serializable property values only (`ALLOWED_PROPERTY_TYPES`).
- Two node types: `agent`, `entity`.
- Raw `sqlite3` for persistence; no ORM.
- src-layout for code; mirrored test tree; pytest as the test runner.
- Universes are self-contained folders; per-universe assets copied on scaffold.

### Integration Points
- `mechanics/` directory in each universe: the codebase the operator edits.
- `diagnostics/` directory in each universe: where AUTO-02 writes. Schema defined here; populated here (validation) and in Phase 5 (tick execution).
- `register_mechanic` MCP tool stub (Phase 0) is deleted; the MCP server updates to the 3-tool surface.
- Phase 3 use-case manifests feed the integration-test harness; the manifest format (produced by Phase 3) must be stable by the time Phase 4 plan 04-04 runs.

### Scale Consideration
- Universes may accumulate many mechanics. Registry import is eager (imports every mechanic module at scan time). If startup time becomes a concern at many hundreds of mechanics, lazy loading is a future optimization. Not a v1 concern.

</code_context>

<specifics>
## Specific Ideas

- "The simulation instance folder acts just like a codebase and the tool calls elegantly make that codebase come to life" — this is the organizing metaphor. Every Phase 4 decision should ask: would this feel natural in a normal Python codebase?
- Mechanics provide abstractions or conveniences over framework primitives with clear API contracts. The `Mechanic` base class + DSL is the contract; helpers (`_*.py`) provide conveniences; AST rules enforce the contract boundary.
- Opus is the operator, not a generator. We don't "prompt it to produce code"; it authors code using its own tools in its own session. Phase 4's gift to the operator is a clean codebase to author in + a strict gate to catch mistakes.
- meta.yaml was a ceremony that paid nothing class attributes don't already pay. Removing it tightens the authoring loop.
- `git log -- mechanics/<id>.py` replaces `git log -- mechanics/<id>/` with no loss of per-mechanic history, as long as the default one-mechanic-per-file convention holds.
- Drop `register_mechanic` reflects a principle: the universe is a codebase, so "registration" = "being in the codebase and passing validation". No ceremony needed.

</specifics>

<deferred>
## Deferred Ideas

- **Runtime sandboxing (RestrictedPython).** v2 hardening per PROJECT.md. AST rules approximate a pre-runtime safety layer; snapshots provide the post-runtime safety net.
- **Automatic diagnostics rotation.** v1 retains everything; manual `prune-diagnostics` CLI is sufficient. Revisit when universes routinely hold >10k ticks.
- **Lazy mechanic loading.** Registry imports every module on scan; acceptable until mechanic counts grow.
- **Dedicated `.claude/skills/author-mechanic/` skill inside scaffolded universes.** Defer unless authoring friction emerges.
- **Coherence checking** (HARD-02): ensuring new mechanics don't contradict existing ones. Future hardening.
- **Cost monitoring / circuit breakers** (HARD-03) for operator LLM calls. v2.
- **Multi-mechanic-per-file workflows and conventions.** Defer concrete guidance until a real case appears; default remains one-per-file.

</deferred>

---

*Phase: 04-llm-mechanic-generation*
*Context gathered: 2026-04-12*
