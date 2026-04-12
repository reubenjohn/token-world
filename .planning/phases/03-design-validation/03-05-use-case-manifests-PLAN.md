---
phase: 03-design-validation
plan: 05
type: execute
wave: 1
depends_on: [01]
files_modified:
  - .planning/use-cases/_README.md
  - .planning/use-cases/_TEMPLATE.md
  - .planning/use-cases/spatial/MANIFEST.md
  - .planning/use-cases/social/MANIFEST.md
  - .planning/use-cases/resource/MANIFEST.md
  - .planning/use-cases/environmental/MANIFEST.md
  - .planning/use-cases/edge-case/MANIFEST.md
autonomous: true
requirements:
  - DVAL-01
tags:
  - use-cases
  - manifests
  - scaffolding

must_haves:
  truths:
    - ".planning/use-cases/ exists with five category subfolders and a README explaining the format"
    - "Each category has a MANIFEST.md listing every UC ID, title, one-line scenario, and a 'no-seed-mechanic?' flag (at least one YES per category, per D-03)"
    - "Total manifest entries sum to 35 (spatial=7, social=8, resource=7, environmental=7, edge-case=6)"
    - "Every UC ID follows the pattern UC-[SOVRE]NN and IDs are unique"
    - "Template file shows the exact frontmatter shape that validate_frontmatter accepts"
  artifacts:
    - path: ".planning/use-cases/_README.md"
      provides: "Format spec, ID scheme, authoring workflow, gap taxonomy"
      min_lines: 60
    - path: ".planning/use-cases/_TEMPLATE.md"
      provides: "Copy-pastable template with every frontmatter key + narrative sections"
      min_lines: 50
    - path: ".planning/use-cases/spatial/MANIFEST.md"
      provides: "7 entries UC-S01..UC-S07"
      min_lines: 25
    - path: ".planning/use-cases/social/MANIFEST.md"
      provides: "8 entries UC-O01..UC-O08"
      min_lines: 28
    - path: ".planning/use-cases/resource/MANIFEST.md"
      provides: "7 entries UC-R01..UC-R07"
      min_lines: 25
    - path: ".planning/use-cases/environmental/MANIFEST.md"
      provides: "7 entries UC-V01..UC-V07"
      min_lines: 25
    - path: ".planning/use-cases/edge-case/MANIFEST.md"
      provides: "6 entries UC-E01..UC-E06"
      min_lines: 22
  key_links:
    - from: ".planning/use-cases/*/MANIFEST.md"
      to: ".planning/use-cases/_TEMPLATE.md"
      via: "Wave 2 authors copy template and fill per manifest row"
      pattern: "UC-[SOVRE]"
    - from: ".planning/use-cases/_README.md"
      to: "src/token_world/use_cases/loader.py"
      via: "README documents the exact keys validate_frontmatter enforces"
      pattern: "REQUIRED_KEYS"
---

<objective>
Create the use-case library skeleton — README, template, and five per-category MANIFEST.md files that pre-assign stable UC IDs and scenario one-liners. These manifests are the contract that Wave 2 authoring plans execute against: each row becomes exactly one authored file.

Purpose: Eliminate write-collision risk in Wave 2 (each author owns exactly one file path, pre-decided here). Ensures category balance (7/8/7/7/6 = 35, per RESEARCH.md). Surfaces no-seed-mechanic cases per D-03.

Output: 7 new markdown files; no code changes.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/03-design-validation/03-CONTEXT.md
@.planning/phases/03-design-validation/03-RESEARCH.md
@src/token_world/use_cases/loader.py
@src/token_world/mechanic/seeds/movement/mechanic.py
@src/token_world/mechanic/seeds/observation/mechanic.py
@src/token_world/mechanic/seeds/environmental_reaction/mechanic.py

<interfaces>
Required frontmatter keys (from loader.py REQUIRED_KEYS):
id, category, title, status, setup, actions, expected_observations, gaps

ID scheme:
- S = spatial → UC-S01..UC-S07
- O = social/Other-agent → UC-O01..UC-O08
- R = resource → UC-R01..UC-R07
- V = enVironmental → UC-V01..UC-V07
- E = edge-case → UC-E01..UC-E06

Existing seed mechanics (for no-matching-mechanic tagging): movement, observation, environmental_reaction.

