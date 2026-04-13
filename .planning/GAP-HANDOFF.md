# Phase 3 Gap Handoff

**Created:** 2026-04-12
**Source:** `.planning/GAP-ANALYSIS.md` (synthesis of 35 use cases across 5 categories)
**Purpose:** Address-now gaps grouped by target downstream phase. Phase N planners MUST read this file and cite these gap IDs in their plan requirements / frontmatter.

## By Target Phase

### Phase 04 (LLM Mechanic Generation)

| Gap ID | Summary | Source UCs | Rationale |
|--------|---------|------------|-----------|
| GAP-MECH01 | Movement seed traverses `connects` edges without inspecting intermediate blocking entities (doors, locks, barriers). | UC-S01, UC-E06 | Seed-mechanic scope — Phase 4 LLM mechanic generation |
| GAP-MECH02 | No `look` / line-of-sight seed mechanic; observation seed reveals direct neighbors regardless of occluders. | UC-S02 | Seed mechanic; consumes GAP-GRAPH01 |
| GAP-MECH03 | No `find_nearest` seed mechanic for classified "find the nearest X" intents. | UC-S03 | Seed mechanic; consumes GAP-GRAPH02 |
| GAP-MECH04 | No AoE seed mechanic; seeds handle single-target verbs only (damage fan-out, pressure waves). | UC-S04 | Seed mechanic; consumes GAP-GRAPH03 |
| GAP-MECH05 | Movement seed ignores terrain type and movement-cost multiplier; every move costs the same regardless of floor vs mud vs water. | UC-S06, UC-V05 | Seed mechanic; extend movement seed |
| GAP-MECH06 | Movement seed updates `location` edges but does not sync actor's continuous `position` to destination centroid. | UC-S07 | Seed-mechanic post-move hook |
| GAP-MECH07 | No `trade` mechanic — transactional swap of held items + coin is not expressible with current seeds. | UC-O01 | Seed mechanic; requires pending-offer state (GAP-ENG01) |
| GAP-MECH08 | No `give` / scalar-transfer seed mechanic for one-sided hand-off of an item or a scalar amount. | UC-O03, UC-R03 | Seed mechanic; single transfer primitive covers both item and scalar forms |
| GAP-MECH09 | No `persuade` mechanic; agents have no mutable disposition properties that other agents can influence. | UC-O02 | Seed mechanic; requires GAP-ENG03 llm_adjudicated category |
| GAP-MECH10 | No `tell` / belief-write mechanic; per-agent mental models cannot diverge from ground truth through speech. | UC-O04 | Seed mechanic; consumes GAP-GRAPH04 |
| GAP-MECH11 | No `teach` mechanic; `knows_skill` list does not propagate between co-located agents. | UC-O05 | Seed mechanic; requires GAP-ENG04 skill-as-node |
| GAP-MECH12 | Mechanic API assumes a single `actor`; no cooperative / multi-actor mechanic expressible (lifting, dueting). | UC-O06 | Framework extension — accept `actors: list[NodeId]` + `sum_property(actors, prop)` helper |
| GAP-MECH13 | No `speak` propagation mechanic; utterances are heard by nobody or everybody regardless of volume. | UC-O08 | Seed mechanic; consumes GAP-GRAPH03 earshot |
| GAP-MECH14 | No `craft` mechanic; recipe-driven multi-input consumption with typed output is unsupported. | UC-R01 | Seed mechanic; requires GAP-ENG06 conservation |
| GAP-MECH15 | No `consume` mechanic; can't combine `remove_node` with a property delta atomically (eat apple → hunger down). | UC-R02 | Seed mechanic; generic parametrisation |
| GAP-MECH16 | Pickup seed ignores `inventory_cap`; outgoing `holds` edges not counted before adding a new one. | UC-R04 | Seed-mechanic precondition; requires GAP-CROSS02 refusal narrative |
| GAP-MECH17 | No degradation / wear mechanic; using an item does not decrement durability or trigger break-at-zero. | UC-R05 | Seed mechanic; requires GAP-ENG07 passive-tick for ambient decay |
| GAP-MECH18 | No `fungible_pay` mechanic; framework cannot subset-sum held entities to a target amount. | UC-R06 | Seed mechanic; consumes GAP-GRAPH10 decision |
| GAP-MECH19 | No framework review gate for `source='llm_generated'` mechanics; `reviewed=false` runs as if trusted. | UC-R07 | Framework extension — pre-execution gate with static-analysis pass |
| GAP-MECH20 | No weather-triggered / fire-propagation mechanic family atop `environmental_reaction`. | UC-V01, UC-V02 | Seed mechanic family; requires GAP-ENG07 tick sweep + GAP-ENG08 cycle detector |
| GAP-MECH21 | No `world_state_reaction` family for seasons / weather / day-night (periodic `world` properties). | UC-V02, UC-V04 | Seed mechanic family; requires GAP-ENG09 world-property matcher |
| GAP-MECH22 | No passive-tick decay mechanic reading `decay_period`; nothing fires each tick to progress rot / rust. | UC-V03 | Seed mechanic; requires GAP-ENG07 tick sweep |
| GAP-MECH23 | No illumination-propagation mechanic; lighting a torch doesn't recompute room `illumination`. | UC-V06 | Seed mechanic; feeds GAP-CROSS01 observation projection |
| GAP-MECH24 | No contagion mechanic; proximity + probability-driven transmission unhandled. | UC-V07 | Seed mechanic; requires GAP-GRAPH05 seeded RNG |
| GAP-MECH25 | No belief-update side effect on visibly-failed precondition (actor walks away not knowing the chest was locked). | UC-E03 | Seed mechanic pattern; consumes GAP-GRAPH04 |
| GAP-MECH26 | No authoring guidelines (or pre-commit lint) warning mechanic authors about reactive cycles. | UC-E05 | Authoring-skill documentation + lint; Phase 4 scope |
| GAP-MECH27 | No minimal `try_door` seed (report door state, flip `locked=false` when actor has matching key). | UC-E06 | Seed mechanic; shares refusal pattern GAP-CROSS02 |
| GAP-ENG16 | Mechanic generation may trigger on nonsense verbs, polluting the registry with garbage (`gragh`-style). | UC-E04 | Phase 4 generation-gate — classifier-confidence threshold plus manual-review queue |

