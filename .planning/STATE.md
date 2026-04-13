---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: 07-CONTEXT.md written; 23 decisions locked (SIM-09, SIM-10 addressed); ready for gsd-plan-phase
stopped_at: Completed 07-attention-and-consciousness-01-PLAN.md
last_updated: "2026-04-13T18:44:43.129Z"
last_activity: 2026-04-13 -- Phase 07 context gathered
progress:
  total_phases: 9
  completed_phases: 8
  total_plans: 63
  completed_plans: 57
  percent: 90
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** The simulation engine reliably interprets agent actions, generates coherent mechanics as executable Python code, and maintains a consistent knowledge graph
**Current focus:** Phase 07 context gathered — ready for research + planning

## Current Position

Phase: 07 (attention-and-consciousness) — CONTEXT GATHERED
Plans: 0 of TBD
Status: 07-CONTEXT.md written; 23 decisions locked (SIM-09, SIM-10 addressed); ready for gsd-plan-phase
Last activity: 2026-04-13 -- Phase 07 context gathered

Progress: [███████░░░] 78% (7 of 9 phases complete; Phase 07 in context phase)

## Performance Metrics

**Velocity:**

- Total plans completed: 20
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 00 | 2 | - | - |
| 01 | 3 | - | - |
| 02 | 3 | - | - |
| 03 | 12 | - | - |

**Recent Trend:**

- Last 5 plans: none
- Trend: N/A

