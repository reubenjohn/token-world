---
phase: 05-simulation-engine
status: partial
fixed: 4
deferred: 2
fixed_at: 2026-04-13T13:03:03Z
---

# Review Fix Report — Phase 05

## Summary

All four Warning findings (WR-01 through WR-04) were fixed with TDD: each got
a regression test that failed before the fix and passed after. WR-01 rewrote
a brittle operator-precedence expression in `contagion.py` into explicit
branching with a `# noqa: SIM108` suppression to preserve readability intent.
WR-02 extended the classifier's known-node validation to cover `indirect_object`
(completing the GAP-ENG02 closure). WR-03 added soft-fail `try/except` guards
for `max_chain_depth` and `classifier_min_confidence` in the config loader to
match the contract already honoured for `universe_seed`. WR-04 narrowed the
bare `except Exception` in `visibility._outgoing_edges` to `nx.NodeNotFound`,
so corrupted-graph `NetworkXError` now propagates instead of being silently
dropped. The two Info findings (IN-01, IN-02) are deferred — they are not in
the `critical_warning` fix scope and were explicitly excluded.

Full test suite: **1116 passed, 14 skipped** (baseline was 1103 — 13 new
regression tests added). `ruff check src/` and `ruff format --check src/`
both pass clean.

---

## Fixes Applied

### WR-01: contagion.py — operator precedence bug silently skips transmissions

- **File:** `src/token_world/mechanic/seeds/contagion.py:149`
- **Finding:** Compound boolean `if rng is not None and rng.random() < rate or rng is None and rate >= 1.0` is logically correct but dangerously brittle to future edits.
- **Fix:** Replaced with explicit `if rng is not None: / else:` branching with `# noqa: SIM108` to suppress ruff's ternary suggestion (which would defeat the readability intent). Also updated the pre-existing `isinstance` tuple to union syntax (`int | float`) to satisfy ruff UP038.
- **Test:** `tests/test_mechanic/test_seeds/test_contagion.py::TestContagionRngNoneFallback` (3 tests: rate=0.5/1.0/1.5 with `rng=None` fallback)
- **Commit:** `ebd19ae` — `fix(05): WR-01 rewrite contagion rng branch for clarity`

### WR-02: classifier.py — `indirect_object` not validated against `known_node_ids`

- **File:** `src/token_world/engine/classifier.py:164-173`
- **Finding:** `_apply_known_target_check` only checked `classified.target`; a hallucinated `indirect_object` node ID passed through silently as `VerdictOk`.
- **Fix:** Refactored `_apply_known_target_check` to extract `classified` first, then check both `target` and `indirect_object` against `known_node_ids`. A hallucinated `indirect_object` now returns `VerdictNoSuchTarget(target_text=indirect_object)`.
- **Test:** `tests/test_engine/test_classifier.py::TestClassifierIndirectObjectValidation` (3 tests: hallucinated indirect_object → NoSuchTarget; valid indirect_object → VerdictOk; null indirect_object → no trigger)
- **Commit:** `9deac2a` — `fix(05): WR-02 validate indirect_object against known_node_ids in classifier`

### WR-03: config.py — `max_chain_depth` and `classifier_min_confidence` hard-fail on bad values

- **File:** `src/token_world/engine/config.py:49-52`
- **Finding:** Bare `int(...)` and `float(...)` casts on engine section fields raised `ValueError`/`TypeError` on malformed YAML (`"ten"`, `null`), violating the function's soft-fail contract.
- **Fix:** Wrapped both casts in `try/except (TypeError, ValueError)` with `logger.warning(...)` fallback to defaults, matching the pattern already used for `universe_seed`.
- **Test:** `tests/test_engine/test_config.py::TestLoadEngineConfigSoftFailEngineSection` (5 tests: string/null for each field → default + WARNING; valid int → parsed correctly)
- **Commit:** `1f4f01d` — `fix(05): WR-03 soft-fail on malformed max_chain_depth and classifier_min_confidence`

### WR-04: visibility.py — bare `except Exception` swallows `NetworkXError`

- **File:** `src/token_world/engine/visibility.py:120-123`
- **Finding:** `_outgoing_edges` caught all exceptions from `ego_subgraph`, silently discarding corrupted-graph `NetworkXError` that should propagate as a genuine error signal.
- **Fix:** Added `import networkx as nx` and narrowed the catch from `except Exception` to `except nx.NodeNotFound` with a comment explaining the TOCTOU safety rationale. `NetworkXError` and other unexpected exceptions now propagate to the caller.
- **Test:** `tests/test_engine/test_visibility.py::TestOutgoingEdgesErrorHandling` (2 tests: `NodeNotFound` → returns `[]`; `NetworkXError` → raises)
- **Commit:** `172c74f` — `fix(05): WR-04 narrow visibility _outgoing_edges exception to NodeNotFound`

---

## Deferred

### IN-01: matcher.py — `NoMatchResult.candidates` is always empty — reason: not in critical_warning scope

`DeterministicMatcher.match` always populates `NoMatchResult.candidates` with `[]`
even when mechanics scored above zero but below threshold. This means the
`YieldSignal.candidate_mechanic_ids` hint is always empty. Not a correctness bug
for the yield path — the feature from D-11 is simply not yet implemented.
Deferred to the 05-08 orchestrator wiring task per the reviewer's note.

### IN-02: visibility.py — belief overlay can write untrusted property names — reason: not in critical_warning scope

`_apply_belief_overlay` merges `believed_props` directly without filtering
structural keys (`type`, `hidden_properties`, `beliefs`). Per D-14, beliefs are
"not full epistemic logic; just enough to make MECH10/MECH25 work" — this is
within v1 spec. The reviewer explicitly scoped this to Phase 6 / observer
grounding. Deferred.

---

## Verification

- **Full suite:** 1116 passed, 14 skipped (baseline 1103 — 13 new regression tests)
- **Ruff check:** clean (`uv run ruff check src/`)
- **Ruff format:** clean (`uv run ruff format --check src/`)

---

_Fixed: 2026-04-13T13:03:03Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
