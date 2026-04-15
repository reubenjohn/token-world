---
phase: 04-llm-mechanic-generation
plan: 06
subsystem: mechanic-authoring
tags: [seeds, spatial, mech-01, mech-05, mech-06, d-11, d-38]
requires:
  - 04-01 (flat mechanic layout; Mechanic ABC + class-level id/tags)
  - 04-02 (validate-mechanic CLI)
  - 04-03 (DiagnosticsSink — consumed indirectly by harness)
  - 04-04 (integration harness + harness matcher; do NOT extend here)
  - 04-05 (authoring guide + _helpers.py convention)
  - src/token_world/mechanic/{protocol,context,matchers,engine,registry}.py
  - src/token_world/mechanic/seeds/{movement,observation,environmental_reaction}.py
provides:
  - MECH01 passage_move seed mechanic (voluntary; doorway/bridge/direct connects)
  - MECH05 terrain_move seed mechanic (voluntary; stamina cost via multiplier)
  - MECH06 position_sync seed mechanic (involuntary; post-move hook)
  - _helpers.py: _find_open_passage, _current_location, _PASSAGE_SUBTYPES, _is_passage_open
  - UC-S01 / UC-S06 / UC-S07 / UC-V05 flipped from expected_outcome=yield → pass
  - VALIDATION rows 04-06-T1 / T2 / T3
affects:
  - src/token_world/mechanic/seeds/_helpers.py (added helpers; was stub)
  - src/token_world/mechanic/seeds/passage_move.py (created)
  - src/token_world/mechanic/seeds/terrain_move.py (created)
  - src/token_world/mechanic/seeds/position_sync.py (created)
  - tests/test_mechanic/test_seeds/test_passage_move.py (created)
  - tests/test_mechanic/test_seeds/test_terrain_move.py (created)
  - tests/test_mechanic/test_seeds/test_position_sync.py (created)
  - tests/test_mechanic/test_registry.py (seed-universe list bumped to 6 ids)
  - .planning/use-cases/spatial/UC-S01-movement-through-doorway.md (verb + target + expected_outcome)
  - .planning/use-cases/spatial/UC-S06-traversal-across-terrain.md (verb + target + expected_outcome + reverse connects edges)
  - .planning/use-cases/spatial/UC-S07-position-updating-on-move.md (verb + expected_outcome)
  - .planning/use-cases/environmental/UC-V05-terrain-effect.md (verb + expected_outcome)
  - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md (rows T1-T3)
tech-stack:
  added: []
  patterns:
    - "Helpers live under _helpers.py with underscore prefix (D-05: registry skips); shared by ≥2 seeds before graduating — _find_open_passage will also be used by plan 04-07's try_door (MECH27)."
    - "Matcher ownership stays with 04-04: plans 04-06..04-11 align *manifest classified.verb* to mechanic ids rather than extending match_mechanic_for_verb."
    - "Involuntary post-move hook via EdgeMatcher(add_edge, located_in). Engine splits 'alice->room_b' on '->' so chain-ctx.target == actor; position_sync walks located_in neighbors rather than parsing mutation payload."
    - "Terrain cost = max(source, target) so actors pay for the heaviest terrain touched on a step; integer-rounded so UC-V05 assertion (stamina 20→18) lands exactly."
key-files:
  created:
    - src/token_world/mechanic/seeds/passage_move.py
    - src/token_world/mechanic/seeds/terrain_move.py
    - src/token_world/mechanic/seeds/position_sync.py
    - tests/test_mechanic/test_seeds/test_passage_move.py
    - tests/test_mechanic/test_seeds/test_terrain_move.py
    - tests/test_mechanic/test_seeds/test_position_sync.py
  modified:
    - src/token_world/mechanic/seeds/_helpers.py (_find_open_passage, _current_location, vocab constants)
    - tests/test_mechanic/test_registry.py (TestSeedUniverse.test_scan_discovers_seeds expected list)
    - .planning/use-cases/spatial/UC-S01-movement-through-doorway.md
    - .planning/use-cases/spatial/UC-S06-traversal-across-terrain.md
    - .planning/use-cases/spatial/UC-S07-position-updating-on-move.md
    - .planning/use-cases/environmental/UC-V05-terrain-effect.md
    - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md