*Updated after each plan completion*
| Phase 03-design-validation P02 | 4 | 2 tasks | 4 files |
| Phase 03 P03 | 4min | 3 tasks | 5 files |
| Phase 03 P04 | 5min | 3 tasks | 7 files |
| Phase 03 P03-05 | 6min | 2 tasks | 7 files |
| Phase 03 P11 | 30min | 1 tasks | 40 files |
| Phase 03 P12 | 25min | 3 tasks | 4 files |
| Phase 05-simulation-engine P02 | 35 | 2 tasks | 6 files |
| Phase 05-simulation-engine P03 | 6 | 3 tasks | 7 files |
| Phase 05-simulation-engine P04 | 5 | 4 tasks | 2 files |
| Phase 05-simulation-engine P05 | 25 | 1 tasks | 3 files |
| Phase 05-simulation-engine P6 | 62 | 2 tasks | 6 files |
| Phase 05-simulation-engine P07 | 4 | 1 tasks | 3 files |
| Phase 05-simulation-engine P08 | 130 | 2 tasks | 4 files |
| Phase 05-simulation-engine P09 | 5 | 1 tasks | 3 files |
| Phase 06-resident-agent P00 | 18 | 1 tasks | 2 files |
| Phase 06-resident-agent P01 | 75 | 5 tasks | 13 files |
| Phase 06-resident-agent-end-to-end-loop P03 | 25 | 2 tasks | 6 files |
| Phase 06 P02 | 25 | 3 tasks | 7 files |
| Phase 06 P05 | 40 | 4 tasks | 9 files |
| Phase 06 P06 | 22 | 2 tasks | 12 files |
| Phase 07-attention-and-consciousness P01 | 18 | 3 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Hybrid SDK: Agent SDK orchestrates, raw Anthropic API powers deterministic pipeline inside tools (Phase 6 -- AGENT-03, AGENT-04)
- Universe instance as self-contained agent workspace (CLAUDE.md, .mcp.json, universe.db, mechanics/, agents/)
- Mechanics versioned as part of universe git repo (not separate)
- No sandboxing for v1 (hobby project; RestrictedPython deferred per research recommendation)
- Opus for mechanic generation, Sonnet/Haiku for engine classification (model routing)
- Use case library comes BEFORE simulation engine (Phase 3) so gap analysis informs engine design
- [Phase 03-design-validation]: Full rtree replacement on rebuild() instead of per-id deletions — simpler code, <50ms @ 10k nodes
- [Phase 03-design-validation]: Deferred rtree import via TYPE_CHECKING + in-property import — mechanics that never use ctx.spatial never import rtree
- [Phase 03-design-validation]: ValueError on intersects(positionless_node) — loud failure surfaces author bugs instead of silent empty list
- [Phase 03]: TemporalIndex mem+disk merge with dedup on (tick, type, target, property, new_value) — reads session EventStore plus graph_events SQLite, works uniformly across save/load boundaries
- [Phase 03]: TemporalIndex treats sqlite3.OperationalError (missing table) as empty-disk — supports in-memory-only graphs where save() has never run
- [Phase 03]: Lazy @property pattern established for ctx.spatial + ctx.temporal — composable zero-cost DSL extensions on MechanicContext
- [Phase 03]: viz-graph CLI: anchors always preserved through downstream filters; whole-graph rendering explicitly unsupported (must --node/--seed-query/--all-agents)
- [Phase 03]: Mermaid ID sanitization appends sha256[:6] suffix on substitution -- distinct dangerous inputs (x", x|) produce distinct sanitized IDs
- [Phase 03]: Use-case library skeleton: 35 UC IDs pre-assigned in per-category MANIFEST.md files (7/8/7/7/6) — Wave 2 authors claim rows rather than invent IDs, making 35 parallel writes collision-free by construction
- [Phase 03]: [Phase 03]: validator_exception: target_may_not_exist canonicalized for UCs whose missing-target/actor IS the test condition (UC-E01, UC-O05); engine sentinel actor recognized by audit tooling for tick-driven passive mechanics (UC-V01..V04)
- [Phase 03]: [Phase 03]: Category-scoped gap IDs (S-/O-/R-/V-/E- prefix + G/M/E layer letter + NN) serve Wave-3 dedup; Wave 4 renumbers to canonical GAP-<layer><NN> and collapses 6 flagged cross-category overlap clusters
- [Phase 03]: [Phase 03]: 68 canonical GAP IDs (GAP-GRAPH/MECH/ENG/CROSS) synthesised from 80 Wave-3 category-scoped gaps; 6 cross-category overlap clusters merged (observation projection, graceful refusal, terrain vocab, fungibility, passive-tick sweep, blocked movement); three-way dispositions 52 address-now / 16 defer / 0 out-of-scope
- [Phase 03]: [Phase 03]: GAP-X01 shadow alias in Cross-Cutting Rationale (no standalone OOS row) — preserves schema regex [GMEX] coverage without breaking frontmatter layer-sum reconciliation
- [Phase 05-simulation-engine]: _node_type_matches checks type and subtype independently to avoid shadowing subtype='container' with built-in type='entity'
- [Phase 05-simulation-engine]: CheckResult uses reasons: list[str] not narrative: str — refuse() returns CheckResult(passed=False, reasons=[narrative])
- [Phase 05-simulation-engine]: Used ego_subgraph() public API to access edge types in VisibilityProjector — no private NetworkX access
- [Phase 05]: Observer client injected via constructor (not module-level) so test mocking works without patching
- [Phase 05-simulation-engine]: D-16: ConservationChecker verify-only (no rollback); empty conserved_properties = O(1) opt-out; rollback is orchestrator responsibility (Plan 05-08)
- [Phase 05-07]: Reused Phase 4 _atomic_write_json for T-05-SUMMARY-PARTIAL-WRITE mitigation; json.loads(model_dump_json()) for strict-JSON dict guarantee
- [Phase 05-simulation-engine]: cast(VerdictOk, verdict) at ExecuteDecision/YieldDecision branch points — mypy cannot narrow ClassifierVerdict through decide() semantics
- [Phase 05-simulation-engine]: WorldPropertyMatcher.match() called directly in sweep (Phase 2 matches() helper doesn't dispatch Phase 5 matchers)
- [Phase 05-simulation-engine]: _ClassifierDiagnosticsAdapter bridges Wave 1 classifier.py write_prompt/response/parsed API to Phase 4 TickDiagnostics.write_classification
- [Phase 05-simulation-engine]: Lazy imports inside _tool_* functions keep mcp_server module import cost minimal
- [Phase 05-simulation-engine]: _anthropic_factory module-level monkeypatch surface; rollback missing db is -32602 not -32603
- [Phase 06-00]: TickResult.projected_state reuses the projection dict already computed for Observer.synthesize — no extra projector call, no drift; None on yield/refuse paths (scorer must handle None as groundedness=0.5 per 06-RESEARCH)
- [Phase 06-01]: ResidentAgent uses raw Anthropic SDK (not Agent SDK); default model claude-haiku-4-5 per D-02; system prompt is hash-stable (world_rules + personality block, NO history)
- [Phase 06-01]: Session forking via KnowledgeGraph.snapshot/restore — no DB copy, no git branch per D-08
- [Phase 06-01]: ensure_memory_tables(conn) shared DDL helper imported by both AgentMemory and SessionManager (no DDL duplication)
- [Phase 06-01]: CLI module-level imports required for monkeypatching (deferred imports break patch("token_world.cli.X"))
- [Phase 06-resident-agent-end-to-end-loop]: D-16: 35 Phase-3 UC manifests reused as E2E regression tests
- [Phase 06-resident-agent-end-to-end-loop]: D-25: FakeClassifier + FakeObserver bypass LLM cost — 35 x 2 calls per CI avoided
- [Phase 06]: agent_id stubbed to 'unknown' in BatchSummary v1 — TickSummary has no actor field; resolve in Phase 7
- [Phase 06]: TickCompressor._BATCH_PROMPT_TEMPLATE set post-class-definition due to slots=True dataclass restriction
- [Phase 06]: pytest summary regex uses three independent patterns (passed/failed/duration) for correct parsing regardless of ordering
- [Phase 06]: judge_evaluate imported at cli.py module level so patch('token_world.cli.judge_evaluate') works in tests without deferred import
- [Phase 06]: AdversarialBank uses ClassVar frozen dataclasses — stateless, deterministic via caller-supplied RNG
- [Phase 07-attention-and-consciousness]: D-23: frozen dataclasses for ThresholdSpec/LongRunningAction (not Pydantic) — consistent with YieldSignal, Mutation pattern
- [Phase 07-attention-and-consciousness]: D-16: turns_total=None = indefinite duration; JSON null roundtrips correctly through to_dict/from_dict
- [Phase 07-attention-and-consciousness]: Serialization boundary: tuple[ThresholdSpec,...] in-memory; list[dict] in to_dict() to satisfy ALLOWED_PROPERTY_TYPES

### Roadmap Evolution

- Phase 4.1 inserted after Phase 4: Operator Agent Harness (URGENT) — Agent SDK driver required to verify Phase 5's yield→author→resume loop end-to-end; existing roadmap had no phase for the operator-side orchestration that Phase 5 depends on

### Pending Todos

None yet.

### Blockers/Concerns

- RestrictedPython CVE-2025-22153: needs review during Phase 4 planning to confirm controlled namespace workaround sufficiency
- Research docs (STACK.md, ARCHITECTURE.md, SUMMARY.md) recommend Sonnet for mechanic generation — this was overridden to Opus per user decision. Research docs are stale on this point; authoritative docs (CLAUDE.md, PROJECT.md) correctly say Opus. Update research docs before Phase 4.

## Session Continuity

Last session: 2026-04-13T18:44:43.125Z
Stopped at: Completed 07-attention-and-consciousness-01-PLAN.md
Resume file: None
