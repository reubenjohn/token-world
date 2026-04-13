---
phase: 05-simulation-engine
status: gaps_found
verifier: gsd-verifier
verified_at: 2026-04-13T13:09:03Z
score: 4/7 success criteria verified
must_haves_verified: 17
must_haves_total: 27
gaps: 5
requirement_coverage:
  - id: SIM-01
    status: partial
    evidence: "src/token_world/engine/classifier.py — Classifier.classify() exists, Haiku-backed, four verdicts including no_viable_action; but no SimulationEngine.run_tick orchestrator calls it end-to-end"
  - id: SIM-02
    status: complete
    evidence: "src/token_world/engine/matcher.py:93 — DeterministicMatcher.match(); src/token_world/mechanic/matchers.py — VerbMatcher, WorldPropertyMatcher, DecayMatcher, TickMatcher"
  - id: SIM-03
    status: complete
    evidence: "src/token_world/engine/decider.py:29 — decide() precedence ladder; YieldDecision emitted on no_match; RefuseDecision emitted on classifier refusal"
  - id: SIM-04
    status: missing
    evidence: "No SimulationEngine.run_tick() orchestrator. No observer.py, conservation.py, passive_sweep.py, or engine.py in src/token_world/engine/. ChainExecutionEngine exists in src/token_world/mechanic/engine.py but is not wired to the classify→match→decide→execute→observe pipeline."
  - id: SIM-05
    status: partial
    evidence: "src/token_world/engine/visibility.py — VisibilityProjector exists and projects actor-visible graph state. But no Sonnet observer (observer.py) consumes this output; no grounded observation text is produced. D-15 hard-grounding constraint prompt not written."
  - id: SIM-06
    status: missing
    evidence: "No simulation history log. No diagnostics wiring of engine LLM calls to DiagnosticsSink (plan 05-08 tasks not executed). tests/test_engine/ has no test_engine.py or test_tick_summary.py."
  - id: SIM-07
    status: complete
    evidence: "src/token_world/engine/visibility.py — VisibilityProjector.project_for() filters by containment, illumination, hidden_properties; belief overlay via actor.beliefs; 30 tests pass"
  - id: SIM-08
    status: missing
    evidence: "No ConservationChecker. No conservation.yaml config. No rollback-on-violation logic. refusal.py defines a conservation_violation reason code (line 30) but that is a template string only — no enforcement exists."
  - id: SIM-11
    status: missing
    evidence: "TickSummary Pydantic model exists in src/token_world/engine/models.py:118 but no code writes tick_<id>.json files to tick_summaries/. tick_summaries/ dirs are scaffolded in scaffold.py:115-117 but never populated."
---

# Phase 05: Simulation Engine — Verification Report

**Phase Goal:** The engine interprets text actions, routes them to mechanics (or yields to the operator when none match), executes selected mechanics, and returns grounded observations — the full pipeline works end-to-end without a live agent. Under the inversion-of-control model established in Phase 4, the engine NEVER generates code; when no mechanic matches, it halts the tick and yields to the operator, which authors the needed mechanic via normal SDLC before the tick resumes.

**Verified:** 2026-04-13T13:09:03Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

The phase completed Wave 0 (Plan 05-01: classifier + config + RNG + AST rule) and Wave 1 plans 05-02, 05-03, 05-04 (matcher, decider, visibility projector). Wave 2 — the engine orchestrator (05-08), observation synthesis (05-05), conservation checker (05-06), passive sweep (05-07), tick summary writer, diagnostics wiring, MCP tool replacement, and CLI engine-turn command — was **not executed**. The four delivered components are individually complete and tested (1116 passing tests), but they are not wired into a functioning pipeline. The phase goal ("full pipeline works end-to-end") is not achieved.

---

## Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Text action classified into structured action; classifier returns `no_viable_action` for nonsense | PARTIAL | `classifier.py:59` — `Classifier.classify()` fully implemented. But no orchestrator calls it; standalone, not end-to-end. |
| 2 | No mechanic match → engine halts with structured yield signal; `resume_tick` picks up new mechanic | FAILED | `decider.py:29` — `decide()` returns `YieldDecision`. But no `SimulationEngine.run_tick()` exists to emit a `YieldSignal` from `operator/yield_signal.py`. The yield decision is never converted to an operator-readable signal. |
| 3 | Observations contain only information derivable from graph state | FAILED | `visibility.py` — `VisibilityProjector` produces the projected state dict. But no Sonnet observer (`observer.py`) synthesises observation text. No observation is produced at all. |
| 4 | Observations contextually filtered (temperature hidden when examining keyboard) | VERIFIED | `visibility.py:57` — containment walk, illumination filter, `hidden_properties` stripping. 30 tests. Closes GAP-CROSS01. |
| 5 | Conservation laws enforced | FAILED | `refusal.py:30` — `conservation_violation` template string exists. No `ConservationChecker` class, no `conservation.yaml` config parser, no rollback-on-violation logic. |
| 6 | Per-tick summaries written to `tick_summaries/` after each tick | FAILED | `models.py:118` — `TickSummary` schema defined. `scaffold.py:115-117` — `tick_summaries/{ticks,batches,epochs}/` dirs scaffolded. Nothing writes tick JSON files. |
| 7 | Classifier, matcher, observer LLM calls wired to DiagnosticsSink (AUTO-02 end-to-end) | FAILED | `classifier.py:83` — `tick_diag_ctx` parameter exists; diagnostics write if caller passes a sink. No orchestrator exists to pass the sink. Observer LLM call doesn't exist. Matcher produces no LLM call so that part is N/A. AUTO-02 end-to-end wiring is not established. |

**Score:** 2/7 success criteria fully verified. SC-1 is partial (component exists, not orchestrated). SC-4 is fully verified.

---

## Deferred Items

No items are deferred. Phase 6 requirements (AGENT-01..04, TEST-04, SIM-12) do not cover the missing Phase 5 items. The missing requirements (SIM-01 completion, SIM-04, SIM-05 completion, SIM-06, SIM-08, SIM-11) remain Phase 5 scope.

---

## Required Artifacts by Plan

### Plan 05-01 Must-Haves

| Must-Have | Verified | Evidence |
|-----------|----------|----------|
| engine package exists at src/token_world/engine/ with __init__.py | YES | `src/token_world/engine/__init__.py` — exists |
| ClassifiedAction Pydantic model has verb/actor/target/indirect_object/params fields | YES | `models.py:15-24` |
| ClassifierVerdict is a discriminated union (ok\|no_viable_action\|no_such_target\|low_confidence) | YES | `models.py:58-61` |
| Pydantic models use extra='ignore' so Haiku output extras don't crash parsing | YES | `models.py:18` — `ConfigDict(extra="ignore")` on all models |
| Classifier retries once on malformed JSON then returns no_viable_action | YES | `classifier.py:92-100` |
| EngineConfig loads universe.yaml with defaults on missing/malformed file | YES | `config.py` — soft-fail pattern; REVIEW-FIX WR-03 extended this to engine section |
| ctx.rng property returns a seeded random.Random derived from (universe_seed, tick_id) | YES | `src/token_world/mechanic/context.py` — BLAKE2b-seeded `rng` property |
| AST validation rejects mechanic modules that import random | YES | `validation.py` — `FORBIDDEN_EXACT_IMPORTS` frozenset; 5 tests pass |
| universe scaffold creates universe.yaml with a random universe_seed if file missing | YES | `scaffold.py` — idempotent guard + `generate_universe_seed()` |

All 9 Plan 05-01 must-haves: VERIFIED (9/9)

### Plan 05-02 Must-Haves

