# Spatial Use Cases — Manifest

Spatial is the most framework-stretching category: positions, lines of sight,
containment, adjacency, doorways, area effects, and trajectories all exercise
the R-tree spatial index (GRAPH-06) and the movement seed mechanic. Seven
cases cover the minimum surface; movement + observation seeds already handle
the basic edge-following case, so most YES flags here are about *what's
missing beyond the seed*.

| ID     | Slug                          | Title                                   | Scenario (one line)                                                                          | No seed mechanic? | Notes                                                                                  |
|--------|-------------------------------|-----------------------------------------|----------------------------------------------------------------------------------------------|--------------------|----------------------------------------------------------------------------------------|
| UC-S01 | movement-through-doorway      | Movement through a doorway              | Alice walks east through a doorway into an adjacent room.                                    | no                 | Movement seed covers direct edges; doorway traversal via `connects` may surface a gap. |
| UC-S02 | line-of-sight-occlusion       | Line-of-sight occlusion                 | Alice tries to observe bob in an adjacent room; a wall occludes.                             | YES                | No LOS mechanic exists; graph query needed for occluder ray-check.                     |
| UC-S03 | nearest-object-query          | Nearest object query                    | Alice asks for the nearest weapon.                                                           | YES                | Requires `ctx.spatial.nearest` + subtype filter; no "query surroundings" mechanic yet. |
| UC-S04 | area-of-effect                | Area-of-effect explosion                | An explosion at [5,5] damages all entities within radius 3.                                  | YES                | Needs bbox `within` query + fan-out apply pattern; no AoE mechanic in seeds.           |
| UC-S05 | containment-hierarchy         | Containment hierarchy                   | Sword is inside chest which is inside room_a; describing sword involves a chain.             | YES                | No transitive-containment query; observation seed only reads direct neighbors.         |
| UC-S06 | traversal-across-terrain      | Traversal across terrain                | Alice crosses a river via a bridge.                                                          | YES                | No terrain-typed traversal mechanic; movement seed is terrain-agnostic.                |
| UC-S07 | position-updating-on-move     | Position updating on move               | After movement, alice's position reflects her new room's centroid.                           | no                 | Movement seed updates `located_in` but doesn't recompute `position` from room bbox.    |

## Wave 2 Authoring Checklist

Each row below maps to exactly one file. Wave 2 agents copy `_TEMPLATE.md` to
the target path and fill it in; no agent touches more than one path.

- [ ] `.planning/use-cases/spatial/UC-S01-movement-through-doorway.md`
- [ ] `.planning/use-cases/spatial/UC-S02-line-of-sight-occlusion.md`
- [ ] `.planning/use-cases/spatial/UC-S03-nearest-object-query.md`
- [ ] `.planning/use-cases/spatial/UC-S04-area-of-effect.md`
- [ ] `.planning/use-cases/spatial/UC-S05-containment-hierarchy.md`
- [ ] `.planning/use-cases/spatial/UC-S06-traversal-across-terrain.md`
- [ ] `.planning/use-cases/spatial/UC-S07-position-updating-on-move.md`
