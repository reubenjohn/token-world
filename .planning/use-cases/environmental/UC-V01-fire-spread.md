---
id: UC-V01
category: environmental
title: "Fire spread"
status: draft
setup:
  graph_builder: |
    # A lit torch sits on a wooden table. The torch is on fire and hot; the
    # table is flammable but still cool. When the environmental_reaction seed
    # sees the torch's temperature cross 100, fire should propagate to the
    # adjacent wooden table.
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_node(
        "wooden_table",
        node_type="entity",
        subtype="furniture",
        flammable=True,
        temperature=20,
        on_fire=False,
    )
    kg.add_node(
        "torch",
        node_type="entity",
        subtype="torch",
        flammable=True,
        temperature=150,
        on_fire=True,
    )
    kg.add_edge("wooden_table", "room_a", relation="located_in")
    kg.add_edge("torch", "wooden_table", relation="resting_on")
    kg.add_edge("torch", "room_a", relation="located_in")
actions:
  - actor: engine
    intent: "advance one tick to let heat propagate from the torch to adjacent flammable entities"
    classified:
      verb: tick_advance
      target: wooden_table
      utterance: "environmental pass"
expected_observations:
  - actor: engine
    narrative_contains: ["wooden_table", "fire", "spread"]
    graph_assertions:
      - kind: property_equals
        node: wooden_table
        property: on_fire
        value: true
      - kind: property_equals
        node: wooden_table
        property: temperature
        value: 150
      - kind: has_edge
        src: torch
        dst: wooden_table
        relation: resting_on
gaps:
  - layer: mechanic
    severity: defer
    summary: "environmental_reaction seed covers single-hop spread but not chain depth limits or extinguish-over-time."
    proposed_fix: "Layer a burn-duration mechanic on top of the seed that decrements temperature each tick and clears on_fire at 0."
  - layer: engine
    severity: address-now
    summary: "No cycle detector when fire spread triggers further spreads on the same tick; chain execution may reprocess the same node."
    proposed_fix: "Engine should track a per-tick visited set and cap chain depth (see SIM-08 cascade control)."
---

# UC-V01: Fire spread

## Vignette

The torch has been burning all night on the wooden table, and by morning the
table itself is smoking. The wood beneath the torch's base has been baking
for hours; a thin curl of smoke rises, then a lick of flame catches on the
grain. Within a breath the tabletop is burning too. To anyone watching, it
looks like the fire has leapt from one object to the next — but under the
hood it is the environmental_reaction mechanic firing as soon as the table's
temperature crosses the ignition threshold.

## Why this matters

This is the canonical chain-execution scenario and the one case the
`environmental_reaction` seed mechanic was explicitly written to handle. It
proves the mechanic framework can propagate side effects to a neighbor in a
single tick. It also pressure-tests the engine's cascade controls: if the
newly-ignited table then has flammable neighbors of its own, the chain must
advance without looping forever or collapsing the tick budget.

## Related use cases

- UC-V02 (weather change can extinguish the same fire)
- UC-V07 (contagion — another proximity-triggered propagation)
- UC-V04 (seasons — another time-driven cascade)
