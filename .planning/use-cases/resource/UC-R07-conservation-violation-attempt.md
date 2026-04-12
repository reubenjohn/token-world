---
id: UC-R07
category: resource
title: "Conservation violation attempt"
status: draft
setup:
  graph_builder: |
    # Alice is penniless; an LLM-generated mechanic is about to try to conjure money.
    kg.add_node("alice", node_type="agent", coin=0)
    kg.add_node("void_chamber", node_type="entity", subtype="room")
    kg.add_edge("alice", "void_chamber", relation="located_in")
    # Flag describing the provenance of the mechanic under test.
    kg.add_node("wish_for_riches_mechanic", node_type="entity", subtype="mechanic",
                source="llm_generated", reviewed=False)
actions:
  - actor: alice
    intent: "wish for one thousand coin to appear in my purse from nowhere"
    classified:
      verb: invoke_mechanic
      target: wish_for_riches_mechanic
      effect:
        property_delta:
          node: alice
          property: coin
          delta: 1000
          source_node: null
expected_observations:
  - actor: alice
    narrative_contains: ["cannot", "nothing", "conservation"]
    graph_assertions:
      - kind: property_equals
        node: alice
        property: coin
        value: 0
      - kind: has_node
        node: wish_for_riches_mechanic
      - kind: not_has_property
        node: alice
        property: coin_source_override
gaps:
  - layer: engine
    severity: address-now
    summary: "No SIM-08 conservation enforcement: mechanics can currently add to a conserved property without citing a source, so LLM-generated code can silently create value from nothing."
    proposed_fix: "SIM-08 hook — every mutation that increments a property listed in the conserved-property registry (coin, mass, energy, nutrition) must cite a matching decrement on another node, or a sink entity, or be flagged as a violation and rolled back."
  - layer: mechanic
    severity: address-now
    summary: "No framework-level review gate: a mechanic with source='llm_generated' and reviewed=false runs as if it were trusted first-party code."
    proposed_fix: "Gate mechanic execution behind a reviewed=true flag; require the mechanic registry to set reviewed=true only after a static-analysis pass that checks for unbalanced property deltas. Refuses to run unreviewed mechanics that touch conserved properties."
  - layer: engine
    severity: address-now
    summary: "Violations should be observable, not silent: the engine needs a standard failure narrative so actors learn the world has rules."
    proposed_fix: "Reuse the UC-R04 (ok=False, narrative=...) contract so the conservation violation surfaces to the actor as a grounded observation rather than a missing effect."
  - layer: engine
    severity: defer
    summary: "Conserved-property registry itself is not yet defined — every scenario guesses."
    proposed_fix: "Ship a small YAML registry of conserved properties (coin, mass, nutrition, energy) as part of SIM-08; let domain plans add to it."
---

# UC-R07: Conservation violation attempt

## Vignette

Alice closes her eyes in the void chamber and wills a thousand coin into her
empty purse. A freshly-generated mechanic, still warm from the LLM, tries
obligingly to honour the request — it calls `kg.set("alice", "coin", 1000)`
with no corresponding sink. The engine intercepts the mutation, refuses to
commit it, and tells Alice plainly that the world does not work that way;
her purse is as empty as it was a moment ago.

## Why this matters

This is the acid test for the **SIM-08 conservation law** requirement. If
LLM-generated mechanics can mint value with no source, the simulation's
ground-truth contract is cosmetic — every downstream guarantee (fair trade,
scarcity, meaningful crafting) collapses. Catching this case at the engine
level is the point: we explicitly want a mechanic that tries to cheat, so
we can assert the framework stops it. This case is the first-class test
partner for SIM-08 implementation in Phase 5; closing the `address-now` gaps
here is what turns SIM-08 from a requirement bullet into a defensible
guarantee, and the review-gate gap directly informs how the mechanic
registry will grade LLM-generated code before executing it.

## Related use cases

- UC-R01, UC-R02, UC-R03 (legitimate conservation-respecting interactions that SIM-08 must still allow)
- UC-R04 (refusal contract this case reuses for the violation narrative)
- UC-E05 and edge-case adversarial LLM behaviour (sibling scenarios for mechanic review gating)
