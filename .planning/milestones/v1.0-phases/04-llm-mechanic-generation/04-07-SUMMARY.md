---
phase: 04-llm-mechanic-generation
plan: 07
subsystem: mechanic-authoring
tags: [seeds, spatial, social, mech-02, mech-03, mech-04, mech-13, mech-27, d-11, d-37]
requires:
  - 04-01 (flat layout; Mechanic ABC; tags default)
  - 04-02 (validate-mechanic CLI)
  - 04-04 (integration harness + frozen matcher; do NOT extend here)
  - 04-05 (authoring guide + _helpers.py convention)
  - 04-06 (_find_open_passage; _current_location; _PASSAGE_SUBTYPES)
  - src/token_world/mechanic/{protocol,context,matchers,engine,registry}.py
  - src/token_world/graph/spatial.py (SpatialIndex with nearest/within/intersects)
provides:
  - MECH02 look seed mechanic (voluntary; room-local visibility; GAP-GRAPH02 fallback)
  - MECH03 find_nearest seed mechanic (voluntary; ctx.spatial.nearest + brute-force fallback)
  - MECH04 aoe seed mechanic (voluntary; ctx.spatial.within + circle refinement)
  - MECH13 speak seed mechanic (voluntary; room-filtered + earshot-radius fan-out)
  - MECH27 try_door seed mechanic (voluntary; unlock-or-refuse branching)
  - _helpers.py: _find_matching_key — walks actor.holds for a key_id match
  - UC-S02 / UC-S03 / UC-S04 / UC-O08 / UC-E06 flipped from expected_outcome=yield → pass
  - Refusal-narrative pattern (last_refusal_narrative / last_refusal_target on actor) for 04-08 MECH16 reuse
  - VALIDATION rows 04-07-T1 / T2 / T3
affects:
  - src/token_world/mechanic/seeds/_helpers.py (_find_matching_key added; _find_open_passage conceptually reused)
  - src/token_world/mechanic/seeds/look.py (created)
  - src/token_world/mechanic/seeds/find_nearest.py (created)
  - src/token_world/mechanic/seeds/aoe.py (created)
  - src/token_world/mechanic/seeds/speak.py (created)
  - src/token_world/mechanic/seeds/try_door.py (created)
  - tests/test_mechanic/test_seeds/test_look.py (created; 11 tests)
  - tests/test_mechanic/test_seeds/test_find_nearest.py (created; 9 tests)
  - tests/test_mechanic/test_seeds/test_aoe.py (created; 8 tests)
  - tests/test_mechanic/test_seeds/test_speak.py (created; 10 tests)
  - tests/test_mechanic/test_seeds/test_try_door.py (created; 12 tests)
  - tests/test_mechanic/test_registry.py (seed-universe assertion: 6 → 11 ids)
  - .planning/use-cases/spatial/UC-S02-line-of-sight-occlusion.md (expected_outcome)
  - .planning/use-cases/spatial/UC-S03-nearest-object-query.md (expected_outcome)
  - .planning/use-cases/spatial/UC-S04-area-of-effect.md (expected_outcome)
  - .planning/use-cases/social/UC-O08-speech-broadcast.md (expected_outcome + verb + target + setup last_utterance)
  - .planning/use-cases/edge-case/UC-E06-move-into-locked-room.md (expected_outcome + verb + target)
  - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md (rows T1-T3)
  - .planning/phases/04-llm-mechanic-generation/deferred-items.md (pre-existing 04-06 ruff drift)
