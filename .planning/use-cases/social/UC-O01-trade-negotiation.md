---
id: UC-O01
category: social
title: "Trade negotiation"
status: reviewed
expected_outcome: blocked
setup:
  graph_builder: |
    # Alice has a sword; bob has 10 coin. They meet in a tavern.
    kg.add_node("alice", node_type="agent", inventory=[])
    kg.add_node("bob", node_type="agent", inventory=["coin:10"])
    kg.add_node("sword", node_type="entity", subtype="weapon", value=10)
    kg.add_node("tavern", node_type="entity", subtype="room")
    kg.add_edge("sword", "alice", relation="held_by")
    kg.add_edge("alice", "tavern", relation="located_in")
    kg.add_edge("bob", "tavern", relation="located_in")
actions:
  - actor: alice
    intent: "offer the sword to bob for 10 coin"
    classified:
      verb: offer
      target: sword
      indirect_object: bob
      amount: 10
      currency: coin
  - actor: bob
    intent: "accept alice's offer"
    classified:
      verb: accept
      target: alice
      offer_ref: sword
expected_observations:
  - actor: alice
    narrative_contains: ["offer", "bob", "sword", "10 coin"]
    graph_assertions:
      - kind: has_node
        node: sword
      - kind: has_node
        node: bob
  - actor: bob
    narrative_contains: ["accept", "sword", "coin"]
    graph_assertions:
      - kind: has_edge
        src: sword
        dst: bob
        relation: held_by
      - kind: not_has_edge
        src: sword
        dst: alice
        relation: held_by
      - kind: property_equals
        node: alice
        property: inventory
        value: ["coin:10"]
      - kind: property_equals
        node: bob
        property: inventory
        value: []
gaps:
  - layer: mechanic
    severity: address-now
    summary: "No trade/exchange mechanic — transactional swap of held items and fungible coin is not expressible today."
    proposed_fix: "Add a `trade` mechanic with an atomic two-sided commit: precondition both parties agree + items present, side effect swaps `held_by` edges and decrements/increments inventory counts."
  - layer: engine
    severity: address-now
    summary: "Classifier has no notion of a multi-turn offer/accept protocol; each turn is currently interpreted in isolation."
    proposed_fix: "Introduce a pending-offer state on the offering agent and let the classifier resolve `accept` intents against the most recent open offer directed at the speaker."
  - layer: graph
    severity: defer
    summary: "Fungible currency is encoded as `inventory=[\"coin:10\"]` string tags, which does not support arithmetic queries."
    proposed_fix: "Promote fungible resources to first-class nodes with a `quantity` property, so trade mechanics can compose with other resource-handling mechanics."
---

# UC-O01: Trade negotiation

## Vignette

Alice slides the sword across the tavern table, hilt-first. "Ten coin and
it's yours." Bob weighs the blade in his hand, checks the edge, and nods —
he counts out ten coin from his pouch. By the time the door closes behind
her, Alice's belt is lighter and her purse is full.

## Why this matters

Trade is the canonical multi-actor transaction. Any simulation that aspires
to hold a working economy needs an atomic exchange primitive, and the engine
has to interpret a multi-turn offer/accept protocol as a single logical
action. Today we have neither: there is no trade mechanic, and the
classifier treats each utterance as an isolated intent. This use case
forces us to confront transactional commit semantics before the economy
category (UC-R0x) compounds the problem.

## Related use cases

- UC-O03 (give-sword-to-bob — one-sided transfer, no reciprocation)
- UC-R01..UC-R07 (resource handling — once trade works, these compose on top)
