---
phase: 03-design-validation
plan: 06
subsystem: design-validation/use-cases
tags: [use-cases, authoring, spatial]
requires:
  - .planning/use-cases/_TEMPLATE.md
  - .planning/use-cases/_README.md
  - .planning/use-cases/spatial/MANIFEST.md
  - src/token_world/use_cases/loader.py
provides:
  - .planning/use-cases/spatial/UC-S01-movement-through-doorway.md
  - .planning/use-cases/spatial/UC-S02-line-of-sight-occlusion.md
  - .planning/use-cases/spatial/UC-S03-nearest-object-query.md
  - .planning/use-cases/spatial/UC-S04-area-of-effect.md
  - .planning/use-cases/spatial/UC-S05-containment-hierarchy.md
  - .planning/use-cases/spatial/UC-S06-traversal-across-terrain.md
  - .planning/use-cases/spatial/UC-S07-position-updating-on-move.md
affects:
  - phase 03 wave 3 category aggregation (spatial category ready for review)
  - phase 03 wave 4 gap-analysis synthesis (10 inline gaps surfaced)
tech_stack:
  added: []
  patterns:
    - "Use-case frontmatter: setup.graph_builder (Python str exec'd against KG) + actions[] + expected_observations[] + gaps[]"
    - "Gap layer/severity taxonomy: {graph|mechanic|engine} x {address-now|defer|out-of-scope}"
key_files:
  created:
    - .planning/use-cases/spatial/UC-S01-movement-through-doorway.md
    - .planning/use-cases/spatial/UC-S02-line-of-sight-occlusion.md
    - .planning/use-cases/spatial/UC-S03-nearest-object-query.md
    - .planning/use-cases/spatial/UC-S04-area-of-effect.md
    - .planning/use-cases/spatial/UC-S05-containment-hierarchy.md
    - .planning/use-cases/spatial/UC-S06-traversal-across-terrain.md
    - .planning/use-cases/spatial/UC-S07-position-updating-on-move.md
  modified: []
decisions:
  - "Inline gap severities: 10 address-now gaps across all 7 UCs (plan required >=3) — spatial is the most gap-rich category and this pushes those gaps to the Wave 4 synthesis backlog early."
  - "graph_builder strings use the public KnowledgeGraph API only (add_node/add_edge/set), per CLAUDE.md mutation-mediated-access constraint, so they replay cleanly in the Wave 3 review harness and the Phase 6 regression."
  - "Every action's target also appears literally in its file's graph_builder string, enabling a cheap static check (grep) ahead of the strict runtime check in Wave 3."
metrics:
  duration_min: 12
  tasks_completed: 1
  files_created: 7
  files_modified: 0
  completed_at: 2026-04-12
---

# Phase 3 Plan 06: Authoring Spatial Use Cases Summary

Authored the 7 spatial use case files pre-assigned in `spatial/MANIFEST.md`,
surfacing 10 `address-now` gaps across graph, mechanic, and engine layers for
the Wave 4 synthesis backlog.

## Deliverables

| UC ID  | File                                                                         | Title                        | Gap count (address-now / defer) |
|--------|------------------------------------------------------------------------------|------------------------------|---------------------------------|
| UC-S01 | `.planning/use-cases/spatial/UC-S01-movement-through-doorway.md`             | Movement through a doorway   | 1 / 1                           |
| UC-S02 | `.planning/use-cases/spatial/UC-S02-line-of-sight-occlusion.md`              | Line-of-sight occlusion      | 2 / 0                           |
| UC-S03 | `.planning/use-cases/spatial/UC-S03-nearest-object-query.md`                 | Nearest object query         | 2 / 0                           |
| UC-S04 | `.planning/use-cases/spatial/UC-S04-area-of-effect.md`                       | Area-of-effect explosion     | 2 / 1                           |
| UC-S05 | `.planning/use-cases/spatial/UC-S05-containment-hierarchy.md`                | Containment hierarchy        | 1 / 1                           |
| UC-S06 | `.planning/use-cases/spatial/UC-S06-traversal-across-terrain.md`             | Traversal across terrain     | 1 / 2                           |
| UC-S07 | `.planning/use-cases/spatial/UC-S07-position-updating-on-move.md`            | Position updating on move    | 1 / 1                           |

## Gaps Surfaced

