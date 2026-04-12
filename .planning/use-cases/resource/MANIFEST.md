# Resource Use Cases — Manifest

Resource is the conservation-heavy category: crafting, consumption, gifting,
currency, inventory caps, degradation, fungibility, and conservation-violation
attempts. Every case exercises the "mass/energy conservation" invariant we
want the engine to enforce — either by providing a mechanic that upholds it
or by surfacing a gap where a naive generated mechanic could break it.

| ID     | Slug                              | Title                                | Scenario (one line)                                                                          | No seed mechanic? | Notes                                                                              |
|--------|-----------------------------------|--------------------------------------|----------------------------------------------------------------------------------------------|--------------------|------------------------------------------------------------------------------------|
| UC-R01 | craft-sword-from-materials        | Craft sword from materials           | Alice combines iron and wood at a forge to craft a sword.                                    | YES                | Needs multi-input crafting mechanic; no seed covers material consumption.          |
| UC-R02 | consume-food                      | Consume food                         | Alice eats an apple; apple is removed, hunger drops.                                         | YES                | Tests remove_node + property update in a single mechanic.                          |
| UC-R03 | gift-currency                     | Gift currency                        | Alice gives bob 5 coin.                                                                      | YES                | Fungible transfer; exercises property-equals delta checks.                         |
| UC-R04 | inventory-limit                   | Inventory limit                      | Alice tries to pick up an 11th item when inventory cap is 10.                                | YES                | Needs precondition failure + observation of refusal; no inventory mechanic yet.    |
| UC-R05 | degradation-over-time             | Degradation over time                | Alice's sword loses 1 durability per use; breaks at 0.                                       | YES                | Needs periodic/tick-driven mechanic + threshold behavior.                          |
| UC-R06 | fungible-currency                 | Fungible currency                    | Alice pays 7 coin; can be any combination of denominations.                                  | YES                | Tests fungibility abstraction — single scalar vs discrete tokens.                  |
| UC-R07 | conservation-violation-attempt    | Conservation violation attempt       | An LLM generates a mechanic that creates coin from nothing; must be rejected.                | YES                | Engine-layer: needs mechanic-review gate that detects unbalanced add_node.         |

## Wave 2 Authoring Checklist

- [ ] `.planning/use-cases/resource/UC-R01-craft-sword-from-materials.md`
- [ ] `.planning/use-cases/resource/UC-R02-consume-food.md`
- [ ] `.planning/use-cases/resource/UC-R03-gift-currency.md`
- [ ] `.planning/use-cases/resource/UC-R04-inventory-limit.md`
- [ ] `.planning/use-cases/resource/UC-R05-degradation-over-time.md`
- [ ] `.planning/use-cases/resource/UC-R06-fungible-currency.md`
- [ ] `.planning/use-cases/resource/UC-R07-conservation-violation-attempt.md`
