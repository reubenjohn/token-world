---
phase: 03
created: 2026-04-12
total_gaps: 68
use_cases_surveyed: 35
dispositions:
  address_now: 52
  defer: 16
  out_of_scope: 0
layers:
  graph_api: 18
  mechanic_protocol: 29
  engine_pipeline: 19
  cross_cutting: 2
---

# Phase 3: Gap Analysis

**Date:** 2026-04-12
**Use cases surveyed:** 35
**Gaps identified:** 68
**Disposition summary:** 52 address-now, 16 defer, 0 out-of-scope

## Summary

Phase 3 authored 35 use cases across five categories (spatial, social, resource, environmental, edge-case), surfaced 104 inline gaps, collapsed them to 80 category-scoped entries in Wave 3, and now synthesises them into **68 canonical cross-phase gaps** after applying cross-category deduplication. The canonical list is organised by architecture layer: **Graph API (18)**, **Mechanic Framework (29)**, **Engine Pipeline (19)**, and **Cross-Cutting (2)**. Six Wave-3-flagged overlap clusters were resolved here: observation projection (`GAP-CROSS01` subsumes S-E01, V-E05, O-E06, E-E05), graceful refusal (`GAP-CROSS02` subsumes R-E02, partial E-E10), terrain vocabulary (`GAP-GRAPH07` merges S-G05 + V-G04), fungibility (`GAP-GRAPH10` merges O-G03 + R-G01), passive-tick sweep (`GAP-ENG07` merges V-E01 + R-E03), and blocked movement (`GAP-MECH01` merges S-M01 + E-M03). Each canonical ID is stable — later phases cite these IDs directly.

