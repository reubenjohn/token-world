# Phase 15: Multi-agent Dashboard Scaffold — Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous smart discuss)

<domain>
## Phase Boundary

REQ-V12-DASHBOARD-05: Make the dashboard multi-agent-ready without changing the engine baseline (which stays single-agent per D-17).

Four SC deliverables:
- SC-1: Agent-selector dropdown above tick stream; single agent → defaults to it; two synthetic agents → filters tick feed
- SC-1a: Every tick card shows `· actor_id` badge
- SC-2: Graph canvas outlines selected agent node + highlights its located_in pseudo-edge
- SC-3: Stats strip per-agent yield-rate rollup when >1 agent; hidden in single-agent case

</domain>

<decisions>
## Implementation Decisions

### Agent selector
- NiceGUI ui.select() above tick stream, bound to reactive `selected_agent` state variable
- "" (empty string) means "all agents" — default when single agent
- Reads agent nodes via inspect/agents.py query pattern (agent-typed nodes in KG)
- Refreshes on same timer cadence as tick stream

### Actor badge
- Append `· {actor_id}` small label to each tick card in tick_stream panel
- Read actor from tick summary JSON `classified_action.actor` field (or `action_text` fallback)
- Style: text-slate-400 text-xs

### Graph highlight
- graph_canvas.py (NOT graph.py) handles graph rendering
- When selected_agent is set: find node, apply CSS outline; find located_in pseudo-edge, highlight it
- Reuse DASHBOARD-04 pseudo-edge machinery already in place

### Stats rollup
- Compute per-agent yield counts in stats aggregation
- Show per-agent breakdown row only when agent count > 1
- Hide in single-agent case (no UI clutter for current baseline)

### Engine stays single-agent
- D-17 preserved — no engine changes
- Dashboard is multi-agent-READY, not multi-agent-REQUIRED

### Test strategy
- Fixture universe with 2 synthetic agent nodes in KG
- Assert selector shows both agents
- Assert actor badge visible in tick card
- Dashboard panel tests only (no NiceGUI server needed for render_cells style tests)

</decisions>

<code_context>
## Existing Code Insights

- `src/token_world/dashboard/app.py` — main page handler; mount order: quality → stats → tick_stream → graph_canvas
- `src/token_world/dashboard/panels/tick_stream.py` — tick card rendering; actor badge goes here
- `src/token_world/dashboard/panels/stats.py` — stats aggregation; per-agent rollup addition
- `src/token_world/dashboard/panels/graph_canvas.py` — graph rendering (NOT graph.py)
- `src/token_world/inspect/agents.py` — agent node query pattern to reuse for selector

</code_context>

<specifics>
## Specific Requirements

- Agent selector must appear ABOVE tick stream in app.py mount order
- Scroll preservation: any new scrollable container uses tick_stream.py's scroll_area pattern
- Dark-mode Tailwind classes throughout (bg-slate-*, text-*)
- Single plan (15-01), Wave 1 — all changes are tightly coupled through selected_agent state

</specifics>

<deferred>
## Deferred Ideas

- Multi-agent engine support (v2.0, requires D-17 change)
- Per-agent memory inspector in drawer (v2.0)

</deferred>
