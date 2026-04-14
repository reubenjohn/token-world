---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Quality + Depth
status: active
stopped_at: v1.2 formally opened; warm-up already shipped in session 6; active backlog pending roadmap
last_updated: "2026-04-14T00:00:00.000Z"
last_activity: 2026-04-14 -- v1.1 retroactively archived; v1.2 milestone opened; v2.0 backlog stub created
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14 at v1.2 milestone open)

**Core value:** The simulation engine reliably interprets agent actions, yields to the operator for novel situations, and maintains a consistent knowledge graph — so from a resident agent's perspective, the world feels fully real and its rules emerge coherently.
**Current focus:** v1.2 Quality + Depth — truthful engine, grounded observer, richer play via composite actions + multi-agent scaffold, quality KPIs + CI gating, seed corpus expansion, graph conventions codification.

## Current Position

Milestone v1.2 opened 2026-04-14 — see `.planning/REQUIREMENTS.md` for REQ-V12-* detail.

11 warm-up requirements shipped pre-formal-scaffolding (sessions 4–6 direct-edit + subagent work). The remaining active backlog is 20 REQ-V12-* items spanning:

- Engine truthfulness (3 remaining)
- Dashboard UX + multi-agent scaffold (5)
- Operator CLI extensions (2)
- Quality KPIs (1)
- Seed corpus + graph conventions (5)
- Emergence tooling (2)
- Ops + tooling (2)

Progress: [░░░░░░░░░░] 0% — roadmapper will scaffold phases on next invocation. 11 warm-up items already done but not yet counted in the phase framework.

Tests: 1952 passing at milestone open (up from 1687 at v1.0 close, 1885 at v1.1 close).

## v1.2 milestone scope

**Inclusive scope mandate (user, session 6):** every remaining requirement across the project lands in v1.2 unless it's "really a very far-fetched" item, in which case it goes into `.planning/backlog/v2.0-REQUIREMENTS.md`. See that file for the 15 REQ-V20-* items parked for the next milestone after v1.2.

**Warm-up delivered (sessions 4–6 direct-edit, pre-formal-scaffolding):**

- REQ-V12-ENGINE-01 primary-check-fail → RefuseDecision (commit `afc5c73`)
- REQ-V12-ENGINE-02 observer grounding to mutation list (commit `e110e2c`)
- REQ-V12-DASHBOARD-01..04 dashboard scroll/expansion/side-effect-chain/graph-edges (`d31090d`, `6101da0`)
- REQ-V12-CLI-01 inspect table headers (`fa68200`)
- REQ-V12-CLI-02 `token-world yield` CLI + Active Yield banner (`7435536`)
- REQ-V12-PLAYTEST-01 Mira prompt tightening + auto-halt (`0fcd614`)
- REQ-V12-ECONOMY-01 Willowbrook `_economy.py` (universe commit `ce671cd`)
- REQ-V12-QUALITY-01 dashboard QA + sim-quality rubric docs (`890b464`)
- REQ-V12-DOCS-01 tooling-surfaces.md (`3eec1c5`)
- REQ-V12-TOOLING-01 `commit.sh` explicit paths (`958a28b`)

## Accumulated Context

### Decisions (v1.1 — archived; kept for cross-milestone reference)

- **v1.1 D-01 (NiceGUI for dashboard stack):** revisits the FastAPI/Flask ban. Validated through v1.1 ship.
- **v1.1 D-02 (External-operator mode canonical unattended path):** validated through overnight run — 11 mechanics authored, zero API spend.
- **v1.1 D-03 (Single-agent baseline):** carried into v1.2. Multi-agent engine cutover remains v2 (REQ-V20-MULTI-01); v1.2 only ships the dashboard *scaffold* (REQ-V12-DASHBOARD-05).

### Decisions (v1.2 — pending)

Placeholder; decisions for v1.2 will be tracked here as they land:
- D-01 (v1.2) TBD — composite-action decomposition choice (§E1 options 1/2/3 — recommended option 1)
- D-02 (v1.2) TBD — locked/blocked/inventory_full audit conventions (surfaces into `docs/design/graph-conventions.md`)
- D-03 (v1.2) TBD — engine treats "check failed at execution time" as hard refusal (partially landed via REQ-V12-ENGINE-01; remaining scope on sibling check-fail paths)

### Pending Todos

- Roadmapper subagent invocation to scaffold v1.2 phases
- Historical tick-summary migration (REQ-V12-OPS-02, optional) for willowbrook ticks 22/34/38

### Blockers/Concerns

- None at milestone open. Warm-up items shipped; CI green; 1952 tests passing.

## Session Continuity

Last session: 2026-04-14 session 6 close + v1.2 milestone open (this pass)
Stopped at: v1.1 archived; v1.2 formally scaffolded; v2.0 backlog stub created; roadmapper pending
Resume file: `.planning/REQUIREMENTS.md` + `.planning/backlog/v2.0-REQUIREMENTS.md`

**Next action:** spawn roadmapper subagent to lay down v1.2 phase structure against the 20 active REQ-V12-* items.
