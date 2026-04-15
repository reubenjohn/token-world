---
phase: 05-simulation-engine
status: passed
verifier: gsd-verifier
verified_at: 2026-04-13T15:00:00Z
previous_status: gaps_found
previous_gaps_closed: 5
score: 7/7 success criteria verified
must_haves_verified: 56
must_haves_total: 56
re_verification:
  previous_status: gaps_found
  previous_score: 2/7
  gaps_closed:
    - "Gap 1: No SimulationEngine orchestrator — closed by Plan 05-08 (engine.py, run_tick 3-path pipeline)"
    - "Gap 2: No observation synthesiser — closed by Plan 05-05 (observer.py, D-15 grounding)"
    - "Gap 3: No conservation enforcement — closed by Plan 05-06 (conservation.py, rollback wired)"
    - "Gap 4: No tick summary writer — closed by Plan 05-07 (summary_writer.py, atomic JSON write)"
    - "Gap 5: No MCP tool implementation — closed by Plan 05-09 (mcp_server.py stubs replaced)"
  gaps_remaining: []
  regressions: []
requirement_coverage:
  - id: SIM-01
    status: complete
    evidence: "src/token_world/engine/classifier.py — Classifier.classify(); wired into run_tick Stage 1; test_run_tick_classifier_refuse_no_viable_action PASS"
  - id: SIM-02
    status: complete
    evidence: "src/token_world/engine/matcher.py — DeterministicMatcher.match(); wired into run_tick Stage 2"
  - id: SIM-03
    status: complete
    evidence: "src/token_world/engine/decider.py — decide() ladder; YieldDecision → YieldSignal emitted in _handle_yield(); test_run_tick_yield_signal_validate_succeeds PASS"
  - id: SIM-04
    status: complete
    evidence: "src/token_world/engine/engine.py:200 — SimulationEngine.run_tick(); ChainExecutionEngine wired; test_run_tick_execute_path_calls_chain_execution_engine PASS"
  - id: SIM-05
    status: complete
    evidence: "src/token_world/engine/observer.py — Observer.synthesize() with D-15 phrase; VisibilityProjector feeds it; test_system_prompt_contains_grounding_phrase PASS"
  - id: SIM-06
    status: complete
    evidence: "engine.py:219-230 — DiagnosticsSink.open_tick() with _ClassifierDiagnosticsAdapter; test_run_tick_writes_diagnostics_per_tick_folder PASS"
  - id: SIM-07
    status: complete
    evidence: "src/token_world/engine/visibility.py — VisibilityProjector with illumination, hidden_properties, belief overlay; 30 tests"
  - id: SIM-08
    status: complete
    evidence: "src/token_world/engine/conservation.py — ConservationChecker.verify(); rollback via graph.restore(); test_run_tick_conservation_violation_rolls_back_and_refuses PASS"
  - id: SIM-11
    status: complete
    evidence: "src/token_world/engine/summary_writer.py — TickSummaryWriter.write() to tick_summaries/ticks/tick_<id>.json; test_run_tick_execute_path_writes_tick_summary_file PASS"
  - id: UNIV-03
    status: complete
    evidence: "src/token_world/mcp_server.py — resume_tick/rollback/list_mechanics fully implemented; 29 tests in test_mcp_tools.py"
---

# Phase 05: Simulation Engine — Re-Verification Report

**Phase Goal:** The engine interprets text actions, routes them to mechanics (or yields to the operator when none match), executes selected mechanics, and returns grounded observations — the full pipeline works end-to-end without a live agent. Under the inversion-of-control model established in Phase 4, the engine NEVER generates code; when no mechanic matches, it halts the tick and yields to the operator, which authors the needed mechanic via normal SDLC before the tick resumes.

**Verified:** 2026-04-13T15:00:00Z
**Status:** PASSED
**Re-verification:** Yes — supersedes gaps_found report from 2026-04-13T13:09:03Z

---

## Summary