One-line summaries of every inline gap, for the Wave 4 aggregator.

### UC-S01 Movement through a doorway
- **mechanic / address-now** — Movement seed can't traverse a chained `connects → connects` path through a doorway entity.
- **graph / defer** — No canonical 'passage' vocabulary; doorways are ad-hoc `subtype="doorway"` entities.

### UC-S02 Line-of-sight occlusion
- **mechanic / address-now** — No LOS mechanic; observation seed would silently over-share bob's position.
- **graph / address-now** — No `segment_intersections(p1, p2, filter=occludes)` on the GRAPH-06 spatial index.

### UC-S03 Nearest object query
- **graph / address-now** — No filtered `ctx.spatial.nearest(point, filter=…, k=1)` on the spatial index.
- **mechanic / address-now** — No `find_nearest` verb/mechanic; seed observation only describes direct neighbors.

### UC-S04 Area-of-effect explosion
- **graph / address-now** — No `ctx.spatial.within(shape)` query (bbox or circle) on GRAPH-06.
- **mechanic / address-now** — No AoE mechanic; single-action/multi-mutation fan-out pattern not exercised by seeds.
- **engine / defer** — Fan-out mutations not transactional; partial failure is silent.

### UC-S05 Containment hierarchy
- **engine / address-now** — Observation pipeline cannot walk `inside → located_in` chains (anticipates SIM-07).
- **graph / defer** — No unified containment-relation convention across `inside` vs `located_in`.

### UC-S06 Traversal across terrain
- **mechanic / address-now** — Movement seed is terrain-agnostic; can't distinguish bridge (legal) from river (illegal).
- **graph / defer** — No canonical terrain-typing system; `traversable` is an ad-hoc bool.
- **mechanic / defer** — No hook for state-dependent passability (damaged/flooded/locked bridges).

### UC-S07 Position updating on move
- **mechanic / address-now** — Movement seed updates `location` but leaves continuous `position` stale, silently poisoning later spatial queries.
- **graph / defer** — No `kg.centroid_of(node_id)` helper / documented room-centroid convention.

**Totals:** 10 `address-now` gaps, 7 `defer` gaps, 0 `out-of-scope`. Plan threshold (`>=3` address-now) cleared 3× over; every file contributes at least one address-now gap.

## Deviations from Plan

None — plan executed exactly as written.

All per-file specifics in the plan's task description were followed, with enrichment where useful (e.g., an extra `defer` gap per case to document known-but-not-blocking concerns for Wave 4).

## Verification

- `load_use_case` + `validate_frontmatter` ran clean on all 7 files (0 errors).
- Each file's `setup.graph_builder` string was executed against a live `KnowledgeGraph` (in-memory temp DB) — all 7 built successfully (3–7 nodes each).
- `## Vignette` and `## Why this matters` present in every file.
- Every `actions[].actor` and `actions[].classified.target` string appears literally in the same file's `graph_builder`.
- All files ≥ 78 lines (plan required ≥ 40).
- `uv run pytest tests/test_design_validation/test_use_case_schema.py::test_each_use_case_has_valid_frontmatter` — PASSED.
- `uv run pytest tests/test_design_validation/test_use_case_schema.py::test_use_case_ids_are_unique` — PASSED.
- `test_library_has_use_cases` — expected fail (asserts ≥30 files; only 7 exist yet because plans 03-07..03-10 run in parallel in the same wave). Will pass once the wave completes.

## Commits

- `8041990` — docs(03-06): author 7 spatial use cases UC-S01..UC-S07

## Self-Check: PASSED

- `.planning/use-cases/spatial/UC-S01-movement-through-doorway.md` — FOUND
- `.planning/use-cases/spatial/UC-S02-line-of-sight-occlusion.md` — FOUND
- `.planning/use-cases/spatial/UC-S03-nearest-object-query.md` — FOUND
- `.planning/use-cases/spatial/UC-S04-area-of-effect.md` — FOUND
- `.planning/use-cases/spatial/UC-S05-containment-hierarchy.md` — FOUND
- `.planning/use-cases/spatial/UC-S06-traversal-across-terrain.md` — FOUND
- `.planning/use-cases/spatial/UC-S07-position-updating-on-move.md` — FOUND
- Commit `8041990` — FOUND in `git log`
