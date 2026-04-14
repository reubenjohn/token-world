---
phase: 14-engine-polish-seed-corpus-hygiene
verified: 2026-04-14T00:00:00Z
status: passed
score: 4/4
overrides_applied: 0
---

# Phase 14: Engine Polish + Seed Corpus Hygiene — Verification Report

**Phase Goal:** Close the last small engine-truthfulness follow-ups, promote the five universe-agnostic mechanics the overnight run authored, and stop the seed script from silently deleting them on re-seed.
**Verified:** 2026-04-14
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | A refused tick's observation text contains the "You try, but" refuse wrapper exactly once | VERIFIED | `test_refusal_wrapper.py` — 9 tests pass including doubly-nested and parametrized variants; single `_WRAPPER_PREFIX = "You try, but "` constant in `refusal.py`; `_strip_wrapper()` collapses any nesting depth before `format_map` |
| 2   | A new universe ships with examine, pet, sharpen, hum, drop as framework-level seed mechanics — no authoring yield needed | VERIFIED | `test_seed_mechanics.py` — 11 tests pass (importability + mechanic interface for all 5; `test_keep_mechanics_contains_new_seeds` passes); all 5 `id` values confirmed (`drop.py:43 id = "drop"`) |
| 3   | A new universe spawned from seed script includes bench (weathered=True), chicken coop, and broken gate with hook properties | VERIFIED | `test_seed_starter.py` — 7 tests pass; `seed_starter_universe.py` confirmed: bench (`weathered=True`, `planks_intact=5`), chicken_coop (`chickens_inside=3`, `door_latched`, `eggs_today`, `feed_level`), broken_gate (`broken=True`, `latched=False`, `repair_progress=0.0`) |
| 4   | `--preserve-mechanics` leaves authored mechanics untouched; running without flag prints loud stderr warning naming files | VERIFIED | `--help` shows flag; `test_preserve_mechanics_skips_prune` + `test_without_preserve_mechanics_calls_prune` + `test_prune_prints_stderr_warning` all pass |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/token_world/engine/refusal.py` | Idempotent wrapper via `_strip_wrapper()` | VERIFIED | `_strip_wrapper` at line 44; applied to `format_map["reason"]` at line 79; single `_WRAPPER_PREFIX` constant |
| `tests/test_engine/test_refusal_wrapper.py` | 9 regression tests, all pass | VERIFIED | 9/9 pass including pre-wrapped, doubly-nested, parametrized variants |
| `src/token_world/mechanic/seeds/examine.py` | ExamineMechanic, id="examine" | VERIFIED | Importable; interface test passes |
| `src/token_world/mechanic/seeds/pet.py` | PetMechanic, id="pet" | VERIFIED | Importable; interface test passes |
| `src/token_world/mechanic/seeds/sharpen.py` | SharpenMechanic, id="sharpen" | VERIFIED | Importable; interface test passes |
| `src/token_world/mechanic/seeds/hum.py` | HumMechanic, id="hum" | VERIFIED | Importable; interface test passes |
| `src/token_world/mechanic/seeds/drop.py` | DropMechanic, id="drop" | VERIFIED | `id = "drop"` confirmed at line 43; importable; interface test passes |
| `tests/test_mechanic/test_seed_mechanics.py` | 11 tests covering all 5 mechanics + _KEEP_MECHANICS | VERIFIED | 11/11 pass |
| `scripts/seed_starter_universe.py` | bench/coop/gate entities + `--preserve-mechanics` flag | VERIFIED | All entities with hook properties present; argparse flag recognized |
| `tests/test_scripts/test_seed_starter.py` | 7 tests covering entities + both flag code paths | VERIFIED | 7/7 pass |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `refusal.py` → `_strip_wrapper` | `RefusalTemplate.render()` | Called on `format_map["reason"]` before `format_map()` | WIRED | Line 79 confirms application |
| `seeds/drop.py` | `_KEEP_MECHANICS` frozenset in `seed_starter_universe.py` | frozenset membership | WIRED | `test_keep_mechanics_contains_new_seeds` confirms all 5 new ids present |
| `seed_starter_universe.py` → `_prune_seed_mechanics` | `--preserve-mechanics` flag | `args.preserve_mechanics` → `preserve_mechanics` kwarg | WIRED | `test_preserve_mechanics_skips_prune` confirms bypass; `test_without_preserve_mechanics_calls_prune` confirms default path |
| `scaffold-mechanic` CLI | seed collision guard | `--id toss` (not "drop") | WIRED | `test_scaffold_mechanic.py` uses `--id toss`; docstring explains collision avoidance |

### SC-2 Drop-vs-Toss Finding

The PLAN asked for a "drop" verb mechanic; `drop.py` delivers `id = "drop"` as specified.

The "toss" name appears only in `test_scaffold_mechanic.py` — the scaffold collision-guard test was changed from `--id drop` to `--id toss` because `drop` is now a seed mechanic and the scaffold CLI correctly refuses to overwrite it. This is a correct fix, not a gap: the scaffold test needed a non-seed name, and "toss" is purely a test fixture ID. The seed mechanic itself is `id = "drop"` as the roadmap requires.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| REQ-V12-ENGINE-05 | 14-01 | Refused tick wrapper appears exactly once | SATISFIED | `_strip_wrapper()` + 9-test regression suite, all pass |
| REQ-V12-SEEDS-01 | 14-02, 14-03 | 5 seed mechanics + 3 hook entities | SATISFIED | 11 seed tests + 7 entity tests, all pass |
| REQ-V12-TOOLING-02 | 14-03 | `--preserve-mechanics` flag + loud warning | SATISFIED | 7 tests confirming both code paths |

### Anti-Patterns Found

None. Confirmed:
- No TODO/FIXME/placeholder text in modified files
- All 5 mechanics produce real graph mutations
- No hardcoded empty returns in seed mechanics or API routes
- Pre-existing traceability drift in `tests/test_meta/test_requirements_traceability.py` is out-of-scope, pre-dates this phase (documented in 14-02-SUMMARY.md), and does not affect phase 14 deliverables

### Full Test Suite

- Excluding the pre-existing `test_no_traceability_drift[active-milestone]` failure (pre-dates phase 14): **2000 passed, 14 skipped**
- Including it: 1 failed (pre-existing), 1533 passed before stop — expected and documented

### Human Verification Required

None — all success criteria are fully verifiable programmatically. No visual, real-time, or external-service dependencies.

### Gaps Summary

No gaps. All four success criteria are met with passing test suites and confirmed source-level wiring.

---

_Verified: 2026-04-14T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
