---
phase: 03-design-validation
plan: 13
type: gap-closure
wave: 5
depends_on: [12]
files_modified:
  - src/token_world/graph/knowledge_graph.py
autonomous: true
requirements:
  - DVAL-01
tags:
  - gap-closure
  - typing
  - mypy

must_haves:
  truths:
    - "uv run mypy src/token_world/graph/ exits 0 with 'Success: no issues found'"
    - "KnowledgeGraph.save_snapshot returns int (not Any)"
    - "KnowledgeGraph.list_snapshots returns list[SnapshotInfo] (not Any)"
    - "uv run pytest tests/test_graph/ -q still passes all tests"
    - "uv run ruff check src/ still exits 0"
    - "uv run ruff format --check src/ still exits 0"
  artifacts:
    - path: "src/token_world/graph/knowledge_graph.py"
      provides: "Snapshot-related methods with explicit return types that satisfy mypy --strict-optional no-any-return"
      contains: "def save_snapshot"
  key_links:
    - from: "src/token_world/graph/knowledge_graph.py:save_snapshot"
      to: "src/token_world/graph/persistence.py:GraphPersistence.save_snapshot"
      via: "explicit return annotation on GraphPersistence OR cast() at call site so mypy sees int, not Any"
      pattern: "def save_snapshot\\("
    - from: "src/token_world/graph/knowledge_graph.py:list_snapshots"
      to: "src/token_world/graph/persistence.py:GraphPersistence.list_snapshots"
      via: "explicit return annotation list[SnapshotInfo] OR cast() at call site"
      pattern: "def list_snapshots\\("
---

<objective>
Close UAT gap (Test 3, severity: minor) — `uv run mypy src/token_world/graph/` currently reports two `no-any-return` errors at `knowledge_graph.py:450` and `:479` because `GraphPersistence.save_snapshot` and `GraphPersistence.list_snapshots` return `Any` (untyped sqlite passthrough) and their return values are handed back directly from annotated-as-`int` / `list[SnapshotInfo]` methods on `KnowledgeGraph`.

Purpose: Phase 03 UAT verdict is CONDITIONAL PASS. This gap blocks the "type-check green" criterion that Phase 04 assumes when consuming the graph module. Fix narrows the trust boundary so downstream mechanic-authoring agents can rely on the public API types.

Output: A clean `uv run mypy src/token_world/graph/` (0 errors), with no behaviour change to the snapshot API.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/03-design-validation/03-UAT.md
@src/token_world/graph/knowledge_graph.py
@src/token_world/graph/persistence.py
@src/token_world/graph/models.py
</context>

<threat_model>
**Threat surface:** Type-system correctness only — no runtime behaviour change, no new data flow, no new serialization paths. The edit is confined to annotations and/or a `cast()` call.

**Low-severity only:** A sloppy fix that silences mypy with `# type: ignore` instead of tightening the annotation would regress the type safety promise Phase 04 depends on. Mitigation: `<acceptance_criteria>` forbids `# type: ignore[no-any-return]` in the diff.
</threat_model>

<tasks>

<task id="13.1">
<title>Annotate GraphPersistence snapshot methods so their return types are concrete</title>

<read_first>
  - src/token_world/graph/persistence.py (current snapshot method signatures — see `save_snapshot`, `list_snapshots`)
  - src/token_world/graph/models.py (for `SnapshotInfo` import location)
  - src/token_world/graph/knowledge_graph.py (lines 430–480 — the two call sites that trigger `no-any-return`)
</read_first>

<action>
In `src/token_world/graph/persistence.py`, ensure `GraphPersistence.save_snapshot(...)` is annotated with `-> int` and `GraphPersistence.list_snapshots(...)` is annotated with `-> list[SnapshotInfo]`. If the methods are already annotated but the body returns an unannotated sqlite cursor value (e.g. `cur.lastrowid`, `cur.fetchall()`), wrap the returned expression:

