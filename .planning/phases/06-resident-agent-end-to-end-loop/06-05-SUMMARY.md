---
phase: 06-resident-agent-end-to-end-loop
plan: "05"
subsystem: playtest
tags: [hash-registry, regression-trigger, judge, prompt-change-detection]
dependency_graph:
  requires:
    - 06-03  # regression suite at tests/test_regression/
    - 06-04  # PlaytestRunner with hash_check_fn hook
  provides:
    - PromptHashRegistry (compute/load/save/detect_changes/trigger_regression)
    - optional Sonnet judge pass (evaluate, build_transcript, prompt_hash)
    - CLI wiring: hash_check_fn + --judge flag
  affects:
    - src/token_world/cli.py (additive: hash_check_fn wiring + judge stub replacement)
    - src/token_world/engine/classifier.py (additive: system_prompt_text classmethod)
    - src/token_world/engine/observer.py (additive: system_prompt_text classmethod)
tech_stack:
  added: []
  patterns:
    - SHA-256 via hashlib for prompt-change detection
    - atomic write via _atomic_write_json for prompts.sha256.json
    - JSONL append pattern for regression-history.jsonl
    - subprocess.run with timeout=600 for regression trigger
    - Pydantic model_validate for report reconstruction in judge path
key_files:
  created:
    - src/token_world/playtest/hash_registry.py
    - src/token_world/playtest/judge.py
    - tests/test_playtest/test_hash_registry.py
    - tests/test_playtest/test_judge.py
  modified:
    - src/token_world/playtest/__init__.py
    - src/token_world/cli.py
    - src/token_world/engine/classifier.py
    - src/token_world/engine/observer.py
    - tests/test_playtest/test_runner.py
decisions:
  - "Regex for pytest summary parsing uses three independent patterns (passed/failed/duration) so each count is found regardless of ordering — SUMMARY_RE approach failed on 'N failed in Xs' (no passed group)"
  - "judge_evaluate imported at cli.py module level (not deferred import) so patch('token_world.cli.judge_evaluate') works in tests"
  - "runner.hash_check_fn assigned after PlaytestRunner construction (mutable dataclass) — no runner.py changes needed per extensibility contract"
metrics:
  duration: "~40 minutes"
  completed_date: "2026-04-13"
  tasks_completed: 4
  tasks_total: 4
  tests_added: 25
  files_created: 4
  files_modified: 5
---

# Phase 06 Plan 05: Prompt-Hash Registry + Auto-Regression Trigger + Optional Sonnet Judge Summary

SHA-256 prompt-hash registry (D-14), auto-regression trigger on hash change (D-15, AUTO-07), and optional Sonnet judge pass (D-13, TEST-04) — all wired into the playtest CLI via runner hook injection, zero modifications to runner.py.

## What Was Built

### (a) prompts.sha256.json Schema

Written to `<universe_dir>/prompts.sha256.json` on every `token-world playtest` run.

```json
{
  "classifier_system_prompt": "<64-char SHA-256 hex>",
  "observer_system_prompt":   "<64-char SHA-256 hex>",
  "agent_system_prompt":      "<64-char SHA-256 hex>",
  "updated_at":               "2026-04-13T10:00:00Z"
}
```

- Only hashes stored, never raw prompt text (D-14 privacy).
- Written atomically via `_atomic_write_json`.
- `updated_at` is stripped by `PromptHashRegistry.load()` — callers only see hash dicts.

### (b) regression-history.jsonl Schema + Sample Row

Appended to `<universe_dir>/regression-history.jsonl` when `detect_changes` returns non-empty.

Schema per line:
```json
{
  "timestamp_iso":   "2026-04-13T10:05:23Z",
  "trigger":         "prompt_hash_change",
  "changed_prompts": ["agent_system_prompt"],
  "exit_code":       0,
  "pass_count":      35,
  "fail_count":      0,
  "duration_s":      12.4,
  "error":           null
}
```

Sample row (timeout scenario):
```json
{
  "timestamp_iso":   "2026-04-13T10:06:00Z",
  "trigger":         "prompt_hash_change",
  "changed_prompts": ["classifier_system_prompt", "observer_system_prompt"],
  "exit_code":       -1,
  "pass_count":      0,
  "fail_count":      0,
  "duration_s":      0.0,
  "error":           "timeout"
}
```

- JSONL (append-only, never overwrite) — two runs produce two lines.
- exit_code=1 from known regression gaps is **informative**, not treated as runner failure.
- error field is null on success, "timeout" on TimeoutExpired, or descriptive string on other exceptions.

### (c) Judge Prompt Template Text + SHA-256

Template (in `src/token_world/playtest/judge.py`):

```
You are a simulation quality auditor. Evaluate the following resident-agent \
playtest transcript across three dimensions, each scored 0.0 to 1.0:

1. coherence - do agent actions make sense in sequence?
2. personality_consistency - does the agent stay in character?
3. world_rule_adherence - do actions respect the stated world rules?

Transcript:
{transcript}

Return JSON exactly matching:
{
  "scores": {
    "coherence": <0..1 float>,
    "personality_consistency": <0..1 float>,
    "world_rule_adherence": <0..1 float>
  },
  "rationale": "<1-3 sentence explanation>"
}
```

