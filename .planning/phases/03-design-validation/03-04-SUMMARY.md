---
phase: 03-design-validation
plan: 04
subsystem: visualization
tags: [cli, mermaid, visualization, viz-graph, injection-mitigation]

# Dependency graph
requires:
  - phase: 01-graph-foundation
    provides: KnowledgeGraph API (_graph attr, nodes(**filters), has_node)
  - phase: 03-design-validation
    plan: 01
    provides: token_world.viz package + escape_label() (Wave 0 scaffolding)
provides:
  - src/token_world/viz/graph_viz.py (extract_subgraph, to_mermaid, TooManyNodesError)
  - token-world viz-graph CLI subcommand (filtered Mermaid flowchart emission)
  - docs/guides/viz-graph.md (user-facing usage guide, 119 lines)
  - T-03-02 mitigation shipped end-to-end (label escape + ID sanitization with
    sha256 collision suffix)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Undirected ego_graph as the always-filtered 'focused view' primitive
       (whole-graph rendering explicitly unsupported)"
    - "Sanitised Mermaid IDs via alphanum-only filter + sha256[:6] suffix on
       substitution -- prevents collision between x\" and x|"
    - "Anchor always preserved through downstream filters (so user's explicit
       focus is never silently dropped)"

key-files:
  created:
    - src/token_world/viz/graph_viz.py
    - tests/test_cli/__init__.py
    - tests/test_cli/test_viz_graph.py
    - docs/guides/viz-graph.md
  modified:
    - src/token_world/viz/__init__.py  # re-export graph_viz symbols
    - src/token_world/cli.py           # register viz-graph subcommand
    - tests/test_viz/test_viz_graph.py # extend Wave 0 stubs with 6 new tests

key-decisions:
  - "Node IDs sanitized with sha256[:6] suffix on substitution -- guarantees
     distinct Mermaid IDs for distinct dangerous inputs (x\", x|)"
  - "Anchors always preserved through --type/--has-property/--exclude-property
     filters -- user's explicit focus is never silently dropped"
  - "Whole-graph rendering is intentionally unsupported (exit 2 without an
     anchor flag) -- diagrams of 1000+ nodes are unreadable; force filtering"
  - "Exit codes 0/1/2/3/4 map to success / missing universe / bad-anchor /
     empty-anchor-set / node-cap-exceeded -- scriptable discrimination"

patterns-established:
  - "CLI-level smoke tests under tests/test_cli/ using CliRunner + tmp_path
     XDG_DATA_HOME redirection -- isolates universe creation per-test"
  - "Mermaid emission = subgraph.nodes loop + subgraph.edges loop, skipping
     edges whose endpoints were filtered out of the kept set"

requirements-completed: [AUTO-04]

# Metrics
duration: ~5min
completed: 2026-04-12
---

# Phase 3 Plan 04: viz-graph CLI Summary

**`token-world viz-graph` ships end-to-end: filtered ego-graph extraction, Mermaid flowchart emission with label/ID escaping, 150-node cap, and a 119-line user guide — rendered cleanly by `mmdc` on the first try.**

## Performance

- **Duration:** ~5 min
- **Completed:** 2026-04-12
- **Tasks:** 3
- **Files touched:** 7 (4 created, 3 modified)

## Accomplishments

- `extract_subgraph(kg, anchor=..., depth=...)` and `extract_subgraph(kg, anchors=[...], depth=...)` return an ego-graph (undirected) or union thereof.
- `to_mermaid(kg, sub, max_nodes=150, style=True, type_filter=..., has_property=..., exclude_property=...)` emits a `flowchart LR` block with `classDef agent`/`classDef entity` styling and emoji-prefixed labels.
- `TooManyNodesError` is raised with an actionable message ("tighten filter with --depth, --type, ..."), mapped to CLI exit 4.
- `token-world viz-graph SLUG` CLI registered with 11 flags (`--node`, `--depth`, `--seed-query`, `--all-agents`, `--type`, `--has-property`, `--exclude-property`, `--max-nodes`, `--output`, `--no-style`, + universe positional).
- T-03-02 mitigation shipped: every label runs through `escape_label()`; every Mermaid ID runs through `_sanitize_mermaid_id()` (alphanum-only, sha256 suffix on substitution so `x"` vs `x|` produce distinct IDs).
- 10 new viz module tests + 10 CLI smoke tests = 20 new tests, all green. Full suite: 275 passed, 5 skipped (Wave 2+ UC/GAP stubs), 0 failed.
- End-to-end render verified: sample graph piped through `mmdc` produced a valid PNG without parse errors.

