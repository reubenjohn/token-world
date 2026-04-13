---
phase: 03-design-validation
plan: 12
subsystem: use-case-library
tags: [gap-analysis, synthesis, cross-phase, handoff]

requires:
  - phase: 03-design-validation
    provides: 5 CATEGORY-SUMMARY.md files with 80 deduplicated category-scoped gaps (Wave 3, plan 11)
  - phase: 03-design-validation
    provides: 35 reviewed use cases UC-S01..S07, UC-O01..O08, UC-R01..R07, UC-V01..V07, UC-E01..E06
provides:
  - canonical .planning/GAP-ANALYSIS.md (68 gaps, four-layer organisation, three-way dispositions)
  - .planning/GAP-HANDOFF.md (49 address-now gaps grouped by Target Phase)
  - .planning/backlog/phase-03-gap-deferrals.md (16 deferred gaps)
  - phase-local GAP-ANALYSIS.md symlink for Wave-0 schema test path resolution
  - stable canonical IDs (GAP-GRAPH/MECH/ENG/CROSS<NN>) cited by downstream phases
  - schema test transition SKIPPED -> PASSED
affects: [phase-04-llm-mechanic-generation, phase-05-simulation-engine, phase-03-roadmap (three address-now graph items)]

tech-stack:
  added: []
  patterns:
    - "canonical gap IDs GAP-<LAYER><NN>: stable across phases, cited directly by downstream planners"
    - "three-way disposition vocabulary address-now | defer | out-of-scope (D-06)"
    - "layered organisation (graph-api, mechanic-protocol, engine-pipeline, cross-cutting) as the canonical reading order"
    - "shadow-alias ID GAP-X01 preserves schema regex [GMEX] coverage without introducing a spurious out-of-scope gap"
    - "deterministic handoff file emission: address-now gaps with Target Phase not-03 get a row in GAP-HANDOFF.md; defer gaps get a row in the backlog; counts reconcile with frontmatter"

key-files:
  created:
    - .planning/GAP-ANALYSIS.md
    - .planning/GAP-HANDOFF.md
    - .planning/backlog/phase-03-gap-deferrals.md
    - .planning/phases/03-design-validation/GAP-ANALYSIS.md (symlink)
  modified: []

key-decisions:
  - "Six Wave-3 cross-category overlap clusters merged into canonical gaps: observation projection (GAP-CROSS01 from S-E01+V-E05+O-E06+E-E05), graceful refusal (GAP-CROSS02 from R-E02+partial E-E10), terrain vocabulary (GAP-GRAPH07 from S-G05+V-G04), fungibility (GAP-GRAPH10 from O-G03+R-G01), passive-tick sweep (GAP-ENG07 from V-E01+R-E03), blocked movement (GAP-MECH01 from S-M01+E-M03)."
  - "76% address-now ratio declared intentional, not disposition drift: 27 of 52 address-now items are seed mechanics (Phase 4's core deliverable), so framework-surface address-now is 25/41 (61%)."
  - "GAP-X01 shadow alias in Cross-Cutting Rationale (not a separate Out-of-Scope row) — no use case surfaced a genuinely out-of-scope gap per REQUIREMENTS.md §Out of Scope."

patterns-established:
  - "Canonical gap ID numbering stable across phases — later phases cite GAP-<LAYER><NN> directly instead of re-deriving."
  - "Handoff/backlog files derive mechanically from GAP-ANALYSIS.md frontmatter counts — any future edit that breaks the reconciliation fails the quality gate."

requirements-completed: [DVAL-02]

duration: ~25min
completed: 2026-04-12
---

# Phase 3 Plan 12: Gap Analysis Synthesis Summary

**Synthesised 80 Wave-3 category-scoped gaps into 68 canonical cross-phase gaps with stable IDs, four-layer organisation, and three-way dispositions — transitioning the Wave-0 schema test from SKIPPED to PASSED and delivering Phase 3 success criterion #2 (DVAL-02).**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-12T22:00Z
- **Completed:** 2026-04-12T22:25Z
- **Tasks:** 3 (synthesis, handoff emission, quality gates)
- **Files created:** 4 (GAP-ANALYSIS.md, GAP-HANDOFF.md, deferrals backlog, phase-local symlink)

## Accomplishments

