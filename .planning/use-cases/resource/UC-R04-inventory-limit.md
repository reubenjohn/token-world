---
id: UC-R04
category: resource
title: "Inventory limit"
status: reviewed
expected_outcome: blocked
setup:
  graph_builder: |
    # Alice's inventory is already full: 10 items held, cap 10.
    kg.add_node("alice", node_type="agent", inventory_cap=10)
    kg.add_node("storeroom", node_type="entity", subtype="room")
    kg.add_edge("alice", "storeroom", relation="located_in")
    for i in range(10):
        item_id = f"item_{i:02d}"
        kg.add_node(item_id, node_type="entity", subtype="junk")
        kg.add_edge("alice", item_id, relation="holds")
    # An eleventh item on the floor, tempting.
    kg.add_node("item_10", node_type="entity", subtype="junk")
    kg.add_edge("item_10", "storeroom", relation="located_in")
actions:
  - actor: alice
    intent: "pick up item_10 from the floor"
    classified:
      verb: pickup
      target: item_10
expected_observations:
  - actor: alice
    narrative_contains: ["inventory", "full", "cannot"]
    graph_assertions:
      - kind: not_has_edge
        src: alice
        dst: item_10
        relation: holds
      - kind: has_edge
        src: item_10
        dst: storeroom
        relation: located_in
      - kind: property_equals
        node: alice
        property: inventory_cap
        value: 10
gaps:
  - layer: mechanic
    severity: address-now
    summary: "Pickup mechanic does not check inventory_cap precondition before adding a holds edge."
    proposed_fix: "Seed pickup mechanic must count outgoing holds edges on the actor and refuse when count >= inventory_cap."
  - layer: engine
    severity: address-now
    summary: "No standard way for a mechanic to refuse an action and produce a user-facing failure narrative — current contract assumes every action mutates state."
    proposed_fix: "Engine must accept a (ok=False, narrative=...) result from a mechanic, leave the graph unchanged, and still return an observation to the actor."
  - layer: graph
    severity: defer
    summary: "Inventory is implicit (count of holds edges) rather than a first-class container; later features like bags-inside-bags will need a container node type."
    proposed_fix: "Phase 8: introduce container subtype with explicit capacity property and contained_by relation for nested storage."
---

# UC-R04: Inventory limit

## Vignette

Alice crouches over an abandoned coin pouch on the storeroom floor, but when
she reaches for it her pack bulges visibly — every strap is already pulled
tight over the ten things she's already lugging. She straightens up
empty-handed; the pouch stays where it is. Nothing in the room has changed
except that she has acknowledged, a little sourly, that she is out of space.

## Why this matters

A realistic simulation must be able to say no. This case pressure-tests
whether the framework can represent a refused action: the mechanic declines,
the graph is unchanged, but the actor still receives a grounded observation
explaining why. That engine contract — "ok=False + narrative" — is a
prerequisite for every bounded-resource scenario the world will later grow
into (carry weight, encumbrance, spell slots, stamina gating). It also forces
the question of whether inventory is a counted edge relation or a proper
container, a design choice that ripples into UC-R01 crafting and Phase 8
storage mechanics.

## Related use cases

- UC-R01 (successful pickup of crafted output — the happy path)
- UC-R07 (another refusal case, this time driven by conservation rather than capacity)
- UC-E03 and edge-case refusals (generic refusal pattern shared by many domains)
