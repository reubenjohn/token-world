# Phase 11 — NiceGUI Dashboard — PLAN

**Context:** `.planning/phases/11-nicegui-dashboard/11-CONTEXT.md` (D-01 NiceGUI + transitive FastAPI permitted)
**Goal:** Read-only web dashboard at `localhost:PORT` that makes a running
Willowbrook universe legible. MVP 4 panels.

## Scope cuts (make tonight shippable)

- **No** tick scrubber (uses snapshot/restore — deferred to v1.2)
- **No** agent inspector drawer (use `token-world agents --format json` CLI instead)
- **No** 8-bit graph canvas custom styling — use a straightforward vis.js or
  Cytoscape node-link. Pretty later.
- **No** SSE — poll tick_summaries/ticks/ every 2s in NiceGUI's reactive loop.
  Reactive updates give us live-tail feel without dealing with ASGI event streams.

## Build order

### Plan 11-01 — NiceGUI skeleton + stats strip (60 min)
- [x] Add `nicegui` to `pyproject.toml` as optional `[dashboard]` extra
- [x] `src/token_world/dashboard/__init__.py` — empty
- [x] `src/token_world/dashboard/app.py` — NiceGUI `create_app(universe_dir)`
- [x] `src/token_world/dashboard/panels/stats.py` — always-visible header using `token-world stats` JSON
- [x] CLI wiring: `token-world dashboard <slug> [--port 8080]` in `src/token_world/cli.py`
- [x] Smoke test: `uv run token-world dashboard willowbrook` → browser opens, stats render
- [x] 1 pytest checking the app module imports without error

### Plan 11-02 — Live tick stream panel (45 min)
- [x] `src/token_world/dashboard/panels/tick_stream.py`
- [x] Poll `tick_summaries/ticks/` every 2s via `ui.timer`
- [x] Card format: tick_id | action_text (truncated) | mechanic_id OR yield OR refuse | observation (truncated)
- [x] Auto-scroll to newest
- [x] Click a tick card → expand to full detail (via `token-world tick --format json`)
- [x] Pytest: card renders from a synthetic tick dict

### Plan 11-03 — Graph canvas panel (60 min)
- [x] `src/token_world/dashboard/panels/graph_canvas.py`
- [x] Use `ui.mermaid` OR Cytoscape via `ui.html` — whichever lands simpler
  in NiceGUI. Mermaid is already a dep; Cytoscape requires CDN.
- [x] Render current graph (nodes + edges, color by type/subtype)
- [x] Click a node → right drawer shows full properties
- [x] Pytest: renders from a `KnowledgeGraph` fixture
### Plan 11-04 — Causal chain viewer (30 min)
- [x] `src/token_world/dashboard/panels/causal_chain.py`
- [x] Input: node_id + property
- [x] Call `token-world trace <slug> <node> <prop> --format json`
- [x] Render as a vertical tree of hops
- [x] Pytest: renders from a synthetic trace JSON

### Plan 11-05 — Wire + polish (30 min)
- [x] Tab or split-pane layout: stats strip header | tick stream left | graph canvas right top | causal chain right bottom
- [x] Error states: universe doesn't exist, universe is empty, run isn't running yet
- [x] Dark mode via NiceGUI theme
- [x] `docs/guides/dashboard.md` — 1-page explainer
- [x] Update CLAUDE.md Script Catalog row

## Verification (must pass before closing)

- SC-1: `uv run token-world dashboard willowbrook --port 8080` — opens browser tab, renders 4 panels
- SC-2: While `run_unattended.py` is active, tick stream updates within 3s of a new tick file
- SC-3: Click node in graph canvas → property drawer shows JSON
- SC-4: Stats strip shows current tick / throughput / yield rate / cost
- SC-5: Causal chain input `mira` + `last_observed` renders the walker tree (after `examine` mechanic runs)
- SC-6: All 4 panels render at 1280px viewport without layout breakage

## Guard rails

- Dashboard is **read-only**. No buttons that mutate graph state.
- **Graceful degradation**: missing tick_summaries/ or empty operator-log.jsonl
  must not crash the panel; show a placeholder.
- Pinned versions in `pyproject.toml` (no `nicegui>=*`).
- Transitive FastAPI is acceptable per D-01; direct `fastapi` imports in
  dashboard code are NOT acceptable (document + keep clean).
- One Click CLI command total (`dashboard`); no separate npm/node build step.

## Files of note (to be created)

- `src/token_world/dashboard/__init__.py`
- `src/token_world/dashboard/app.py`
- `src/token_world/dashboard/panels/stats.py`
- `src/token_world/dashboard/panels/tick_stream.py`
- `src/token_world/dashboard/panels/graph_canvas.py`
- `src/token_world/dashboard/panels/causal_chain.py`
- `src/token_world/cli.py` (add `dashboard` subcommand)
- `pyproject.toml` (add [dashboard] extra)
- `docs/guides/dashboard.md`
- `tests/test_dashboard/` (new)

## Out of scope (stretch for v1.2)

- Tick scrubber with snapshot-restore
- Mechanic registry panel
- Agent inspector drawer
- Hosted (non-localhost) deployment
- Recording / asciinema capture
