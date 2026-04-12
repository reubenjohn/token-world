---
id: UC-O02
category: social
title: "Persuasion check"
status: draft
setup:
  graph_builder: |
    # Alice wants bob to unlock a door that bob (reluctantly) guards.
    kg.add_node("alice", node_type="agent")
    kg.add_node("bob", node_type="agent", disposition="wary")
    kg.add_node("door", node_type="entity", subtype="door", locked=True)
    kg.add_node("corridor", node_type="entity", subtype="room")
    kg.add_edge("alice", "corridor", relation="located_in")
    kg.add_edge("bob", "corridor", relation="located_in")
    kg.add_edge("door", "corridor", relation="located_in")
actions:
  - actor: alice
    intent: "try to convince bob to unlock the door so I can pass"
    classified:
      verb: persuade
      target: bob
      about: door
      desired_outcome: unlock
      utterance: "please, it's urgent — I need to pass"
expected_observations:
  - actor: alice
    narrative_contains: ["bob", "door", "convince"]
    graph_assertions:
      - kind: has_node
        node: door
      - kind: has_node
        node: bob
  - actor: bob
    narrative_contains: ["alice", "unlock"]
    graph_assertions:
      - kind: has_property
        node: door
        property: locked
gaps:
  - layer: engine
    severity: address-now
    summary: "Persuasion is a probabilistic social action; the engine has no model for outcome resolution beyond deterministic mechanics."
    proposed_fix: "Add an `llm_adjudicated` mechanic category that lets a seed LLM call decide success/failure based on disposition, charisma, argument quality, then deterministically apply the chosen side effect."
  - layer: mechanic
    severity: address-now
    summary: "No persuade/convince mechanic; agents have no mutable disposition property that other agents can influence."
    proposed_fix: "Ship a `persuade` mechanic that reads target `disposition`, an (optional) `charisma` stat on the speaker, and writes either a side-effect mutation (unlock) or a disposition shift (target becomes less wary)."
  - layer: graph
    severity: defer
    summary: "Reputation/relationship edges (alice→bob, trust=0.3) are not modeled."
    proposed_fix: "When reputation matters, add `trust` edges between agent pairs and let persuasion read them as a modifier."
---

# UC-O02: Persuasion check

## Vignette

Alice meets bob's eyes across the corridor. "Please. It's urgent — I need
to pass." Bob's hand stays on the key at his belt. He's wary, and she can
tell; whether he opens the door depends as much on how he hears her as on
what she says. He hesitates, weighing her words.

## Why this matters

Persuasion is the first scenario where the outcome isn't purely a function
of graph state — it's a judgment call. The engine today only runs
deterministic mechanics, which means any social action with an uncertain
outcome is inexpressible. We need a category of LLM-adjudicated mechanics
that take graph context as input, make a bounded decision, and commit the
result through the normal mutation API. This use case anchors that design
decision.

## Related use cases

- UC-O04 (deception — adversarial variant of social influence)
- UC-O05 (teaching — cooperative variant, also agent-to-agent)
