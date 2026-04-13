---
phase: 07-attention-and-consciousness
reviewed: 2026-04-13T21:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - src/token_world/engine/long_running.py
  - src/token_world/engine/long_running_hook.py
  - src/token_world/engine/engine.py
  - src/token_world/engine/visibility.py
  - src/token_world/engine/observer.py
  - src/token_world/engine/models.py
  - src/token_world/engine/summary_writer.py
  - src/token_world/engine/__init__.py
  - src/token_world/mechanic/context.py
  - src/token_world/mechanic/seeds/sleep.py
  - src/token_world/mechanic/seeds/autopilot_travel.py
  - src/token_world/mechanic/seeds/autopilot_advance.py
  - src/token_world/mechanic/seeds/drunk.py
  - src/token_world/mechanic/seeds/sober_up.py
  - src/token_world/playtest/runner.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-04-13T21:00:00Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Phase 07 delivers the composable interruption-threshold pattern across sleep, autopilot travel, and drunk state mechanics. The core infrastructure — `LongRunningAction`/`ThresholdSpec`/`ThresholdEvaluator` dataclasses, `LongRunningHook`, engine routing (`run_tick(str|None)`), and `VisibilityProjector.project_for(attention_state=)` — is well-designed and correctly implemented. Serialization round-trips are correct, the insta-cancel pitfall is properly mitigated, BFS has a depth cap preventing infinite loops, and the `random` module is absent from all seed mechanics (only `ctx.rng` is available, though none of the seed mechanics here use it).

Three warnings were found, all relating to state-flag lifecycle: the `is_sleeping`, `is_traveling`, and `is_drunk` flags set at LRA start are never cleared when the LRA ends (interrupt or natural completion). This causes stale state visible to mechanics and the Observer. Three info items cover a redundant exception clause, a fragile `assert` in production code, and missing idempotency in drunk LRA startup.

## Warnings

### WR-01: `is_sleeping`, `is_traveling`, and `is_drunk` flags never cleared on LRA termination

**Files:**
- `src/token_world/mechanic/seeds/sleep.py:93` — sets `is_sleeping=True`
- `src/token_world/mechanic/seeds/autopilot_travel.py:164` — sets `is_traveling=True`
- `src/token_world/mechanic/seeds/drunk.py:89` — sets `is_drunk=True`
- `src/token_world/engine/long_running_hook.py` — clears `current_long_action` on interrupt/complete but sets no state flags

**Issue:** Each seed mechanic sets a state flag on the actor node (`is_sleeping`, `is_traveling`, `is_drunk`) when starting the LRA. When the LRA ends — either by threshold interruption or natural completion — `LongRunningHook` clears `current_long_action` from the graph, but does not clear these companion flags. After waking from sleep, the actor retains `is_sleeping=True`; after arriving at a destination, `is_traveling=True` persists; after sobering up, `is_drunk=True` persists indefinitely (and `sober_up.py` uses `is_drunk` as its own gate — line 43 — meaning a sobered-up actor will never have `sober_up` run again, but `is_drunk=True` still pollutes projections and any mechanic that checks it).

The `sober_up` companion mechanic is the sharpest case: it relies on `is_drunk` to find actors that need recovery (line 43: `if not props.get("is_drunk"): continue`). Once the drunk LRA fires its sobriety threshold, `current_long_action` is cleared, but `is_drunk` stays `True`. On the next passive sweep `sober_up` still sees `is_drunk=True` and will keep raising `sobriety_level` past 1.0 (clamped by `min(1.0,...)`, so no crash — but the mechanic fires unnecessarily). The Observer will also see `is_drunk=True` in projections and may produce incoherent narratives.

**Fix:** The hook should clear state flags when it clears the LRA. The cleanest approach is to have `LongRunningHook` accept an optional set of "on-clear" property mutations from the LRA payload. However, a simpler v1 fix is to handle cleanup inside each mechanic pair by checking the mechanic's `action_text` in hook results — or by having the hook read a `clear_on_end: {"is_sleeping": false}` subkey from the LRA payload and apply those mutations before returning. The minimal per-mechanic fix:

`sleep.py` — no cleanup mechanic is needed because `is_sleeping` is only a semantic flag and has no mechanical consequences in current code. However for correctness:

```python
# In LongRunningHook.process(), after graph.set(actor, _LRA_PROPERTY, None):
# Read payload's clear_on_end dict and apply each property.
clear_on_end = payload.get("clear_on_end", {})
for prop, val in clear_on_end.items():
    graph.set(actor, prop, val)
```

Then each mechanic passes `clear_on_end` in its payload:

```python
# sleep.py begin_long_action call:
attention_state={...},
# Add to payload implicitly via begin_long_action helper:
# (requires extending begin_long_action to accept extra payload keys, or:)

# Alternatively, pass clear_on_end inside attention_state's sibling key.
# Simplest: extend begin_long_action signature with clear_on_end:
ctx.begin_long_action(
    action_text="sleeping",
    turns_total=8,
    thresholds=thresholds,
    attention_state={...},
    clear_on_end={"is_sleeping": False},
)
```

At minimum, `is_drunk=True` must be cleared since `sober_up` uses it as a gate.

---

### WR-02: `assert` used for control flow in production path in `autopilot_travel.py`

**File:** `src/token_world/mechanic/seeds/autopilot_travel.py:155-156`

