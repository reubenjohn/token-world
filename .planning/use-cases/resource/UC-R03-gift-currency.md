---
id: UC-R03
category: resource
title: "Gift currency"
status: reviewed
setup:
  graph_builder: |
    # Alice has 10 coin; bob is broke. Both are in the tavern.
    kg.add_node("alice", node_type="agent", coin=10)
    kg.add_node("bob", node_type="agent", coin=0)
    kg.add_node("tavern", node_type="entity", subtype="room")
    kg.add_edge("alice", "tavern", relation="located_in")
    kg.add_edge("bob", "tavern", relation="located_in")
actions:
  - actor: alice
    intent: "give bob 5 coin as a token of goodwill"
    classified:
      verb: give
      target: bob
      indirect_object: coin
      amount: 5
expected_observations:
  - actor: alice
    narrative_contains: ["bob", "coin", "5"]
    graph_assertions:
      - kind: property_equals
        node: alice
        property: coin
        value: 5
      - kind: property_equals
        node: bob
        property: coin
        value: 5
gaps:
  - layer: mechanic
    severity: address-now
    summary: "No transfer mechanic: no primitive for moving a scalar property from one node to another while preserving total."
    proposed_fix: "Ship a transfer(sender, receiver, property, amount) mechanic that decrements sender and increments receiver in a single transaction; refuse if sender would go negative."
  - layer: engine
    severity: address-now
    summary: "Classifier must handle an indirect object (bob) distinct from the direct object (coin); v0 classifier only supports a single target."
    proposed_fix: "Extend the classifier schema to include indirect_object and amount, and update the engine dispatcher to route (verb='give', indirect_object=...) correctly."
  - layer: engine
    severity: address-now
    summary: "No conservation assertion on paired mutations: sender -5 and receiver +5 must net to zero."
    proposed_fix: "Engine conservation hook (SIM-08 precursor) validates that the sum of deltas on any conserved property is zero within a single action."
---

# UC-R03: Gift currency

## Vignette

Alice fishes five copper coins out of her purse and slides them across the
tavern table to Bob. Bob picks them up with a nod, the weight of them obvious
from the clink. Alice's purse is lighter by the same amount, and nobody feels
cheated — the coins did not multiply and they did not vanish, they simply
moved.

## Why this matters

Currency transfer is the smallest case that exercises three mechanics-
framework gaps at once: the classifier needs an indirect object slot, the
mechanic library needs a generic transfer primitive, and the engine needs to
recognise that a paired decrement/increment on a conserved scalar is a valid
move while an unpaired one is not. Whatever shape the solution takes will
generalise to lending, trading, tipping, and every "give X to Y" interaction
the world can invent.

## Related use cases

- UC-R06 (fungible currency: what happens when the amount is physically made of discrete tokens)
- UC-R07 (conservation violation: what goes wrong when the paired delta isn't checked)
- UC-O04 and social equivalents (reputational transfers share the structural pattern)
