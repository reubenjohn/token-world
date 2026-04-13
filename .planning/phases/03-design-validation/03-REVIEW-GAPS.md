---
phase: 03-design-validation
reviewed: 2026-04-12T20:15:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - src/token_world/graph/persistence.py
  - src/token_world/graph/knowledge_graph.py
  - src/token_world/viz/mermaid.py
  - src/token_world/use_cases/loader.py
  - src/token_world/use_cases/__init__.py
  - tests/test_graph/test_mypy_clean.py
  - tests/test_viz/test_mermaid_escape.py
  - tests/test_design_validation/test_use_case_loader.py
  - tests/test_design_validation/test_use_case_schema.py
  - tests/test_mechanic/test_cli.py
  - tests/test_mechanic/test_context.py
  - tests/test_mechanic/test_engine.py
  - tests/test_mechanic/test_registry.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 03: Gap-Closure Code Review Report

**Reviewed:** 2026-04-12T20:15:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Follow-up review covering the phase-03 gap-closure commits (03-13 mypy return
types, 03-14 angle-bracket escaping, 03-15 `graph_assertion` kind whitelist,
plus the deferred-ruff cleanup). The gap-closure work is solid: escape ordering
is correct, the assertion-kind whitelist covers all three plausible containers
(`setup.graph_assertions`, `expected_observations[*].graph_assertions`,
`actions[*].graph_assertions`), regression tests are thorough, and the
`test_cli.py` cleanup correctly removes a self-OR'd tautology.

One pre-existing bug was noticed in passing (`"` → `#quot;` missing its
leading `&`), but it was introduced in `d59224a` (before this review window)
and is therefore out of the declared scope — flagged as Info for triage.

## Warnings

### WR-01: `_validate_value` does not recursively guard dict values against non-JSON keys

**File:** `src/token_world/graph/knowledge_graph.py:17-36`

**Issue:** Not in scope of 03-gap commits; flagged only because it sits
adjacent to the `cast`-affected persistence path. Ignore if out of scope for
this review.

---

Actually retracting this — out-of-scope and pre-existing. Promoting the one
genuine concern from this review window to WR-01:

### WR-01: `self._persistence: Any = None` defeats static typing on the whole persistence surface

**File:** `src/token_world/graph/knowledge_graph.py:61`

**Issue:** The attribute is typed `Any`, which is why three `cast(...)` calls
are needed at lines 441, 479, and (transitively) in `save`/`load`/`restore`.
`cast` is a runtime no-op, so mypy sees the declared type but the actual
return values from `self._persistence.*` are whatever `GraphPersistence`
returns. The casts happen to match today (`save_snapshot -> int`,
`list_snapshots -> list[SnapshotInfo]`), but if `GraphPersistence` signatures
drift, the casts will silently lie because the `Any` declaration prevents
mypy from cross-checking. The whole point of 03-13's mypy-clean guard was to
stop `Any` from leaking out of the graph module; typing `_persistence` as
`Any` undermines that guarantee at the boundary.

**Fix:**
```python
from token_world.graph.persistence import GraphPersistence  # top-level import

class KnowledgeGraph:
    def __init__(self, db_path: Path | None = None) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()
        self._events: EventStore = EventStore()
        self._db_path = db_path
        self._current_tick: int = 0
        self._persistence: GraphPersistence | None = (
            GraphPersistence(db_path) if db_path is not None else None
        )
```

Then drop the `cast(int, ...)` on line 441 and `cast(list[SnapshotInfo], ...)`
on line 479 — mypy will infer both directly. Keep the `cast(int, cursor.lastrowid)`
in `persistence.py:210`, which is a genuine `Optional[int] -> int` narrowing
at the sqlite3 stub boundary.

(The original `# Import here to avoid circular imports` comment predates the
split into `persistence.py`; verify no new circular dep appears after the
move — there shouldn't be one because `persistence.py` only imports
`GraphEvent` and `SnapshotInfo`, not `KnowledgeGraph`.)

## Info

### IN-01: `"` escape emits `#quot;` instead of `&quot;` (pre-existing, out of scope)

**File:** `src/token_world/viz/mermaid.py:10`

**Issue:** The translation map uses `'"': "#quot;"` — missing the leading
`&`. Every other entity in the map (`&#91;`, `&#93;`, `&#124;`, `&lt;`, `&gt;`)
has the ampersand. `#quot;` is not a valid HTML/Mermaid entity; it renders
as the literal text `#quot;` in Mermaid output. This predates the 03-14
commit (blame points to `d59224a`, phase 03-01 scaffolding), and
`tests/test_viz/test_mermaid_escape.py:13` plus `test_viz_graph.py:58`
explicitly test for `#quot;`, so fixing it requires updating tests too.

