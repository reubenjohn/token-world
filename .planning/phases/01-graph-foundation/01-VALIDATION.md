---
phase: 1
slug: graph-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | GRAPH-01 | — | N/A | unit | `uv run pytest tests/test_graph/ -x -q` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | GRAPH-02 | — | N/A | unit | `uv run pytest tests/test_graph/ -x -q` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | GRAPH-03 | — | N/A | unit | `uv run pytest tests/test_graph/ -x -q` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | GRAPH-04 | — | N/A | unit | `uv run pytest tests/test_graph/ -x -q` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | GRAPH-05 | — | N/A | unit | `uv run pytest tests/test_graph/ -x -q` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 2 | TEST-03 | — | N/A | integration | `uv run pytest tests/test_graph/ -x -q` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 3 | TEST-06 | — | N/A | unit | `uv run pytest tests/test_graph/ -x -q` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 3 | AUTO-01 | — | N/A | manual | Review CLAUDE.md content | ❌ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_graph/` — test directory for graph module
- [ ] `tests/test_graph/conftest.py` — shared graph fixtures and builders
- [ ] `tests/test_graph/test_knowledge_graph.py` — stubs for GRAPH-01 through GRAPH-05
- [ ] `tests/test_graph/test_snapshots.py` — stubs for TEST-03 (snapshot round-trip)
- [ ] `tests/test_graph/test_helpers.py` — stubs for TEST-06 (convenience builders)

*Existing pytest infrastructure in `tests/conftest.py` covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CLAUDE.md completeness | AUTO-01 | Content quality assessment | Review CLAUDE.md for architecture overview, critical constraints, validation protocols, and script catalog |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
