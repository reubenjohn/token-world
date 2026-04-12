---
id: UC-S04
category: spatial
title: "Area-of-effect explosion"
status: reviewed
setup:
  graph_builder: |
    # Five entities scattered in a 10x10 field. Explosion at [5,5] radius 3.
    kg.add_node("mage", node_type="agent", position=[0, 0])
    kg.add_node("field", node_type="entity", subtype="room", bbox=[0, 0, 10, 10])
    kg.add_edge("mage", "field", relation="located_in")
    # Inside radius 3 of [5,5]:
    kg.add_node("barrel_1", node_type="entity", subtype="barrel", position=[5, 5], hp=10)
    kg.add_node("barrel_2", node_type="entity", subtype="barrel", position=[6, 7], hp=10)
    kg.add_node("goblin_1", node_type="entity", subtype="goblin", position=[4, 4], hp=8)
    # Outside radius 3:
    kg.add_node("barrel_3", node_type="entity", subtype="barrel", position=[1, 1], hp=10)
    kg.add_node("goblin_2", node_type="entity", subtype="goblin", position=[9, 9], hp=8)
    for e in ("barrel_1", "barrel_2", "goblin_1", "barrel_3", "goblin_2"):
        kg.add_edge(e, "field", relation="located_in")
actions:
  - actor: mage
    intent: "cast fireball at the center of the field"
    classified:
      verb: aoe
      target: barrel_1
      center: [5, 5]
      radius: 3
      damage: 5
expected_observations:
  - actor: mage
    narrative_contains: ["fireball", "explodes", "damage"]
    graph_assertions:
      - kind: property_equals
        node: barrel_1
        property: damaged
        value: true
      - kind: property_equals
        node: goblin_1
        property: damaged
        value: true
      - kind: not_has_property
        node: barrel_3
        property: damaged
      - kind: not_has_property
        node: goblin_2
        property: damaged
gaps:
  - layer: graph
    severity: address-now
    summary: "No `within(bbox_or_circle)` query; without it, an AoE mechanic must iterate every positioned node to pick victims."
    proposed_fix: "Expose `ctx.spatial.within(shape)` on GRAPH-06, supporting both axis-aligned bbox and centered-radius shapes."
  - layer: mechanic
    severity: address-now
    summary: "No AoE mechanic; the seeds handle single-target verbs only. Damage-conservation (sum of hp reductions equals computed damage) is not checked anywhere."
    proposed_fix: "Add an `area_of_effect` mechanic that fans out a damage predicate over `ctx.spatial.within(...)` results and emits one mutation per affected entity."
  - layer: engine
    severity: defer
    summary: "Fan-out mutations from a single action are not batched or transactional; partial failure is silent."
    proposed_fix: "Consider a tick-scoped transaction wrapper so AoE mutations either all commit or all roll back."
---

# UC-S04: Area-of-effect explosion

## Vignette

The mage raises a hand over the field. A fireball streaks to the center,
[5,5], and detonates with a roar. Two barrels at the blast site and a
goblin near the epicenter flinch as the shockwave hits them; a third
barrel and a second goblin, both farther away at the field's corners, are
untouched. Smoke drifts; splinters fall.

The engine must partition the five entities correctly — three damaged,
two spared — using nothing but their `position` and the blast's center
and radius.

## Why this matters

AoE is the canonical fan-out pattern: one action, many side effects, all
keyed on geometry. It stresses three layers: the graph needs an efficient
`within` query, the mechanic needs to iterate results and emit one
mutation per target, and the engine needs to keep that fan-out coherent
inside a single tick. A naïve implementation that scans every positioned
node will work for this UC and collapse in production.

## Related use cases

- UC-S03 (nearest-object-query — sibling GRAPH-06 query)
- UC-R04 (resource cases where effects fan out over area)
