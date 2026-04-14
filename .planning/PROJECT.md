# Token World

## What This Is

A universe simulator where LLM-powered resident agents inhabit a text-based world and interact with an environment whose rules are procedurally authored on-the-fly. Under the inversion-of-control model established during v1.0, the simulation engine never generates code itself — it classifies agent actions, matches existing mechanics deterministically, and when no mechanic matches yields a structured signal to the operator (an Agent SDK driver with an Opus mechanic-authoring subagent). The operator authors the needed mechanic via normal Python SDLC (with a 6-stage validation gate), and the tick resumes. All world state lives in a schema-less NetworkX+SQLite knowledge graph that evolves as new concepts emerge.

## Core Value

The simulation engine reliably interprets agent actions, yields to the operator for novel situations, and maintains a consistent knowledge graph — so from a resident agent's perspective, the world feels fully real and its rules emerge coherently.

## Requirements

### Validated (v1.0)

- [x] Universe instance as self-contained folder with CLAUDE.md, .mcp.json, universe.db, git versioning — v1.0 (Phase 0)
- [x] Knowledge graph with flexible schema that supports arbitrary properties and relations — v1.0 (Phase 1)
- [x] Graph state snapshots for rollback and replay — v1.0 (Phase 1)
- [x] Mechanic framework providing primitives for preconditions (graph queries) and side effects (graph mutations) — v1.0 (Phase 2)
- [x] Mechanic versioning so every change to a mechanic is tracked — v1.0 (Phase 2, via git)
- [x] Flat Python mechanic layout + 6-stage validation pipeline — v1.0 (Phase 4)
- [x] Operator-authored mechanics via Agent SDK driver (supersedes "LLM-powered mechanic generation pipeline") — v1.0 (Phase 4.1 + verified end-to-end at $1.15/23 turns)
- [x] Simulation engine that classifies actions, matches mechanics, or yields structured signal to the operator — v1.0 (Phase 5)
- [x] Grounded observations (Sonnet synthesizer with hard grounding D-15; VisibilityProjector with belief overlay) — v1.0 (Phase 5)
- [x] Conservation laws enforced via YAML-defined invariants — v1.0 (Phase 5)
- [x] Tick summary JSON per tick + hierarchical compression (tick → batch → epoch) — v1.0 (Phases 5, 6)
- [x] Resident agent with randomly generated personality interacting via text — v1.0 (Phase 6)
- [x] Agent memory persists across sessions (SQLite, session forking via graph snapshot) — v1.0 (Phase 6)
- [x] Full persistence of graph state, mechanics, agent memory/personality, and simulation history — v1.0 (Phases 0, 1, 6)
- [x] Attention & consciousness as composable interruption thresholds (sleep, daydream, autopilot travel, drunkenness from one pattern) — v1.0 (Phase 7)
- [x] Design validation: 35 use cases + gap analysis + regression suite — v1.0 (Phases 3, 6)
- [x] Diagnostics filesystem with per-tick prompts/responses/parsed output + operator namespace — v1.0 (Phases 4, 4.1)
- [x] Optional spatial + temporal index primitives for mechanics — v1.0 (Phase 3)
- [x] Mermaid graph visualization with ego-graph filtering — v1.0 (Phase 3)
- [x] Playtest runner with adversarial scenario injection + quality scoring — v1.0 (Phase 6)
- [x] Pluggable LLM backend (AnthropicSDK default + ClaudeCLI for zero-cost UAT) — v1.0 (Phase 7.1)

### Validated (v1.1)

- [x] External-operator mode (file-based yield protocol, subagent-as-operator, $0 marginal) — v1.1 (Phase 08, commit `8f1f18e`)
- [x] Seed starter universe (Willowbrook) + unattended runner — v1.1 (Phase 08, commit `0a95763`)
- [x] Operator CLI query surface (`inspect`, `tick`, `trace`, `stats`, `mechanics`, `watch`, `agents`, `diff`) — v1.1 (Phase 09)
- [x] NiceGUI dashboard — 4 panels (tick stream, graph canvas, stats strip, causal chain) — v1.1 (Phase 11)
- [x] Unattended Willowbrook overnight run — 11 novel mechanics authored autonomously — v1.1 (Phase 12, experiment)
- [x] Warm-up burn-down of v1.0 Known Gaps (04.1 SC-2, traceability/roadmap CI, research-doc refresh, `BatchSummary.agent_id`) — v1.1 (Phase 10)
- [x] Classifier permissive-verb prompt + markdown-fence stripper — v1.1 (commits `3ffb9f5`, `f84c9b2`; required for emergence)
- [x] Seed-mechanic pruning + bootstrap scenario + yield-handler subagent prompt — v1.1 (commit `ee0284b`)

## Current Milestone: v1.2 Quality + Depth

**Goal:** Harden the truthfulness of the emergence loop (engine bugs, observability,
energy economy, dashboard UX) and open the door to richer play (composite actions,
multi-agent scaffold, KPIs) — taking everything remaining across the project into
one inclusive milestone before v2.

