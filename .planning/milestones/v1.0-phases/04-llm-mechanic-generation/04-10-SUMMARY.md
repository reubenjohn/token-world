---
phase: 04-llm-mechanic-generation
plan: 10
subsystem: mechanic-authoring
tags: [seeds, resource, durability, currency, mech-17, mech-18, d-11, d-37, gap-mech29-deferred]
requires:
  - 04-01 (flat layout; Mechanic ABC; tags default)
  - 04-02 (validate-mechanic CLI; six-stage validation pipeline)
  - 04-03 (diagnostics sink — implicit, exercised via validate-mechanic)
  - 04-04 (integration harness + frozen matcher; not extended here)
  - 04-05 (authoring guide + _helpers.py convention)
  - 04-08 (pending_* convention precedent for actor-side staged action context; _refuse_with_narrative)
provides:
  - MECH17 degrade seed mechanic (voluntary; use-on-tool durability decrement; remove-on-zero)
  - MECH18 fungible_pay seed mechanic (voluntary; subset-sum exact-payment over held coin entities)
  - _helpers.py _subset_sum (backtracking DFS exact-sum subset selector — graduated to _helpers.py from inception so a future make_change mechanic for GAP-MECH29 reuses without a relocate-helper churn commit)
  - UC-R06 flipped yield -> pass (verb pay -> fungible_pay; pending_payment staged on alice)
  - UC-R05 stays blocked with refined rationale (GAP-ENG02 routing + threshold-flag-vs-removal-at-zero semantics mismatch documented inline)
  - VALIDATION rows 04-10-T1 / T2
affects:
  - src/token_world/mechanic/seeds/{degrade,fungible_pay}.py (2 new modules)
  - src/token_world/mechanic/seeds/_helpers.py (+_subset_sum)
  - tests/test_mechanic/test_seeds/test_{degrade,fungible_pay}.py (2 new test files; 35 new unit tests)
  - tests/test_mechanic/test_registry.py (TestSeedUniverse seed-id list bumped 21 -> 23)
  - .planning/use-cases/resource/UC-R05-degradation-over-time.md (yield -> blocked + multi-blocker rationale)
  - .planning/use-cases/resource/UC-R06-fungible-currency.md (yield -> pass + verb rewrite + pending_payment staging)
  - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md (rows T1/T2)
tech-stack:
  added: []
  patterns:
    - "Backtracking subset-sum graduated to _helpers.py from first use. Normally D-11 says graduate after >= 3 shared uses; we ship from _helpers.py because GAP-MECH29 (change-making) is explicitly deferred to Phase 7+ AND will reuse _subset_sum verbatim. Avoiding a future move-the-helper churn commit is worth the local D-11 deviation; the helper docstring names the second consumer to make the rationale auditable."
    - "Refusal-with-narrative on no-exact-subset (fungible_pay) keeps pending_payment in place rather than clearing it. This differs from the give/trade pattern (which clears pending_* on success AND on most refusals). Rationale: payment failures are commonly retry-with-different-amount situations (the agent learns it can't make 4 from {5,2}, then tries 5 instead). Clearing pending_payment would force the agent to re-stage on every retry, which the harness has no way to do without re-running the graph_builder. Leaving it in place is the Phase-4-friendly default."
    - "bool-is-int rejection: degrade.check explicitly rejects bool durability values (isinstance(durability, bool) sieve) so a typo durability=True doesn't slip through Python's bool-is-int relation. Mirrored in fungible_pay.check on amount and in _eligible_coins on denomination. Pattern is reusable for any mechanic that requires strict-int property values."
    - "Phase-4 GAP-ENG02 workaround for MECH18: actor.pending_payment={recipient, amount, kind} mirrors the 04-08 pending_* convention. Two new positional fields needed (amount, kind, on top of recipient) but the dict shape keeps the swap-in surface uniform with give and trade. Phase 5's ctx.claim slot replaces three reads in fungible_pay.apply without changing the public mechanic shape."
    - "_eligible_coins(ctx, actor, kind) inline helper inside fungible_pay rather than _helpers.py. Three reasons: (1) only fungible_pay reads kind-filtered held entities today; (2) the kind/subtype/fungible_kind dual lookup is fungible-specific bookkeeping, not a primitive; (3) D-11 graduates after >= 3 shared uses, and there is currently exactly one use. If a future inventory_filter or weighted_pick mechanic surfaces, it migrates to _helpers.py at that point."
