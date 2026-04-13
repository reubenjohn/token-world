---
id: UC-R05
category: resource
title: "Degradation over time"
status: reviewed
expected_outcome: blocked
# Phase-4 status (recorded 04-10):
#
# A degrade seed mechanic SHIPS in 04-10 (MECH17). It is the use-on-tool
# form: actor holds tool -> apply decrements durability by usage_cost
# (default 1) -> at <= 0 the node is removed (holds edge drops with it).
#
# UC-R05 stays `blocked` for two compounding reasons, BOTH of which
# would have to be addressed before the manifest can flip:
#
#   1. Routing (GAP-ENG02): the manifest's classified shape is
#      `verb=strike, target=dummy, instrument=sword`. The Phase-4
#      harness routes by `verb -> mechanic.id` and uses
#      `target = classified.target or classified.indirect_object` --
#      it has no `instrument` slot. Routing strike->degrade with the
#      sword as target requires Phase 5's classifier and a third
#      MechanicContext field for the instrument.
#
#   2. Threshold-flag semantics: the third expected_observation
#      asserts `property_equals(sword, durability, 0)` AND
#      `property_equals(sword, broken, true)` on a still-existing
#      sword node. The 04-10 degrade contract removes the node at
#      durability <= 0 (per PLAN.md), so neither assertion can hold
#      after the third swing -- the sword would be gone. Honouring
#      this UC's assertion semantics needs a `wear + threshold`
#      mechanic that sets `broken=true` at zero and removes the node
#      only on a separate `discard`/`break` action. That refinement
#      is a Phase-5+ concern (see UC-R05 mechanic-gap proposed_fix).
#
# When Phase 5 lands (a) the classifier with `instrument` routing
# AND (b) the wear+threshold refinement (or the manifest is rewritten
# to assert remove-on-zero), this UC can flip to `pass`.
setup:
  graph_builder: |
    # Alice holds a worn sword near a straw training dummy.
    kg.add_node("alice", node_type="agent")
    kg.add_node("training_yard", node_type="entity", subtype="room")
    kg.add_node("sword", node_type="entity", subtype="weapon", durability=3, broken=False)
    kg.add_node("dummy", node_type="entity", subtype="target")
    kg.add_edge("alice", "training_yard", relation="located_in")
    kg.add_edge("dummy", "training_yard", relation="located_in")
    kg.add_edge("alice", "sword", relation="holds")
actions:
  - actor: alice
    intent: "swing the sword at the dummy"
    classified:
      verb: strike
      target: dummy
      instrument: sword
  - actor: alice
    intent: "swing the sword at the dummy again"
    classified:
      verb: strike
      target: dummy
      instrument: sword
  - actor: alice
    intent: "swing the sword at the dummy one more time"
    classified:
      verb: strike
      target: dummy
      instrument: sword
expected_observations:
  - actor: alice
    narrative_contains: ["sword", "swing"]
    graph_assertions:
      - kind: property_equals
        node: sword
        property: durability
        value: 2
  - actor: alice
    narrative_contains: ["sword", "notch"]
    graph_assertions:
      - kind: property_equals
        node: sword
        property: durability
        value: 1
  - actor: alice
    narrative_contains: ["sword", "break"]
    graph_assertions:
      - kind: property_equals
        node: sword
        property: durability
        value: 0
      - kind: property_equals
        node: sword
        property: broken
        value: true
gaps:
  - layer: mechanic
    severity: address-now
    summary: "No degradation mechanic: strike does not decrement instrument durability or trigger threshold behaviour at 0."
    proposed_fix: "Seed a generic wear(instrument, amount=1) hook that strike and similar verbs call, plus a threshold rule that sets broken=true when durability reaches 0."
  - layer: engine
    severity: defer
    summary: "Tick-driven passive degradation (rust, rot) independent of actor use is out of scope until SIM-09 attention/tick infrastructure lands."
    proposed_fix: "Phase 7: bind passive degradation to the SIM-09 tick scheduler so perishables advance without an actor's explicit action."
  - layer: graph
    severity: defer
    summary: "No standard property vocabulary for condition tracking (durability vs integrity vs charges vs uses)."
    proposed_fix: "Document a convention for condition properties so mechanics across domains use the same names; revisit when enough examples exist."
---

# UC-R05: Degradation over time

## Vignette

Alice squares up against the straw dummy and swings. The sword bites deep,
and by the second strike the edge is obviously rougher than it was. On the
third swing the blade finally snaps off near the guard — she stares at the
broken hilt in her hand, no longer holding a usable weapon at all.

## Why this matters

Degradation is where use and consequence meet: every time an actor does
something, the thing they did it with should notice. This exercises three
framework questions at once — can a mechanic reach through from the verb
(strike) to a non-target instrument (sword) and mutate it? Can the framework
express a threshold rule (durability <= 0 → broken)? And can a single plan
sequence three identical actions and observe three different graph states?
The defer'd passive-time gap also stakes a claim for SIM-09 attention/tick
infrastructure so rot and rust can be expressed later without retrofitting.

## Related use cases

- UC-R02 (consumption is degradation in a single step — apple has durability=1)
- UC-R01 (crafting an item defines what "new" looks like; this is what used looks like)
- UC-V04 and environmental examples (environmental decay uses the same threshold pattern)
