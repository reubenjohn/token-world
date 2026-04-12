# Resource — Category Summary

**Use cases reviewed:** 7 (UC-R01..UC-R07)
**Total inline gaps:** 21
**Deduplicated gaps:** 16

## Review Findings

- **All UCs pass schema validator:** YES (UC-R01..UC-R07).
- **All UCs' `setup.graph_builder` creates every referenced actor/target:** YES. Each setup executes cleanly and every `actions[].actor` and `actions[].classified.target` resolves to a pre-created node.
- **UC status transitions:**
  - draft → reviewed: UC-R01, UC-R02, UC-R03, UC-R04, UC-R05, UC-R06, UC-R07 (all 7).
  - remaining as draft: none.
- **Cross-category clustering:** the conservation gaps (R-E01, R-M01-conservation) are the same surface UC-S04 touches in its defer row and UC-E02 touches in exclusive-target resolution. Wave 4 should consolidate conservation + mutation-atomicity into a single engine plan.

## Deduplicated Gap List

| ID | Layer | Severity | Summary | Source UCs | Proposed Fix |
|----|-------|----------|---------|------------|--------------|
| R-M01 | mechanic | address-now | No crafting mechanic; recipe-driven multi-input consumption is unsupported. | UC-R01 | Add a `craft` mechanic with a recipe registry keyed on `(tool_type, input materials)`, producing a typed output node and removing inputs. |
| R-E01 | engine | address-now | No conservation enforcement across mutations: mechanics can increment a conserved property (coin, mass, energy, nutrition) without citing a matching decrement. | UC-R01, UC-R03, UC-R07 | SIM-08 hook — every increment to a registered conserved property must cite a matching decrement on another node (or a sink entity) or be rolled back. Shared with S-M04 (AoE damage-conservation). |
| R-M02 | mechanic | address-now | No consume mechanic: can't combine `remove_node` with a property delta (hunger -= nutrition) atomically. | UC-R02 | Ship a generic `consume` mechanic parametrized by `(target_subtype=food, property=hunger, delta_from=nutrition)` so every edible reuses one mechanic. |
| R-M03 | mechanic | address-now | No transfer mechanic: no primitive for moving a scalar property from one node to another while preserving total. | UC-R03 | Ship `transfer(sender, receiver, property, amount)` mechanic that decrements sender and increments receiver in a single transaction; refuse if sender would go negative. Dual to O-M02 (give) for non-scalar items. |
| R-M04 | mechanic | address-now | Pickup mechanic ignores `inventory_cap`; it does not count outgoing `holds` edges before adding a new one. | UC-R04 | Seed pickup mechanic must count outgoing `holds` edges on the actor and refuse when count ≥ `inventory_cap`. |
| R-E02 | engine | address-now | No standard contract for a mechanic to refuse an action and produce a user-facing failure narrative — current contract assumes every action mutates state. | UC-R04, UC-R07, UC-E06 (cross-cat) | Engine must accept `(ok=False, narrative=...)` from a mechanic, leave the graph unchanged, and still return a grounded observation to the actor. Shared pattern with UC-E06 "blocked by X" narrative helper. |
| R-M05 | mechanic | address-now | No degradation/wear mechanic; using an item does not decrement durability or trigger break-at-zero. | UC-R05 | Seed a generic `wear(instrument, amount=1)` hook that `strike` and similar verbs call; add a threshold rule that sets `broken=true` at 0 durability. |
| R-M06 | mechanic | address-now | No fungibility mechanic: framework cannot pick "any subset of held coin entities whose denominations sum to amount" and transfer them. | UC-R06 | Ship `fungible_pay` mechanic that solves subset-sum over held entities of a given subtype/denomination and transfers the chosen entities; refuses if no valid subset exists. |
| R-M07 | mechanic | address-now | No framework review gate: a mechanic with `source='llm_generated'` and `reviewed=false` runs as if it were trusted first-party code. | UC-R07 | Gate mechanic execution behind `reviewed=true`; require the mechanic registry to set `reviewed=true` only after a static-analysis pass checking for unbalanced conserved-property deltas. |
| R-G01 | graph | defer | Amount-as-property (alice.coin=N) vs. amount-as-entities (one coin per node) tradeoff: ergonomic vs. individuable. No documented convention. | UC-R06, UC-O01, UC-O03 (cross-cat) | Document both representations; provide a converter helper when a mechanic needs to switch. Overlaps with O-G03. |
| R-G02 | graph | defer | No standard property vocabulary for condition tracking (durability vs. integrity vs. charges vs. uses). | UC-R05 | Document a convention for condition properties so mechanics across domains use the same names; revisit when enough examples exist. |
| R-G03 | graph | defer | No structured "contains materials of" lineage from a crafted item back to its inputs. | UC-R01 | Optional `crafted_from` provenance edge recorded by the craft mechanic for Phase 8 history queries. |
| R-G04 | graph | defer | Inventory is implicit (count of `holds` edges) rather than a first-class container; nested storage (bags-inside-bags) will need a container subtype. | UC-R04 | Phase 8: introduce `container` subtype with explicit `capacity` property and `contained_by` relation for nested storage. |
| R-M08 | mechanic | defer | No notion of partial consumption (half-eaten apple) or stacked portions. | UC-R02 | Add a `portion`/`serving` property so food can be consumed in discrete bites before being removed. |
| R-M09 | mechanic | defer | No making-change mechanic when exact payment is impossible (pay 4 with only 5s and 2s). | UC-R06 | Extend `fungible_pay` with a max-overpay tolerance and emit change-owed state. |
| R-E03 | engine | defer | Tick-driven passive degradation (rust, rot) is out of scope until SIM-09 passive-tick infrastructure lands; conserved-property registry itself is not yet defined. | UC-R05, UC-R07, UC-V03, UC-V04 (cross-cat) | Bind passive degradation to SIM-09 tick scheduler when available; ship a YAML registry of conserved properties (coin, mass, nutrition, energy) that domain plans extend. |

**Audit metadata:** 21 inline gaps across 7 UCs collapsed to 16 entries; the principal merges were (a) UC-R01 + UC-R03 + UC-R07 conservation concerns into a single R-E01 engine hook, (b) UC-R04 + UC-R07 graceful-refusal contracts into R-E02 (which also surfaces in UC-E06), and (c) UC-R05 passive-decay with UC-V03/V04 passive-tick needs into R-E03. No UC failed the runtime sanity check and no frontmatter edits were required for this category.

## Patterns Noticed

Resource UCs are the most **mechanic-heavy** of the five categories — 9 of 16 dedup'd gaps are mechanic-layer, because every resource interaction (craft, consume, transfer, pickup, wear, pay) is a missing seed. The engine gaps cluster into exactly two themes: **conservation enforcement** (R-E01) and **graceful refusal** (R-E02, already surfacing in UC-R04/R07/E06 independently). These two together cover most "the action didn't happen and the actor needs to know why" scenarios across all five categories — Wave 4 should elevate both to first-class engine primitives. The `defer` items are almost entirely **representation/vocabulary** questions (amount-as-property vs. amount-as-entity, condition property names, provenance edges) — none block v1 but each will bite consistency later if not documented now. Finally, `UC-R07` stands out as the most load-bearing edge-case UC: it is the only UC that directly exercises the mechanic-review gate (R-M07), and its failure surfaces a trust-model gap that touches every other category indirectly.
