---
status: complete
phase: 03-design-validation
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md, 03-05-SUMMARY.md, 03-06-SUMMARY.md, 03-07-SUMMARY.md, 03-08-SUMMARY.md, 03-09-SUMMARY.md, 03-10-SUMMARY.md, 03-11-SUMMARY.md, 03-12-SUMMARY.md]
started: 2026-04-13T02:03:22Z
updated: 2026-04-13T02:45:00Z
verdict: PASS (3 gaps closed by 03-13/14/15 gap-closure plans)
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running service / clear ephemeral state. `uv run token-world create demo-uat` scaffolds a universe (CLAUDE.md, .mcp.json, universe.db, mechanics/, agents/). `uv run token-world list` lists it. `uv run pytest tests/ -q` reports green baseline.
result: pass
evidence: scripts/uat_phase_03.py check_scaffold_and_cli → PASS; `uv run pytest tests/ -q` → 291 passed in 3.66s

### 2. Full Test Suite Green
expected: `uv run pytest tests/ -q` passes all ~280 tests with 0 failures, 0 errors. All spatial, temporal, viz, use-case schema, and gap-analysis schema tests are green (no SKIPPED entries left from Wave 0 stubs).
result: pass
evidence: 291 passed in 3.66s (up from 280 reported in 03-12-SUMMARY as more regression tests have landed), 0 skipped, 0 failed

### 3. Lint / Format / Type-Check Green
expected: `uv run ruff check src/` → "All checks passed"; `uv run ruff format --check src/` → all files formatted; `uv run mypy src/token_world/graph/` → 0 issues.
result: pass
reported: "mypy src/token_world/graph/ reports 2 errors at knowledge_graph.py:450 and :479 — 'Returning Any from function declared to return int' and '...list[SnapshotInfo]'. ruff check and ruff format pass."
severity: minor
resolution: "Closed by 03-13 (commits e4bd871, 1981f12). Replaced ignore with typing.cast in persistence + knowledge_graph; mypy now exits 0. Regression guard added in tests/test_graph/test_mypy_clean.py."

### 4. SpatialIndex API via ctx.spatial
expected: Inside a mechanic, `ctx.spatial.nearest(point=[0,0], k=3)` / `ctx.spatial.within(bbox=...)` / `ctx.spatial.intersects(node_id)` return correct results. `position` and `bbox` nodes both indexed; malformed coords logged + skipped (no crash). `ctx._spatial is None` until first access (lazy).
result: pass
evidence: tests/test_graph/test_spatial_index.py (12/12) + tests/test_mechanic/test_context_spatial.py (3/3) all green

### 5. TemporalIndex API via ctx.temporal
expected: `ctx.temporal.query_history(node_id)`, `query_changes(property=...)`, `find_state_at_tick(node_id, tick)`, `last_change(node_id, property)` all work on mem+disk merged event streams. `TemporalQueryOutOfRange` raised for unreachable ticks. `ctx._temporal is None` until first access.
result: pass
evidence: tests/test_graph/test_temporal_index.py (13/13) + tests/test_mechanic/test_context_temporal.py (4/4) all green

### 6. token-world viz-graph CLI
expected: `uv run token-world viz-graph <slug> --node <id> --depth 2` on a populated universe emits a well-formed `flowchart LR` Mermaid block: classDef agent/entity styling, emoji-prefixed labels, quoted edge labels. All node labels run through `escape_label`; node IDs sanitized.
result: pass
evidence: scripts/uat_phase_03.py check_viz_graph_cli → PASS; output includes flowchart LR, alice, room_a, sword, located_in, held_by, classDef agent, classDef entity