- **68 canonical cross-phase gaps** synthesised across 5 category summaries and 35 use cases.
- **Four-layer organisation:** Graph API (18), Mechanic Framework (29), Engine Pipeline (19), Cross-Cutting (2). Layer sum reconciles with frontmatter total_gaps.
- **Three-way dispositions:** 52 address-now, 16 defer, 0 out-of-scope. Disposition sum reconciles with frontmatter total_gaps.
- **Six cross-category overlap clusters resolved** (observation projection, graceful refusal, terrain vocab, fungibility, passive-tick sweep, blocked movement) — each merges 2-4 Wave-3 source IDs into a single canonical gap.
- **49 address-now gaps routed by Target Phase** in GAP-HANDOFF.md: 28 to Phase 04 (LLM Mechanic Generation, 27 seed mechanics + 1 generation-gate), 21 to Phase 05 (Simulation Engine), 0 to Phase 06/07. Phase 03 absorbs 3 additive graph-API queries.
- **16 deferred gaps** parked in `.planning/backlog/phase-03-gap-deferrals.md` — cluster on vocabulary consistency and v2 multi-agent concerns.
- **Schema test transitioned SKIPPED → PASSED.** `tests/test_design_validation/test_gap_analysis_schema.py` both tests now pass (was 2 skipped before this plan).
- **Full test suite green.** `uv run pytest tests/ -x -q` → 280 passed.
- **Zero dangling UC references.** All 35 UC IDs cited in GAP-ANALYSIS.md resolve to real files under `.planning/use-cases/**/UC-*.md`.

## Task Commits

1. **Task 1:** Synthesise canonical GAP-ANALYSIS.md — `73d838c` (feat)
2. **Task 2:** Emit GAP-HANDOFF.md and phase-03-gap-deferrals.md — `0dca29f` (feat)
3. **Task 3:** Quality gates ran green; no code changes to commit.

## Address-now Gaps with Target Phase

### Phase 03 (3 — additive R-tree query methods)

- `GAP-GRAPH01` — `ctx.spatial.segment_intersections(p1, p2, filter=...)`
- `GAP-GRAPH02` — `ctx.spatial.nearest(point, filter, k)`
- `GAP-GRAPH03` — `ctx.spatial.within(shape)` (covers AoE and earshot)

### Phase 04 (28 — seed mechanics + generation-gate)

- Seed mechanics (27): GAP-MECH01..27 (movement/LOS/find_nearest/AoE/terrain/trade/give/persuade/tell/teach/cooperative/speak/craft/consume/pickup/wear/fungible_pay/review-gate/weather/world-state/decay/illumination/contagion/belief-update/cycle-lint/try_door)
- Classifier gate: GAP-ENG16 — confidence threshold + manual-review queue on mechanic generation

### Phase 05 (21 — engine pipeline + belief-graph + cross-cutting)

- Graph primitives: GAP-GRAPH04 (beliefs), GAP-GRAPH05 (seeded RNG)
- Classifier: GAP-ENG01, 02, 04, 11, 15 (offer/accept, indirect_object, skills-as-nodes, no_such_target, no_viable_action)
- Mechanic dispatch: GAP-ENG03, 05, 09 (llm_adjudicated, intent-fusion, WorldPropertyMatcher)
- Conservation + tick: GAP-ENG06, 07 (conservation hook, passive-tick sweep)
- Chain control: GAP-ENG08, 17, 18 (cycle detector, chain_truncated trace, max_chain_depth config)
- Concurrency: GAP-ENG13, 14 (turn ordering, pre-execution conflict scan)
- Calendar: GAP-ENG10 (day-of-year → season)
- Grounding guardrail: GAP-ENG12 (hard-constraint observation template)
- Cross-cutting: GAP-CROSS01 (observation projection), GAP-CROSS02 (graceful refusal contract)

### Phase 06/07

None route here.

## Deferred Gaps (16)

See `.planning/backlog/phase-03-gap-deferrals.md`. Summary:

- **13 graph-API vocabulary/convention items** (portals, terrain, containment, position accessor, fungibility representation, reputation edges, condition properties, crafted_from provenance, container subtype, sky-exposure derivation, transform-vs-swap convention, CAS primitive, door-state convention).
- **2 mechanic enrichments** (partial consumption, making-change).
- **1 engine UX hardening item** (multi-party commit / consent / listener-reaction — GAP-ENG19).

## Decisions Made

- **Merged 6 Wave-3 cross-category overlap clusters into canonical gaps.** The merges are the single highest-leverage output of this synthesis: GAP-CROSS01 (observation projection) alone consolidates four source IDs spanning spatial, environmental, social, and edge-case categories — closing half the edge-case category's address-now load by construction.
- **GAP-X01 as shadow alias in Cross-Cutting Rationale, not a standalone Out-of-Scope row.** No surfaced use case conflicts with REQUIREMENTS.md §Out of Scope; declaring GAP-X01 as a phantom row would break frontmatter reconciliation. The plan's Task 1 Step C explicitly offered this fallback and it was chosen.
- **Address-now ratio (76%) declared intentional.** 27 of 52 address-now items are seed mechanics — Phase 4's primary deliverable, not framework-surface gaps. Excluding seed mechanics, the framework-surface address-now ratio is 25/41 (61%), which is healthy. Documented in the Summary section.
- **Target Phase mapping from D-06.** Phase 3 roadmap items (GRAPH-06/07, AUTO-04 extensions) → 03; Phase 4 scope (mechanic generation, seed mechanics, generation gates) → 04; Phase 5 scope (classifier pipeline, observation, chain control, passive tick, conservation) → 05; v2 multi-agent or hardening → defer/v2.

