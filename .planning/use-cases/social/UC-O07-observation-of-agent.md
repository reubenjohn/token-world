---
id: UC-O07
category: social
title: "Observation of another agent"
status: reviewed
setup:
  graph_builder: |
    # Alice sees bob across the tavern; bob is wounded and wearing a red cloak.
    kg.add_node("alice", node_type="agent")
    kg.add_node(
        "bob",
        node_type="agent",
        hp=80,
        max_hp=100,
        posture="slumped",
        wearing=["red_cloak"],
        secret_plan="assassinate the duke",
    )
    kg.add_node("tavern", node_type="entity", subtype="room")
    kg.add_edge("alice", "tavern", relation="located_in")
    kg.add_edge("bob", "tavern", relation="located_in")
actions:
  - actor: alice
    intent: "look at bob"
    classified:
      verb: observe
      target: bob
expected_observations:
  - actor: alice
    narrative_contains: ["bob", "slumped", "red cloak"]
    graph_assertions:
      - kind: has_node
        node: bob
      - kind: has_property
        node: bob
        property: posture
      - kind: has_property
        node: bob
        property: wearing
gaps:
  - layer: engine
    severity: address-now
    summary: "The observation seed exposes every property on the target node indiscriminately — there is no notion of which properties are outwardly visible vs. private."
    proposed_fix: "Tag each property (or each property-writing mechanic) with a visibility class (`public`, `private`, `requires_inspection`); the observation seed filters by class when projecting the target node."
  - layer: mechanic
    severity: defer
    summary: "Visible-state derivation is static — hp shows as a raw number, not as `slightly wounded`."
    proposed_fix: "Add a per-property `render_visible(value) -> str` hook so mechanics can emit human-readable summaries without leaking exact numbers."
  - layer: engine
    severity: defer
    summary: "No line-of-sight check; if bob were behind a screen, alice would still observe him."
    proposed_fix: "Compose observation with the spatial `line_of_sight` query (UC-S0x) once spatial is mature."
---

# UC-O07: Observation of another agent

## Vignette

Alice scans the tavern and finds bob in the back corner, slumped against
the wall with his red cloak drawn tight around his shoulders. He looks
tired — hurt, maybe. Whatever he's planning, he keeps to himself; she
can only see what he's chosen to show.

## Why this matters

Observation is the one social scenario where a seed mechanic already
exists — the observation seed projects a target node's properties into
narrative. That makes UC-O07 a stress test rather than a greenfield
design: the seed happily leaks `secret_plan` alongside posture and
clothing. We have to decide what "visible" means at the framework level,
because any private state — intentions, beliefs, hidden inventory —
leaks until we do. This use case is where the visibility contract gets
designed.

## Related use cases

- UC-O04 (deception — beliefs are private by construction)
- UC-O08 (speech broadcast — a different kind of information channel)
