---
id: UC-S01
category: spatial
title: "Movement through a doorway"
status: reviewed
expected_outcome: pass
setup:
  graph_builder: |
    # Two rooms connected by a doorway entity. Alice starts in room_a.
    kg.add_node("alice", node_type="agent", position=[0, 0], stamina=10)
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_node("room_b", node_type="entity", subtype="room", bbox=[5, -5, 15, 5])
    kg.add_node(
        "doorway_1",
        node_type="entity",
        subtype="doorway",
        position=[5, 0],
        open=True,
    )
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("room_a", "doorway_1", relation="connects")
    kg.add_edge("doorway_1", "room_b", relation="connects")
actions:
  - actor: alice
    intent: "walk east through the doorway into room_b"
    classified:
      verb: passage_move
      direction: east
      target: room_b
      via: doorway_1
expected_observations:
  - actor: alice
    narrative_contains: ["room_b", "doorway", "east"]
    graph_assertions:
      - kind: has_edge
        src: alice
        dst: room_b
        relation: located_in
      - kind: not_has_edge
        src: alice
        dst: room_a
        relation: located_in
      - kind: has_node
        node: doorway_1
gaps:
  - layer: mechanic
    severity: address-now
    summary: "Movement seed requires a direct edge from current location to target; it cannot traverse an intermediate doorway entity."
    proposed_fix: "Extend movement mechanic (or add doorway_traversal mechanic) to resolve a path through entities tagged subtype=doorway when they expose a connects→connects chain, honoring the `open` property."
  - layer: graph
    severity: defer
    summary: "No first-class notion of 'portals' or 'passage' in the graph vocabulary; doorways are ad-hoc entities with subtype='doorway'."
    proposed_fix: "Document a convention (or helper method) for passage-typed entities so mechanics can query them uniformly."
---

# UC-S01: Movement through a doorway

## Vignette

Alice stands at the eastern edge of room_a, a few paces from the open doorway
that leads to room_b. She decides to walk east. The doorway is open; beyond
it the floorboards of the adjoining room are visible. She steps through and
finds herself on the other side, the frame passing behind her as she enters
room_b.

A human reading this expects a single observation: she is now in room_b, no
longer in room_a, and the doorway mediated the transition. The graph should
reflect that `located_in` has moved from room_a to room_b.

## Why this matters

This case pressure-tests whether the movement seed mechanic can handle the
common real-world pattern of rooms connected *through* a passage entity,
rather than directly. The seed only traverses a single `located_in`-eligible
edge; a doorway sits between room_a and room_b, so the seed's `check` will
fail unless the engine can plan through the doorway. This surfaces the first
mechanic-layer gap: passage traversal.

## Related use cases

- UC-S06 (traversal-across-terrain — same shape, different passage entity)
- UC-S07 (position-updating-on-move — what happens to `position` after the move)
