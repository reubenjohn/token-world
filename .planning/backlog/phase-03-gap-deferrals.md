# Deferred from Phase 3

## Deferred from Phase 3

**Source:** `.planning/GAP-ANALYSIS.md`
**Created:** 2026-04-12
**Count:** 16

These gaps were surfaced in Phase 3 gap analysis but deferred to a later milestone per D-06 (three-way disposition). They cluster on vocabulary consistency, v2 multi-agent concerns, and narrow mechanic enrichments that can wait until v1 usage surfaces concrete need.

| Gap ID | Summary | Source UCs | Why Deferred | Candidate Milestone |
|--------|---------|------------|--------------|--------------------|
| GAP-GRAPH06 | No first-class portal/passage vocabulary; doorways are ad-hoc `subtype='doorway'` entities. | UC-S01 | Vocabulary consistency — wait until v1 usage surfaces concrete need | v2 |
| GAP-GRAPH07 | No canonical terrain typing (water/wall/floor/bridge/stair); `traversable` and `terrain_type` are ad-hoc per UC. | UC-S06, UC-V05, UC-V02, UC-V04 | Cross-category ontology question; defer until Phase 4 mechanic authoring forces the decision | v2 |
| GAP-GRAPH08 | Containment split across `inside` vs `located_in`; no `containment_chain(node)` helper for uniform traversal. | UC-S05 | Vocabulary consistency; narrow helper, ship when needed | v2 |
| GAP-GRAPH09 | No canonical `position_of(node)` accessor; entities expose centroid ad-hoc. | UC-S07 | Ergonomic helper; defer until multiple mechanics need it | v2 |
| GAP-GRAPH10 | Amount-as-property vs amount-as-entities (fungible currency, mass, nutrition) has no documented convention. | UC-O01, UC-R06, UC-O03 | Cross-cutting representation tradeoff; revisit when Phase 4 authoring produces concrete cases | v2 |
| GAP-GRAPH11 | No reputation/relationship edges between agent pairs; persuasion and belief mechanics lack a trust modifier input. | UC-O02, UC-O04 | Requires v2 multi-agent — single-agent v1 doesn't exercise reputation graphs | v2 |
| GAP-GRAPH12 | No standard vocabulary for condition tracking (durability / integrity / charges / uses). | UC-R05 | Vocabulary consistency; wait for multiple examples | v2 |
| GAP-GRAPH13 | No `crafted_from` provenance edge from crafted items back to inputs (lineage for Phase 8 history queries). | UC-R01 | Scheduled for Phase 8+ history tooling | v2 |
| GAP-GRAPH14 | No first-class `container` subtype with explicit `capacity` + nested `contained_by`; inventory is implicit `holds`-edge count. | UC-R04 | Phase 8 inventory enrichment; v1 `holds` count suffices | v2 |
| GAP-GRAPH15 | `outdoor=True` is per-entity rather than derived through containment; weather reactions can't walk the containment chain. | UC-V02 | Overlaps with GAP-GRAPH08 containment helper; ship together when needed | v2 |
| GAP-GRAPH16 | No convention for in-place property transformation (`rotten=true`) vs. node-swap (remove + add); authors may diverge. | UC-V03 | Documentation/convention gap; resolve during Phase 4 mechanic authoring | v2 |
| GAP-GRAPH17 | Graph API lacks transactional/compare-and-swap primitive for protecting shared-resource mutations against interleaving. | UC-E02 | Single-agent v1 doesn't interleave; required for v2 multi-agent | v2 |
| GAP-GRAPH18 | Door state has no canonical representation (door-as-entity vs. `connects`-edge property); convention undocumented. | UC-E06 | Convention documentation; resolve during Phase 4 mechanic authoring | v2 |
| GAP-MECH28 | No partial / portioned consumption (half-eaten apple, discrete bites before removal). | UC-R02 | Narrow enrichment; ship when authoring needs it | v2 |
| GAP-MECH29 | No making-change in `fungible_pay` when exact payment is impossible (pay 4 with 5s and 2s, change owed). | UC-R06 | Enrichment of GAP-MECH18; defer until commerce is exercised | v2 |
| GAP-ENG19 | Multi-party commit / consent / listener-reaction primitive: no way for target/recipient to refuse before commit; no atomic precondition check across multi-actor mechanics; no listener-next-tick reaction hook. | UC-O03, UC-O06, UC-O08, UC-E03, UC-E05, UC-E06 | Engine UX hardening; observer-belief propagation is v2 multi-agent territory | v2 |

---
*Backlog derived deterministically from `.planning/GAP-ANALYSIS.md` — 2026-04-12*
