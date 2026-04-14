# Roadmap: Token World

## Overview

Token World is a universe simulator where LLM-powered resident agents inhabit a text-based world whose rules are procedurally authored on-the-fly. v1.0 shipped the full end-to-end loop; v1.1 delivered the emergence tooling (Operator CLI + NiceGUI dashboard + ExternalOperator substrate) that proved unattended mechanic authoring works.

v1.2 (Quality + Depth) is the current milestone, opened 2026-04-14 — absorbing every remaining requirement across the project except the handful of truly far-fetched multi-agent / transactional / distributed items parked in `backlog/v2.0-REQUIREMENTS.md`.

## Milestones

- ✅ **v1.0 MVP** — Phases 0..7, 04.1 + 07.1 inserted (shipped 2026-04-14)
- ✅ **v1.1 Emergence Tooling** — Phases 08..12 (shipped 2026-04-14, retroactively archived)
- 🟢 **v1.2 Quality + Depth** — Phases 12.5 (warm-up) + 13..19 (active), opened 2026-04-14
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

**Warm-up shipped** (sessions 4–6 direct-edit, pre-formal-scaffolding): 13 REQ-V12-* items. Tracked as virtual **Phase 12.5 — v1.2 Warm-up** (see detail below) so traceability / progress checkers recognise the scope without a dedicated phase directory.

**Active phases (13..19):** seven phases, 21 active REQ-V12-* requirements. Each requirement is mapped to exactly one phase.

Phase list:

- [x] Phase 12.5: v1.2 Warm-up (13/13 items — shipped pre-scaffolding)
- [x] Phase 13: Quality KPIs substrate (1 REQ) (completed 2026-04-14)
- [ ] Phase 14: Engine polish + seed corpus hygiene (3 REQs)
- [ ] Phase 15: Multi-agent dashboard scaffold (1 REQ)
- [ ] Phase 16: Composite actions (1 REQ, architectural — design + implementation waves)
- [ ] Phase 17: Operator & dev ergonomics (8 REQs)
- [ ] Phase 18: Graph conventions + engine audit + chain seed corpus (6 REQs)
- [ ] Phase 19: Historical tick-summary migration (1 REQ, optional)

### Phase 12.5 — v1.2 Warm-up (estimate: 0 plans; shipped direct-edit)

**Goal:** Burn down the §J truthfulness + dashboard-UX + process-artefact backlog surfaced in session-5 user feedback, before formal v1.2 scaffolding landed.
**Depends on:** v1.1 Phase 12
**Requirements:** REQ-V12-ENGINE-01, REQ-V12-ENGINE-02, REQ-V12-DASHBOARD-01, REQ-V12-DASHBOARD-02, REQ-V12-DASHBOARD-03, REQ-V12-DASHBOARD-04, REQ-V12-CLI-01, REQ-V12-CLI-02, REQ-V12-PLAYTEST-01, REQ-V12-ECONOMY-01, REQ-V12-QUALITY-01, REQ-V12-DOCS-01, REQ-V12-TOOLING-01
**Plans:** 0 (shipped as 13 targeted direct-edit / subagent passes during sessions 4–6; no PLAN.md / SUMMARY.md artefacts — each item maps to a specific commit under the REQUIREMENTS.md Traceability table)
**Status:** Complete — all 13 items shipped in-session

Success criteria:
1. SC-1: Engine tick summary never records `status=executed, refused=false` for a tick whose primary mechanic `check()` refused (verified live: willowbrook tick 61 records `refused=true, mechanic_check_failed, mutations=0`; pre-fix would have logged as executed) — `afc5c73`.
2. SC-2: Observer narration never contradicts the applied mutation list (verified live tick 35 post-fix; three regression tests in place) — `e110e2c`.
3. SC-3: Dashboard is usable >2 s without scroll dying (Playwright-verified: tick stream 400→400 over 5 s / 2+ poll cycles; drawer 100→100 over 7 s / 3+ cycles) — `d31090d` + `6101da0`.
4. SC-4: Every §J-table delivered item has a commit row in REQUIREMENTS.md Traceability with its SHA and shipped status.

