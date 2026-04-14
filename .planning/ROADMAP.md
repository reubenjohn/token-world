# Roadmap: Token World

## Overview

Token World is a universe simulator where LLM-powered resident agents inhabit a text-based world whose rules are procedurally authored on-the-fly. v1.0 shipped the full end-to-end loop; v1.1 delivered the emergence tooling (Operator CLI + NiceGUI dashboard + ExternalOperator substrate) that proved unattended mechanic authoring works.

v1.2 (Quality + Depth) is the current milestone, opened 2026-04-14 — absorbing every remaining requirement across the project except the handful of truly far-fetched multi-agent / transactional / distributed items parked in `backlog/v2.0-REQUIREMENTS.md`.

## Milestones

- ✅ **v1.0 MVP** — Phases 0..7, 04.1 + 07.1 inserted (shipped 2026-04-14)
- ✅ **v1.1 Emergence Tooling** — Phases 08..12 (shipped 2026-04-14, retroactively archived)
- 🟢 **v1.2 Quality + Depth** — opened 2026-04-14, phases TBD (roadmapper pending)
- 📋 **v2.0 Far-Fetched** — stub at `backlog/v2.0-REQUIREMENTS.md` (multi-agent engine, distributed/transactional primitives, sandboxing)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 0, 1, 2, 3, 4, 04.1, 5, 6, 7, 07.1) — SHIPPED 2026-04-14</summary>

- [x] Phase 0: Universe Infrastructure (2/2 plans)
- [x] Phase 1: Graph Foundation (3/3 plans)
- [x] Phase 2: Mechanic Framework (3/3 plans)
- [x] Phase 3: Design Validation (15/15 plans — 12 planned + 3 follow-up fixes)
- [x] Phase 4: Mechanic Authoring & Validation Infrastructure (12/12 plans)
- [x] Phase 04.1: Operator Agent Harness (INSERTED) (5/5 plans)
- [x] Phase 5: Simulation Engine (9/9 plans)
- [x] Phase 6: Resident Agent & End-to-End Loop (7/7 plans)
- [x] Phase 7: Attention & Consciousness (7/7 plans)
- [x] Phase 07.1: claude-cli LLM Backend (INSERTED) (2/2 plans)

**Full details:** [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
**Requirements snapshot:** [milestones/v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)
**Summary entry:** [MILESTONES.md](MILESTONES.md)

</details>

<details>
<summary>✅ v1.1 Emergence Tooling (Phases 08..12) — SHIPPED 2026-04-14</summary>

- [x] Phase 08: Emergence Substrate (3/3 plans retroactive) — ExternalOperator + seed Willowbrook + unattended runner
- [x] Phase 09: Operator CLI Surface (6/6 plans retroactive) — `inspect/tick/trace/mechanics/stats/watch` + P1 `agents/diff`
- [x] Phase 10: Warm-up Backlog + Automation (direct-edit; no PLANs) — 6 v1.0 Known Gaps burned down
- [x] Phase 11: NiceGUI Dashboard (5/5 plans — full GSD) — 4 panels, 26 tests
- [x] Phase 12: Overnight Orchestration (experiment; no PLANs) — 11 mechanics authored autonomously

**Full details:** [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
**Requirements snapshot:** [milestones/v1.1-REQUIREMENTS.md](milestones/v1.1-REQUIREMENTS.md)
**Summary entry:** [MILESTONES.md](MILESTONES.md)

</details>

### 🟢 v1.2 Quality + Depth (opened 2026-04-14)

**Vision:** Harden truthfulness of the emergence loop (engine bugs, observer grounding, dashboard UX) and open the door to richer play (composite actions, multi-agent scaffold, quality KPIs). Inclusive milestone — every remaining requirement across the project lives here unless truly far-fetched.

**Warm-up delivered (sessions 4–6 direct-edit, pre-formal-scaffolding):** 11 REQ-V12-* items shipped. See `milestones/v1.2` REQUIREMENTS (the live `.planning/REQUIREMENTS.md` until milestone close).

**Phases TBD — roadmapper subagent will fill in when spawned against REQUIREMENTS.md.** Active scope spans:

- Engine truthfulness completion (REQ-V12-ENGINE-03..05)
- Dashboard UX + multi-agent scaffold + run-status + agent inspector + mechanic timeline (REQ-V12-DASHBOARD-05..09)
- Operator CLI extensions (REQ-V12-CLI-03..04)
- Quality KPIs subpackage + CLI + panel (REQ-V12-QUALITY-02)
- Seed corpus expansion + Willowbrook refinement (REQ-V12-SEEDS-01, REQ-V12-TOOLING-02)
- Graph conventions codification (REQ-V12-GRAPH-01..04)
- Emergence tooling carried from v1.1 (REQ-V12-EMERGE-01..02)
- Ops (REQ-V12-OPS-01..02)

See `.planning/REQUIREMENTS.md` for the full REQ-V12 table; phase breakdown follows.

## Progress

**Execution Order:**
Phases execute in numeric order within each milestone. Decimal phases (e.g., 04.1) are urgent insertions between integer phases.

### v1.0 (Shipped 2026-04-14)

| Phase | Milestone | Plans Complete | Status   | Completed  |
|-------|-----------|----------------|----------|------------|
| 0. Universe Infrastructure | v1.0 | 2/2 | Complete | 2026-04-11 |
| 1. Graph Foundation | v1.0 | 3/3 | Complete | 2026-04-11 |
| 2. Mechanic Framework | v1.0 | 3/3 | Complete | 2026-04-12 |
| 3. Design Validation | v1.0 | 15/15 | Complete | 2026-04-12 |
| 4. Mechanic Authoring & Validation Infrastructure | v1.0 | 12/12 | Complete | 2026-04-13 |
| 04.1. Operator Agent Harness (INSERTED) | v1.0 | 5/5 | Complete | 2026-04-13 |
| 5. Simulation Engine | v1.0 | 9/9 | Complete | 2026-04-13 |
| 6. Resident Agent & End-to-End Loop | v1.0 | 7/7 | Complete | 2026-04-14 |
| 7. Attention & Consciousness | v1.0 | 7/7 | Complete | 2026-04-13 |
| 07.1. claude-cli LLM Backend (INSERTED) | v1.0 | 2/2 | Complete | 2026-04-14 |

### v1.1 (Shipped 2026-04-14 — retroactively archived)

Full phase detail moved to [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md). v1.1 ran in hybrid mode; most phases (08, 09, 10, 12) have no PLAN.md/SUMMARY.md files because the work landed as direct-edit + retroactive scaffolding. The lone fully-GSD-scaffolded phase is listed here so the roadmap-progress checker doesn't flag it as unmentioned:

| Phase | Milestone | Plans Complete | Status   | Notes |
|-------|-----------|----------------|----------|-------|
| 11. NiceGUI Dashboard | v1.1 | 1/1 | Complete | Only v1.1 phase with formal PLAN.md; SUMMARY.md retroactive |

### v1.2 (Active — opened 2026-04-14)

Phases TBD — roadmapper subagent will fill in against `.planning/REQUIREMENTS.md` (20 active REQ-V12-* items; 11 warm-up items already shipped). The first plan lands when roadmapper runs.

---

_For the full v1.0 phase breakdown, see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)._
_For v1.1, see [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)._
