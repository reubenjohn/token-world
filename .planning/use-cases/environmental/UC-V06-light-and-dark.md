---
id: UC-V06
category: environmental
title: "Light and dark"
status: draft
setup:
  graph_builder: |
    # Alice and Bob are in a pitch-black cellar. An unlit torch hangs on
    # the wall nearby but nobody is carrying it. Alice shouldn't be able
    # to see Bob until she picks up the torch and it becomes a live light
    # source.
    kg.add_node("dark_room", node_type="entity", subtype="room", illumination=0)
    kg.add_node("alice", node_type="agent", position=[0, 0])
    kg.add_node("bob", node_type="agent", position=[2, 0])
    kg.add_node(
        "torch",
        node_type="entity",
        subtype="torch",
        lit=False,
        light_radius=5,
        portable=True,
    )
    kg.add_edge("alice", "dark_room", relation="located_in")
    kg.add_edge("bob", "dark_room", relation="located_in")
    kg.add_edge("torch", "dark_room", relation="located_in")
actions:
  - actor: alice
    intent: "peer around the room to see who else is here"
    classified:
      verb: look
      target: dark_room
  - actor: alice
    intent: "grope toward the wall, find the torch, and light it"
    classified:
      verb: pick_up
      target: torch
  - actor: alice
    intent: "now that the torch is lit, look around again"
    classified:
      verb: look
      target: dark_room
expected_observations:
  - actor: alice
    narrative_contains: ["dark", "cannot see", "too dark"]
    graph_assertions:
      - kind: property_equals
        node: dark_room
        property: illumination
        value: 0
      - kind: not_has_property
        node: alice
        property: last_saw
  - actor: alice
    narrative_contains: ["torch", "light", "flicker"]
    graph_assertions:
      - kind: has_edge
        src: alice
        dst: torch
        relation: holds
      - kind: property_equals
        node: torch
        property: lit
        value: true
  - actor: alice
    narrative_contains: ["bob", "see"]
    graph_assertions:
      - kind: property_equals
        node: dark_room
        property: illumination
        value: 5
      - kind: has_property
        node: alice
        property: last_saw
gaps:
  - layer: engine
    severity: address-now
    summary: "Observation seed lists neighbors regardless of illumination; there's no filter between 'what the graph contains' and 'what the actor can perceive' (SIM-07)."
    proposed_fix: "Introduce an observation filter layer in the engine that consults light/LOS before revealing entities (SIM-07 observation filtering)."
  - layer: mechanic
    severity: address-now
    summary: "No mechanic propagates illumination from a lit torch to its surrounding room/entities; lighting up a torch doesn't actually change the room's illumination."
    proposed_fix: "Author illumination_propagation mechanic that sums light_radius from lit sources within a room and writes illumination onto the room node."
  - layer: graph
    severity: defer
    summary: "No standard for how light interacts with containment (e.g., a torch in a closed chest)."
    proposed_fix: "Define a light-exposure derivation over containment edges; document in ARCHITECTURE.md alongside the illumination_propagation mechanic."
---

# UC-V06: Light and dark

## Vignette

Alice calls Bob's name into the darkness of the cellar but she can't see
him — she can't see anything at all; the room is pitch black. She feels
along the damp stone wall until her hand finds a wooden haft: the torch.
She takes it down, strikes it alight, and suddenly the whole cellar is
visible. Bob is right there, squinting at her, three paces away.

## Why this matters

This case pressure-tests the separation between *what exists in the graph*
and *what the actor can perceive*. Those have to be different layers for
the simulation to feel like a world with limits rather than a spreadsheet
where every property is visible to everyone. It is also the case that
forces the engine to gain an observation filter — a feature that will be
reused by stealth, invisibility, fog-of-war, and sensory disabilities.

## Related use cases

- UC-S02 (line-of-sight-occlusion — the other half of perception filtering)
- UC-V04 (seasons — day/night is another illumination scenario)
- UC-O* (social — whispers and overhearing have the same perception-filter pattern)
