# Phase 11 — NiceGUI Dashboard (Track B)

**Milestone:** v1.1 Emergence Tooling
**Mode:** Full GSD phase (plan → execute → verify)
**Dependencies:** Phase 08 (substrate), Phase 09 (operator CLI — dashboard consumes its JSON output)

## Goal

A **read-only web dashboard** that makes a running or completed universe legible
to a human observer. Complements the existing Claude Code chat surface
(which is where humans steer a universe as operator) — the dashboard is the
passive "watch the universe move" channel.

**Moment of truth:** someone clicks a localhost link, sees a resident agent
making decisions, sees the operator authoring a new mechanic on the fly, and
believes this is really happening.

## Scope

### In
- NiceGUI tech stack with FastAPI transitive dependency (revisiting the CLAUDE.md
  ban: direct FastAPI app usage is still banned; NiceGUI wrapping FastAPI is permitted)
- 4 panels MVP + a 5th if time allows:
  - **Tick stream** (live, SSE/poll) — newest first, card-like: intent → verdict → mechanic → observation
  - **Graph canvas** — interactive node-link, click node → property drawer
  - **Stats strip** — always-visible header with tick #, tick/min, yield %, novel mechanics, cost
  - **Causal chain viewer** — consumes `token-world trace` JSON for "why does X.prop=Y?"
  - *(stretch)* **Mechanic registry table** — verb, author, call count, last invoked
- Consumes existing artefacts only (`tick_summaries/*.json`, `universe.db`,
  `operator-log.jsonl`, `token-world inspect/stats/trace --format json`) — no
  new producer-side schema
- Local-only (`uv run token-world dashboard <slug>` opens on `localhost:PORT`)

### Out (v1.2 candidates)
- Hosted public URL (Cloudflare Pages, etc.)
- Tick scrubber + snapshot-restore rewind
- Agent inspector drawer
- 8-bit custom visualizations
- Mutation surfaces (all mutation still goes through engine + MCP)
- Recording mode / asciinema capture

## D-01 (v1.1) — Tech Stack

**Decision:** NiceGUI (Python-native reactive UI, transitively depends on FastAPI + Vue).

**Ban revisit:** CLAUDE.md's "Do not use FastAPI/Flask" targets *direct*
application-framework imports (i.e., writing `@app.get` handlers). NiceGUI
abstracts that surface — the dashboard code uses NiceGUI components, not
FastAPI routes directly. The transitive dependency is documented in
`pyproject.toml` under an optional dashboard extra.

**Alternatives considered:**
- Starlette — too low-level; no reactive component model; would need to hand-build panels
- Streamlit — data-app style, app-store feel; weaker for a custom tick feed + graph canvas composition
- Textual — beautiful TUI but not shareable as a link
- Static HTML + stdlib SSE — viable zero-dep path; viable as a fallback but loses reactive convenience for 4+ panels

**Trade-off accepted:** transitive FastAPI in exchange for single-language
stack, reactive updates without JS tooling, mature Vue components (echarts,
tables, dialogs), and shipping this in one night instead of three.

## Data surfaces the dashboard reads

| Panel | Data source |
|---|---|
| Tick stream | `<universe>/tick_summaries/ticks/tick_*.json` (poll dir for new files) |
| Graph canvas | `token-world graph <slug> --format json` (or direct SQLite read) |
| Stats strip | `token-world stats <slug> --format json` (composes with existing `cost` CLI) |
| Causal chain | `token-world trace <slug> <node> <prop> --format json` |
| Mechanic registry (stretch) | `token-world mechanics <slug> --format json` |

## Success criteria

- SC-1: `uv run token-world dashboard willowbrook` opens a browser at localhost:PORT
- SC-2: While `run_unattended.py` is running, the tick stream panel updates
  live without manual refresh within 3s of a new tick file landing
- SC-3: Click a node in the graph canvas → property drawer shows its full
  JSON properties
- SC-4: Stats strip shows current tick / tick-per-min / yield % / cost
- SC-5: Feed the causal-chain panel a node+prop and see the walker tree
- SC-6: All 4 panels render acceptably on a 1280px-wide viewport

## Constraints

- **Read-only**. No buttons that mutate state — mutation is always via engine + MCP.
- **Loads even on an offline/stopped universe** (graceful degradation, no crash on missing files).
- **Single entry point** — `token-world dashboard <slug>`; no separate npm/yarn/anything toolchain.
- **Tests** — at least one smoke test per panel (imports, renders-without-crash).

## Risks

- **Tick-file poll performance on large universes** — mitigate: only re-read files whose mtime
  changed; hold at most N tick cards in DOM.
- **NiceGUI FastAPI transitivity discovered via security scan** — mitigate: pin versions,
  document the decision in D-01, pyproject extras group.
- **Graph canvas scale** — mitigate: initially render only the ego-graph of the active
  agent; full graph as opt-in expand.

## Out-of-lane files (do not touch in this phase)

- `src/token_world/engine/` (engine contract stable)
- `src/token_world/operator/` except adding dashboard-view-only helpers
- `src/token_world/mechanic/` (no new mechanic work in this phase)

## Ready signals

- Phase 08 shipped (✅ external.py + seed + unattended runner)
- Phase 09 ships at least `stats` + `trace` JSON endpoints (blocking sub-panels, not whole dashboard)
- CI green at time of plan.
