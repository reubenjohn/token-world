---
id: UC-S02
category: spatial
title: "Line-of-sight occlusion"
status: reviewed
setup:
  graph_builder: |
    # Alice in room_a, bob in room_b, wall between. Rooms share a boundary at x=5.
    kg.add_node("alice", node_type="agent", position=[0, 0])
    kg.add_node("bob", node_type="agent", position=[10, 0])
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_node("room_b", node_type="entity", subtype="room", bbox=[5, -5, 15, 5])
    kg.add_node(
        "wall_1",
        node_type="entity",
        subtype="wall",
        bbox=[4.9, -5, 5.1, 5],
        occludes=True,
    )
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("bob", "room_b", relation="located_in")
    kg.add_edge("wall_1", "room_a", relation="borders")
    kg.add_edge("wall_1", "room_b", relation="borders")
actions:
  - actor: alice
    intent: "look across the wall toward bob"
    classified:
      verb: look
      target: bob
expected_observations:
  - actor: alice
    narrative_contains: ["cannot see", "wall"]
    graph_assertions:
      - kind: not_has_property
        node: alice
        property: saw
      - kind: has_node
        node: wall_1
      - kind: has_property
        node: wall_1
        property: occludes
gaps:
  - layer: mechanic
    severity: address-now
    summary: "No line-of-sight mechanic; observation seed reports direct neighbors only and will either error on an out-of-room target or (worse) silently reveal bob."
    proposed_fix: "Add a look mechanic that uses a spatial ray-check against entities with `occludes=True` and returns a 'cannot see' narrative when the ray is blocked."
  - layer: graph
    severity: address-now
    summary: "No spatial query for 'entities intersecting the segment from A to B'; without it, an LOS mechanic cannot check occluders efficiently."
    proposed_fix: "Extend GRAPH-06 spatial index with a `segment_intersections(p1, p2, filter=occludes)` helper on the R-tree."
---

# UC-S02: Line-of-sight occlusion

## Vignette

Alice is in room_a; bob is in the adjoining room_b. A solid stone wall
separates the two rooms, pierced by no window or doorway along this
sightline. Alice tries to look at bob. She sees the wall — and nothing of
what lies beyond it. The narrative the engine returns should name the wall
as the reason bob is invisible, not a distance limit or an error.

No graph edge `alice —saw→ bob` should be created; the engine must not
grant perceptual knowledge across a known occluder.

## Why this matters

Line-of-sight is the canonical spatial query the graph alone cannot answer
cheaply. It needs geometric reasoning — a segment between two positions
intersected against occluder bounding boxes. This case tests two layers at
once: the graph layer's ability to run `segment_intersections` queries, and
the mechanic layer's ability to express "cannot see" as a first-class
observation rather than a generated hallucination.

## Related use cases

- UC-S03 (nearest-object-query — also requires GRAPH-06 spatial index)
- UC-S05 (containment-hierarchy — the other case where "just list neighbors" fails)
