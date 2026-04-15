---
phase: 17-operator-dev-ergonomics
plan: "03"
subsystem: dashboard-graph
tags: [dashboard, agent-inspector, graph-canvas, drawer, tdd]
dependency_graph:
  requires: [17-02]
  provides: [agent_inspector.render_agent_inspector_sections, graph_canvas._on_node_click-routing]
  affects: [dashboard.graph_canvas]
tech_stack:
  added: []
  patterns: [framework-agnostic-sections, user-driven-drawer-rebuild]
key_files:
  created:
    - src/token_world/dashboard/panels/agent_inspector.py
    - tests/test_dashboard/test_agent_inspector.py
  modified:
    - src/token_world/dashboard/panels/graph_canvas.py
decisions:
  - "Sections returned as plain dicts for framework-agnostic testing (no NiceGUI in unit tests)"
  - "memory capped at last 10 entries (T-17-03-02); persona truncated to 100 chars first line (T-17-03-01)"
  - "_rebuild_agent_drawer is only called from _on_node_click (§A7 scroll guarantee preserved)"
  - "_load_recent_actions wrapped in try/except returns [] on error (T-17-03-03)"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-14"
  tasks_completed: 2
  files_changed: 3
---

# Phase 17 Plan 03: Agent Inspector Drawer Summary

Replaces the raw JSON property dump for agent nodes with a structured 6-section inspector drawer, addressing the session-5 operator complaint that agent state was unreadable.

## What Was Built

**SC-4 — agent_inspector.py:**
- `render_agent_inspector_sections(agent_summary, recent_actions)` returns list of 6 section dicts for testing
- Sections: Identity (id + personality keys or persona preview), Location (located_in property), Memory (last 10 entries), Active LRA (action + elapsed/total), Attention (key-value pairs), Recent Actions (last 10)
- `agent_summary_from_props(node_id, properties)` builds AgentSummary from graph node dict
- `mount_agent_inspector()` renders sections via NiceGUI ui.expansion() per section

**SC-4 — graph_canvas.py extensions:**
- `_load_recent_actions(universe_dir, agent_id, limit=10)` scans tick summaries for actor_id matches
- `_on_node_click` branches: `properties.get("type") == "agent"` routes to `_rebuild_agent_drawer`, else generic drawer
- `_rebuild_agent_drawer()` added as separate function; imported from agent_inspector lazily
- Poll handler `_rebuild()` unchanged — never touches the drawer (§A7 preserved)

## Tests

- `tests/test_dashboard/test_agent_inspector.py` — 10 cases (personality, persona text, location present/absent, memory truncation, LRA active/none, attention, empty recent actions, all 6 sections present)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
- `tests/test_dashboard/test_agent_inspector.py` — 10 passed
- Commit: `4d3a42e`