The framework held up well at the **Graph API layer** (most graph work is additive — new query methods on top of the existing R-tree, no schema rework) and at the **Mechanic Protocol layer** (the single-actor `Mechanic.check/apply` contract covers the vast majority of seed mechanics; only `GAP-MECH12` multi-actor requires a framework extension). The bulk of **address-now** load lands on **Phase 4** (27 seed-mechanic gaps to author — this is exactly Phase 4's scope of authoring seed mechanics that exercise the framework end-to-end) and **Phase 5** (18 engine-pipeline gaps spanning classifier verdicts, observation projection, chain-depth policy, passive-tick sweep, and graceful refusal). Phase 3's own roadmap absorbs 3 graph-API gaps (`GAP-GRAPH01..03` — segment-intersections, nearest-neighbor, within-shape — direct extensions of the completed GRAPH-06 R-tree primitive). The 76% address-now ratio is deliberately high because seed mechanics (27 of 52 address-now items) are Phase 4's primary deliverable; they are work lists, not framework-surface gaps. Excluding seed-mechanic handoffs, framework-surface address-now gaps are 25/41 (61%) — a more honest headline. The 16 `defer` items cluster on vocabulary consistency (portals, terrain, containment, condition properties, fungibility representation) that can settle after v1 usage surfaces concrete needs.

Per-layer totals: Graph Layer 18, Mechanic Framework 29, Engine Pipeline 19, Cross-Cutting 2 (sum = 68).
Per-disposition totals: address-now 52, defer 16, out-of-scope 0 (sum = 68).

## Gaps by Architecture Layer

### Graph Layer

| ID | Gap | Source Use Cases | Disposition | Rationale | Target Phase |
|----|-----|------------------|-------------|-----------|--------------|
| GAP-GRAPH01 | `ctx.spatial.segment_intersections(p1, p2, filter=occludes)` is missing; LOS mechanics must scan every occluder. | UC-S02 | address-now | Extends GRAPH-06 R-tree — Phase 3 roadmap scope (D-06 heuristic) | 03 |
| GAP-GRAPH02 | `ctx.spatial.nearest(point, filter, k)` is missing; "nearest X" intents require brute-force scan. | UC-S03 | address-now | Extends GRAPH-06 R-tree — Phase 3 roadmap scope | 03 |
| GAP-GRAPH03 | `ctx.spatial.within(shape)` (bbox / radius / AoE / earshot) is missing; AoE and speech-radius mechanics must iterate all positioned nodes. | UC-S04, UC-O08 | address-now | Extends GRAPH-06 R-tree — Phase 3 roadmap scope; single primitive covers AoE and earshot | 03 |
| GAP-GRAPH04 | No first-class belief-vs-ground-truth representation; per-agent `beliefs` dict is ad-hoc and a lie overwrites reality. | UC-O04, UC-E03 | address-now | Phase 5 grounding-under-failure scope; required by observation-projection pipeline (`GAP-CROSS01`) | 05 |
| GAP-GRAPH05 | No seeded-RNG primitive on `MechanicContext`; probabilistic mechanics (contagion, combat) break replay determinism. | UC-V07 | address-now | Engine determinism contract — Phase 5 scope | 05 |
| GAP-GRAPH06 | No first-class portal/passage vocabulary; doorways are ad-hoc `subtype='doorway'` entities. | UC-S01 | defer | Vocabulary consistency — wait until v1 usage surfaces concrete need | v2 |
| GAP-GRAPH07 | No canonical terrain typing (water/wall/floor/bridge/stair); `traversable` and `terrain_type` are ad-hoc per UC. | UC-S06, UC-V05, UC-V02, UC-V04 | defer | Cross-category ontology question; defer until Phase 4 mechanic authoring forces the decision | v2 |
| GAP-GRAPH08 | Containment split across `inside` vs `located_in`; no `containment_chain(node)` helper for uniform traversal. | UC-S05 | defer | Vocabulary consistency; narrow helper, ship when needed | v2 |
| GAP-GRAPH09 | No canonical `position_of(node)` accessor; entities expose centroid ad-hoc. | UC-S07 | defer | Ergonomic helper; defer until multiple mechanics need it | v2 |
| GAP-GRAPH10 | Amount-as-property vs amount-as-entities (fungible currency, mass, nutrition) has no documented convention. | UC-O01, UC-R06, UC-O03 | defer | Cross-cutting representation tradeoff; revisit when Phase 4 authoring produces concrete cases | v2 |
| GAP-GRAPH11 | No reputation/relationship edges between agent pairs; persuasion and belief mechanics lack a trust modifier input. | UC-O02, UC-O04 | defer | Requires v2 multi-agent — single-agent v1 doesn't exercise reputation graphs | v2 |
| GAP-GRAPH12 | No standard vocabulary for condition tracking (durability / integrity / charges / uses). | UC-R05 | defer | Vocabulary consistency; wait for multiple examples | v2 |
| GAP-GRAPH13 | No `crafted_from` provenance edge from crafted items back to inputs (lineage for Phase 8 history queries). | UC-R01 | defer | Scheduled for Phase 8+ history tooling | v2 |
| GAP-GRAPH14 | No first-class `container` subtype with explicit `capacity` + nested `contained_by`; inventory is implicit `holds`-edge count. | UC-R04 | defer | Phase 8 inventory enrichment; v1 `holds` count suffices | v2 |
| GAP-GRAPH15 | `outdoor=True` is per-entity rather than derived through containment; weather reactions can't walk the containment chain. | UC-V02 | defer | Overlaps with `GAP-GRAPH08` containment helper; ship together when needed | v2 |
| GAP-GRAPH16 | No convention for in-place property transformation (`rotten=true`) vs. node-swap (remove + add); authors may diverge. | UC-V03 | defer | Documentation/convention gap; resolve during Phase 4 mechanic authoring | v2 |
| GAP-GRAPH17 | Graph API lacks transactional/compare-and-swap primitive for protecting shared-resource mutations against interleaving. | UC-E02 | defer | Single-agent v1 doesn't interleave; required for v2 multi-agent | v2 |
| GAP-GRAPH18 | Door state has no canonical representation (door-as-entity vs. `connects`-edge property); convention undocumented. | UC-E06 | defer | Convention documentation; resolve during Phase 4 mechanic authoring | v2 |

### Mechanic Framework Layer

| ID | Gap | Source Use Cases | Disposition | Rationale | Target Phase |
|----|-----|------------------|-------------|-----------|--------------|
| GAP-MECH01 | Movement seed traverses `connects` edges without inspecting intermediate blocking entities (doors, locks, barriers). | UC-S01, UC-E06 | address-now | Seed-mechanic scope — Phase 4 LLM mechanic generation | 04 |
| GAP-MECH02 | No `look` / line-of-sight seed mechanic; observation seed reveals direct neighbors regardless of occluders. | UC-S02 | address-now | Seed mechanic; consumes `GAP-GRAPH01` | 04 |
| GAP-MECH03 | No `find_nearest` seed mechanic for classified "find the nearest X" intents. | UC-S03 | address-now | Seed mechanic; consumes `GAP-GRAPH02` | 04 |
| GAP-MECH04 | No AoE seed mechanic; seeds handle single-target verbs only (damage fan-out, pressure waves). | UC-S04 | address-now | Seed mechanic; consumes `GAP-GRAPH03` | 04 |
| GAP-MECH05 | Movement seed ignores terrain type and movement-cost multiplier; every move costs the same regardless of floor vs mud vs water. | UC-S06, UC-V05 | address-now | Seed mechanic; extend movement seed | 04 |
| GAP-MECH06 | Movement seed updates `location` edges but does not sync actor's continuous `position` to destination centroid. | UC-S07 | address-now | Seed-mechanic post-move hook | 04 |
| GAP-MECH07 | No `trade` mechanic — transactional swap of held items + coin is not expressible with current seeds. | UC-O01 | address-now | Seed mechanic; requires pending-offer state (`GAP-ENG01`) | 04 |
| GAP-MECH08 | No `give` / scalar-transfer seed mechanic for one-sided hand-off of an item or a scalar amount. | UC-O03, UC-R03 | address-now | Seed mechanic; single transfer primitive covers both item (`held_by` rewrite) and scalar (conserved property) forms | 04 |
| GAP-MECH09 | No `persuade` mechanic; agents have no mutable disposition properties that other agents can influence. | UC-O02 | address-now | Seed mechanic; requires `GAP-ENG03` llm_adjudicated category | 04 |
| GAP-MECH10 | No `tell` / belief-write mechanic; per-agent mental models cannot diverge from ground truth through speech. | UC-O04 | address-now | Seed mechanic; consumes `GAP-GRAPH04` | 04 |
| GAP-MECH11 | No `teach` mechanic; `knows_skill` list does not propagate between co-located agents. | UC-O05 | address-now | Seed mechanic; requires `GAP-ENG04` skill-as-node | 04 |
| GAP-MECH12 | Mechanic API assumes a single `actor`; no cooperative / multi-actor mechanic expressible (lifting, dueting). | UC-O06 | address-now | **Framework extension** — accept `actors: list[NodeId]` + `sum_property(actors, prop)` helper | 04 |
| GAP-MECH13 | No `speak` propagation mechanic; utterances are heard by nobody or everybody regardless of volume. | UC-O08 | address-now | Seed mechanic; consumes `GAP-GRAPH03` earshot | 04 |
| GAP-MECH14 | No `craft` mechanic; recipe-driven multi-input consumption with typed output is unsupported. | UC-R01 | address-now | Seed mechanic; requires `GAP-ENG06` conservation | 04 |
| GAP-MECH15 | No `consume` mechanic; can't combine `remove_node` with a property delta atomically (eat apple → hunger down). | UC-R02 | address-now | Seed mechanic; generic parametrisation | 04 |
| GAP-MECH16 | Pickup seed ignores `inventory_cap`; outgoing `holds` edges not counted before adding a new one. | UC-R04 | address-now | Seed-mechanic precondition; requires `GAP-CROSS02` refusal narrative | 04 |
| GAP-MECH17 | No degradation / wear mechanic; using an item does not decrement durability or trigger break-at-zero. | UC-R05 | address-now | Seed mechanic; requires `GAP-ENG07` passive-tick for ambient decay | 04 |
| GAP-MECH18 | No `fungible_pay` mechanic; framework cannot subset-sum held entities to a target amount. | UC-R06 | address-now | Seed mechanic; consumes `GAP-GRAPH10` decision | 04 |
| GAP-MECH19 | No framework review gate for `source='llm_generated'` mechanics; `reviewed=false` runs as if trusted. | UC-R07 | address-now | **Framework extension** — pre-execution gate with static-analysis pass | 04 |
| GAP-MECH20 | No weather-triggered / fire-propagation mechanic family atop `environmental_reaction`; cascade chains and material-specific effects unhandled. | UC-V01, UC-V02 | address-now | Seed mechanic family; requires `GAP-ENG07` tick sweep + `GAP-ENG08` cycle detector | 04 |
| GAP-MECH21 | No `world_state_reaction` family for seasons / weather / day-night (periodic `world` properties); each would otherwise need bespoke mechanic. | UC-V02, UC-V04 | address-now | Seed mechanic family; requires `GAP-ENG09` world-property matcher | 04 |
| GAP-MECH22 | No passive-tick decay mechanic reading `decay_period`; nothing fires each tick to progress rot / rust. | UC-V03 | address-now | Seed mechanic; requires `GAP-ENG07` tick sweep | 04 |
| GAP-MECH23 | No illumination-propagation mechanic; lighting a torch doesn't recompute room `illumination`. | UC-V06 | address-now | Seed mechanic; feeds `GAP-CROSS01` observation projection | 04 |
| GAP-MECH24 | No contagion mechanic; proximity + probability-driven transmission unhandled. | UC-V07 | address-now | Seed mechanic; requires `GAP-GRAPH05` seeded RNG | 04 |
| GAP-MECH25 | No belief-update side effect on visibly-failed precondition (actor walks away not knowing the chest was locked). | UC-E03 | address-now | Seed mechanic pattern; consumes `GAP-GRAPH04` | 04 |
| GAP-MECH26 | No authoring guidelines (or pre-commit lint) warning mechanic authors about reactive cycles; two mutually-triggering mechanics only fail in composition. | UC-E05 | address-now | Authoring-skill documentation + lint; Phase 4 scope | 04 |
| GAP-MECH27 | No minimal `try_door` seed (report door state, flip `locked=false` when actor has matching key). | UC-E06 | address-now | Seed mechanic; shares refusal pattern (`GAP-CROSS02`) | 04 |
| GAP-MECH28 | No partial / portioned consumption (half-eaten apple, discrete bites before removal). | UC-R02 | defer | Narrow enrichment; ship when authoring needs it | v2 |
| GAP-MECH29 | No making-change in `fungible_pay` when exact payment is impossible (pay 4 with 5s and 2s, change owed). | UC-R06 | defer | Enrichment of `GAP-MECH18`; defer until commerce is exercised | v2 |

### Engine Pipeline Layer

| ID | Gap | Source Use Cases | Disposition | Rationale | Target Phase |
|----|-----|------------------|-------------|-----------|--------------|
| GAP-ENG01 | Classifier has no multi-turn offer/accept protocol; each turn is interpreted in isolation so `trade` cannot span ticks. | UC-O01 | address-now | Phase 5 classifier pipeline — pending-offer state on offering agent | 05 |
| GAP-ENG02 | Classified-action schema has no `indirect_object`; ditransitive verbs (give / teach / show / tell) cannot structurally distinguish direct object from recipient. | UC-O03, UC-O05, UC-R03 | address-now | Phase 5 classifier schema extension | 05 |
| GAP-ENG03 | No `llm_adjudicated` mechanic category for probabilistic/social-check resolution (persuasion, intimidation). | UC-O02 | address-now | Phase 5 mechanic-category extension | 05 |
| GAP-ENG04 | Skill / concept names are bare strings, not nodes — classifier cannot disambiguate "teach a skill" from "teach a song" or "teach about a person". | UC-O05 | address-now | Phase 5 classifier; introduce `skill` namespace or entity nodes | 05 |
| GAP-ENG05 | Tick loop interprets each agent's intent independently; no intent-fusion pre-pass to dispatch multi-actor mechanics. | UC-O06 | address-now | Phase 5 pre-execution pass; pairs with `GAP-MECH12` multi-actor mechanic | 05 |
| GAP-ENG06 | No conservation enforcement across mutations; an increment to a conserved property can lack a matching decrement (coin/mass/nutrition). | UC-R01, UC-R03, UC-R07, UC-S04 | address-now | Phase 5 engine hook; YAML registry of conserved properties | 05 |
| GAP-ENG07 | Engine loop only invokes mechanics in response to actions; no tick-end sweep for passive/environmental/decay mechanics. | UC-V01, UC-V02, UC-V03, UC-V04, UC-V07, UC-R05 | address-now | Phase 5 tick-end sweep (SIM-09 passive-tick handling) | 05 |
| GAP-ENG08 | No cycle detector / per-tick visited set for spread/propagation chains; a node can be reprocessed and state can oscillate. | UC-V01, UC-E05 | address-now | Phase 5 chain-depth policy; emits `chain_truncated` (see `GAP-ENG17`) | 05 |
| GAP-ENG09 | Mechanic-matcher vocabulary has no `WorldPropertyMatcher`; world-level property changes (season/weather/day-of-year) have nowhere to dispatch from. | UC-V02, UC-V04 | address-now | Phase 5 matcher extension; canonical `world` node | 05 |
| GAP-ENG10 | Calendar / time-scale not formalised; `day_of_year → season` derivation has nowhere to live. | UC-V04 | address-now | Phase 5 engine; tie to tick → batch → epoch hierarchy | 05 |
| GAP-ENG11 | Classifier does not defensively handle targets that fail graph lookup; no standard `no_such_target` verdict. | UC-E01 | address-now | Phase 5 classifier — grounding under failure | 05 |
| GAP-ENG12 | Observation synthesiser has no grounding guardrail when target is absent; a free-generation LLM may hallucinate the missing entity (violates SIM-05). | UC-E01, UC-E04 | address-now | Phase 5 observation pipeline hard-constraint template + rubric test | 05 |
| GAP-ENG13 | No documented turn-ordering policy for concurrent actors targeting the same exclusive entity on the same tick; behaviour undefined. | UC-E02 | address-now | Phase 5 engine invariant (tick-order FIFO or single-actor-per-tick) | 05 |
| GAP-ENG14 | No pre-execution conflict-detection pass; two actions on the same exclusive target both execute in isolation. | UC-E02 | address-now | Phase 5 engine — groups actions by (verb, exclusive_target) and resolves via `GAP-ENG13` policy | 05 |
| GAP-ENG15 | Classifier has no `no_viable_action` verdict; under-constrained LLM fabricates a plausible verb rather than admit meaninglessness. | UC-E04 | address-now | Phase 5 classifier + confidence threshold | 05 |
| GAP-ENG16 | Mechanic generation may trigger on nonsense verbs, polluting the registry with garbage (`gragh`-style). | UC-E04 | address-now | Phase 4 generation-gate — classifier-confidence threshold plus manual-review queue | 04 |
| GAP-ENG17 | Chain-truncation events (cycle or max-depth) are not surfaced to observation or trace; silent truncation hides real engine behaviour. | UC-E05 | address-now | Phase 5 trace event; narrative helper ("the cascade falls into a loop") | 05 |
| GAP-ENG18 | `max_chain_depth=10` is a hardcoded magic number with no doc rationale and no per-universe override. | UC-E05 | address-now | Phase 5 universe-config key with documented default | 05 |
| GAP-ENG19 | Multi-party commit / consent / listener-reaction primitive: no way for target/recipient to refuse before commit; no atomic precondition check across multi-actor mechanics; no listener-next-tick reaction hook. | UC-O03, UC-O06, UC-O08, UC-E03, UC-E05, UC-E06 | defer | Engine UX hardening; observer-belief propagation is v2 multi-agent territory | v2 |

### Cross-Cutting

| ID | Gap | Source Use Cases | Disposition | Rationale | Target Phase |
|----|-----|------------------|-------------|-----------|--------------|
| GAP-CROSS01 | Observation pipeline is not a projection — no `visible_to(actor)` scoping, no containment-chain walk, no illumination filter, no public/private/requires-inspection property visibility class. Four UCs in three categories all point at the same engine surface: "the observation pipeline needs to PROJECT, not DUMP". | UC-S05, UC-V06, UC-O07, UC-E03 | address-now | Phase 5 observation projection layer (SIM-07). Consolidates S-E01 + V-E05 + O-E06 + E-E05. Highest-leverage cross-cutting gap — closes half the edge-case category by construction. Shadow alias: **GAP-X01** (reserved placeholder — see Out of Scope section). | 05 |
| GAP-CROSS02 | No standard contract for a mechanic to refuse an action and produce a grounded user-facing failure narrative ("the door is locked", "bag is full", "nothing happens"). Currently each mechanic reinvents its own "blocked-by" template; engine assumes every action mutates state. | UC-R04, UC-R07, UC-E06 | address-now | Phase 5 engine contract `(ok=False, narrative=...)` + shared blocked-by helper. Consolidates R-E02 + partial E-E10. | 05 |

## Architecture Adjustments

Concrete changes to existing framework code derived from `address-now` gaps with Target Phase `03` (all three extend the completed GRAPH-06 R-tree primitive):

- Add `ctx.spatial.segment_intersections(p1, p2, filter=...)` to the SpatialIndex DSL — implements `GAP-GRAPH01`
- Add `ctx.spatial.nearest(point, filter=..., k=1)` to the SpatialIndex DSL — implements `GAP-GRAPH02`
- Add `ctx.spatial.within(shape)` (bbox / radius) to the SpatialIndex DSL — implements `GAP-GRAPH03`

These are additive method-level extensions on the existing `MechanicContext.spatial` lazy property (established in plan 03-02). No schema change, no new persistence surface, no API break. Wave-4 decision: these three can be absorbed in a Phase 3 follow-on plan OR deferred to Phase 4 authoring (where the first consumer mechanic will surface which signature is ergonomic). Recommendation: defer to Phase 4; author the consumer mechanic + the query method in the same commit so ergonomics inform the signature.

## Dispositions

### Address Now

All 52 address-now gaps route to downstream phases as follows. Phase 3 itself absorbs 3 graph-API extensions; Phase 4 absorbs 28 (27 seed mechanics + `GAP-ENG16` generation-gate); Phase 5 absorbs 21 (engine pipeline + both cross-cutting gaps + beliefs/RNG graph primitives).

**Phase 03 (3):**

- `GAP-GRAPH01` — segment intersections on R-tree
- `GAP-GRAPH02` — nearest-neighbor on R-tree
- `GAP-GRAPH03` — within-shape / radius on R-tree (covers AoE and earshot)

**Phase 04 — LLM Mechanic Generation (28):**

- `GAP-MECH01` — blocked-movement (doorway + locked-door path precondition)
- `GAP-MECH02` — look / line-of-sight seed
- `GAP-MECH03` — find_nearest seed
- `GAP-MECH04` — AoE seed
- `GAP-MECH05` — terrain-aware movement
- `GAP-MECH06` — movement position-sync
- `GAP-MECH07` — trade
- `GAP-MECH08` — give / scalar-transfer
- `GAP-MECH09` — persuade
- `GAP-MECH10` — tell / belief-write
- `GAP-MECH11` — teach
- `GAP-MECH12` — cooperative multi-actor mechanic (framework extension)
- `GAP-MECH13` — speak propagation
- `GAP-MECH14` — craft
- `GAP-MECH15` — consume
- `GAP-MECH16` — pickup with inventory-cap
- `GAP-MECH17` — wear / degradation
- `GAP-MECH18` — fungible_pay
- `GAP-MECH19` — mechanic review gate (framework extension)
- `GAP-MECH20` — weather / fire propagation family
- `GAP-MECH21` — world_state_reaction family
- `GAP-MECH22` — passive-tick decay
- `GAP-MECH23` — illumination propagation
- `GAP-MECH24` — contagion
- `GAP-MECH25` — belief-update on failed precondition
- `GAP-MECH26` — reactive-cycle authoring guidelines + lint
- `GAP-MECH27` — try_door seed
- `GAP-ENG16` — classifier-confidence gate on mechanic generation

**Phase 05 — Simulation Engine (21):**

- `GAP-GRAPH04` — belief representation (canonical `believes_about` edges)
- `GAP-GRAPH05` — seeded-RNG on `MechanicContext`
- `GAP-ENG01` — multi-turn offer/accept state
- `GAP-ENG02` — `indirect_object` classifier field
- `GAP-ENG03` — `llm_adjudicated` mechanic category
- `GAP-ENG04` — skill / concept nodes vs strings
- `GAP-ENG05` — intent-matching multi-actor fusion pre-pass
- `GAP-ENG06` — conservation enforcement + conserved-property registry
- `GAP-ENG07` — passive-tick sweep (tick-end invocation; covers decay, weather, fire, seasons, contagion)
- `GAP-ENG08` — chain cycle detector + per-tick visited set
- `GAP-ENG09` — `WorldPropertyMatcher`
- `GAP-ENG10` — calendar / time-scale derivation
- `GAP-ENG11` — `no_such_target` classifier verdict
- `GAP-ENG12` — grounding guardrail for absent targets
- `GAP-ENG13` — concurrent-action ordering policy
- `GAP-ENG14` — pre-execution conflict detection
- `GAP-ENG15` — `no_viable_action` verdict + confidence threshold
- `GAP-ENG17` — `chain_truncated` trace event
- `GAP-ENG18` — `max_chain_depth` universe-config key
- `GAP-CROSS01` — observation projection (`visible_to` + property visibility classes + containment walk + illumination filter)
- `GAP-CROSS02` — graceful refusal contract `(ok=False, narrative=...)` + blocked-by helper

### Defer

See `.planning/backlog/phase-03-gap-deferrals.md` for the full deferred list (16 gaps). Summary:

- **Graph-API vocabulary/convention (13):** `GAP-GRAPH06` (portals), `GAP-GRAPH07` (terrain), `GAP-GRAPH08` (containment convention), `GAP-GRAPH09` (position accessor), `GAP-GRAPH10` (fungibility), `GAP-GRAPH11` (reputation edges), `GAP-GRAPH12` (condition-property vocabulary), `GAP-GRAPH13` (crafted_from provenance), `GAP-GRAPH14` (container subtype), `GAP-GRAPH15` (sky-exposure derivation), `GAP-GRAPH16` (transform-vs-swap convention), `GAP-GRAPH17` (CAS primitive), `GAP-GRAPH18` (door-state convention)
- **Mechanic-enrichment (2):** `GAP-MECH28` (partial consumption), `GAP-MECH29` (making-change)
- **Engine UX hardening (1):** `GAP-ENG19` (multi-party commit / consent / listener-reaction)

### Out of Scope

No use case surfaced a genuinely out-of-scope gap (i.e. one conflicting with REQUIREMENTS.md §Out of Scope — game adaptation, web UI, visual output, real-time, civic simulation, distributed graph, authentication, plugin system). No rows appear in this section.

The reserved shadow-alias ID **GAP-X01** is declared purely to preserve the Wave-0 schema regex `GAP-[GMEX]\d{2}` coverage across all four letter classes. It is not a gap, not a work item, and not counted in `total_gaps`. It is cited once in the Cross-Cutting table Rationale cell for `GAP-CROSS01` (per plan 03-12 Task 1 Step C guidance: "if no out-of-scope gaps, add an explicit `GAP-X01 — shadow alias` entry in the Cross-Cutting table Rationale column").

## Cross-References

By use case (reverse lookup — every UC cited in at least one canonical gap):

- UC-S01 → [GAP-GRAPH06, GAP-MECH01]
- UC-S02 → [GAP-GRAPH01, GAP-MECH02]
- UC-S03 → [GAP-GRAPH02, GAP-MECH03]
- UC-S04 → [GAP-GRAPH03, GAP-MECH04, GAP-ENG06]
- UC-S05 → [GAP-GRAPH08, GAP-CROSS01]
- UC-S06 → [GAP-GRAPH07, GAP-MECH05]
- UC-S07 → [GAP-GRAPH09, GAP-MECH06]
- UC-O01 → [GAP-GRAPH10, GAP-MECH07, GAP-ENG01]
- UC-O02 → [GAP-GRAPH11, GAP-MECH09, GAP-ENG03]
- UC-O03 → [GAP-GRAPH10, GAP-MECH08, GAP-ENG02, GAP-ENG19]
- UC-O04 → [GAP-GRAPH04, GAP-GRAPH11, GAP-MECH10]
- UC-O05 → [GAP-MECH11, GAP-ENG02, GAP-ENG04]
- UC-O06 → [GAP-MECH12, GAP-ENG05, GAP-ENG19]
- UC-O07 → [GAP-CROSS01]
- UC-O08 → [GAP-GRAPH03, GAP-MECH13, GAP-ENG19]
- UC-R01 → [GAP-GRAPH13, GAP-MECH14, GAP-ENG06]
- UC-R02 → [GAP-MECH15, GAP-MECH28]
- UC-R03 → [GAP-GRAPH10, GAP-MECH08, GAP-ENG02, GAP-ENG06]
- UC-R04 → [GAP-GRAPH14, GAP-MECH16, GAP-CROSS02]
- UC-R05 → [GAP-GRAPH12, GAP-MECH17, GAP-ENG07]
- UC-R06 → [GAP-GRAPH10, GAP-MECH18, GAP-MECH29]
- UC-R07 → [GAP-MECH19, GAP-ENG06, GAP-CROSS02]
- UC-V01 → [GAP-MECH20, GAP-ENG07, GAP-ENG08]
- UC-V02 → [GAP-GRAPH07, GAP-GRAPH15, GAP-MECH20, GAP-MECH21, GAP-ENG07, GAP-ENG09]
- UC-V03 → [GAP-GRAPH16, GAP-MECH22, GAP-ENG07]
- UC-V04 → [GAP-GRAPH07, GAP-MECH21, GAP-ENG07, GAP-ENG09, GAP-ENG10]
- UC-V05 → [GAP-GRAPH07, GAP-MECH05]
- UC-V06 → [GAP-MECH23, GAP-CROSS01]
- UC-V07 → [GAP-GRAPH05, GAP-MECH24, GAP-ENG07]
- UC-E01 → [GAP-ENG11, GAP-ENG12]
- UC-E02 → [GAP-GRAPH17, GAP-ENG13, GAP-ENG14]
- UC-E03 → [GAP-GRAPH04, GAP-MECH25, GAP-CROSS01, GAP-ENG19]
- UC-E04 → [GAP-ENG12, GAP-ENG15, GAP-ENG16]
- UC-E05 → [GAP-MECH26, GAP-ENG08, GAP-ENG17, GAP-ENG18, GAP-ENG19]
- UC-E06 → [GAP-GRAPH18, GAP-MECH01, GAP-MECH27, GAP-CROSS02, GAP-ENG19]

## Appendix

### Cross-category merges applied during synthesis

| Canonical ID | Merged Wave-3 IDs | Merge rationale |
|--------------|--------------------|-----------------|
| `GAP-GRAPH03` | `S-G03` (within-shape) + `O-G02` (agents_within earshot) | Same R-tree query surface; shape-based spatial filter covers both AoE and earshot. |
| `GAP-GRAPH04` | `O-G01` (beliefs divergence) + `E-G01` (belief-vs-truth representation) | Identical modelling question viewed from social vs edge-case angles. |
| `GAP-GRAPH07` | `S-G05` + `V-G04` | Terrain ontology across spatial and environmental categories. |
| `GAP-GRAPH10` | `O-G03` + `R-G01` | Fungibility / amount-as-property vs amount-as-entities across social and resource. |
| `GAP-MECH01` | `S-M01` (doorway) + `E-M03` (locked-room path) | Same movement-precondition gap. |
| `GAP-MECH05` | `S-M05` (terrain-aware) + `V-M04` (terrain cost) | Same movement extension; stamina is a cost multiplier. |
| `GAP-MECH08` | `O-M02` (give) + `R-M03` (scalar transfer) | Single transfer primitive for items and conserved scalars. |
| `GAP-ENG07` | `V-E01` (passive-tick sweep) + `R-E03` (passive degradation) | Same tick-end-sweep requirement. |
| `GAP-CROSS01` | `S-E01` + `V-E05` + `O-E06` + `E-E05` | Observation-projection surface — consolidated across four UCs in three categories. |
| `GAP-CROSS02` | `R-E02` + partial `E-E10` (blocked-by narrative helper) | Graceful refusal contract + shared narrative template. |

### Wave-3 gaps not surfacing in the canonical list

All 80 Wave-3 dedup'd gaps are accounted for in the canonical list above — no Wave-3 ID was dropped. Cross-category merges reduce 80 source entries to 69 canonical gaps (11 merged). The 6 explicit Wave-3 overlap clusters flagged by plan 03-11 are all resolved (see merges table above; `GAP-ENG19` also gathers the deferred portions of `E-E10` plus `O-E07`).

---
*Phase 3 gap analysis synthesis — 2026-04-12*
