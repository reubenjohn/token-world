---
phase: 04-llm-mechanic-generation
plan: 08
subsystem: mechanic-authoring
tags: [seeds, object-interaction, social, resource, mech-07, mech-08, mech-14, mech-15, mech-16, d-11, d-37]
requires:
  - 04-01 (flat layout; Mechanic ABC; tags default)
  - 04-02 (validate-mechanic CLI)
  - 04-04 (integration harness + frozen matcher; not extended here)
  - 04-05 (authoring guide + _helpers.py convention)
  - 04-07 (refusal-narrative pattern; _find_matching_key precedent)
  - src/token_world/mechanic/{protocol,context,matchers,engine,registry}.py
provides:
  - MECH07 trade seed mechanic (voluntary; single-tick atomic two-party swap)
  - MECH08 give seed mechanic (voluntary; item OR scalar transfer with pending_give)
  - MECH14 craft seed mechanic (voluntary; recipe-driven multi-input consumption via ctx.claim_id)
  - MECH15 consume seed mechanic (voluntary; remove held food + hunger delta, floored at 0)
  - MECH16 pickup seed mechanic (voluntary; inventory_cap-bounded; refusal narrative on full/already-held)
  - _helpers.py _count_holds (outgoing holds edge counter — shared primitive for pickup / give item-form)
  - _helpers.py _refuse_with_narrative (shared "write last_refusal_narrative + optional last_refusal_target" helper — absorbs the try_door pattern)
  - UC-O01 single-tick flipped yield → pass (manifest rewritten to mirrored pending_trade)
  - UC-O03 flipped blocked → pass (manifest converted from held_by → holds; pending_give staged)
  - UC-R01 flipped blocked → pass (recipe embedded on forge)
  - UC-R02 flipped yield → pass (shape already consume-compatible)
  - UC-R03 flipped blocked → pass (scalar pending_give staged)
  - UC-R04 flipped blocked → pass (shape already pickup-compatible)
  - VALIDATION rows 04-08-T1 / T2 / T3
affects:
  - src/token_world/mechanic/seeds/_helpers.py (+_count_holds, +_refuse_with_narrative)
  - src/token_world/mechanic/seeds/{pickup,consume,give,trade,craft}.py (new modules)
  - tests/test_mechanic/test_seeds/test_{pickup,consume,give,trade,craft}.py (new test files)
  - tests/test_mechanic/test_registry.py (TestSeedUniverse.test_scan_discovers_seeds: 11 → 16 ids)
  - tests/test_cli/test_scaffold_mechanic.py (scaffold id pickup → forage — avoids collision with copied seed)
  - .planning/use-cases/social/UC-O01-trade-negotiation.md (rewrite for single-tick)
  - .planning/use-cases/social/UC-O03-give-sword-to-bob.md (holds direction + pending_give)
  - .planning/use-cases/resource/UC-R01-craft-sword-from-materials.md (forge.recipe)
  - .planning/use-cases/resource/UC-R02-consume-food.md (expected_outcome only)
  - .planning/use-cases/resource/UC-R03-gift-currency.md (scalar pending_give)
  - .planning/use-cases/resource/UC-R04-inventory-limit.md (expected_outcome only)
  - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md
