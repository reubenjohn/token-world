---
id: UC-V05
category: environmental
title: "Terrain effect"
status: reviewed
expected_outcome: yield
setup:
  graph_builder: |
    # Alice is knee-deep in swamp when she tries to walk onto the dry path.
    # The swamp should tax her movement: the same step that would be cheap
    # on dry_land costs her double her usual energy here.
    kg.add_node("alice", node_type="agent", move_speed=10, stamina=20, position=[0, 0])
    kg.add_node(
        "swamp",
        node_type="entity",
        subtype="area",
        terrain_type="swamp",
        movement_cost_multiplier=2.0,
    )
    kg.add_node(
        "dry_land",
        node_type="entity",
        subtype="area",
        terrain_type="path",
        movement_cost_multiplier=1.0,
    )
    kg.add_edge("alice", "swamp", relation="located_in")
    kg.add_edge("swamp", "dry_land", relation="adjacent_to")
    kg.add_edge("dry_land", "swamp", relation="adjacent_to")
actions:
  - actor: alice
    intent: "slog out of the swamp onto the dry path"
    classified:
      verb: move
      target: dry_land
      direction: east
expected_observations:
  - actor: alice
    narrative_contains: ["swamp", "slow", "dry_land"]
    graph_assertions:
      - kind: has_edge
        src: alice
        dst: dry_land
        relation: located_in
      - kind: not_has_edge
        src: alice
        dst: swamp
        relation: located_in
      - kind: property_equals
        node: alice
        property: stamina
        value: 18
gaps:
  - layer: mechanic
    severity: address-now
    summary: "Movement seed mechanic does not read terrain_type or movement_cost_multiplier from the source/destination; all moves cost the same."
    proposed_fix: "Extend movement mechanic to look up movement_cost_multiplier on the actor's current and destination nodes, and deduct stamina accordingly."
  - layer: graph
    severity: defer
    summary: "Terrain is currently just a subtype string (terrain_type); a proper terrain ontology would let mechanics query terrain categories without hardcoding strings."
    proposed_fix: "Decide whether terrain categorisation belongs in the subtype hierarchy or in a dedicated terrain-properties node. Document in ARCHITECTURE.md."
  - layer: mechanic
    severity: defer
    summary: "Terrain may also affect line-of-sight, stealth, noise — not just movement."
    proposed_fix: "Generalise terrain effects: allow a mechanic to register interest in a terrain property (slow, loud, hides_sightlines) rather than coupling terrain to movement alone."
---

# UC-V05: Terrain effect

## Vignette

Alice is standing in a swamp. Every step is heavy; the muck closes over her
boots and she has to pull them free before she can put them down again. By
the time she reaches the dry path on the other side, she's winded from what
should have been an easy walk. The same distance on the path, she would
have covered without noticing. The swamp itself slowed her down.

## Why this matters

Terrain is the first mechanic that has to look at *where the actor is
standing* and *where they're going* to decide how an action resolves. The
current movement seed treats every edge as equivalent, which would render
every landscape interchangeable. This case forces the framework to
acknowledge that the graph's geometry alone isn't enough — some properties
of the terrain must become part of how mechanics execute.

## Related use cases

- UC-S06 (traversal-across-terrain — the spatial counterpart)
- UC-S01 (movement-through-doorway — the base movement case this modifies)
- UC-V06 (light-and-dark — another case where surroundings affect actions)
