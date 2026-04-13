---
phase: 03-design-validation
status: needs-fix
depth: standard
reviewed: 2026-04-12
files_reviewed: 11
files_reviewed_list:
  - src/token_world/cli.py
  - src/token_world/graph/persistence.py
  - src/token_world/graph/spatial.py
  - src/token_world/graph/temporal.py
  - src/token_world/mechanic/context.py
  - src/token_world/mechanic/loader.py
  - src/token_world/use_cases/__init__.py
  - src/token_world/use_cases/loader.py
  - src/token_world/viz/__init__.py
  - src/token_world/viz/graph_viz.py
  - src/token_world/viz/mermaid.py
findings_count:
  critical: 0
  high: 1
  medium: 4
  low: 5
  info: 3
  total: 13
---

# Phase 03 Code Review: Design Validation

**Depth:** standard (per-file language-aware analysis)
**Files reviewed:** 11 source files (tests scanned for coverage gaps only)
**Status:** needs-fix (one HIGH correctness bug, several MEDIUM issues worth addressing)

## Overall Summary

The phase 03 implementation is largely solid and defensive, with explicit security awareness (parameterized SQL throughout `temporal.py`, ID sanitisation in `graph_viz.py`, label escaping in `mermaid.py`). The focus-area risks called out in the review brief (SQL injection, Mermaid injection, YAML parsing) are all handled correctly:

- **SQL in `temporal.py` and `persistence.py`**: every statement uses `?` placeholders; `where` fragments are static. No f-string SQL. The dynamic `placeholders = ",".join("?" * len(...))` in `prune_snapshots` is a count, not user data, so it is safe.
- **Mermaid emission in `graph_viz.py` / `mermaid.py`**: labels are HTML-escaped via `escape_label` (Mermaid's `#quot;` / `&#91;` style is intentional and valid Mermaid syntax, not a typo), IDs are sanitised to `[A-Za-z0-9_]` with SHA-256 hash suffix for collision avoidance, and `max_nodes` caps denial-of-service surface. Good.
- **YAML frontmatter parsing** in `use_cases/loader.py` uses `yaml.safe_load` (not `yaml.load`) and validates the schema shape defensively.

The headline issues are:

1. **HIGH — `TemporalIndex.find_state_at_tick` does not replay `add_node` events**, so a node that is removed and re-added between a snapshot and the query tick will end up with empty state instead of the re-add's property set. Time-travel queries are silently wrong for this scenario.
2. **MEDIUM — `SpatialIndex` mutates `self._next_int_id` but never reuses it across partial-rebuild situations**; combined with a stale-index risk if the graph changes mid-mechanic, callers relying on `ctx.spatial` must know that the index is frozen on first access.
3. **MEDIUM — `escape_label`'s truncation counts post-escape characters**, so a label with many quotes is truncated much shorter than 60 "logical" characters; if a Mermaid escape entity is split across the 60-char boundary, the output contains a corrupt entity like `&#12…`.
4. **MEDIUM — `graph_viz.extract_subgraph` reaches into `kg._graph`**, violating the repo-wide "all graph access via `KnowledgeGraph` API" invariant documented in `CLAUDE.md`. The comment acknowledges the access but the invariant has no public escape hatch yet.
5. **MEDIUM — `use_cases/loader.py` does not accept CRLF-encoded frontmatter**; a file saved on Windows with `---\r\n` delimiters will be rejected as "missing YAML frontmatter".

Test coverage for the new modules is reasonable; see LOW findings for gaps (no test for `find_state_at_tick` re-add scenario, no test for `prune_snapshots` empty-delete edge case).

No critical security issues found. Parameterized queries are used consistently. `mechanic/loader.py`'s `exec_module` is flagged INFO because arbitrary-Python-execution is the explicit v1 design (per `CLAUDE.md` Technology Stack: "No sandboxing for v1").

---

## HIGH

### H-01 — `find_state_at_tick` loses state on remove-then-readd sequences

- **File:** `src/token_world/graph/temporal.py:146-153`
- **Summary:** The replay loop in `find_state_at_tick` handles only `set_property` and `remove_node` events. It ignores `add_node`, so a node that is removed and later re-added within the replay window ends up with empty props even though the `add_node` event's `new_value_json` holds the correct initial state.
- **Detail:** The loop is:
  ```python
  for e in history:
      if e.event_type == "set_property" and e.property_name:
          state[e.property_name] = json.loads(e.new_value_json) if ...
      elif e.event_type == "remove_node":
          state = {}
  ```
  `KnowledgeGraph.add_node` writes an event with `event_type="add_node"` and a full `new_value_json = {"type": node_type, **props}` (see `knowledge_graph.py:160-168`). When replay encounters a `remove_node` followed by an `add_node`, the reconstructed state is `{}` instead of the re-add's properties. Any downstream mechanic that asks for "what did this node look like at tick T after it was restored" will get an incorrect empty dict. The Wave-4 spatial / resource use cases explicitly exercise remove/re-add sequences (e.g., pickup/drop cycles), so this matters.
- **Fix:** Add an `add_node` branch that seeds `state` from the event payload:
  ```python
  elif e.event_type == "add_node":
      state = json.loads(e.new_value_json) if e.new_value_json else {}
  ```
  Add a regression test in `tests/test_graph/test_temporal_index.py` covering the add → remove → add sequence across a snapshot boundary.

---

## MEDIUM

### M-01 — `escape_label` truncation can produce broken HTML entities

- **File:** `src/token_world/viz/mermaid.py:22-25`
- **Summary:** Truncation is applied to the post-escape string at a raw character boundary. If the 60th character lands inside an escape sequence like `&#124;` or `<br/>`, the output contains a corrupt fragment (`&#12…`, `<br…`), which renders as literal text or breaks the label entirely in Mermaid.
- **Detail:** Consider `text = "|" * 12`. After `translate`, it is `&#124;` × 12 = 72 chars. Truncated at `max_len=60`, we get `&#124;&#124;&#124;&#124;&#124;&#124;&#124;&#124;&#124;&#12…` — the final entity is malformed. This is not a security issue (it can't inject anything), but it produces visibly broken diagrams.
- **Fix:** Truncate the *input* before escaping, or walk the escaped string backwards when `len > max_len` to find the last complete entity boundary (`;` or `/>`) before trimming. Simplest pragmatic fix:
  ```python
  if len(text) > max_len - 1:
      text = text[: max_len - 1]
  escaped = text.translate(_ESCAPES)
  if len(escaped) > max_len:
      escaped = escaped[: max_len - 1] + "…"
  ```
  Add a parameterised test case for `"|" * 20` asserting no bare `&#` or `<br` without a terminator remains.

### M-02 — `graph_viz.extract_subgraph` bypasses the `KnowledgeGraph` API

- **File:** `src/token_world/viz/graph_viz.py:78`
- **Summary:** `base: nx.DiGraph = kg._graph  # intentional access to the underlying DiGraph` violates the repo invariant "All graph mutations go through `KnowledgeGraph` methods" and the weaker "never direct NetworkX access" convention from `CLAUDE.md`.
- **Detail:** `KnowledgeGraph` exposes `nodes()`, `neighbors()`, `has_node()`, `has_edge()` but no primitive for "give me the NetworkX ego-graph around X". The viz module papers over that gap by reaching into a private attribute. Two downstream risks: (a) if `KnowledgeGraph` ever switches its internal representation (e.g., to a subgraph-index hybrid), viz silently breaks; (b) other contributors will cite this as precedent to reach into `_graph` elsewhere.
- **Fix:** Add a read-only `KnowledgeGraph.ego_subgraph(anchor, depth)` or `KnowledgeGraph.as_readonly_view()` method that returns a frozen `nx.DiGraph` copy. Have `extract_subgraph` call the new method. Optionally mark the current access with a TODO pointing at the phase-04 API-surface work rather than silently tolerating it.

### M-03 — `TemporalIndex` reaches into `KnowledgeGraph._events` and `_db_path`

- **File:** `src/token_world/graph/temporal.py:65, 93, 159, 222`
- **Summary:** Accessing private `_events` and `_db_path` on `KnowledgeGraph` couples `TemporalIndex` to the graph module's internal representation. The docstring acknowledges the debt but the invariant is the same as M-02.
- **Detail:** `self._graph._events.get_events()` and `getattr(self._graph, "_db_path", None)` will break if `KnowledgeGraph` ever splits storage responsibilities (e.g., moves the event store to a separate holder, or renames the DB handle). `getattr(..., None)` masks the failure at import time but silently returns empty history at query time, which is worse than an AttributeError.
- **Fix:** Add public accessors to `KnowledgeGraph`: `get_session_events() -> list[GraphEvent]` and `get_db_path() -> Path | None`. Update `TemporalIndex.__init__` to hold these references and update call sites. Remove the `getattr` fallback — if the graph has no db_path, that's a valid state (in-memory only) and should be represented by a sentinel, not by AttributeError-squash.

### M-04 — Use-case loader rejects CRLF-encoded frontmatter

- **File:** `src/token_world/use_cases/loader.py:36-40`
- **Summary:** `load_use_case` checks `text.startswith("---\n")` and splits on `"---\n"`. A use-case file saved on Windows or by an editor that emits CRLF line endings will have `"---\r\n"` delimiters and be rejected with "missing YAML frontmatter", even though the file is syntactically valid.
- **Detail:** This is the kind of "works on my machine" issue that bites downstream contributors authoring use cases from Windows/VSCode. Since `yaml.safe_load` itself is CRLF-tolerant, only the framing check is the problem.
- **Fix:** Normalise line endings before framing, e.g.:
  ```python
  text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
  ```
  Add a regression test that writes a CRLF-framed use-case fixture and asserts it loads cleanly.

---

## LOW

### L-01 — `SpatialIndex` staleness is silent

- **File:** `src/token_world/graph/spatial.py:89-124`
- **Summary:** `rebuild()` is only called at index construction time (via `MechanicContext.spatial`'s lazy initialiser). If a mechanic's `apply` phase mutates the graph and then reads `ctx.spatial` again, the index is stale — the docstring says "rebuildable" but there is no automatic re-scan trigger.
- **Detail:** For phase 03's use cases this is fine (check reads spatial, apply writes mutations, next tick rebuilds). But it's not discoverable from the API; a future contributor will burn an afternoon on "why isn't the new node showing up in `ctx.spatial.nearest()`".
- **Fix:** Document the contract in the `MechanicContext.spatial` docstring: "The index is built once per context and does NOT refresh after mutations; construct a fresh context or call `ctx.spatial.rebuild()` manually if you need post-mutation queries." Optionally expose `rebuild()` on `MechanicContext` as a convenience.

### L-02 — `_passes_filter` double-negative return is hard to read

- **File:** `src/token_world/graph/spatial.py:143`
- **Summary:** `return not (subtype is not None and props.get("subtype") != subtype)` is logically correct but takes three reads to parse.
- **Fix:**
  ```python
  if subtype is not None and props.get("subtype") != subtype:
      return False
  return True
  ```
  (ruff's `SIM` rules may flag this but the cost is one extra line for considerable readability.)

### L-03 — `prune_snapshots` would emit `IN ()` if guard were bypassed

- **File:** `src/token_world/graph/persistence.py:286-290`
- **Summary:** The early return `if count <= max_count: return []` protects against empty `deleted_ids`, but the code below would produce `DELETE ... WHERE snapshot_id IN ()` (a syntax error) if that guard were ever removed or skipped. It's a defence-in-depth concern.
- **Fix:** Add an explicit guard immediately before the DELETE:
  ```python
  if not deleted_ids:
      return []
  placeholders = ",".join("?" * len(deleted_ids))
  ```

### L-04 — `viz-graph --output` does not validate parent directory

- **File:** `src/token_world/cli.py:383-385`
- **Summary:** `Path(output).write_text(mermaid, encoding="utf-8")` raises a raw `FileNotFoundError` if the parent directory does not exist. Click's `type=click.Path(writable=True)` permits non-existent paths, so the CLI's own error handling path is bypassed and the user sees a Python traceback.
- **Fix:** Either (a) add `Path(output).parent.mkdir(parents=True, exist_ok=True)` before writing, or (b) wrap the write in a try/except and emit `click.echo(f"Error: ...", err=True); raise SystemExit(5)` to match the other exit codes (1=universe missing, 2=usage, 3=empty anchor set, 4=too many nodes). Document the new exit code alongside the others in the docstring.

### L-05 — `query-graph --has-property` and `--near` combined with `--type` compute filters twice

- **File:** `src/token_world/cli.py:186-196`
- **Summary:** When `--near` is given together with `--type`, the code calls `kg.neighbors(near_node)` (no type filter) then applies `type` filtering with a second `kg.query(n)` pass per candidate. For each candidate that already passed `--has-property`, this is a third call to `kg.query(n)`. On a large neighbourhood this is O(3n) queries where O(n) would suffice.
- **Fix:** Compute `props = kg.query(n)` once per candidate and run all filter predicates off that dict:
  ```python
  filtered = []
  for n in candidates:
      props = kg.query(n)
      if node_type and props.get("type") != node_type:
          continue
      if has_prop and has_prop not in props:
          continue
      filtered.append(n)
  candidates = filtered
  ```
  Also reduces the number of graph queries in the JSON output path. (Not a v1 performance concern per the review scope, but correctness-adjacent: fewer query calls means fewer opportunities for stale/inconsistent reads if `KnowledgeGraph.query` is ever enhanced with caching.)

---

## INFO

### I-01 — `mechanic/loader.py` executes arbitrary user Python

- **File:** `src/token_world/mechanic/loader.py:34-39`
- **Summary:** `spec.loader.exec_module(module)` runs any `mechanic.py` on disk. This is the documented v1 design ("No sandboxing for v1; add RestrictedPython if needed" — `CLAUDE.md`).
- **Detail:** Flagged for visibility only. Before any network-exposed deployment, this must gate on a trust boundary (e.g., universes loaded from a user-controlled path should require a trust flag, or run under RestrictedPython/subprocess sandbox).
- **Fix:** None required for v1. Track in `deferred-items.md` if not already.

### I-02 — `SpatialIndex._coerce_bbox` rejects `bool` values as non-numeric

- **File:** `src/token_world/graph/spatial.py:47, 54`
- **Summary:** `isinstance(v, int | float) and not isinstance(v, bool)` correctly excludes `True`/`False` from position lists — these would otherwise coerce to `1.0` / `0.0`. Good defensive choice; flagging for reviewers who might think the `not isinstance(v, bool)` is redundant.
- **Fix:** None. Consider a brief inline comment explaining why bool is excluded, to prevent future "simplification" PRs.

### I-03 — Test file `test_use_case_schema.py` skips when library is empty

- **File:** `tests/test_design_validation/test_use_case_schema.py:14-16`
- **Summary:** All three tests `pytest.skip()` if no use-case files are authored. This is correct for phase-03 wave-1 CI but means the tests silently pass until Wave 2 authoring produces files. A CI guard ("skipped tests must flip to passing by Wave-2 completion") is worth adding to the phase gate.
- **Fix:** No code change. Add a note to `03-VALIDATION.md` or the wave-2 plan that these skips must flip to passing before phase-03 exit.

---

## Files Reviewed (Sources)

| File | Lines | Findings |
|---|---|---|
| `src/token_world/cli.py` | 387 | L-04, L-05 |
| `src/token_world/graph/persistence.py` | 320 | L-03 |
| `src/token_world/graph/spatial.py` | 226 | L-01, L-02, I-02 |
| `src/token_world/graph/temporal.py` | 265 | H-01, M-03 |
| `src/token_world/mechanic/context.py` | 180 | (clean) |
| `src/token_world/mechanic/loader.py` | 47 | I-01 |
| `src/token_world/use_cases/__init__.py` | 7 | (clean) |
| `src/token_world/use_cases/loader.py` | 77 | M-04 |
| `src/token_world/viz/__init__.py` | 8 | (clean) |
| `src/token_world/viz/graph_viz.py` | 264 | M-02 |
| `src/token_world/viz/mermaid.py` | 26 | M-01 |

Tests scanned for coverage correctness; no issues that would gate the phase.

---

_Reviewed: 2026-04-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