**Issue:** `apply()` contains `assert path is not None and len(path) >= 2`. In production, Python assertions can be disabled with `-O` / `PYTHONOPTIMIZE=1`. If `check()` and `apply()` are ever called with a different `ctx` snapshot (e.g., graph mutated between calls in a multi-agent v2 scenario, or by a buggy test harness), this `assert` silently becomes unreachable and `path[1:]` on `None` raises an `AttributeError` rather than a clear error. More concretely, `apply()` re-runs `_find_path` indirectly via `actor_props["location"]` — if `location` is `None` at apply time (race or bug), `_find_path(ctx, None, ctx.target)` returns `None` and the assertion is the only guard.

**Fix:** Replace `assert` with an explicit guard that raises `RuntimeError` (or returns an empty list for graceful degradation):

```python
path = _find_path(ctx, current_location, ctx.target)
if path is None or len(path) < 2:
    # check() should have caught this; defensive guard for production
    return []  # or raise RuntimeError(f"autopilot_travel: no path from {current_location} to {ctx.target}")
```

---

### WR-03: `_handle_long_running_tick` reads `current_long_action` before the hook, but the hook also reads it — two reads that could diverge if graph is mutated between them

**File:** `src/token_world/engine/engine.py:718`

**Issue:** `_handle_long_running_tick` reads `lra = self._graph.query(actor, "current_long_action") or {}` to extract `attention_state` for the projection call (step 1), then passes the graph to `LongRunningHook.process()` which independently reads `lra` again (step 2). In v1's single-agent synchronous tick loop there is no concurrent mutation so this is safe. However the two reads create a logical inconsistency: if the hook's read returns a different dict than the engine's pre-projection read (e.g., future passive mechanic runs before the hook), the `attention_state` used for projection would not match the LRA being evaluated. This is a latent TOCTOU pattern.

Additionally, the `or {}` fallback on line 718 means that if `current_long_action` is `None` (just cleared by a mechanic in the same tick), the engine continues into `_handle_long_running_tick` with an empty `lra` dict. The hook then returns `HookResult.inactive()` — causing `hook_result.observation` to be `None`, which then hits `observation=hook_result.observation or ""` at line 827, returning an empty observation to the caller. The `PlaytestRunner` would store an empty string in memory, which is confusing.

This path is guarded by `has_active_long_action()` at the top of `run_tick`, but a mechanic could theoretically clear the LRA in the same tick (e.g., via an involuntary mechanic that fires before `_handle_long_running_tick` is called — though the current code does not show such a mechanic). The risk is low but the empty-observation fallback is worth documenting.

**Fix:** Add a guard in `_handle_long_running_tick` for the empty-lra case:

```python
lra = self._graph.query(actor, "current_long_action") or {}
if not lra:
    # LRA was cleared between has_active_long_action check and here
    logger.warning("LRA disappeared between has_active_long_action check and _handle_long_running_tick for actor=%s", actor)
    # Fall through to hook; hook will return HookResult.inactive() with empty observation
```

---

## Info

### IN-01: Redundant `KeyError` in `except (KeyError, Exception)` in `long_running_hook.py`

**File:** `src/token_world/engine/long_running_hook.py:116`

**Issue:** `except (KeyError, Exception)` is redundant — `Exception` is a supertype of `KeyError`, so `KeyError` is never reached as a distinct handler. The clause is equivalent to `except Exception`.

**Fix:**
```python
except Exception:
    return HookResult.inactive()
```

---

### IN-02: `sober_up` does not clear `is_drunk` flag when sobriety reaches 1.0

**File:** `src/token_world/mechanic/seeds/sober_up.py:71-76`

**Issue:** `sober_up.apply()` only sets `sobriety_level`; it never clears `is_drunk=False` even when `new_sobriety` reaches 1.0. The LongRunningHook clears `current_long_action` when `sobriety_level > 0.8` fires, but the sober_up mechanic continues running every tick afterward (since `is_drunk=True` still passes the `_find_drunk_actors_with_room_to_recover` filter and `sobriety < 1.0` is already blocked — but `is_drunk` flag remains `True`). This is already flagged in WR-01 as the highest-impact instance; noted here as a separate actionable item in `sober_up.py` specifically.

**Fix:** Add a sobriety-capped cleanup mutation:
```python
new_sobriety = min(1.0, current_sobriety + RECOVERY_RATE)
mutations.append(ctx.set(actor_id, "sobriety_level", new_sobriety))
if new_sobriety >= 1.0:
    mutations.append(ctx.set(actor_id, "is_drunk", False))
```

---

### IN-03: `autopilot_advance` silently accepts `next_index=0` which indicates a corrupt LRA payload

**File:** `src/token_world/mechanic/seeds/autopilot_advance.py:131-135`

**Issue:** `autopilot_travel` always initializes `next_index=1`, so `next_index=0` in an active traveling LRA would indicate a corrupt or manually crafted payload. When `next_index=0`, the mechanic computes `prev_room = None` (correct guard) and moves actor to `route[0]` — the starting room — which is a no-op location update. No error is logged. The behavior is silent and confusing (the actor "moves" to where they already are on the first advance).

**Fix:** Add a minimum guard:
```python
if next_index == 0:
    logger.warning(
        "autopilot_advance: next_index=0 for actor %s; skipping (likely corrupt LRA payload)",
        actor_id,
    )
    continue
```

---

_Reviewed: 2026-04-13T21:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
