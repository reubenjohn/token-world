---
id: UC-R01
category: resource
title: "Craft sword from materials"
status: reviewed
expected_outcome: blocked
setup:
  graph_builder: |
    # Alice stands at a forge with raw materials in hand.
    kg.add_node("alice", node_type="agent", hunger=30, inventory_cap=10)
    kg.add_node("forge", node_type="entity", subtype="workstation", tool_type="forge")
    kg.add_node("smithy", node_type="entity", subtype="room")
    kg.add_node("iron_ingot", node_type="entity", subtype="material", material="iron", mass=1.0)
    kg.add_node("wood_plank", node_type="entity", subtype="material", material="wood", mass=0.3)
    kg.add_edge("alice", "smithy", relation="located_in")
    kg.add_edge("forge", "smithy", relation="located_in")
    kg.add_edge("alice", "iron_ingot", relation="holds")
    kg.add_edge("alice", "wood_plank", relation="holds")
actions:
  - actor: alice
    intent: "use the forge to combine the iron ingot and the wood plank into a sword"
    classified:
      verb: craft
      target: forge
      inputs: [iron_ingot, wood_plank]
      output: sword
expected_observations:
  - actor: alice
    narrative_contains: ["forge", "sword", "iron"]
    graph_assertions:
      - kind: not_has_edge
        src: alice
        dst: iron_ingot
        relation: holds
      - kind: not_has_edge
        src: alice
        dst: wood_plank
        relation: holds
      - kind: has_property
        node: alice
        property: inventory_cap
gaps:
  - layer: mechanic
    severity: address-now
    summary: "No crafting mechanic exists; recipe-driven multi-input consumption is unsupported."
    proposed_fix: "Add a craft mechanic with a recipe registry keyed on (tool_type, input materials) producing a typed output node and removing inputs."
  - layer: engine
    severity: address-now
    summary: "Conservation is not checked: nothing prevents a crafted output whose mass exceeds sum of inputs."
    proposed_fix: "Engine-level pre/post hook compares total mass of affected subgraph; reject mutations that violate conservation without a declared sink."
  - layer: graph
    severity: defer
    summary: "No structured 'contains materials of' lineage from crafted item back to its inputs."
    proposed_fix: "Optional provenance edge (e.g. crafted_from) recorded by the craft mechanic for Phase 8 history queries."
---

# UC-R01: Craft sword from materials

## Vignette

Alice stands in the smithy beside a glowing forge, an iron ingot in one hand
and a wood plank in the other. She feeds both into the forge, works the
bellows, and after several tense minutes lifts a newly finished sword from the
anvil — heavier than the ingot alone, lighter than she expected, and clearly
made of the two things she put in.

## Why this matters

Crafting is the canonical conservation scenario: a mechanic must remove
multiple input nodes and produce one output node in a single atomic step, and
the engine must be able to check that nothing was invented out of thin air.
Without a recipe-aware mechanic the simulation has no way to express "combine
A and B into C", and without an engine-level conservation hook an LLM-
generated mechanic could silently duplicate mass. This case also exercises the
tool/workstation pattern (forge as prerequisite) that future mechanics —
alchemy, cooking, enchanting — will reuse.

## Related use cases

- UC-R02 (single-input consumption: eating food is the degenerate case of crafting)
- UC-R07 (conservation violation: what crafting looks like when the engine fails to enforce balance)
- UC-R05 (crafted artifacts degrade through use — the inverse of crafting)