decisions:
  - "passage_move accepts BOTH passage-entity-mediated moves (src→P→dst) AND direct connects (src→dst). This collapses UC-S01, UC-S06, UC-S07 onto a single mechanic. Bridge (UC-S06) treated as a passage subtype because traversable=True maps onto the same 'gate open?' question as open=True."
  - "Terrain cost uses max(source, target) rather than destination-only. UC-V05 vignette says the swamp (source) slows alice; destination-only would give cost=1 instead of the asserted 2. max() preserves both intuitions: impassable destination (wall=99) still blocks, and heavy source still drains correctly."
  - "passage_move.apply() sets actor.location property AND remakes the located_in edge. UC-S07's property_equals assertion needs location='room_b'; keeping the mirror avoids a second 'mirror' mechanic and keeps compatibility with the original movement seed."
  - "position_sync spatial-anchor preference: centroid > bbox midpoint > point position. Deterministic so chained re-writes stay idempotent; skips silently when the destination carries none of them (check returns False — no mutations)."
  - "Matcher extension deliberately NOT attempted. Per 04-04-SUMMARY Extension Contract, plan-local matcher edits are forbidden; we update manifest classified.verb values instead. UC-S06 setup patch (added reverse connects edges) is a graph-shape fix, not a matcher change."
  - "Registry seed test (test_scan_discovers_seeds) bumped to the 6-seed list once. Future seed plans (04-07..04-11) will edit the same assertion."
metrics:
  duration: ~45 min
  completed: 2026-04-12
  test_delta: 476 → 518 (+42 from 38 new test methods; 4 UCs moved xfail → pass)
  xfail_delta: 14 → 10 (4 UCs flipped)
---

# Phase 4 Plan 06: Seed cluster — spatial movement extensions (MECH01/05/06) Summary

Ships the first seed-authoring cluster. Three mechanics close GAP-MECH01,
GAP-MECH05, GAP-MECH06 and the first four use cases flip from `yield`
(xfail) to `pass` in the integration harness. One shared helper
(`_find_open_passage`) lands in `_helpers.py` and will be reused by plan
04-07's `try_door` (MECH27).

## Cluster Map

| ID       | Mechanic      | voluntary | tags                     | UCs closed                         |
| -------- | ------------- | --------- | ------------------------ | ---------------------------------- |
| MECH01   | passage_move  | true      | [spatial, passage]       | UC-S01, UC-S06, UC-S07             |
| MECH05   | terrain_move  | true      | [spatial, terrain]       | UC-V05                             |
| MECH06   | position_sync | false     | [spatial, post-move]     | (triggers reactively during S07)   |

## Mechanic Contracts

### `passage_move` (MECH01)

Voluntary. Accepts two path shapes:

1. **Direct connects:** `src --connects--> dst`. UC-S07 pattern
   (rooms directly connected; no intermediate entity).
2. **Mediated:** `src --connects--> passage --connects--> dst` where
   `passage.subtype ∈ {doorway, passage, bridge}` and either
   `passage.open == True` (doorway/passage) or
   `passage.traversable == True` (bridge). UC-S01 / UC-S06 pattern.

`apply()` removes the old `located_in` edge, adds a new one to the
target, and mirrors the destination into `actor.location` (property).

### `terrain_move` (MECH05)

Voluntary. Reads terrain-cost info from either end of the step:

1. Explicit `movement_cost_multiplier` property (float).
2. Fallback `_DEFAULT_TERRAIN_COSTS` lookup by `terrain_type`
   (floor=1, grass=1, path=1, bridge=1, stair=2, swamp=2, mud=3,
   sand=3, water=5, wall=99).

Effective cost = `max(source_cost, target_cost)` so the actor pays for
the heaviest terrain touched. Costs ≥ `_IMPASSABLE_THRESHOLD` (50) fail
the check unconditionally. Otherwise stamina is debited by
`int(round(cost))`.