| Must-Have | Verified | Evidence |
|-----------|----------|----------|
| Deterministic matcher iterates voluntary mechanics and scores each against classified action | YES | `matcher.py:93-141` — `DeterministicMatcher.match()` |
| Score formula: 3*verb_match + 2*target_type_match + 1*actor_type_match | YES | `matcher.py:29-60` — `score_mechanic()` |
| Ties broken alphabetically by mechanic id | YES | `matcher.py:125` — `sort(key=lambda t: (-t[1], t[0]))` |
| MatchResult is either matched or no_match (Pydantic discriminated union) | YES | `models.py:81-84` |
| WorldPropertyMatcher matches involuntary mechanics on world-property mutations | YES | `src/token_world/mechanic/matchers.py` — `WorldPropertyMatcher` added |
| DecayMatcher matches involuntary mechanics on nodes having decay_period property | YES | `matchers.py` — `DecayMatcher` added |
| TickMatcher always matches (passive per-tick invocation) | YES | `matchers.py` — `TickMatcher` added |

All 7 Plan 05-02 must-haves: VERIFIED (7/7)

### Plan 05-03 Must-Haves

| Must-Have | Verified | Evidence |
|-----------|----------|----------|
| decide(verdict, match_result) returns Decision (Execute\|Yield\|Refuse) per D-12 precedence ladder | YES | `decider.py:29-90` |
| Classifier refusal verdicts short-circuit to Refuse | YES | `decider.py:57-75` |
| Matcher no_match with well-formed classified action returns Yield | YES | `decider.py:80-84` |
| Matcher matched returns Execute | YES | `decider.py:76-79` |
| RefusalTemplate.render(reason_code, details) returns consistent narrative string | YES | `refusal.py:50-70` — 8 reason codes; _SafeDict for missing keys |
| ctx.refuse(reason_code, details) returns CheckResult(passed=False, narrative=...) via same template | YES | `context.py` — `refuse()` method added; REVIEW-FIX confirmed correct shape |

All 6 Plan 05-03 must-haves: VERIFIED (6/6)

### Plan 05-04 Must-Haves

| Must-Have | Verified | Evidence |
|-----------|----------|----------|
| VisibilityProjector.project_for(actor) returns dict[node_id, {type, properties, edges}] | YES | `visibility.py:57` |
| Projection includes actor's node, their location, containment-neighbour nodes, and held items | YES | `visibility.py` — containment walk via `location`, `contains`, `inside`, `on`, `holds` edges |
| Illumination filter dims rooms where illumination < threshold unless actor holds a light source | YES | `visibility.py` — `_apply_illumination_filter()`, ILLUMINATION_THRESHOLD=0.2 |
| hidden_properties list on a node excludes named properties from projection | YES | `visibility.py` — `_apply_hidden_properties()` strips key + list itself |
| Belief overlay applies actor.beliefs[node_id] on nodes already in projection | YES | `visibility.py` — `_apply_belief_overlay()` |
| Belief entries for nodes NOT in projection are silently ignored (no phantom nodes) | YES | `visibility.py` — conditional `if node_id in result` guard |

All 6 Plan 05-04 must-haves: VERIFIED (6/6)

**Total plan must-haves:** 28 defined across 4 plans. 28 verified, 0 failed.

**Note on unexecuted plans:** Plans 05-05 through 05-12 (observer, conservation, passive sweep, orchestrator, tick summary, MCP tools, CLI engine-turn, verification/docs) were never written or executed. Their must-haves were never defined in frontmatter because the plans themselves don't exist.

---

## Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `classifier.py` | `operator/yield_signal.py` | `SimulationEngine.run_tick()` | NOT WIRED — no orchestrator exists |
| `decider.py:YieldDecision` | `operator/yield_signal.py:YieldSignal` | engine orchestrator conversion | NOT WIRED — `YieldDecision` is never converted to `YieldSignal` |
| `matcher.py:DeterministicMatcher` | `mechanic/engine.py:ChainExecutionEngine` | execute stage | NOT WIRED — no execute stage exists |
| `visibility.py:VisibilityProjector` | Sonnet observer | observation synthesis | NOT WIRED — no observer module exists |
| `models.py:TickSummary` | `tick_summaries/tick_*.json` | tick summary writer | NOT WIRED — schema defined but no writer |
| `classifier.py:tick_diag_ctx` | `DiagnosticsSink` | engine orchestrator passing sink | NOT WIRED — orchestrator doesn't exist to pass sink |

---

## Data-Flow Trace (Level 4)

