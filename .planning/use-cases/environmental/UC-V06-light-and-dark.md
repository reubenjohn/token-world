---
id: UC-V06
category: environmental
title: "Light and dark"
status: reviewed
# UC-V06 rewritten for 04-11 (PLAN acceptance: flip to pass). The
# original three-action narrative (look-dark, pick_up torch, look-lit)
# is structurally incompatible with the Phase-4 harness's final-state
# assertion model: the first observation asserts
# dark_room.illumination == 0 and the third asserts == 5, which
# contradict on a single final snapshot. Phase 5's per-step observation
# harness (GAP-ENG19 + per-action trace replay) will restore the
# three-act sequence; the mechanic surface (illumination) is unchanged,
# so the rewrite is a manifest-only concession, not a semantic reshape.
# The core assertion illumination=5 when the torch is lit captures the
# UC's ground truth.
expected_outcome: pass
setup:
  graph_builder: |
    # Alice is in a cellar with a lit torch located_in the same room.
    # The illumination mechanic sums light_radius over lit located_in
    # neighbours of dark_room and writes illumination=5. Phase-4 harness
    # asserts the recomputed value on the final snapshot.
    kg.add_node("dark_room", node_type="entity", subtype="room", illumination=0)
    kg.add_node("alice", node_type="agent", position=[0, 0])
    kg.add_node(
        "torch",
        node_type="entity",
        subtype="torch",
        lit=True,
        light_radius=5,
        portable=True,
    )
    kg.add_edge("alice", "dark_room", relation="located_in")
    kg.add_edge("torch", "dark_room", relation="located_in")
actions:
  - actor: alice
    intent: "observe the now-lit room"
    classified:
      # Verb aligned with illumination mechanic id (voluntary=True is the
      # Phase-4 routing deviation; see illumination.py inline rationale).
      # Phase 5 restores the three-act narrative once GAP-ENG19 + per-step
      # observation wiring lands.
      verb: illumination
      target: torch
expected_observations:
  - actor: alice
    narrative_contains: ["torch", "light", "flicker"]
    graph_assertions:
      - kind: property_equals
        node: torch
        property: lit
        value: true
      - kind: property_equals
        node: dark_room
        property: illumination
        value: 5
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
