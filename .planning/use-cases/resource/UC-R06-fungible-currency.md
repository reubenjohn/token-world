---
id: UC-R06
category: resource
title: "Fungible currency"
status: reviewed
expected_outcome: yield
setup:
  graph_builder: |
    # Alice carries a mix of coins in three denominations; the shopkeeper is waiting.
    kg.add_node("alice", node_type="agent")
    kg.add_node("shop", node_type="entity", subtype="room")
    kg.add_node("shopkeeper", node_type="agent", coin_received=0)
    kg.add_edge("alice", "shop", relation="located_in")
    kg.add_edge("shopkeeper", "shop", relation="located_in")
    # One 5-coin, two 2-coins, two 1-coins — total 11.
    kg.add_node("coin_5", node_type="entity", subtype="coin", denomination=5)
    kg.add_node("coin_2a", node_type="entity", subtype="coin", denomination=2)
    kg.add_node("coin_2b", node_type="entity", subtype="coin", denomination=2)
    kg.add_node("coin_1a", node_type="entity", subtype="coin", denomination=1)
    kg.add_node("coin_1b", node_type="entity", subtype="coin", denomination=1)
    for c in ("coin_5", "coin_2a", "coin_2b", "coin_1a", "coin_1b"):
        kg.add_edge("alice", c, relation="holds")
actions:
  - actor: alice
    intent: "pay the shopkeeper 7 coin for the goods"
    classified:
      verb: pay
      target: shopkeeper
      indirect_object: coin
      amount: 7
expected_observations:
  - actor: alice
    narrative_contains: ["shopkeeper", "7"]
    graph_assertions:
      - kind: property_equals
        node: shopkeeper
        property: coin_received
        value: 7
      - kind: has_node
        node: alice
gaps:
  - layer: mechanic
    severity: address-now
    summary: "No fungibility mechanic: framework cannot pick 'any subset of held coin entities whose denominations sum to amount' and transfer them."
    proposed_fix: "Ship a fungible_pay mechanic that solves the subset-sum over held entities of a given subtype/denomination and transfers the chosen entities; falls back to refusal if no valid subset exists."
  - layer: graph
    severity: defer
    summary: "Representation tension: amount-as-property (alice.coin=N) is ergonomic but loses identity; amount-as-entities (one coin per node) scales badly but supports individuation (counterfeit coin, marked coin)."
    proposed_fix: "Document both representations; let mechanic authors pick per domain; provide a helper that converts between them when the mechanic needs to switch."
  - layer: mechanic
    severity: defer
    summary: "No making-change mechanic when exact amount is impossible (e.g. pay 4 with only 5s and 2s)."
    proposed_fix: "Phase 7+: extend fungible_pay to take a max-overpay tolerance and emit change-owed state; out of scope for v1."
---

# UC-R06: Fungible currency

## Vignette

Alice spills her coins onto the shop counter: one five-piece, two twos, two
ones. She pushes seven coin worth across — the five and two of the ones,
though she could as easily have paid the five, the two, or the three two-
pieces combined with an extra one — and the shopkeeper sweeps her payment
into a drawer without caring which combination made it up.

## Why this matters

Real currency is fungible: "pay 7" must succeed whenever the actor holds any
combination summing to 7, regardless of which discrete coins make it up. If
the framework models coins as unique entities the mechanic must solve subset-
sum; if it models coin as a scalar property the mechanic is trivial but loses
the ability to talk about individual coins (the counterfeit, the marked one,
the one that belonged to grandma). Surfacing this tension now — before
Phase 5 commits — lets authors pick consciously, and the fungible_pay
mechanic sets the pattern every quantity-plus-identity resource (arrows,
rations, ingredients) will follow.

## Related use cases

- UC-R03 (gift-currency: the scalar-property shape of the same interaction)
- UC-R01 (crafting with multiple indistinguishable material nodes reuses this logic)
- UC-R04 (refusal pattern applies when no subset sums to the requested amount)
