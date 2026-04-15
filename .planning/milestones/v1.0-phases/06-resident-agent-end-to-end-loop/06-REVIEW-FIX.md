---
phase: 06-resident-agent-end-to-end-loop
fixed_at: 2026-04-13T17:48:11Z
review_path: .planning/phases/06-resident-agent-end-to-end-loop/06-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 06: Code Review Fix Report

**Fixed at:** 2026-04-13T17:48:11Z
**Source review:** .planning/phases/06-resident-agent-end-to-end-loop/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (WR-01 through WR-04; IN-01..IN-03 deferred — see below)
- Fixed: 4
- Skipped: 0

All four warning findings were fixed via TDD: regression test written first (confirmed
failing), source fix applied, test confirmed passing, committed atomically.

## Fixed Issues

### WR-01: `--output` path is silently ignored by PlaytestRunner

**Files modified:** `src/token_world/playtest/runner.py`, `tests/test_playtest/test_runner.py`
**Commit:** a2d910a
**Applied fix:** Replaced `report.write(output_path.parent)` (which generated a
UUID-named file in a `playtest-reports/` subdirectory) with an explicit
`output_path.parent.mkdir(parents=True, exist_ok=True)` + `_atomic_write_json(output_path, ...)`
+ `return output_path`. The caller-specified path (including filename and extension) is
now honoured exactly.

**Regression tests added:**
- `test_runner_honours_exact_output_path` — asserts returned path equals requested path
  and file exists there; asserts `playtest-reports/` dir was NOT created
- `test_runner_creates_parent_dirs_for_output_path` — asserts nested parent dirs are
  created automatically

---

### WR-02: `PlaytestRunner` never calls `memory.maybe_compact_summary()`

**Files modified:** `src/token_world/playtest/runner.py`, `tests/test_playtest/test_runner.py`
**Commit:** a2d910a
**Applied fix:** Added `self.memory.maybe_compact_summary(self.session_id, self.agent._client)`
call immediately after `self.memory.store_turn(...)` in the main simulation loop, matching
the pattern in `cli.py`'s `agent-turn` command. The agent's `_client` attribute is accessed
via `# type: ignore[attr-defined]` since `agent` is typed as `object` in the dataclass.

**Regression test added:**
- `test_runner_calls_maybe_compact_summary_each_turn` — runs 12-turn playtest with mocked
  memory; asserts `maybe_compact_summary` was called exactly 12 times

---

### WR-03: `run_turn()` crashes with `IndexError` on empty LLM response

**Files modified:**
- `src/token_world/resident/agent.py`
- `src/token_world/resident/memory.py`
- `src/token_world/resident/personality.py`
- `tests/test_resident/test_agent.py`
- `tests/test_resident/test_memory.py`
- `tests/test_resident/test_personality.py`

**Commit:** 7fc161d
**Applied fix:** Added `if not content: raise ValueError("LLM returned empty response in ...")` guard
before `content[0]` access in all three locations:
- `agent.py:run_turn()` — raises `ValueError("LLM returned empty response in run_turn()")`
- `memory.py:maybe_compact_summary()` — raises `ValueError("LLM returned empty response in maybe_compact_summary()")`
- `personality.py:PersonalityGenerator.generate()` — raises `ValueError("LLM returned empty response in PersonalityGenerator.generate()")`

Also applied the IN-01 trivial cast fix in `memory.py`: changed
`response.content[0].text.strip()` to `str(content[0].text).strip()` (the guard
refactor made this natural).

**Regression tests added:**
- `test_agent.py::test_run_turn_raises_on_empty_content_list`
- `test_memory.py::test_maybe_compact_summary_raises_on_empty_content`
- `test_personality.py::test_generator_raises_on_empty_content_list`

Each test mocks the API client to return `response.content = []` and asserts
`ValueError` with message matching `[Ee]mpty`.

---

### WR-04: `trigger_regression` subprocess has no working-directory pin

**Files modified:** `src/token_world/playtest/hash_registry.py`, `tests/test_playtest/test_hash_registry.py`
**Commit:** 629ee9d
**Applied fix:** Computed `_project_root = Path(__file__).parents[3]` before the
`subprocess.run` call. `hash_registry.py` resides at
`src/token_world/playtest/hash_registry.py`, so `.parents[3]` correctly resolves to
the project root. Passed `cwd=_project_root` to `subprocess.run`.

**Regression test added:**
- `test_hash_registry.py::test_trigger_regression_uses_project_root_as_cwd` — changes
  process cwd to `/tmp`, invokes `trigger_regression`, and asserts the captured `cwd`
  kwarg is not `/tmp` and points to a directory containing `pyproject.toml` or
  `src/token_world/`.

---

## Deferred Info Findings

### IN-01: `memory.new_summary` missing `str()` cast

**Status:** Fixed incidentally as part of WR-03. The guard refactor naturally produced
`str(content[0].text).strip()` in `memory.py`.

### IN-02: `_build_messages` conditional structure is confusing

**File:** `src/token_world/resident/agent.py:151-161`
**Reason:** This is a documentation/clarity issue only — the reviewer confirmed no data
loss occurs. The summary is correctly embedded in turns when turns exist. Fixing requires
restructuring logic that currently works correctly, which risks introducing a regression
for zero clarity gain in a working system. Deferred to a future refactor phase.

### IN-03: `adversarial_rate` scenario field is parsed but never applied

**File:** `src/token_world/playtest/scenarios.py:77`
**Reason:** The reviewer noted this is not a correctness bug — the runner still works.
Implementing the feature requires new logic in `_determine_action` and a sampling
decision point that deserves its own design decision. Deferred to a future feature phase
(Wave 4+ per the original plan comment in runner.py).

---

_Fixed: 2026-04-13T17:48:11Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
