---
quick_task: 260413-syz-write-daydream-seed-mechanic-integration
plan: 01
subsystem: phase-07-attention-and-consciousness
tags: [seeds, composability, long-running-actions, verification]
requires:
  - LongRunningHook infrastructure (Phase 07-04)
  - ctx.begin_long_action helper (Phase 07-03)
  - sleep.py seed as structural template
provides:
  - DaydreamMechanic — bounded 4-tick cognitive long-running action
  - 4-seed composability demonstration (physiological / cognitive / chemical / movement)
  - Literal satisfaction of ROADMAP Phase 7 SC2 (daydreaming now exists as named)
affects:
  - Phase 07 verification status (human_needed → passed)
  - MechanicRegistry seed-discovery enumeration (one new seed ID)
tech_stack:
  added: []
  patterns:
    - seed mechanic file = pure data + ctx.begin_long_action call
    - graceful-degradation location fallback (Q8): omit threshold rather than raise
    - substitution→addition pattern for unblocking verification overrides
key_files:
  created:
    - src/token_world/mechanic/seeds/daydream.py
    - tests/test_engine/test_daydream_integration.py
  modified:
    - .planning/phases/07-attention-and-consciousness/07-VERIFICATION.md
    - tests/test_mechanic/test_registry.py
decisions:
  - "Daydream added as 4th seed (not replacement for drunk): converts D-18 substitution into addition, satisfies SC2 literally AND strengthens composability proof"
  - "turns_total=4 chosen to distinguish bounded-cognitive case from sleep's bounded-physiological case (8 ticks) and drunk's indefinite case (None)"
  - "noise threshold at 0.4 (vs sleep's 0.7): shallower cognitive state is interrupted more easily — data-level variation on the same infrastructure"
  - "attention_state suppress=[ambient_sound, peripheral_vision]: different from sleep's [visual_detail, smell] — different sensory modalities suit the cognitive drift state"
  - "Body header Status: line also flipped to 'passed' alongside frontmatter (Rule 2: body/frontmatter must be internally consistent)"
metrics:
  tasks_total: 3
  commits: 4
  duration_minutes: 8
  tests_added: 5
  test_count_delta: "771 → 776 (Phase 7 scope); 1644 → 1645 (repo-wide)"
  completed: 2026-04-14
---

# Quick Task 260413-syz: Write Daydream Seed Mechanic + Integration Summary

Added `daydream` as the FOURTH seed mechanic in the Phase 7 composability family, converting the D-18 "drunk substituted for daydreaming" override into a pure addition and flipping 07-VERIFICATION.md from `human_needed` to `passed` with 6/6 must-haves verified. One generic interruption-threshold pattern now demonstrably handles four distinct state categories: physiological (sleep), cognitive (daydream), chemical (drunk), movement (autopilot_travel).

## Files Created

### `src/token_world/mechanic/seeds/daydream.py` (115 lines)

Pure-data seed mechanic mirroring `sleep.py`'s shape:

- `id="daydream"`, `voluntary=True`, `tags=["cognitive", "long_running"]`
- `watches()` returns `[VerbMatcher(verb="daydream")]`
- `check()`: actor must exist; no existing `current_long_action` (refuses with `mechanic_check_failed` if already in an LRA)
- `apply()`:
  - Sets `actor.is_daydreaming = True`
  - Starts 4-tick LRA via `ctx.begin_long_action`:
    - `action_text="daydreaming"`, `turns_total=4`
    - Thresholds: `{room}.noise_level > 0.4` (if resolvable) and `actor.health < 0.2` (always)
    - `attention_state.suppress=["ambient_sound", "peripheral_vision"]`, `boost=["noise_level"]`
    - `clear_on_end={"is_daydreaming": False}`
- Graceful-degradation location fallback (Q8): omits noise threshold if `actor.location` is not a string or the room node is absent — does NOT raise.

### `tests/test_engine/test_daydream_integration.py` (327 lines, 5 tests)

Deterministic end-to-end integration tests using `MockAnthropicClient` and the `shutil.copy`-into-tmp_universe seed-install precedent from `test_sleep_integration.py`:

