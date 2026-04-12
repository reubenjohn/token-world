---
phase: 03
slug: design-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Populated from RESEARCH.md §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing project framework) |
| **Config file** | `pyproject.toml` (existing `[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest -v` |
| **Estimated runtime** | ~30 seconds (full suite, grows with phase 3 tests) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Task IDs are populated by the planner. This table is the contract — every task the planner produces must appear here with either an automated command or a Wave 0 dependency. The planner fills rows during step 8; the plan-checker enforces completeness.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {pending — planner fills} | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 establishes the test scaffolding that later waves write against. The planner MUST include Wave 0 tasks that deliver:

- [ ] `tests/test_design_validation/conftest.py` — shared fixtures for use-case loading and gap-analysis parsing
- [ ] `tests/test_design_validation/test_use_case_schema.py` — schema/shape validator for use-case YAML frontmatter (DVAL-01)
- [ ] `tests/test_design_validation/test_gap_analysis_schema.py` — schema validator for GAP-ANALYSIS.md layer sections + disposition table (DVAL-02)
- [ ] `tests/test_graph/test_spatial_index.py` — stubs for GRAPH-06 (query_nearby, query_bbox, invalidation, lazy construction cost)
- [ ] `tests/test_graph/test_temporal_index.py` — stubs for GRAPH-07 (query_history, query_changes, find_state_at_tick)
- [ ] `tests/test_viz/test_viz_graph.py` — stubs for AUTO-04 (ego-graph extraction, filtered Mermaid output, 150-node cap, anchor required)
- [ ] `tests/test_viz/conftest.py` — small GraphBuilder-based fixtures for viz tests
- [ ] `src/token_world/viz/__init__.py` — package init (enables imports from test stubs)

*No new framework install required — pytest already configured in pyproject.toml.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Narrative vignette quality (readable English, captures intent) | DVAL-01 | Subjective prose quality is not automatable | Spot-read ≥1 vignette per category during review; confirm it makes sense without reading the structured frontmatter |
| Mermaid visual readability at 50/100/150 nodes | AUTO-04 | Layout readability is visual, not structural | Render via mcp-mermaid at three sizes; confirm nodes/labels legible; file in `docs/design/viz-samples/` |
| Gap analysis completeness (found gaps are real) | DVAL-02 | Whether a gap is "real" requires architectural judgment | Human (or top-level Claude) reviews GAP-ANALYSIS.md against CONTEXT.md decisions and marks each gap as valid/invalid |

*All other phase behaviors must have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (spatial, temporal, viz, use-case schema, gap-analysis schema)
- [ ] No watch-mode flags (`--watch`, `pytest-watch`, etc. forbidden)
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter once planner populates Per-Task Verification Map

**Approval:** pending
