# Environmental — Category Summary

**Use cases reviewed:** 7 (UC-V01..UC-V07)
**Total inline gaps:** 20
**Deduplicated gaps:** 15

## Review Findings

- **All UCs pass schema validator:** YES (UC-V01..UC-V07).
- **All UCs' `setup.graph_builder` creates every referenced actor/target:** YES, with one audit-script clarification. UC-V01/V02/V03/V04 use `actor: engine` to denote a tick-driven/system-level actor rather than a graph-resident agent — this is an intentional sentinel for passive/environmental mechanics. The sanity-check script was updated (Wave 3 deviation) to treat `engine` as a valid actor sentinel; no UC frontmatter was modified for this family. Targets referenced in `actions[].classified.target` (e.g. `wooden_table`, `world`, `oak_tree`) are all present in their respective setups.
- **UC status transitions:**
  - draft → reviewed: UC-V01, UC-V02, UC-V03, UC-V04, UC-V05, UC-V06, UC-V07 (all 7).
  - remaining as draft: none.
- **Recurring engine dependency:** every V-UC except UC-V05 and UC-V06 depends on a passive-tick loop (SIM-09). That is not an environmental-category shortfall per se — it is a framework precondition. Wave 4 should track it as a single cross-category engine gap rather than repeating it per UC.

## Deduplicated Gap List

| ID | Layer | Severity | Summary | Source UCs | Proposed Fix |
|----|-------|----------|---------|------------|--------------|
| V-E01 | engine | address-now | Engine loop only invokes mechanics in response to actions; no tick-end sweep exists, so no passive/environmental mechanic can fire without an agent action. | UC-V01, UC-V02, UC-V03, UC-V04, UC-V07 | Add a tick-end sweep that invokes all mechanics whose matcher subscribes to `current_tick` (SIM-09 passive-tick handling). Shared driver for fire spread, weather flips, decay, seasons, and contagion symptom progression. |
| V-M01 | mechanic | address-now | `environmental_reaction` seed handles single-entity temperature changes but not weather-triggered cascades or chain-depth limits for propagation. | UC-V01, UC-V02 | Layer a `weather_reaction` / `fire_propagation` mechanic family on the seed that enumerates outdoor or adjacent entities and applies material-specific side effects; cap chain depth explicitly. |
| V-E02 | engine | address-now | No cycle detector for spread/propagation chains on the same tick; a node could be reprocessed and state could oscillate. | UC-V01, UC-E05 (cross-cat) | Engine tracks a per-tick visited set and caps chain depth. Overlaps with UC-E05's `max_chain_depth` config and `chain_truncated` trace event. |
| V-E03 | engine | address-now | No global-state tick hook: weather and calendar sit on a `world` node but no mechanic framework primitive watches world-level property changes. | UC-V02, UC-V04 | Extend mechanic matcher vocabulary with a `WorldPropertyMatcher`, or define a canonical `world` node the engine dispatches from each tick (SIM-10). |
| V-M02 | mechanic | address-now | No world-state reaction family: seasons, weather, and day/night are all periodic `world` properties but each would otherwise need its own bespoke mechanic. | UC-V02, UC-V04 | Generalise to a scheduled `world_state_reaction` mechanic family, parametrized by the world property being tracked. |
| V-M03 | mechanic | address-now | No passive-tick decay mechanic; `decay_period` is on the apple but nothing reads it each tick. | UC-V03 | Introduce a passive-tick matcher (watches `current_tick` on `world`) so a `decay_mechanic` can fire each tick. Requires V-E01. |
| V-E04 | engine | address-now | Calendar/time-scale modelling is not formalised; `day_of_year → season` derivation has nowhere to live. | UC-V04 | Define `day_of_year → season` derivation in the engine or a scheduled mechanic; tie to tick→batch→epoch hierarchy (see phase 02 AGENT-02 design). |
| V-M04 | mechanic | address-now | Movement seed does not read `terrain_type` or `movement_cost_multiplier`; all moves cost the same. | UC-V05 | Extend movement to read cost multiplier from source/destination and deduct stamina accordingly. Overlaps with S-M05 (terrain-aware movement). |
| V-E05 | engine | address-now | Observation seed lists neighbors regardless of illumination; no filter between "what the graph contains" and "what the actor can perceive". | UC-V06 | Introduce an observation filter layer in the engine that consults light/LOS before revealing entities (SIM-07 observation filtering). Shared with UC-O07 (visibility) and UC-E03 (partial knowledge). |
| V-M05 | mechanic | address-now | No illumination-propagation mechanic; lighting a torch doesn't change the room's illumination. | UC-V06 | Author `illumination_propagation` mechanic that sums `light_radius` from lit sources within a room and writes `illumination` onto the room node. |
| V-M06 | mechanic | address-now | No contagion mechanic; transmission is proximity + probability dependent and no seed handles either. | UC-V07 | Author `contagion_mechanic` that enumerates co-located agents and rolls transmission against carrier's symptomatic state and target's `immune_system`. |
| V-G01 | graph | address-now | Non-deterministic mutations are not first-class; engine currently assumes `mechanic.apply` is pure, conflicting with probabilistic transmission (and future dice/combat). | UC-V07 | Introduce a seeded-RNG primitive on `MechanicContext` so probabilistic mechanics are reproducible under replay; document the determinism contract. |
| V-G02 | graph | defer | `outdoor=True` is modeled per-entity; a location-based derivation (`is_under_sky`) would scale better through nested containment. | UC-V02 | Add sky-exposure derivation over containment edges, or let `weather_reaction` walk the containment chain. Overlaps with S-G06 containment-traversal helper. |
| V-G03 | graph | defer | Apple transformation is a property flip (`rotten=true`) rather than a node-swap; no convention declares when to pick which. | UC-V03 | Document convention in mechanic-framework doc: prefer in-place property transformation unless the entity's identity genuinely changes. |
| V-G04 | graph | defer | Ad-hoc property flags (deciduous, outdoor, flammable, terrain_type) cross UCs with no ontology; a plant/terrain/material taxonomy would reduce hardcoded subtype branches. | UC-V02, UC-V04, UC-V05 | Decide whether ontology belongs in subtype hierarchy or in per-mechanic branching; document in ARCHITECTURE.md. |

