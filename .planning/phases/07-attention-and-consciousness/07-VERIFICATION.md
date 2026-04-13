---
phase: 07-attention-and-consciousness
verified: 2026-04-13T20:08:32Z
status: human_needed
score: 5/6 must-haves verified
overrides_applied: 0
requirement_coverage:
  - id: SIM-09
    status: complete
    evidence: "src/token_world/engine/long_running.py, long_running_hook.py, engine.py:_handle_long_running_tick"
  - id: SIM-10
    status: complete
    evidence: "src/token_world/mechanic/seeds/sleep.py, autopilot_travel.py, drunk.py — all use ctx.begin_long_action via the same LongRunningHook infrastructure"
must_haves_verified: 5
must_haves_total: 6
human_verification:
  - test: "Confirm 'drunk' satisfies ROADMAP SC2 in place of 'daydreaming'"
    expected: "The spirit of SC2 (three different types sharing one infrastructure) is met; the literal name 'daydreaming' was substituted with 'drunk' per CONTEXT D-18 (auto-mode decision). Developer should confirm this substitution is acceptable."
    why_human: "D-18 is an auto-mode decision (no human reviewed the selection). The ROADMAP SC2 explicitly names 'daydreaming'; the implemented set is sleep + autopilot_travel + drunk. 'Drunk' demonstrates more (turns_total=None path) but is not daydreaming. Developer acceptance required."
---

# Phase 7: Attention & Consciousness — Verification Report

**Phase Goal:** Long-running actions and consciousness states use a single composable interruption threshold pattern, making the simulation feel temporally alive
**Verified:** 2026-04-13T20:08:32Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Long-running actions skip boring intermediate turns (continuation ticks emit static "time passes" template) | VERIFIED | `long_running_hook.py:31` — `_TIME_PASSES_TEMPLATE = "Time passes. You continue {action_text}."` returned on continuing path; engine calls `_handle_long_running_tick` when `action_text is None` |
| 2 | Engine only interrupts when significance exceeds attention threshold | VERIFIED | `ThresholdEvaluator.evaluate()` fires on first matching threshold; hook clears LRA and synthesises interruption narrative via `Observer.synthesize` with `interruption_context` dict |
| 3 | Sleep, autopilot travel, and drunk all use the same interruption threshold infrastructure (one `LongRunningAction` dataclass + one `LongRunningHook`) | VERIFIED | All three seed mechanics call `ctx.begin_long_action()` which writes `current_long_action` dict; hook reads same property regardless of mechanic identity |
| 4 | Agent traveling a long distance experiences compressed time with interruptions only for significant events | VERIFIED | `test_autopilot_integration.py` proves 4-room travel in 3 continuation ticks; attention_state suppresses `fine_detail`; hazard threshold interrupts when `hazard_level > 0.5` |
| 5 | Sleep, daydreaming, and autopilot travel all demonstrate composability per ROADMAP SC2 | PARTIAL | Sleep and autopilot_travel exist and use the pattern. 'Daydreaming' was substituted with 'drunk' per CONTEXT D-18 (auto-mode decision). 'Drunk' correctly uses the same infrastructure. **Human confirmation needed** — see Human Verification section. |
| 6 | Review-fix cycle closed all 3 warnings and 3 info items with TDD | VERIFIED | `07-REVIEW-FIX.md` status `all_fixed` (6/6); WR-01 adds `_apply_clear_on_end` to hook + `clear_on_end` param to all three mechanics; WR-02 replaces `assert` with explicit guard; WR-03 adds warning log for TOCTOU; IN-01/IN-02/IN-03 all fixed with regression tests; 771 tests pass |

**Score:** 5/6 truths verified (1 pending human confirmation)

### Deferred Items