key-files:
  created:
    - src/token_world/mechanic/seeds/degrade.py
    - src/token_world/mechanic/seeds/fungible_pay.py
    - tests/test_mechanic/test_seeds/test_degrade.py
    - tests/test_mechanic/test_seeds/test_fungible_pay.py
  modified:
    - src/token_world/mechanic/seeds/_helpers.py
    - tests/test_mechanic/test_registry.py
    - .planning/use-cases/resource/UC-R05-degradation-over-time.md
    - .planning/use-cases/resource/UC-R06-fungible-currency.md
    - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md
key-decisions:
  - "UC-R05 stays blocked, NOT flipped to pass via verb rewire. The plan's decision tree authorised either path; the call to keep blocked was driven by a structural assertion-vs-mechanic mismatch the plan did not anticipate. The third expected_observation asserts property_equals(sword, durability, 0) AND property_equals(sword, broken, true) on a still-existing sword node. The PLAN-specified degrade contract removes the node at durability <= 0, so honouring this UC's assertion semantics needs a wear+threshold mechanic shape (set broken=true at zero, remove only on a separate discard verb) — a Phase-5+ refinement. Combined with the GAP-ENG02 routing block (no instrument slot for verb=strike, target=dummy, instrument=sword), this UC is double-blocked and stays blocked. The full rationale is recorded as inline frontmatter comments on UC-R05 so future executors don't re-litigate the call."
  - "UC-R06 verb rewritten pay -> fungible_pay (Rule-2 deviation). Same precedent as 04-09's lift -> cooperate and open -> belief_update: the Phase-4 harness routes by verb -> mechanic.id and has no classifier; aligning the manifest's verb with the seed's id is the cleanest path to a passing assertion chain under the Phase-4 voluntary harness. Phase 5's classifier swaps it back to pay without further mechanic surgery."
  - "_subset_sum graduates to _helpers.py from first use, not after >= 3 (D-11 deviation). GAP-MECH29 (change-making — overpay + emit change-owed state) is explicitly deferred and will reuse _subset_sum verbatim; the future make_change mechanic is the second consumer that already justifies the helper's place in _helpers.py. Avoiding a later move-the-helper churn commit is worth the local D-11 deviation. The helper docstring names GAP-MECH29 + future change-making as the second consumer so the rationale is auditable."
  - "Refusal-on-no-subset leaves pending_payment in place rather than clearing it. Differs from give/trade where pending_* clears on most refusals. Rationale: payment failures are commonly retry-with-a-different-amount scenarios; clearing pending_payment would force the agent to re-stage every retry, which the Phase-4 harness has no way to do without re-running graph_builder. The Phase-4-friendly default is leave-in-place; Phase-5 retry semantics can revisit."
  - "Strict-int sieve via explicit isinstance(x, bool) rejection. Python's bool-is-int relation means isinstance(True, int) is True, so a typo durability=True or amount=False would pass a naive check. Both mechanics explicitly reject bool values; the pattern is documented in degrade.py and fungible_pay.py for future seed authors to reuse."
patterns-established:
  - "Strict-int property sieve: ``isinstance(x, int) and not isinstance(x, bool)`` for any mechanic that requires a numeric property to be a true int. Adopted by degrade (durability), fungible_pay (amount, denomination)."
  - "pending_payment={recipient, amount, kind} convention as Phase-4 GAP-ENG02 workaround for fungible mechanics (mirror of 04-08 pending_give/pending_trade). Three fields instead of two, but same dict-on-actor shape; same swap-in surface for Phase 5's ctx.claim."
  - "Helper graduation rule local exception: when a future deferred mechanic is named in the deferred-items list AND that mechanic will provably reuse the helper, graduate from inception to avoid a churn commit at the deferral's resolution. Documented in _helpers.py docstring for the helper."
  - "Refusal-but-keep-pending: refuse_with_narrative without clearing the pending_* dict on the actor when the refusal is retry-friendly (no-exact-subset, recipient gone but pending intent still valid). Distinguishes from give/trade's clear-on-refusal, which assumes the action's intent is consumed by attempting it."
requirements-completed:
  - MECH-03