**SHA-256:** `05e2e25e6cebf7a14a6786b746e61b46471b7463c77f484b80286bf18bbf8598`

Exposed via `token_world.playtest.judge.prompt_hash()` for downstream change detection.

Judge output is appended to the playtest report as `report["judge"]`:
```json
{
  "scores": {
    "coherence": 0.9,
    "personality_consistency": 0.85,
    "world_rule_adherence": 0.8
  },
  "rationale": "Agent was consistent throughout.",
  "model": "claude-sonnet-4-5",
  "prompt_hash": "05e2e25e..."
}
```

Schema-additive: `schema_version` stays at 1; `judge` key is optional.

### (d) No runner.py Modifications — Contract Verified

```
git diff src/token_world/playtest/runner.py
(empty output)
```

All three features are wired from `cli.py` using the hook points left by 06-04:
- `runner.hash_check_fn = _hash_check` — assigned post-construction on the mutable dataclass
- `judge_evaluate` called after `runner.run()` returns, using the completed report JSON

### (e) Requirements Satisfied

| Requirement | How Satisfied |
|-------------|---------------|
| TEST-04 | `judge_evaluate()` scores coherence/personality_consistency/world_rule_adherence 0..1; opt-in via `--judge` |
| TEST-05 | `PromptHashRegistry.detect_changes()` compares SHA-256 of three prompts against stored baseline |
| AUTO-07 | `trigger_regression()` runs `uv run pytest tests/test_regression/ -m regression` subprocess; result in regression-history.jsonl |

## Tests

- 15 tests in `tests/test_playtest/test_hash_registry.py` (Tasks 1+2)
- 5 tests in `tests/test_playtest/test_judge.py` (Task 3)
- 5 new tests in `tests/test_playtest/test_runner.py` (Task 4 CLI wiring)
- Total new tests: **25**
- Full suite: **1342 passed, 14 skipped** (baseline was 1317)

## Commits

| Hash | Description |
|------|-------------|
| `fcd0bf9` | feat(06-05): PromptHashRegistry with SHA-256 change detection + regression trigger [D-14, D-15, AUTO-07] |
| `a47e8f1` | feat(06-05): optional Sonnet judge [D-13, TEST-04] |
| `0184eb0` | feat(06-05): CLI wiring for prompt-hash + auto-regression + judge [D-13, D-14, D-15, AUTO-07] |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pytest summary regex for "N failed in Xs" pattern**
- **Found during:** Task 2 (test 13 failed in RED)
- **Issue:** Original `_SUMMARY_RE` composite regex required `passed` group to appear before `failed`; `"2 failed in 1.0s"` parsed failed=0 instead of failed=2
- **Fix:** Replaced single compound regex with three independent patterns (`_PASSED_RE`, `_FAILED_RE`, `_DURATION_RE`); each matches independently regardless of ordering
- **Files modified:** `src/token_world/playtest/hash_registry.py`
- **Commit:** `fcd0bf9`

**2. [Rule 1 - Bug] Fixed test fixture missing required PlaytestReport fields**
- **Found during:** Task 4 (test 24 — judge not called because PlaytestReport.model_validate raised silently)
- **Issue:** `_cli_universe_setup` fake report JSON missing `scenario_file` and `schema_version` fields required by Pydantic model; exception swallowed by `except Exception` in judge block
- **Fix:** Added `scenario_file: null` and `schema_version: 1` to fake report fixture
- **Files modified:** `tests/test_playtest/test_runner.py`
- **Commit:** `0184eb0`

**3. [Rule 2 - Missing] Added `pytest` import to test_runner.py**
- **Found during:** Task 4 (test 24 NameError)
- **Issue:** `pytest.approx` used in new tests but `import pytest` was missing from test_runner.py
- **Fix:** Added `import pytest` to imports
- **Files modified:** `tests/test_playtest/test_runner.py`
- **Commit:** `0184eb0`

**4. [Rule 2 - Missing] Refactored test CLI patch helper from dict-based to list-based**
- **Found during:** Task 4 (AttributeError — `patch.multiple` can't patch `anthropic.Anthropic` via dotted attribute name)
- **Issue:** `patch.multiple("token_world.cli", **{"anthropic.Anthropic": ...})` fails because `anthropic.Anthropic` is not a valid single attribute name on the cli module
- **Fix:** Changed `_make_cli_patches` to return a list of `patch()` context managers; tests use `contextlib.ExitStack` to enter all patches
- **Files modified:** `tests/test_playtest/test_runner.py`
- **Commit:** `0184eb0`

## Known Stubs

None — all three components are fully implemented and wired.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. `trigger_regression` runs a subprocess but only `uv run pytest` with fixed args; no user-controlled input reaches the subprocess command.

## Self-Check: PASSED

- FOUND: src/token_world/playtest/hash_registry.py
- FOUND: src/token_world/playtest/judge.py
- FOUND: tests/test_playtest/test_hash_registry.py
- FOUND: tests/test_playtest/test_judge.py
- FOUND commit: fcd0bf9
- FOUND commit: a47e8f1
- FOUND commit: 0184eb0