`apply()` consumes stamina, remakes the `located_in` edge, mirrors
`actor.location`. Accepts both `connects` and `adjacent_to` as the
adjacency relation (UC-V05 uses `adjacent_to`; UC-S06-style bridges use
`connects`).

### `position_sync` (MECH06)

**Involuntary.** Matcher:
`EdgeMatcher(event_type="add_edge", edge_label="located_in")`. Fires
reactively after any mechanic that adds a `located_in` edge. The
chain-engine emits `add_edge` mutations with `target="<src>-><dst>"` and
splits on `->`, so `chain_ctx.target == actor_id` (the moved agent).
The mechanic resolves the new destination via
`_current_location(ctx, actor_id)` rather than trusting the mutation
payload.

Spatial-anchor preference (deterministic):
1. Destination's `centroid` property
2. `bbox` midpoint `[(x0+x1)/2, (y0+y1)/2]`
3. Destination's point `position`

`check()` returns `False` (no-op) when the destination exposes none of
these — position_sync silently skips non-spatial entities rather than
corrupting them.

## Shared Helpers (D-11)

Added to `src/token_world/mechanic/seeds/_helpers.py`:

```python
_PASSAGE_SUBTYPES: frozenset[str]  # {"doorway", "passage", "bridge"}
_is_passage_open(props: dict) -> bool
_find_open_passage(ctx, src, dst) -> str | None
_current_location(ctx, actor) -> str | None
```

`_current_location` is the common "where is the actor?" lookup used by
all three new seeds; extracting it prevents the three mechanics from
drifting to different semantics (out-neighbors vs filtered in-neighbors
vs `actor.location` prop).

`_find_open_passage` is already consumed by `passage_move` and slated
for reuse by `try_door` in plan 04-07 (MECH27). That's the D-11 "≥ 3
uses" threshold crossing already visible on the horizon.

## Use-Case Flips

| UC      | Before                | After                                 | Mechanic     |
|---------|-----------------------|---------------------------------------|--------------|
| UC-S01  | yield (no matcher)    | pass (graph assertions satisfied)     | passage_move |
| UC-S06  | yield                 | pass                                  | passage_move |
| UC-S07  | yield                 | pass (position_sync chains)           | passage_move + position_sync |
| UC-V05  | yield                 | pass (stamina 20 → 18)                | terrain_move |

**Manifest-level edits:** classified.verb flipped from `move` → the
matching mechanic id (per 04-04's matcher contract: harness matches on
exact `verb == info.id`). UC-S06 additionally gained reverse connects
edges (`room_a→bridge_stone`, `room_b→bridge_stone`) so the walk
direction lines up with the actor's source room — the original
directionality (`bridge_stone→room_a`) is insufficient for walking
*from* room_a.

## Matcher Extension Contract

Per 04-04's Extension Contract (and 04-REVIEWS HIGH #1), this plan did
**not** extend `match_mechanic_for_verb`. The strategic choice was to
align manifest `classified.verb` values to mechanic ids (exact match
via the current stub) rather than teaching the matcher about aliases,
tag fallbacks, or classifier-driven routing. Those extensions — if ever
needed — must land in `tests/test_mechanic/test_harness_matcher.py`
first, owned by a later plan (Phase 5's classifier replacement being
the likely home).

## Deviations from Plan

### Auto-fixed (Rule 2/3, in-scope)

**1. [Rule 3 - Blocking] Registry seed-universe test pinned the
pre-plan 3-seed list.**
- Found during: Task 1 GREEN phase-gate.
- Issue: `tests/test_mechanic/test_registry.py::TestSeedUniverse::test_scan_discovers_seeds`
  asserted `ids == ["environmental_reaction", "movement", "observation"]`.
  Adding any new seed module breaks that invariant.
- Fix: Updated the assertion to the final 6-seed list once Task 2
  landed. The seed-universe test expects to be updated exactly once
  per seed-authoring plan; plans 04-07..04-11 will each bump it.