# Metrics
duration: ~9min
completed: 2026-04-13
---

# Phase 04 Plan 10: Resource Seed Cluster (degrade + fungible_pay) Summary

**Two resource seed mechanics (MECH17 degrade, MECH18 fungible_pay) plus a backtracking _subset_sum helper; UC-R06 flipped yield -> pass; UC-R05 stays blocked with a refined dual-blocker rationale documented inline; full suite green at 722/16s/1xf.**

## Performance

- **Duration:** ~9 min (3 task commits — RED test commit, GREEN feat commit, Task-2 manifest+VALIDATION+ruff-format commit folded together)
- **Started:** 2026-04-13T08:01Z
- **Completed:** 2026-04-13T08:10Z
- **Tasks:** 2 (per PLAN.md)
- **Files created:** 4 (2 seeds + 2 test files)
- **Files modified:** 5 (_helpers.py, test_registry.py, 2 UC manifests, VALIDATION.md)

## Accomplishments

- Shipped MECH17 (degrade) — use-on-tool durability decrement with remove-on-zero. Bool-is-int sieve on durability and usage_cost; defaults to usage_cost=1 when the property is absent or malformed.
- Shipped MECH18 (fungible_pay) — subset-sum-driven exact-change payment over held coin entities. Reads actor.pending_payment={recipient, amount, kind}; transfers a subset whose denominations sum exactly to amount; refuses with a GAP-MECH29 narrative (change-making deferred to Phase 7+) when no exact subset exists.
- Added `_subset_sum(values, target)` helper to `_helpers.py` from first use (D-11 deviation rationale documented in helper docstring + key-decisions).
- 35 new unit tests (15 degrade + 20 fungible_pay including 7 _subset_sum cases). All pass.
- Both mechanics validate clean through the six-stage pipeline (`uv run token-world validate-mechanic`).
- UC-R06 flipped to pass via verb rewrite (pay -> fungible_pay) + pending_payment staging in graph_builder.
- UC-R05 stays blocked with a 25-line inline rationale comment in frontmatter explaining the dual-blocker (GAP-ENG02 routing + threshold-flag-vs-removal-at-zero semantics mismatch).
- VALIDATION.md updated with rows 04-10-T1 (mechanic+helper unit) and 04-10-T2 (UC-R05/R06 integration), each marked `passing`.
- `tests/test_mechanic/test_registry.py::TestSeedUniverse.test_scan_discovers_seeds` bumped from 21 -> 23 ids (degrade + fungible_pay inserted alphabetically).
- Full pytest suite: **722 passed, 16 skipped, 1 xfailed** (was 686/15s/3xf at start of plan).

## Task Commits

1. **Task 1 RED: failing tests for degrade + fungible_pay** — `0e68474` (test)
2. **Task 1 GREEN: MECH17 degrade + MECH18 fungible_pay seeds + _subset_sum helper** — `d4623ab` (feat)
3. **Task 2: UC-R06 flip + UC-R05 blocked rationale + VALIDATION rows + ruff format** — `aece9a2` (feat; folds the post-format E501 fix in fungible_pay.py and the ruff format pass over the three new files)

No separate REFACTOR commit — the GREEN cut was already minimal-and-clean; the only post-GREEN edit was the E501 fix on a single check() reasons-list line, which folded naturally into the Task 2 commit.

## Files Created/Modified

### Created

