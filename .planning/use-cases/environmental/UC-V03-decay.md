---
id: UC-V03
category: environmental
title: "Decay"
status: draft
setup:
  graph_builder: |
    # A perfectly good apple is set on a shelf at tick 0 with a 100-tick
    # shelf life. Nobody touches it. By the time the world has ticked 100
    # times, the apple should have rotted on its own.
    kg.add_node("world", node_type="entity", subtype="world", current_tick=0)
    kg.add_node("pantry", node_type="entity", subtype="room")
    kg.add_node(
        "apple",
        node_type="entity",
        subtype="food",
        freshness="fresh",
        rotten=False,
        placed_at_tick=0,
        decay_period=100,
    )
    kg.add_edge("apple", "pantry", relation="located_in")
    kg.add_edge("pantry", "world", relation="located_in")
actions:
  - actor: engine
    intent: "advance 100 ticks with no agent intervention; apple should decay on its own"
    classified:
      verb: tick_advance
      target: world
      amount: 100
expected_observations:
  - actor: engine
    narrative_contains: ["apple", "rotten", "spoil"]
    graph_assertions:
      - kind: property_equals
        node: apple
        property: rotten
        value: true
      - kind: property_equals
        node: apple
        property: freshness
        value: rotten
      - kind: property_equals
        node: world
        property: current_tick
        value: 100
gaps:
  - layer: mechanic
    severity: address-now
    summary: "No mechanic fires in the absence of an agent action; passive-time decay has no trigger today."
    proposed_fix: "Introduce a passive-tick mechanic matcher (watches current_tick changes on 'world') so decay_mechanic can fire each tick without an agent action. Tie to SIM-09 (Phase 7 passive-tick handling)."
  - layer: engine
    severity: address-now
    summary: "Engine loop only invokes mechanics in response to actions; no tick-boundary sweep exists."
    proposed_fix: "Add a tick-end sweep that invokes all mechanics whose matcher subscribes to current_tick (SIM-09). Until then, passive scenarios cannot be expressed."
  - layer: graph
    severity: defer
    summary: "Apple transformation is modelled as a property flip (rotten=true), not a node-swap (apple→rotten_apple). Either is valid; pick one for consistency."
    proposed_fix: "Adopt a single convention in the mechanic framework doc: prefer in-place property transformation unless the identity of the entity genuinely changes."
---

# UC-V03: Decay

## Vignette

The apple was fresh when it was set on the pantry shelf, and nobody came to
eat it. Day after day the world turned, and the apple sat there. After a
hundred tick-days its skin had darkened, the flesh beneath had softened,
and it was unmistakably rotten — not because any agent did anything to it,
but because time itself acted on it.

## Why this matters

Decay is the archetypal *passive-time* scenario: no actor, no action, just
time. The current engine only fires mechanics in response to agent actions,
so this case cannot pass until the passive-tick path (SIM-09, Phase 7) is
implemented. It is exactly the kind of gap Wave 4 synthesis is meant to
surface — a whole class of real-world mechanics (hunger, thirst,
recharging, sleep-debt, decay) is currently unreachable.

## Related use cases

- UC-V04 (seasons — another long-horizon passive-time cascade)
- UC-R* (resource scarcity scenarios that need passive depletion)
- UC-V07 (contagion — also benefits from passive tick progression)