Valid gap layers: graph, mechanic, engine.
Valid gap severities: address-now, defer, out-of-scope.
Valid statuses: draft, reviewed, locked.
Valid graph_assertion kinds (documented in _README.md): has_node, has_edge, not_has_edge, has_property, property_equals, not_has_property.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write _README.md and _TEMPLATE.md</name>
  <files>.planning/use-cases/_README.md, .planning/use-cases/_TEMPLATE.md</files>
  <read_first>
    - .planning/phases/03-design-validation/03-RESEARCH.md §Use Case Library Format, §Authoring Template, §Gap Analysis
    - src/token_world/use_cases/loader.py (authoritative on required keys and valid enum values)
  </read_first>
  <action>
    Create `.planning/use-cases/_README.md` with sections (in this order):
    1. `# Token World Use Case Library` — 2-paragraph purpose statement (pressure-test framework; feed gap analysis; produce Phase 6 regression spec)
    2. `## How to author a new use case` — numbered steps: copy `_TEMPLATE.md` to `<category>/UC-XX-<slug>.md`, fill frontmatter, write narrative, add inline gaps, run `uv run pytest tests/test_design_validation/test_use_case_schema.py -v`
    3. `## ID scheme` — table: category → letter → range
    4. `## Required frontmatter keys` — table listing every key validator enforces with description (`id`, `category`, `title`, `status`, `setup.graph_builder`, `actions[]`, `expected_observations[]`, `gaps[]` and each gap's required sub-keys: layer, severity, summary, proposed_fix)
    5. `## Gap taxonomy` — 3 layers (graph / mechanic / engine) and 3 severities (address-now / defer / out-of-scope) with when to use each
    6. `## Structured action format` — document `{actor, intent, classified: {verb, target, ...}}`
    7. `## Structured observation format` — document `{actor, narrative_contains: [str], graph_assertions: [{kind, ...}]}` and list the fixed vocabulary of assertion kinds: has_node, has_edge, not_has_edge, has_property, property_equals, not_has_property
    8. `## Status lifecycle` — draft (author) → reviewed (Wave 3) → locked (Phase 6 regression)
    9. `## Authoring trust model` — `setup.graph_builder` is Python executed by the Phase 6 regression harness. Treat use cases as committed code, not data. No user input crosses this boundary.

    Create `.planning/use-cases/_TEMPLATE.md` — a copy-pastable file mirroring the example in RESEARCH.md §Use case file template. Use `id: UC-XX00` placeholder. Include every required frontmatter key plus at least one example `graph_assertion` of each of the six supported kinds. End with the three narrative sections: `# UC-XX00: Title`, `## Vignette`, `## Why this matters`, `## Related use cases`.

    Both files must be valid markdown; _TEMPLATE.md must parse as YAML frontmatter when split on `---\n`.
  </action>
  <verify>
    <automated>test -f .planning/use-cases/_README.md && test -f .planning/use-cases/_TEMPLATE.md && python3 -c "from pathlib import Path; t = Path('.planning/use-cases/_TEMPLATE.md').read_text(); assert t.startswith('---'); import yaml; parts = t.split('---\n', 2); yaml.safe_load(parts[1]); print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `wc -l .planning/use-cases/_README.md` ≥ 60
    - `wc -l .planning/use-cases/_TEMPLATE.md` ≥ 50
    - `grep -c "^## " .planning/use-cases/_README.md` ≥ 7
    - `_TEMPLATE.md` starts with `---\n` and contains valid YAML frontmatter (parses via yaml.safe_load)
    - `grep -q "has_node\|has_edge\|property_equals" .planning/use-cases/_TEMPLATE.md` passes (assertion kinds listed)
    - `grep -q "address-now" .planning/use-cases/_TEMPLATE.md` passes
  </acceptance_criteria>
  <done>Authors in Wave 2 can copy _TEMPLATE.md and fill it; _README.md answers every "how do I" question without reading source.</done>
</task>

<task type="auto">
  <name>Task 2: Write the 5 category MANIFEST.md files (pre-assign all 35 UC IDs)</name>
  <files>.planning/use-cases/spatial/MANIFEST.md, .planning/use-cases/social/MANIFEST.md, .planning/use-cases/resource/MANIFEST.md, .planning/use-cases/environmental/MANIFEST.md, .planning/use-cases/edge-case/MANIFEST.md</files>
  <read_first>
    - .planning/use-cases/_README.md (Task 1 output — authoritative on ID scheme)
    - .planning/phases/03-design-validation/03-RESEARCH.md §Use Case Distribution (rationale per category)
    - src/token_world/mechanic/seeds/movement/mechanic.py (to judge which scenarios the seed covers)
    - src/token_world/mechanic/seeds/observation/mechanic.py
    - src/token_world/mechanic/seeds/environmental_reaction/mechanic.py
  </read_first>
  <action>
    Each MANIFEST.md uses the same structure:
    ```
    # <Category> Use Cases — Manifest

    <2-3 line rationale for this category's focus>

    | ID | Slug | Title | Scenario (one line) | No seed mechanic? | Notes |
    |----|------|-------|---------------------|--------------------|-------|
    | UC-X01 | slug | Title | ... | no/YES | ... |
    ```

    Assign the following (propose these exact IDs + titles — authors in Wave 2 may refine the scenario text but must keep the ID + slug):

    **spatial/MANIFEST.md (7 cases):**
    - UC-S01 movement-through-doorway — "Alice walks east through a doorway into an adjacent room." — no (movement covers basic case, but through-entity-typed-doorway may surface a gap)
    - UC-S02 line-of-sight-occlusion — "Alice tries to observe bob in an adjacent room; a wall occludes." — YES
    - UC-S03 nearest-object-query — "Alice asks for the nearest weapon." — YES (requires spatial index)
    - UC-S04 area-of-effect — "An explosion at [5,5] damages all entities within radius 3." — YES
    - UC-S05 containment-hierarchy — "Sword is inside chest which is inside room_a; describing sword involves a chain." — YES
    - UC-S06 traversal-across-terrain — "Alice crosses a river via a bridge." — YES
    - UC-S07 position-updating-on-move — "After movement, alice's position reflects her new room's centroid." — no (if movement updates position)

    **social/MANIFEST.md (8 cases):**
    - UC-O01 trade-negotiation — "Alice offers bob a sword for 10 coin." — YES
    - UC-O02 persuasion-check — "Alice tries to convince bob to unlock a door." — YES
    - UC-O03 give-sword-to-bob — "Multi-object: alice gives the sword to bob." — YES (tests indirect-object modeling)
    - UC-O04 deception — "Alice tells bob the chest is empty when it isn't." — YES
    - UC-O05 teaching — "Alice teaches bob how to use a lockpick." — YES
    - UC-O06 cooperation-lift-heavy — "Alice and bob lift a boulder together." — YES
    - UC-O07 observation-of-agent — "Alice looks at bob and observes bob's visible state." — no (observation seed covers partial)
    - UC-O08 speech-broadcast — "Alice shouts; all agents within earshot hear." — YES (needs spatial + social)

    **resource/MANIFEST.md (7 cases):**
    - UC-R01 craft-sword-from-materials — "Alice combines iron and wood at a forge to craft a sword." — YES
    - UC-R02 consume-food — "Alice eats an apple; apple is removed, hunger drops." — YES
    - UC-R03 gift-currency — "Alice gives bob 5 coin." — YES
    - UC-R04 inventory-limit — "Alice tries to pick up an 11th item when inventory cap is 10." — YES
    - UC-R05 degradation-over-time — "Alice's sword loses 1 durability per use; breaks at 0." — YES
    - UC-R06 fungible-currency — "Alice pays 7 coin; can be any combination of denominations." — YES
    - UC-R07 conservation-violation-attempt — "An LLM generates a mechanic that creates coin from nothing; must be rejected." — YES

    **environmental/MANIFEST.md (7 cases):**
    - UC-V01 fire-spread — "Fire on torch spreads to adjacent flammable wooden table." — no (environmental_reaction covers basic spread)
    - UC-V02 weather-change — "Rain begins; outdoor entities become wet; fire extinguishes." — YES
    - UC-V03 decay — "Uneaten apple rots after N ticks into rotten_apple." — YES
    - UC-V04 seasons — "Season advances from summer to autumn; trees shed leaves." — YES
    - UC-V05 terrain-effect — "Alice in swamp moves at half speed." — YES
    - UC-V06 light-and-dark — "Alice in a dark room can't observe entities unless she has a torch." — YES
    - UC-V07 contagion — "Bob contracts a cold from alice; symptoms cascade." — YES

    **edge-case/MANIFEST.md (6 cases):**
    - UC-E01 action-against-nonexistent-target — "Alice attacks a dragon; no dragon exists in graph." — YES (tests engine error handling)
    - UC-E02 concurrent-actors — "Alice and bob both try to pick up the last apple on the same tick." — YES (turn ordering; v1 deferrable)
    - UC-E03 partial-knowledge — "Alice tries to open a locked chest she doesn't know is locked." — YES
    - UC-E04 nonsense-input — "Alice says 'gragh flibble xyzzy'; engine must respond coherently." — YES
    - UC-E05 circular-chain — "Mechanic A triggers B triggers A; engine must detect and break the cycle." — YES
    - UC-E06 move-into-locked-room — "Alice tries to walk through a locked door." — YES

    Each MANIFEST also ends with a "## Wave 2 Authoring Checklist" listing the slugs and the full file path each author must produce, e.g. `.planning/use-cases/spatial/UC-S01-movement-through-doorway.md`.

    At least one "YES" in every category (D-03 satisfied). Counts verify: 7+8+7+7+6 = 35.
  </action>
  <verify>
    <automated>for cat in spatial social resource environmental edge-case; do test -f .planning/use-cases/$cat/MANIFEST.md || { echo "MISSING $cat"; exit 1; }; done && python3 -c "
import re
from pathlib import Path
expected = {'spatial': ('S', 7), 'social': ('O', 8), 'resource': ('R', 7), 'environmental': ('V', 7), 'edge-case': ('E', 6)}
all_ids = []
for cat, (letter, count) in expected.items():
    text = Path(f'.planning/use-cases/{cat}/MANIFEST.md').read_text()
    ids = re.findall(rf'UC-{letter}\d{{2}}', text)
    unique = sorted(set(ids))
    assert len(unique) == count, f'{cat}: expected {count} unique UC-{letter}NN ids, got {len(unique)}: {unique}'
    all_ids.extend(unique)
    # At least one YES (no-seed-mechanic flag)
    assert 'YES' in text, f'{cat}: missing at least one YES (no-seed-mechanic) per D-03'
assert len(all_ids) == len(set(all_ids)) == 35, f'collisions or wrong total: {len(all_ids)} unique={len(set(all_ids))}'
print('ok 35 unique UC ids across 5 manifests')
"</automated>
  </verify>
  <acceptance_criteria>
    - 5 MANIFEST.md files exist, one per category
    - Each file contains exactly the expected count of UC IDs (7/8/7/7/6) matching the category letter
    - Total = 35 unique UC IDs across all manifests
    - Each manifest has at least one "YES" (no-seed-mechanic) row (D-03)
    - Each manifest includes a Wave 2 authoring checklist listing the exact target file path for every UC
    - `grep -q "UC-S01-movement-through-doorway" .planning/use-cases/spatial/MANIFEST.md` passes (predicted path format)
  </acceptance_criteria>
  <done>All 35 use cases are pre-assigned with stable IDs, titles, slugs, and target file paths. Wave 2 can fan out in parallel with zero collisions.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

None. All files are author-controlled markdown in-repo; no executable code, no external input.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03-01 | Tampering | Use-case manifests | accept | Committed in-repo, same trust level as test code. Reviewed by Wave 3 category aggregator. |
</threat_model>

<verification>
- 5 MANIFEST.md files + _README.md + _TEMPLATE.md exist
- 35 unique UC IDs pre-assigned
- At least one no-seed-mechanic flag per category
- Total distribution 7/8/7/7/6 confirmed
</verification>

<success_criteria>
1. `_README.md` documents authoring workflow, ID scheme, and gap taxonomy — readable without consulting other files.
2. `_TEMPLATE.md` is copy-pastable and validates against `validate_frontmatter` when filled with dummy values.
3. Every category manifest lists its exact UC set with stable IDs matching the letter convention.
4. 35 IDs total, unique, distributed 7/8/7/7/6.
5. Each category has at least one case flagged as lacking a seed mechanic (D-03).
</success_criteria>

<output>
After completion, create `.planning/phases/03-design-validation/03-05-SUMMARY.md` listing the 35 UC IDs (grouped by category) and noting which ones are "no seed mechanic" → these will be the primary gap-discovery candidates in Wave 2 authoring.
</output>