tech-stack:
  added: []
  patterns:
    - "Refusal narrative pattern established in try_door: when a mechanic refuses to fire its canonical side effect, it still writes last_refusal_narrative + last_refusal_target on the actor. Consumable by Phase 5 observation synthesis and by any future blocked-interaction mechanic (MECH16 use_object, pick_lock)."
    - "Degraded-query fallback for GAP-GRAPH02 documented in look.py module docstring: room-local visibility filter preserves UC-S02's 'cannot see across wall' invariant by construction. When segment_intersections lands, swap in a true ray check without breaking the UC."
    - "ctx.spatial.within (UC-S04 bbox) over-approximates a circle at the corners, so aoe.py post-filters with Euclidean distance² vs radius². The bbox-only fast path still runs for nodes with bbox-not-position (rooms, multi-tile entities)."
    - "Matcher extension contract (04-04-SUMMARY) honored: classified.verb renamed to match mechanic id; no edit to match_mechanic_for_verb. UC-O08 (shout→speak) and UC-E06 (move→try_door) follow the pattern."
    - "speak uses room-filter + Euclidean radius composition: cross-room listeners are excluded by room membership (natural wall occlusion), and distant same-room listeners are excluded by radius. This composition handles UC-O08 with zero explicit occluder handling."
    - "_find_matching_key crosses the D-11 '3 shared uses' threshold once a pick_lock / try_chest mechanic (04-08+) lands. Consistent with _find_open_passage's trajectory in 04-06."
key-files:
  created:
    - src/token_world/mechanic/seeds/look.py
    - src/token_world/mechanic/seeds/find_nearest.py
    - src/token_world/mechanic/seeds/aoe.py
    - src/token_world/mechanic/seeds/speak.py
    - src/token_world/mechanic/seeds/try_door.py
    - tests/test_mechanic/test_seeds/test_look.py
    - tests/test_mechanic/test_seeds/test_find_nearest.py
    - tests/test_mechanic/test_seeds/test_aoe.py
    - tests/test_mechanic/test_seeds/test_speak.py
    - tests/test_mechanic/test_seeds/test_try_door.py
  modified:
    - src/token_world/mechanic/seeds/_helpers.py (added _find_matching_key)
    - tests/test_mechanic/test_registry.py (TestSeedUniverse.test_scan_discovers_seeds bumped to 11 ids)
    - .planning/use-cases/spatial/UC-S02-line-of-sight-occlusion.md
    - .planning/use-cases/spatial/UC-S03-nearest-object-query.md
    - .planning/use-cases/spatial/UC-S04-area-of-effect.md
    - .planning/use-cases/social/UC-O08-speech-broadcast.md
    - .planning/use-cases/edge-case/UC-E06-move-into-locked-room.md
    - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md
    - .planning/phases/04-llm-mechanic-generation/deferred-items.md
decisions:
  - "look ships the degraded fallback rather than a blocked_by stub because UC-S02's assertion chain (not_has_property alice.saw) holds by the room-local scan regardless of GAP-GRAPH02. A stub would unnecessarily block a UC that's already satisfiable with the available primitives."
  - "find_nearest reads the filter subtype from ctx.target.subtype rather than a separate filter field. This keeps the MechanicContext DSL unchanged — UC-S03's classified.filter is not passed to the mechanic; we derive the same subtype from the canonical target entity. The target is treated as a reference example, not the canonical answer — the mechanic re-computes the winner against its own point."
  - "aoe post-filters bbox hits with true Euclidean radius² because UC-S04's corner entities (barrel_3 at dist √32 ≈ 5.66) sit inside the bbox [2,2,8,8] but outside the radius-3 circle. Without post-filtering, UC-S04's not_has_property barrel_3.damaged would fail."
  - "aoe reads blast_radius from the target entity (default 3.0). This models 'the explosion is a property of the payload' — UC-S04's fireball targets barrel_1 as the detonation site; a dynamite in a future scenario would carry its own radius. Alternative (radius from actor) was rejected because it conflates 'who launched it' with 'what exploded'."
  - "speak ranges over ctx.find_nodes(type='agent') rather than positional listeners only. An unpositioned agent in the same room still hears the utterance, which matches natural-language intuition and keeps the mechanic useful on hand-crafted graphs without spatial info. The earshot-radius filter applies only when both speaker and listener carry a 2D point."
  - "try_door's 3-branch apply (unlocked / locked+key / locked+no-key) uses the same _find_matching_key helper path as any future pick_lock mechanic. The refusal branch writes to the actor (not the door) so UC-E06's door-locked-stays-True assertion is trivially preserved; the door state is immutable without a matching key."
  - "UC-O08 setup patch (add last_utterance='help!' to alice) is a ground-truth fix, not a mechanic extension. The original manifest buried the utterance in classified.utterance, which the mechanic can't see. Moving it to setup state matches how a real simulation would flow: the resident agent's last utterance is a graph property, the classified verb is routing metadata."
