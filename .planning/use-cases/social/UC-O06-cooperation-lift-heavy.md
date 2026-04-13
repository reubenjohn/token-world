---
id: UC-O06
category: social
title: "Cooperation to lift a heavy object"
status: reviewed
expected_outcome: blocked
setup:
  graph_builder: |
    # A boulder too heavy for one person blocks a path; two agents together can shift it.
    kg.add_node("alice", node_type="agent", strength=200)
    kg.add_node("bob", node_type="agent", strength=200)
    kg.add_node("boulder", node_type="entity", subtype="obstacle", mass=500, lifted_by=[])
    kg.add_node("path", node_type="entity", subtype="room")
    kg.add_edge("alice", "path", relation="located_in")
    kg.add_edge("bob", "path", relation="located_in")
    kg.add_edge("boulder", "path", relation="located_in")
actions:
  - actor: alice
    intent: "lift the boulder with bob"
    classified:
      verb: lift
      target: boulder
      co_actors: [bob]
  - actor: bob
    intent: "help alice lift the boulder"
    classified:
      verb: lift
      target: boulder
      co_actors: [alice]
expected_observations:
  - actor: alice
    narrative_contains: ["lift", "boulder", "bob"]
    graph_assertions:
      - kind: property_equals
        node: boulder
        property: lifted_by
        value: ["alice", "bob"]
  - actor: bob
    narrative_contains: ["heave", "boulder"]
    graph_assertions:
      - kind: property_equals
        node: boulder
        property: lifted_by
        value: ["alice", "bob"]
gaps:
  - layer: engine
    severity: address-now
    summary: "The tick loop interprets each agent's intent independently; there is no way to fuse two compatible intents into a single multi-actor mechanic invocation."
    proposed_fix: "Add an intent-matching pre-pass that detects complementary `co_actors` across intents in the same tick and dispatches a single multi-actor mechanic call."
  - layer: mechanic
    severity: address-now
    summary: "No cooperative-action mechanic exists; the mechanic API assumes a single `actor` argument and cannot express summed-capability preconditions like `sum(strength) >= mass`."
    proposed_fix: "Extend the mechanic framework to accept an `actors: list[NodeId]` precondition and provide a helper `sum_property(actors, prop)` for summed-capability checks."
  - layer: engine
    severity: defer
    summary: "No commit/rollback semantics if one participant's precondition fails mid-tick (e.g., bob is actually exhausted)."
    proposed_fix: "Multi-actor mechanics should evaluate all preconditions atomically before any side effect fires, and fail the whole action if any participant is ineligible."
---

# UC-O06: Cooperation to lift a heavy object

## Vignette

The boulder half-blocks the path, and neither Alice nor Bob can shift it
alone. They brace their shoulders against opposite faces of the stone,
count to three, and heave in unison. The boulder rocks, tips, and rolls
clear of the track — together they managed what neither could have done
by themselves.

## Why this matters

This is the first scenario where an action is fundamentally a property
of two (or more) intents considered together, not of any single intent
in isolation. Our tick loop today processes each agent one at a time,
so "lift with bob" from alice and "help alice lift" from bob look like
two separate failing attempts. Fixing that requires both a mechanic-API
change (actors as a list) and an engine-level intent-fusion pass — a
non-trivial concurrency design decision that this use case forces us
to confront explicitly.

## Related use cases

- UC-O01 (trade — two intents must also agree, but sequentially, not simultaneously)
- UC-O08 (speech broadcast — one actor affecting many, the inverse shape)