The initial verification (2026-04-13T13:09:03Z) found `gaps_found` with 5 blocking gaps: no SimulationEngine orchestrator, no Sonnet observer, no conservation enforcement, no tick summary writer, and MCP tools remaining Phase 0 stubs. All 5 gaps were closed by Plans 05-05 through 05-09, plus two code-review + fix cycles (Wave 1 WR-01..WR-04, Wave 2-4 WR-01..WR-04) that added 13+4=17 regression tests. This re-verification confirms the phase goal is fully achieved.

**Score progression:** 2/7 (initial) → 7/7 (re-verification)
**Test count progression:** 1116 passed (initial) → 1219 passed (re-verification, +103 tests)

---

## Gap Closure Evidence

### Gap 1: No SimulationEngine orchestrator → CLOSED by Plan 05-08

**Plan:** 05-08 (SimulationEngine.run_tick orchestrator)
**Commit:** af9a2d3 (feat), 0b6effb (test+fix), + Wave2 review fixes a7c4cf4/f4256f4/2da13f6

`src/token_world/engine/engine.py` — `SimulationEngine.run_tick(action_text, actor) -> TickResult` implements the full D-01 five-stage pipeline:

1. Stage 1: `Classifier.classify()` (Haiku, with `_ClassifierDiagnosticsAdapter` for Phase-4 sink wiring)
2. Stage 2: `DeterministicMatcher.match()` on `VerdictOk` path
3. Stage 3: `decide(verdict, match_result)` — precedence ladder
4. Stage 4: `ChainExecutionEngine.execute()` on execute path; `YieldSignal` construction on yield path; `RefusalTemplate.render()` on refuse path
5. Stage 5: `Observer.synthesize()` with `VisibilityProjector` projection on execute path

Three terminal paths verified by tests:
- `test_run_tick_execute_path_returns_ok_with_observation` — PASS
- `test_run_tick_yield_path_no_match_returns_yieldsignal` — PASS
- `test_run_tick_classifier_refuse_no_viable_action` — PASS

D-02 idempotent registry: `self._registry.scan()` at top of every `run_tick` — verified by `test_run_tick_idempotent_registry_scan_picks_up_new_mechanic_after_first_call`.

**SIM-01, SIM-04, SIM-06, AUTO-02 closed.**

### Gap 2: No observation synthesiser → CLOSED by Plan 05-05

**Plan:** 05-05 (Observer Sonnet synthesiser)
**Commit:** 4ee0554

`src/token_world/engine/observer.py` — `Observer` dataclass wrapping Sonnet under `_SYSTEM_PROMPT` containing the D-15 literal phrase:

> "HARD GROUNDING CONSTRAINT: use only facts that appear in the provided state"

The observer has three code paths:
- Refusal short-circuit: returns narrative verbatim, no LLM call
- Empty-projection fallback: returns darkness text, no LLM call
- Normal path: single Sonnet call with projected state JSON + trace summary

All three paths write to `TickDiagnostics` and are tested:
- `test_system_prompt_contains_grounding_phrase` — D-15 literal substring assert, PASS
- `test_refusal_narrative_returned_verbatim` — PASS
- `test_empty_projection_returns_darkness_fallback_no_llm_call` — PASS
- `test_substring_grounding_observer_only_mentions_known_node_ids` — weak Phase-5 grounding check (full rubric deferred to Phase 6 TEST-04 per plan), PASS

**SIM-05 closed.**

### Gap 3: No conservation enforcement → CLOSED by Plan 05-06

**Plan:** 05-06 (ConservationChecker)
**Commits:** 49095bc, 7d46b5a

`src/token_world/engine/conservation.py` — `ConservationChecker.from_yaml(path)` (soft-fail loader) + `verify(mutations) -> ConservationVerdict`.

Conservation enforcement wired in `engine.py` at two points:
1. After primary `ChainExecutionEngine.execute()` (`engine.py:383-418`)
2. After passive sweep combined mutations (`engine.py:432-462`)

On `is_violation`: `graph.restore(pre_tick_snapshot_id)` called, `RefusalTemplate.render("conservation_violation", ...)` narrative returned, `TickResult.refused(...)` returned. Test: `test_run_tick_conservation_violation_rolls_back_and_refuses` — PASS.

Consecutive rollbacks produce distinct monotonic tick IDs verified by `test_run_tick_consecutive_conservation_rollbacks_produce_distinct_tick_ids` — PASS (Wave 2 WR-03 fix).

