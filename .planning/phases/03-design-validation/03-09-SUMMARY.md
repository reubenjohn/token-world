---
phase: 03-design-validation
plan: 09
subsystem: use-cases/environmental
tags: [use-cases, authoring, environmental, chain-execution, passive-time]
requires:
  - .planning/use-cases/environmental/MANIFEST.md (UC-V01..UC-V07 pre-assigned)
  - .planning/use-cases/_TEMPLATE.md
  - .planning/use-cases/_README.md
  - src/token_world/use_cases/loader.py
provides:
  - 7 environmental use cases (UC-V01..UC-V07) validating chain-execution and passive-time scenarios
  - 11 address-now gaps surfaced across mechanic, engine, and graph layers
  - SIM-09 traceability link from UC-V03 decay to Phase 7 passive-tick work
affects:
  - Phase 3 Wave 4 gap synthesis input (11 address-now gaps feed the backlog)
  - Phase 6 regression spec (each UC becomes an integration test)
  - Phase 7 SIM-09 passive-tick requirement (UC-V03 explicit traceability)
tech-stack:
  added: []
  patterns:
    - world-level properties modelled on a single "world" node (UC-V02, UC-V03, UC-V04)
    - multi-step action/observation sequences (UC-V06: look → pick_up → look)
    - "engine" as a synthetic actor for passive/world-driven ticks (UC-V01..V04)
key-files:
  created:
    - .planning/use-cases/environmental/UC-V01-fire-spread.md
    - .planning/use-cases/environmental/UC-V02-weather-change.md
    - .planning/use-cases/environmental/UC-V03-decay.md
    - .planning/use-cases/environmental/UC-V04-seasons.md
    - .planning/use-cases/environmental/UC-V05-terrain-effect.md
    - .planning/use-cases/environmental/UC-V06-light-and-dark.md
    - .planning/use-cases/environmental/UC-V07-contagion.md
  modified: []
decisions:
  - "Modelled world-level state (weather, season, current_tick) on a dedicated 'world' node rather than as engine-internal globals — keeps the 'graph is ground truth' invariant."
  - "Used 'engine' as the synthetic actor for passive-time and world-driven transitions; this exposes the gap around passive-tick matchers rather than papering over it."
  - "Apple rot (UC-V03) modelled as in-place property flip (rotten=true) not node-swap (apple→rotten_apple); recorded as an open convention decision in the gap list."
  - "UC-V06 uses a three-action sequence (look/pick_up/look) to demonstrate observation-filter behavior — the template supports multi-step scenarios without further changes."
metrics:
  duration: "single-session authoring"
  completed: 2026-04-12
  tasks: 1
  files_created: 7
  total_lines: 655
---

# Phase 3 Plan 9: Environmental Use Case Authoring Summary

## One-liner

Authored 7 environmental use cases (UC-V01..UC-V07) covering fire spread, weather, decay, seasons, terrain, light/dark, and contagion — surfacing 11 address-now gaps across mechanic, engine, and graph layers with explicit SIM-09 traceability for passive-time work.

## What was built

Seven markdown files under `.planning/use-cases/environmental/`, each combining a YAML frontmatter (setup.graph_builder, actions, expected_observations, gaps) with a narrative body (Vignette + Why-this-matters + Related use cases). Every file validates against `token_world.use_cases.validate_frontmatter` and carries at least one classified action with paired graph-assertion observations.

## Per-UC gap summary

| UC      | Title            | Scenario (one-line)                                       | Key gaps surfaced                                                                                               |
|---------|------------------|-----------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| UC-V01  | Fire spread      | Torch ignites adjacent wooden table via env-reaction seed | engine (address-now): cascade cycle-detection / chain-depth cap                                                 |
| UC-V02  | Weather change   | Rain extinguishes outdoor fires, wets fabric              | engine (address-now): WorldPropertyMatcher missing; mechanic (address-now): no weather_reaction mechanic         |
| UC-V03  | Decay            | Apple rots after 100 passive ticks (no agent action)      | mechanic (address-now): passive-tick matcher — cites **SIM-09** for Phase 7; engine (address-now): tick-sweep    |
| UC-V04  | Seasons          | Summer→autumn transition, oak drops leaves                | engine (address-now): calendar/time-scale modelling not formalised                                               |
| UC-V05  | Terrain effect   | Swamp costs 2× movement                                   | mechanic (address-now): movement seed ignores movement_cost_multiplier                                           |
| UC-V06  | Light and dark   | 3-step scenario: dark look / take torch / lit look        | engine (address-now): observation filter (SIM-07); mechanic (address-now): illumination_propagation              |
| UC-V07  | Contagion        | Alice coughs, bob probabilistically infected              | graph (address-now): seeded-RNG primitive for probabilistic mechanics; mechanic (address-now): contagion mechanic|