### Phase 05 (Simulation Engine)

| Gap ID | Summary | Source UCs | Rationale |
|--------|---------|------------|-----------|
| GAP-GRAPH04 | No first-class belief-vs-ground-truth representation; per-agent `beliefs` dict is ad-hoc and a lie overwrites reality. | UC-O04, UC-E03 | Phase 5 grounding-under-failure scope; required by observation-projection pipeline (GAP-CROSS01) |
| GAP-GRAPH05 | No seeded-RNG primitive on `MechanicContext`; probabilistic mechanics (contagion, combat) break replay determinism. | UC-V07 | Engine determinism contract — Phase 5 scope |
| GAP-ENG01 | Classifier has no multi-turn offer/accept protocol; each turn is interpreted in isolation so `trade` cannot span ticks. | UC-O01 | Phase 5 classifier pipeline — pending-offer state on offering agent |
| GAP-ENG02 | Classified-action schema has no `indirect_object`; ditransitive verbs cannot structurally distinguish direct object from recipient. | UC-O03, UC-O05, UC-R03 | Phase 5 classifier schema extension |
| GAP-ENG03 | No `llm_adjudicated` mechanic category for probabilistic/social-check resolution. | UC-O02 | Phase 5 mechanic-category extension |
| GAP-ENG04 | Skill / concept names are bare strings, not nodes — classifier cannot disambiguate "teach a skill" from "teach a song". | UC-O05 | Phase 5 classifier; introduce `skill` namespace or entity nodes |
| GAP-ENG05 | Tick loop interprets each agent's intent independently; no intent-fusion pre-pass to dispatch multi-actor mechanics. | UC-O06 | Phase 5 pre-execution pass; pairs with GAP-MECH12 multi-actor mechanic |
| GAP-ENG06 | No conservation enforcement across mutations; an increment to a conserved property can lack a matching decrement. | UC-R01, UC-R03, UC-R07, UC-S04 | Phase 5 engine hook; YAML registry of conserved properties |
| GAP-ENG07 | Engine loop only invokes mechanics in response to actions; no tick-end sweep for passive/environmental/decay mechanics. | UC-V01, UC-V02, UC-V03, UC-V04, UC-V07, UC-R05 | Phase 5 tick-end sweep (SIM-09 passive-tick handling) |
| GAP-ENG08 | No cycle detector / per-tick visited set for spread/propagation chains; a node can be reprocessed and state can oscillate. | UC-V01, UC-E05 | Phase 5 chain-depth policy; emits chain_truncated (see GAP-ENG17) |
| GAP-ENG09 | Mechanic-matcher vocabulary has no `WorldPropertyMatcher`; world-level property changes have nowhere to dispatch from. | UC-V02, UC-V04 | Phase 5 matcher extension; canonical `world` node |
| GAP-ENG10 | Calendar / time-scale not formalised; `day_of_year → season` derivation has nowhere to live. | UC-V04 | Phase 5 engine; tie to tick → batch → epoch hierarchy |
| GAP-ENG11 | Classifier does not defensively handle targets that fail graph lookup; no standard `no_such_target` verdict. | UC-E01 | Phase 5 classifier — grounding under failure |
| GAP-ENG12 | Observation synthesiser has no grounding guardrail when target is absent; free-generation LLM may hallucinate the missing entity. | UC-E01, UC-E04 | Phase 5 observation pipeline hard-constraint template + rubric test |
| GAP-ENG13 | No documented turn-ordering policy for concurrent actors targeting the same exclusive entity on the same tick. | UC-E02 | Phase 5 engine invariant (tick-order FIFO or single-actor-per-tick) |
| GAP-ENG14 | No pre-execution conflict-detection pass; two actions on the same exclusive target both execute in isolation. | UC-E02 | Phase 5 engine — groups actions by (verb, exclusive_target) and resolves via GAP-ENG13 policy |
| GAP-ENG15 | Classifier has no `no_viable_action` verdict; under-constrained LLM fabricates a plausible verb rather than admit meaninglessness. | UC-E04 | Phase 5 classifier + confidence threshold |
| GAP-ENG17 | Chain-truncation events (cycle or max-depth) are not surfaced to observation or trace; silent truncation hides real engine behaviour. | UC-E05 | Phase 5 trace event; narrative helper |
| GAP-ENG18 | `max_chain_depth=10` is a hardcoded magic number with no doc rationale and no per-universe override. | UC-E05 | Phase 5 universe-config key with documented default |
| GAP-CROSS01 | Observation pipeline is not a projection — no `visible_to(actor)` scoping, no containment-chain walk, no illumination filter, no property visibility classes. | UC-S05, UC-V06, UC-O07, UC-E03 | Phase 5 observation projection layer (SIM-07). Highest-leverage cross-cutting gap. |
| GAP-CROSS02 | No standard contract for a mechanic to refuse an action and produce a grounded user-facing failure narrative. | UC-R04, UC-R07, UC-E06 | Phase 5 engine contract `(ok=False, narrative=...)` + shared blocked-by helper. |

### Phase 06 (Resident Agent)

_No gaps route to this phase._

### Phase 07 (Attention & Consciousness)

_No gaps route to this phase._

---
*Handoff derived deterministically from `.planning/GAP-ANALYSIS.md` — 2026-04-12*
