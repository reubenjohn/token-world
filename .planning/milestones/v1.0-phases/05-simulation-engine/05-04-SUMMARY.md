---
phase: 05-simulation-engine
plan: "04"
title: "VisibilityProjector + belief overlay (GAP-CROSS01 + GAP-GRAPH04)"
subsystem: engine
tags:
  - engine
  - visibility
  - observation
  - belief
  - illumination
  - graph
dependency_graph:
  requires:
    - "05-01 (engine package, KnowledgeGraph API)"
    - "01-graph (KnowledgeGraph.ego_subgraph public API)"
  provides:
    - "token_world.engine.visibility.VisibilityProjector (D-14)"
    - "project_for() convenience function"
    - "Closes GAP-CROSS01 (observation projection, highest-leverage cross-cutting gap)"
    - "Closes GAP-GRAPH04 (belief vs ground truth overlay)"
  affects:
    - "05-05 (Sonnet observer consumes VisibilityProjector output under hard grounding constraint)"
tech_stack:
  added: []
  patterns:
    - "Pure-function projection via ego_subgraph() public API — no private NetworkX access"
    - "Four-stage composition: containment walk → illumination → hidden_properties → belief overlay"
    - "dataclass(slots=True) for zero-overhead projector wrapper"
    - "frozenset for containment edge type membership checks"
key_files:
  created:
    - src/token_world/engine/visibility.py
    - tests/test_engine/test_visibility.py
  modified: []
decisions:
  - "Used ego_subgraph(depth=1, undirected=False) to access edge type data via public KnowledgeGraph API instead of reaching into private _graph NetworkX DiGraph"
  - "ILLUMINATION_THRESHOLD=0.2 as module constant matching D-14 spec; dim = strip contained-node properties to empty dict + dimmed=True marker on room entry"
  - "hidden_properties removal also strips the hidden_properties key itself to avoid leaking the filter list"
  - "Belief overlay uses actor.beliefs[node_id] = {prop: value} minimal representation (not full epistemic logic) per D-14 spec"
metrics:
  duration_minutes: 5
  tasks_completed: 4
  tasks_total: 4
  files_created: 2
  files_modified: 0
  tests_added: 30
  completed_date: "2026-04-13"
---

# Phase 5 Plan 04: VisibilityProjector Summary

Pure-function observation projection layer for the simulation engine, closing the highest-leverage cross-cutting gap (GAP-CROSS01) and the belief-vs-ground-truth gap (GAP-GRAPH04).

## One-liner

VisibilityProjector composes containment walk, illumination filter, hidden_properties stripping, and belief overlay into a JSON-serializable dict[node_id, entry] that the Sonnet observer (Plan 05-05) consumes under a hard grounding constraint.

## What Was Built

### Task 1: Core VisibilityProjector with containment walk (c283c1c / 7f46fdd)

`src/token_world/engine/visibility.py` — `VisibilityProjector` dataclass wrapping a `KnowledgeGraph`.

`project_for(actor_id)` returns `dict[str, dict[str, Any]]` keyed by node id, each value = `{type, properties, edges}`. Stage 1 (containment walk):
- Actor always included (or empty dict if actor doesn't exist)
- Actor's location (first `location` edge target) included
- All nodes connected to the room via `contains`, `inside`, or `on` edges included
- Actor's held items (`holds` edge targets) included
- Deduplication: same node reachable via multiple paths appears only once
- Properties are defensive copies (mutation doesn't affect graph)

Edge type access uses `ego_subgraph(depth=1, undirected=False)` — the public KnowledgeGraph API — rather than private NetworkX attributes.

### Task 2: Illumination filter (7f46fdd)

`_apply_illumination_filter()` — when room `illumination` property < `ILLUMINATION_THRESHOLD` (0.2):
- Room entry gains `dimmed: True` marker
- All contained entities have properties stripped to `{}` and gain `dimmed: True`
- Actor and held items are always fully visible regardless of room darkness
- Exception: if actor holds any entity with `tags` containing `"light_source"` OR `light_source: True` property, dimming is suppressed entirely

### Task 3: Property visibility classes — hidden_properties (7f46fdd)

`_apply_hidden_properties()` — for each projected node:
- If node has `hidden_properties: list[str]`, all named properties are removed from the projection
- The `hidden_properties` key itself is also removed (don't leak the filter list)
- Properties not in the list are retained (default-open visibility)
- Empty `hidden_properties: []` has no effect

### Task 4: Belief overlay — GAP-GRAPH04 (7f46fdd)

`_apply_belief_overlay()` — if actor has `beliefs: dict[node_id, dict[prop, value]]`:
- For each belief entry, if `node_id` is already in projection, overlay belief properties on top of ground truth
- Beliefs for nodes NOT in projection are silently ignored (no phantom entities)
- Non-dict belief values are silently ignored
- Unmentioned properties retain ground truth values

## Deviations from Plan

None — plan executed exactly as written. All four task implementations match the plan's pseudocode closely.

## Known Stubs

None. All four stages are fully implemented and wired. The `project_for()` module-level convenience alias is exported alongside `VisibilityProjector`.

## Threat Flags

None. No new network endpoints, auth paths, or trust boundary changes. The projector is a pure read-only function over the knowledge graph.

## Self-Check: PASSED
