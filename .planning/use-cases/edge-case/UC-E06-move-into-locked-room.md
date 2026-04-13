---
id: UC-E06
category: edge-case
title: "Move into a locked room"
status: reviewed
expected_outcome: yield
setup:
  graph_builder: |
    # Alice stands in room_a. A door entity sits between room_a and
    # room_b, locked=true. The graph has a `connects` edge from room_a
    # to the door and from the door to room_b so the movement seed can
    # traverse via the door — which, because it is locked, should block
    # the move entirely.
    kg.add_node("alice", node_type="agent", position=[0, 0], stamina=10)
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_node("room_b", node_type="entity", subtype="room", bbox=[5, -5, 15, 5])
    kg.add_node("door_1", node_type="entity", subtype="door", locked=True, direction="east")
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("room_a", "door_1", relation="connects")
    kg.add_edge("door_1", "room_b", relation="connects")
actions:
  - actor: alice
    intent: "walk east into the next room"
    classified:
      verb: move
      direction: east
      target: room_b
expected_observations:
  - actor: alice
    narrative_contains: ["door", "locked"]
    graph_assertions:
      - kind: has_edge
        src: alice
        dst: room_a
        relation: located_in
      - kind: not_has_edge
        src: alice
        dst: room_b
        relation: located_in
      - kind: property_equals
        node: door_1
        property: locked
        value: true
      - kind: property_equals
        node: alice
        property: stamina
        value: 10
gaps:
  - layer: mechanic
    severity: address-now
    summary: "The movement seed mechanic traverses `connects` edges without inspecting intermediate blocking entities (doors, barriers, gates); a locked door on the path is silently ignored and alice would teleport through."
    proposed_fix: "Extend the movement seed's precondition to require all traversed entities along the path have `locked != true` (and, more generally, do not carry a `blocks_traversal` property); add a failure branch that emits a 'the way is blocked by <entity>' observation."
  - layer: mechanic
    severity: address-now
    summary: "There is no seed mechanic for interacting with a door (unlock, open, knock); the scenario surfaces the door concept but the mechanic corpus cannot act on it yet."
    proposed_fix: "Add a minimal `try_door` seed mechanic that reports the door state and, when alice has a matching key, flips `locked=false`; documented in the seeds README."
  - layer: graph
    severity: defer
    summary: "Door state is modeled as a property on a door node threaded into a `connects` path; an equally valid model puts `locked` on the edge between rooms. No convention exists, so authors may diverge."
    proposed_fix: "Pick a canonical representation (door-as-entity is preferred because it can carry key/keyhole/state properties) and document it in `docs/design/graph-conventions.md`."
  - layer: engine
    severity: defer
    summary: "Narrative grounding for 'your action did nothing because of a blocking entity' is a recurring pattern (locked doors, closed shutters, impassable terrain); without a shared template, each mechanic will re-invent the wording."
    proposed_fix: "Add an engine helper that composes 'blocked by X' narratives from a mechanic-supplied reason code and the blocking node's properties."
---

# UC-E06: Move into a locked room

## Vignette

Alice walks east, expecting the open doorway she remembers. Instead she
meets a heavy oak door, iron-banded, with a keyhole at chest height. She
pushes; the door does not move. She steps back and looks at it. It is
locked. She is still in the same room.

## Why this matters

Movement is the most frequently-invoked seed mechanic, and it is the
simplest case where the graph's path must be respected *together with*
the state of the entities on that path. A movement mechanic that only
checks edge existence is structurally wrong: any future door, gate,
shutter, or collapsed tunnel will be ignored. This scenario grounds the
seed-mechanic gap (movement must inspect traversed entities) and the
authoring-convention gap (where does `locked` live — node or edge?) in a
single concrete vignette that Phase 4/5 plans can regress against. It
also seeds the vocabulary for "blocked by X" observations that other
edge-cases (UC-E03 locked chest, future barriers) will reuse.

## Related use cases

- UC-S02 (basic movement — happy path this scenario breaks)
- UC-E03 (locked chest — other blocked-interaction case)
