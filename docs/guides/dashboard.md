# Dashboard

A read-only NiceGUI web UI that makes a running or completed Token World
universe legible to a human observer. It is the passive "watch the
universe move" channel — for steering a universe, keep using Claude Code
as the operator surface.

## Quick start

```bash
# 1. Install the optional dashboard extras (one time).
uv sync --extra dashboard

# 2. Launch the dashboard against a universe slug.
uv run token-world dashboard willowbrook --port 8080
```

A browser tab opens at `http://localhost:8080`. If the port is already
in use, pass a different `--port`.

### Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--port N` | `8080` | Bind the NiceGUI server on `localhost:N`. |
| `--no-show` | — | Skip the automatic browser open (useful for remote SSH). |
| `--no-dark` | — | Light mode. |

## Panels

The dashboard mounts four panels at the `/` route:

### 1. Stats strip (header)

Nine compact cells: universe, tick count, latest tick id, throughput,
yield rate, mechanics used, novel mechanics, cost, backend. Refreshes
every 2 seconds.

Data source: `token_world.inspect.stats.aggregate` — identical output
to `token-world stats <slug> --format json`.

### 2. Live tick stream (left column)

Newest-first list of recent tick cards (up to 50). Each card shows

```
tick_id · status · status_detail
  timestamp
  action: (truncated)
  mechanic: id (if matched)
  obs: (truncated)
```

Click a card to expand the full JSON payload. Status color: amber for
`yield`, rose for `refuse`, slate for `exec`, slate-darker for
`unmatched`. Polls every 2 seconds.

### 3. Graph canvas (right column, top)

Mermaid flowchart of the universe knowledge graph. Nodes coloured by
type/subtype:

- **Agent** — blue
- **Container** — amber
- **Location** — green
- **Item / weapon / tool** — purple
- **Generic entity** — slate

Clickable button row beneath the chart; clicking a node id opens the
property drawer on the right with the full JSON property bundle.

Cap: 60 nodes — larger graphs show a truncation banner (extend in
v1.2 with subgraph anchoring).

### 4. Causal chain (right column, bottom)

"Why does `alice.hp = 7`?" Enter a node id + property name, click
**Trace**, and see each mutation hop in order: tick id, mechanic,
old -> new value, action text, observation. Driven by
`token_world.inspect.trace.trace`, identical to
`token-world trace <slug> <node> <prop> --format json`.

## Architecture

```
token_world.dashboard
├── app.py                     # NiceGUI page factory (create_app / run_app)
└── panels/
    ├── stats.py               # Header cells (inspect.stats)
    ├── tick_stream.py         # Polling card list (tick_summaries/ticks/)
    ├── graph_canvas.py        # Mermaid + property drawer (KnowledgeGraph)
    └── causal_chain.py        # Trace walker UI (inspect.trace)
```

All panels are **read-only**. The dashboard never writes to the graph,
mechanics/, operator-log.jsonl, or any universe file. Mutations continue
to flow exclusively through the simulation engine + MCP.

## Graceful degradation

- **Missing universe** — CLI exits 1 with a hint before NiceGUI starts.
- **Empty universe** — all panels render placeholder banners ("no ticks
  yet", "empty graph"); nothing crashes.
- **Missing universe.db** — graph panel surfaces the error, other panels
  keep working.
- **Malformed tick JSON** — silently skipped per the same policy as the
  CLI `inspect` aggregator.

## Testing

```bash
uv run pytest tests/test_dashboard/ -v
```

The test suite covers:

- CLI subcommand registration and missing-slug exit path.
- Pure render helpers (`render_cells`, `build_card`, `build_mermaid`,
  `report_to_view_model`) from synthetic payloads.
- Disk-bound loaders (`load_stats`, `load_recent_tick_cards`,
  `load_graph_snapshot`, `run_trace`) against `fake_universe` fixtures.

Live server smoke-tests are deliberately kept minimal (the NiceGUI server
starts reliably; curling `/` returns 200). Browser-automated UI tests
belong in v1.2 if needed.

## D-01 — FastAPI ban revisited

`CLAUDE.md` bans direct FastAPI usage. NiceGUI transitively depends on
FastAPI + Vue, and we admit that transitive dep under the optional
`[dashboard]` extra. Dashboard code uses only NiceGUI components — no
`from fastapi import ...` and no `@app.get(...)` route handlers. See
`.planning/phases/11-nicegui-dashboard/11-CONTEXT.md` for the full
rationale.

## Out of scope (v1.2 candidates)

- Tick scrubber with snapshot-restore rewind.
- Agent inspector drawer.
- 8-bit / custom visual theming.
- Non-localhost / hosted deployment.
- Recording / asciinema export.
- Mechanic registry panel (use `token-world mechanics <slug>` today).
