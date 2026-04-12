# Social — Category Summary

**Use cases reviewed:** 8 (UC-O01..UC-O08)
**Total inline gaps:** 24
**Deduplicated gaps:** 18

## Review Findings

- **All UCs pass schema validator:** YES (UC-O01..UC-O08).
- **All UCs' `setup.graph_builder` creates every referenced actor/target:** YES after adding `validator_exception: target_may_not_exist` to **UC-O05**. UC-O05's classified target `lockpicking` is deliberately a bare string because the UC's own engine-layer gap documents that skills should be nodes rather than free-form strings; the exception marker formalizes that gap-as-test-condition, consistent with the UC-E01 pattern.
- **UC status transitions:**
  - draft → reviewed: UC-O01, UC-O02, UC-O03, UC-O04, UC-O05, UC-O06, UC-O07, UC-O08 (all 8).
  - remaining as draft: none.
- **Documented deviation:** one UC file (UC-O05) had its frontmatter augmented with a single new key (`validator_exception`) — see also UC-E01 where the same exception is standard. This is the only content touch across Wave 3 aggregation.

## Deduplicated Gap List

| ID | Layer | Severity | Summary | Source UCs | Proposed Fix |
|----|-------|----------|---------|------------|--------------|
| O-M01 | mechanic | address-now | No trade/exchange mechanic — transactional swap of held items and coin is not expressible today. | UC-O01 | Add a `trade` mechanic with atomic two-sided commit: precondition both parties agree + items present; side effect swaps `held_by` edges and adjusts inventory counts. |
| O-E01 | engine | address-now | Classifier has no multi-turn offer/accept protocol; each turn is interpreted in isolation. | UC-O01 | Introduce a pending-offer state on the offering agent; let the classifier resolve `accept` intents against the most recent open offer directed at the speaker. |
| O-E02 | engine | address-now | Classifier has no `indirect_object` field; ditransitive verbs (give/teach/show/tell) cannot structurally distinguish direct object from recipient. | UC-O03, UC-O05, UC-R03 (cross-cat) | Extend classified-action schema with an optional `indirect_object` key; teach the classifier prompt to populate it for ditransitive verbs. |
| O-M02 | mechanic | address-now | No transfer/give mechanic — even a one-sided hand-off of a held item is not expressible. | UC-O03, UC-R03 (cross-cat) | Add a `give` mechanic: precondition `held_by(target, actor)` and co-located actor/recipient; side effect rewrites `held_by(target, recipient)`. Overlaps with UC-R03's scalar-transfer mechanic — share the conservation-preserving transfer primitive. |
| O-E03 | engine | address-now | Persuasion/social-check outcomes are probabilistic; the engine has no model for LLM-adjudicated resolution beyond deterministic mechanics. | UC-O02 | Add an `llm_adjudicated` mechanic category that lets a seed LLM decide success/failure from disposition/charisma/argument quality, then deterministically applies the chosen side effect. |
| O-M03 | mechanic | address-now | No persuade/convince mechanic; agents lack mutable disposition properties that other agents can influence. | UC-O02 | Ship a `persuade` mechanic that reads target `disposition` and optional `charisma`, writing either a side-effect mutation (unlock) or a disposition shift. |
| O-M04 | mechanic | address-now | No belief-tracking mechanic; per-agent mental models cannot diverge from ground truth. | UC-O04, UC-E03 (cross-cat) | Add a `tell` mechanic that writes into `beliefs[listener][claim_subject]=claim_value` independent of whether the claim matches reality. |
| O-G01 | graph | address-now | Ground truth and per-agent beliefs share the same node properties, so a lie overwrites reality instead of diverging from it. | UC-O04, UC-E03 (cross-cat) | Model beliefs as a `beliefs` dict keyed by other node IDs (or as belief-edges) so e.g. `bob.beliefs[chest]={contents: []}` can coexist with `chest.contents=[coin:100]`. |
| O-M05 | mechanic | address-now | No teach/learn mechanic; `knows_skill` is a plain list and nothing copies entries from one agent to another under the right preconditions. | UC-O05 | Add a `teach` mechanic with precondition `skill in actor.knows_skill` and co-located actor/recipient; side effect appends to `recipient.knows_skill` if absent. |
| O-E04 | engine | address-now | Skill/concept names are bare strings, not nodes — classifier cannot disambiguate "teach a skill" from "teach about a person" or "teach a song". | UC-O05 | Introduce `skill` entity nodes (or a skills namespace) so `teach`-family actions can name a target skill node rather than a free-form string. |
| O-E05 | engine | address-now | Tick loop interprets each agent's intent independently; no way to fuse compatible intents into a multi-actor mechanic call. | UC-O06 | Add an intent-matching pre-pass that detects complementary `co_actors` across intents in the same tick and dispatches a single multi-actor mechanic. |
| O-M06 | mechanic | address-now | No cooperative-action mechanic; the mechanic API assumes a single `actor` and cannot express summed-capability preconditions. | UC-O06 | Extend the mechanic framework to accept `actors: list[NodeId]` and provide `sum_property(actors, prop)` for summed-capability checks. |
| O-E06 | engine | address-now | Observation seed exposes every property on the target node indiscriminately — there is no notion of public vs. private vs. inspection-required visibility. | UC-O07, UC-V06 (cross-cat) | Tag each property (or each mechanic that writes it) with a visibility class (`public`, `private`, `requires_inspection`); observation seed filters by class when projecting the target. |
| O-G02 | graph | address-now | No earshot/range query; positions exist but no helper enumerates agents within a radius, let alone with sound-blocking entities. | UC-O08 | Add `kg.agents_within(origin, radius, occluders=...)` as a graph primitive, composable with `blocks_sound=True` entities for occlusion. Overlaps with S-G03 (`ctx.spatial.within`) — likely the same query surface. |
| O-M07 | mechanic | address-now | No speech-propagation mechanic; utterances are heard by nobody or everybody. | UC-O08 | Ship a `speak` mechanic that takes a volume parameter, queries `agents_within(speaker, radius_for(volume), occluders=walls)`, and emits narrative observations only for those listeners. |
| O-G03 | graph | defer | Fungible currency represented as `inventory=["coin:10"]` strings does not support arithmetic queries. | UC-O01, UC-R06 (cross-cat) | Promote fungible resources to first-class nodes with a `quantity` property. See R-G01 for the dual amount-as-property vs. amount-as-entities tradeoff. |
| O-G04 | graph | defer | Reputation/relationship edges (alice→bob, trust=X) are not modeled. | UC-O02, UC-O04 | Add `trust`/`relation` edges between agent pairs; persuasion/belief mechanics read them as a modifier. |
| O-E07 | engine | defer | Cross-cutting: consent, partial-failure rollback, and listener reactions. No way for target/recipient to refuse before commit; no atomic precondition check across multi-actor mechanics; no hook for listener-next-tick reaction to speech/teaching. | UC-O03, UC-O06, UC-O08 | Group under a "multi-party commit" engine primitive: evaluate all preconditions atomically before any side effect; queue listener-perception events for next-tick response. |

## Patterns Noticed

Social UCs concentrate almost entirely at the **mechanic** and **engine** layers — only two graph-layer gaps are address-now. The recurring theme is that social interaction requires **pairs of actors**, which breaks both the classifier schema (no `indirect_object`, O-E02) and the mechanic API (single-`actor` assumption, O-M06). Belief divergence (O-M04/O-G01) and visibility filtering (O-E06) together form an "epistemic layer" that spans social, environmental (UC-V06 light), and edge-case (UC-E03 partial knowledge) — Wave 4 should consider a unified "observation projection / belief model" plan. Finally, several gaps surface a tradeoff the project has not yet resolved: **things-as-strings vs. things-as-nodes** (skills in O-E04, currency in O-G03, concepts in UC-O05). A single decision in ARCHITECTURE.md could retire several of these gaps at once.
