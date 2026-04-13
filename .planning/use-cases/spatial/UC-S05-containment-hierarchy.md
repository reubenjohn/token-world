---
id: UC-S05
category: spatial
title: "Containment hierarchy"
status: reviewed
expected_outcome: blocked
setup:
  graph_builder: |
    # Sword inside chest inside room_a. Alice observes the sword.
    kg.add_node("alice", node_type="agent", position=[0, 0])
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_node(
        "chest_oak",
        node_type="entity",
        subtype="chest",
        position=[2, 2],
        open=True,
    )
    kg.add_node(
        "sword_silver",
        node_type="entity",
        subtype="weapon",
        weapon_kind="sword",
    )
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("chest_oak", "room_a", relation="located_in")
    kg.add_edge("sword_silver", "chest_oak", relation="inside")
actions:
  - actor: alice
    intent: "look at the silver sword"
    classified:
      verb: look
      target: sword_silver
expected_observations:
  - actor: alice
    narrative_contains: ["sword", "chest", "room_a"]
    graph_assertions:
      - kind: has_edge
        src: sword_silver
        dst: chest_oak
        relation: inside
      - kind: has_edge
        src: chest_oak
        dst: room_a
        relation: located_in
      - kind: has_node
        node: sword_silver
gaps:
  - layer: engine
    severity: address-now
    summary: "Observation seed reads direct neighbors only; it cannot follow an `inside → located_in` chain to describe 'the sword in the chest in the room'."
    proposed_fix: "Add a recursive-containment walker to the observation pipeline, capped at a configurable depth (anticipates SIM-07)."
  - layer: graph
    severity: defer
    summary: "No distinction between `inside` and `located_in`; both encode containment but at different granularities and future mechanics may need to treat them uniformly."
    proposed_fix: "Document containment-relation convention and optionally expose a `containment_chain(node)` helper that walks whichever relations are tagged containment-like."
---

# UC-S05: Containment hierarchy

## Vignette

Alice stands in room_a. A heavy oak chest sits against the wall, its lid
propped open. Inside the chest, resting on velvet, lies a silver sword.
Alice looks at the sword. The description she hears should name all three
nested layers — sword, chest, room — not just the sword in isolation, and
not the chest with the sword omitted.

The graph already encodes this nesting through two relations
(`sword_silver -inside→ chest_oak -located_in→ room_a`). The question is
whether the engine walks the chain.

## Why this matters

Containment is a chain, not a single edge. The observation seed returns
direct neighbors; a sword's direct neighbor is the chest, not the room.
Any realistic scene description (inventory, crates, pockets, rooms,
houses) needs transitive containment. This case is the simplest form of
that generalized problem and surfaces an engine-layer gap: the
observation pipeline needs a bounded recursive walker.

## Related use cases

- UC-S01 (movement-through-doorway — the other chained-traversal case)
- UC-R02 (inventory — containment inside an agent rather than an entity)