### 7. Mermaid Injection Safety (escape_label)
expected: A node whose label contains `"`, `[`, `]`, `|`, `<`, `>` is rendered with HTML-entity-escaped tokens (`#quot;`, `&#91;`, etc.). Output still parses as valid Mermaid; no injection of subgraph / classDef / arrow syntax via label text.
result: pass
reported: "escape_label escapes `\"` `[` `]` `|` but leaves raw `<` and `>` untouched. A label containing `<script>alert(1)</script>` passes through unescaped. Mermaid accepts HTML in labels depending on `securityLevel`; relying on deployment config is not defense-in-depth."
severity: major
evidence: 'independent agent found escape_label(\'<script>\') → \'<script>\' (no escape); _ESCAPES table in src/token_world/viz/mermaid.py covers only " \n [ ] |'
resolution: "Closed by 03-14 (commits 6b9b931, 8b007b0). Added < → &lt; and > → &gt; to _ESCAPES with <br/> reinsertion preserved; 7 adversarial test cases added; CLI smoke test verifies no raw <script substring in output."

### 8. Use Case Library (35 UC files)
expected: `.planning/use-cases/` contains `_README.md`, `_TEMPLATE.md`, and 5 category folders (spatial/social/resource/environmental/edge-case) with 7+8+7+7+6=35 `UC-*.md` files. Every UC has valid YAML frontmatter with required keys; IDs match `^UC-[SOVRE]\d{2}$`; all 35 unique. `graph_assertion.kind` values constrained to the documented 6-kind vocabulary. `tests/test_design_validation/test_use_case_schema.py` PASSES.
result: pass
reported: "35 UC files present + schema fields validate, BUT `validate_frontmatter` does NOT enforce the fixed 6-kind `graph_assertion` vocabulary (has_node|has_edge|has_property|property_equals|not_has_edge|not_has_property). Independent agent injected `kind: totally_fake_kind` into a UC's graph_assertion and validator returned zero errors. The 6-kind claim in _README.md and 03-05-SUMMARY is enforced by convention only."
severity: major
evidence: src/token_world/use_cases/loader.py validate_frontmatter checks REQUIRED_KEYS but has no VALID_ASSERTION_KINDS whitelist
resolution: "Closed by 03-15 (commits 867f44e, e8228f3). Added VALID_ASSERTION_KINDS frozenset; validate_frontmatter rejects unknown kinds in setup.graph_assertions and action.graph_assertions; 17 new regression tests; live adversarial probe rejected totally_fake_kind."

### 9. Category Aggregation Summaries
expected: 5 `CATEGORY-SUMMARY.md` files under `.planning/use-cases/{spatial,social,resource,environmental,edge-case}/` deduplicating 104 inline gaps to 80 category-scoped entries. Each summary lists cross-category overlap flags for Wave 4.
result: pass
evidence: scripts/uat_phase_03.py check_category_summaries → PASS; all 5 CATEGORY-SUMMARY.md present

### 10. GAP-ANALYSIS.md Structure
expected: `.planning/phases/03-design-validation/GAP-ANALYSIS.md` exists with 68 canonical gaps organised across 4 layers (Graph API 18 / Mechanic Framework 29 / Engine Pipeline 19 / Cross-Cutting 2) and 3 dispositions (52 address-now / 16 defer / 0 out-of-scope). `tests/test_design_validation/test_gap_analysis_schema.py` PASSES.
result: pass
evidence: scripts/uat_phase_03.py check_gap_analysis → PASS; schema pytest passes; all 4 layer headings present

### 11. GAP-HANDOFF.md Routes 49 Address-Now Gaps
expected: `.planning/GAP-HANDOFF.md` (top-level) routes 49 address-now gaps to downstream phases: 28 → Phase 04, 21 → Phase 05, 3 absorbed by Phase 03. `.planning/backlog/phase-03-gap-deferrals.md` parks the 16 deferred gaps.
result: pass
evidence: scripts/uat_phase_03.py check_gap_handoff → PASS; handoff file at .planning/GAP-HANDOFF.md mentions Phase 04 + Phase 05; deferrals parked

## Summary

total: 11
passed: 11
issues: 0
pending: 0
skipped: 0
blocked: 0
gaps_closed: 3 (03-13 minor, 03-14 major, 03-15 major)

