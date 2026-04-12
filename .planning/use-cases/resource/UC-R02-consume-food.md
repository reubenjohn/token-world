---
id: UC-R02
category: resource
title: "Consume food"
status: reviewed
setup:
  graph_builder: |
    # Alice is hungry and holding an apple.
    kg.add_node("alice", node_type="agent", hunger=80)
    kg.add_node("kitchen", node_type="entity", subtype="room")
    kg.add_node("apple", node_type="entity", subtype="food", nutrition=25)
    kg.add_edge("alice", "kitchen", relation="located_in")
    kg.add_edge("alice", "apple", relation="holds")
actions:
  - actor: alice
    intent: "eat the apple to take the edge off my hunger"
    classified:
      verb: consume
      target: apple
expected_observations:
  - actor: alice
    narrative_contains: ["apple", "hunger"]
    graph_assertions:
      - kind: not_has_edge
        src: alice
        dst: apple
        relation: holds
      - kind: property_equals
        node: alice
        property: hunger
        value: 55
gaps:
  - layer: mechanic
    severity: address-now
    summary: "No consume mechanic: can't combine remove_node (apple) with property delta (hunger -= nutrition) atomically."
    proposed_fix: "Ship a generic consume mechanic parametrized by (target_subtype=food, property=hunger, delta_from=nutrition) so every edible uses one mechanic."
  - layer: mechanic
    severity: defer
    summary: "No notion of partial consumption (half-eaten apple) or stacked portions."
    proposed_fix: "Phase 7: add portion/serving property so food can be consumed in discrete bites before being removed."
---

# UC-R02: Consume food

## Vignette

Alice's stomach has been growling for hours. She pulls the apple from her
pack, bites down, and keeps going until only a core is left — which she
tosses into the compost bin. The gnawing in her belly quiets by a noticeable
notch, though she's still nowhere near satisfied.

## Why this matters

This is the simplest valid conservation scenario: one input is destroyed, one
scalar on the actor goes down. It is the benchmark "does the mechanic
framework support a composite mutation in one tick?" case. If the engine
can't express `remove_node(apple) + set(alice.hunger, hunger - 25)` atomically
then every food, potion, or reagent interaction breaks. Consume is also the
pattern every other "resource is destroyed for an effect" mechanic will be
specialized from — lamps burning oil, potions curing wounds, logs feeding a
fire.

## Related use cases

- UC-R01 (crafting is consume with >1 input and a product)
- UC-R05 (degradation consumes one unit of durability per use, not the whole object)
- UC-R06 (paying 7 coin is consume with a quantity parameter)