None — all roadmap items for Phase 7 were addressed in this phase.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/token_world/engine/long_running.py` | `LongRunningAction`, `ThresholdSpec`, `ThresholdEvaluator` (D-15, D-23) | VERIFIED | 198 lines; all three classes present; frozen dataclasses; 6-operator dispatch; D-09 safe defaults |
| `src/token_world/engine/long_running_hook.py` | `LongRunningHook`, `HookResult` (D-15, D-20) | VERIFIED | 314 lines; `HookResult` frozen dataclass; `process()` advances turns_elapsed, evaluates, interrupts, synthesises; `_apply_clear_on_end` for WR-01 |
| `src/token_world/engine/visibility.py` | `VisibilityProjector.project_for(attention_state=None)` Stage 5 (D-12, D-15) | VERIFIED | `_apply_attention_state()` adds Stage 5; suppress removes keys; boost copies to `attention_boosted`; backward-compatible default `attention_state=None` |
| `src/token_world/mechanic/context.py` | `ctx.begin_long_action(...)` helper (D-15) | VERIFIED | `begin_long_action()` at line 286; accepts `action_text`, `turns_total`, `thresholds`, `attention_state`, `clear_on_end`; writes `current_long_action` dict via `kg.set` |
| `src/token_world/engine/engine.py` | `run_tick(str|None)` routing; `_handle_long_running_tick`; `has_active_long_action`; D-11 cancellation (D-07, D-11) | VERIFIED | Lines 245–840; `has_active_long_action()` at 226; LRA detection at 280; D-11 cancellation at 297; `_handle_long_running_tick` at 695 |
| `src/token_world/mechanic/seeds/sleep.py` | Bounded (turns_total=8), noise/health thresholds, attention_state, clear_on_end | VERIFIED | 105 lines; `turns_total=8`; two thresholds (health and room noise); attention suppress/boost; `clear_on_end={"is_sleeping": False}` |
| `src/token_world/mechanic/seeds/autopilot_travel.py` | BFS path, bounded (turns_total=path_len), hazard thresholds, attention_state | VERIFIED | 190 lines; BFS depth-capped at 32; hazard_level threshold per room; 2-step payload augment for route/next_index; `clear_on_end={"is_traveling": False}` via augment |
| `src/token_world/mechanic/seeds/autopilot_advance.py` | Passive TickMatcher advances location each tick | VERIFIED | 165 lines; `TickMatcher()`; `voluntary=False`; advances `location` + moves `type=location` edge; increments `next_index`; `next_index=0` guard (IN-03) |
| `src/token_world/mechanic/seeds/drunk.py` | Indefinite (turns_total=None), sobriety threshold, attention_state, clear_on_end | VERIFIED | 104 lines; `turns_total=None` (D-16); `sobriety_level > 0.8` threshold; suppress fine_detail/social_nuance; `clear_on_end={"is_drunk": False}` |
| `src/token_world/mechanic/seeds/sober_up.py` | Passive TickMatcher raises sobriety 0.1/tick; clears is_drunk at 1.0 | VERIFIED | 81 lines; `TickMatcher()`; `RECOVERY_RATE=0.1`; `if new_sobriety >= 1.0: mutations.append(ctx.set(actor_id, "is_drunk", False))` (IN-02 fix) |
| `src/token_world/playtest/runner.py` | LRA-aware: passes `action=None` for continuation ticks | VERIFIED | Lines 121–131; `engine.has_active_long_action(agent_id)` check; sets `action=None`; `action_for_memory="[long_running_continuation]"` marker |
| `tests/test_engine/test_long_running.py` | Unit tests for primitives | VERIFIED | File exists; 41 tests covering all 6 operators, serialisation, safe-default error paths |
| `tests/test_engine/test_long_running_hook.py` | Hook tests including clear_on_end (WR-01) | VERIFIED | File exists; covers interrupt/completion/continuing + clear_on_end paths |
| `tests/test_engine/test_autopilot_integration.py` | SC3 — compressed-time travel integration test | VERIFIED | 5 scenarios: full 3-tick travel, hazard interruption, attention_state suppression, D-11 cancellation, D-17 tick summary |
| `tests/test_engine/test_sleep_integration.py` | Sleep integration test | VERIFIED | File exists |
| `tests/test_engine/test_drunk_integration.py` | Drunk integration test (6-tick sober cycle, D-16 indefinite) | VERIFIED | File exists; 6 deterministic scenarios |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `engine.run_tick(None, actor)` | `_handle_long_running_tick` | `has_active_long_action()` check at line 280 | WIRED | Action_text=None + active LRA → skip classify entirely |
| `_handle_long_running_tick` | `VisibilityProjector.project_for(attention_state=)` | Line 736 — reads payload's `attention_state` then passes to projector | WIRED | Single projection call reused for hook threshold evaluation (D-09) |
| `LongRunningHook.process()` | `ThresholdEvaluator.evaluate()` | `long_running_hook.py:141` — direct call | WIRED | Evaluates thresholds against projection dict |
| `LongRunningHook.process()` → interrupt | `Observer.synthesize(interruption_context=)` | `_synthesise_interruption()` at line 234 | WIRED | Builds stub `ExecutionTrace`, passes `interruption_context` dict with `interrupted_by` and `long_action` |
| `engine` D-11 cancellation | `kg.set(actor, "current_long_action", None)` | Line 297 when real action_text provided while LRA active | WIRED | Clears LRA, then falls through to normal classify/match/execute pipeline |
| `ctx.begin_long_action()` | `kg.set(actor, "current_long_action", stored)` | `context.py:352` | WIRED | All three seed mechanics use this; graph is ground truth (D-02) |
| `LongRunningHook._apply_clear_on_end()` | `kg.set(actor, prop, val)` for each `clear_on_end` entry | `long_running_hook.py:220–232` | WIRED | Fires on both interrupt and completion paths (WR-01 fix) |
| `AutopilotAdvanceMechanic` (passive) | `AutopilotTravelMechanic` LRA state via graph | Reads `current_long_action.payload.route/next_index`, writes `actor.location` | WIRED | No direct import; graph is the coupling medium (D-01 composition) |
| `SoberUpMechanic` (passive) | `DrunkMechanic` LRA state via graph | Reads `actor.is_drunk`, writes `actor.sobriety_level` | WIRED | No direct import; LongRunningHook fires sobriety threshold next tick |
| `PlaytestRunner.run()` | `engine.has_active_long_action(agent_id)` | `runner.py:121` — `getattr(engine, "has_active_long_action", None)` | WIRED | Skips `agent.run_turn()` when LRA active; passes `None` to `engine.run_tick` |
| Tick summary writer | `long_running_action` field (D-17) | `summary_writer.py:109` accepts kwarg; engine passes at lines 820, 832 | WIRED | Schema field includes `active`, `turns_elapsed`, `turns_total`, `threshold_fired`, `interrupted` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `LongRunningHook.process()` | `lra` (current_long_action dict) | `graph.query(actor, "current_long_action")` | Yes — written by `ctx.begin_long_action()` in seed mechanic `apply()` | FLOWING |
| `ThresholdEvaluator.evaluate()` | `projection` dict | `VisibilityProjector.project_for(actor, attention_state)` | Yes — reads graph nodes via `graph.query(node_id)` | FLOWING |
| `VisibilityProjector._apply_attention_state()` | `attention_state` | `lra["payload"]["attention_state"]` read in engine before projector call | Yes — written by `ctx.begin_long_action(attention_state=...)` | FLOWING |
| `_apply_clear_on_end()` | `clear_on_end` | `payload.get("clear_on_end")` in hook | Yes — written by seed mechanics via `begin_long_action(clear_on_end=...)` | FLOWING |
| `SoberUpMechanic.apply()` | `sobriety_level` | `ctx.query_node(actor_id)["sobriety_level"]` | Yes — written by `DrunkMechanic.apply()` | FLOWING |
| `AutopilotAdvanceMechanic.apply()` | `route`, `next_index` | `lra["payload"]["route"/"next_index"]` | Yes — written by `autopilot_travel.apply()` 2-step augment | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 771 Phase 7 tests pass | `uv run pytest tests/test_engine/ tests/test_mechanic/test_seeds/ -x -q` | 771 passed in 4.24s | PASS |
| `ThresholdEvaluator` exported from public API | `grep "ThresholdEvaluator" src/token_world/engine/__init__.py` | Lines 24 and 56 | PASS |
| `LongRunningHook`, `HookResult` exported | `grep "LongRunningHook\|HookResult" src/token_world/engine/__init__.py` | Lines 27, 53, 55 | PASS |
| `clear_on_end` present in all three seed mechanics | `grep -n "clear_on_end" seeds/drunk.py seeds/sleep.py seeds/autopilot_travel.py` | All three have `clear_on_end` entries | PASS |
| `assert` removed from `autopilot_travel.apply()` (WR-02) | `grep "assert" src/token_world/mechanic/seeds/autopilot_travel.py` | No match | PASS |
| TOCTOU guard in `_handle_long_running_tick` (WR-03) | `grep "LRA disappeared" src/token_world/engine/engine.py` | Line 723 | PASS |

### Composition-Pattern Check (SC2 / D-01 Proof)

**Claim:** One generic pattern handles sleep, autopilot travel, and drunk with no bespoke per-mechanic logic in the engine.

**Evidence:**

1. **Engine hook is pattern-agnostic.** `LongRunningHook.process()` reads `current_long_action` from graph and operates identically regardless of which mechanic started the LRA. There is no `if action_text == "sleeping"` or `if action_text.startswith("traveling")` in `long_running_hook.py`.

2. **Engine routing is pattern-agnostic.** `engine.run_tick()` only checks `has_active_long_action()` (is the property set and a dict?). It does not inspect the `action_text` field of the LRA.

3. **`ThresholdEvaluator` is property-path agnostic.** It evaluates any `"node_id.prop_name"` against the projection. `noise_level`, `hazard_level`, `sobriety_level` are all resolved identically.

4. **All three mechanics use the same API surface:** `ctx.begin_long_action(action_text, turns_total, thresholds, attention_state, clear_on_end)`. The mechanic provides values; the infrastructure provides behaviour.

5. **Passive companions (autopilot_advance, sober_up) use no private engine APIs.** They are plain `TickMatcher` mechanics that read/write graph properties — the same mechanism as any other mechanic.

6. **Variation lives in data, not code:**
   - `sleep`: `turns_total=8`, `attention_state={suppress: [visual_detail, smell]}`
   - `autopilot_travel`: `turns_total=path_len`, thresholds per-room
   - `drunk`: `turns_total=None` (indefinite), `attention_state={suppress: [fine_detail, social_nuance]}`

**Verdict:** D-01 ("composition over specialization") is fully realized. The engine has no special-case code paths for any consciousness state.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| SIM-09 | 07-01 through 07-04 | Action duration and attention threshold — long-running actions skip boring intermediate turns; engine only interrupts when significance exceeds agent's current attention level | SATISFIED | `LongRunningAction` (D-02), `ThresholdEvaluator` (D-03), `LongRunningHook` (D-06), engine continuation path (D-07), D-11 cancellation, D-17 tick summary field — all implemented and tested |
| SIM-10 | 07-05 through 07-07 | Attention/consciousness as a reusable mechanic pattern — sleep, daydreaming, drunkenness, autopilot all use the same interruption threshold infrastructure | SATISFIED | Three seed mechanics (sleep, autopilot_travel, drunk) all use `ctx.begin_long_action()` and `LongRunningHook` without bespoke engine code; `VisibilityProjector.project_for(attention_state=)` extension; composability proof above |

**Note on daydreaming:** REQUIREMENTS.md SIM-10 lists "sleep, daydreaming, drunkenness, autopilot" as examples. CONTEXT D-18 chose drunk over daydreaming as the third seed demonstrator. Drunk satisfies the *pattern* requirement (indefinite LRA, cognitive state, attention modulation) more completely than daydreaming would have (daydreaming would be a simpler bounded case). The requirement is substantively satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `long_running_hook.py:116` (pre-fix) | Redundant `KeyError` in `except (KeyError, Exception)` | Redundant | None — fixed in WR-01/IN-01 cycle; current code uses `except Exception:` |
| `autopilot_travel.py:155` (pre-fix) | `assert path is not None` in production | Fixed | Replaced with `if path is None or len(path) < 2: return []` (WR-02) |

No current anti-patterns remain in the codebase. All review findings were fixed.

### Human Verification Required

#### 1. ROADMAP SC2 — "daydreaming" substituted with "drunk"

**Test:** Review the three seed demonstrators against the ROADMAP SC2 literal wording
**Expected:** Developer confirms that `drunk` satisfies the intent of SC2 ("demonstrate the pattern's composability") in place of a daydreaming mechanic
**Why human:** CONTEXT D-18 was an auto-mode decision (no human in the loop). The ROADMAP SC2 explicitly names "daydreaming" as one of the three states. The implementation chose `drunk` instead because it demonstrates `turns_total=None` (indefinite duration), which is arguably more valuable for showing composability than a daydreaming mechanic would be (which would look similar to sleep). However, this substitution of a named roadmap deliverable requires explicit developer sign-off.

If the substitution is acceptable, add to this file's frontmatter:
```yaml
overrides:
  - must_have: "Sleep, daydreaming, and autopilot travel all use the same interruption threshold infrastructure"
    reason: "Drunk substituted for daydreaming per CONTEXT D-18 (auto-mode). Drunk demonstrates turns_total=None (indefinite) which shows more composability than daydreaming would. Both share identical infrastructure."
    accepted_by: "developer"
    accepted_at: "ISO timestamp"
```

### Gaps Summary

No functional gaps. All infrastructure is present, substantive, wired, and data flows correctly. All six review findings were fixed with TDD. 771 tests pass.

The single pending item is a roadmap naming deviation (daydreaming → drunk) requiring human acceptance, not a technical failure.

---

_Verified: 2026-04-13T20:08:32Z_
_Verifier: Claude (gsd-verifier)_