1. **`test_daydream_happy_path_completes_after_4_ticks`** — Full lifecycle. Alice in quiet study (noise=0.2), issues `"daydream"` → LRA with turns_total=4, turns_elapsed=0, is_daydreaming=True, both thresholds present. 3 continuation ticks advance turns_elapsed to 1,2,3; 4th completion clears the LRA and fires `clear_on_end` (is_daydreaming=False).
2. **`test_daydream_threshold_fires_at_noise_above_0_4_not_at_0_3`** — Proves strict `>` semantics (matches drunk's `sobriety > 0.8` pattern). noise=0.3 no fire; noise=0.4 no fire (strictly greater, not ≥); noise=0.5 fires.
3. **`test_daydream_attention_state_suppresses_ambient_sound_during_continuation`** — `ambient_sound` and `peripheral_vision` both absent from `result.projected_state["study"]["properties"]` during continuation, proving the new suppression keys flow through `VisibilityProjector._apply_attention_state()`.
4. **`test_daydream_cancelled_by_new_agent_action`** — D-11 implicit cancellation: issuing `"look around"` mid-daydream clears the LRA before the pipeline runs; `result.kind in ("refused", "ok", "yielded")`.
5. **`test_daydream_continuation_does_not_call_classifier`** — D-07 proof: `run_tick(None)` during daydream makes zero Haiku calls. Using `MockAnthropicClient([])` as a tripwire — any classifier call would raise `RuntimeError("MockAnthropicClient ran out of responses")`.

## Files Modified

### `.planning/phases/07-attention-and-consciousness/07-VERIFICATION.md`

Frontmatter:
- `status: human_needed` → `passed`
- `score: 5/6` → `6/6 must-haves verified`
- `overrides_applied: 0` → `1`
- `must_haves_verified: 5` → `6`
- Removed `human_verification:` block (4 lines)
- Added `overrides:` block with entry documenting the substitution→addition conversion (accepted_by: developer, accepted_at: 2026-04-13T21:30:00Z)

Body:
- Truth #5 status: `PARTIAL` → `VERIFIED`; evidence rewritten to cite daydream.py and the 4-seed composability
- Score line: `5/6 (1 pending human confirmation)` → `6/6 truths verified`
- Required Artifacts table: added 2 new VERIFIED rows for `daydream.py` and `test_daydream_integration.py`
- Composition-Pattern Check #6 (Variation lives in data): added `daydream` bullet between `sleep` and `autopilot_travel`; annotated sleep with `noise>0.7`
- Requirements Coverage "Note on daydreaming": replaced with resolved-2026-04-13 paragraph explaining the addition
- Removed entire `### Human Verification Required` section (subsection + YAML template)
- Gaps Summary: replaced pending-item sentence with closed-items sentence
- Body header `**Status:** human_needed` → `passed` (consistency with frontmatter; see Deviations)

Timestamp `2026-04-13T20:08:32Z` preserved — this is an update, not a re-verification.

### `tests/test_mechanic/test_registry.py`

Added `"daydream"` to the expected sorted seed-ID list in `test_scan_discovers_seeds` (inserted between `"craft"` and `"decay_tick"`). See Deviations §1.

## Test Count Delta

| Scope | Before | After |
|-------|-------:|------:|
| Phase 7 (`tests/test_engine/ tests/test_mechanic/test_seeds/`) | 771 | 776 |
| Full repo | 1644 | 1645 |

Full repo run: **1645 passed, 14 skipped, 36 deselected** in 42.80s.

## Commits

| Hash | Task | Message |
|------|------|---------|
| 5efac0f | 1 | `feat(seeds): add daydream mechanic — 4th composability demonstrator` |
| 8eff1a7 | 2 | `test(seeds): add daydream integration tests — 5 deterministic scenarios` |
| a396447 | 3 | `docs(phase-07): flip VERIFICATION.md to passed after daydream addition` |
| 2a45e55 | deviation | `fix(tests): add daydream to registry seed-discovery expected list` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Registry seed-discovery test needed update**

- **Found during:** Final overall verification gate (full-repo `uv run pytest -q`)
- **Issue:** `tests/test_mechanic/test_registry.py::TestSeedUniverse::test_scan_discovers_seeds` enumerates the complete sorted list of seed IDs discovered by `MechanicRegistry`. Adding `daydream.py` to `src/token_world/mechanic/seeds/` changed the discovered set, which is exactly the invariant the test was designed to catch.
- **Fix:** Inserted `"daydream"` in sorted position between `"craft"` and `"decay_tick"` in the expected list.
- **Files modified:** `tests/test_mechanic/test_registry.py` (+1 line)
- **Commit:** 2a45e55
- **Scope rationale:** The CRITICAL_FILE_SCOPE_GUARDRAIL forbids `tests/test_regression/` and `tests/test_mechanic/test_seeds/`, but `tests/test_mechanic/test_registry.py` is outside those forbidden paths. This test *directly measures the contents of seeds/*, so its expected list must grow with any new seed — it would be strictly incorrect to leave it stale.

**2. [Rule 2 - Missing critical functionality] Body header Status line was inconsistent with frontmatter**

- **Found during:** Task 3 sanity-read after applying all planned edits
- **Issue:** The `<verification_update>` block specified frontmatter `status: human_needed → passed` but did not explicitly mention the body header line `**Status:** human_needed` at line 27. Leaving the body header reading `human_needed` would contradict the frontmatter and make the file internally inconsistent (violating CLAUDE.md Operating Principle #6 "Ground truth obsession").
- **Fix:** Updated body header line from `**Status:** human_needed` to `**Status:** passed`.
- **Files modified:** `.planning/phases/07-attention-and-consciousness/07-VERIFICATION.md` (1 line)
- **Commit:** a396447 (folded into the Task 3 commit since it is the same logical change)

### Authentication Gates

None.

### Architectural Changes Asked About

None. All deviations were Rule 1/2 auto-fixes within scope.

## Success Criteria Verification

| SC | Description | Status | Evidence |
|----|-------------|--------|----------|
| SC1 | `daydream.py` mirrors sleep.py shape; locked-design values (turns_total=4, noise>0.4, suppress=[ambient_sound, peripheral_vision], is_daydreaming) | PASS | `src/token_world/mechanic/seeds/daydream.py` — 115 lines, ruff clean, mypy clean |
| SC2 | `test_daydream_integration.py` with ≥5 passing deterministic tests | PASS | 5/5 passing: happy path, strict-> threshold at 0.4, attention suppression, D-11 cancellation, no classifier on continuation |
| SC3 | 07-VERIFICATION.md flipped: `status: passed`, `must_haves_verified: 6`, `overrides_applied: 1` with override block; Truth #5 VERIFIED; human_verification section removed | PASS | All automated grep checks passed; manual Read confirms file structure |
| SC4 | No regression in pre-existing 771 Phase 7 tests | PASS | 776/776 pass (771 pre-existing + 5 new) |
| SC5 | ROADMAP Phase 7 SC2 satisfied literally | PASS | `daydream` now exists as a named seed mechanic alongside sleep and autopilot_travel; composability demonstrated across 4 state categories |

## The Substitution→Addition Framing

The original D-18 auto-mode decision substituted `drunk` for `daydreaming` because drunk demonstrates `turns_total=None` (indefinite duration) — a more expressive composability axis than daydreaming alone would have shown. This was a defensible decision, but left SC2 pending human acceptance because ROADMAP literally names "daydreaming".

By **adding** daydream (keeping drunk as the 3rd seed demonstrating turns_total=None), both points are now satisfied:

- **Literal:** ROADMAP SC2 names "sleep, daydreaming, autopilot travel" — all three now exist as named seeds.
- **Spirit:** Composability is proven more strongly. One pattern handles four distinct state categories via data-only variation:
  - `sleep`: bounded physiological (turns_total=8)
  - `daydream`: bounded cognitive (turns_total=4)
  - `autopilot_travel`: bounded movement (turns_total=path_len)
  - `drunk`: indefinite chemical (turns_total=None)

The framing in the new `overrides:` block records this as a resolved-by-addition override rather than a substitution that was rubber-stamped.

## Self-Check: PASSED

Verified via file-exists and git-log checks:

- `src/token_world/mechanic/seeds/daydream.py` — FOUND
- `tests/test_engine/test_daydream_integration.py` — FOUND
- `.planning/phases/07-attention-and-consciousness/07-VERIFICATION.md` — MODIFIED (confirmed via grep checks above)
- Commit 5efac0f — FOUND (git log)
- Commit 8eff1a7 — FOUND (git log)
- Commit a396447 — FOUND (git log)
- Commit 2a45e55 — FOUND (git log)

Full repo test gate: 1645 passed / 14 skipped / 36 deselected. Zero regressions.
