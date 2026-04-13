---
phase: 05-simulation-engine
reviewed: 2026-04-13T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - src/token_world/engine/observer.py
  - src/token_world/engine/conservation.py
  - src/token_world/engine/summary_writer.py
  - src/token_world/engine/engine.py
  - src/token_world/engine/__init__.py
  - src/token_world/mcp_server.py
  - src/token_world/universe/scaffold.py
  - src/token_world/universe/templates/__init__.py
  - src/token_world/universe/templates/conservation_yaml.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 05 Wave 2-4: Code Review Report

**Reviewed:** 2026-04-13
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Wave 2-4 delivered the Observer, ConservationChecker, TickSummaryWriter, SimulationEngine
orchestrator, and MCP tool wiring. The code is well-structured and closely follows the
design decisions in 05-CONTEXT.md. No security vulnerabilities or data-loss risks were
found. The D-15 grounding phrase is present on every LLM-calling code path; fallback
paths correctly bypass the LLM. The atomic write infra (`_atomic_write_json` with fsync
before `os.replace`) is reused correctly. Rate constants are module-level. Path-traversal
defence is implemented in `_require_universe_path`.

Four warnings were found: a silent exception-swallowing pattern in the passive sweep, a
`TypeError` raised inside the `with open_tick` block without recording it in diagnostics,
a missing `graph.save()` after the conservation rollback in `_handle_execute`, and a
potential MCP information disclosure when `exc` wraps internal paths or graph state in
`-32603` messages. Three info-level items are also noted.

---

## Warnings

### WR-01: Passive sweep swallows mechanic exceptions silently — no diagnostics entry

**File:** `src/token_world/engine/engine.py:685-689`

**Issue:** When a sweep mechanic's `apply()` raises, the engine logs a warning but
`continue`s without appending a `TraceNode` to `sweep_nodes`. This means:

1. The exception is invisible in diagnostics (no trace entry, no mutation record).
2. The tick summary shows fewer sweep mechanics than actually attempted.
3. An operator debugging a broken involuntary mechanic gets no structured artifact to
   inspect — only a module-level log line they may never see.

In contrast, the `check().passed == False` branch at line 674 *does* create a `TraceNode`
with empty mutations, so there is precedent for recording failed attempts.

```python
# Current (line 685-689)
try:
    mutations = mech.apply(sweep_ctx)
except Exception as exc:
    logger.warning("Passive sweep mechanic %s raised: %s", mech.id, exc)
    continue
```

**Fix:** Append a `TraceNode` with the failure recorded before continuing, mirroring the
`check` failure branch:

```python
try:
    mutations = mech.apply(sweep_ctx)
except Exception as exc:
    logger.warning("Passive sweep mechanic %s raised: %s", mech.id, exc)
    sweep_nodes.append(
        TraceNode(
            mechanic_id=mech.id,
            actor=sentinel,
            target=sentinel,
            check_result=check,
            mutations=[],
        )
    )
    continue
```

This keeps sweep exceptions observable in the tick summary and diagnostics without
changing the tick's outcome.

---

### WR-02: `TypeError` for unhandled Decision type escapes `open_tick` without a status record

**File:** `src/token_world/engine/engine.py:303-304`

