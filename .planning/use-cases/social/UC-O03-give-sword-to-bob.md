---
id: UC-O03
category: social
title: "Give sword to bob"
status: reviewed
expected_outcome: blocked
setup:
  graph_builder: |
    # Alice is holding a sword; bob stands next to her in a clearing.
    kg.add_node("alice", node_type="agent")
    kg.add_node("bob", node_type="agent")
    kg.add_node("sword", node_type="entity", subtype="weapon")
    kg.add_node("clearing", node_type="entity", subtype="room")
    kg.add_edge("sword", "alice", relation="held_by")
    kg.add_edge("alice", "clearing", relation="located_in")
    kg.add_edge("bob", "clearing", relation="located_in")
actions:
  - actor: alice
    intent: "give the sword to bob"
    classified:
      verb: give
      target: sword
      indirect_object: bob
expected_observations:
  - actor: alice
    narrative_contains: ["give", "sword", "bob"]
    graph_assertions:
      - kind: has_edge
        src: sword
        dst: bob
        relation: held_by
      - kind: not_has_edge
        src: sword
        dst: alice
        relation: held_by
  - actor: bob
    narrative_contains: ["alice", "sword"]
    graph_assertions:
      - kind: has_edge
        src: sword
        dst: bob
        relation: held_by
gaps:
  - layer: engine
    severity: address-now
    summary: "ActionClassification has no `indirect_object` field; grammar with both a direct object (sword) and recipient (bob) cannot be represented structurally."
    proposed_fix: "Extend the classified action schema with an optional `indirect_object` key and teach the classifier prompt to populate it for ditransitive verbs (give/offer/show/tell/teach)."
  - layer: mechanic
    severity: address-now
    summary: "No transfer/give mechanic — even a one-sided hand-off of a held item is not expressible."
    proposed_fix: "Add a `give` mechanic: precondition `held_by(target, actor)` and `located_in(actor, room) == located_in(recipient, room)`; side effect rewrites `held_by(target, recipient)`."
  - layer: engine
    severity: defer
    summary: "Consent is implicit — bob cannot refuse the sword today."
    proposed_fix: "When consent matters, require the recipient's next tick to accept/reject before the transfer commits."
---

# UC-O03: Give sword to bob

## Vignette

Alice hefts the sword and turns to bob. "Here. You'll need this more than
I will." She extends it, hilt-first, and Bob takes the grip. The weight
settles into his hand; Alice's palms are suddenly empty.

## Why this matters

This is the simplest possible multi-object social action, and yet today's
classifier schema cannot represent it: `give` has two arguments (what,
to whom), but our action shape has only `target`. Every ditransitive verb
— give, show, tell, teach, offer — has the same problem. Fixing the
classifier schema here unblocks most of the social category, so this use
case is deliberately minimal: the graph shape is trivial, but the engine
gap it surfaces is load-bearing.

## Related use cases

- UC-O01 (trade — give + receive in both directions)
- UC-O04 (deception — tell X to Y, same grammar)
- UC-O05 (teaching — teach X to Y, same grammar)