### Phase 13: Quality KPIs substrate (estimate: 2 plans)

**Goal:** Every overnight run ends with an automatable, mechanically-scored quality report consumed by both CLI users and the dashboard — with CI able to gate a release on thresholds from the sim-quality rubric (docs already shipped in Phase 12.5).
**Depends on:** Phase 12.5 (warm-up; ENGINE-01 + ENGINE-02 make the data honest enough to score)
**Requirements:** REQ-V12-QUALITY-02
**Plans:** 2/2 plans complete
- [x] 13-01-PLAN.md — Quality scorer subpackage + CLI command
- [x] 13-02-PLAN.md — Dashboard Quality panel + CI gate + pytest wiring

Success criteria:
1. SC-1: Operator runs `token-world quality <slug>` and sees a single scorecard with all 8 rubric dimensions (groundedness, character stability, action coherence, refusal clustering, vocabulary growth, novel subtype rate, graph fan-out, conservation drift) — no filesystem-poking, no `grep` pipelines.
2. SC-2: Dashboard opens with a "Quality" panel that consumes `token-world quality --format json` and renders the scorecard live; never re-computes the numbers itself (per §G allocation rule).
3. SC-3: A post-run CI hook fails with a named-dimension error message when any dimension drops below its documented threshold for the last 50 ticks of a run.
4. SC-4: Operator re-runs `token-world quality <slug>` on the current willowbrook dataset and gets an interpretable score (proves the sub-package + rubric work on real data, not just fixture tests).

### Phase 14: Engine polish + seed corpus hygiene (estimate: 3 plans)

**Goal:** Close the last small engine-truthfulness follow-ups, promote the five universe-agnostic mechanics the overnight run authored, and stop the seed script from silently deleting them on re-seed.
**Depends on:** Phase 12.5 (ENGINE-01 shipped; refuse-observation path now exercised in production, surfacing the doubled-wrapper bug)
**Requirements:** REQ-V12-ENGINE-05, REQ-V12-SEEDS-01, REQ-V12-TOOLING-02
**Plans:** 2/3 plans executed
Plans:
- [x] 14-01-PLAN.md — ENGINE-05 refusal wrapper regression test + fix
- [x] 14-02-PLAN.md — 5 seed mechanics (examine/pet/sharpen/hum/drop) + _KEEP_MECHANICS
- [ ] 14-03-PLAN.md — SC-3 entities (bench/coop/gate) + --preserve-mechanics flag

Success criteria:
1. SC-1: A refused tick's observation text contains the "You try, but" refuse wrapper exactly once (regression test on willowbrook tick 61 or equivalent fixture; grep confirms a single source-of-truth for the wrapper string).
2. SC-2: A new universe created from `seed_starter_universe.py` ships with `examine`, `pet`, `sharpen`, `hum`, `drop` as framework-level seed mechanics — no authoring yield needed for these verbs on the first tick.
3. SC-3: A new universe spawned from the seed script includes a `bench (weathered=True)`, a chicken coop, and a broken gate — each with hook properties that mechanics can observe on authoring.
4. SC-4: Running `seed_starter_universe.py --preserve-mechanics` against an existing universe with authored mechanics leaves every `<universe>/mechanics/*.py` file untouched; running without the flag prints a loud stderr warning naming every mechanic that would be overwritten.

### Phase 15: Multi-agent dashboard scaffold (estimate: 1 plan)

**Goal:** The dashboard is ready for a second agent the moment one exists in the engine (v2), without a re-architecture of the panels. Single-agent remains the engine baseline per D-17.
**Depends on:** Phase 12.5 (DASHBOARD-01..04 shipped; scroll / pseudo-edges in place)
**Requirements:** REQ-V12-DASHBOARD-05
**Plans:** TBD

Success criteria:
1. SC-1: Operator opens the dashboard and sees an agent-selector dropdown above the tick stream; with one agent present it defaults to that agent; with two synthesised agents in a fixture universe it filters the tick feed on selection change.
2. SC-1a: Every rendered tick card shows a `· actor_id` badge, so the operator can disambiguate multi-agent traffic once it exists.
3. SC-2: Graph canvas visually outlines the currently-selected agent node and highlights its `located_in` pseudo-edge (reuses the DASHBOARD-04 pseudo-edge machinery).
4. SC-3: Stats strip surfaces a per-agent yield-rate rollup when >1 agent exists; hides the rollup in the single-agent default case.