## Deviations from Plan

### Auto-fixed Issues

None. The plan executed exactly as written. Task 1 Step C's shadow-alias guidance was followed (GAP-X01 appears in Cross-Cutting Rationale rather than as a standalone Out-of-Scope row because no real out-of-scope gap surfaced).

The plan's sanity note on address-now ratio (>50% is a smell) was consciously evaluated; the ratio is 76% but this is legitimate because seed mechanics are Phase 4's core scope — they're work items in a work list, not framework holes. The Summary explains this transparently.

## Issues Encountered

- **Frontmatter layer-sum reconciliation vs. OOS row.** Initial draft included a standalone `GAP-X01` Out-of-Scope row, which broke `sum(layers.values()) == total_gaps` (layers covers only graph/mech/eng/cross, not an OOS section). Resolution: moved GAP-X01 to a shadow-alias reference inside `GAP-CROSS01`'s Rationale cell, set `out_of_scope: 0`, and `total_gaps: 68`. Both reconciliations now pass. This matches the plan's Task 1 Step C explicit fallback instruction.
- **Phase 5 success-criterion phrasing from RESEARCH.md.** The plan called out that "success criterion #2" of Phase 3 is "Gap analysis report identifies missing mechanics or framework capabilities, and each gap has a disposition". Verified every row in GAP-ANALYSIS.md carries exactly one disposition from `{address-now, defer, out-of-scope}` via grep regex in Task 1 verify. Passed.

## Quality Gate Evidence

```
uv run pytest tests/test_design_validation/test_gap_analysis_schema.py -v
  test_gap_analysis_exists_and_has_required_sections PASSED
  test_gap_ids_follow_scheme PASSED

uv run pytest tests/ -x -q
  280 passed in 3.92s

Frontmatter reconciliation:
  sum(dispositions.values()) = 52 + 16 + 0 = 68 == total_gaps  [OK]
  sum(layers.values())       = 18 + 29 + 19 + 2 = 68 == total_gaps  [OK]

UC cross-references:
  35 unique UC IDs in doc, 0 dangling  [OK]

Artifact existence:
  .planning/GAP-ANALYSIS.md                                          [file]
  .planning/GAP-HANDOFF.md                                           [file]
  .planning/backlog/phase-03-gap-deferrals.md                        [file]
  .planning/phases/03-design-validation/GAP-ANALYSIS.md              [symlink -> ../../GAP-ANALYSIS.md]
```

## Next Phase Readiness

- **Phase 3 success criterion #2 satisfied (DVAL-02 complete).** Gap analysis report exists with 68 gaps, each carrying a disposition from the D-06 three-way vocabulary.
- **Phase 4 planner has a single entry point.** `.planning/GAP-HANDOFF.md` §"Phase 04 (LLM Mechanic Generation)" lists 28 address-now gaps (27 seed mechanics + 1 generation gate) with their source UCs and rationales. Phase 4 plans MUST cite these GAP IDs in their frontmatter.
- **Phase 5 planner has a single entry point.** `.planning/GAP-HANDOFF.md` §"Phase 05 (Simulation Engine)" lists 21 address-now gaps covering classifier pipeline, observation projection, chain control, passive tick, conservation, and the two cross-cutting gaps.
- **Stable IDs.** `GAP-GRAPH01..18`, `GAP-MECH01..29`, `GAP-ENG01..19`, `GAP-CROSS01..02` are now frozen; later phases cite these directly without renumbering.
- **Deferred pool curated.** `.planning/backlog/phase-03-gap-deferrals.md` holds 16 items for v2 milestone planning.

## Self-Check: PASSED

- [x] `.planning/GAP-ANALYSIS.md` exists, 278 lines, all 14 required headings present (verified via `grep -qE` sequence in Task 1 verify).
- [x] `.planning/GAP-HANDOFF.md` exists with `## By Target Phase` and subsections for Phase 04/05/06/07.
- [x] `.planning/backlog/phase-03-gap-deferrals.md` exists with `## Deferred from Phase 3` heading.
- [x] `.planning/phases/03-design-validation/GAP-ANALYSIS.md` is a symlink resolving to `../../GAP-ANALYSIS.md` (verified `test -L` and `test -f`).
- [x] Frontmatter reconciliation: 52+16+0 = 18+29+19+2 = 68 = total_gaps.
- [x] Every `Source Use Cases` cell references UC IDs that resolve to real files (35 unique UCs, 0 dangling).
- [x] `tests/test_design_validation/test_gap_analysis_schema.py` PASSED (was SKIPPED).
- [x] `uv run pytest tests/ -x -q` = 280 passed.
- [x] Commits `73d838c` (Task 1) and `0dca29f` (Task 2) exist on master.

---
*Phase: 03-design-validation*
*Completed: 2026-04-12*
