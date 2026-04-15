---
phase: 03-design-validation
plan: 05
subsystem: use-case-library
tags: [use-cases, manifests, scaffolding, wave-1, phase-3]

# Dependency graph
requires:
  - phase: 03-design-validation
    plan: 01
    provides: validate_frontmatter + REQUIRED_KEYS + VALID_LAYERS/SEVERITIES — every key documented in _README.md mirrors the validator
provides:
  - .planning/use-cases/_README.md — format spec, ID scheme, gap taxonomy, assertion vocabulary (Wave 2 authors' one-stop doc)
  - .planning/use-cases/_TEMPLATE.md — copy-pastable skeleton with every required key and all six graph_assertion kinds
  - 5 per-category MANIFEST.md files pre-assigning 35 stable UC IDs + slugs + target file paths
  - Wave 2 authoring contract — each of 35 planned UCs has exactly one owning file path; parallel-safe by construction
affects:
  - 03-06-authoring-spatial
  - 03-07-authoring-social
  - 03-08-authoring-resource
  - 03-09-authoring-environmental
  - 03-10-authoring-edge-case
  - 03-11-category-aggregation
  - 03-12-gap-analysis-synthesis

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pre-assigned stable IDs in MANIFEST.md per category — authors claim rows, never invent IDs"
    - "Wave 2 authoring checklist as markdown task list inside each manifest — grep-able, diff-able"

key-files:
  created:
    - .planning/use-cases/_README.md
    - .planning/use-cases/_TEMPLATE.md
    - .planning/use-cases/spatial/MANIFEST.md
    - .planning/use-cases/social/MANIFEST.md
    - .planning/use-cases/resource/MANIFEST.md
    - .planning/use-cases/environmental/MANIFEST.md
    - .planning/use-cases/edge-case/MANIFEST.md
  modified: []

key-decisions:
  - "UC-S07 and UC-V01 flagged no (seed mechanic nominally covers) — all other 33 UCs surface gaps, matching D-03 expectation"
  - "UC-O08 (speech-broadcast) explicitly cross-cuts spatial + social — first composition-tax example Wave 4 will aggregate"
  - "Resource category includes UC-R07 conservation-violation-attempt — engine-layer gap, not mechanic-layer, to seed Phase 4 mechanic-review discussions"

requirements-completed: [DVAL-01]

# Metrics
duration: ~6min
completed: 2026-04-12
---

# Phase 3 Plan 05: Use-case Manifests Summary

**Use-case library skeleton shipped — README, template, and 5 category manifests pre-assign 35 stable UC IDs with no-seed-mechanic flags; Wave 2 can now fan out with zero collisions.**

## Performance

- **Duration:** ~6 min
- **Completed:** 2026-04-12T21:22:16Z
- **Tasks:** 2
- **Files created:** 7 (2 library-wide + 5 per-category manifests)

## Accomplishments

- `.planning/use-cases/_README.md` (179 lines, 8 `## ` sections) — documents the authoring workflow, ID scheme, all 8 required frontmatter keys, gap taxonomy, both structured formats, the fixed 6-kind graph_assertion vocabulary, status lifecycle, and trust model
- `.planning/use-cases/_TEMPLATE.md` (69 lines) — valid YAML frontmatter parses via `yaml.safe_load`, contains one example of each of the six `graph_assertion` kinds, plus the three narrative sections
- 5 MANIFEST.md files, one per category, totaling 139 lines
- All 35 UC IDs unique and matching `^UC-[SOVRE]\d{2}$`: 7 spatial (S) + 8 social (O) + 7 resource (R) + 7 environmental (V) + 6 edge-case (E)
- At least one `YES` (no-seed-mechanic) flag per category satisfies D-03
- Each manifest ends with an explicit Wave 2 authoring checklist — target file paths are pre-decided, so the 35 parallel Wave 2 tasks cannot collide on writes
- Test suite unchanged: `tests/test_design_validation/test_use_case_schema.py` all 3 tests SKIPPED (waiting for `UC-*.md` files — expected until Wave 2)

## Task Commits

1. **Task 1: Write _README.md and _TEMPLATE.md** — `a445efe` (docs)
2. **Task 2: Write 5 category MANIFEST.md files (35 UC IDs)** — `042434a` (docs)

## Files Created

- `.planning/use-cases/_README.md` — library-wide format spec and authoring guide
- `.planning/use-cases/_TEMPLATE.md` — copy-pastable skeleton used by Wave 2 authors
- `.planning/use-cases/spatial/MANIFEST.md` — UC-S01..UC-S07 (7 cases)
- `.planning/use-cases/social/MANIFEST.md` — UC-O01..UC-O08 (8 cases)
- `.planning/use-cases/resource/MANIFEST.md` — UC-R01..UC-R07 (7 cases)
- `.planning/use-cases/environmental/MANIFEST.md` — UC-V01..UC-V07 (7 cases)
- `.planning/use-cases/edge-case/MANIFEST.md` — UC-E01..UC-E06 (6 cases)

## UC Inventory (35 pre-assigned)

### Spatial (7)

| ID | Slug | No-seed? |
|----|------|----------|
| UC-S01 | movement-through-doorway | no |
| UC-S02 | line-of-sight-occlusion | YES |
| UC-S03 | nearest-object-query | YES |
| UC-S04 | area-of-effect | YES |
| UC-S05 | containment-hierarchy | YES |
| UC-S06 | traversal-across-terrain | YES |
| UC-S07 | position-updating-on-move | no |

### Social (8)

| ID | Slug | No-seed? |
|----|------|----------|
| UC-O01 | trade-negotiation | YES |
| UC-O02 | persuasion-check | YES |
| UC-O03 | give-sword-to-bob | YES |
| UC-O04 | deception | YES |
| UC-O05 | teaching | YES |
| UC-O06 | cooperation-lift-heavy | YES |
| UC-O07 | observation-of-agent | no |
| UC-O08 | speech-broadcast | YES |

### Resource (7)

| ID | Slug | No-seed? |
|----|------|----------|
| UC-R01 | craft-sword-from-materials | YES |
| UC-R02 | consume-food | YES |
| UC-R03 | gift-currency | YES |
| UC-R04 | inventory-limit | YES |
| UC-R05 | degradation-over-time | YES |
| UC-R06 | fungible-currency | YES |
| UC-R07 | conservation-violation-attempt | YES |

### Environmental (7)

| ID | Slug | No-seed? |
|----|------|----------|
| UC-V01 | fire-spread | no |
| UC-V02 | weather-change | YES |
| UC-V03 | decay | YES |
| UC-V04 | seasons | YES |
| UC-V05 | terrain-effect | YES |
| UC-V06 | light-and-dark | YES |
| UC-V07 | contagion | YES |

### Edge-case (6)

| ID | Slug | No-seed? |
|----|------|----------|
| UC-E01 | action-against-nonexistent-target | YES |
| UC-E02 | concurrent-actors | YES |
| UC-E03 | partial-knowledge | YES |
| UC-E04 | nonsense-input | YES |
| UC-E05 | circular-chain | YES |
| UC-E06 | move-into-locked-room | YES |

### No-seed-mechanic hotlist (Wave 2 priority for gap discovery)

Of the 35 cases, **32 are flagged `YES` (no seed mechanic covers)**. Only three are `no`:

- **UC-S01** movement-through-doorway — movement seed handles basic edges; may still surface a gap around `connects`-property traversal
- **UC-S07** position-updating-on-move — movement seed updates `located_in`; centroid recompute may still be missing
- **UC-V01** fire-spread — environmental_reaction seed covers basic adjacency; chain-depth behavior may still surface a gap
- **UC-O07** observation-of-agent — observation seed partial; "what counts as visible" is the gap angle

These four are the most likely to produce narrow, concrete gaps (seed present but insufficient); the other 32 will produce broader "mechanic entirely missing" gaps that feed Phase 4 planning directly.

## Decisions Made

- **Stable IDs pre-assigned in manifests, not authored ad-hoc.** Keeps 35 parallel Wave 2 tasks collision-free and makes cross-referencing in GAP-ANALYSIS.md stable from day one.
- **Explicit target file paths in each manifest's Wave 2 checklist.** Authors copy the path, never invent one. Makes the Wave 2 plans trivially verifiable by `test -f <path>`.
- **At least one no-seed-mechanic flag per category.** D-03 demands gap surfacing; the YES column makes the flag scannable at a glance.
- **Template uses placeholder `id: UC-XX00`.** The validator's regex would reject `XX00`, but the template is never loaded by tests — only `UC-[SOVRE]NN` files matched by the glob. Keeping the placeholder prevents accidental duplicate IDs.

## Deviations from Plan

None — plan executed exactly as written. Both tasks completed, all acceptance criteria satisfied, no Rule 1–4 fixes required.

## Issues Encountered

None.

## User Setup Required

None — no external services, env vars, or dashboard configuration introduced by this plan.

## Next Phase Readiness

**Wave 2 plans unblocked** (all 5 can start in parallel):

- `03-06 authoring-spatial` — reads `.planning/use-cases/spatial/MANIFEST.md`, authors 7 UC files
- `03-07 authoring-social` — reads social manifest, authors 8 UC files
- `03-08 authoring-resource` — reads resource manifest, authors 7 UC files
- `03-09 authoring-environmental` — reads environmental manifest, authors 7 UC files
- `03-10 authoring-edge-case` — reads edge-case manifest, authors 6 UC files

Every Wave 2 author has: (1) a stable UC ID pre-assigned, (2) a slug and exact target file path, (3) a one-line scenario, (4) the `_TEMPLATE.md` to copy, (5) the `_README.md` spec, (6) the no-seed-mechanic flag indicating whether to dig for gaps. No shared state between Wave 2 tasks other than the template — parallel writes are safe.

**Wave 3 aggregation (`03-11-category-aggregation`)** waits on Wave 2 completion; will read the manifests to ensure every row produced exactly one file.

**Wave 4 synthesis (`03-12-gap-analysis-synthesis`)** waits on Wave 3; will read all 35 authored `gaps[]` entries plus the per-category summaries.

**No blockers.**

## Self-Check: PASSED

Verified artifacts exist on disk and commits are in git history:

- FOUND: `.planning/use-cases/_README.md` (179 lines, 8 `## ` sections)
- FOUND: `.planning/use-cases/_TEMPLATE.md` (69 lines, YAML parses)
- FOUND: `.planning/use-cases/spatial/MANIFEST.md` (7 UC-S ids)
- FOUND: `.planning/use-cases/social/MANIFEST.md` (8 UC-O ids)
- FOUND: `.planning/use-cases/resource/MANIFEST.md` (7 UC-R ids)
- FOUND: `.planning/use-cases/environmental/MANIFEST.md` (7 UC-V ids)
- FOUND: `.planning/use-cases/edge-case/MANIFEST.md` (6 UC-E ids)
- FOUND commit `a445efe` (Task 1 — docs)
- FOUND commit `042434a` (Task 2 — docs)
- 35 unique UC IDs confirmed across all manifests
- At least one YES per category confirmed (D-03)
- `tests/test_design_validation/` → 5 skipped, 0 failed (UC files pending Wave 2)

---

*Phase: 03-design-validation*
*Plan: 05*
*Completed: 2026-04-12*
