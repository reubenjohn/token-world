---
phase: 03-design-validation
plan: 10
subsystem: use-case-library
tags:
  - use-cases
  - authoring
  - edge-case
  - robustness
dependency-graph:
  requires:
    - 03-05-use-case-manifests (MANIFEST rows, template, loader)
  provides:
    - 6 edge-case UC files validating against use_cases/loader.py
    - 22 gap entries (15 address-now, 5 defer, 1 out-of-scope, 1 defer at mechanic layer for E02)
  affects:
    - wave-3 edge-case aggregation (plan 16 or equivalent)
    - wave-4 gap-analysis synthesis (all three layers touched)
tech-stack:
  added: []
  patterns:
    - authoring trust model (committed repo code executed by Phase 6)
    - graph_assertion fixed vocabulary (has_node, has_edge, not_has_edge,
      has_property, property_equals, not_has_property)
    - gap taxonomy (layer × severity × layer-specific proposed_fix)
key-files:
  created:
    - .planning/use-cases/edge-case/UC-E01-action-against-nonexistent-target.md
    - .planning/use-cases/edge-case/UC-E02-concurrent-actors.md
    - .planning/use-cases/edge-case/UC-E03-partial-knowledge.md
    - .planning/use-cases/edge-case/UC-E04-nonsense-input.md
    - .planning/use-cases/edge-case/UC-E05-circular-chain.md
    - .planning/use-cases/edge-case/UC-E06-move-into-locked-room.md
  modified: []
decisions:
  - UC-E01 expresses the missing-target scenario by simply omitting the
    target from the graph; no validator_exception key is needed because
    the schema loader does not assert target-in-setup.
  - UC-E05's engine-layer gaps are framed around observability,
    configurability, and authoring ergonomics rather than the existence
    of cycle detection, because `ChainEngine._evaluate_chain` already
    implements a seen-set plus max_depth=10 bound.
  - UC-E06 models the door as an entity node threaded into a `connects`
    path (rather than a property on a room-to-room edge) and files the
    alternate representation as a defer-level graph gap to be settled in
    graph-conventions docs.
metrics:
  duration: ~15 minutes
  completed: 2026-04-12
  tasks: 1
  files: 6
---

# Phase 03 Plan 10: Edge-Case Use Case Authoring Summary

Authored the 6 edge-case use cases (UC-E01..UC-E06) assigned by the
edge-case MANIFEST, each surfacing at least one address-now framework
robustness gap and all six passing `validate_frontmatter`.

## What Was Built

Six markdown files under `.planning/use-cases/edge-case/`, each with the
full frontmatter schema (id, category, title, status, setup with
graph_builder, actions, expected_observations, gaps) plus a Vignette,
Why-this-matters, and Related-use-cases body. All files ≥ 40 lines.

## Use Cases and Gaps Exposed

| UC     | Title                              | Address-now gaps (layer)                     | Other gaps                               |
|--------|------------------------------------|----------------------------------------------|-------------------------------------------|
| UC-E01 | Action against nonexistent target  | engine × 2 (target resolution, observation grounding) | mechanic (defer)                          |
| UC-E02 | Concurrent actors                  | engine × 2 (turn-ordering, conflict-detection) | mechanic (defer), graph (defer)           |
| UC-E03 | Partial knowledge                  | graph × 1, mechanic × 1, engine × 1          | engine (defer, multi-agent propagation)   |
| UC-E04 | Nonsense input                     | engine × 3 (classifier verdict, mechanic-gen gate, observation template) | mechanic (out-of-scope)                   |
| UC-E05 | Circular mechanic chain            | engine × 2 (truncation observability, configurable depth), mechanic × 1 (authoring guidance) | engine (defer, cycle-key extension)       |
| UC-E06 | Move into locked room              | mechanic × 2 (movement blocking, try_door seed) | graph (defer), engine (defer, blocked-by template) |

Totals: 15 address-now, 5 defer, 1 out-of-scope, plus the deferred entries
listed above. Every file contains at least one address-now entry.

## Key Traceability Assertions Satisfied

- UC-E01: `setup.graph_builder` contains no `dragon` node; the
  `classified.target` is `dragon` with no corresponding setup node.
- UC-E05: vignette and gap summaries explicitly mention `cycle` and
  `chain depth`; two address-now engine gaps plus one address-now
  mechanic gap are specifically about cycle detection / depth bounds.
- All 6 files parse with `token_world.use_cases.load_use_case` and clear
  `validate_frontmatter` without errors.

## Verification

- `uv run python3 -c "…validate all 6…"` → `OK: all 6 edge-case UCs
  pass all checks.`
- `uv run pytest tests/test_design_validation/test_use_case_schema.py
  -v` → `test_each_use_case_has_valid_frontmatter PASSED`,
  `test_use_case_ids_are_unique PASSED`. The third test
  (`test_library_has_use_cases`, requires ≥30 UCs) fails as expected
  because only this wave-2 plan's 6 files exist; it will turn green
  once the other wave-2 plans land.

## Deviations from Plan

None. Plan executed exactly as written. The plan's `<interfaces>` note
offered two approaches for UC-E01 (either `validator_exception` key or
null target); I chose the cleaner third option the plan also implied:
leave the `classified.target` as the string `"dragon"` (so the engine
still sees the classifier's attempted target) and simply omit the node
from the setup graph. No schema exception is needed because the
validator does not enforce target-in-setup.

## Commits

- `6b66ebd` docs(03-10): author 6 edge-case use cases (UC-E01..UC-E06)

## Self-Check: PASSED

Created files verified on disk:

- FOUND: .planning/use-cases/edge-case/UC-E01-action-against-nonexistent-target.md
- FOUND: .planning/use-cases/edge-case/UC-E02-concurrent-actors.md
- FOUND: .planning/use-cases/edge-case/UC-E03-partial-knowledge.md
- FOUND: .planning/use-cases/edge-case/UC-E04-nonsense-input.md
- FOUND: .planning/use-cases/edge-case/UC-E05-circular-chain.md
- FOUND: .planning/use-cases/edge-case/UC-E06-move-into-locked-room.md

Commit verified:

- FOUND: 6b66ebd
