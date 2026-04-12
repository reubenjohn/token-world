---
phase: 0
slug: universe-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 0 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml (Wave 0 installs) |
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
| 00-01-01 | 01 | 1 | UNIV-01 | — | N/A | unit | `uv run pytest tests/test_universe_manager.py -k test_create` | ❌ W0 | ⬜ pending |
| 00-01-02 | 01 | 1 | UNIV-04 | — | N/A | unit | `uv run pytest tests/test_universe_manager.py -k test_load` | ❌ W0 | ⬜ pending |
| 00-01-03 | 01 | 1 | UNIV-04 | — | N/A | unit | `uv run pytest tests/test_universe_manager.py -k test_list` | ❌ W0 | ⬜ pending |
| 00-01-04 | 01 | 1 | UNIV-04 | — | N/A | unit | `uv run pytest tests/test_universe_manager.py -k test_delete` | ❌ W0 | ⬜ pending |
| 00-02-01 | 02 | 1 | UNIV-02 | — | N/A | unit | `uv run pytest tests/test_claude_md.py` | ❌ W0 | ⬜ pending |
| 00-02-02 | 02 | 1 | UNIV-03 | — | N/A | unit | `uv run pytest tests/test_mcp_json.py` | ❌ W0 | ⬜ pending |
| 00-02-03 | 02 | 1 | UNIV-05 | — | N/A | unit | `uv run pytest tests/test_agents_md.py` | ❌ W0 | ⬜ pending |
| 00-03-01 | 03 | 2 | UNIV-06 | — | N/A | integration | `uv run pytest tests/test_tick_summaries.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (tmp_path universes)
- [ ] `tests/test_universe_manager.py` — stubs for UNIV-01, UNIV-04
- [ ] `tests/test_claude_md.py` — stubs for UNIV-02
- [ ] `tests/test_mcp_json.py` — stubs for UNIV-03
- [ ] `tests/test_agents_md.py` — stubs for UNIV-05
- [ ] `tests/test_tick_summaries.py` — stubs for UNIV-06
- [ ] pytest installed via `uv add --dev pytest`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Claude Code discovers MCP tools from .mcp.json | UNIV-03 | Requires live Claude Code session | Open universe folder in Claude Code, verify tool list shows resume_tick, rollback, list_mechanics, register_mechanic |
| AGENTS.md symlink works cross-harness | UNIV-05 | Requires multiple harness installs | Verify `readlink AGENTS.md` points to CLAUDE.md, open in Codex if available |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