- `src/token_world/mechanic/seeds/degrade.py` — MECH17. ~110 lines including module docstring documenting UC-R05's blocked rationale inline so future readers find it from the seed itself.
- `src/token_world/mechanic/seeds/fungible_pay.py` — MECH18. ~180 lines including the GAP-ENG02 / GAP-MECH29 / coin_received-tally rationale.
- `tests/test_mechanic/test_seeds/test_degrade.py` — 15 tests across metadata, check, apply (including a three-swing chain that mirrors UC-R05's intent end-to-end).
- `tests/test_mechanic/test_seeds/test_fungible_pay.py` — 20 tests across the helper (7), metadata (3), check (5), apply (5: UC-R06 happy path with the conservation invariant, single-coin exact, no-subset refusal w/ GAP-MECH29 narrative, recipient missing, kind filtering).

### Modified

- `src/token_world/mechanic/seeds/_helpers.py` — `_subset_sum(values, target)` added between `_count_holds` and `_refuse_with_narrative`. Backtracking DFS; quick-rejects target <= 0 / empty list / sum(values) < target. Helper docstring names GAP-MECH29 / future change-making as the second consumer.
- `tests/test_mechanic/test_registry.py` — `TestSeedUniverse.test_scan_discovers_seeds` ids bumped 21 -> 23 (degrade + fungible_pay inserted alphabetically).
- `.planning/use-cases/resource/UC-R05-degradation-over-time.md` — `expected_outcome: yield -> blocked` plus a 25-line inline frontmatter comment block explaining the dual-blocker decision (GAP-ENG02 routing + threshold-flag vs removal-at-zero) so future executors don't re-litigate.
- `.planning/use-cases/resource/UC-R06-fungible-currency.md` — `expected_outcome: yield -> pass`. Verb `pay -> fungible_pay`. `pending_payment={recipient, amount, kind}` pre-staged on alice in graph_builder. Inline comments name the GAP-ENG02 swap-in surface for Phase 5.
- `.planning/phases/04-llm-mechanic-generation/04-VALIDATION.md` — rows 04-10-T1 / 04-10-T2.

## Decisions Made

See `key-decisions` frontmatter for the five binding decisions (UC-R05 stays blocked, UC-R06 verb rewire, _subset_sum graduates from first use, refusal-but-keep-pending for fungible_pay, strict-int sieve via bool-is-int rejection).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] UC-R05 was authorised as either pass-or-blocked by the plan's decision tree, but the structural mismatch between PLAN's degrade contract and UC-R05's assertion semantics ruled out the pass branch**

