---
phase: 03-design-validation
plan: 08
type: execute
wave: 2
depends_on: [05]
files_modified:
  - .planning/use-cases/resource/UC-R01-craft-sword-from-materials.md
  - .planning/use-cases/resource/UC-R02-consume-food.md
  - .planning/use-cases/resource/UC-R03-gift-currency.md
  - .planning/use-cases/resource/UC-R04-inventory-limit.md
  - .planning/use-cases/resource/UC-R05-degradation-over-time.md
  - .planning/use-cases/resource/UC-R06-fungible-currency.md
  - .planning/use-cases/resource/UC-R07-conservation-violation-attempt.md
autonomous: true
requirements:
  - DVAL-01
tags:
  - use-cases
  - authoring
  - resource
  - conservation

must_haves:
  truths:
    - "7 resource use case files exist (UC-R01..UC-R07), each parsing and validating"
    - "Each file's setup graph includes all referenced actors/targets"
    - "At least 4 files surface address-now gaps (crafting, inventory limits, conservation)"
    - "UC-R07 specifically stress-tests conservation violation — must have gaps mapped to SIM-08 future requirement"
  artifacts:
    - path: ".planning/use-cases/resource/UC-R01-craft-sword-from-materials.md"
      min_lines: 40
    - path: ".planning/use-cases/resource/UC-R02-consume-food.md"
      min_lines: 40
    - path: ".planning/use-cases/resource/UC-R03-gift-currency.md"
      min_lines: 40
    - path: ".planning/use-cases/resource/UC-R04-inventory-limit.md"
      min_lines: 40
    - path: ".planning/use-cases/resource/UC-R05-degradation-over-time.md"
      min_lines: 40
    - path: ".planning/use-cases/resource/UC-R06-fungible-currency.md"
      min_lines: 40
    - path: ".planning/use-cases/resource/UC-R07-conservation-violation-attempt.md"
      min_lines: 40
  key_links:
    - from: "each UC-R*.md"
      to: ".planning/use-cases/_TEMPLATE.md"
      via: "copy template, fill per resource/MANIFEST.md row"
      pattern: "category: resource"
---

<objective>
Author the 7 resource use case files pre-assigned in `.planning/use-cases/resource/MANIFEST.md`. Resource cases pressure-test conservation, inventory, crafting, currency, and degradation — all conservation-heavy scenarios that inform SIM-08.

Purpose: Surface gaps around material/energy conservation enforcement, inventory modeling, crafting recipes, and fungibility. Feeds Wave 4 gap synthesis and directly influences Phase 5 (SIM-08 conservation laws).

Output: 7 new use-case markdown files, each passing the schema validator.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/use-cases/_README.md
@.planning/use-cases/_TEMPLATE.md
@.planning/use-cases/resource/MANIFEST.md
@.planning/phases/03-design-validation/03-RESEARCH.md
@.planning/REQUIREMENTS.md
@src/token_world/use_cases/loader.py
@src/token_world/graph/knowledge_graph.py

<interfaces>
Same authoring contract as plan 06 (_README.md is authoritative). Every file:
- category: resource
- id: UC-R01..UC-R07
- status: draft
- setup.graph_builder must create every referenced node
- ≥2 graph_assertions per observation
- inline gaps as appropriate