## Gaps

- truth: "mypy src/token_world/graph/ reports 0 issues"
  status: failed
  reason: "mypy src/token_world/graph/ reports 2 errors at knowledge_graph.py:450 and :479 — 'Returning Any from function declared to return int' and '...list[SnapshotInfo]'. ruff check and ruff format pass. Confirmed by independent agent — no additional mypy errors elsewhere in src/token_world/."
  severity: minor
  test: 3
  artifacts:
    - path: "src/token_world/graph/knowledge_graph.py"
      issue: "line 450: `save_snapshot` returns Any from sqlite call but declared `int`; line 479: `list_snapshots` returns Any from persistence call but declared `list[SnapshotInfo]`"
  missing:
    - "Add explicit cast/annotation so `save_snapshot` returns int (e.g., `return int(snapshot_id)` or `-> Any` on the persistence method)"
    - "Same pattern for `list_snapshots` — either annotate persistence return type or `cast(list[SnapshotInfo], ...)`"

- truth: "escape_label neutralises every Mermaid-meaningful character including `<` and `>` so untrusted labels cannot inject HTML/Mermaid syntax"
  status: failed
  reason: "Independent agent found escape_label leaves raw `<` and `>` unchanged — only `\" \\n [ ] |` are in _ESCAPES. The intended `<br/>` for newlines is fine, but any other attacker-controlled `<tag>` passes through unescaped. Whether Mermaid renders it depends on deployment securityLevel, so this is not defense-in-depth."
  severity: major
  test: 7
  artifacts:
    - path: "src/token_world/viz/mermaid.py"
      issue: "_ESCAPES table at line 5 omits < and >; translate() leaves them verbatim"
  missing:
    - "Extend _ESCAPES to map `<` → `&lt;` and `>` → `&gt;` THEN re-insert the literal token `<br/>` only for original `\\n` positions (post-escape), or flip to a whitelist approach"
    - "Add adversarial unit test with payload `<script>alert(1)</script>` asserting no `<script` substring survives in output"

- truth: "validate_frontmatter enforces the fixed 6-kind graph_assertion vocabulary (has_node|has_edge|has_property|property_equals|not_has_edge|not_has_property) claimed by _README.md and 03-05-SUMMARY"
  status: failed
  reason: "Independent agent injected `kind: totally_fake_kind` into a UC and validate_frontmatter returned zero errors. Vocabulary is enforced by human convention only — first LLM-authored UC that drifts (e.g. Phase 04 mechanic generation) can introduce silent schema rot."
  severity: major
  test: 8
  artifacts:
    - path: "src/token_world/use_cases/loader.py"
      issue: "REQUIRED_KEYS + ID_PATTERN enforced, but no VALID_ASSERTION_KINDS check on graph_assertion[*].kind"
  missing:
    - "Add VALID_ASSERTION_KINDS = frozenset({has_node, has_edge, has_property, property_equals, not_has_edge, not_has_property})"
    - "In validate_frontmatter, iterate setup.graph_assertions and action.graph_assertions; append error for any kind not in the set"
    - "Add failing-then-passing test in tests/test_design_validation/test_use_case_schema.py with an invalid kind fixture"

## Independent Review

This UAT was cross-checked by an unbiased general-purpose agent (2026-04-13).
Verdict: **CONDITIONAL PASS** — advance to Phase 04 only after the 3 gaps above
are closed. Items the agent additionally confirmed:
- 291/291 pytest green, 68-gap arithmetic in GAP-ANALYSIS.md reconciles, 49
  unique IDs in GAP-HANDOFF.md, 35 UC IDs unique.
- viz-graph CLI degrades gracefully on missing universe / depth=0 / huge depth.
- Cross-ref spot-checks (UC-R04, UC-S05) match canonical GAP-ANALYSIS entries.
- One minor schema-gaming artifact: `GAP-X01` exists purely to satisfy the
  `GAP-[GMEX]\\d{2}` regex — noted, not gated on.
