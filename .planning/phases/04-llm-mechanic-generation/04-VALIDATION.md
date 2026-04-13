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

<!--
Rows will be appended by each plan's final task:
- 04-02 Task 4 appends 04-02-T1 through 04-02-T4
- 04-03 Task 3 appends 04-03-T1 through 04-03-T4
- 04-03 Task 4 (NEW — registry→sink wiring, closes D-15) appends 04-03-T5
- 04-04 Task 3 appends 04-04-T1 through 04-04-T4 (now includes 04-04-T3 for invariant test + 04-04-T4 phase-gate)
- 04-05 through 04-11 append their own rows
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
