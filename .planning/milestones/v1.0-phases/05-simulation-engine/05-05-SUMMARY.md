---
phase: 05-simulation-engine
plan: "05"
title: "Observer Sonnet synthesiser (GAP-ENG12 + D-15 hard grounding)"
subsystem: engine
tags:
  - engine
  - observer
  - sonnet
  - grounding
  - observation
  - diagnostics
dependency_graph:
  requires:
    - "05-04 (VisibilityProjector — observer consumes project_for() output)"
    - "mechanic/trace.py (ExecutionTrace + TraceNode)"
    - "mechanic/diagnostics.py (TickDiagnostics.write_observation)"
  provides:
    - "token_world.engine.observer.Observer (D-15 hard-grounding synthesiser)"
    - "Closes GAP-ENG12 (hard-constraint observation template)"
    - "Closes GAP-CROSS01 partial (observer consumption of projected state)"
  affects:
    - "05-08 (SimulationEngine.run_tick wires Observer into the tick pipeline)"
tech_stack:
  added: []
  patterns:
    - "dataclass(slots=True) with injected client — same shape as Classifier (classifier.py)"
    - "Refusal short-circuit: verbatim passthrough, no LLM call"
    - "Empty-projection fallback: darkness narrative, no LLM call"
    - "Single LLM call per synthesize() — no internal retry (pitfall #14 + #6 compliance)"
    - "Token usage captured on instance fields for tick-summary cost accounting (D-24)"
    - "Diagnostics fan-out: write_observation() called for all code paths including fallbacks"
key_files:
  created:
    - src/token_world/engine/observer.py
    - tests/test_engine/test_observer.py
  modified:
    - src/token_world/engine/__init__.py
decisions:
  - "Injected client constructor (not module-level anthropic.Anthropic()) — enables test mocking without patching"
  - "add_edge uses type= kwarg (not edge_type=) to match KnowledgeGraph convention — discovered via test failure in grounding test"
  - "Darkness fallback returned for single-actor-only projection (no edges, <=2 props) — actor floating in void without observable world context"
  - "Diagnostics write_observation called on all paths (LLM, refusal, fallback) so operator always gets an observation entry in the tick diagnostics folder"
metrics:
  duration_minutes: 25
  tasks_completed: 1
  tasks_total: 1
  files_created: 2
  files_modified: 1
  tests_added: 13
  completed_date: "2026-04-13"
---

# Phase 5 Plan 05: Observer Sonnet Synthesiser Summary

Sonnet-backed observation synthesiser that closes Gap 2 from 05-VERIFICATION.md by consuming a VisibilityProjector projection + ExecutionTrace and producing grounded prose the resident agent reads.

## One-liner

Observer wraps Sonnet under a D-15 hard-grounding system prompt, short-circuits on refusal narratives and empty projections, captures token usage for cost accounting, and fans out to TickDiagnostics on every synthesize() call path.

## What Was Built

### Task 1: Observer dataclass + grounded synthesis (TDD) — 4ee0554

`src/token_world/engine/observer.py` — `Observer` dataclass with injected client, following the same shape as `Classifier`.

**Core behaviour:**

- `synthesize(projection, trace, refusal_narrative, actor_id, action_text, tick_diag_ctx) -> str`
- **Refusal short-circuit:** if `refusal_narrative` is not None, return it verbatim (no LLM call). Diagnostics still write.
- **Empty-projection fallback:** if projection is empty or actor-only (no edges, ≤2 properties), return `"You can sense nothing — only darkness and silence."` (no LLM call). Diagnostics still write.
- **Normal path:** build grounded user prompt from (actor_id, action_text, projection JSON, trace summary), call Sonnet once, capture token usage on `last_input_tokens`/`last_output_tokens`, write diagnostics, return text.
- **Chain truncation (D-17b):** when `trace.truncated=True`, appends `"Time blurs as events cascade beyond perception."` to the user prompt.

**System prompt (`_SYSTEM_PROMPT`):**

Contains the D-15 literal phrase `"use only facts that appear in the provided state"` plus explicit instruction not to invent objects, properties, or sensory details. Output is plain text only.

**Module constant:** `_MODEL = "claude-sonnet-4-5-20250929"` — overridable per-instance via dataclass field.

**`__init__.py` update:** `Observer` added to imports and `__all__`. Docstring updated to accurately describe wired vs. pending (Plan 05-08) components.

**Test surface (13 tests — all green):**

1. `test_synthesize_returns_nonempty_text_for_normal_projection` — happy path, LLM called
2. `test_system_prompt_contains_grounding_phrase` — D-15 literal substring assert
3. `test_empty_projection_returns_darkness_fallback_no_llm_call` — empty dict → fallback, no LLM
4. `test_actor_only_projection_returns_darkness_fallback` — actor-only projection → fallback, no LLM
5. `test_refusal_narrative_returned_verbatim` — exact string match
6. `test_refusal_narrative_skips_llm_call` — no LLM on refusal
7. `test_diagnostics_written_when_tick_ctx_provided` — exactly one write_observation per call
8. `test_diagnostics_written_for_refusal_when_tick_ctx_provided` — refusal path also writes
9. `test_diagnostics_skipped_when_tick_ctx_none` — no AttributeError
10. `test_token_usage_captured_after_call` — last_input_tokens=100, last_output_tokens=20
11. `test_substring_grounding_observer_only_mentions_known_node_ids` — weak Phase-5 grounding check (D-15 + pitfall #6; full rubric deferred to Phase 6 TEST-04)
12. `test_chain_truncation_mentioned_in_user_prompt_when_trace_truncated` — D-17b closure
13. `test_llm_called_at_most_once_per_synthesize` — no internal retry

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] KnowledgeGraph.add_edge uses `type=` kwarg, not `edge_type=`**
- **Found during:** Task 1 (test #10 grounding test failure)
- **Issue:** Test-authored graph setup used `kg.add_edge("alice", "room_1", edge_type="location")` — the `edge_type` kwarg is stored as a property named `edge_type`, but `_outgoing_edges` in VisibilityProjector reads `edge_data.get("type", "related")`. Result: all edges showed as `"related"`, the location edge was never found, projection returned only `{"alice": ...}`.
- **Fix:** Changed all `add_edge` calls in the test file to use `type="location"` / `type="contains"` — matching the convention in `tests/test_engine/test_visibility.py`.
- **Files modified:** `tests/test_engine/test_observer.py`
- **Commit:** 4ee0554 (included in task commit)

**2. [Rule 1 - Bug] CheckResult uses `reasons: list[str]` not `reason: str`**
- **Found during:** Task 1 (first RED run)
- **Issue:** `_simple_trace()` helper used `CheckResult(passed=True, reason="ok")` but the dataclass field is `reasons: list[str]`.
- **Fix:** Changed to `CheckResult(passed=True, reasons=["ok"])`.
- **Files modified:** `tests/test_engine/test_observer.py`
- **Commit:** 4ee0554 (included in task commit)

## Known Stubs

None. The Observer is fully implemented. It is not yet wired into a tick pipeline (that is Plan 05-08), but as a standalone component it is complete.

## Threat Flags

None. Observer adds no new network endpoints, auth paths, or file access patterns. The grounding constraint (T-05-OBS-HALLUCINATION) is mitigated via the system prompt + test #11. The prompt injection surface (T-05-OBS-PROMPT-INJECTION) is accepted per the threat model — action_text is escaped via `!r` and projection content derives from the engine-controlled graph. The empty-crash DoS (T-05-OBS-EMPTY-CRASH) is mitigated by the darkness fallback (tests #3, #4).

## Self-Check: PASSED
