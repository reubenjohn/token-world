---
id: UC-E01
category: edge-case
title: "Action against nonexistent target"
status: reviewed
expected_outcome: blocked
validator_exception: target_may_not_exist
setup:
  graph_builder: |
    # Alice is alone in a plain room. The classified target for the
    # scenario's action deliberately does not exist as a node here: the
    # scenario tests the engine's behavior when target resolution fails.
    # Do NOT add the missing target to this setup — its absence is the
    # whole point of the test.
    kg.add_node("alice", node_type="agent", position=[0, 0], stamina=10)
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_edge("alice", "room_a", relation="located_in")
actions:
  - actor: alice
    intent: "attack the dragon with my bare hands"
    classified:
      verb: attack
      target: dragon
      utterance: "attack the dragon with my bare hands"
expected_observations:
  - actor: alice
    narrative_contains: ["no dragon", "nothing"]
    graph_assertions:
      - kind: not_has_property
        node: alice
        property: in_combat
      - kind: has_edge
        src: alice
        dst: room_a
        relation: located_in
      - kind: property_equals
        node: alice
        property: stamina
        value: 10
gaps:
  - layer: engine
    severity: address-now
    summary: "Action classifier does not defensively handle targets that fail graph lookup; no standard 'missing target' verdict exists."
    proposed_fix: "Add a target-resolution step in the classifier pipeline that returns a `no_such_target` verdict with the attempted identifier, so downstream mechanics are skipped and observation synthesis renders a grounded 'no X here' narrative."
  - layer: engine
    severity: address-now
    summary: "Observation synthesizer has no guardrail forcing narrative to remain grounded when the classified target is absent; a free-generation LLM may hallucinate a dragon into existence in the prose, violating SIM-05 grounding."
    proposed_fix: "When the engine emits a `no_such_target` verdict, feed the observation LLM a hard constraint template ('the target does not exist in the world') and assert in tests that narrative never introduces the missing entity as real."
  - layer: mechanic
    severity: defer
    summary: "No seed mechanic describes the failure mode of a missing target at the mechanic layer; engine handles it before any mechanic fires."
    proposed_fix: "Document in authoring guidelines that mechanics may assume their targets exist because the engine filters missing-target actions upstream."
---

# UC-E01: Action against nonexistent target

## Vignette

Alice stands alone in the empty room, balling her hands into fists. "I'll
show that dragon," she mutters, and swings — at nothing. There is no
dragon. There has never been a dragon. The air is undisturbed except by
her breathing.

## Why this matters

This is the canonical test of engine defensiveness against hallucination.
The classifier can and will emit targets that are not in the graph
(misheard, imagined, referring to the wrong universe). If the engine
forwards such an action to mechanics or — worse — lets the observation
LLM invent the dragon to justify the verb, SIM-05 grounding is violated
and the simulation becomes unreliable. The setup graph deliberately
contains no dragon; the engine must notice, refuse to execute, and
produce a grounded "nothing is there" observation without mutating the
graph. This is the baseline robustness case every other edge-case
scenario builds on.

## Related use cases

- UC-E04 (nonsense-input — complementary: no valid verb at all)
- UC-E03 (partial-knowledge — related: actor acts on false belief)