metrics:
  duration: ~50 min
  completed: 2026-04-12
  test_delta: 518 → 573 (+50 from 50 new test methods; 5 UCs moved xfail → pass; full-suite xfail 10 → 5)
  xfail_delta: 10 → 5 (5 UCs flipped)
---

# Phase 4 Plan 07: Seed cluster — spatial queries + AoE + speech + try_door (MECH02/03/04/13/27) Summary

Ships the second seed-authoring cluster. Five mechanics close GAP-MECH02,
GAP-MECH03, GAP-MECH04, GAP-MECH13, GAP-MECH27 and five use cases flip
from `yield` (xfail) to `pass`. One helper (`_find_matching_key`) is
added to `_helpers.py`, and `try_door` establishes the refusal-narrative
pattern that downstream blocked-interaction mechanics (04-08 MECH16)
will reuse.

## Cluster Map

| ID       | Mechanic      | voluntary | tags                                 | UC closed |
| -------- | ------------- | --------- | ------------------------------------ | --------- |
| MECH02   | look          | true      | [spatial, observation]               | UC-S02    |
| MECH03   | find_nearest  | true      | [spatial, query]                     | UC-S03    |
| MECH04   | aoe           | true      | [spatial, aoe]                       | UC-S04    |
| MECH13   | speak         | true      | [social, speech, spatial]            | UC-O08    |
| MECH27   | try_door      | true      | [spatial, interaction, passage]      | UC-E06    |

## Mechanic Contracts

### `look` (MECH02)

Voluntary. Reads `actor.located_in` room; writes `actor.last_observed` =
sorted list of entity ids sharing the room, minus any entity with
`occludes=True` (walls are not treated as observed objects). The UC-S02
invariant "alice does not gain perceptual knowledge across the wall" is
preserved by construction: bob lives in `room_b`, not `room_a`, so he is
simply not a located_in-neighbor of alice's room and is excluded from
`last_observed` without any ray-casting logic.

GAP-GRAPH02 (`ctx.spatial.segment_intersections`) is documented in the
module docstring as the ceiling for this fallback. When that gap closes,
`look` should switch to a segment-ray check that sees cross-room when
unobstructed.

### `find_nearest` (MECH03)

Voluntary. Reads the filter subtype from `ctx.target.subtype` (the target
is a reference example, not the canonical answer), then calls
`ctx.spatial.nearest(point, k=5, subtype=subtype)` with post-fetch
self-exclusion. Falls back to a brute-force Euclidean scan over
`ctx.find_nodes(subtype=subtype)` when the spatial index is empty. Writes
the winning id to `actor.nearest_result`.

UC-S03 pattern: alice at `[0,0]`, dagger at `[3,1]` (~3.16) wins against
sword `[7,0]` (7) and bow `[12,-4]` (~12.6).

### `aoe` (MECH04)

Voluntary. Reads `center = target.position` and `radius =
target.blast_radius` (default 3.0). Queries
`ctx.spatial.within([cx-r, cy-r, cx+r, cy+r])` for bbox-intersecting
nodes, then post-filters with true Euclidean distance² vs radius² to
avoid damaging corner entities that sit inside the bbox but outside the
circle. Skips the actor and any node with `subtype="room"`. One
`damaged=True` mutation per victim.

UC-S04 partitions 3 damaged (barrel_1, barrel_2, goblin_1 — distances 0,
~2.24, ~1.41) vs 2 spared (barrel_3, goblin_2 — both ~5.66 > 3).

### `speak` (MECH13)

