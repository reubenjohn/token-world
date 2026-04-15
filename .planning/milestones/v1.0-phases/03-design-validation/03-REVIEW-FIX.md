---
phase: 03-design-validation
fixed_at: 2026-04-12
review_path: .planning/phases/03-design-validation/03-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-04-12
**Source review:** `.planning/phases/03-design-validation/03-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope (HIGH + MEDIUM): 5
- Fixed: 5
- Skipped: 0

Scope note: this review used HIGH/MEDIUM/LOW/INFO severity labels. The fix
scope `critical_warning` was mapped to HIGH + MEDIUM (LOW and INFO excluded
per config). All 5 in-scope findings were resolved with atomic commits and
accompanying regression tests. Final test suite: 291 passed (up from 281
baseline — 10 new regression tests across temporal / mermaid / use-case
loader / knowledge-graph). `uv run ruff check src/` clean. `uv run mypy
src/token_world/graph/` retains two pre-existing `no-any-return` warnings
unrelated to these fixes.

## Fixed Issues

### H-01: `find_state_at_tick` loses state on remove-then-readd sequences

**Files modified:** `src/token_world/graph/temporal.py`, `tests/test_graph/test_temporal_index.py`
**Commit:** `b85a91f`
**Applied fix:** The replay loop in `TemporalIndex.find_state_at_tick` now has a
dedicated `add_node` branch that seeds `state` from the event's
`new_value_json` payload (type + initial props) instead of resetting to `{}`.
The pre-existing `remove_node`-clears-stale-props test was kept and a new
regression test (`test_find_state_at_tick_readd_with_initial_props_seeds_state`)
covers the remove → re-add-with-props cycle that was silently wrong.

Note on prior work: commit `250cf7a` had partially addressed H-01 by treating
`add_node` the same as `remove_node` (both reset state to `{}`). That fix
prevented stale-prop leak but still dropped re-add payloads. This iteration
completes the fix as prescribed in REVIEW.md.

### M-01: `escape_label` truncation can produce broken HTML entities

**Files modified:** `src/token_world/viz/mermaid.py`, `tests/test_viz/test_mermaid_escape.py`
**Commit:** `ff1aef5`
**Applied fix:** When the escaped string exceeds `max_len`, the truncation
point is now walked back off any unterminated `&…;` or `<…>` entity before
appending the ellipsis. Four parameterised regression tests cover dense `|`,
`[`, `"`, and `\n` inputs and assert the output has no unterminated entities.

### M-02: `graph_viz.extract_subgraph` bypasses the `KnowledgeGraph` API

**Files modified:** `src/token_world/graph/knowledge_graph.py`, `src/token_world/viz/graph_viz.py`
**Commit:** `43912ba` (combined with M-03)
**Applied fix:** Added public `KnowledgeGraph.ego_subgraph(anchor, *, depth,
undirected)` method that accepts either a single anchor or a non-empty
sequence of anchors and returns a fresh `nx.DiGraph` copy with
`graph["anchors"]` pre-populated. `extract_subgraph` now delegates to this
public method instead of reaching into `kg._graph`. Docstring references the
review finding for future readers.

### M-03: `TemporalIndex` reaches into `KnowledgeGraph._events` and `_db_path`

**Files modified:** `src/token_world/graph/knowledge_graph.py`, `src/token_world/graph/temporal.py`
**Commit:** `43912ba` (combined with M-02)
**Applied fix:** Added public accessors `KnowledgeGraph.get_session_events()`
and `KnowledgeGraph.get_db_path()`. `TemporalIndex.query_history`,
`query_changes`, `_load_baseline`, and `_query_disk` now use these
accessors instead of private `_events` / `_db_path` access. The
`getattr(..., None)` fallback was removed: in-memory-only graphs return
`None` from `get_db_path()` directly, matching the `_db_path: Path | None`
type annotation.

Incidental drive-by: `isinstance(value, (list, dict))` → `isinstance(value,
list | dict)` to satisfy ruff `UP038` (pre-existing issue surfaced by the
pre-commit hook because the file was now in the change set).

### M-04: Use-case loader rejects CRLF-encoded frontmatter

**Files modified:** `src/token_world/use_cases/loader.py`, `tests/test_design_validation/test_use_case_loader.py`
**Commit:** `1b18de8`
**Applied fix:** `load_use_case` now normalises `\r\n` and bare `\r` to `\n`
before applying the `---\n` framing check. A new test module
`test_use_case_loader.py` covers LF, CRLF, and bare-CR inputs plus the two
existing error paths (missing frontmatter, no closing delimiter).

## Skipped Issues

None — all 5 in-scope findings were resolved.

---

_Fixed: 2026-04-12_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
_Worktree: `.claude/worktrees/agent-a237387b`_
_Branch: `worktree-agent-a237387b`_