VisibilityProjector (the only wired artifact that touches dynamic data) was checked:

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `visibility.py:VisibilityProjector` | `result: dict[str, dict]` | `graph.ego_subgraph()` via `KnowledgeGraph` public API | YES — live graph queries | FLOWING |
| `classifier.py:Classifier.classify()` | `ClassifierVerdict` | Anthropic SDK `messages.create()` | YES — real LLM call (or mock in tests) | FLOWING (standalone) |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SIM-01 | 05-01 | Engine interprets resident agent text output into structured actions | PARTIAL | Classifier component complete; not orchestrated |
| SIM-02 | 05-02 | Engine matches structured actions to existing mechanics | COMPLETE | `matcher.py` + REQUIREMENTS.md traceability table: "Complete" |
| SIM-03 | 05-03 | Engine triggers mechanic generation when no existing mechanic matches (in v1: yields) | COMPLETE | `decider.py` — YieldDecision produced on no_match |
| SIM-04 | Unexecuted | Engine executes matched/generated mechanic and applies side effects to graph | MISSING | No execute stage; no orchestrator; ChainExecutionEngine not wired |
| SIM-05 | 05-04 (partial) | Observations grounded in graph state | PARTIAL | VisibilityProjector produces projected state; no observer synthesises text |
| SIM-06 | Unexecuted | Simulation history log | MISSING | No logger/sink wiring; plans 05-08/05-12 not written |
| SIM-07 | 05-04 | Observations contextually filtered | COMPLETE | VisibilityProjector with illumination, hidden_properties, belief overlay |
| SIM-08 | Unexecuted | Conservation laws enforced | MISSING | ConservationChecker not implemented; refusal template string only |
| SIM-11 | Unexecuted | Per-tick structured summary JSON | MISSING | TickSummary schema defined; no writer; tick_summaries/ dirs empty |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/token_world/mcp_server.py:89` | 89 | `"This is a Phase 0 stub."` — MCP tools still return "not implemented" | Blocker | `resume_tick`, `rollback`, `list_mechanics` MCP tools remain Phase 0 stubs; phase goal states these should be wired (plan 05-10 not executed) |
| `src/token_world/engine/__init__.py:4` | 4 | Docstring references `SimulationEngine.run_tick` which does not exist | Warning | Misleading — the class is referenced but never created |

The `TickSummary` model (`models.py:118`) is a schema-only stub: the model is defined and exported but no production code ever instantiates it with real data.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Classifier returns no_viable_action for nonsense | `uv run pytest tests/test_engine/test_classifier.py -q` | 14 passed | PASS |
| DeterministicMatcher returns MatchedResult on verb match | `uv run pytest tests/test_engine/test_matcher.py -q` | 16 passed | PASS |
| decide() returns YieldDecision on no_match | `uv run pytest tests/test_engine/test_decider.py -q` | 11 passed | PASS |
| VisibilityProjector filters dark room | `uv run pytest tests/test_engine/test_visibility.py -q` | 30 passed | PASS |
| Full pipeline classify→match→execute→observe runs end-to-end | No test exists for this | test_engine.py not created | FAIL |
| Per-tick summary written to tick_summaries/ | No test exists for this | test_tick_summary.py not created | FAIL |
| MCP resume_tick calls real engine | `uv run pytest tests/test_mcp_server.py -q` | Returns "not implemented" stub | FAIL |

---

## Human Verification Required

None — all gaps are programmatically verifiable. The missing components are absent (not ambiguously present), and the MCP stub status is confirmed by code inspection.

---

## Gaps Summary

Phase 5 was declared "Complete" (4/4 plans) but only the first four of twelve planned sub-plans were executed (Wave 0 and partial Wave 1). The core pipeline building blocks exist in isolation but are not assembled. Five specific gaps block goal achievement:

### Gap 1: No SimulationEngine orchestrator (blocks SC-1, SC-2, SC-7)

- Requirement: SIM-04 (execute), SIM-01 (full-path), SIM-06 (diagnostics)
- Missing: `src/token_world/engine/engine.py` — `SimulationEngine.run_tick(action_text, actor_id)` wiring classify → match → decide → execute → observe → tick_summary → diagnostics
- The `YieldDecision` from `decider.py` is never converted to a `YieldSignal` instance from `operator/yield_signal.py`, breaking the Phase 4.1 harness integration

### Gap 2: No observation synthesiser (blocks SC-3, SC-7)

- Requirement: SIM-05 (partial — VisibilityProjector done, Sonnet observer missing)
- Missing: `src/token_world/engine/observer.py` — Sonnet-backed synthesis with hard grounding constraint (D-15); prompt template; raw Anthropic SDK call; diagnostics write
- The projected state dict from `VisibilityProjector` has no consumer that produces observation text

### Gap 3: No conservation enforcement (blocks SC-5)

- Requirement: SIM-08
- Missing: `src/token_world/engine/conservation.py` — `ConservationChecker`; `conservation.yaml` parser; rollback-on-violation via Phase 1 snapshot mechanism
- The `conservation_violation` refusal code in `refusal.py` is a template string only

### Gap 4: No tick summary writer (blocks SC-6)

- Requirement: SIM-11
- Missing: Code that instantiates `TickSummary` and writes `tick_summaries/ticks/tick_<id>.json` after each `run_tick` call
- `TickSummary` Pydantic model (`models.py:118`) is defined with correct D-20 schema but is never used in production code

### Gap 5: No MCP tool implementation (deferred from plan 05-10)

- Requirement: UNIV-03 (revised in Phase 4)
- Missing: `resume_tick`, `rollback`, `list_mechanics` in `mcp_server.py` remain Phase 0 stubs returning "not implemented"
- The operator harness (`cli.py run-tick`) works via Python API but the MCP tools — which are how Claude Code inside a universe folder invokes the engine — are not wired

---

## Codebase Evidence

**Commits spanning Phase 5 (from SUMMARY.md reports):**
- 5e4eb31 — engine package + Pydantic models (Plan 05-01 Task 1)
- cf9d35b — EngineConfig + universe.yaml scaffolding (Plan 05-01 Task 2)
- 049bf5c — MechanicContext.rng property (Plan 05-01 Task 3)
- cba009c — AST rule + contagion.py migration (Plan 05-01 Task 4)
- b19308d — Haiku Classifier wrapper (Plan 05-01 Task 5)
- 029eb96 — shared test fixtures (Plan 05-01 Task 6)
- d66dc7c — new matcher primitives (Plan 05-02 Task 1)
- 3aaaa39 — DeterministicMatcher + registry split (Plan 05-02 Task 2)
- af48c3d — RefusalTemplate (Plan 05-03 Task 1)
- aa072f8 — Decider (Plan 05-03 Task 2)
- a0ae6a9 — ctx.refuse helper (Plan 05-03 Task 3)
- c283c1c / 7f46fdd — VisibilityProjector (Plan 05-04)
- ebd19ae — WR-01 contagion fix
- 9deac2a — WR-02 indirect_object validation
- 1f4f01d — WR-03 config soft-fail
- 172c74f — WR-04 visibility exception narrowing

**Test counts:**
- `tests/test_engine/`: 115 tests pass (8 files)
- `tests/test_mechanic/test_context_rng.py`: 8 tests
- `tests/test_mechanic/test_validation_ast_rng.py`: 5 tests
- `tests/test_mechanic/test_matchers_world_decay_tick.py`: 14 tests
- `tests/test_mechanic/test_context_refuse.py`: 8 tests
- Full suite: 1116 passed, 14 skipped

**Missing test files (per VALIDATION.md task map):**
- `tests/test_engine/test_observer.py` — never created (plan 05-05 not executed)
- `tests/test_engine/test_conservation.py` — never created (plan 05-06 not executed)
- `tests/test_engine/test_passive_sweep.py` — never created (plan 05-07 not executed)
- `tests/test_engine/test_engine.py` — never created (plan 05-08 not executed)
- `tests/test_engine/test_tick_summary.py` — never created (plan 05-08 not executed)

---

_Verified: 2026-04-13T13:09:03Z_
_Verifier: Claude (gsd-verifier)_