tech-stack:
  added: []
  patterns:
    - "Shared helper _refuse_with_narrative centralises the 04-07 try_door refusal idiom. Every voluntary mechanic that refuses inside apply (pickup, give, trade, craft) writes last_refusal_narrative + last_refusal_target through this helper, keeping the observation-synthesis surface in one place until 04-04's Extension Contract absorbs it at the harness layer."
    - "Phase-4 workaround convention for GAP-ENG02 (no indirect_object on MechanicContext): use-case graph_builder pre-stages actor.pending_give / actor.pending_trade dicts; mechanics read them in apply and clear them with ctx.set(..., None). When GAP-ENG02 lands in Phase 5, the three pending_* reads swap for ctx.indirect_object / ctx.amount without changing public mechanic shape."
    - "Single-tick atomic trade: mirrored pending_trade offers on both parties are swapped in one tick. Multi-turn offer/accept (UC-O01's original manifest shape) is explicitly deferred to Phase 5's GAP-ENG01 (classifier-level concern)."
    - "Recipe-on-workstation pattern for craft: target.recipe = {inputs: [node_ids], output_subtype: str, output_name?: str, output_props?: dict}. Keeps the recipe ground-truth in the graph alongside the tool, avoiding a separate registry until Phase 8."
    - "_count_holds crosses the D-11 '3 shared uses' threshold (pickup, give item-form, potential future weight/encumbrance mechanic). First helper graduated from seed-local to _helpers.py under the 04-08 cluster."
    - "Refusal-by-design inside apply: check returns passed=True whenever the action is COHERENT (actor+target exist, target is a valid subject), and refusal discriminators (inventory full, asymmetric trade, missing recipe input) live in apply where they can emit last_refusal_narrative. This matches 04-07 try_door and keeps narratives observable until harness-level synthesis lands (04-04 Extension Contract)."
key-files:
  created:
    - src/token_world/mechanic/seeds/pickup.py
    - src/token_world/mechanic/seeds/consume.py
    - src/token_world/mechanic/seeds/give.py
    - src/token_world/mechanic/seeds/trade.py
    - src/token_world/mechanic/seeds/craft.py
    - tests/test_mechanic/test_seeds/test_pickup.py
    - tests/test_mechanic/test_seeds/test_consume.py
    - tests/test_mechanic/test_seeds/test_give.py
    - tests/test_mechanic/test_seeds/test_trade.py
    - tests/test_mechanic/test_seeds/test_craft.py
  modified:
    - src/token_world/mechanic/seeds/_helpers.py
    - tests/test_mechanic/test_registry.py
    - tests/test_cli/test_scaffold_mechanic.py
    - .planning/use-cases/social/UC-O01-trade-negotiation.md
    - .planning/use-cases/social/UC-O03-give-sword-to-bob.md
    - .planning/use-cases/resource/UC-R01-craft-sword-from-materials.md
    - .planning/use-cases/resource/UC-R02-consume-food.md
    - .planning/use-cases/resource/UC-R03-gift-currency.md
    - .planning/use-cases/resource/UC-R04-inventory-limit.md
    - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md
key-decisions:
  - "Rewrote UC-O01 to a single-tick atomic trade instead of leaving it as yield. The PLAN.md decision tree allowed either path; rewriting was chosen because (a) the manifest already listed in files_modified, (b) the single-tick shape closes the UC today and keeps the multi-turn flavour as a tracked Phase 5 gap (GAP-ENG01), (c) leaving it as yield would have created a permanent 'false red' — a mechanic exists that exercises the single-tick path the narrative describes, just not the multi-turn protocol."
  - "Refusal-on-apply vs refusal-on-check: we keep CheckResult.passed=True whenever the action is *coherent* and push refusal discriminators (inventory full, asymmetric trade, missing recipe input, actor doesn't hold item) into apply where _refuse_with_narrative can emit last_refusal_narrative. This mirrors 04-07's try_door pattern and keeps Phase-4 refusal narratives observable in the graph until 04-04's harness-level synthesis lands."
  - "give ignores ctx.target and reads everything from actor.pending_give. Rationale: UC-O03 and UC-R03 disagree on what classified.target *means* (UC-O03 points at the item, UC-R03 points at the recipient), so routing through pending_give keeps the mechanic shape uniform across both UCs. When GAP-ENG02 adds indirect_object, the mechanic grows new reads without breaking either manifest."
  - "craft.py reads recipe off ctx.target (the workstation), not off the actor. Rationale: matches UC-R01's natural-language shape ('use THE FORGE to combine X and Y'), keeps recipes local to the tool that performs them, and avoids a recipe registry in Phase 4 (deferred to Phase 8). ctx.claim_id is used for the output id so that repeated crafts in the same graph deconflict naturally."
  - "trade.py refuses asymmetric offers (alice offers sword for shield, bob offers coin for sword) with a narrative rather than silently swapping whatever partial match exists. Honouring mutual consent is the Phase-5-friendly default: when the classifier gains accept/reject semantics, the same asymmetry check fires without changing the mechanic."
  - "UC-O03 converted from held_by (entity→agent) to holds (agent→entity). Rationale: every resource-category UC already uses holds; keeping UC-O03 on held_by would have required the give mechanic to support two inventory conventions simultaneously. D-37 / D-11 economy of conventions favoured one direction across the library; holds won because it matches how seeds read inventory (actor → neighbors(relation='holds'))."