Out of scope for this review since it predates the three gap commits, but
worth filing as a separate issue — the asymmetry is almost certainly a
typo. If it's intentional (e.g., Mermaid-specific quirk), a comment would
help.

**Fix:**
```python
'"': "&quot;",
```
and update the two test expectations.

### IN-02: Redundant `cast()` calls produce false confidence

**File:** `src/token_world/graph/knowledge_graph.py:441, 479`

**Issue:** Both `save_snapshot` and `list_snapshots` on `GraphPersistence`
are already typed with concrete returns (`-> int` and `-> list[SnapshotInfo]`).
The `cast(int, ...)` and `cast(list[SnapshotInfo], ...)` on these call sites
are only necessary because `self._persistence: Any` (see WR-01) erases the
type. Fixing WR-01 drops both casts.

A redundant `cast` is a code smell in itself: a future reader may assume
"this needed narrowing" and leave it in place during a refactor where the
real type actually changed — masking a bug.

**Fix:** Remove both casts after typing `_persistence` properly.

### IN-03: Non-dict observation/action items silently skipped (pre-existing)

**File:** `src/token_world/use_cases/loader.py:109-122`

**Issue:** When iterating `expected_observations`, `setup`, and `actions`,
non-dict entries are silently skipped (`if isinstance(obs, dict): ...`). A
malformed UC that accidentally puts a string or list at these positions
slips past validation. Not a bug introduced by 03-15 — the same pattern
existed for the rest of `validate_frontmatter` — but worth noting while
adjacent code is being hardened.

**Fix (if in scope for a future pass):**
```python
for o_idx, obs in enumerate(fm.get("expected_observations", []) or []):
    if not isinstance(obs, dict):
        errors.append(
            f"{source}: expected_observations[{o_idx}] must be a mapping"
        )
        continue
    _check_assertions(obs.get("graph_assertions"), ...)
```
Same pattern for `actions[*]`.

---

## Particular-concern resolution

Addressing the four concerns raised in the review brief:

1. **`escape_label` ordering** — Correct. `_ENTITY_ESCAPES` is applied via
   `str.translate` in a single pass (step 1), then `\n → <br/>` is applied
   afterward (step 2). Attacker-supplied `<br/>` in input becomes
   `&lt;br/&gt;` in step 1 and survives step 2 untouched. Empirically
   verified: `escape_label('<br/>', max_len=100) == '&lt;br/&gt;'` and
   `escape_label('safe<br/>attacker', max_len=100) == 'safe&lt;br/&gt;attacker'`.
   `test_attacker_supplied_br_is_escaped` and
   `test_escape_neutralises_angle_brackets` lock this in.

2. **`graph_assertion` kind whitelist coverage** — Full. `_check_assertions`
   is called on all three containers: `expected_observations[o_idx].graph_assertions`
   (loader.py:111), `setup.graph_assertions` (line 118), and
   `actions[a_idx].graph_assertions` (line 122). Regression tests in
   `test_use_case_loader.py` cover all three containers and include null-ish
   edge cases (`""`, `None`, wrong-case `"HAS_EDGE"`). The `test_use_case_schema.py::test_every_authored_assertion_uses_a_valid_kind`
   cross-check scans real authored UCs, which is the strongest possible
   guard against drift.

3. **`typing.cast` safety** — `cast(int, cursor.lastrowid)` in
   `persistence.py:210` is safe at runtime: `INSERT OR REPLACE` with an
   `AUTOINCREMENT` PK always writes a row, so `lastrowid` is non-None. The
   two casts in `knowledge_graph.py` (lines 441, 479) are **redundant** —
   they exist only because `_persistence: Any`. See WR-01 and IN-02.

4. **`test_cli.py` simplification** — Correct. The removed
   `"not found" in (result.output + (result.output or "")).lower()` was a
   pure no-op: `(result.output + (result.output or ""))` collapses to
   `result.output + result.output` when output is truthy and `"" + "" == ""`
   otherwise; doubling the haystack cannot introduce a substring that
   wasn't already in the original. The LHS (`"not found" in result.output.lower()`)
   fully subsumes it. No other test relied on this branch; grep for
   `not found` finds only this one assertion in test_cli.py.

---

_Reviewed: 2026-04-12T20:15:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
