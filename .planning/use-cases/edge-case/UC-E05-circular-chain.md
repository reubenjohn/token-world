---
id: UC-E05
category: edge-case
title: "Circular mechanic chain"
status: reviewed
expected_outcome: blocked
setup:
  graph_builder: |
    # Alice stands near two opposing runes. Triggering rune_a causes
    # mechanic "echo_a" to mutate rune_b, whose reactive mechanic
    # "echo_b" in turn mutates rune_a — a cycle. The runes are seeded
    # with a `charge` counter so the chain has observable state, and a
    # starting chain_events list so we can count iterations before the
    # engine breaks out.
    kg.add_node("alice", node_type="agent", position=[0, 0])
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_node("rune_a", node_type="entity", subtype="rune", charge=0, paired_with="rune_b")
    kg.add_node("rune_b", node_type="entity", subtype="rune", charge=0, paired_with="rune_a")
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("rune_a", "room_a", relation="located_in")
    kg.add_edge("rune_b", "room_a", relation="located_in")
actions:
  - actor: alice
    intent: "touch rune_a to activate it"
    classified:
      verb: activate
      target: rune_a
expected_observations:
  - actor: alice
    narrative_contains: ["rune", "chain"]
    graph_assertions:
      - kind: has_node
        node: rune_a
      - kind: has_node
        node: rune_b
      - kind: has_property
        node: rune_a
        property: charge
      - kind: has_property
        node: rune_b
        property: charge
gaps:
  - layer: engine
    severity: address-now
    summary: "Cycle detection in ChainEngine uses a (mechanic_id, target) seen-set plus a hard `max_depth=10` bound, but there is no surfaced trace event or observation-layer explanation when a chain is truncated for cycle reasons; silent truncation hides real engine behavior from agents and from debugging."
    proposed_fix: "Emit a `chain_truncated` trace event with `reason in {cycle, max_depth}` and surface it in the observation narrative ('the cascade falls into a loop and sputters out') so both the actor and debugging tooling see why the chain halted."
  - layer: engine
    severity: address-now
    summary: "The chain depth limit (currently hardcoded 10) is a magic number with no doc rationale, no per-universe override, and no authoring guidance on when deep chains are legitimate; authors cannot reason about when a chain will be cut."
    proposed_fix: "Expose `max_chain_depth` in universe config with a documented default and rationale; record the decision in CLAUDE.md so mechanic authors can plan chain lengths deliberately."
  - layer: mechanic
    severity: address-now
    summary: "There are no authoring guidelines warning mechanic authors about reactive cycles; two mutually-triggering mechanics can pass review individually and only fail in composition."
    proposed_fix: "Add a 'reactive-mechanic cycle hazards' section to the mechanic authoring skill (with this UC as the canonical example) and a pre-commit lint that flags reactive-trigger graphs containing cycles."
  - layer: engine
    severity: defer
    summary: "Cycle detection keys on (mechanic_id, target); a chain that alternates targets but visits the same mechanic pair could still loop under this signature until max_depth saves it."
    proposed_fix: "Extend cycle detection to consider (mechanic_id, target_signature, mutation_fingerprint); revisit once real mechanics expose the limitation."
---

# UC-E05: Circular mechanic chain

## Vignette

Alice lays a fingertip against rune_a. It warms, flares, and throws a
pale echo at rune_b across the room. Rune_b catches it, brightens, and
flings the pulse back. The runes trade the glow faster and faster until
the cascade falters and fades — the engine, unseen, has decided the loop
has run long enough. Alice's finger is still warm. The room is quiet
again.

## Why this matters

Reactive mechanics make Token World expressive: a single action can
ripple into a cascade of consequences. They also make it trivially easy
to author a cycle that would, unchecked, run forever. The current
ChainEngine already implements cycle detection (via a `seen` set keyed
on `(mechanic_id, target)`) and a depth cap (`max_depth=10`). That is
necessary but not sufficient — the truncation is silent, the cap is a
magic number, and authors have no guidance on avoiding cycles in the
first place. This scenario forces those issues into the open: cycle
detection exists, but its observability, configurability, and authoring
ergonomics do not. Phase 4 / 5 planners closing these gaps should leave
the engine's cycle-detection mechanism in place and layer
observability / ergonomics on top.

## Related use cases

- UC-E04 (nonsense-input — other engine-layer safety case)
- UC-E02 (concurrent actors — other orchestration-layer hazard)