- **Found during:** Task 2 (decision-tree application)
- **Issue:** The plan's `must_haves` listed two paths for UC-R05: "use-on-tool form flips to `pass` if the manifest targets that action" or "ambient decay form remains `blocked`". Actually applying the decision tree surfaced a third state the plan didn't anticipate: UC-R05's assertion chain (the third expected_observation expects `property_equals(sword, durability, 0)` AND `property_equals(sword, broken, true)` on a still-existing sword node) is incompatible with PLAN's degrade-with-removal-at-zero contract. After three swings starting from durability=3, the third swing reduces 1->0 and removes the node — both assertions fail because the sword is gone. Honouring this UC needs a different mechanic shape (wear+threshold: set broken=true at zero, remove only on a separate discard verb).
- **Fix:** Kept `expected_outcome: blocked` and added a 25-line inline frontmatter comment documenting the dual-blocker (GAP-ENG02 routing + threshold-flag-vs-removal semantics) so future executors don't re-litigate the call. The plan's `must_haves` row about UC-R05 is honoured ("ambient-decay form remains `blocked`") but the rationale is now precise rather than aspirational.
- **Files modified:** `.planning/use-cases/resource/UC-R05-degradation-over-time.md`
- **Verification:** `uv run pytest tests/test_integration/test_use_cases.py -k "UC-R05" -v -rs` → SKIPPED with reason "UC-R05: blocked by framework gap". (Generic skip reason because UC-R05's existing engine-layer gap is `defer` severity, not `address-now`; the inline frontmatter comment is the load-bearing rationale for the call.)
- **Committed in:** `aece9a2` (folded into Task 2)

**2. [Rule 2 - Missing Critical] UC-R06's classified verb `pay` had no Phase-4 mechanic and would not route through fungible_pay without a verb rewrite**

- **Found during:** Task 2 (UC-R06 flip verification)
- **Issue:** The Phase-4 harness routes by `verb -> mechanic.id`. UC-R06's manifest classified verb was `pay`; the seed mechanic id is `fungible_pay`. Without the verb rewrite, UC-R06 would skip with "no matching mechanic" and stay at yield. Same pattern as 04-09's `lift -> cooperate` and `open -> belief_update`.
- **Fix:** Rewrote the classified verb `pay -> fungible_pay`. Inline comment names the rationale and the Phase-5 swap-back point.
- **Files modified:** `.planning/use-cases/resource/UC-R06-fungible-currency.md`
- **Verification:** `uv run pytest tests/test_integration/test_use_cases.py -k "UC-R06" -v` → PASSED.
- **Committed in:** `aece9a2` (folded into Task 2)

**3. [Rule 2 - Missing Critical] UC-R06 manifest did not pre-stage actor.pending_payment on the graph_builder**

- **Found during:** Task 2 (UC-R06 flip verification, before adding the staging)
- **Issue:** GAP-ENG02 means the harness has no third positional slot for the recipient/amount/kind that fungible_pay's `apply` needs. The check would refuse with "actor has no pending_payment dict" and `any_mechanic_fired` would stay False, failing the `expected_outcome: pass` branch.
- **Fix:** Pre-staged `alice.pending_payment = {"recipient": "shopkeeper", "amount": 7, "kind": "coin"}` in the graph_builder. Mirror of 04-08's `pending_give` / `pending_trade` and 04-09's `utterance` conventions. Inline comment names the GAP-ENG02 workaround so Phase 5's `ctx.claim` swap-in surface is greppable.
- **Files modified:** `.planning/use-cases/resource/UC-R06-fungible-currency.md`
- **Verification:** Same as deviation 2 — `uv run pytest tests/test_integration/test_use_cases.py -k "UC-R06" -v` → PASSED.
- **Committed in:** `aece9a2` (folded into Task 2)

**4. [Rule 1 - Bug] fungible_pay.py E501 (line too long, 102 chars) on the "pending_payment missing positive int amount" check.reasons line**

- **Found during:** Task 2 phase-gate (`uv run ruff check`)
- **Issue:** A `CheckResult(passed=False, reasons=["..."])` line wrapped beyond 100 characters because the message string was inlined.
- **Fix:** Split the call across three lines (`passed=False,`, `reasons=[...],`, `)`). After ruff format ran, the multi-line constants and a few test method signatures were also folded back onto single lines (the formatter's preference). Net change is cosmetic.
- **Files modified:** `src/token_world/mechanic/seeds/fungible_pay.py`, plus format-only diffs to `tests/test_mechanic/test_seeds/test_degrade.py` and `tests/test_mechanic/test_seeds/test_fungible_pay.py`.
- **Verification:** `uv run ruff check src/token_world/mechanic/seeds/ tests/test_mechanic/test_seeds/test_degrade.py tests/test_mechanic/test_seeds/test_fungible_pay.py tests/test_mechanic/test_registry.py` → "All checks passed!"; `uv run ruff format --check` → "6 files already formatted".
- **Committed in:** `aece9a2` (folded into Task 2)

**5. [Local D-11 deviation] _subset_sum graduated to _helpers.py from first use, not after >= 3 shared uses**

- **Found during:** Task 1 GREEN authoring
- **Issue:** D-11 says helpers graduate to `_helpers.py` only after >= 3 shared uses across seeds. `_subset_sum` has exactly one user today (fungible_pay). Strict adherence would put it inside fungible_pay.py.
- **Fix:** Graduated from first use anyway. Rationale: GAP-MECH29 (change-making — overpay + emit change-owed state) is explicitly deferred to Phase 7+ in the GAP-ANALYSIS, and the future `make_change` mechanic that closes it will reuse `_subset_sum` verbatim. Putting the helper in `_helpers.py` from inception avoids a later move-the-helper churn commit when GAP-MECH29 is addressed. The helper docstring names GAP-MECH29 / future change-making as the second consumer so the rationale is auditable in code.
- **Files modified:** `src/token_world/mechanic/seeds/_helpers.py`
- **Verification:** Tests for the helper live in `test_fungible_pay.py::TestSubsetSum` (7 cases); `uv run token-world validate-mechanic src/token_world/mechanic/seeds/fungible_pay.py` → PASS (the import from `_helpers` is on the allowed-imports list per D-14).
- **Committed in:** `d4623ab` (folded into the GREEN commit)

---

**Total deviations:** 5 — 3 Rule-2 missing-critical (one each for UC-R05 rationale refinement, UC-R06 verb rewrite, UC-R06 pending_payment staging), 1 Rule-1 bug (E501 line length), 1 local D-11 deviation (helper graduation timing).
**Impact on plan:** All five deviations were either pre-anticipated by PLAN.md (UC-R06 verb rewrite is the same pattern as 04-09; UC-R05 decision tree explicitly authorised either path; the E501 is a routine post-GREEN cleanup) or were structural-mismatch discoveries that the plan's decision tree didn't anticipate (UC-R05 dual-blocker; D-11 graduation timing). No scope creep beyond the plan's `files_modified` list.

## Authentication Gates

None.

## Issues Encountered

None — the plan executed cleanly. The only friction was discovering the UC-R05 assertion-vs-degrade-contract mismatch during Task 2, which the inline frontmatter rationale resolves without code changes.

## Threat Flags

No new threat surface introduced. The plan's declared T-04-AST-BYPASS is accepted (mitigated by the validation pipeline, which ran green against both new seeds). Both mechanics use only the public MechanicContext API + standard library typing; no networkx/pickle/eval/exec/__import__ calls; AST stage 2 of the validate-mechanic pipeline confirms.

## Known Stubs

None. UC-R05 stays at `expected_outcome: blocked` per the decision tree, which is the manifest's authoritative tri-state outcome, not a stub mechanic; no new framework-gap-stub mechanics added in this plan.

## Next Phase Readiness

- 23 seed mechanics now ship under `src/token_world/mechanic/seeds/` (was 21 at start of plan). One more cluster planned for 04-11 (environmental family per D-37).
- `_subset_sum` is in place for GAP-MECH29 (change-making) when Phase 7+ ships the `make_change` mechanic.
- UC-R05 is the second use case (after UC-R02's earlier "shape already aligned" annotation in 04-08) where the manifest's assertion semantics ruled the decision tree more strictly than the plan anticipated. Pattern worth watching: whenever a UC's assertion chain references both "node still exists" AND "property X" on a node a Phase-4 mechanic would remove, the UC stays blocked even when routing is solvable. Documented inline in UC-R05 so future executors find the precedent.
- Phase-5 swap-in surfaces for this plan are concentrated:
  - GAP-ENG02 (no `claim` slot on MechanicContext): 1 swap site in fungible_pay.apply (the `pending_payment` dict read), 1 in UC-R06 graph_builder (the staging line), 1 in UC-R05 (the `instrument` field that doesn't route today).
  - GAP-MECH29 (change-making): 1 future-mechanic file (`make_change.py`) reusing `_subset_sum` plus a "change-owed" emission step.
  - Threshold + discard refinement for UC-R05: 1 future mechanic (`wear` or refined `degrade`) that decouples broken-flag from node-removal.

## Self-Check: PASSED

- All 4 created files present on disk:
  - `src/token_world/mechanic/seeds/degrade.py` — present
  - `src/token_world/mechanic/seeds/fungible_pay.py` — present
  - `tests/test_mechanic/test_seeds/test_degrade.py` — present
  - `tests/test_mechanic/test_seeds/test_fungible_pay.py` — present
- All 3 commits resolvable on branch:
  - `0e68474` (test) — present
  - `d4623ab` (feat) — present
  - `aece9a2` (feat) — present
- Phase gates:
  - `uv run pytest -q` → **722 passed, 16 skipped, 1 xfailed** (was 686/15s/3xf at plan start; +35 unit tests = 36 net-new pass, +1 net-new skip from UC-R06 yield -> pass and UC-R05 yield -> blocked offsetting; the xfail count went down because UC-R06 was previously yield-with-no-fire = xfail and is now pass).
  - `uv run pytest tests/test_integration/test_use_cases.py -k "UC-R05 or UC-R06" -v` → 1 passed (R06), 1 skipped (R05).
  - `uv run ruff check` on all 6 files this plan touched → clean.
  - `uv run ruff format --check` on all 6 files this plan touched → clean.
  - `uv run token-world validate-mechanic src/token_world/mechanic/seeds/{degrade,fungible_pay}.py` → both PASS through all six pipeline stages.
- Acceptance greps:
  - `grep -n "GAP-MECH29\|cannot make exact change\|no exact subset" src/token_world/mechanic/seeds/fungible_pay.py` → 5 matches (acceptance criterion: >= 1).
  - `grep -c "04-10-T" .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md` → 2 (acceptance criterion: >= 2).
  - `grep -E "expected_outcome: pass" .planning/use-cases/resource/UC-R06-fungible-currency.md` → 1 match.
  - `grep -E "expected_outcome: blocked" .planning/use-cases/resource/UC-R05-degradation-over-time.md` → 1 match.

---

*Phase: 04-llm-mechanic-generation*
*Completed: 2026-04-13*