- Commits: `395d42e`, `646cc5d`.

**2. [Rule 1 - Bug] UC-V05 terrain cost semantics: destination-only
cost gave stamina 19, the manifest asserts 18.**
- Found during: Task 2 GREEN (`test_apply_uc_v05_swamp_to_dry_land`).
- Issue: Initial `terrain_move` read multiplier from destination only;
  UC-V05's swamp (source, multiplier 2.0) carries the cost, not the
  dry path (destination, multiplier 1.0). The vignette also supports
  source-as-cost: "the swamp itself slowed her down."
- Fix: Changed to `max(source_cost, target_cost)`. Preserves
  impassable-destination (wall) guard and the "source drains" UC-V05
  intuition in one rule.
- Commit: `646cc5d`.

**3. [Rule 3 - Blocking] UC-S06 setup had one-way `bridge→room`
connects edges; passage_move walks `src→connects→P`, so
`room_a→bridge_stone` was missing.**
- Found during: Task 3 harness run.
- Issue: `ctx.neighbors(room_a, relation="connects")` returned `[]`
  because the manifest only declared `bridge_stone→room_a`, not the
  reverse. No passage found; UC failed.
- Fix: Added reverse connects edges in the manifest's graph_builder.
  Edges are semantically bidirectional (you can walk either way across
  a bridge); explicit reverse edges make that physical.
- Commit: `4bff16a`.

**4. [Rule 2 - Style] Ruff lint drift on freshly authored seeds
(UP037 quoted annotations, SIM110 explicit-loop, E501 line length).**
- Found during: Task 3 phase-gate (`ruff check src/token_world/mechanic/seeds/`).
- Issue: 12 findings across the 4 new files; quotes around
  `MechanicContext` annotations were unnecessary given
  `from __future__ import annotations`.
- Fix: `uv run ruff check --fix`, then hand-fixed the 2 remaining
  (E501 reflow, SIM110 any() refactor), then `uv run ruff format`.
  Zero behavioral changes.
- Commit: `4bff16a`.

### Pre-existing / out-of-scope

- `src/token_world/mechanic/validation.py` still carries the 2 E501
  findings inherited from 04-02; unchanged by this plan. Remains in
  `deferred-items.md` for 04-12 cleanup.

## Test Counts

- Before plan: **476 passed, 22 skipped, 14 xfailed**.
- After plan: **518 passed, 22 skipped, 10 xfailed** (+42 tests, 4 UCs
  flipped from xfail to pass).

Per-test-file counts:
- `test_passage_move.py`: 17 tests
- `test_terrain_move.py`: 12 tests
- `test_position_sync.py`: 9 tests
- (Existing suites unchanged; only the seed registry list expanded.)

## Lint / Format / Type

- `uv run ruff check src/token_world/mechanic/seeds/` — clean.
- `uv run ruff format src/token_world/mechanic/seeds/` — clean
  (one file reformatted during execution, final state is clean).
- Full-suite `ruff check src/` still shows the pre-existing
  `validation.py` E501 drift (04-02 inheritance; out of scope).

## Commits

| Task           | Commit  | Type   | Summary                                                                       |
|----------------|---------|--------|-------------------------------------------------------------------------------|
| T1 (RED)       | 9a788a9 | test   | failing tests for MECH01 passage_move + _find_open_passage                    |
| T1 (GREEN)     | 395d42e | feat   | passage_move + _helpers.py (_find_open_passage, _current_location)            |
| T2 (RED)       | e6e0f79 | test   | failing tests for MECH05 terrain_move + MECH06 position_sync                  |
| T2 (GREEN)     | 646cc5d | feat   | terrain_move + position_sync                                                  |
| T3             | 4bff16a | feat   | UC flips (S01/S06/S07/V05) + VALIDATION rows + ruff cleanup                   |

## Notes for Downstream Plans