**Gap totals:** 11 address-now, 6 defer, 0 out-of-scope. All 7 files surface address-now gaps (plan minimum was 4 of 7).

## Key themes surfaced for Wave 4 synthesis

1. **Passive-tick mechanics are currently unreachable.** UC-V03 decay, UC-V04 seasons, and implicitly UC-V07 symptom progression all need a tick-boundary sweep the engine does not perform today. UC-V03 explicitly cites SIM-09 for Phase 7 traceability.
2. **World-level state has no first-class matcher.** UC-V02 weather and UC-V04 seasons both write to a dedicated "world" node, but the mechanic matcher vocabulary only supports per-entity property changes. A WorldPropertyMatcher (or a canonical tick-dispatch from the world node) is the smallest step that unlocks both.
3. **Non-deterministic mechanics are unmodelled.** UC-V07 contagion is the first use case that requires probabilistic state change, and the framework's assumption that `apply()` is pure directly conflicts with it. A seeded-RNG primitive on MechanicContext (or a dedicated probabilistic-mutation API) is needed before the contagion mechanic can ship.
4. **Observation filtering is a reusable gap.** UC-V06 (light/dark) overlaps with UC-S02 (LOS occlusion) from Wave 2 spatial: both need the same engine layer that separates "what the graph contains" from "what the actor can perceive" (SIM-07). This is a high-value consolidation target for Wave 4.
5. **Cascade control matters even at depth 1.** UC-V01 fire spread works today at a single hop, but the moment a chain-depth or cycle-detection primitive is missing, two-hop scenarios (fire → table → chair) are at risk. The engine gap is small but pointed (SIM-08 cascade control).

## Validation

- Plan verification script (inline in plan): **passed** — 7 files, 11 address-now gaps, UC-V03 cites SIM-09.
- `tests/test_design_validation/test_use_case_schema.py`: **frontmatter + uniqueness tests pass**. The `test_library_has_use_cases` assertion (>= 30 total) fails here as expected — this worktree authors only the 7 environmental UCs; the remaining 28 come from parallel waves and are collected at phase-level by the orchestrator.
- Per-file line counts: all 7 files are between 85 and 112 lines (minimum was 40).

## Commits

| Task | Commit   | File                                                                |
|------|----------|---------------------------------------------------------------------|
| UC-V01 | 37d7492 | .planning/use-cases/environmental/UC-V01-fire-spread.md             |
| UC-V02 | ba2163d | .planning/use-cases/environmental/UC-V02-weather-change.md          |
| UC-V03 | efc31eb | .planning/use-cases/environmental/UC-V03-decay.md                   |
| UC-V04 | d1b0a25 | .planning/use-cases/environmental/UC-V04-seasons.md                 |
| UC-V05 | 55c815f | .planning/use-cases/environmental/UC-V05-terrain-effect.md          |
| UC-V06 | 000bcfe | .planning/use-cases/environmental/UC-V06-light-and-dark.md          |
| UC-V07 | fc8fea5 | .planning/use-cases/environmental/UC-V07-contagion.md               |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Every use case is fully authored with complete frontmatter, graph_builder, actions, expected_observations, gaps, and narrative sections.

## Self-Check: PASSED

- All 7 UC files exist on disk at the plan's target paths.
- All 7 commits verified in git log (hashes above).
- Plan verification script returns `ok 7 environmental UCs, 11 address-now gaps, UC-V03 cites SIM-09`.
- Schema validator frontmatter + uniqueness tests pass.
