---
phase: 02-mechanic-framework
plan: 01
subsystem: mechanic-framework
tags: [mechanic, protocol, abc, dsl, matchers, chain-execution, trace]
dependency_graph:
  requires: [graph-module]
  provides: [mechanic-protocol, mechanic-context, matchers, chain-engine, execution-trace]
  affects: [seed-mechanics, mechanic-registry, simulation-engine]
tech_stack:
  added: []
  patterns: [abc-protocol, dsl-wrapper, declarative-matchers, recursive-chain-execution]
key_files:
  created:
    - src/token_world/mechanic/__init__.py
    - src/token_world/mechanic/protocol.py
    - src/token_world/mechanic/context.py
    - src/token_world/mechanic/matchers.py
    - src/token_world/mechanic/trace.py
    - src/token_world/mechanic/engine.py
    - tests/test_mechanic/__init__.py
    - tests/test_mechanic/conftest.py
    - tests/test_mechanic/test_protocol.py
    - tests/test_mechanic/test_context.py
    - tests/test_mechanic/test_matchers.py
    - tests/test_mechanic/test_engine.py
    - tests/test_mechanic/test_trace.py
  modified: []
decisions:
  - "Engine fires involuntary mechanics on all unique matching targets per mutation batch, not just the first match"
metrics:
  duration: "~6 minutes"
  completed: "2026-04-12T07:57:42Z"
  tasks_completed: 2
  tasks_total: 2
  test_count: 51
  test_suite_total: 167
---

# Phase 02 Plan 01: Mechanic Framework Core Summary

Mechanic ABC with check/apply contract, MechanicContext DSL wrapping KnowledgeGraph, declarative matchers (PropertyChange/Edge/Node), ChainExecutionEngine with recursive involuntary mechanic chaining (depth limit + cycle detection), and ExecutionTrace tree for audit trails.

## What Was Built

### Mechanic Protocol (`protocol.py`)
- `Mechanic` ABC enforcing `check(ctx) -> CheckResult` and `apply(ctx) -> list[Mutation]` contract via abstract methods
- `CheckResult` frozen dataclass with `passed: bool` and `reasons: list[str]`
- Default `voluntary = True` and `watches() -> []` for voluntary mechanics
- Forward references via `TYPE_CHECKING` to avoid circular imports

### MechanicContext (`context.py`)
- DSL wrapper providing query methods: `query_node`, `query_neighbors`, `has_node`, `has_edge`, `find_nodes`
- Mutation methods: `mutate`, `add_node`, `remove_node`, `add_edge`, `remove_edge`
- All methods delegate to `KnowledgeGraph` via private `_graph` attribute
- Carries `actor` and `target` attributes set by the engine

### Matchers (`matchers.py`)
- `PropertyChangeMatcher`: matches `set_property` mutations, optional `node_type` filter
- `EdgeMatcher`: matches `add_edge`/`remove_edge`, optional `edge_label` filter
- `NodeMatcher`: matches `add_node`/`remove_node`, optional `node_type` filter
- `matches()` function evaluating any matcher against a mutation + graph

### Chain Execution Engine (`engine.py`)
- `ChainExecutionEngine` takes involuntary mechanics list and `max_depth` (default 10)
- `execute()` runs initial mechanic, then recursively evaluates involuntary mechanic matchers against resulting mutations
- Cycle detection via `(mechanic_id, target)` pairs in a `seen` set
- Depth limit truncation with `truncated` flag on trace
- Fires on all unique matching targets per mutation batch (not just first)

### Execution Trace (`trace.py`)
- `TraceNode` dataclass: mechanic_id, actor, target, check_result, mutations, children
- `ExecutionTrace` dataclass: root, total_mechanics_executed, max_depth_reached, truncated

### Test Suite (51 tests)
- Protocol: ABC enforcement, CheckResult immutability, watches() default
- Context: all 10 DSL methods verified as correct delegation
- Matchers: property/edge/node matching with type filters, invalid event_type rejection
- Engine: basic execution, failing check, chain triggers, max_depth truncation, cycle detection, multi-target firing
- Trace: construction, defaults, tree structure

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Engine multi-target firing**
- **Found during:** Task 2 test writing
- **Issue:** Engine's inner loop had a `break` after first mutation match per mechanic, causing it to fire only once per mechanic regardless of how many distinct targets matched
- **Fix:** Collect all unique matching targets per mechanic before firing, then execute for each target
- **Files modified:** `src/token_world/mechanic/engine.py`
- **Commit:** baa1682

## Decisions Made

1. **Multi-target firing**: The engine fires involuntary mechanics once per unique target, not once per mutation batch. This is correct for scenarios like fire spreading -- a temperature change on multiple nodes should trigger the fire mechanic on each affected node independently.

## Verification Results

- All imports resolve: `from token_world.mechanic import ...` works for all 10 exports
- `uv run mypy src/token_world/mechanic/` -- Success, 0 issues in 6 files
- `uv run ruff check src/token_world/mechanic/` -- All checks passed
- `uv run pytest tests/test_mechanic/ -x -q` -- 51 passed
- `uv run pytest -v` -- 167 passed (full suite green)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 2145d9b | feat(02-01): create mechanic framework production code |
| 2 | baa1682 | test(02-01): comprehensive mechanic framework tests |

## Self-Check: PASSED

- All 13 created files exist on disk
- Both task commits (2145d9b, baa1682) found in git log
