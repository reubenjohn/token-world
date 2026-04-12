---
id: UC-V07
category: environmental
title: "Contagion"
status: draft
setup:
  graph_builder: |
    # Alice has a cold. Bob shares her small, poorly ventilated office.
    # When Alice coughs, there's a meaningful chance Bob catches the same
    # infection. Symptoms — if they develop — should follow on subsequent
    # ticks.
    kg.add_node("office", node_type="entity", subtype="room", ventilated=False)
    kg.add_node(
        "alice",
        node_type="agent",
        infected=True,
        disease="common_cold",
        symptomatic=True,
    )
    kg.add_node(
        "bob",
        node_type="agent",
        infected=False,
        immune_system="average",
    )
    kg.add_edge("alice", "office", relation="located_in")
    kg.add_edge("bob", "office", relation="located_in")
actions:
  - actor: alice
    intent: "cough into the room without covering her mouth"
    classified:
      verb: cough
      target: office
      indirect_object: bob
expected_observations:
  - actor: alice
    narrative_contains: ["cough", "office", "bob"]
    graph_assertions:
      - kind: property_equals
        node: alice
        property: infected
        value: true
      - kind: property_equals
        node: bob
        property: infected
        value: true
      - kind: property_equals
        node: bob
        property: disease
        value: common_cold
gaps:
  - layer: mechanic
    severity: address-now
    summary: "No contagion mechanic exists; transmission is proximity + probability dependent and no seed mechanic handles either."
    proposed_fix: "Author contagion_mechanic that enumerates co-located agents and rolls transmission against the carrier's symptomatic state and the target's immune_system."
  - layer: graph
    severity: address-now
    summary: "Non-deterministic mutations are not first-class: the engine currently assumes mechanic.apply is pure, which conflicts with probabilistic transmission."
    proposed_fix: "Introduce a seeded-RNG primitive on MechanicContext so probabilistic mechanics are reproducible under replay; document determinism contract."
  - layer: engine
    severity: defer
    summary: "Symptom progression over multiple ticks (fever → cough → recovery) needs the same passive-tick loop as UC-V03 decay."
    proposed_fix: "Reuse the SIM-09 passive-tick mechanism once landed; contagion mechanic writes scheduled-state updates that fire on subsequent ticks."
---

# UC-V07: Contagion

## Vignette

Alice has been sniffling all morning. She and Bob share the same small,
stuffy office; there's no real ventilation and the window hasn't opened in
weeks. When Alice coughs — openly, without covering her mouth — she sprays
a fine mist that hangs in the still air. A day later Bob wakes up with the
same tickle in his throat that Alice had a week ago. The cold has jumped.

## Why this matters

Contagion is the first *probabilistic, proximity-driven* scenario in the
library, and it exposes two deep holes at once. First, there is no
contagion-style mechanic anywhere in the seed set. Second, and more
fundamental, the mechanic framework assumes `apply()` is deterministic —
probabilistic mutations break that assumption and demand a principled RNG
story before they can ship. The case also ties to passive-time progression
(UC-V03) once symptoms start cascading.

## Related use cases

- UC-V01 (fire spread — the other proximity-triggered propagation)
- UC-V03 (decay — symptom progression shares its passive-time need)
- UC-O* (social — disease transmission patterns mirror rumor spread)