Voluntary. Scope = every other agent sharing the speaker's room AND
within `earshot_radius` Euclidean (default 15.0, overridable per-actor).
Cross-room listeners are naturally excluded by room membership
(`blocks_sound` walls need no explicit handling in UC-O08). Utterance
source: `ctx.target.utterance` → `actor.last_utterance` → `"<no
utterance>"`. Emits one `last_heard` append-style mutation per listener
via read-modify-write (properties are immutable JSON).

UC-O08 pattern: alice at `[0,0]` in room_a, bob at `[5,0]` in room_a,
charlie at `[30,0]` in room_b. Bob hears; charlie doesn't.

### `try_door` (MECH27)

Voluntary. Target must have `subtype in {"door", "doorway", "gate"}`.
Three branches:

1. `target.locked != True` → no mutation.
2. `target.locked == True` AND `_find_matching_key(actor,
   target.required_key_id)` → set `target.locked = False`.
3. `target.locked == True` AND no matching key → write
   `actor.last_refusal_narrative = "the door is locked"` and
   `actor.last_refusal_target = target`. Door state unchanged.

UC-E06 pattern: alice without a key hits branch (3). Door stays locked,
alice stays in room_a, stamina unchanged; all UC-E06 assertions hold.

## Shared Helper (D-11)

Added to `src/token_world/mechanic/seeds/_helpers.py`:

```python
def _find_matching_key(ctx, actor, required_key_id) -> str | None
```

Walks *actor*'s `holds` out-edges for an entity whose `key_id` property
matches. Returns `None` on no match. `try_door` is the first consumer;
04-08's `pick_lock` / `try_chest` will be 2nd and 3rd, formally crossing
the D-11 "≥ 3 shared uses" threshold.

`_find_open_passage` (added in 04-06) was conceptually reused by
`try_door` via the subtype-frozen set; the mechanic doesn't call the
helper directly because its target IS the door (not the adjacency
shape), but the `_DOOR_SUBTYPES` frozenset in `try_door.py` mirrors
`_PASSAGE_SUBTYPES` in `_helpers.py` — both describe "passage-like"
entities with different entry points.

## Use-Case Flips

