---
id: UC-E02
category: edge-case
title: "Concurrent actors contesting a resource"
status: reviewed
setup:
  graph_builder: |
    # Alice and bob both see the last apple on the table. Each intends to
    # grab it on the same tick. The graph holds a single apple; the
    # engine must decide who wins — or flag that it does not yet know how.
    kg.add_node("alice", node_type="agent", position=[0, 0], stamina=10)
    kg.add_node("bob", node_type="agent", position=[1, 0], stamina=10)
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_node("apple", node_type="entity", subtype="food", edible=True)
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("bob", "room_a", relation="located_in")
    kg.add_edge("apple", "room_a", relation="located_in")
actions:
  - actor: alice
    intent: "grab the apple off the table"
    classified:
      verb: take
      target: apple
  - actor: bob
    intent: "snatch the apple before alice can"
    classified:
      verb: take
      target: apple
expected_observations:
  - actor: alice
    narrative_contains: ["apple"]
    graph_assertions:
      - kind: has_node
        node: apple
  - actor: bob
    narrative_contains: ["apple"]
    graph_assertions:
      - kind: has_node
        node: apple
gaps:
  - layer: engine
    severity: address-now
    summary: "Engine has no documented turn-ordering policy when two agents' classified actions contest the same target on the same tick; behavior is undefined."
    proposed_fix: "Define a deterministic resolution rule for v1 (e.g., tick-order FIFO, or single-actor-per-tick as a hard constraint) and document it as an engine invariant; Phase 5 authoring plan should make this explicit."
  - layer: engine
    severity: address-now
    summary: "There is no pre-execution conflict-detection pass that notices two actions target the same exclusive entity; mechanics execute in isolation and may both succeed, double-taking the apple."
    proposed_fix: "Add a conflict-scan step between classification and mechanic execution that groups actions by (verb, exclusive_target) and resolves via the ordering policy above."
  - layer: mechanic
    severity: defer
    summary: "No seed mechanic for 'take' expresses that the target leaves the world (becomes unavailable) atomically; a naive implementation could duplicate state if two mechanics fire in parallel."
    proposed_fix: "Require take-family mechanics to assert the target is still `located_in` the actor's room as a precondition, so the second mechanic's check fails once the first mutation commits."
  - layer: graph
    severity: defer
    summary: "Graph API lacks a transactional / compare-and-swap primitive to protect shared-resource mutations against interleaving."
    proposed_fix: "Wrap per-tick mutations in a batch with precondition re-check, or expose a `get_and_set` conditional mutator on KnowledgeGraph."
---

# UC-E02: Concurrent actors contesting a resource

## Vignette

The apple sits alone on the table. Alice reaches for it from the left;
bob lunges from the right. Both of them intend, in the same breath, to
walk away with it. Only one apple exists. The engine has one tick to
decide whose hand closes around it — and to tell the other, coherently,
why their grasp closed on air.

## Why this matters

Token World's v1 is single-actor-per-tick by design, but the mechanic
framework and graph already support multi-agent worlds, and the
authoring corpus must include the scenario so planners cannot pretend it
is out of scope. Two simultaneous, contested takes expose whether the
engine has a defined ordering policy, whether mechanics guard against
double-spend, and whether the graph has transactional semantics. Today
none of these are explicit — this use case surfaces them all. The
apple-contest is deliberately mundane so the gap is about orchestration,
not about the mechanic.

## Related use cases

- UC-R02, UC-R03 (resource contention in the happy path)
- UC-O06 (social interaction between two actors)