patterns-established:
  - "Voluntary-refusal via _refuse_with_narrative: check passes on coherence; apply emits last_refusal_narrative + last_refusal_target when the canonical side effect is blocked by a precondition only visible at apply time."
  - "pending_* dict convention as Phase-4 workaround for GAP-ENG02: manifests pre-stage the third argument on actor.pending_give / actor.pending_trade; mechanics read and clear."
  - "Recipe-on-workstation for craft: target carries the recipe dict; no registry in Phase 4."
requirements-completed:
  - MECH-03

# Metrics
duration: ~25min
completed: 2026-04-12
---

# Phase 04 Plan 08: Object-Interaction Seed Cluster Summary

**Five object-interaction seed mechanics (trade/give/craft/consume/pickup) with shared _count_holds + _refuse_with_narrative helpers; six UCs flipped to pass; full suite green.**

## Performance

- **Duration:** ~25 min (3 task commits + 1 style + 1 manifest commit)
- **Started:** 2026-04-12 (executor session)
- **Completed:** 2026-04-12
- **Tasks:** 3 (per PLAN.md)
- **Files created:** 10 (5 seeds + 5 test files)
- **Files modified:** 10 (_helpers.py, 2 test infra files, 6 UC manifests, 1 VALIDATION.md)

## Accomplishments

- Shipped MECH07 (trade), MECH08 (give), MECH14 (craft), MECH15 (consume), MECH16 (pickup) — all seed-validated, all flat under `src/token_world/mechanic/seeds/`.
- Added two shared helpers under `_helpers.py`: `_count_holds` (outgoing holds edges) and `_refuse_with_narrative` (absorbs the 04-07 try_door refusal idiom for reuse across 4 of the 5 new mechanics).
- Flipped 6 object-interaction UCs to `expected_outcome: pass`: UC-O01 (single-tick trade), UC-O03, UC-R01, UC-R02, UC-R03, UC-R04.
- 52 new unit tests across the 5 seed modules; full pytest suite (631 passed / 17 skipped / 4 xfailed) remains green.
- VALIDATION.md updated with rows 04-08-T1/T2/T3, each marked `✅ passing`.
- `tests/test_mechanic/test_registry.py::TestSeedUniverse.test_scan_discovers_seeds` bumped from 11 → 16 ids.

## Task Commits

1. **Task 1: MECH15 consume + MECH16 pickup + shared helpers** — `3917c0c` (feat)
2. **Task 2: MECH07 trade + MECH08 give + MECH14 craft** — `e99ef41` (feat)
3. **Task 2.5: ruff format on seeds + tests** — `c68ca57` (style; cosmetic fold)
4. **Task 3: flip 6 UCs + VALIDATION rows + registry bump + scaffold-test id swap** — `dc2d3d6` (feat)

## Files Created/Modified

### Created

- `src/token_world/mechanic/seeds/pickup.py` — MECH16: inventory_cap-bounded holds add; refuses with narrative on full/already-held.
- `src/token_world/mechanic/seeds/consume.py` — MECH15: remove held food + decrement actor.hunger by nutrition (floored at 0).
- `src/token_world/mechanic/seeds/give.py` — MECH08: item-form and scalar-form transfers driven by `actor.pending_give`; clears pending_give after transfer.
- `src/token_world/mechanic/seeds/trade.py` — MECH07: single-tick atomic two-party swap via mirrored `pending_trade` dicts.
- `src/token_world/mechanic/seeds/craft.py` — MECH14: recipe-driven multi-input consumption; recipe lives on `target.recipe`; uses `ctx.claim_id` for output.
- `tests/test_mechanic/test_seeds/test_{pickup,consume,give,trade,craft}.py` — 52 unit tests across the five seeds.