| UC      | Before                | After                                    | Mechanic      |
|---------|-----------------------|------------------------------------------|---------------|
| UC-S02  | yield (no matcher)    | pass (last_observed filters occluders)   | look          |
| UC-S03  | yield                 | pass (dagger_bronze wins)                | find_nearest  |
| UC-S04  | yield                 | pass (3 damaged, 2 spared)               | aoe           |
| UC-O08  | yield                 | pass (bob hears; charlie doesn't)        | speak         |
| UC-E06  | yield                 | pass (door stays locked; narrative set)  | try_door      |

**Manifest-level edits:**

- UC-S02/S03/S04: `expected_outcome` only.
- UC-O08: `expected_outcome` + `classified.verb: shout → speak` +
  `classified.target: bob` added + `setup` seeds `last_utterance=
  "help!"` on alice.
- UC-E06: `expected_outcome` + `classified.verb: move → try_door` +
  `classified.target: room_b → door_1`.

## Matcher Extension Contract

Per 04-04's Extension Contract (and 04-REVIEWS HIGH #1), this plan did
**not** extend `match_mechanic_for_verb`. Alignment was done by renaming
manifest `classified.verb` values to the matching mechanic id (exact
match via the current stub). Matcher ownership remains with the
post-plan centralized gate in
`tests/test_mechanic/test_harness_matcher.py`.

## Deviations from Plan

### Auto-fixed (Rule 2/3, in-scope)

**1. [Rule 3 - Blocking] Registry seed-universe test pinned the
6-seed list from 04-06.**
- Found during: Task 3 harness run (full suite).
- Issue: `tests/test_mechanic/test_registry.py::TestSeedUniverse::test_scan_discovers_seeds`
  asserted the 04-06-era 6-seed list. Adding 5 new seeds breaks that
  invariant.
- Fix: Bumped to the 11-seed list once all 5 new mechanics landed
  (the same "bump exactly once per plan" pattern 04-06 established).
- Commit: ffc76f3.

**2. [Rule 3 - Blocking] UC-O08 classified.verb was "shout", but the
harness matches on exact mechanic id.**
- Found during: Task 3 harness run on UC-O08.
- Issue: With `verb: shout`, no mechanic matched; UC failed with
  "expected mechanic to match but none did".
- Fix: Flipped `classified.verb: shout → speak` in the manifest,
  honouring the matcher extension contract (no edits to
  `match_mechanic_for_verb`). Added `target: bob` to satisfy harness's
  `target = classified.get("target") or classified.get("indirect_object")`
  contract.
- Commit: ffc76f3.

**3. [Rule 3 - Blocking] UC-O08 setup did not expose the utterance on
any node.**
- Found during: Task 3 harness run on UC-O08.
- Issue: The original manifest carried the utterance only on
  `classified.utterance`, which is not visible to the mechanic. The
  mechanic reads `target.utterance` → `actor.last_utterance` → fallback,
  and the fallback would have been silently propagated — losing the
  "help!" string that the UC vignette relies on.
- Fix: Added `last_utterance="help!"` to alice's setup props.
- Commit: ffc76f3.

**4. [Rule 3 - Blocking] UC-E06 classified.verb was "move" and target
was "room_b".**
- Found during: Task 3 harness run.
- Issue: `verb: move` with target "room_b" would have routed to
  `movement`, which fails its own check (alice has `position`, not
  `location`, and no located_in edge to room_b directly). Even if it
  fired, it would have violated UC-E06's `not_has_edge alice->room_b`
  assertion.
- Fix: Flipped `verb: move → try_door` and `target: room_b → door_1`
  per plan Task 3 instructions (align to mechanic id).
- Commit: ffc76f3.

**5. [Rule 2 - Style] Ruff format drift on freshly authored test files.**
- Found during: Task 3 phase-gate (`ruff format --check
  tests/test_mechanic/test_seeds/`).
- Issue: 5 new test files had collapsed multi-arg calls; formatter
  reflowed them to one-line form. Zero behavioural change.
- Fix: `uv run ruff format` on the 5 new tests and 5 new mechanic
  modules + `_helpers.py`. Tests still pass after reflow.
- Commit: ffc76f3.

### Pre-existing / out-of-scope

- `tests/test_mechanic/test_seeds/test_passage_move.py`,
  `test_position_sync.py`, `test_terrain_move.py` carry 5 ruff findings
  (I001 / F401 / E501) inherited from 04-06. Unchanged by this plan.
  Logged in `deferred-items.md` § 04-07 discoveries for 04-12 cleanup.
- `src/token_world/mechanic/validation.py` still has the 04-02/04-03
  E501 findings; unchanged by this plan. Already logged.

## Test Counts

- Before plan: **518 passed, 22 skipped, 10 xfailed**.
- After plan: **573 passed, 22 skipped, 5 xfailed** (+55 tests, 5 UCs
  flipped from xfail to pass).

Per-test-file counts (new):
- `test_look.py`: 11 tests
- `test_find_nearest.py`: 9 tests
- `test_aoe.py`: 8 tests
- `test_speak.py`: 10 tests
- `test_try_door.py`: 12 tests (includes 3 for `_find_matching_key`)

## Lint / Format / Type

- `uv run ruff check` on all plan-touched files — clean.
- `uv run ruff format --check` on all plan-touched files — clean.
- Full-tree `ruff check` still shows pre-existing 04-06 test drift
  (out of scope; logged in deferred-items.md).

## Commits

| Task | Commit  | Type | Summary                                                                  |
|------|---------|------|--------------------------------------------------------------------------|
| T1   | 98ed35c | feat | MECH02 look + MECH03 find_nearest + MECH04 aoe (28 tests)                |
| T2   | 27c401b | feat | MECH13 speak + MECH27 try_door + _find_matching_key helper (22 tests)    |
| T3   | ffc76f3 | feat | Flip 5 UCs to pass + VALIDATION rows + seed-registry bump + format       |

## Notes for Downstream Plans

- **Plan 04-08 (MECH07/08/14/15/16 object interaction):**
  - `_find_matching_key` is the 1st use of the "walks
    actor.holds for matching prop" idiom; a `pick_lock` / `try_chest`
    would be 2nd and 3rd. Once those land, consider a broader
    `_find_held_matching(ctx, actor, key, value) -> str | None`.
  - Reuse the refusal-narrative pattern from `try_door`: write
    `last_refusal_narrative` + `last_refusal_target` on actor when the
    mechanic "fires" but its canonical side effect is suppressed
    (blocked container, broken tool, insufficient skill).
- **Phase 5 (simulation engine):** The observation synthesizer should
  surface `last_observed`, `nearest_result`, `last_heard`,
  `last_refusal_narrative`, and `damaged` flags as natural-language
  narrative. These are the first 5 "observation-facing" properties
  seed mechanics write; they form the template for how Phase-5
  narrative should weave graph state into prose.
- **GAP-GRAPH02 closure (framework follow-up):** When
  `ctx.spatial.segment_intersections` lands, swap `look`'s room-local
  scan for a true ray check. UC-S02 will still pass because the ray
  from alice to bob intersects wall_1 (occludes=True); the look
  mechanic will continue to not-write `saw`.
- **Matcher ownership:** Plans 04-08..04-11 follow the same pattern —
  align manifest `classified.verb` to mechanic ids. Do NOT edit
  `match_mechanic_for_verb`.
- **Plan 04-12 (final cleanup):**
  - Bump `test_scan_discovers_seeds` once more for the final seed list.
  - Clear deferred-items.md § 04-06 / 04-07 ruff drift.
  - Flip `04-07-T1/T2/T3` from ⬜ pending to ✅ done in VALIDATION.md.

## Threat Flags

None beyond the plan's declared `<threat_model>` (T-04-AST-BYPASS —
validation pipeline runs on all 5 new modules; no new attack surface).
The new seeds add no network paths, auth boundaries, schema changes, or
shell interpolation surface.

