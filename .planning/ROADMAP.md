# Roadmap: Token World

## Overview

Token World is a universe simulator where LLM-powered resident agents inhabit a text-based world whose rules are procedurally authored on-the-fly. The v1.0 milestone shipped the full end-to-end loop: knowledge graph, mechanic framework, operator-authored mechanics under inversion of control, simulation engine with grounded observations, resident agent with memory, and composable attention/consciousness mechanics.

The next milestone (v1.1) is not yet scoped — definition pending via `/gsd-new-milestone`.

## Milestones

- ✅ **v1.0 MVP** — Phases 0..7, 04.1 + 07.1 inserted (shipped 2026-04-14)
- 📋 **v1.1** — (not yet scoped)

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

### 📋 v1.1 (Not Yet Scoped)

Milestone v1.1 is pending. Kick off via `/gsd-new-milestone`. Candidate themes surfaced during v1.0 close (see PROJECT.md § Active):

- Close Phase 04.1 SC-2 interactive smoke test (now zero-cost via `ClaudeCLIBackend`)
- Refresh stale research docs on Opus-vs-Sonnet model routing
- Populate `agent_id` correctly in BatchSummary
- Second-agent experimentation (precursor to v2's MULTI-01)
- Cost monitoring / circuit breakers (HARD-03)
- Dashboard / graph visualizer (previously out-of-scope; reconsider)

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

### v1.1 (Planning)

TBD — run `/gsd-new-milestone` to scope.

---

_For the full v1.0 phase breakdown, see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)._
