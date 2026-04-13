---
phase: 4
slug: llm-mechanic-generation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (project-standard; see `pyproject.toml`) |
| **Config file** | `pyproject.toml` + existing `tests/conftest.py`, `tests/test_graph/conftest.py` |
| **Quick run command** | `uv run pytest -x -q` |
| **Full suite command** | `uv run pytest -v` |
| **Estimated runtime** | ~30–60 seconds (full suite at end of phase, including 35 parametrized use-case tests + 27 seed-mechanic unit tests) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest -v`
- **Before `/gsd-verify-work`:** Full suite must be green + `uv run ruff check src/` clean + `uv run mypy src/token_world/mechanic/` clean
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

*To be filled by planner. Each plan task must emit a row here or declare a Wave 0 dependency.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-T1 | 04-01 | 1 | MECH-05 | — | Flat module discovery; Mechanic.tags default; import filter prevents base re-detection | unit | `uv run pytest tests/test_mechanic/test_loader.py -x -q` | ✓ (created) | ✅ passing |
| 04-01-T2 | 04-01 | 1 | MECH-06 | T-04-REGISTRY-SHADOWING | Registry rejects duplicate ids with ValueError | unit | `uv run pytest tests/test_mechanic/test_registry.py tests/test_mechanic/test_seeds/ -x -q` | ✓ (created) | ✅ passing |
| 04-01-T3 | 04-01 | 1 | UNIV-03 | — | MCP surface = 3 tools; scaffold copies flat files; mirrored test tree | unit | `uv run pytest tests/test_mcp_server.py tests/test_universe/test_scaffold.py -x -q` | ✓ (exists) | ✅ passing |
| 04-01-T4 | 04-01 | 1 | — (prereq H-01/M-04) | — | find_state_at_tick replays add_node; loader accepts CRLF | unit | `uv run pytest tests/test_graph/test_temporal_index.py::test_find_state_at_tick_handles_remove_then_readd tests/test_design_validation/test_use_case_schema.py::test_load_use_case_accepts_crlf_frontmatter -x -q` | ✓ (created) | ✅ passing |
| 04-01-T5 | 04-01 | 1 | MECH-05,MECH-06,UNIV-03 | — | Full suite green; lint + mypy clean | phase-gate | `uv run pytest -x -q && uv run ruff check src/ && uv run ruff format --check src/` | ✓ | ✅ passing |
| 04-02-T1 | 04-02 | 2 | MECH-04 | T-04-AST-BYPASS | AST visitor flags forbidden imports + calls; accumulates all findings before fail | unit | `uv run pytest tests/test_mechanic/test_validation.py -x -q` | ✓ (created) | ✅ passing |
| 04-02-T2 | 04-02 | 2 | MECH-04 | — | All 21 per-stage + per-rule validation tests cover D-14 | unit | `uv run pytest tests/test_mechanic/test_validation.py -x -q` | ✓ | ✅ passing |
| 04-02-T3 | 04-02 | 2 | MECH-03,MECH-04 | T-04-TEST-EXEC | validate-mechanic CLI; registry auto-scan excludes invalid; subprocess uses argv list (no shell=True) | integration | `uv run pytest tests/test_cli/test_validate_mechanic.py tests/test_mechanic/test_registry.py -x -q` | ✓ (created) | ✅ passing |
| 04-02-T4 | 04-02 | 2 | MECH-03,MECH-04 | — | Full suite + lint + format + mypy clean | phase-gate | `uv run pytest -x -q && uv run ruff check src/ && uv run ruff format --check src/ && uv run mypy src/token_world/mechanic/` | ✓ | ✅ passing |
| 04-03-T1 | 04-03 | 2 | AUTO-02 | T-04-DIAG-JSON-INJECTION | summary.json / trace.json / parsed.json written via atomic JSON dump; readers parse with json.loads; no eval/exec/yaml.load in diagnostics.py | unit | `uv run pytest tests/test_mechanic/test_diagnostics.py -x -q` | ✓ | ✅ passing |
| 04-03-T2 | 04-03 | 2 | AUTO-02 | T-04-DIAG-PATH-TRAVERSAL | open_validation sanitises mechanic_id; final path verified under root; symlink-safe tmp sweep | unit | `uv run pytest tests/test_mechanic/test_diagnostics.py::test_open_validation_sanitizes_dangerous_mechanic_id tests/test_mechanic/test_diagnostics.py::test_boot_time_cleanup_removes_stale_tmp_files tests/test_mechanic/test_diagnostics.py::test_boot_time_cleanup_does_not_follow_symlinks -x` | ✓ | ✅ passing |
| 04-03-T3 | 04-03 | 2 | AUTO-02 | T-04-PRUNE-DESTRUCTION | prune dry-run by default; skips symlinks; verifies path-under-root before rmtree | unit | `uv run pytest tests/test_mechanic/test_diagnostics.py::test_prune_dry_run_returns_candidates_without_deleting tests/test_mechanic/test_diagnostics.py::test_prune_refuses_to_follow_symlinks tests/test_mechanic/test_diagnostics.py::test_prune_refuses_path_outside_root_when_symlinked -x` | ✓ | ✅ passing |
| 04-03-T4 | 04-03 | 2 | AUTO-02 | — | prune-diagnostics CLI: dry-run default, --confirm deletes, usage errors exit 2, missing universe exits 1 | integration | `uv run pytest tests/test_cli/test_prune_diagnostics.py -x -q` | ✓ | ✅ passing |
| 04-03-T5 | 04-03 | 2 | AUTO-02, MECH-04 | T-04-DIAG-PATH-TRAVERSAL | Registry→sink wiring closes D-15 loop: failing validation reports persist to `diagnostics/validation/<ts>_<id>/report.json`; sink-write failures degrade to warnings, registry keeps indexing | integration | `uv run pytest tests/test_mechanic/test_registry.py::TestRegistrySinkWiring -x -q` | ✓ | ✅ passing |
| 04-05-T1 | 04-05 | 2 | MECH-03 | T-04-AST-BYPASS | Authoring guide explicitly states AST rules are NOT a sandbox; documents blocked_by stub convention (D-38); absorbs GAP-MECH19 + GAP-MECH26 rationale | doc | `test $(wc -l < docs/guides/authoring-mechanics.md) -ge 400 && grep -q "NOT a sandbox\|not a sandbox" docs/guides/authoring-mechanics.md && grep -q "blocked_by" docs/guides/authoring-mechanics.md` | ✓ (created) | ✅ passing |
| 04-05-T2 | 04-05 | 2 | AUTO-03, MECH-03 | T-04-SCAFFOLD-ID-TRAVERSAL | scaffold-mechanic CLI: regex `^[a-z][a-z0-9_]*$` rejects traversal; refuses overwrites; scaffolded skeleton passes validation; scaffold copies docs/guides/authoring-mechanics.md byte-identical to <universe>/docs/authoring-mechanics.md | integration | `uv run pytest tests/test_cli/test_scaffold_mechanic.py tests/test_universe/test_scaffold.py -x -q` | ✓ | ✅ passing |
| 04-05-T3 | 04-05 | 2 | AUTO-03, MECH-03 | — | Full suite green; lint clean on files touched by this plan | phase-gate | `uv run pytest -x -q && uv run ruff check src/token_world/cli.py src/token_world/universe/scaffold.py src/token_world/universe/templates/claude_md.py` | ✓ | ✅ passing |
| 04-04-T1 | 04-04 | 3 | — (schema extension) | — | expected_outcome is optional; invalid values rejected; UC-S01 annotated as yield canary | unit | `uv run pytest tests/test_design_validation/test_use_case_schema.py -x -q` | ✓ | ✅ passing |
| 04-04-T2 | 04-04 | 3 | TEST-02 | T-04-HARNESS-EXEC, T-04-MANIFEST-SCHEMA-DRIFT | Harness collects 35 UCs; explicit outcome branching via pytest.xfail/fail/skip; DiagnosticsSink exercised per test; import-safe discovery | integration | `uv run pytest tests/test_integration/test_use_cases.py -q` | ✓ (created) | ✅ passing |
| 04-04-T3 | 04-04 | 3 | TEST-02 | — | Invariant: every manifest has a valid expected_outcome (authoritative pytest check, not grep) | unit | `uv run pytest tests/test_use_cases/test_manifest_outcomes.py -q` | ✓ (created) | ✅ passing |
| 04-04-T4 | 04-04 | 3 | TEST-02 | — | Full suite green after manifest annotations (skips + xfails only, no fails) | phase-gate | `uv run pytest tests/test_integration/ tests/test_use_cases/ -q && uv run pytest -x -q` | ✓ | ✅ passing |
| 04-06-T1 | 04-06 | 4 | MECH-03 | — | MECH01 passage_move validates; doorway + direct-connects + bridge paths honored; closed doorway refused | unit | `uv run pytest tests/test_mechanic/test_seeds/test_passage_move.py -x -q` | ✓ | ⬜ pending |
| 04-06-T2 | 04-06 | 4 | MECH-03 | — | MECH05 terrain_move + MECH06 position_sync validate; UC-V05 stamina 20→18; position_sync fires reactively via ChainExecutionEngine | unit | `uv run pytest tests/test_mechanic/test_seeds/test_terrain_move.py tests/test_mechanic/test_seeds/test_position_sync.py -x -q` | ✓ | ⬜ pending |
| 04-06-T3 | 04-06 | 4 | MECH-03, TEST-02 | — | UC-S01 / UC-S06 / UC-S07 / UC-V05 flipped to expected_outcome=pass; harness green on all four | integration | `uv run pytest tests/test_integration/test_use_cases.py -k "UC-S01 or UC-S06 or UC-S07 or UC-V05" -q` | ✓ | ⬜ pending |
| 04-07-T1 | 04-07 | 4 | MECH-03 | — | MECH02/03/04 spatial-query mechanics validate + pass tests | unit | `uv run pytest tests/test_mechanic/test_seeds/test_look.py tests/test_mechanic/test_seeds/test_find_nearest.py tests/test_mechanic/test_seeds/test_aoe.py -x -q` | ✓ | ⬜ pending |
| 04-07-T2 | 04-07 | 4 | MECH-03 | — | MECH13/27 speak + try_door validate + refusal-narrative pattern | unit | `uv run pytest tests/test_mechanic/test_seeds/test_speak.py tests/test_mechanic/test_seeds/test_try_door.py -x -q` | ✓ | ⬜ pending |
| 04-07-T3 | 04-07 | 4 | MECH-03, TEST-02 | — | UC-S02/S03/S04/O08/E06 flip to pass | integration | `uv run pytest tests/test_integration/test_use_cases.py -k "UC-S02 or UC-S03 or UC-S04 or UC-O08 or UC-E06" -x -q` | ✓ | ⬜ pending |
| 04-08-T1 | 04-08 | 4 | MECH-03 | — | MECH15/16 consume + pickup; _count_holds + _refuse_with_narrative helpers | unit | `uv run pytest tests/test_mechanic/test_seeds/test_pickup.py tests/test_mechanic/test_seeds/test_consume.py -x -q` | ✓ | ✅ passing |
| 04-08-T2 | 04-08 | 4 | MECH-03 | — | MECH07/08/14 trade + give + craft | unit | `uv run pytest tests/test_mechanic/test_seeds/test_trade.py tests/test_mechanic/test_seeds/test_give.py tests/test_mechanic/test_seeds/test_craft.py -x -q` | ✓ | ✅ passing |
| 04-08-T3 | 04-08 | 4 | MECH-03, TEST-02 | T-04-AST-BYPASS | 6 object-interaction UCs flip from yield/blocked to pass (UC-O01 single-tick; multi-turn is GAP-ENG01 Phase 5) | integration | `uv run pytest tests/test_integration/test_use_cases.py -k "UC-O01 or UC-O03 or UC-R01 or UC-R02 or UC-R03 or UC-R04" -x -q` | ✓ | ✅ passing |
| 04-09-T1 | 04-09 | 4 | MECH-03 | — | MECH10/11/25 tell+teach+belief_update validate + tests | unit | `uv run pytest tests/test_mechanic/test_seeds/test_tell.py tests/test_mechanic/test_seeds/test_teach.py tests/test_mechanic/test_seeds/test_belief_update.py -x -q` | ✓ | ✅ passing |
| 04-09-T2 | 04-09 | 4 | MECH-03 | T-04-STUB-IMPORT-LEAK | MECH09/12 stubs validate; blocked_by convention wired in harness; UC-O02 routes via GAP-ENG03, UC-O06 via GAP-ENG05 | integration | `uv run pytest tests/test_mechanic/test_seeds/test_persuade.py tests/test_mechanic/test_seeds/test_cooperate.py tests/test_mechanic/test_harness_matcher.py tests/test_integration/test_use_cases.py -k "UC-O02 or UC-O06" -x -q` | ✓ | ✅ passing |
| 04-09-T3 | 04-09 | 4 | MECH-03, TEST-02 | — | UC-O04/O05/E03 flip to pass; UC-O02/O06 correctly blocked via stub gap ids | integration | `uv run pytest tests/test_integration/test_use_cases.py -k "UC-O02 or UC-O04 or UC-O05 or UC-O06 or UC-E03" -q` | ✓ | ✅ passing |
| 04-10-T1 | 04-10 | 4 | MECH-03 | T-04-AST-BYPASS | MECH17/18 degrade + fungible_pay validate + tests; _subset_sum helper graduated to _helpers.py | unit | `uv run pytest tests/test_mechanic/test_seeds/test_degrade.py tests/test_mechanic/test_seeds/test_fungible_pay.py -x -q` | ✓ | ✅ passing |
| 04-10-T2 | 04-10 | 4 | MECH-03, TEST-02 | — | UC-R06 flips yield -> pass (verb pay -> fungible_pay; pending_payment staged); UC-R05 stays blocked per decision tree (GAP-ENG02 routing + threshold-flag semantics mismatch documented inline) | integration | `uv run pytest tests/test_integration/test_use_cases.py -k "UC-R05 or UC-R06" -q` | ✓ | ✅ passing |

<!--
Rows will be appended by each plan's final task:
- 04-02 Task 4 appends 04-02-T1 through 04-02-T4
- 04-03 Task 3 appends 04-03-T1 through 04-03-T4
- 04-03 Task 4 (NEW — registry→sink wiring, closes D-15) appends 04-03-T5
- 04-04 Task 3 appends 04-04-T1 through 04-04-T4 (now includes 04-04-T3 for invariant test + 04-04-T4 phase-gate)
- 04-05 through 04-11 append their own rows
- 04-06 Task 3 appends 04-06-T1 through 04-06-T3 (passage_move / terrain_move / position_sync + 4 UC flips)
- 04-12 Task 1 flips all ⬜ pending to ✅ done and flips frontmatter
-->

---

## Wave 0 Requirements

- [ ] `tests/test_mechanic/test_validation.py` — unit tests for AST walker + ValidationReport (MECH-04)
- [ ] `tests/test_mechanic/test_loader_flat.py` — new module-based discovery (MECH-03)
- [ ] `tests/test_mechanic/test_diagnostics.py` — DiagnosticsSink API + atomic writes (AUTO-02)
- [ ] `tests/test_integration/conftest.py` — shared fixtures for use-case-driven tests (TEST-02)
- [ ] `tests/test_integration/test_use_cases.py` — parametrized harness stub (TEST-02)
- [ ] `tests/test_use_cases/test_manifest_outcomes.py` — invariant: every UC manifest has a valid `expected_outcome` (TEST-02 / W7 mitigation from 04-04)
- [ ] `tests/test_mechanic/test_seeds/` — mirrored seed test tree (MECH-03)
- [ ] No new framework install required (pytest already in `pyproject.toml`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Authoring-guide quality | MECH-03 (readability) | Prose quality not grep-able | Read `docs/guides/authoring-mechanics.md` end-to-end; attempt to author a new mechanic using only the guide |
| Operator SDLC feel | MECH-03 (ergonomics) | Qualitative dogfooding | `cd` into a scaffolded universe; author one mechanic; run `validate-mechanic`; assess friction |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
