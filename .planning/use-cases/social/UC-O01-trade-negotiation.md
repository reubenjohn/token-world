---
id: UC-O01
category: social
title: "Trade negotiation"
status: reviewed
expected_outcome: pass
setup:
  graph_builder: |
    # Single-tick atomic trade (Phase 4 scope). Both parties arrive
    # with their offers already pre-negotiated via pending_trade
    # mirrors — the multi-turn offer/accept protocol (GAP-ENG01) is
    # Phase 5's responsibility.
    kg.add_node(
        "alice",
        node_type="agent",
        pending_trade={
            "offer_item": "sword",
            "demand_item": "coin_pouch",
            "counterparty": "bob",
        },
    )
    kg.add_node(
        "bob",
        node_type="agent",
        pending_trade={
            "offer_item": "coin_pouch",
            "demand_item": "sword",
            "counterparty": "alice",
        },
    )
    kg.add_node("sword", node_type="entity", subtype="weapon", value=10)
    kg.add_node("coin_pouch", node_type="entity", subtype="currency", amount=10)
    kg.add_node("tavern", node_type="entity", subtype="room")
    kg.add_edge("alice", "sword", relation="holds")
    kg.add_edge("bob", "coin_pouch", relation="holds")
    kg.add_edge("alice", "tavern", relation="located_in")
    kg.add_edge("bob", "tavern", relation="located_in")
actions:
  - actor: alice
    intent: "trade sword for bob's coin pouch (offers already staged on both sides)"
    classified:
      verb: trade
      target: bob
expected_observations:
  - actor: alice
    narrative_contains: ["trade", "bob", "sword", "coin"]
    graph_assertions:
      - kind: has_edge
        src: bob
        dst: sword
        relation: holds
      - kind: not_has_edge
        src: alice
        dst: sword
        relation: holds
      - kind: has_edge
        src: alice
        dst: coin_pouch
        relation: holds
      - kind: not_has_edge
        src: bob
        dst: coin_pouch
        relation: holds
gaps:
  - layer: mechanic
    severity: address-now
    summary: "No trade/exchange mechanic — transactional swap of held items and fungible coin is not expressible today."
    proposed_fix: "Add a `trade` mechanic with an atomic single-tick commit over two parties' mirrored pending_trade offers. (Shipped 04-08 MECH07.)"
  - layer: engine
    severity: defer
    summary: "Classifier has no notion of a multi-turn offer/accept protocol; Phase 4 ships only the single-tick atomic form."
    proposed_fix: "Introduce a pending-offer state on the offering agent and let the classifier resolve `accept` intents against the most recent open offer directed at the speaker. GAP-ENG01; deferred to Phase 5."
  - layer: graph
    severity: defer
    summary: "Fungible currency is modelled as a coin_pouch entity rather than arithmetic on a scalar property."
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
to hold a working economy needs an atomic exchange primitive. Phase 4 ships
the **single-tick atomic swap** via `trade` (MECH07): both parties arrive
with mirrored `pending_trade` offers in the graph, and the mechanic commits
the swap in one tick. The **multi-turn offer/accept protocol** (one party
proposes at tick N, the other accepts at tick N+1) is a classifier concern
tracked as `GAP-ENG01` and deferred to Phase 5. This UC covers only the
atomic half.

## Related use cases

- UC-O03 (give-sword-to-bob — one-sided transfer, no reciprocation)
- UC-R01..UC-R07 (resource handling — once trade works, these compose on top)