**Issue:** The `else: raise TypeError(...)` branch at line 304 is inside the
`with self._diagnostics.open_tick(next_tick)` block, but no `tick_ctx.set_summary(status="error", ...)` is called before the raise. The `open_tick` finalizer still runs (it's a `finally`), but it writes whatever `set_summary` last recorded — which at that point is nothing (no `set_summary` call has happened on these paths). The diagnostics `summary.json` will contain an empty/default status while an unhandled exception propagates to the caller.

This is a latent issue: the branch is unreachable today (the type system covers all
Decision variants), but a future Decision subtype could trigger it.

**Fix:** Add a `set_summary` call before the raise:

```python
else:
    tick_ctx.set_summary(status="error", error=f"Unhandled decision type: {type(decision).__name__}")
    raise TypeError(f"Unhandled Decision type: {type(decision).__name__}")
```

---

### WR-03: Conservation rollback in `_handle_execute` doesn't call `graph.save()` after restore

**File:** `src/token_world/engine/engine.py:381, 427`

**Issue:** Both conservation violation branches call `self._graph.restore(pre_tick_snapshot_id)` but do not follow with `self._graph.save()`. From `knowledge_graph.py:471`, `restore()` internally calls `self.save()` — so in-process state is correct. However, MCP callers in `mcp_server.py` call `graph.save()` *after* `engine.run_tick()` returns (line 181). If `restore()` already committed the restored state to the DB, the post-run `graph.save()` will overwrite it with the restored (correct) state again — which is idempotent and fine.

The actual risk is narrower: within `run_tick`, after `self._graph.restore(...)`, the
`self._graph._current_tick` is reset to the snapshot's tick (the pre-tick value). The
`tick_id_str` used for the refused `TickResult` and tick summary reflects `next_tick`
(the incremented value). So the graph is at `pre_tick` but the refused result carries
`tick_id = next_tick`. On the **next** `run_tick` call, `self._graph.current_tick + 1`
will recompute `next_tick` from the restored snapshot value, colliding with the refused
tick's `tick_id` unless the caller increments past it.

In practice `restore()` does call `save()`, but the tick counter is not reset to
`pre_tick - 1` — it stays at the snapshot's tick. This means the refused-tick ID is
orphaned but the next tick ID will be `pre_tick + 1`, which equals the refused tick ID.
Two consecutive ticks could receive the same `tick_id` string if the pattern is:
run_tick → conservation violation → rollback → next run_tick.

**Fix:** After `self._graph.restore(pre_tick_snapshot_id)`, explicitly reset the tick
counter to `pre_tick_snapshot_tick - 1` so the next `run_tick` allocates a fresh
monotonic ID:

```python
self._graph.restore(pre_tick_snapshot_id)
# Reset tick to pre-tick value so next run_tick allocates a fresh monotonic ID.
# restore() set current_tick to the snapshot's tick (pre_tick - 1 conceptually);
# we need it one below so the next +1 produces a non-colliding tick.
self._graph.set_tick(next_tick - 1)
```

Alternatively, verify that `graph.restore()` always resets `current_tick` to a value
strictly less than `next_tick` and document the invariant. Either way, a test covering
"two consecutive ticks after a conservation rollback get distinct tick IDs" should be
added.

---

### WR-04: MCP `-32603` handler leaks internal exception message text to JSON-RPC output

**File:** `src/token_world/mcp_server.py:309-314`

**Issue:** The broad `except Exception` handler at line 309 returns:

```python
return _jsonrpc_error(req_id, -32603, f"Internal error: {exc}")
```

`str(exc)` on common Python exceptions can contain file-system paths (e.g., from
`FileNotFoundError`, `PermissionError`), snapshot IDs, or graph internals. These are
sent to the MCP client (the operator's LLM harness) in the JSON-RPC response body.

For this hobby project's threat model the risk is low (the operator is also the user),
but the full traceback goes to stderr (correctly) while the message body reveals more
than a generic "internal error" should. Contrast with `-32602` paths which use explicit
parameter names.

**Fix:** Return a fixed generic message for `-32603`; leave the full exception detail on
stderr only:

```python
except Exception as exc:
    import traceback
    sys.stderr.write(traceback.format_exc())
    # Do not echo exc details to the client — full trace is on stderr.
    return _jsonrpc_error(req_id, -32603, "Internal error")
```

If operator-side debugging is important, the tick's `diagnostics/summary.json` already
captures error state. The MCP client only needs to know "it failed."

---

## Info

### IN-01: `observer.py` — `full_prompt` variable constructed but not passed to LLM call

**File:** `src/token_world/engine/observer.py:162-163`

**Issue:** Lines 162-163 build `full_prompt = _SYSTEM_PROMPT + "\n\n---\n\n" + user_prompt`
and then immediately pass `_SYSTEM_PROMPT` and `user_prompt` separately to
`client.messages.create(system=..., messages=[...])`. The `full_prompt` variable is only
used as the `prompt` argument to `tick_diag_ctx.write_observation(...)` at line 183.
The name `full_prompt` implies it's the complete LLM input, which is correct for
diagnostics logging purposes, but the variable is never passed to the API call.

This is not a bug — the Anthropic API correctly receives `system=` and `messages=`
separately, and the diagnostics log correctly shows the combined prompt. However the
variable name is misleading: it is the **diagnostics prompt string**, not the LLM input.

**Fix:** Rename for clarity:

```python
diag_prompt = _SYSTEM_PROMPT + "\n\n---\n\n" + user_prompt
...
tick_diag_ctx.write_observation(prompt=diag_prompt, ...)
```

---

### IN-02: `summary_writer.py` — `_flatten_trace_mutations` is a near-duplicate of `observer.py:_flatten_mutations`

**File:** `src/token_world/engine/summary_writer.py:64-81` and
`src/token_world/engine/observer.py:55-64`

**Issue:** Both modules implement a trace-tree walker that collects all mutations. The
implementations differ only in that `observer.py` uses recursion and `summary_writer.py`
uses an iterative stack (which is better — avoids Python recursion depth). There is also
a third copy in `engine.py:_flatten_mutations` (lines 741-751).

This is not a correctness issue today because all three are equivalent, but divergence
risk is real: if `TraceNode` gains a new children structure, all three must be updated
in sync.

**Fix:** Promote the iterative implementation from `summary_writer.py` to a single
canonical function in `token_world.mechanic.trace` (where `ExecutionTrace` and
`TraceNode` live) and import it from both `observer.py` and `engine.py`. The refactor
is low-risk because `trace.py` already imports nothing from the engine layer.

---

### IN-03: `_ClassifierDiagnosticsAdapter._maybe_flush` flushes only when `stage == "classification"` — other stage names silently no-op

**File:** `src/token_world/engine/engine.py:97-110`

**Issue:** `_maybe_flush` only calls `write_classification` when `stage == "classification"`. If the Wave 1 `classifier.py` ever calls `write_prompt(stage="something_else", ...)`, the flush is silently skipped and the diagnostics entry is lost. There is no warning or assertion.

Currently `classifier.py` uses `stage="classification"` consistently, so this is dormant. But because the adapter was introduced as a compatibility shim (not a first-class API), any future modification to `classifier.py`'s stage name will produce a silent diagnostics gap.

**Fix:** Add an assertion or `logger.warning` in `_maybe_flush` when a response+parsed pair exists but the stage name doesn't match "classification":

```python
if response or parsed:
    if stage != "classification":
        logger.warning(
            "_ClassifierDiagnosticsAdapter: unexpected stage %r — "
            "diagnostics not flushed; check classifier.py stage names",
            stage,
        )
    elif hasattr(self._ctx, "write_classification"):
        self._ctx.write_classification(prompt=prompt, response=response, parsed=parsed)
```

---

## Specific Watch-For Responses

1. **Observer grounding phrase on all paths** — PASS. `_SYSTEM_PROMPT` (lines 37-49)
   contains the D-15 literal phrase `"use only facts that appear in the provided state"`.
   Refusal and empty-projection paths bypass the LLM entirely and return pre-composed
   strings; they never reach `client.messages.create`. All three paths write diagnostics.

2. **Conservation snapshot atomicity** — MOSTLY PASS, with WR-03 above. The snapshot is
   taken before execute at line 221. `graph.restore()` calls `save()` internally making
   the rollback durable. The tick-ID collision risk after rollback is the residual issue.

3. **Passive sweep recursion** — PASS. Sweep mechanics fire at most once per sweep call
   per the `for mech in self._registry.involuntary_mechanics()` loop. Sweep mutations are
   collected in `sweep_nodes` after the loop and are NOT fed back into another sweep;
   the function returns immediately. No recursion path exists.

4. **Diagnostics adapter duplication** — PASS. `_ClassifierDiagnosticsAdapter` is a thin
   bridge (32 lines) with no duplicated logic. It buffers up to 3 keys per stage and
   delegates via `__getattr__`. No classifier logic was copied.

5. **MCP YieldSignal handling** — PASS. `_tool_resume_tick` (line 189) checks
   `result.yield_signal is not None` and serialises via `to_json()`. Yield path is
   correctly handled. Execute and Refuse paths use `result.observation` and
   `result.refusal_reason` respectively.

6. **MCP rollback path-traversal** — PASS. `_require_universe_path` rejects `..` segments
   at line 123. `snapshot_id` is integer-coerced with an explicit error on non-integer
   input. Missing `universe.db` returns `-32602` not `-32603`. No numeric bounds check
   on `snapshot_id` (arbitrary large int), but this is mitigated by `graph.restore()`
   raising `ValueError` on unknown IDs, which routes to `-32603`.

7. **TickSummaryWriter fsync before rename** — PASS. `_atomic_write_json` calls
   `os.fsync(f.fileno())` before `os.replace()` (verified in
   `src/token_world/mechanic/diagnostics.py:70`).

8. **USD cost rate constants** — PASS. All four rate constants are module-level in
   `summary_writer.py:36-39` (`_HAIKU_INPUT_PER_MTOK`, `_HAIKU_OUTPUT_PER_MTOK`,
   `_SONNET_INPUT_PER_MTOK`, `_SONNET_OUTPUT_PER_MTOK`) with a comment directing
   operators to adjust them in source with test verification.

9. **engine.py modifying Wave 1 artifacts** — PASS. No monkeypatching. `_ClassifierDiagnosticsAdapter`
   wraps `tick_ctx` without modifying `classifier.py` or any Wave 1 module.

---

_Reviewed: 2026-04-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