### Modified

- `src/token_world/mechanic/seeds/_helpers.py` — `_count_holds` + `_refuse_with_narrative` added.
- `tests/test_mechanic/test_registry.py` — seed-universe id list bumped 11 → 16.
- `tests/test_cli/test_scaffold_mechanic.py` — `--id pickup` → `--id forage` to avoid collision with the pickup seed copied into scaffolded universes.
- `.planning/use-cases/social/UC-O01-trade-negotiation.md` — rewritten to single-tick atomic trade (mirrored pending_trade).
- `.planning/use-cases/social/UC-O03-give-sword-to-bob.md` — held_by → holds; pending_give staged on alice.
- `.planning/use-cases/resource/UC-R01-craft-sword-from-materials.md` — `forge.recipe` embedded.
- `.planning/use-cases/resource/UC-R02-consume-food.md` — yield → pass (shape already aligned).
- `.planning/use-cases/resource/UC-R03-gift-currency.md` — scalar pending_give staged.
- `.planning/use-cases/resource/UC-R04-inventory-limit.md` — blocked → pass (shape already aligned).
- `.planning/phases/04-llm-mechanic-generation/04-VALIDATION.md` — rows T1/T2/T3.

## Decisions Made

See `key-decisions` frontmatter for the six binding decisions made during this plan (UC-O01 rewrite, refusal-on-apply vs check, give's pending_give routing, craft's recipe location, trade's symmetric-consent default, UC-O03's held_by → holds conversion).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `tests/test_cli/test_scaffold_mechanic.py` used `--id pickup`, which now collides with the copied seed**

- **Found during:** Task 3 (full-suite verification)
- **Issue:** `token-world create` scaffolds a universe by copying every seed under `src/token_world/mechanic/seeds/` into `<universe>/mechanics/`. With `pickup.py` now a seed, `scaffold-mechanic <slug> --id pickup` sees an existing `mechanics/pickup.py` and refuses to overwrite, exiting 1. The test was asserting exit_code 0. This is collision, not a bug in scaffold-mechanic.
- **Fix:** Swapped `--id pickup` → `--id forage` (a non-seed id) everywhere in the test function. Added a docstring note explaining the "non-seed id" requirement so the trap doesn't recur as more seeds land.
- **Files modified:** `tests/test_cli/test_scaffold_mechanic.py`
- **Verification:** `uv run pytest tests/test_cli/test_scaffold_mechanic.py -x -q` passes; full suite remains green.
- **Committed in:** dc2d3d6 (folded into Task 3)

**2. [Rule 2 - Missing Critical] `tests/test_mechanic/test_registry.py::test_scan_discovers_seeds` hard-coded 11-id list**

- **Found during:** Task 3 (full-suite verification)
- **Issue:** This test asserts the *exact* sorted list of seed ids discovered in a freshly scaffolded universe. Adding 5 seeds made the assertion stale; leaving it stale is a regression, since future plans would see "test passed" without actually exercising the new seeds.
- **Fix:** Bumped the hard-coded list to 16 ids (adds consume, craft, give, pickup, trade).
- **Files modified:** `tests/test_mechanic/test_registry.py`
- **Verification:** `uv run pytest tests/test_mechanic/test_registry.py -x -q` passes.
- **Committed in:** dc2d3d6 (folded into Task 3)

**3. [Rule 2 - Missing Critical] UC-O01 manifest shape was multi-turn, incompatible with the `pass` outcome the plan required**