- **Plan 04-07 (MECH27 try_door, MECH02 look, MECH08 pickup):**
  Reuse `_find_open_passage` from `_helpers.py` for `try_door`. That
  will be the 3rd shared use, formally crossing the D-11 threshold. No
  new helper required unless a cross-seed pattern appears. `try_door`
  should set `passage.open = True` on a successful attempt; this does
  NOT require a chain-engine hook because passage_move reads `open`
  live on each check.
- **Plan 04-08+ (hunger, drink, rest, craft):** If any new seed adds a
  `located_in` edge, `position_sync` will automatically fire for it.
  That's why it lives in the shared seed directory rather than inside
  passage_move. Authors of voluntary mechanics that add `located_in`
  edges should pair-test with position_sync to verify the cascade.
- **Plan 04-12 (final cleanup):**
  `tests/test_mechanic/test_registry.py::TestSeedUniverse::test_scan_discovers_seeds`
  will need one final bump to the full seed list once 04-07..04-11 all
  land.
- **Matcher ownership:** Plans 04-07..04-11 follow the same pattern as
  this plan — align manifest `classified.verb` to mechanic ids. Do
  NOT edit `match_mechanic_for_verb`.

## Threat Flags

None beyond the plan's declared `<threat_model>` (T-04-AST-BYPASS,
T-04-HELPER-CYCLE — both marked `accept` as written). The new seeds
add no new network paths, auth boundaries, schema changes, or shell
interpolation surface.

## Self-Check: PASSED

- All 5 commits present in `git log --oneline` (9a788a9, 395d42e,
  e6e0f79, 646cc5d, 4bff16a).
- Files created (Glob-verified):
  - `src/token_world/mechanic/seeds/passage_move.py` ✓
  - `src/token_world/mechanic/seeds/terrain_move.py` ✓
  - `src/token_world/mechanic/seeds/position_sync.py` ✓
  - `tests/test_mechanic/test_seeds/test_passage_move.py` ✓
  - `tests/test_mechanic/test_seeds/test_terrain_move.py` ✓
  - `tests/test_mechanic/test_seeds/test_position_sync.py` ✓
- Files modified:
  - `src/token_world/mechanic/seeds/_helpers.py` (was stub; now has
    _find_open_passage, _current_location, _PASSAGE_SUBTYPES,
    _is_passage_open) ✓
  - 4 UC manifests flipped to `expected_outcome: pass` ✓
  - `tests/test_mechanic/test_registry.py` bumped to 6-seed list ✓
  - `.planning/phases/04-llm-mechanic-generation/04-VALIDATION.md`
    gained rows 04-06-T1/T2/T3 ✓
- Acceptance greps:
  - `grep -n "class PassageMoveMechanic"` → 1 match ✓
  - `grep -n 'id = "passage_move"'` → 1 match ✓
  - `grep -n 'id = "terrain_move"'` → 1 match ✓
  - `grep -n 'id = "position_sync"'` → 1 match ✓
  - `grep -n "voluntary = False" position_sync.py` → 1 match ✓
  - `grep -n "def watches" position_sync.py` → 1 match ✓
  - `grep -n "def _find_open_passage" _helpers.py` → 1 match ✓
  - `grep -c "^| 04-06-T"` in VALIDATION.md → 3 ✓
  - `grep -l "expected_outcome: pass"` in the 4 UC manifests → 4 hits ✓
- Validation CLI: `token-world validate-mechanic` PASS on all 3 new
  modules ✓
- Tests:
  - `uv run pytest tests/test_mechanic/test_seeds/test_passage_move.py -x -q` — 17 passed ✓
  - `uv run pytest tests/test_mechanic/test_seeds/test_terrain_move.py tests/test_mechanic/test_seeds/test_position_sync.py -x -q` — 21 passed ✓
  - `uv run pytest tests/test_integration/test_use_cases.py -k "UC-S01 or UC-S06 or UC-S07 or UC-V05" -q` — 4 passed ✓
  - `uv run pytest -x -q` — 518 passed, 22 skipped, 10 xfailed ✓
- Lint/format/type on touched seeds: clean ✓
