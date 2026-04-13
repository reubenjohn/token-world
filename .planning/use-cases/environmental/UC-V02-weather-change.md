---
id: UC-V02
category: environmental
title: "Weather change"
status: reviewed
expected_outcome: blocked
setup:
  graph_builder: |
    # The world sits under clear skies. A lit torch burns in an open camp,
    # and a fabric tent stands nearby. When the world-level weather flips to
    # "rain", every outdoor entity should feel it: the torch's fire goes
    # out, and the fabric tent becomes wet.
    kg.add_node("world", node_type="entity", subtype="world", weather="clear", time_of_day="noon")
    kg.add_node("camp", node_type="entity", subtype="area", outdoor=True)
    kg.add_node(
        "torch",
        node_type="entity",
        subtype="torch",
        flammable=True,
        on_fire=True,
        temperature=150,
        outdoor=True,
    )
    kg.add_node(
        "fabric_tent",
        node_type="entity",
        subtype="tent",
        material="fabric",
        wet=False,
        outdoor=True,
    )
    kg.add_edge("camp", "world", relation="located_in")
    kg.add_edge("torch", "camp", relation="located_in")
    kg.add_edge("fabric_tent", "camp", relation="located_in")
actions:
  - actor: engine
    intent: "shift weather from clear to rain; propagate wetness and extinguish outdoor fires"
    classified:
      verb: set_weather
      target: world
      value: rain
expected_observations:
  - actor: engine
    narrative_contains: ["rain", "torch", "fabric_tent"]
    graph_assertions:
      - kind: property_equals
        node: world
        property: weather
        value: rain
      - kind: property_equals
        node: torch
        property: on_fire
        value: false
      - kind: property_equals
        node: fabric_tent
        property: wet
        value: true
gaps:
  - layer: engine
    severity: address-now
    summary: "No global-state tick hook: weather lives on a 'world' node but no mechanic framework primitive watches world-level property changes."
    proposed_fix: "Extend mechanic matcher vocabulary with a WorldPropertyMatcher or define a canonical 'world' node the engine dispatches from each tick (see SIM-10)."
  - layer: mechanic
    severity: address-now
    summary: "No weather-triggered mechanic exists; environmental_reaction seed only handles single-entity temperature changes, not cross-cutting weather effects."
    proposed_fix: "Author weather_reaction mechanic that enumerates outdoor entities and applies material-specific side effects (wet fabric, extinguished fires, muddied ground)."
  - layer: graph
    severity: defer
    summary: "'outdoor=True' is modelled per-entity; a location-based query (is_under_sky) would scale better for nested containment."
    proposed_fix: "Add sky-exposure derivation on top of containment edges, or let weather_reaction walk the containment chain until it finds an outdoor boundary."
---

# UC-V02: Weather change

## Vignette

The camp was peaceful a moment ago — torchlight steady, the tent taut and
dry. Then the sky darkened and rain began to sweep across the clearing. In
seconds the torch guttered and died as the first drops hit its flame; the
canvas of the tent grew dark and heavy as it soaked through. Nothing in the
camp moved on its own, but everything in the camp changed, because the
weather itself changed.

## Why this matters

Weather is a cross-cutting world state: it affects many entities at once,
and those effects depend on each entity's material and exposure. This case
stresses how the framework models *global* state that isn't attached to a
specific actor. It also exposes the mismatch between per-entity matchers
(the current norm) and world-level triggers (needed here) — a first-class
engine gap.

## Related use cases

- UC-V01 (fire spread — this case reverses it)
- UC-V04 (seasons — another global-state cascade)
- UC-V06 (light-and-dark — another world-level property)
