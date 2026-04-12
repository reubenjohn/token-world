---
id: UC-O08
category: social
title: "Speech broadcast"
status: draft
setup:
  graph_builder: |
    # Alice shouts in room_a. Bob is with her; charlie is in the next room behind a wall.
    kg.add_node("alice", node_type="agent", position=[0, 0])
    kg.add_node("bob", node_type="agent", position=[5, 0])
    kg.add_node("charlie", node_type="agent", position=[30, 0])
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-10, -10, 10, 10])
    kg.add_node("room_b", node_type="entity", subtype="room", bbox=[20, -10, 40, 10])
    kg.add_node("wall", node_type="entity", subtype="wall", blocks_sound=True)
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("bob", "room_a", relation="located_in")
    kg.add_edge("charlie", "room_b", relation="located_in")
    kg.add_edge("wall", "room_a", relation="borders")
    kg.add_edge("wall", "room_b", relation="borders")
actions:
  - actor: alice
    intent: "shout 'help!'"
    classified:
      verb: shout
      utterance: "help!"
      volume: loud
expected_observations:
  - actor: alice
    narrative_contains: ["shout", "help"]
    graph_assertions:
      - kind: has_node
        node: alice
  - actor: bob
    narrative_contains: ["alice", "shout", "help"]
    graph_assertions:
      - kind: has_edge
        src: bob
        dst: room_a
        relation: located_in
  - actor: charlie
    narrative_contains: []
    graph_assertions:
      - kind: not_has_edge
        src: charlie
        dst: room_a
        relation: located_in
gaps:
  - layer: graph
    severity: address-now
    summary: "No earshot/range query; the graph has positions but no helper to enumerate agents within a radius of a point, let alone one that accounts for sound-blocking entities."
    proposed_fix: "Add `kg.agents_within(origin, radius, occluders=...)` as a graph API primitive, composable with `blocks_sound=True` entities for occlusion."
  - layer: mechanic
    severity: address-now
    summary: "No speech-propagation mechanic; utterances are either heard by nobody (today) or everybody (if we naively broadcast)."
    proposed_fix: "Ship a `speak` mechanic that takes a volume parameter, queries `agents_within(speaker, radius_for(volume), occluders=walls)`, and emits narrative observations only for those listeners."
  - layer: engine
    severity: defer
    summary: "Listeners are modeled as passive; there is no hook for bob's own tick to react to hearing alice."
    proposed_fix: "When a listener receives speech, enqueue a pending perception that their next tick can respond to via normal intent classification."
---

# UC-O08: Speech broadcast

## Vignette

Alice cups her hands and shouts, "Help!" — loud enough to startle the
sparrows on the windowsill. Bob, three paces away, snaps his head up;
the word reaches him clearly. Beyond the wall, Charlie keeps reading,
undisturbed. The stone swallows the sound before it ever reaches him.

## Why this matters

Speech is the first action whose audience is determined by spatial
geometry rather than explicit targeting. The engine has to answer
"who hears this?" by querying positions and occluders, not by following
an `indirect_object` field. That requires a spatial earshot primitive
on the graph, a broadcast-shaped mechanic, and a story about how
passive listeners get woken up by perception events. This use case is
where the social and spatial categories first have to compose.

## Related use cases

- UC-O06 (cooperation — many agents coordinating, different shape)
- UC-O07 (observation — information flow without active broadcast)