**Target features:**
- Truthful engine (primary-check-fail → RefuseDecision; observer grounded to mutations; `locked`/`blocked`/`inventory_full` emergent, not engine-coded; composite actions)
- Grounded observer (outcome-consistent with mutations; no stale descriptions; double-wrap templates fixed)
- Dashboard UX + multi-agent scaffold + run-status indicator + agent inspector drawer + mechanic timeline
- Richer play via composite actions + Willowbrook seed refinement + mutation-chain visibility
- Quality KPIs subpackage + CLI + dashboard panel + CI gating + QA checklists
- Graph conventions codified (door, container, portal, fungible amount)
- Seed corpus expansion (examine / pet / sharpen / hum / drop promoted; `--preserve-mechanics` flag)
- Ops & tooling (visible `.stop` warning, historical tick-migration, operator decision-log enrichment, overlap detector)

Full scope: `.planning/REQUIREMENTS.md` (REQ-V12-* namespace, inclusive of all
remaining requirements across the project).

### Active (v1.2)

- [x] REQ-V12-ENGINE-01 primary-check-fail → RefuseDecision (shipped warm-up `afc5c73`)
- [x] REQ-V12-ENGINE-02 observer grounding to mutation list (shipped warm-up `e110e2c`)
- [x] REQ-V12-DASHBOARD-01..04 dashboard UX cluster (shipped warm-up `d31090d`, `6101da0`)
- [x] REQ-V12-CLI-01..02 inspect headers + `token-world yield` CLI (shipped warm-up `fa68200`, `7435536`)
- [x] REQ-V12-PLAYTEST-01 Mira prompt tightening + auto-halt (shipped warm-up `0fcd614`)
- [x] REQ-V12-ECONOMY-01 Willowbrook `_economy.py` (shipped warm-up, universe commit `ce671cd`)
- [x] REQ-V12-QUALITY-01 dashboard QA + sim-quality rubric docs (shipped warm-up `890b464`)
- [x] REQ-V12-DOCS-01 tooling-surfaces.md allocation principle (shipped warm-up `3eec1c5`)
- [x] REQ-V12-TOOLING-01 `commit.sh` explicit paths (shipped warm-up `958a28b`)
- [ ] REQ-V12-ENGINE-03..05, REQ-V12-DASHBOARD-05..09, REQ-V12-CLI-03..04, REQ-V12-QUALITY-02, REQ-V12-SEEDS-01, REQ-V12-GRAPH-01..04, REQ-V12-EMERGE-01..02, REQ-V12-OPS-01..02, REQ-V12-TOOLING-02 — active, phases TBD (roadmapper pending)

See `.planning/REQUIREMENTS.md` for full REQ-V12 detail.

### Out of Scope (reaffirmed)

The following items stay project-level out of scope — permanent, not merely
"later". v2 far-fetched candidates live in `.planning/backlog/v2.0-REQUIREMENTS.md`.

- Game adaptation / playable game — v1 is a simulation, not a game
- Multimodal output (images, maps, 8-bit graphics) — text-first
- Civic simulation scenarios (UBI, economics) — requires mature mechanics ecosystem
- Real-time simulation — turn-based is simpler and sufficient
- Authentication / multi-user — local hobby project
- Plugin system for mechanics — framework IS the plugin API
- Cloud-hosted / public dashboard URL — local only
- Agent SDK overnight runs — explicitly forbidden per §L cost rails; subagents under the subscription are the blessed shape

The following items are **deferred to v2.0** (not out of scope, just far-fetched):

- Multi-agent simulation engine (MULTI-01..03, reframed as REQ-V20-MULTI-01)
- Review agents / bird's-eye monitoring (MON-01..03, reframed as REQ-V20-MULTI-02)
- Sandboxed mechanic execution / RestrictedPython (HARD-01, CVE-2025-22153, reframed as REQ-V20-HARD-01)
- Distributed graph / sharding (reframed as REQ-V20-DIST-01)
- All 12 phase-03 gap deferrals not promoted to v1.2 Graph Conventions

## Context

Token World shipped v1.0 on 2026-04-14 in 3 calendar days (but over many autonomous-agent hours). Final state:

- **Codebase:** 18,736 LOC Python (src) + 31,078 LOC tests. 34 seed mechanics. 1687 tests passing.
- **Tech stack:** Python 3.12+, NetworkX (in-memory graph), SQLite (persistence), Anthropic SDK (raw) for deterministic pipeline, Agent SDK (Opus) at operator layer, `claude-cli` subprocess backend for zero-cost UAT.
- **Key ratios:** LLM call distribution — Haiku (classifier) dominates per-tick; Sonnet (observer) second; Opus (mechanic authoring) rare-but-expensive (hundreds of turns per invocation, gated to yield-only).
- **Verification maturity:** 10/10 phases shipped verification reports. Phase 04.1's SC-2 interactive smoke test is the only outstanding item; 07.1 makes it trivially runnable.
- **Tooling:** Every capability the simulation needs (graph viz, mechanic scaffolding, diagnostics replay, playtest, prompt-hash registry) also serves agents working on the project — dogfooding principle holds.
- **No side channels:** graph-is-ground-truth invariant maintained across the milestone.