Parallelism: 7 disjoint files — run in parallel.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author UC-R01..UC-R07 (7 resource use cases)</name>
  <files>.planning/use-cases/resource/UC-R01-craft-sword-from-materials.md, .planning/use-cases/resource/UC-R02-consume-food.md, .planning/use-cases/resource/UC-R03-gift-currency.md, .planning/use-cases/resource/UC-R04-inventory-limit.md, .planning/use-cases/resource/UC-R05-degradation-over-time.md, .planning/use-cases/resource/UC-R06-fungible-currency.md, .planning/use-cases/resource/UC-R07-conservation-violation-attempt.md</files>
  <read_first>
    - .planning/use-cases/_TEMPLATE.md
    - .planning/use-cases/_README.md
    - .planning/use-cases/resource/MANIFEST.md
    - .planning/REQUIREMENTS.md §Simulation Engine (SIM-08 conservation)
  </read_first>
  <action>
    Author each file at the exact target path. Follow plan 06 task 1's frontmatter + narrative contract.

    **Per-file scenario guidance:**

    UC-R01 (craft-sword-from-materials): Setup: alice holds iron_ingot and wood_plank, forge entity in room. Action: alice crafts sword at forge. Observation: iron_ingot + wood_plank consumed (removed from graph), sword entity added held_by alice. Gap (mechanic, address-now): no crafting mechanic; needs recipe registry. Gap (engine, address-now): conservation — total mass/value before = after.

    UC-R02 (consume-food): Setup: alice holds apple, alice has `hunger=80`. Action: alice eats apple. Observation: apple removed, alice's `hunger` reduced. Gap (mechanic, address-now): consume mechanic. Gap: simple — may be implementable with existing primitives, flag ambiguity.

    UC-R03 (gift-currency): Setup: alice has `coin=10`, bob has `coin=0`. Action: alice gives 5 coin to bob. Observation: alice.coin=5, bob.coin=5. Gap (engine, address-now): indirect object (bob). Gap (mechanic, address-now): transfer mechanic; conservation check (10 = 5 + 5).

    UC-R04 (inventory-limit): Setup: alice has `inventory_cap=10`, already holds 10 items. Action: alice picks up an 11th. Observation: action fails; narrative explains inventory full; graph unchanged. Gap (mechanic, address-now): inventory-limit enforcement in pickup mechanic. Gap (engine, address-now): graceful action-rejection with user-facing narrative.

    UC-R05 (degradation-over-time): Setup: sword with `durability=3`. Action: alice uses sword 3 times (3 actions). Observation: durability 3→2→1→0; on 0, sword becomes `broken=true` or removed. Gap (mechanic, address-now): degradation mechanic; per-use hook. Gap (engine, defer): passive-time mechanics (tie to Phase 7 SIM-09).

    UC-R06 (fungible-currency): Setup: alice has coin entities of denominations 5, 2, 1 (mixed representation). Action: alice pays 7 coin. Observation: any valid combination (5+2, or 5+1+1, or 2+2+2+1) is accepted; balance drops by 7. Gap (mechanic, address-now): fungibility — currency should be aggregated, not per-coin-entity. Gap (graph, defer): amount-as-property vs amount-as-node-count tension.

    UC-R07 (conservation-violation-attempt): Setup: an LLM-generated mechanic attempts to add 1000 coin to alice with no source. Action: trigger this mechanic. Observation: engine rejects the mutation; narrative notes violation; graph unchanged. Gap (engine, address-now): SIM-08 conservation enforcement — every `add_property` delta to a conserved property (coin, mass, energy) must cite a source deletion of equal magnitude. Gap (mechanic, address-now): framework-level conservation checker hook.

    Each file ≥40 lines, passes validator. At least 4 files must have gaps with severity=address-now. UC-R07 must explicitly mention SIM-08 in its gap `proposed_fix` text (traceability to requirements).
  </action>
  <verify>
    <automated>uv run pytest tests/test_design_validation/test_use_case_schema.py -v && python3 -c "
from pathlib import Path
from token_world.use_cases import load_use_case, validate_frontmatter
files = sorted(Path('.planning/use-cases/resource').glob('UC-R*.md'))
assert len(files) == 7, f'expected 7, got {len(files)}'
errs = []
for f in files:
    fm, body = load_use_case(f)
    errs.extend(validate_frontmatter(fm, source=str(f)))
    if '## Vignette' not in body: errs.append(f'{f}: missing ## Vignette')
assert not errs, '\n'.join(errs)
addr = sum(1 for f in files for fm, _ in [load_use_case(f)] for g in fm.get('gaps', []) if g.get('severity') == 'address-now')
assert addr >= 4, f'expected >=4 address-now gaps, got {addr}'
# UC-R07 must reference SIM-08
uc_r07 = Path('.planning/use-cases/resource/UC-R07-conservation-violation-attempt.md').read_text()
assert 'SIM-08' in uc_r07, 'UC-R07 must cite SIM-08 in its gap analysis'
print(f'ok 7 resource UCs, {addr} address-now gaps, UC-R07 cites SIM-08')
"</automated>
  </verify>
  <acceptance_criteria>
    - 7 target files exist at the manifest paths
    - All pass validate_frontmatter
    - All have Vignette + Why-this-matters sections
    - Every actor/target appears in corresponding setup.graph_builder
    - ≥4 files have address-now gaps
    - UC-R07 references SIM-08 in text (traceability to Phase 5 requirement)
    - All files ≥40 lines
  </acceptance_criteria>
  <done>7 resource UCs authored; conservation + crafting + inventory gaps surfaced.</done>
</task>

</tasks>

<threat_model>
Same as plan 06 — author-controlled in-repo. T-03-01 accepted.
</threat_model>

<verification>
- 7 files exist, validate green, schema test passes
- UC-R07 explicitly cites SIM-08
- ≥4 address-now gaps
</verification>

<success_criteria>
1. All 7 resource UC files exist and validate.
2. UC-R07 cites SIM-08 (requirement traceability).
3. At least 4 files contribute address-now gaps.
4. Setup graphs are self-contained (no dangling references).
</success_criteria>

<output>
Create `.planning/phases/03-design-validation/03-08-SUMMARY.md` listing UC-R0X entries, titles, and the conservation-related gaps surfaced (Phase 5 input).
</output>
