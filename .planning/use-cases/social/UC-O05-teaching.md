---
id: UC-O05
category: social
title: "Teaching a skill"
status: reviewed
expected_outcome: pass
validator_exception: target_may_not_exist  # `lockpicking` is an unmodeled skill string; absence-as-node is the engine gap itself.
setup:
  graph_builder: |
    # Alice knows lockpicking; bob does not. They have an afternoon.
    kg.add_node("alice", node_type="agent", knows_skill=["lockpicking"])
    kg.add_node("bob", node_type="agent", knows_skill=[])
    kg.add_node("workshop", node_type="entity", subtype="room")
    kg.add_node("practice_lock", node_type="entity", subtype="lock")
    kg.add_edge("alice", "workshop", relation="located_in")
    kg.add_edge("bob", "workshop", relation="located_in")
    kg.add_edge("practice_lock", "workshop", relation="located_in")
actions:
  - actor: alice
    intent: "teach bob how to pick a lock"
    classified:
      verb: teach
      target: lockpicking
      indirect_object: bob
expected_observations:
  - actor: alice
    narrative_contains: ["teach", "bob", "lockpicking"]
    graph_assertions:
      - kind: property_equals
        node: alice
        property: knows_skill
        value: ["lockpicking"]
  - actor: bob
    narrative_contains: ["learn", "lockpicking"]
    graph_assertions:
      - kind: property_equals
        node: bob
        property: knows_skill
        value: ["lockpicking"]
gaps:
  - layer: mechanic
    severity: address-now
    summary: "No teach/learn mechanic; `knows_skill` is a plain list property and nothing copies entries from one agent to another under the right preconditions."
    proposed_fix: "Add a `teach` mechanic with precondition `skill in actor.knows_skill` and `co-located(actor, recipient)`, side effect appending to `recipient.knows_skill` if absent."
  - layer: engine
    severity: address-now
    summary: "Skill name (`lockpicking`) is a bare string, not a node — classifier cannot disambiguate between teaching a skill, teaching about a person, or teaching a song."
    proposed_fix: "Introduce a `skill` entity node (or a `skills` namespace of entities) so `teach` actions can name a target skill node rather than a free-form string."
  - layer: mechanic
    severity: defer
    summary: "All teaching is instantaneous; no proficiency levels, no time cost, no possibility of partial learning."
    proposed_fix: "Model skill as `{name: str, level: int}` records and let `teach` raise `level` by 1 per tick up to the teacher's level."
---

# UC-O05: Teaching a skill

## Vignette

Alice sets the practice lock on the workbench and taps the shaft with a
tension wrench. "Feel that? That's the pin binding." Bob bends over the
lock, listening to her voice and the tiny clicks under his fingers. An
hour later the lock drops open in his hand — not elegantly, but open.
He can do it now.

## Why this matters

Teaching is the benign twin of deception: one agent deliberately changes
another agent's state. Unlike a lie, teaching wants the change to stick
and to match ground truth. It's also our first scenario where the object
of the action isn't a physical entity — "lockpicking" is a concept. That
forces us to decide whether skills are strings on agents, first-class
nodes, or something richer. This use case anchors that decision early,
before we sprawl skill strings across dozens of other mechanics.

## Related use cases

- UC-O03 (give — same indirect-object grammar, physical variant)
- UC-O04 (deception — changes beliefs, not capabilities)
