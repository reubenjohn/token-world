---
id: UC-XX00
category: spatial
title: "Short human-readable title"
status: draft            # draft | reviewed | locked
setup:
  graph_builder: |
    # Python executed against a fresh KnowledgeGraph bound to `kg`.
    # Use KnowledgeGraph API only (add_node/add_edge/set); no direct nx access.
    kg.add_node("alice", node_type="agent", position=[0, 0])
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_edge("alice", "room_a", relation="located_in")
actions:
  - actor: alice
    intent: "say what the actor is trying to do in natural language"
    classified:
      verb: example_verb
      target: room_a
      # additional keys as needed: direction, indirect_object, amount, utterance, ...
expected_observations:
  - actor: alice
    narrative_contains: ["substring one", "substring two"]
    graph_assertions:
      # One example of each supported assertion kind. Delete what you don't need.
      - kind: has_node
        node: room_a
      - kind: has_edge
        src: alice
        dst: room_a
        relation: located_in
      - kind: not_has_edge
        src: alice
        dst: room_b
        relation: located_in
      - kind: has_property
        node: alice
        property: position
      - kind: property_equals
        node: alice
        property: stamina
        value: 10
      - kind: not_has_property
        node: alice
        property: poisoned
gaps:
  - layer: mechanic        # graph | mechanic | engine
    severity: address-now  # address-now | defer | out-of-scope
    summary: "One-sentence description of the missing capability."
    proposed_fix: "Concrete suggestion for closing the gap (name a mechanic, API, or engine hook)."
---

# UC-XX00: Short human-readable title

## Vignette

Two or three sentences describing the scene from the actor's perspective.
Prose only — no YAML, no code fences. Should read like a paragraph from a
novella, grounded in the entities declared in `setup.graph_builder`.

## Why this matters

Name the framework concern this scenario is pressure-testing. What would
break or look wrong if the engine handled it poorly? Which seed mechanic
(if any) is being exercised, and which gap are you surfacing?

## Related use cases

- UC-XX01 (short reason for relation)
- UC-XX02 (short reason for relation)
