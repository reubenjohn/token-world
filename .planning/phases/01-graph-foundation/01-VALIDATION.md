---
phase: 1
slug: graph-foundation
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-11
audited: 2026-04-11
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
| **Estimated runtime** | ~1 second |
| **Total tests** | 59 |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test File | Key Tests | Status |
|---------|------|------|-------------|-----------|-----------|--------|
| 01-01-01 | 01 | 1 | GRAPH-01 | `test_knowledge_graph.py` | `test_arbitrary_properties`, `test_edge_arbitrary_properties`, `test_allowed_types` | ✅ green |
| 01-01-02 | 01 | 1 | GRAPH-02 | `test_knowledge_graph.py` | `test_emergent_property`, `test_set_property` | ✅ green |
| 01-01-03 | 01 | 1 | GRAPH-03 | `test_persistence.py` | `test_save_load_roundtrip`, `test_persist_survives_restart`, `test_directed_graph_preserved` | ✅ green |
| 01-01-04 | 01 | 1 | TEST-06 | `test_knowledge_graph.py` | `test_graph_builder`, `test_graph_builder_chaining` | ✅ green |
| 01-02-01 | 02 | 2 | GRAPH-04 | `test_snapshots.py` | `test_snapshot_creation`, `test_snapshot_linked_to_tick`, `test_snapshot_with_summary` | ✅ green |
| 01-02-02 | 02 | 2 | GRAPH-05 | `test_snapshots.py` | `test_restore_basic`, `test_restore_nodes`, `test_restore_edges`, `test_restore_properties`, `test_restore_directed`, `test_multiple_snapshots_restore_any` | ✅ green |
| 01-02-03 | 02 | 2 | TEST-03 | `test_snapshots.py` | `test_roundtrip_integrity` | ✅ green |
| 01-03-01 | 03 | 3 | AUTO-01 | — | Manual review | ✅ verified |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Test Coverage by Module

| Test File | Tests | Covering |
|-----------|-------|----------|
| `test_knowledge_graph.py` | 29 | GRAPH-01, GRAPH-02, TEST-06, node types (D-01), property validation (D-04), mutations, events |
| `test_identity.py` | 3 | claim_id deconfliction (D-02) |
| `test_persistence.py` | 8 | GRAPH-03, SQLite roundtrip, directed graph preservation, event persistence |
| `test_snapshots.py` | 22 | GRAPH-04, GRAPH-05, TEST-03, snapshot retention, event compaction |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Status |
|----------|-------------|------------|-------------------|--------|
| CLAUDE.md completeness | AUTO-01 | Content quality assessment | Review CLAUDE.md for architecture overview, critical constraints, validation protocols, and script catalog | ✅ verified |

---

## Validation Audit 2026-04-11

| Metric | Count |
|--------|-------|
| Requirements audited | 8 |
| Covered (automated) | 7 |
| Covered (manual) | 1 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or manual coverage
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 1s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified 2026-04-11
