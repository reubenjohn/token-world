# Spatial — Category Summary

**Use cases reviewed:** 7 (UC-S01..UC-S07)
**Total inline gaps:** 16
**Deduplicated gaps:** 14

## Review Findings

- **All UCs pass schema validator:** YES (UC-S01..UC-S07 all load cleanly via `load_use_case` and produce zero errors from `validate_frontmatter`).
- **All UCs' `setup.graph_builder` creates every referenced actor/target:** YES. Each UC's `exec(setup.graph_builder, {"kg": kg})` completed without exceptions against a fresh `KnowledgeGraph`, and every `actions[].actor` and `actions[].classified.target` resolves to a node the setup created.
- **UC status transitions:**
  - draft → reviewed: UC-S01, UC-S02, UC-S03, UC-S04, UC-S05, UC-S06, UC-S07 (all 7).
  - remaining as draft: none.
- **Cross-category dependency flagged:** the spatial gaps frequently reference `ctx.spatial.*` queries — these assume GRAPH-06 (the completed Phase 3 spatial R-tree) is available to mechanics, which it already is. Wave 4 should consolidate the "spatial observation filter" pattern (S-E01 below) with UC-V06 light/LOS and UC-O07 visibility filtering — all three describe the same engine-layer projection surface.

## Deduplicated Gap List

| ID | Layer | Severity | Summary | Source UCs | Proposed Fix |
|----|-------|----------|---------|------------|--------------|
| S-M01 | mechanic | address-now | Movement seed cannot traverse an intermediate doorway entity; it only handles direct `connects` edges between rooms, and has no `open`-property gate. | UC-S01, UC-E06 (cross-cat) | Extend movement mechanic (or add a `doorway_traversal` mechanic) to resolve a path through `subtype=doorway` entities along the `connects` chain, honoring the `open`/`locked` property and emitting a grounded "the way is blocked" narrative on failure. |
| S-M02 | mechanic | address-now | No line-of-sight mechanic; the observation seed lists direct neighbors regardless of occluders, so it either errors on out-of-room targets or silently reveals them. | UC-S02 | Add a `look` mechanic that uses a spatial ray-check against entities with `occludes=True`, returning a "cannot see" narrative when the ray is blocked. |
| S-G01 | graph | address-now | No segment-intersection spatial query; an LOS mechanic cannot efficiently check occluders on the line from A to B. | UC-S02 | Extend GRAPH-06 with `ctx.spatial.segment_intersections(p1, p2, filter=occludes)` on top of the R-tree. |
| S-G02 | graph | address-now | No nearest-neighbor query; `ctx.spatial` exposes bbox/radius queries but not k-NN, so "nearest X" intents require a brute-force scan. | UC-S03 | Expose `ctx.spatial.nearest(point, filter=..., k=1)` backed by the R-tree with optional property-equality predicate. |
| S-M03 | mechanic | address-now | No `find_nearest` mechanic; the observation seed only describes what is already in the actor's neighborhood edges. | UC-S03 | Add `find_nearest` mechanic that classifies intents like "find the nearest weapon" and returns the named entity via the new spatial query (S-G02). |
| S-G03 | graph | address-now | No `within(shape)` spatial query; an AoE mechanic must iterate every positioned node to pick victims. | UC-S04 | Expose `ctx.spatial.within(shape)` on GRAPH-06, supporting axis-aligned bbox and centered-radius shapes. |
| S-M04 | mechanic | address-now | No AoE mechanic; seeds handle single-target verbs only. Damage-conservation across affected entities is not checked. | UC-S04 | Add an `area_of_effect` mechanic that fans out a damage predicate over `ctx.spatial.within(...)` and emits one mutation per affected entity. |
| S-E01 | engine | address-now | Observation pipeline reads direct neighbors only; it cannot follow an `inside → located_in` containment chain to describe nested contents. | UC-S05 | Add a recursive-containment walker to the observation pipeline, capped at a configurable depth (anticipates SIM-07). See also UC-V06/UC-O07 for the broader "observation projection" gap. |
| S-M05 | mechanic | address-now | Movement seed is terrain-agnostic; it cannot distinguish "walk through a river (illegal)" from "walk across a bridge (legal)" when both are adjacent to the same rooms. | UC-S06 | Add a terrain-aware movement mechanic (or extend movement seed) requiring `traversable=True` on the chosen path and rejecting `traversable=False` obstacles. |
| S-M06 | mechanic | address-now | Movement seed updates `location` edges but does not recompute the actor's continuous `position` from the destination centroid, leaving discrete and continuous coords desynchronized. | UC-S07 | Extend movement (or add a post-move hook) to copy `centroid` from the destination entity into the actor's `position` when the target is a room with a centroid. |
| S-G04 | graph | defer | No first-class "portal"/"passage" vocabulary; doorways are ad-hoc `subtype='doorway'` entities without standard traversal semantics. | UC-S01 | Document a convention (or helper) for passage-typed entities so mechanics can query them uniformly. |
| S-G05 | graph | defer | No canonical terrain-typing system; `traversable` is an ad-hoc boolean rather than a first-class attribute. | UC-S06, UC-V05 (cross-cat) | Document a terrain vocabulary (water, wall, floor, bridge, stair) and/or add a lightweight validator. |
| S-G06 | graph | defer | Containment split across `inside` vs. `located_in`; no canonical convention or `containment_chain(node)` helper for uniform traversal. | UC-S05 | Document containment-relation convention; optionally expose `containment_chain(node)` that walks all containment-tagged relations. Also relevant to UC-V06 light-through-containment. |
| S-G07 | graph | defer | No canonical "position of this entity" accessor; room-like entities expose `centroid` ad-hoc, and an entity's position is not uniformly derivable. | UC-S07 | Document room-centroid convention, or add `kg.centroid_of(node_id)` that falls back to bbox midpoint. |

(Note: two `defer`-tier items not promoted to their own rows — UC-S04's batched/transactional fan-out mutations and UC-S06's state-dependent-passability predicate — are captured under S-E01/S-M05 as adjacent concerns; Wave 4 can split them out into their own canonical GAP IDs if cross-category synthesis finds evidence they deserve separate treatment.)

**Audit metadata:** 16 inline gaps across 7 UCs collapsed to 14 entries; the two merges were (a) UC-S01's doorway-traversal gap with UC-E06's locked-door gap (same movement-mechanic surface, viewed from different narrative angles), and (b) UC-S06's terrain-ontology defer row with UC-V05's terrain-subtype defer row (same canonical-vocabulary question).

## Patterns Noticed

Every address-now spatial gap points to the same two-layer pattern: the graph already stores positions (via the Phase 3 spatial index) but lacks the **query vocabulary** (`within`, `nearest`, `segment_intersections`) that mechanics need, and there is **no seed mechanic** that consumes those queries to produce grounded observations. Closing the graph-layer gaps without the mechanic layer leaves capabilities invisible to agents; closing mechanic gaps without the graph layer forces brute-force scans. The `defer` items cluster around **vocabulary consistency** (portals, terrain, containment, canonical positions) — none block v1 but all would reduce ad-hoc divergence between mechanic authors. Finally, UC-S01's doorway gap and UC-E06's locked-door gap are the **same movement-mechanic gap** viewed from different angles; Wave 4 should merge them when assigning a canonical GAP-M ID.