### Phase 16: Composite actions (estimate: 2 plans — design + implementation)

**Goal:** One agent action can fire multiple primary mechanics within a tick, unblocking richer narrative ("I open the chest and take the key") without changing the mechanic protocol. Architectural; the design wave must land and close the design gate before implementation starts.
**Depends on:** Phase 12.5 (ENGINE-01 honest refusal path; a composite tick's sub-actions can now refuse honestly instead of silently)
**Requirements:** REQ-V12-ENGINE-04
**Plans:** TBD (expect 2 — one for the design doc + classifier schema bump, one for engine iteration + yield-handler prompt update + regression tests)

Success criteria:
1. SC-1: `docs/design/composite-actions.md` (v1.2 D-01) chooses between the three options documented in MORNING-HANDOFF §E1, with a decision rationale referenced from PROJECT.md Key Decisions.
2. SC-2: Classifier emits an `actions: [...]` array; a single-verb input wraps as a 1-element list (back-compat guarantee preserved for every existing test).
3. SC-3: A multi-verb fixture input (`"open the chest and take the key"`) produces a multi-mechanic `ExecutionTrace` with one entry per sub-action, each independently refusable.
4. SC-4: Classifier `SCHEMA_VERSION` bumped and prompt-hash registry records the bump; yield-handler subagent prompt notes the per-sub-action invocation contract.

### Phase 17: Operator & dev ergonomics (estimate: 4 plans)

**Goal:** Every operator investigation the author reached for during sessions 4–6 (raw classifier response, mechanic lifecycle, run-alive?, agent internals, yield decision rationale, stale `.stop` kill-switch) becomes a one-liner on the CLI or a sticky surface on the dashboard — per §G allocation rules (CLI canonical producer; dashboard consumes JSON).
**Depends on:** Phase 12.5 (CLI-01/CLI-02 shipped; the ergonomics this phase extends)
**Requirements:** REQ-V12-CLI-03, REQ-V12-CLI-04, REQ-V12-DASHBOARD-07, REQ-V12-DASHBOARD-08, REQ-V12-DASHBOARD-09, REQ-V12-EMERGE-01, REQ-V12-EMERGE-02, REQ-V12-OPS-01
**Plans:** TBD

Success criteria:
1. SC-1: Operator inspects any tick stage via `token-world tick <slug> <id> --stage classification|matcher|observer [--raw]` and sees the parsed payload (or raw prompt+response with `--raw`) without reaching into `diagnostics/tick_N/`.
2. SC-2: Operator runs `token-world mechanics <slug> --history` and sees every mechanic's first-authored commit + timestamp + last-invoked tick in chronological order; the dashboard registry panel renders the same two columns (sortable) consuming the CLI JSON.
3. SC-3: Dashboard stats strip renders a green/yellow/red run-status dot reading `<universe>/.run-pid`; hover tooltip shows PID + start time. `run_unattended.py` writes the PID on start and removes on clean exit; startup fails loudly with a non-zero exit and a named-file stderr warning when `<universe>/.stop` is present.
4. SC-4: Clicking an agent node in the dashboard graph opens an inspector drawer with labelled sections (Identity, Location, Memory, Active LRA, Attention state, Recent actions) — reuses the DASHBOARD-01 non-rebuild scroll guarantee; drawer scroll survives poll cycles.
5. SC-5: Every yield-resolution event in `<universe>/operator-log.jsonl` carries the authoring subagent's final JSON (reasoning + overlap score + test-pass/fail history + cost); overlap score was computed against the existing registry before authoring started, and the subagent's system prompt includes the overlap report with a "prefer edit-existing above threshold" instruction.

### Phase 18: Graph conventions + engine audit + chain seed corpus (estimate: 3 plans)

**Goal:** Codify the four graph-shape conventions the overnight run surfaced, sweep the engine for the hardcoded property-name smell that necessitates them, and seed enough chain-producing mechanics that the side-effect tree (DASHBOARD-03, shipped) is interesting on real runs.
**Depends on:** Phase 12.5 (DASHBOARD-03 side-effect tree shipped — this phase makes it information-dense)
**Requirements:** REQ-V12-ENGINE-03, REQ-V12-GRAPH-01, REQ-V12-GRAPH-02, REQ-V12-GRAPH-03, REQ-V12-GRAPH-04, REQ-V12-DASHBOARD-06
**Plans:** TBD

Success criteria:
1. SC-1: `docs/design/graph-conventions.md` (new) documents the canonical representation for doors, containers, portals/passages, and fungible amounts — each section cross-referenced from the requirement text.
2. SC-2: Engine grep audit reports zero semantic references to `locked` / `blocked` / `inventory_full` inside `src/token_world/engine/` and `src/token_world/mechanic/` (excluding `seeds/`); any legitimate reads carry a code comment flagging them as reads-only framework hooks.
3. SC-3: A regression test uses an arbitrary property name (e.g. `warded`, `trapped`) in a synthetic mechanic and receives identical engine treatment to `locked` — proving the engine no longer privileges specific strings.
4. SC-4: Registry audit report lists every seed mechanic's `watches()` spec; at least 3 new `PropertyChangeMatcher` / `EdgeMatcher` seed mechanics land (mood-change, contains-edge, temperature watcher) — a fresh willowbrook run shows non-trivial chain depth in the dashboard side-effect tree.

### Phase 19: Historical tick-summary migration (estimate: 1 plan, optional)

**Goal:** Backfill truthfulness into the willowbrook run artefacts that pre-date REQ-V12-ENGINE-01 (ticks 22, 34, 38) so downstream KPIs and the playtest scorer stop double-counting false-EXECUTED records forever.
**Depends on:** Phase 13 (KPI scorer exists so the migrated data has a consumer)
**Requirements:** REQ-V12-OPS-02
**Plans:** TBD (skip if the willowbrook archive gets retired before this phase is reached — OPTIONAL per REQUIREMENTS.md)

Success criteria:
1. SC-1: Operator runs `scripts/migrate_tick_summaries.py willowbrook --dry-run` and sees a diff of every pre-ENGINE-01 tick whose primary-mechanic check would have failed under current engine logic.
2. SC-2: Operator runs the migration with `--apply`; every rewritten tick summary JSON records `refused=true, mechanic_check_failed, mutations=0`; re-running with `--apply` is a no-op (idempotent).
3. SC-3: The dashboard KPI panel (Phase 13) post-migration no longer counts ticks 22/34/38 as "successful EXECUTED with zero mutations", restoring honest groundedness scores on the archive.

## Progress

**Execution Order:**
Phases execute in numeric order within each milestone. Decimal phases (e.g., 04.1, 12.5) are urgent insertions between integer phases.

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

| Phase | Milestone | Plans Complete | Status   | Notes |
|-------|-----------|----------------|----------|-------|
| 13. Quality KPIs substrate | v1.2 | 2/2 | Complete   | 2026-04-14 |
| 14. Engine polish + seed corpus hygiene | v1.2 | 2/3 | In Progress|  |
| 15. Multi-agent dashboard scaffold | v1.2 | 0/0 | Planning | DASHBOARD-05 — dashboard-only; engine stays single-agent |
| 16. Composite actions | v1.2 | 0/0 | Planning | ENGINE-04 — architectural; design wave + implementation wave |
| 17. Operator & dev ergonomics | v1.2 | 0/0 | Planning | CLI-03/04, DASHBOARD-07/08/09, EMERGE-01/02, OPS-01 |
| 18. Graph conventions + engine audit + chain seed corpus | v1.2 | 0/0 | Planning | ENGINE-03, GRAPH-01..04, DASHBOARD-06 |
| 19. Historical tick-summary migration (OPTIONAL) | v1.2 | 0/0 | Planning | OPS-02 — skip if archive retired first |

---

_For the full v1.0 phase breakdown, see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)._
_For v1.1, see [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)._