## Constraints

- **Language:** Python 3.12+ — engine, framework, all mechanics
- **Knowledge Graph:** schema-less (NetworkX DiGraph + JSON-serializable properties only)
- **Persistence:** full state persistence (SQLite via `json_graph.node_link_data`)
- **Budget:** hobby project — cost-efficient LLM usage; Haiku/Sonnet/Opus routing by role
- **Grounding:** all simulation responses derive from graph state + mechanic execution
- **No ORM, no pickle, no LangChain:** see CLAUDE.md for full forbidden-tech list
- **Mutation-mediated graph access:** all writes go through `KnowledgeGraph` API (never direct NetworkX)
- **Two node types only:** `agent` and `entity` — everything else is emergent properties

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python for engine and mechanics | Rich AI/ML ecosystem, easy LLM code generation, networkx available | Good — delivered 34 mechanics + full infra in v1.0 |
| Flexible schema-less knowledge graph | New concepts must emerge dynamically (temperature, inventory, currency) as mechanics create them | Good — 1687 tests exercise dynamic properties; zero migrations |
| Full persistence from the start | Enables time-travel debugging, rollback, replay — foundational for tooling | Good — snapshot/restore used daily during v1.0 |
| Single agent + engine for v1 | Prove core loop works before scaling | Good — core loop validated; multi-agent scoped to v2+ |
| Hybrid SDK: Agent SDK orchestrates, raw API inside tools | Agent SDK (Opus) sits at operator layer; MCP tools + raw SDK for classification/observation | Good — both paths operational; programmatic harness verified end-to-end |
| Mechanics as flat Python modules (normal SDLC) | Each `mechanics/<id>.py` with class attributes; shared helpers as `_*.py`; tests in project tree. Supersedes Phase 2 folder-per-mechanic D-15. | Good — Phase 4 delivered flat layout; 34 mechanics author/refactor like normal Python |
| Universe instance as agent workspace | Self-contained folder with CLAUDE.md + AGENTS.md symlink + .mcp.json + universe.db + mechanics/ + agents/ | Good — harness-agnostic design holds |
| No sandboxing for v1 | Hobby project; RestrictedPython deferred | Accepted — CVE-2025-22153 on watchlist for v2 |
| Hierarchical tick summaries | Tick → batch (100) → epoch (100 batches) as JSON | Good — TickCompressor delivered SIM-12 |
| Opus-via-Agent-SDK authors mechanics; Sonnet/Haiku power engine inner loop | Top-level coding agent = mechanic author (not bespoke generation pipeline); inner loop uses cheaper models | Good — Model routing implemented; cost-efficient; Opus-authoring validated at ~$1.15/23 turns |
| 3-tool MCP surface (resume_tick, rollback, list_mechanics) | Operator uses filesystem + SQLite directly; minimal MCP | Good — D-19 delivered in Phase 4; Phase 5-09 MCP server exposes exactly these 3 |
| Inversion of control: engine yields, never generates | Engine halts on no-match with structured YieldSignal; operator authors via SDLC; resume_tick picks up new mechanic | Good — D-34 in Phase 4; Phase 04.1 delivered operator harness; Phase 5 delivered yield-producing engine |
| Session forking via KnowledgeGraph.snapshot/restore (not git branch) | Reuses graph snapshot machinery; no DB copy | Good — Phase 6 D-08; AGENT-04 delivered without filesystem overhead |
| Composable interruption thresholds | `LongRunningAction + ThresholdSpec + ThresholdEvaluator` primitives reused across sleep/daydream/autopilot/drunk | Good — project philosophy ("composition over specialization") validated by 5 mechanics from 1 pattern |
| Pluggable LLM backend (AnthropicSDK default, ClaudeCLI alt) | Zero-cost live UAT via user's Claude subscription; unblock Phase 6 live-API verification | Good — Phase 07.1 delivered; all 3 LLM classes refactored backward-compat |
| Conservation checker verify-only, no rollback | Rollback is orchestrator responsibility; O(1) opt-out via empty conserved_properties | Good — Phase 5 D-16 |
| ALLOWED_PROPERTY_TYPES list (str/int/float/bool/None/list/dict) | JSON-serializable invariant enforces schemaless guarantee without schema declarations | Good — enforced by validator; no property-type violations shipped |
| TickResult.projected_state reuses Observer projection dict | No extra projector call, no drift; None on yield/refuse paths | Good — Phase 6-00 D-based; groundedness scoring consumes it |
| Prefer ruff + mypy + prek (not full pre-commit) | Modern, fast toolchain; agents discover via CLAUDE.md script catalog | Good — CI green through milestone |

## Documentation

See [CLAUDE.md](../CLAUDE.md) § Documentation Maintenance for documentation practices. Architecture diagrams in [docs/design/architecture.md](../docs/design/architecture.md), simulation pipeline in [docs/design/simulation-pipeline.md](../docs/design/simulation-pipeline.md).

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-14 at v1.2 milestone open (retroactively archived v1.1).*
