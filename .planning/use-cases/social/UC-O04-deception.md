---
id: UC-O04
category: social
title: "Deception"
status: draft
setup:
  graph_builder: |
    # A chest full of coin sits in the vault; alice lies to bob about it.
    kg.add_node("alice", node_type="agent")
    kg.add_node("bob", node_type="agent", beliefs={})
    kg.add_node("chest", node_type="entity", subtype="container", contents=["coin:100"])
    kg.add_node("vault", node_type="entity", subtype="room")
    kg.add_edge("alice", "vault", relation="located_in")
    kg.add_edge("bob", "vault", relation="located_in")
    kg.add_edge("chest", "vault", relation="located_in")
actions:
  - actor: alice
    intent: "tell bob that the chest is empty"
    classified:
      verb: tell
      target: bob
      indirect_object: chest
      utterance: "the chest is empty"
      claim:
        node: chest
        property: contents
        value: []
expected_observations:
  - actor: alice
    narrative_contains: ["tell", "bob", "chest", "empty"]
    graph_assertions:
      - kind: has_node
        node: chest
      - kind: property_equals
        node: chest
        property: contents
        value: ["coin:100"]
  - actor: bob
    narrative_contains: ["alice", "says", "empty"]
    graph_assertions:
      - kind: has_property
        node: bob
        property: beliefs
gaps:
  - layer: mechanic
    severity: address-now
    summary: "No belief-tracking mechanic; agents' per-agent mental models diverge from ground truth but nothing writes that divergence into the graph."
    proposed_fix: "Add a `tell` mechanic that writes into `beliefs[listener][claim_subject] = claim_value`, independent of whether the claim matches ground truth."
  - layer: graph
    severity: address-now
    summary: "Ground truth and per-agent beliefs share the same node properties, so a lie overwrites reality instead of diverging from it."
    proposed_fix: "Model beliefs as a `beliefs` dict keyed by other node IDs (or as belief-edges), so bob.beliefs[chest]={contents: []} coexists with chest.contents=[coin:100]."
  - layer: engine
    severity: defer
    summary: "Observation layer does not filter by speaker credibility — bob has no way to weigh alice's claim against his own prior knowledge."
    proposed_fix: "When trust edges exist, the engine can decide whether a `tell` updates beliefs at all, or how strongly; out of scope until UC-O02 lands."
---

# UC-O04: Deception

## Vignette

Alice glances at the chest, then at bob, and keeps her face perfectly
still. "It's empty," she says. "Someone got here before us." Bob hasn't
lifted the lid. Behind her, a hundred coin sit undisturbed in the dark —
but as far as bob now knows, there's nothing worth taking in this room.

## Why this matters

Deception requires the graph to represent two incompatible states at once:
the ground truth (chest has 100 coin) and bob's belief (chest is empty).
Today we have exactly one layer of state, so a lie would either have to
mutate the real chest (breaking ground truth) or have no effect at all
(breaking the scenario). This use case forces the design decision for
per-agent belief modeling, which then unlocks mystery, intrigue, and
information-asymmetric economies.

## Related use cases

- UC-O02 (persuasion — influence without asserting false facts)
- UC-O07 (observation — what an agent sees feeds what they believe)