- **Found during:** Task 3 (UC flip)
- **Issue:** UC-O01's Phase-3 manifest listed two actions (`offer` then `accept`). The Phase-4 harness matcher fires at most one mechanic per action and has no cross-action memory; neither `offer` nor `accept` matches any seed id today. Flipping to `pass` with that manifest would permanently fail. The plan decision tree explicitly allowed rewriting to single-tick if the manifest was multi-turn; the files_modified list pre-approved the edit.
- **Fix:** Rewrote the manifest to a single `trade` action with mirrored `pending_trade` pre-staged on both parties. The vignette is preserved; the gap entry is updated to note that multi-turn offer/accept is GAP-ENG01 deferred to Phase 5.
- **Files modified:** `.planning/use-cases/social/UC-O01-trade-negotiation.md`
- **Verification:** `uv run pytest tests/test_integration/test_use_cases.py -k UC-O01 -v` reports PASSED.
- **Committed in:** dc2d3d6 (folded into Task 3)

**4. [Rule 2 - Missing Critical] UC-O03 manifest used `held_by` (entity→agent) direction, incompatible with the seed library's `holds` convention**

- **Found during:** Task 3 (UC flip)
- **Issue:** UC-O03 (and UC-O01's original Phase-3 shape) modelled inventory as `held_by(item, owner)`. Every resource-category UC and every Phase-4 seed uses `holds(owner, item)`. Keeping UC-O03 on `held_by` would have required `give` to support two direction conventions simultaneously, doubling the mechanic's surface for no narrative benefit.
- **Fix:** Converted UC-O03 to `holds`. Pre-staged `alice.pending_give = {"item": "sword", "recipient": "bob"}` to carry the recipient through the Phase-4 no-indirect-object DSL (GAP-ENG02 workaround).
- **Files modified:** `.planning/use-cases/social/UC-O03-give-sword-to-bob.md`
- **Verification:** `uv run pytest tests/test_integration/test_use_cases.py -k UC-O03 -v` reports PASSED.
- **Committed in:** dc2d3d6 (folded into Task 3)

---

**Total deviations:** 4 auto-fixed (3 Rule 2 missing-critical, 1 Rule 3 blocking)
**Impact on plan:** All four deviations were pre-approved or pre-anticipated by PLAN.md (UC-O01 decision tree, UC-O03 holds alignment is mechanic-convention hygiene, test-registry is a test-data update, scaffold-mechanic collision is a Phase-4 dogfooding friction worth fixing once). No scope creep.

## Issues Encountered

None — plan executed roughly as written, with the four pre-anticipated deviations above.

## Threat Flags

No new threat surface introduced. The cluster reuses the mutation API, claim_id, and query reads. The plan's declared T-04-AST-BYPASS is accepted (mitigated by the validation pipeline, which ran green against all 5 new seeds).

## Next Phase Readiness

- 16 seed mechanics now ship under `src/token_world/mechanic/seeds/` (flat D-10 layout). Plans 04-09 through 04-11 can compose on top without new scaffolding.
- The refusal-narrative pattern is now centralised enough to graduate to the harness layer: 04-04's Extension Contract has a ready-made consumer once Phase 5 wires narrative synthesis on the harness side.
- GAP-ENG01 (multi-turn offer/accept) and GAP-ENG02 (indirect_object DSL slot) are the two classifier/DSL gaps that this cluster's pending_* workarounds expose; both belong in Phase 5. The pending_* reads in give/trade are the exact swap-in points.

## Self-Check: PASSED

- All 10 created files present and on-disk (confirmed via commits dc2d3d6/c68ca57/e99ef41/3917c0c).
- All 4 commit hashes (3917c0c, e99ef41, c68ca57, dc2d3d6) resolvable via `git log`.
- Integration gate green: `uv run pytest tests/test_integration/test_use_cases.py -k "UC-O01 or UC-O03 or UC-R01 or UC-R02 or UC-R03 or UC-R04" -v` → 6 passed.
- Full suite green: `uv run pytest -x -q` → 631 passed, 17 skipped, 4 xfailed.
- Ruff lint + format clean on all 13 touched files.

---

*Phase: 04-llm-mechanic-generation*
*Completed: 2026-04-12*