```python
from typing import cast
# save_snapshot
return cast(int, cur.lastrowid)
# list_snapshots
rows = cur.fetchall()
return [SnapshotInfo(...) for row in rows]  # comprehension is already list[SnapshotInfo]
```

Preferred fix order:
1. If signatures are missing/incomplete annotations → add `-> int` / `-> list[SnapshotInfo]` and type any intermediate vars so mypy can infer all the way to the return.
2. If signatures are correct but inner values are `Any` (e.g. `lastrowid` from sqlite3 Cursor is `Any`) → use `typing.cast(int, ...)` at the return site.
3. Do NOT use `# type: ignore[no-any-return]` — that silences the check rather than fixing it.

After edits: `knowledge_graph.py:450` (`return snapshot_id`) and `:479` (`return self._persistence.list_snapshots()`) must satisfy mypy without any change to those two lines; the fix lives in `persistence.py` where the `Any` originates.
</action>

<acceptance_criteria>
  - `uv run mypy src/token_world/graph/` exits 0 and its stdout contains the literal string `Success: no issues found`
  - `git diff src/token_world/graph/knowledge_graph.py` contains 0 lines (no change required there if `persistence.py` is fixed correctly) OR contains only typed `cast(...)` call(s)
  - `git diff src/token_world/graph/persistence.py` does NOT contain the string `# type: ignore[no-any-return]`
  - `git diff src/token_world/graph/persistence.py` does NOT contain the string `# type: ignore` anywhere added on the touched methods
  - `persistence.py` still declares `def save_snapshot(` and `def list_snapshots(` (no rename)
  - `uv run pytest tests/test_graph/ -q` exits 0 with the same test count as before (no test removed or skipped)
</acceptance_criteria>

</task>

<task id="13.2">
<title>Add regression guard: mypy-clean contract for graph module is test-enforced</title>

<read_first>
  - tests/test_graph/ (directory layout — confirm whether a mypy smoke test already exists)
  - pyproject.toml / mypy.ini (mypy config — what strictness is already configured)
</read_first>

<action>
Add a small regression test at `tests/test_graph/test_mypy_clean.py` that shells out to mypy on the graph module and asserts exit 0, so future regressions (e.g. a new `no-any-return` on another snapshot method) fail CI rather than UAT. Skip if `mypy` is not importable (keeps the suite runnable in minimal envs).

Content:

```python
"""Regression: src/token_world/graph/ must be mypy-clean.

UAT gap 03-UAT#3: `save_snapshot` and `list_snapshots` leaked Any-typed
sqlite returns; this test fails fast if a new Any leaks in.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest


@pytest.mark.skipif(shutil.which("mypy") is None, reason="mypy not installed")
def test_graph_module_is_mypy_clean() -> None:
    result = subprocess.run(
        ["mypy", "src/token_world/graph/"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"mypy failed on src/token_world/graph/:\n"
        f"--- STDOUT ---\n{result.stdout}\n"
        f"--- STDERR ---\n{result.stderr}"
    )
```

This is one file, ~25 lines, zero runtime cost (skips cleanly when mypy isn't on PATH).
</action>

<acceptance_criteria>
  - File `tests/test_graph/test_mypy_clean.py` exists
  - File contains the literal string `def test_graph_module_is_mypy_clean`
  - `uv run pytest tests/test_graph/test_mypy_clean.py -q` exits 0 (after task 13.1 is landed)
  - The test is discoverable (no `__init__.py` conflict): `uv run pytest tests/test_graph/test_mypy_clean.py --collect-only` lists exactly 1 test
</acceptance_criteria>

</task>

</tasks>

<verification>
  - `uv run mypy src/token_world/graph/` → `Success: no issues found in 5 source files` (or similar — must exit 0)
  - `uv run pytest tests/ -q` → all tests pass, test count = prior count + 1
  - `uv run ruff check src/` → unchanged (no new lint errors introduced by the annotations)
  - Re-run UAT probe: confirm Test 3 in `.planning/phases/03-design-validation/03-UAT.md` would now flip from `issue` to `pass`
</verification>