**Audit metadata:** 20 inline gaps across 7 UCs collapsed to 15 entries; principal merges were (a) UC-V01 + UC-V02 environmental/weather reaction families into V-M01/V-M02, (b) the V-V01 + V-V02 + V-V03 + V-V04 + V-V07 shared dependency on a passive-tick engine sweep into V-E01 (which also blocks UC-R05), and (c) UC-V02 + UC-V04 world-property matcher needs into V-E03. The `engine` sentinel-actor pattern used by UC-V01..V04 was recognized by the audit script rather than modifying UC frontmatter — no V-UC required content edits during Wave 3.

## Patterns Noticed

Environmental is the **most engine-dependent** category: 6 of 15 dedup'd gaps are engine-layer, and the single biggest one (V-E01 passive-tick sweep) gates five of the seven UCs. Once that single engine primitive lands, most environmental mechanics become straightforward domain authoring. The second cross-cutting theme is **observation filtering** (V-E05) which is the same surface UC-O07 (visibility), UC-S05 (nested containment), and UC-E03 (partial knowledge) describe — four UCs in three categories all pointing at "the observation pipeline needs to project, not dump". Third, several environmental gaps explicitly cross into spatial (terrain costs, containment-chain queries) or edge-case (cascade cycle detection) — reinforcing that environmental is the composition layer where other layers get tested under time. Finally, `defer` items cluster on **convention/ontology** (in-place vs. node-swap, outdoor derivation, plant/terrain taxonomy); each will become a forced decision during Phase 4 mechanic authoring.
