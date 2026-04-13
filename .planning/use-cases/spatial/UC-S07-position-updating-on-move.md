---
id: UC-S07
category: spatial
title: "Position updating on move"
status: reviewed
expected_outcome: pass
setup:
  graph_builder: |
    # Two rooms with distinct centroids. Alice starts in room_a with matching position.
    kg.add_node("alice", node_type="agent", position=[0, 0], location="room_a")
    kg.add_node(
        "room_a",
        node_type="entity",
        subtype="room",
        bbox=[-5, -5, 5, 5],
        centroid=[0, 0],
    )
    kg.add_node(
        "room_b",
        node_type="entity",
        subtype="room",
        bbox=[5, -5, 15, 5],
        centroid=[10, 0],
    )
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("room_a", "room_b", relation="connects")
actions:
  - actor: alice
    intent: "walk east into room_b"
    classified:
      verb: passage_move
      direction: east
      target: room_b
expected_observations:
  - actor: alice
    narrative_contains: ["room_b", "east"]
    graph_assertions:
      - kind: has_edge
        src: alice
        dst: room_b
        relation: located_in
      - kind: property_equals
        node: alice
        property: position
        value: [10, 0]
      - kind: property_equals
        node: alice
        property: location
        value: room_b
gaps:
  - layer: mechanic
    severity: address-now
    summary: "Movement seed updates `location` but does not recompute the actor's `position` from the destination room's centroid, leaving continuous and discrete coordinates desynchronized."
    proposed_fix: "Extend movement mechanic (or add a post-move hook) that copies `centroid` from the destination entity into the actor's `position` whenever the target is a room with a centroid."
  - layer: graph
    severity: defer
    summary: "No first-class concept of 'canonical position of this entity' beyond the ad-hoc `centroid` property; larger systems may want area entities to expose a position accessor."
    proposed_fix: "Document the convention that room-like entities should carry `centroid: [x, y]`, or add a helper `kg.centroid_of(node_id)` that falls back to bbox midpoint."
---

# UC-S07: Position updating on move

## Vignette

Alice stands at coordinates [0, 0] in room_a. Her `position` matches the
room's centroid. She decides to walk east into room_b, whose centroid is
[10, 0]. When the move completes, both her discrete `location` (room_b)
and her continuous `position` ([10, 0]) should reflect the new reality.
Otherwise a later spatial query — "who is closest to the statue at
[9, 0]?" — will still find her at [0, 0], kilometers away from where she
actually is.

## Why this matters

This case surfaces a subtle side-effect bug that is easy to miss in a
purely edge-oriented graph: moving an agent updates the `located_in`
edge but leaves the continuous coordinate stale. All downstream spatial
queries (nearest, within, LOS) rely on `position`, so a stale position
silently poisons every later tick. The fix is small — pull `centroid`
from the destination entity — but the framework needs a standard hook
for it rather than relying on each mechanic to remember.

## Related use cases

- UC-S01 (movement-through-doorway — triggers the same issue when a doorway is the target)
- UC-S03 (nearest-object-query — the query that silently breaks if position drifts)
