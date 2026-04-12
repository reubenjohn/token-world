---
id: UC-S03
category: spatial
title: "Nearest object query"
status: reviewed
setup:
  graph_builder: |
    # Alice at origin. Three weapons at varying distances.
    kg.add_node("alice", node_type="agent", position=[0, 0])
    kg.add_node("armory", node_type="entity", subtype="room", bbox=[-20, -20, 20, 20])
    kg.add_edge("alice", "armory", relation="located_in")
    kg.add_node(
        "sword_rusty",
        node_type="entity",
        subtype="weapon",
        weapon_kind="sword",
        position=[7, 0],
    )
    kg.add_node(
        "dagger_bronze",
        node_type="entity",
        subtype="weapon",
        weapon_kind="dagger",
        position=[3, 1],
    )
    kg.add_node(
        "bow_long",
        node_type="entity",
        subtype="weapon",
        weapon_kind="bow",
        position=[12, -4],
    )
    for obj in ("sword_rusty", "dagger_bronze", "bow_long"):
        kg.add_edge(obj, "armory", relation="located_in")
actions:
  - actor: alice
    intent: "scan the armory and identify the nearest weapon"
    classified:
      verb: find_nearest
      target: dagger_bronze
      filter: {subtype: weapon}
expected_observations:
  - actor: alice
    narrative_contains: ["dagger_bronze", "nearest"]
    graph_assertions:
      - kind: has_node
        node: dagger_bronze
      - kind: property_equals
        node: dagger_bronze
        property: subtype
        value: weapon
      - kind: has_property
        node: dagger_bronze
        property: position
gaps:
  - layer: graph
    severity: address-now
    summary: "No nearest-neighbor query on the spatial index; a brute-force scan of all positioned nodes does not scale and is not part of the public KnowledgeGraph API."
    proposed_fix: "Expose `ctx.spatial.nearest(point, filter=…, k=1)` backed by the GRAPH-06 R-tree with an optional property-equality predicate."
  - layer: mechanic
    severity: address-now
    summary: "No find-nearest mechanic; the observation seed only describes what is already in the actor's neighborhood edges, not arbitrary positioned entities."
    proposed_fix: "Add a `find_nearest` mechanic that classifies intents like 'find the nearest weapon' and returns the named entity via the new spatial query."
---

# UC-S03: Nearest object query

## Vignette

Alice stands in the armory. She needs a weapon — any weapon will do, so
long as it is the nearest one to her. She scans the room. A bronze dagger
sits on a table three paces away; a rusty sword hangs on the far wall; a
longbow leans in the corner. She walks toward the dagger without hesitation.

The engine must pick the dagger (distance ≈ 3.16), not the sword (distance
7) or the bow (distance ≈ 12.6), and it must say so by name.

## Why this matters

This is the simplest "ask a geometric question of the world" case. The
graph's edge structure knows *what* is in the armory; only the spatial
index knows *which is closest*. The case pressure-tests GRAPH-06's ability
to run a filtered nearest-neighbor query and the engine's ability to
classify an intent like "nearest weapon" as a find-nearest action rather
than a look or move.

## Related use cases

- UC-S04 (area-of-effect — also needs spatial index, but `within` instead of `nearest`)
- UC-R01 onward (resource cases that depend on "find the nearest X")