`conservation.yaml` scaffolded idempotently by `scaffold.py` in every new universe.

**SIM-08 closed.**

### Gap 4: No tick summary writer → CLOSED by Plan 05-07

**Plan:** 05-07 (TickSummaryWriter)
**Commit:** 63f5e62

`src/token_world/engine/summary_writer.py` — `TickSummaryWriter.write(summary, universe_dir)` writes `tick_summaries/ticks/tick_<id>.json` atomically (via Phase 4's `_atomic_write_json`: tempfile + os.fsync + os.replace). `build_tick_summary(...)` factory handles all three decision paths (execute/yield/refuse).

`_write_summary()` called at all three terminal paths in `engine.py` so every tick produces a JSON file regardless of outcome.

Test: `test_run_tick_execute_path_writes_tick_summary_file` — PASS. Atomic write (no .tmp leftovers), JSON round-trip, Pydantic re-validation all tested in `test_summary_writer.py` (18 tests).

**SIM-11 closed.**

### Gap 5: MCP tool stubs → CLOSED by Plan 05-09

**Plan:** 05-09 (MCP tool wiring)
**Commit:** d8bee27

`src/token_world/mcp_server.py` — all three Phase 0 stubs replaced:
- `_tool_resume_tick`: constructs `SimulationEngine` + `KnowledgeGraph` from `universe_path`, calls `run_tick()`, serialises `TickResult` to JSON payload including `yield_signal` on yield path
- `_tool_rollback`: `graph.restore(snapshot_id)` + `graph.save()` + returns `{ok, snapshot_id, restored_to_tick, rolled_back_from_tick}`
- `_tool_list_mechanics`: `MechanicRegistry.list_mechanics()` with optional substring filter

Path-traversal defence: `_require_universe_path` rejects `..` segments. Error routing: `-32602` for param errors, `-32603` (generic, no exc leak — Wave 2 WR-04 fix) for internal errors.

Stub text absent: grep for `"This is a Phase 0 stub."` in `mcp_server.py` returns no matches.

29 tests in `tests/test_universe/test_mcp_tools.py` covering execute/yield paths, rollback restore, filter, all error codes, path-traversal.

**UNIV-03 closed.**

---

## Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Text action classified into structured action; `no_viable_action` for nonsense | VERIFIED | `classifier.py:59` + `engine.py:238` Stage 1 wired; `test_run_tick_classifier_refuse_no_viable_action` PASS |
| 2 | No mechanic match → halt with structured yield signal; `resume_tick` picks up new mechanic post-authoring | VERIFIED | `engine.py:_handle_yield()` builds `YieldSignal` + calls `validate()`; `test_run_tick_yield_signal_validate_succeeds` PASS; D-02 registry re-scan picks up new mechanics: `test_run_tick_idempotent_registry_scan_picks_up_new_mechanic_after_first_call` PASS |
| 3 | Observations contain only information derivable from graph state | VERIFIED | `observer.py:43` — D-15 literal phrase; `test_system_prompt_contains_grounding_phrase` PASS; `test_substring_grounding_observer_only_mentions_known_node_ids` PASS |
| 4 | Observations contextually filtered (temperature hidden when examining keyboard) | VERIFIED | `visibility.py` — containment walk, illumination filter, `hidden_properties` stripping; 30 tests PASS |
| 5 | Conservation laws enforced; mechanics cannot create matter/energy from nothing | VERIFIED | `conservation.py` — `ConservationChecker.verify()`; rollback on violation; `test_run_tick_conservation_violation_rolls_back_and_refuses` PASS |
| 6 | Per-tick summaries written to `tick_summaries/` after each tick | VERIFIED | `summary_writer.py` — `TickSummaryWriter.write()`; `test_run_tick_execute_path_writes_tick_summary_file` PASS; atomic write via `_atomic_write_json` |
| 7 | Classifier, matcher, observer LLM calls wired to DiagnosticsSink (AUTO-02 end-to-end) | VERIFIED | `engine.py:219-230` — `_ClassifierDiagnosticsAdapter` bridges Wave 1 classifier API to Phase 4 `TickDiagnostics`; observer wired via `tick_diag_ctx`; `test_run_tick_writes_diagnostics_per_tick_folder` PASS |

**Score: 7/7 success criteria verified.**

---

## Required Artifacts

| Artifact | Provides | Status | Evidence |
|----------|----------|--------|----------|
| `src/token_world/engine/engine.py` | SimulationEngine.run_tick, TickResult | VERIFIED | exists, 825 lines, 3-path pipeline; imported from `token_world.engine` |
| `src/token_world/engine/observer.py` | Observer, D-15 hard grounding | VERIFIED | exists; `_SYSTEM_PROMPT` contains grounding phrase |
| `src/token_world/engine/conservation.py` | ConservationChecker, ConservationVerdict | VERIFIED | exists; wired in engine.py at two points |
| `src/token_world/engine/summary_writer.py` | TickSummaryWriter, build_tick_summary | VERIFIED | exists; atomic write; all 3 decision paths covered |
| `src/token_world/mcp_server.py` | resume_tick, rollback, list_mechanics | VERIFIED | stubs replaced; "This is a Phase 0 stub." absent |
| `src/token_world/engine/classifier.py` | Classifier (Haiku, 4 verdicts) | VERIFIED | exists; wired Stage 1 |
| `src/token_world/engine/matcher.py` | DeterministicMatcher | VERIFIED | exists; wired Stage 2 |
| `src/token_world/engine/decider.py` | decide() precedence ladder | VERIFIED | exists; wired Stage 3 |
| `src/token_world/engine/visibility.py` | VisibilityProjector | VERIFIED | exists; feeds observer |
| `src/token_world/engine/refusal.py` | RefusalTemplate (8 codes) | VERIFIED | exists; used across all refusal paths |
| `src/token_world/engine/models.py` | Pydantic pipeline types | VERIFIED | exists; all exported from `__init__.py` |
| `src/token_world/engine/config.py` | EngineConfig, soft-fail loader | VERIFIED | exists; WR-03 fix extends soft-fail to all fields |

---

## Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `classifier.py:Classifier.classify()` | `engine.py:run_tick Stage 1` | direct call in `_handle_execute/_handle_yield/_handle_refuse` | WIRED |
| `decider.py:YieldDecision` | `operator/yield_signal.py:YieldSignal` | `engine.py:_handle_yield()` builds YieldSignal from classified_action + actor_state | WIRED |
| `matcher.py:DeterministicMatcher` | `mechanic/engine.py:ChainExecutionEngine` | `engine.py:_handle_execute()` — match result → mechanic_id → registry.get_mechanic → chain_engine.execute | WIRED |
| `visibility.py:VisibilityProjector` | `observer.py:Observer.synthesize()` | `engine.py:_handle_execute():468` — `projection = self._projector.project_for(actor)` then `self._observer.synthesize(projection=projection, ...)` | WIRED |
| `models.py:TickSummary` | `tick_summaries/ticks/tick_<id>.json` | `summary_writer.py:TickSummaryWriter.write()` → `_atomic_write_json()` | WIRED |
| `classifier.py:tick_diag_ctx` | `mechanic/diagnostics.py:DiagnosticsSink` | `engine.py:230` — `_ClassifierDiagnosticsAdapter(tick_ctx)` bridging Wave 1 write_prompt/write_response/write_parsed to TickDiagnostics.write_classification | WIRED |
| `conservation.py:ConservationChecker.verify()` | `graph.py:KnowledgeGraph.restore()` | `engine.py:388` — `self._graph.restore(pre_tick_snapshot_id)` on violation | WIRED |
| `mcp_server.py:_tool_resume_tick` | `engine.py:SimulationEngine.run_tick()` | lazy import + construction in `_tool_resume_tick` | WIRED |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `observer.py:Observer.synthesize()` | `projection: dict[str, dict]` | `VisibilityProjector.project_for(actor)` → `KnowledgeGraph.ego_subgraph()` | YES — live graph queries | FLOWING |
| `engine.py:run_tick()` | `verdict` | `Classifier.classify()` → Anthropic SDK (Haiku) | YES — real LLM call or mock in tests | FLOWING |
| `summary_writer.py:TickSummaryWriter.write()` | `summary: TickSummary` | `build_tick_summary(tick_id, action_text, decision, classified_action, trace, ...)` | YES — real tick data from pipeline | FLOWING |
| `conservation.py:ConservationChecker.verify()` | `mutations: list[Mutation]` | `_flatten_mutations(primary_trace)` from ChainExecutionEngine | YES — real mutation list from mechanic execution | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Test | Result | Status |
|----------|------|--------|--------|
| Text action classified (Haiku), `no_viable_action` for nonsense | `test_run_tick_classifier_refuse_no_viable_action` | PASS | PASS |
| Execute path returns observation text | `test_run_tick_execute_path_returns_ok_with_observation` | PASS | PASS |
| Yield path emits valid YieldSignal (Phase 4.1 contract) | `test_run_tick_yield_signal_validate_succeeds` | PASS | PASS |
| Conservation violation rolls back graph + refuses | `test_run_tick_conservation_violation_rolls_back_and_refuses` | PASS | PASS |
| Tick summary JSON written to tick_summaries/ticks/ | `test_run_tick_execute_path_writes_tick_summary_file` | PASS | PASS |
| Diagnostics written per-tick to diagnostics/ folder | `test_run_tick_writes_diagnostics_per_tick_folder` | PASS | PASS |
| D-02 registry re-scan picks up post-yield mechanic | `test_run_tick_idempotent_registry_scan_picks_up_new_mechanic_after_first_call` | PASS | PASS |
| Observer D-15 grounding phrase in system prompt | `test_system_prompt_contains_grounding_phrase` | PASS | PASS |
| Passive sweep TickMatcher fires every tick | `test_tick_matcher_mechanic_fires_every_tick` | PASS | PASS |
| Passive sweep DecayMatcher fires for decay_period nodes | `test_decay_matcher_mechanic_fires_when_node_has_decay_period` | PASS | PASS |
| Passive sweep WorldPropertyMatcher fires on world property mutation | `test_world_property_matcher_fires_only_when_world_property_mutated` | PASS | PASS |
| MCP resume_tick returns observation from real engine | `TestResumeTick::test_resume_tick_execute_path_returns_observation` | PASS | PASS |
| Consecutive conservation rollbacks produce distinct tick IDs | `test_run_tick_consecutive_conservation_rollbacks_produce_distinct_tick_ids` | PASS | PASS |

---

## Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| SIM-01 | Engine interprets resident agent text output into structured actions | COMPLETE | `engine.py:238` Stage 1 classify wired |
| SIM-02 | Engine matches structured actions to existing mechanics | COMPLETE | `engine.py:255` Stage 2 match wired |
| SIM-03 | Engine halts and yields to operator when no mechanic matches | COMPLETE | `engine.py:_handle_yield()` emits YieldSignal via Phase 4.1 contract |
| SIM-04 | Engine executes matched mechanic and applies side effects to graph | COMPLETE | `engine.py:_handle_execute()` chains ChainExecutionEngine |
| SIM-05 | Observations grounded in graph state (no hallucinated state) | COMPLETE | `observer.py` D-15 hard-grounding; VisibilityProjector feeds projected state |
| SIM-06 | Simulation history log: actions, mechanics, mutations, observations | COMPLETE | `DiagnosticsSink.open_tick()` + `_ClassifierDiagnosticsAdapter`; per-tick diagnostics/ folder |
| SIM-07 | Observations contextually filtered (only relevant properties) | COMPLETE | `visibility.py` containment walk + illumination + hidden_properties |
| SIM-08 | Conservation laws enforced; attempts produce failure observations | COMPLETE | `conservation.py` ConservationChecker; rollback + refuse on violation |
| SIM-11 | Per-tick structured summary JSON in tick_summaries/ | COMPLETE | `summary_writer.py` TickSummaryWriter; atomic write; all 3 decision paths |
| UNIV-03 | Generated .mcp.json exposes resume_tick, rollback, list_mechanics | COMPLETE | `mcp_server.py` fully wired; 29 new tests |
| GAP-ENG07 | Passive sweep: involuntary mechanics fire per tick | COMPLETE | `engine.py:_run_passive_sweep()` — TickMatcher/DecayMatcher/WorldPropertyMatcher; 9 sweep tests |

---

## Anti-Pattern Scan

| File | Pattern | Severity | Status |
|------|---------|----------|--------|
| `mcp_server.py` | `"This is a Phase 0 stub."` | Blocker (previous) | CLEARED — grep returns no matches |
| `engine.py` | `_ClassifierDiagnosticsAdapter` in-file shim | Info | ACCEPTABLE — thin bridge (32 lines), IN-03 deferred to cleanup pass |
| `observer.py` | `full_prompt` variable name slightly misleading | Info | ACCEPTABLE — IN-01 deferred; code is correct |
| `observer.py`, `summary_writer.py`, `engine.py` | Duplicate `_flatten_mutations` | Info | ACCEPTABLE — IN-02 deferred; all 3 equivalent; promotion to `mechanic.trace` in a future cleanup |

No blockers or warnings present in the codebase.

---

## Deferred Items (Not Gaps)

These items were identified during code review but explicitly deferred as non-blocking:

| Item | Source | Deferred To | Reason |
|------|--------|-------------|--------|
| `NoMatchResult.candidates` always empty (IN-01 from Wave 1 review) | `matcher.py` | Future cleanup | Not a correctness bug for yield path; D-11 candidate hint feature not implemented |
| Belief overlay can write untrusted property names (IN-02 from Wave 1 review) | `visibility.py` | Phase 6 | Within D-14 v1 spec; observer grounding constraint mitigates |
| `full_prompt` variable name misleading (IN-01 Wave 2 review) | `observer.py` | Cleanup pass | Cosmetic; code is correct |
| Duplicate `_flatten_mutations` (IN-02 Wave 2 review) | `observer.py`, `summary_writer.py`, `engine.py` | Cleanup pass | Implementations equivalent; no divergence risk yet |
| `_ClassifierDiagnosticsAdapter._maybe_flush` silent no-op on unknown stages (IN-03 Wave 2 review) | `engine.py` | Cleanup pass | Dormant; classifier uses consistent stage names |
| Full LLM grounding rubric for observer (TEST-04) | `observer.py` | Phase 6 | Expensive; deferred to milestone boundary per plan |

None of these affect the phase goal or any requirement covered by Phase 5.

---

## Codebase Evidence

**All Phase 5 commits confirmed in git log:**

Wave 0-1 (Plans 05-01..05-04): 5e4eb31, cf9d35b, 049bf5c, cba009c, b19308d, 029eb96, d66dc7c, 3aaaa39, af48c3d, aa072f8, a0ae6a9, c283c1c, 7f46fdd

Wave 1 review fixes: ebd19ae (WR-01), 9deac2a (WR-02), 1f4f01d (WR-03), 172c74f (WR-04)

Wave 2-4 (Plans 05-05..05-09): 4ee0554, 49095bc, 7d46b5a, 63f5e62, af9a2d3, 0b6effb, d8bee27

Wave 2-4 review fixes: a7c4cf4 (WR-01), f4256f4 (WR-02), 2da13f6 (WR-03), f97327f (WR-04)

**Test suite:**
- Full suite: **1219 passed, 14 skipped** (vs 1116 at initial verification, +103 tests)
- `tests/test_engine/`: 189 tests (15 files)
- `tests/test_universe/test_mcp_tools.py`: 29 tests
- Ruff: clean (`uv run ruff check src/`)
- Mypy (graph module): clean

**Source files confirmed present:**
- `src/token_world/engine/__init__.py` — 63 lines, all components exported in `__all__`
- `src/token_world/engine/engine.py` — 825 lines, SimulationEngine + TickResult
- `src/token_world/engine/observer.py` — Observer with D-15 system prompt
- `src/token_world/engine/conservation.py` — ConservationChecker + ConservationVerdict
- `src/token_world/engine/summary_writer.py` — TickSummaryWriter + build_tick_summary
- `src/token_world/mcp_server.py` — 3 real tool implementations, no Phase 0 stubs

---

_Verified: 2026-04-13T15:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — initial was gaps_found (2026-04-13T13:09:03Z); all 5 gaps closed_
