---
id: UC-E04
category: edge-case
title: "Nonsense input"
status: draft
setup:
  graph_builder: |
    # A banal room with alice in it. Nothing special. The scenario is
    # entirely about what happens when alice utters gibberish.
    kg.add_node("alice", node_type="agent", position=[0, 0], stamina=10)
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_edge("alice", "room_a", relation="located_in")
actions:
  - actor: alice
    intent: "gragh flibble xyzzy rutabaga"
    classified:
      verb: none
      utterance: "gragh flibble xyzzy rutabaga"
expected_observations:
  - actor: alice
    narrative_contains: ["alice", "nothing"]
    graph_assertions:
      - kind: has_edge
        src: alice
        dst: room_a
        relation: located_in
      - kind: property_equals
        node: alice
        property: stamina
        value: 10
      - kind: not_has_property
        node: alice
        property: in_combat
gaps:
  - layer: engine
    severity: address-now
    summary: "Classifier has no documented 'no viable action' verdict; under-constrained LLM classifiers will fabricate a plausible-looking verb/target rather than admitting the input is meaningless."
    proposed_fix: "Add an explicit `no_viable_action` classification outcome with a confidence threshold; below threshold, the engine skips mechanic dispatch and routes straight to a 'nothing happens' observation."
  - layer: engine
    severity: address-now
    summary: "Mechanic generation is triggered on unknown verbs; a nonsense utterance could prompt the generator to synthesize a `gragh` mechanic, polluting the registry with garbage."
    proposed_fix: "Gate mechanic generation behind a classifier-confidence check plus a manual-review queue for novel verbs; never auto-generate from `no_viable_action` inputs."
  - layer: engine
    severity: address-now
    summary: "Observation synthesis has no template for 'input was incoherent' — the free-generation prompt may try to rationalize the gibberish and invent entities/events to explain it."
    proposed_fix: "Add a dedicated incoherent-input observation template that produces a grounded, minimal narrative ('alice mutters something unintelligible; nothing happens') and assert narrative does not introduce new entities."
  - layer: mechanic
    severity: out-of-scope
    summary: "No mechanic should ever fire on nonsense input; there is no mechanic-layer fix here by design."
    proposed_fix: "Document in authoring guidelines that mechanics must never be written to handle 'unknown verb' as a trigger."
---

# UC-E04: Nonsense input

## Vignette

Alice stands in the small room, draws a breath, and says, clearly:
"Gragh flibble xyzzy rutabaga." The words land and disappear. She
blinks. Nothing around her has changed. The room notices nothing
because there is nothing to notice.

## Why this matters

LLMs are eager to cooperate. Handed a string of gibberish and asked
"what verb is this?", an unconstrained classifier will happily pick a
verb. Handed "produce a response to alice's action," an unconstrained
observation LLM will write a paragraph explaining what the gibberish
*might* mean. Both behaviors violate the simulator's grounding contract:
the world should respond with nothing because nothing happened. This
scenario is the stress-test for defensive classification, for guarded
mechanic generation, and for the observation-layer guardrail that keeps
the narrative from inventing meaning. Getting this right prevents an
entire class of hallucinations downstream.

## Related use cases

- UC-E01 (nonexistent target — complementary: verb valid, target absent)
- UC-E05 (circular chain — complementary: engine-layer safety)
