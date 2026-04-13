---
phase: 5
slug: simulation-engine
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-13
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (project standard) |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `uv run pytest tests/test_engine/ -x -q` |
| **Full suite command** | `uv run pytest -v` |
| **Integration suite** | `uv run pytest -m integration` (real LLM; excluded from default) |
| **Lint** | `uv run ruff check src/token_world/engine/ src/token_world/mechanic/` |
| **Format check** | `uv run ruff format --check src/` |
| **Type check** | `uv run mypy src/token_world/engine/` |
| **Estimated runtime** | ~20 seconds (unit), ~3 minutes (integration) |

---

## Sampling Rate

- **After every task commit:** Run quick run command on affected tests
- **After every plan wave:** Run full unit suite (`uv run pytest tests/test_engine/ -q`)
- **Before `/gsd-verify-work`:** Full unit suite green + integration suite green
- **Max feedback latency:** 20 seconds (unit); 180 seconds (integration)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Gap IDs | Test Type | Automated Command | Status |
|---------|------|------|-------------|---------|-----------|-------------------|--------|
| 05-01-01 | 01 | 0 | SIM-01 | GAP-ENG11, GAP-ENG15, GAP-ENG02, GAP-ENG16(P5) | unit | `uv run pytest tests/test_engine/test_models.py tests/test_engine/test_classifier.py -q` | ⬜ pending |
| 05-01-02 | 01 | 0 | SIM-01 | GAP-GRAPH05 | unit | `uv run pytest tests/test_engine/test_config.py tests/test_mechanic/test_context_rng.py -q` | ⬜ pending |
| 05-01-03 | 01 | 0 | — | GAP-GRAPH05 | unit | `uv run pytest tests/test_mechanic/test_validation_ast_rng.py -q` | ⬜ pending |
| 05-02-01 | 02 | 1 | SIM-02 | GAP-ENG09 | unit | `uv run pytest tests/test_engine/test_matcher.py -q` | ⬜ pending |
| 05-02-02 | 02 | 1 | SIM-02 | GAP-ENG09 | unit | `uv run pytest tests/test_mechanic/test_matchers_world_decay_tick.py -q` | ⬜ pending |
| 05-03-01 | 03 | 1 | SIM-03 | GAP-CROSS02 | unit | `uv run pytest tests/test_engine/test_decider.py tests/test_engine/test_refusal.py -q` | ⬜ pending |
| 05-04-01 | 04 | 1 | SIM-05, SIM-07 | GAP-CROSS01, GAP-GRAPH04 | unit | `uv run pytest tests/test_engine/test_visibility.py -q` | ⬜ pending |
| 05-05-01 | 05 | 1 | SIM-05 | GAP-ENG12 | unit | `uv run pytest tests/test_engine/test_observer.py -q` | ⬜ pending |
| 05-06-01 | 06 | 1 | SIM-08 | GAP-ENG06 | unit | `uv run pytest tests/test_engine/test_conservation.py -q` | ⬜ pending |
| 05-07-01 | 07 | 1 | SIM-04 | GAP-ENG07, GAP-ENG17, GAP-ENG18 | unit | `uv run pytest tests/test_engine/test_passive_sweep.py -q` | ⬜ pending |
| 05-08-01 | 08 | 2 | SIM-04, SIM-06, SIM-11, AUTO-02 | all P5 gaps | integration | `uv run pytest tests/test_engine/test_engine.py tests/test_engine/test_tick_summary.py -q` | ⬜ pending |
| 05-09-01 | 09 | 2 | SIM-03 | — | integration | `uv run pytest tests/test_operator/test_integration.py -m integration` | ⬜ pending |
| 05-10-01 | 10 | 2 | UNIV-03 | — | unit | `uv run pytest tests/test_mcp_server.py -q` | ⬜ pending |
| 05-11-01 | 11 | 2 | — | — | unit | `uv run pytest tests/test_cli/test_engine_turn.py -q` | ⬜ pending |
| 05-12-01 | 12 | 2 | ALL | ALL | integration | `uv run pytest tests/test_engine/test_use_case_regression.py -m integration` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Plan 05-01 (Wave 0) creates Wave-1 prerequisites:

- [ ] `src/token_world/engine/__init__.py` — package init
- [ ] `src/token_world/engine/models.py` — Pydantic models (`ClassifierVerdict`, `ClassifiedAction`, `MatchResult`, `Decision`, `TickSummary`)
- [ ] `src/token_world/engine/config.py` — `EngineConfig` loader
- [ ] `src/token_world/engine/classifier.py` — Haiku wrapper
- [ ] `src/token_world/mechanic/context.py` modified — `ctx.rng` property
- [ ] `src/token_world/mechanic/validation.py` modified — `import random` AST rule
- [ ] `src/token_world/universe/scaffold.py` modified — seed `universe.yaml` with `universe_seed`
- [ ] `tests/test_engine/__init__.py` — test package
- [ ] `tests/test_engine/conftest.py` — shared fixtures: temp universe, mock-haiku, mock-sonnet, seeded RNG

All six Wave-1 plans (05-02 through 05-07) depend on Plan 05-01 Wave-0 scaffolding being complete.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Classifier calibration on real Haiku with 10 nonsense inputs | SIM-01 (soft quality) | Real-LLM validation of prompt quality | `uv run pytest tests/test_engine/test_classifier_real.py -m integration -v` |
| Observer grounding across 35 UCs | SIM-05 | Phase 6 TEST-04 rubric deferred; Phase 5 ships substring check only | Inspect 05-12 retro run output against use-case manifests |
| End-to-end flow in interactive Claude Code universe | SIM-01..SIM-08 | Interactive-mode smoke; not part of CI | Follow universe CLAUDE.md Operator Flow against a fresh scaffolded universe |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: every plan has automated verify; no gaps
- [x] Wave 0 covers all MISSING references (models, config, classifier, ctx.rng, AST rule)
- [x] No watch-mode flags
- [x] Feedback latency < 20s for unit, < 180s for integration
- [ ] `nyquist_compliant: true` set in frontmatter → **set**

**Approval:** pending final execution.
