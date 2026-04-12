---
phase: 2
slug: mechanic-framework
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | MECH-01 | — | N/A | unit | `uv run pytest tests/test_mechanic/ -x -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | MECH-02 | — | N/A | unit | `uv run pytest tests/test_mechanic/ -x -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | TEST-01 | — | N/A | unit | `uv run pytest tests/test_mechanic/ -x -q` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | MECH-05, MECH-06 | — | N/A | unit | `uv run pytest tests/test_mechanic/ -x -q` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | AUTO-03 | — | N/A | integration | `uv run pytest tests/test_mechanic/ -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mechanic/` — test directory for mechanic module
- [ ] `tests/test_mechanic/conftest.py` — shared fixtures (graph builder, universe fixtures)

*Existing pytest infrastructure covers framework needs. New test directory needed for mechanic module.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
