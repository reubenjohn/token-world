# Phase 16: Composite Actions — Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous smart discuss)

<domain>
## Phase Boundary

REQ-V12-ENGINE-04: One agent action can fire multiple primary mechanics within a tick, unblocking richer narrative ("I open the chest and take the key") without changing the mechanic protocol.

Four SC deliverables:
- SC-1: `docs/design/composite-actions.md` documents the chosen design (v1.2 D-01) with decision rationale referenced from PROJECT.md Key Decisions
- SC-2: Classifier emits `actions: [...]` array; single-verb input wraps as 1-element list (back-compat guarantee)
- SC-3: Multi-verb fixture input produces multi-mechanic `ExecutionTrace` with one entry per sub-action, each independently refusable
- SC-4: Classifier `SCHEMA_VERSION` bumped; prompt-hash registry records the bump; yield-handler subagent prompt notes per-sub-action invocation contract

Architectural constraint: design wave must close before implementation starts. Phase 16 uses two waves: Wave 1 = design + classifier schema, Wave 2 = engine wiring + tests.

</domain>

<decisions>
## Implementation Decisions

### Design choice (v1.2 D-01)
- **Option 1 chosen:** Classifier emits `actions: [...]` list
- Rationale: lowest blast radius — classifier already understands sequential English ("and", "then"); no new component; matcher and chain engine are unchanged; single-action wraps as 1-element list for back-compat
- Alternative (Option 2, top-K matching) rejected: riskier — `check()` may pass for accidentally-overlapping mechanics not meant to fire together
- Alternative (Option 3, ActionDecomposer stage) rejected: extra LLM call per multi-verb action; adds latency and cost

### Classifier schema change
- Current: `ClassifiedAction` has single verb/actor/target; classifier returns one `VerdictOk.classified`
- New: `VerdictOk.classified` becomes `VerdictOk.actions: list[ClassifiedAction]` (non-empty)
- Back-compat: single-verb inputs → list with one element; all existing tests wrapping `VerdictOk` still pass since they can read `verdict.actions[0]`
- `SCHEMA_VERSION` constant in `classifier.py` bumped (current: check file, likely "1.0")
- Prompt update: system prompt tells the classifier to emit `{"kind":"ok","actions":[{...classified...},...], "confidence":0.0-1.0}`

### Engine iteration
- `engine.py` current flow: classify → ONE `ClassifiedAction` → match → decide → execute
- New flow: classify → `list[ClassifiedAction]` → **for each sub-action**: match → decide → execute; collect all `ExecutionTrace` nodes
- Sub-actions execute in order; each is independently refusable (if one refuses, others still run)
- Combined `ExecutionTrace` returned from all sub-actions (root trace chains sub-results)
- `TickSummaryWriter` updated to record the multi-action case in tick JSON
- Tick summary `classified_action` field: keep single-action field for back-compat (use `actions[0]`); add `classified_actions` list field for multi-action inspection

### Yield handling for composite ticks
- If any sub-action yields, the whole tick yields (as today; first yield wins)
- Yield-handler subagent prompt notes it may be invoked once per sub-action
- Update `operator/yield_signal.py` prompt if it contains action-specific language

### Test strategy
- Fixture: `"open the chest and take the key"` → classifier (mocked) returns 2 `ClassifiedAction` objects → engine produces 2-entry `ExecutionTrace`
- Back-compat: single-verb fixture still produces 1-entry trace
- Schema version test: verify `SCHEMA_VERSION` constant incremented
- All existing tests must pass unmodified (the `VerdictOk.actions[0]` wrapper preserves old contract)

### Wave structure
- Wave 1 (16-01): Design doc `docs/design/composite-actions.md` + classifier schema bump (`models.py`, `classifier.py`, `_SYSTEM_PROMPT`) + `SCHEMA_VERSION` constant
- Wave 2 (16-02): Engine iteration loop + tick summary update + yield-handler prompt update + regression tests

</decisions>

<code_context>
## Existing Code Insights

- `src/token_world/engine/classifier.py` — `Classifier` class, `_SYSTEM_PROMPT`, `SCHEMA_VERSION` (check if exists), `VerdictAdapter`
- `src/token_world/engine/models.py` — `ClassifiedAction`, `VerdictOk` (currently has single `classified: ClassifiedAction`)
- `src/token_world/engine/engine.py` — `SimulationEngine.run_tick()` orchestrates: classify → match → decide → execute
- `src/token_world/engine/matcher.py` — `DeterministicMatcher.match(classified_action)` — takes single action
- `src/token_world/engine/decider.py` — `decide(match_result, ...)` — takes single match result
- `src/token_world/mechanic/engine.py` — `ChainExecutionEngine` — executes single mechanic + cascades
- `src/token_world/mechanic/trace.py` — `ExecutionTrace`, `collect_mutations()`
- `src/token_world/engine/summary_writer.py` — `build_tick_summary()` — writes `classified_action` field
- `src/token_world/operator/yield_signal.py` — yield handler prompt

</code_context>

<specifics>
## Specific Requirements

- Wave 1 must be committed before Wave 2 begins (design gate)
- `docs/design/composite-actions.md` must reference PROJECT.md Key Decisions as the authoritative decision log
- MORNING-HANDOFF §E1 three options must be summarized in the design doc with rationale for choosing Option 1
- Prompt hash baseline file must be updated after `_SYSTEM_PROMPT` changes (`scripts/update_prompt_hashes.py`)
- No dashboard changes in this phase (dashboard already renders `ExecutionTrace` tree)

</specifics>

<deferred>
## Deferred Ideas

- Multi-agent conflict detection (v2.0 — D-18)
- Option 2 (top-K matching) and Option 3 (ActionDecomposer) — rejected for v1.2
- Per-sub-action diagnostics panels in dashboard (v2.0)

</deferred>
