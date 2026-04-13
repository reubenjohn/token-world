---
id: UC-V04
category: environmental
title: "Seasons"
status: reviewed
expected_outcome: blocked
setup:
  graph_builder: |
    # Summer ends; autumn arrives. Deciduous trees should lose their
    # leaves as the season flips. The world carries a calendar; an oak
    # tree in the forest carries leaves it does not yet know it is about
    # to drop.
    kg.add_node(
        "world",
        node_type="entity",
        subtype="world",
        season="summer",
        day_of_year=240,
    )
    kg.add_node("forest", node_type="entity", subtype="area")
    kg.add_node(
        "oak_tree",
        node_type="entity",
        subtype="tree",
        deciduous=True,
        has_leaves=True,
        leaves_falling=False,
    )
    kg.add_edge("forest", "world", relation="located_in")
    kg.add_edge("oak_tree", "forest", relation="located_in")
actions:
  - actor: engine
    intent: "advance the calendar so that season transitions from summer to autumn"
    classified:
      # Verb aligned with the weather_reaction mechanic id so the Phase-4
      # harness's D-38 stub-probe routes UC-V04 via GAP-ENG09 (the actual
      # blocking framework gap: no WorldPropertyMatcher yet). When Phase 5
      # lands the matcher primitive AND a generalised world_state_reaction
      # family, the classifier maps the narrative intent back to
      # advance_season automatically.
      verb: weather_reaction
      target: world
      value: autumn
expected_observations:
  - actor: engine
    narrative_contains: ["autumn", "oak_tree", "leaves"]
    graph_assertions:
      - kind: property_equals
        node: world
        property: season
        value: autumn
      - kind: property_equals
        node: oak_tree
        property: leaves_falling
        value: true
      - kind: property_equals
        node: oak_tree
        property: has_leaves
        value: false
gaps:
  - layer: engine
    severity: address-now
    summary: "Calendar/time-scale modelling is not formalised; a season change must be expressible as more than an arbitrary property flip to stay coherent across ticks and epochs."
    proposed_fix: "Define day_of_year → season derivation in the engine or as a scheduled mechanic; tie season transitions to the tick→batch→epoch hierarchy."
  - layer: mechanic
    severity: defer
    summary: "Seasons are a special case of weather (slower, periodic); authoring a dedicated seasons mechanic may duplicate work."
    proposed_fix: "Generalise weather_reaction to a scheduled world_state_reaction mechanic family; parameterise by the world property being tracked (weather vs season vs time_of_day)."
  - layer: graph
    severity: defer
    summary: "'deciduous=True' is a bespoke property; a plant ontology would let seasonal mechanics generalise across species without per-subtype code."
    proposed_fix: "Decide whether ontology belongs in the graph (subtype hierarchy) or in the mechanic (branching on properties). Document the decision."
---

# UC-V04: Seasons

## Vignette

On the last warm day of the year, the oak in the forest looks no different
than it did all summer. But when the calendar turns and autumn begins, the
leaves along its branches start to yellow, then redden, then fall. By the
end of the first week of autumn the branches are bare. It is a slow,
world-wide change that plays out on every deciduous tree at once.

## Why this matters

Seasons are a *long-horizon, periodic, global* cascade. They stress the
engine's notion of time at a larger scale than per-tick mechanics: a season
spans thousands of ticks, yet the transition itself must fire mechanics
reliably. This case is the test of whether the framework can reason about
calendars, not just steps, and whether season-level mechanics can reuse
the same authoring patterns as per-tick ones.

## Related use cases

- UC-V02 (weather change — same pattern at a shorter timescale)
- UC-V03 (decay — another time-driven transformation)
- UC-V06 (light-and-dark — day/night is the shortest-timescale cousin)
