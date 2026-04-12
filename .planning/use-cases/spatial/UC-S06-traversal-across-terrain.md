---
id: UC-S06
category: spatial
title: "Traversal across terrain"
status: reviewed
setup:
  graph_builder: |
    # Alice in room_a; a river separates room_a from room_b; a bridge spans it.
    kg.add_node("alice", node_type="agent", position=[0, 0])
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_node("room_b", node_type="entity", subtype="room", bbox=[10, -5, 20, 5])
    kg.add_node(
        "river_thorn",
        node_type="entity",
        subtype="river",
        bbox=[5, -5, 10, 5],
        traversable=False,
    )
    kg.add_node(
        "bridge_stone",
        node_type="entity",
        subtype="bridge",
        bbox=[6, -1, 9, 1],
        traversable=True,
        spans="river_thorn",
    )
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("river_thorn", "room_a", relation="borders")
    kg.add_edge("river_thorn", "room_b", relation="borders")
    kg.add_edge("bridge_stone", "room_a", relation="connects")
    kg.add_edge("bridge_stone", "room_b", relation="connects")
actions:
  - actor: alice
    intent: "cross the river by walking over the stone bridge"
    classified:
      verb: move
      target: bridge_stone
      indirect_object: room_b
      via: bridge_stone
expected_observations:
  - actor: alice
    narrative_contains: ["bridge", "room_b", "river"]
    graph_assertions:
      - kind: has_edge
        src: alice
        dst: room_b
        relation: located_in
      - kind: not_has_edge
        src: alice
        dst: room_a
        relation: located_in
      - kind: property_equals
        node: bridge_stone
        property: traversable
        value: true
gaps:
  - layer: mechanic
    severity: address-now
    summary: "Movement seed is terrain-agnostic; it cannot distinguish 'walk through a river (illegal)' from 'walk across a bridge (legal)' when both are adjacent to the same rooms."
    proposed_fix: "Add a terrain-aware movement mechanic (or extend movement seed) that requires a traversable=True entity on the chosen path and rejects traversable=False obstacles."
  - layer: graph
    severity: defer
    summary: "No canonical terrain-typing system; `traversable` is an ad-hoc boolean property rather than a first-class attribute."
    proposed_fix: "Document a terrain vocabulary (water, wall, floor, bridge, stair) and either enforce it via a convention or add a lightweight validator."
  - layer: mechanic
    severity: defer
    summary: "Bridges may have state (damaged, flooded, locked) that blocks traversal; the seed has no hook for consulting entity state during pathfinding."
    proposed_fix: "Allow traversable to be callable (or a predicate expression) so mechanics can reason about state-dependent passability."
---

# UC-S06: Traversal across terrain

## Vignette

The river Thorn cuts between room_a and room_b. Alice cannot ford it —
the current is swift and the water deep. A stone bridge spans the river
a short walk upstream. Alice steps onto the bridge, crosses the arch,
and descends into room_b on the far bank. The river is behind her; she
did not swim, she did not wade; she walked across the bridge.

The engine must allow the move specifically because the bridge is
traversable, and must reject the same intent phrased as "walk through
the river."

## Why this matters

This is the terrain-typing case. Real worlds do not have uniform
passability — water, walls, ravines, cliffs all interact with movement
in type-specific ways. The seed movement mechanic treats every edge as
walkable; this case demands a terrain-aware extension that consults
entity properties before allowing a move. It also raises a graph-layer
question about whether terrain typing should be formalized or left
emergent.

## Related use cases

- UC-S01 (movement-through-doorway — the indoor analog of bridge traversal)
- UC-V01 onward (environmental cases with weather-driven passability)
