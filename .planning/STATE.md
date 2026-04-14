---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Emergence Tooling
status: in_progress
stopped_at: Session 4 close — substrate live, dashboard live, 11 mechanics emerged in Willowbrook overnight run
last_updated: "2026-04-15T10:10:00.000Z"
last_activity: 2026-04-15 -- session 4 overnight: 11 mechanics authored autonomously in Willowbrook (examine, pet, sharpen, walk, draw, plant, force, drop, water, hum, lift)
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 8
  completed_plans: 8
  percent: 80
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15 for v1.1 kickoff)

**Core value:** The simulation engine reliably interprets agent actions, yields to the operator for novel situations, and maintains a consistent knowledge graph — so from a resident agent's perspective, the world feels fully real and its rules emerge coherently.
**Current focus:** v1.1 Emergence Tooling — make unattended universe runs possible; give humans and agents a legible view of what's happening.

## Current Position

Milestone: v1.1 — STARTED 2026-04-15
Phases planned: 4 (warm-up/Tracks A-C + dashboard)
Tests: 1743 passing as of v1.0 close; session 4 still pushing commits

Progress: [░░░░░░░░░░] 0% — phases in flight not yet verified

## Session 4 Closeout (Hybrid Mode, Option `c`)

All four tracks shipped:

- **Track A — Operator CLI Surface (8 commands, 98 tests)** ✅
- **Track B — NiceGUI Dashboard (4 panels + polish, 26 tests)** ✅
- **Track C — Emergence substrate + 11 mechanics from overnight run** ✅
- **Track D — Warm-up backlog + automation** ✅

Plus engine bug fixes that unblocked emergence:
- Classifier permissive-verb prompt (commits `3ffb9f5`, `f84c9b2`)
- Markdown-fence stripper for claude-cli backend (`3ffb9f5`)
- mypy override for transitive nicegui (`131b787`)
- v1.1 milestone retro-scaffolding (`a9c2e39`, `6cc2fe9`)

**Pending for next session (Phase 12 + remaining):**
- REQ-EMERGE-05 mechanic overlap detector
- REQ-EMERGE-07 operator-log enrichment with subagent reasoning
- Multi-agent rotation (precursor to v2 MULTI-01) — re-scope decision
- `commit.sh` paths-arg + non-LRA-seed VerbMatcher backfill (anti-patterns 5/6)

## Accumulated Context

### Decisions (v1.1)

- **D-01 (v1.1): NiceGUI for dashboard stack** — revisits the FastAPI/Flask ban. NiceGUI is Python-native reactive UI; FastAPI is transitive, not direct. Rationale: single-language stack, reactive out of box, acceptable because ban targets direct-app-framework use.
- **D-02 (v1.1): External-operator mode is the canonical unattended path** — `ExternalOperator` file-based protocol keeps the overnight run zero-marginal-cost (subagent-as-operator via caller's Claude Code subscription, not paid Agent SDK).
- **D-03 (v1.1): Single-agent remains the v1.1 baseline** — multi-agent is still v2 (MULTI-01..03). Willowbrook starter universe ships with one resident agent (Mira) + rich environment, not two agents.

### Pending Todos

None new; session 4 subagents are working through the warm-up list.

### Blockers/Concerns

- CI green must be maintained across parallel direct-edit subagents (warm-up + Track A). Sequential commits with prek hooks catch lint drift.

## Session Continuity

Last session: 2026-04-15 session 4 (closed)
Stopped at: 11 mechanics emerged in Willowbrook overnight run; dashboard demoable; report written
Resume file: MORNING-HANDOFF.md + `.planning/OVERNIGHT-REPORT-20260415.md`

**Next action:** Demo the dashboard (`uv run token-world dashboard willowbrook`), review the 11 authored mechanics, decide on Phase 12 (mechanic overlap detector, operator-log enrichment) or v1.2 multi-agent re-scope.

### v1.2 REQUIREMENTS assembled (2026-04-14)

v1.2 REQUIREMENTS.md assembled from MORNING-HANDOFF §I (deferred sweep) + §J (prioritised backlog): **12 active**, **11 shipped pre-milestone**, **12 items retained as v2+ deferred** with rationale. `check_requirements_traceability.py --milestone active` passes; meta tests green.