## Task Commits

1. **Task 1: viz.graph_viz module + 6 new tests** — `e3d2eda` (feat)
2. **Task 2: viz-graph CLI subcommand + 10 CLI smoke tests** — `d336d91` (feat)
3. **Task 3: docs/guides/viz-graph.md user guide** — `51ba9bc` (docs)

## Files Created / Modified

### Source

- `src/token_world/viz/graph_viz.py` (new, 237 LOC) — `extract_subgraph`, `to_mermaid`, `TooManyNodesError`, `_sanitize_mermaid_id`, `render_node_label`, `render_edge_label`, `_pick_display_props`, `_node_type`, `_keep_node`.
- `src/token_world/viz/__init__.py` — re-export `extract_subgraph`, `to_mermaid`, `TooManyNodesError` (alongside existing `escape_label`).
- `src/token_world/cli.py` — new `viz-graph` Click subcommand at end of file; reuses `UniverseManager` + `KnowledgeGraph` + `token_world.viz` public API.

### Tests

- `tests/test_viz/test_viz_graph.py` — extended from 6 Wave 0 stubs to 12 tests (added: edge relation labels, no-style minimal, multi-anchor union, type filter, anchor preservation, ID collision hash suffix).
- `tests/test_cli/__init__.py` (new, empty package marker).
- `tests/test_cli/test_viz_graph.py` (new, 10 tests) — anchor required, help surfaces all anchor flags, flowchart emission, max-nodes cap, output file, type/seed filters, all-agents, missing universe, --no-style.

### Docs

- `docs/guides/viz-graph.md` (new, 119 lines) — Why, Quick Examples (7 commands), Flags (table of all 11 options), Anchor-is-mandatory (exit-code table), Rendering to PNG (mcp-mermaid + mmdc + GitHub markdown), When rendering fails (5 tightening strategies), Node label format, Security note (T-03-02 mitigation).

## Decisions Made

