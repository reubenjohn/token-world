---
id: UC-E03
category: edge-case
title: "Partial knowledge — acting on what the actor does not know"
status: reviewed
expected_outcome: pass
setup:
  graph_builder: |
    # Alice is in a study with a locked chest. The chest is locked in the
    # world (ground truth), but alice has never examined it, so she has
    # no belief about its locked state. She acts on the assumption it
    # will open. The engine must honor ground truth while tracking
    # alice's belief state separately.
    kg.add_node("alice", node_type="agent", position=[0, 0], beliefs={})
    kg.add_node("study", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_node("chest", node_type="entity", subtype="container", locked=True, contents=["scroll"])
    kg.add_edge("alice", "study", relation="located_in")
    kg.add_edge("chest", "study", relation="located_in")
actions:
  - actor: alice
    intent: "open the chest to see what's inside"
    classified:
      # Phase 4 stages the failed-open -> belief-update reaction directly
      # via the voluntary belief_update mechanic (MECH25). Phase 5's
      # GAP-ENG19 passive-tick sweep will fire this reactively from a
      # blocked `open` action; until then the manifest names the mechanic
      # explicitly so alice still learns "the chest is locked" under
      # today's harness.
      verb: belief_update
      target: chest
expected_observations:
  - actor: alice
    narrative_contains: ["chest", "locked"]
    graph_assertions:
      - kind: property_equals
        node: chest
        property: locked
        value: true
      - kind: has_property
        node: alice
        property: beliefs
      - kind: not_has_edge
        src: alice
        dst: chest
        relation: opened
gaps:
  - layer: graph
    severity: address-now
    summary: "No first-class representation of per-agent belief vs. ground-truth state; the setup uses a generic `beliefs` dict property, but there is no convention, query helper, or assertion kind for comparing belief with world state."
    proposed_fix: "Introduce a canonical belief-node pattern (e.g., nodes connected to the agent via `believes_about` edges carrying a `property`/`value` pair) plus `has_belief` / `belief_equals` query helpers. Document in the graph conventions."
  - layer: mechanic
    severity: address-now
    summary: "No seed mechanic updates an actor's belief state after an attempted interaction reveals world truth; alice should leave the interaction knowing the chest is locked, but no mechanic writes that belief."
    proposed_fix: "Add a belief-update side effect pattern: whenever a precondition fails visibly (e.g., `locked=true` blocks `open`), the failing mechanic records the observed property into the actor's belief store."
  - layer: engine
    severity: address-now
    summary: "Observation synthesis does not filter narrative by the acting agent's knowledge — it currently has access to the full graph, so it could leak 'the chest is locked' before alice's attempt even resolves."
    proposed_fix: "Introduce a `visible_to(actor)` projection of the graph that scopes observation-LLM context to nodes/properties the actor has directly perceived, with post-attempt reveals added after the mechanic runs."
  - layer: engine
    severity: defer
    summary: "No mechanism for propagating belief updates between agents who witness each other's failures (bob sees alice fail to open the chest → bob learns chest is locked)."
    proposed_fix: "Add an observer belief-propagation hook on action resolution; deferred until multi-agent is in scope (v2+)."
---

# UC-E03: Partial knowledge

## Vignette

The chest crouches in the corner of the study, dark walnut catching the
afternoon light. Alice kneels and lifts the lid — or tries to. The clasp
holds fast. A small iron lock she had not noticed before stares back at
her. Now she knows.

## Why this matters

A simulation where agents have perfect knowledge of world state is a
god's-eye simulation, not a lived one. Token World's observation LLM
currently sees the whole graph, which means it can — and will —
telegraph hidden information into narrative. This scenario forces the
framework to separate *what is true* from *what alice knows is true* and
to update the latter only when mechanics resolve. The gap spans all
three layers: graph conventions for belief, mechanic patterns for
belief-update side effects, and engine projections for observation
filtering. This is the partial-information complement to UC-O04 (which
looks at the same gap from the social/deception angle).

## Related use cases

- UC-O04 (deception — other side of the belief/knowledge gap)
- UC-E01 (nonexistent target — related grounding concern in observation)
- UC-S05 (perception / line-of-sight — scoped graph visibility)
