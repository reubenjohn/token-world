# Requirements — Token World v1.1 (Emergence Tooling)

*Scoped by the MORNING-HANDOFF mandate at v1.0 close. This is not the full v2 scope —
these are the capabilities needed to make unattended universe runs real and
shareable.*

**Milestone vision:** Make it feel possible — maybe even inevitable — that interesting
universes can emerge from play without hand-holding. Give operators (humans AND agents)
an eye into what's happening, and give universes the safety rails to run overnight.

## Requirements

### REQ-OPCLI — Operator CLI Surface (Track A)

Agents need a query language for universes. Every command MUST support `--format json`.

- [ ] REQ-OPCLI-01: `token-world inspect <slug>` — universe at a glance (nodes, mechanics, last N ticks, active LRAs, recent yields)
- [ ] REQ-OPCLI-02: `token-world tick <slug> <id>` — full per-tick detail tree (action → classification → mechanic → mutations → observation)
- [ ] REQ-OPCLI-03: `token-world trace <slug> <node> <prop>` — causal chain walker
- [ ] REQ-OPCLI-04: `token-world mechanics <slug>` — registry browser with call counts + author (seed vs operator)
- [ ] REQ-OPCLI-05: `token-world stats <slug>` — aggregate metrics (tick/min, yield rate, novel-mechanic rate, cost)
- [ ] REQ-OPCLI-06: `token-world watch <slug>` — live tail of tick events

### REQ-EMERGE — Emergence Loop (Track C)

Unattended runs: authoring without human clicks.

- [x] REQ-EMERGE-01: `ExternalOperator` protocol — file-based yield→resolution between engine and out-of-process orchestrator (shipped `8f1f18e`)
- [x] REQ-EMERGE-02: Seed starter universe (Willowbrook) — one agent, rich environment with emergent hooks (shipped `0a95763`)
- [x] REQ-EMERGE-03: Unattended run driver — `scripts/run_unattended.py` with tick / yield / cost / kill-switch rails (shipped `0a95763`)
- [ ] REQ-EMERGE-04: Orchestration loop — Claude Code session that polls inbox, spawns authoring subagents, writes resolutions
- [ ] REQ-EMERGE-05: Mechanic overlap detector — before authoring a new mechanic, diff verb + watches against existing registry; prefer edit-existing on high overlap
- [ ] REQ-EMERGE-06: Overnight 200-tick Willowbrook run with real emergence data captured
- [ ] REQ-EMERGE-07: Operator decision log (`operator-log.jsonl`) — every authoring decision logged with rationale

### REQ-DASH — Read-Only Dashboard (Track B) — v1.1 D-01 NiceGUI

A complementary observer surface for humans watching what agents and the engine are
doing. NOT a chat surface (humans chat with Claude Code, which IS the operator).

- [ ] REQ-DASH-01: NiceGUI stack adopted; FastAPI transitive-ban-revisit documented as D-01
- [ ] REQ-DASH-02: Live tick stream panel — card feed: agent intent → classifier verdict → mechanic match → observation
- [ ] REQ-DASH-03: Graph canvas panel — interactive node-link view; click node → property drawer
- [ ] REQ-DASH-04: Stats strip — always-visible header (tick #, tick/min, yield %, novel mechanics, cost)
- [ ] REQ-DASH-05: Causal chain viewer — "why does alice.mood=curious?" walker (consumes `token-world trace` output)
- [ ] REQ-DASH-06: Shareable locally (localhost:PORT); consumes `tick_summaries/*.json`, `universe.db`, `operator-log.jsonl`

### REQ-WARMUP — Dangling Items Burn-Down

Closed-out paper cuts from v1.0.

- [x] REQ-WARMUP-01: Close Phase 04.1 SC-2 smoke test via claude-cli backend (closed `0ac7f38`)
- [x] REQ-WARMUP-02: `scripts/check_requirements_traceability.py` (+ CI wire) (shipped `acb9797`; pytest-wired in `tests/test_meta/`)
- [x] REQ-WARMUP-03: `scripts/check_roadmap_progress.py` (+ CI wire) (shipped `acb9797`; pytest-wired in `tests/test_meta/`)
- [x] REQ-WARMUP-04: Research docs (`STACK.md`, `ARCHITECTURE.md`, `SUMMARY.md`) refreshed + archival-timestamp headers (shipped `ff211b7`)
- [x] REQ-WARMUP-05: `BatchSummary.agent_id` stub fixed (populate from first mutation's actor) (shipped `97f9648`)
- [x] REQ-WARMUP-06: Agent-workflow friction reducers (`commit.sh`, `run_uat.py`, `phase_show.py`, `ci_status.py`, agent-prompt fragments) (shipped Session 4)

## Non-Requirements (explicitly out of scope for v1.1)

- **Multi-agent simulation** — still v2 (MULTI-01..03)
- **Hosted public dashboard URL** — v1.2 candidate; v1.1 is local-only
- **Mechanic versioning UI** — registry browser ships with call counts; version history is v1.2 candidate
- **RestrictedPython sandboxing** — still v2+
- **Gallery / sharing export** — v1.2 candidate
- **Recording mode / asciinema capture** — v1.2 polish

## Traceability

| Requirement | Phase | Status | Commit / Plan |
|---|---|---|---|
| REQ-EMERGE-01 | Phase 08 (Track C substrate) | done | `8f1f18e` |
| REQ-EMERGE-02 | Phase 08 | done | `0a95763` |
| REQ-EMERGE-03 | Phase 08 | done | `0a95763` |
| REQ-OPCLI-01..06 | Phase 09 (Track A) | in_progress | (subagent) |
| REQ-WARMUP-01..06 | Phase 10 (Warm-up) | done | Session 4 — see commits `0ac7f38`, `acb9797`, `ff211b7`, `97f9648`, `c3fd0ec` |
| REQ-DASH-01..06 | Phase 11 (Track B) | planning | — |
| REQ-EMERGE-04..07 | Phase 12 (overnight orchestration) | planning | — |

---

*Last updated: 2026-04-15 session 4.  Hybrid mode (direct work + GSD for dashboard
and final orchestration).*