- **sha256[:6] suffix on ID sanitisation.** Plain substitution (`x"` -> `x_`, `x|` -> `x_`) would collide. The hash suffix is appended only when substitution happened, so safe IDs stay readable (`alice` -> `alice`) while dangerous ones become distinguishable (`x"` -> `x__f07e4a`, `x|` -> `x__7c2b91`).
- **Anchors preserved through all downstream filters.** `_keep_node` is consulted *only* for non-anchor nodes. Rationale: the user asked explicitly to focus on these nodes; silently dropping them because they don't carry the `has_property` filter would be surprising.
- **Access `kg._graph` directly in `extract_subgraph`.** The public `KnowledgeGraph` API doesn't expose the underlying `nx.DiGraph` and adding a getter wasn't in scope. The private attr is stable (used throughout the codebase in `spatial.py`, `temporal.py`, etc.) and the access point is documented in the module docstring with an inline comment (`# intentional access to the underlying DiGraph`).
- **`node_type` check reads `props.get("type")` first, falls back to `props.get("node_type")`.** `KnowledgeGraph.add_node` stores the type under the key `type` (see `knowledge_graph.py:157`). The `node_type` fallback preserves compatibility if that convention ever changes.
- **Exit codes 2/3/4 distinguish anchor errors from cap errors.** Scripts can discriminate "user needs to supply a filter" (2) from "filter matched nothing" (3) from "filter matched too much" (4). Universe-not-found keeps exit 1 (matches existing CLI conventions in `create`/`delete`/`list-mechanics`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff UP038 + ruff-format re-wrap**

- **Found during:** Task 1 + Task 2 commit pre-commit hooks
- **Issue:** `isinstance(value, (bool, str, int, float))` triggered `UP038` (use `X | Y` union syntax). Long ruff-format re-wrapped line 107 of `test_viz_graph.py` after Task 2.
- **Fix:** Switched to `isinstance(value, bool | str | int | float)`. Accepted ruff-format's auto-wrap and re-staged.
- **Impact:** Cosmetic only; no semantic change.
- **Committed in:** `e3d2eda` (Task 1) and `d336d91` (Task 2) respectively.

**2. [Rule 3 - Blocking] mypy `no-any-return` on `_node_type`**

- **Found during:** Task 1 mypy gate
- **Issue:** `return t` inferred as `Any` because `props.get("type") or props.get("node_type")` has return type `Any | Any`.
- **Fix:** Replaced `if t in ("agent", "entity"): return t` with explicit `if t == "agent" or t == "entity": return str(t)` so mypy narrows the return to `str`.
- **Impact:** None functionally; stricter type narrowing.
- **Committed in:** `e3d2eda` (Task 1).

**3. [Rule 3 - Blocking] mypy `no-any-return` on `render_edge_label`**

- **Found during:** Task 1 mypy gate
- **Issue:** `return escape_label(str(rel))` inferred as `Any`.
- **Fix:** Bound intermediate `escaped: str = escape_label(...)` then `return escaped`.
- **Impact:** None.
- **Committed in:** `e3d2eda` (Task 1).

**Total deviations:** 3 auto-fixed (all Rule 3 blocking — lint/format/type gate noise).
**Impact on plan:** Zero functional impact.

## Issues Encountered

None beyond the three pre-commit/mypy items above.

## User Setup Required

None. No external services, environment variables, or dashboard configuration introduced.

## End-to-end Verification

- Created a throwaway universe via `XDG_DATA_HOME=/tmp/viz_smoke/data token-world create sample`.
- Populated it with `alice` (agent, hp=100), `room_a` (entity, subtype=room), `sword` (entity, subtype=weapon, damage=10), plus `located_in` and `held_by` relations.
- Ran `token-world viz-graph sample --node alice --depth 2` — got a well-formed `flowchart LR` block:

  ```
  flowchart LR
      alice["👤 alice<br/>hp=100"]:::agent
      room_a["🏛 room_a<br/>subtype=room"]:::entity
      sword["🏛 sword<br/>subtype=weapon<br/>damage=10"]:::entity
      alice -- "located_in" --> room_a
      sword -- "held_by" --> alice
      classDef agent fill:#cfe,stroke:#063,color:#000
      classDef entity fill:#fec,stroke:#630,color:#000
  ```

- Piped to `mmdc -i sample.mmd -o sample.png` — produced a valid 13.5 KB PNG (no parse errors, all 3 nodes and 2 edges rendered as expected).

## Success Criteria Check

1. Running `token-world viz-graph my-universe --node alice --depth 2` prints a valid `flowchart LR ...` block to stdout. **PASS** (verified end-to-end above).
2. Running without any anchor flag exits non-zero with a message pointing at `--node`/`--seed-query`/`--all-agents`. **PASS** (`test_requires_anchor` + exit code 2).
3. Exceeding `--max-nodes` exits non-zero with a clear "tighten the filter" message. **PASS** (`test_max_nodes_cap` + exit code 4).
4. Node IDs or labels containing `"`, `|`, `[`, `]`, or newlines are escaped; Mermaid parses the output without error. **PASS** (`test_injection_safe_node_id`, `test_mermaid_id_collision_hash_suffix`, mmdc render succeeded on labels containing escaped content).
5. A `--no-style` run omits classDefs and emoji. **PASS** (`test_no_style_emits_minimal_output` + `test_no_style_flag`).
6. Writing to `--output FILE` creates the file and exits 0. **PASS** (`test_output_file`).
7. `docs/guides/viz-graph.md` is ≥40 lines with all required sections. **PASS** (119 lines, 8/8 required headings present).

## Self-Check: PASSED

Verified artifacts exist on disk and commits are in git history:

- FOUND: `src/token_world/viz/graph_viz.py`
- FOUND: `tests/test_cli/__init__.py`, `tests/test_cli/test_viz_graph.py`
- FOUND: `docs/guides/viz-graph.md` (119 lines)
- FOUND: `src/token_world/viz/__init__.py` exports `extract_subgraph`, `to_mermaid`, `TooManyNodesError`
- FOUND: `src/token_world/cli.py` contains `@cli.command("viz-graph")`
- FOUND commit `e3d2eda` (Task 1 — feat viz.graph_viz)
- FOUND commit `d336d91` (Task 2 — feat viz-graph CLI)
- FOUND commit `51ba9bc` (Task 3 — docs guide)
- Test suite: `uv run pytest tests/ -q` -> 275 passed, 5 skipped (Wave 2+ UC/GAP stubs), 0 failed
- Quality gates: `ruff check`, `ruff format --check`, `mypy src/token_world/viz/ src/token_world/cli.py` all green

---

*Phase: 03-design-validation*
*Plan: 04*
*Completed: 2026-04-12*