## Self-Check: PASSED

- All 3 commits present: `98ed35c`, `27c401b`, `ffc76f3`.
- Files created (Glob-verified):
  - `src/token_world/mechanic/seeds/look.py` ✓
  - `src/token_world/mechanic/seeds/find_nearest.py` ✓
  - `src/token_world/mechanic/seeds/aoe.py` ✓
  - `src/token_world/mechanic/seeds/speak.py` ✓
  - `src/token_world/mechanic/seeds/try_door.py` ✓
  - `tests/test_mechanic/test_seeds/test_look.py` ✓
  - `tests/test_mechanic/test_seeds/test_find_nearest.py` ✓
  - `tests/test_mechanic/test_seeds/test_aoe.py` ✓
  - `tests/test_mechanic/test_seeds/test_speak.py` ✓
  - `tests/test_mechanic/test_seeds/test_try_door.py` ✓
- Files modified:
  - `src/token_world/mechanic/seeds/_helpers.py` (has _find_matching_key) ✓
  - 5 UC manifests flipped to `expected_outcome: pass` ✓
  - `tests/test_mechanic/test_registry.py` bumped to 11-seed list ✓
  - `.planning/phases/04-llm-mechanic-generation/04-VALIDATION.md`
    has 04-07-T1/T2/T3 rows ✓
  - `.planning/phases/04-llm-mechanic-generation/deferred-items.md`
    has 04-07 discovery entry ✓
- Acceptance verification:
  - All 5 mechanics: `uv run token-world validate-mechanic ...` → PASS ✓
  - Unit tests: 50 new pass ✓
  - `uv run pytest tests/test_integration/test_use_cases.py -k "UC-S02
    or UC-S03 or UC-S04 or UC-O08 or UC-E06" -v` → 5 passed ✓
  - `uv run pytest -q` → 573 passed, 22 skipped, 5 xfailed ✓
  - `ruff check` on plan-touched files → clean ✓
  - `ruff format --check` on plan-touched files → clean ✓
