---
phase: 15
plan: "01"
subsystem: dashboard
tags: [dashboard, multi-agent, ui, nicegui]
dependency_graph:
  requires: [dashboard/app.py, dashboard/panels/tick_stream.py, dashboard/panels/graph_canvas.py, dashboard/panels/stats.py, inspect/agents.py]
  provides: [selected_agent reactive state, actor badge, agent selector dropdown, graph highlight, per-agent stats rollup]
  affects: [dashboard/app.py, dashboard/panels/tick_stream.py, dashboard/panels/graph_canvas.py, dashboard/panels/stats.py]
tech_stack:
  added: []
  patterns: [mutable-dict-closure-ref for reactive state sharing, selected_agent={"value":""} contract]
key_files:
  created:
    - tests/test_dashboard/test_stats_panel.py
  modified:
    - src/token_world/dashboard/app.py
    - src/token_world/dashboard/panels/tick_stream.py
    - src/token_world/dashboard/panels/graph_canvas.py
    - src/token_world/dashboard/panels/stats.py
    - tests/test_dashboard/conftest.py
    - tests/test_dashboard/test_tick_stream.py
    - tests/test_dashboard/test_graph_canvas.py
decisions:
  - mutable dict {"value": ""} used as closure-safe reactive ref — avoids rebinding issues across timer callbacks
  - per-agent yield breakdown hidden when <=1 actor — no UI clutter for single-agent baseline
  - graph highlight rebuilds on either signature OR selected_agent change — clean separation of concerns
metrics:
  duration: ~20 minutes
  completed: 2026-04-14
  tasks_completed: 3
  files_modified: 7
  files_created: 1
---

# Phase 15 Plan 01: Multi-agent Dashboard Scaffold Summary

Thread `selected_agent` reactive state through all four dashboard panels — agent selector dropdown, actor badge on tick cards, graph node highlight with thick located_in arrow, and per-agent yield-rate rollup in the stats strip.

## What Was Built

- **SC-1a (actor badge):** `build_card()` extracts `classified_action.actor` and adds `actor_id` key. Tick card header appends `· {actor_id}` badge; expansion body shows it as a small `text-slate-400 text-xs font-mono` label after the timestamp line.
- **SC-1 (agent selector + filtering):** `mount_tick_stream_panel` accepts `selected_agent: dict[str, str] | None`; when `selected_agent["value"]` is non-empty, only matching cards are rendered. `app.py` adds a `ui.select()` dropdown above the tick stream that reads agent nodes via `inspect.agents.aggregate` and refreshes on the 2s cadence.
- **SC-2 (graph highlight):** `build_mermaid(snapshot, selected_agent_id=...)` emits a `style {id} stroke:#facc15,stroke-width:3px` override for the selected node and replaces dashed `-.located_in.->` with a thick `== located_in ==>` arrow for the selected agent's location pseudo-edge. `mount_graph_panel` accepts `selected_agent` and forces chart rebuild when agent selection changes independently of graph signature.
- **SC-3 (per-agent stats rollup):** New `load_per_agent_yield(universe_dir)` helper groups tick files by `classified_action.actor`. `render_cells()` accepts optional `per_agent_yield` kwarg; emits "Yield ({id})" rows after global "Yield rate" only when `len(per_agent_yield) > 1`. `mount_stats_strip` wires both.

## Tests Added / Modified

| File | Change |
|---|---|
| `tests/test_dashboard/test_tick_stream.py` | Added 3 tests: `test_build_card_includes_actor_id_from_classified_action`, `test_build_card_actor_id_empty_when_no_classified_action`, `test_load_recent_tick_cards_filters_by_actor` |
| `tests/test_dashboard/test_graph_canvas.py` | Added 3 tests: `test_build_mermaid_outlines_selected_agent_node`, `test_build_mermaid_highlights_selected_agent_located_in_edge`, `test_build_mermaid_no_outline_when_no_selected_agent` |
| `tests/test_dashboard/test_stats_panel.py` | New file — 5 tests covering single/multi-agent rollup, zero-tick dash, None passthrough, core cell presence |
| `tests/test_dashboard/conftest.py` | Added `fake_universe_two_agents` fixture (2 agent nodes with `located_in` properties, 2 ticks with distinct actors) |

**Suite result:** 79/79 dashboard tests pass. Full suite 1544 pass (1 pre-existing meta test skip unrelated to this plan — requirements traceability drift for phases 13–19).

## Deviations from Plan

None — plan executed exactly as written. `_write_tick_summary` in `tests/test_cli/conftest.py` already had `classified_action` kwarg support, so no changes to that file were needed.

## Known Stubs

None — all four SCs are fully wired. The agent selector reads live KG data; actor badges come from actual tick JSON; graph highlight is data-driven; stats rollup processes real tick files.

## Self-Check: PASSED

- `src/token_world/dashboard/panels/tick_stream.py` — FOUND (actor_id in build_card, selected_agent filter)
- `src/token_world/dashboard/panels/graph_canvas.py` — FOUND (build_mermaid selected_agent_id, mount_graph_panel selected_agent)
- `src/token_world/dashboard/panels/stats.py` — FOUND (load_per_agent_yield, render_cells per_agent_yield kwarg)
- `src/token_world/dashboard/app.py` — FOUND (selected_agent state, ui.select dropdown, agents_aggregate refresh)
- `tests/test_dashboard/test_stats_panel.py` — FOUND (new file, 5 tests)
- Commit `cca77c3` — FOUND
