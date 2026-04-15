---
phase: 03-design-validation
plan: 14
subsystem: viz
tags: [gap-closure, security, viz, mermaid, xss]

# Dependency graph
requires:
  - phase: 03-design-validation
    provides: "escape_label scaffolding + truncation-safety (M-01) from 03-04 viz-graph CLI"
  - phase: 03-design-validation
    provides: "gap-analysis synthesis 03-12 that catalogued UAT #7 angle-bracket gap"
provides:
  - "escape_label entity-escapes '<' and '>' at the escape boundary"
  - "Ordering invariant: entity-escape all hostile chars BEFORE injecting literal <br/> for newlines"
  - "Adversarial regression tests encoding the new escape contract"
affects: [04-llm-mechanic-generation, 04.1-operator-agent-harness, viz-graph-CLI]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Defense-in-depth at the point of production (escape_label), not point of consumption (Mermaid renderer config)"
    - "Ordered translate -> replace: entity-escape first, then inject the ONE legal <br/> token for \\n"

key-files:
  created: []
  modified:
    - "src/token_world/viz/mermaid.py"
    - "tests/test_viz/test_mermaid_escape.py"

key-decisions:
  - "Entity-escape '<' and '>' unconditionally in escape_label rather than rely on Mermaid securityLevel=strict at consumer sites"
  - "Replace '\\n' with literal '<br/>' AFTER translate() so attacker-supplied '<br/>' in input is neutralised while genuine newline rendering survives"
  - "Retain existing truncation-safety (M-01) invariant unchanged — new escapes slot into the same rfind('&')/rfind('<') cut-walker"

patterns-established:
  - "escape-then-inject: any ordering where we must both escape and emit a specific token handles the escape FIRST"

requirements-completed:
  - DVAL-01
  - GRAPH-07

# Metrics
duration: 4min
completed: 2026-04-13
---

# Phase 03-14: escape_label angle-bracket gap closure Summary

**escape_label now entity-escapes `<` and `>` at the emission boundary, neutralising XSS-shaped payloads (`<script>`, `<img onerror=...>`, `<iframe>`) before they reach any downstream Mermaid renderer, while preserving genuine newline-to-`<br/>` rendering.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-13T02:36:04Z
- **Completed:** 2026-04-13T02:39:42Z
- **Tasks:** 3 (2 with file changes, 1 shell smoke check)
- **Files modified:** 2

## Accomplishments

- Closed UAT Test 7 (major severity) — `escape_label('<script>alert(1)</script>')` now returns `'&lt;script&gt;alert(1)&lt;/script&gt;'` instead of the raw payload
- Added 7 new test cases (5 parametrized + 2 standalone) encoding the escape contract, bringing `tests/test_viz/test_mermaid_escape.py` from 11 to 18 test cases, all passing
- Verified end-to-end via `token-world viz-graph`: a node with `name='alice <the brave>'` renders as `alice &lt;the brave&gt;` in the Mermaid output
- Full test suite remains green: 299 passed

## Task Commits

Each task was committed atomically:

1. **Task 14.1: Rewrite escape_label to entity-escape < and >** — `6b9b931` (fix)
2. **Task 14.2: Add adversarial test coverage** — `8b007b0` (test)
3. **Task 14.3: Verify viz-graph CLI output** — no commit (shell smoke check, no files changed)

**Plan metadata:** _see final commit below_

## Files Created/Modified

- `src/token_world/viz/mermaid.py` — added `<` → `&lt;` and `>` → `&gt;` to the entity escape table; reordered so `translate()` runs before `replace("\n", "<br/>")`; truncation-safety walker unchanged
- `tests/test_viz/test_mermaid_escape.py` — appended `test_escape_neutralises_angle_brackets` (parametrized over 5 XSS payloads), `test_escape_preserves_newline_as_br`, and `test_attacker_supplied_br_is_escaped`

## Decisions Made

- **Escape-first, inject-second ordering.** The `.replace("\n", "<br/>")` runs on the already-entity-escaped string so that the `<br/>` token we emit is the ONLY `<br/>` in the output. Any `<br/>` in raw input has already been turned into `&lt;br/&gt;` by the preceding `translate()`.
- **Kept `translate()` for single-pass escaping.** Using `str.maketrans`/`translate()` avoids the classic chain-of-`replace` double-escape bug where `<` → `&lt;` then the `&` in `&lt;` gets re-escaped.
- **Truncation logic unchanged.** The existing rfind(`&`)/rfind(`<`) cut-walker already handles both entity families and the new `<` mapping slots in without modification — M-01 invariant preserved.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `uv run ruff check src/ tests/` reports 4 errors, but all 4 are pre-existing in `tests/test_mechanic/` and predate this plan (verified against `HEAD~2`). Logged to `.planning/phases/03-design-validation/deferred-items.md` under "Pre-existing ruff errors in tests/test_mechanic/". `ruff check src/` and `ruff check tests/test_viz/` both exit clean — this plan introduced no new lint errors.

## Deferred Issues

- Pre-existing ruff violations in `tests/test_mechanic/{test_cli.py,test_context.py,test_engine.py}` — see deferred-items.md. Scope boundary: plan 03-14 only touches `viz/mermaid.py` and `test_mermaid_escape.py`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 04 (LLM mechanic generation) pipelines can now render any LLM-produced label through `escape_label` without relying on a downstream sanitiser.
- UAT Test 7 should flip from `issue` to `pass` on next UAT re-run.

## Self-Check: PASSED

Verified:

- `src/token_world/viz/mermaid.py` exists and contains `"<": "&lt;"` and `"&gt;"` — FOUND
- `tests/test_viz/test_mermaid_escape.py` exists and contains `"<script>alert(1)</script>"`, `test_escape_neutralises_angle_brackets`, `test_escape_preserves_newline_as_br`, `test_attacker_supplied_br_is_escaped` — FOUND
- Commit `6b9b931` (task 14.1) — FOUND in `git log`
- Commit `8b007b0` (task 14.2) — FOUND in `git log`
- `uv run pytest tests/test_viz/ -q` → 30 passed; `uv run pytest tests/test_viz/test_mermaid_escape.py -q` → 18 passed (was 11 before plan: +7 from 3 new test functions, one parametrized over 5 cases)
- `uv run pytest tests/ -q` → 299 passed
- `uv run ruff format --check src/token_world/viz/mermaid.py` → exit 0
- `uv run ruff check src/` → clean
- `uv run mypy src/token_world/viz/` → exit 0
- Adversarial probe: `escape_label('<script>alert(1)</script>')` → `'&lt;script&gt;alert(1)&lt;/script&gt;'` (no `<script` substring)
- CLI smoke test (task 14.3): `viz_gap_14.mmd` contained `flowchart LR` and `alice &lt;the brave&gt;` with no raw `<the`

---
*Phase: 03-design-validation*
*Completed: 2026-04-13*
