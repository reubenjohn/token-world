---
phase: 03-design-validation
plan: 09
type: execute
wave: 2
depends_on: [05]
files_modified:
  - .planning/use-cases/environmental/UC-V01-fire-spread.md
  - .planning/use-cases/environmental/UC-V02-weather-change.md
  - .planning/use-cases/environmental/UC-V03-decay.md
  - .planning/use-cases/environmental/UC-V04-seasons.md
  - .planning/use-cases/environmental/UC-V05-terrain-effect.md
  - .planning/use-cases/environmental/UC-V06-light-and-dark.md
  - .planning/use-cases/environmental/UC-V07-contagion.md
autonomous: true
requirements:
  - DVAL-01
tags:
  - use-cases
  - authoring
  - environmental

must_haves:
  truths:
    - "7 environmental use case files exist (UC-V01..UC-V07), each parsing and validating"
    - "Each file's setup graph includes all referenced actors/targets"
    - "At least 4 files surface address-now gaps (environmental mechanics are chain-heavy)"
    - "UC-V01 references environmental_reaction seed; other UCs flag what the seed does not cover"
  artifacts:
    - path: ".planning/use-cases/environmental/UC-V01-fire-spread.md"
      min_lines: 40
    - path: ".planning/use-cases/environmental/UC-V02-weather-change.md"
      min_lines: 40
    - path: ".planning/use-cases/environmental/UC-V03-decay.md"
      min_lines: 40
    - path: ".planning/use-cases/environmental/UC-V04-seasons.md"
      min_lines: 40
    - path: ".planning/use-cases/environmental/UC-V05-terrain-effect.md"
      min_lines: 40
    - path: ".planning/use-cases/environmental/UC-V06-light-and-dark.md"
      min_lines: 40
    - path: ".planning/use-cases/environmental/UC-V07-contagion.md"
      min_lines: 40
  key_links:
    - from: "each UC-V*.md"
      to: ".planning/use-cases/_TEMPLATE.md"
      via: "copy template, fill per environmental/MANIFEST.md row"
      pattern: "category: environmental"
---

<objective>
Author the 7 environmental use case files. Environmental cases pressure-test chain execution, passive-time mechanics, and world-state propagation (fire spread, weather, decay, seasons, terrain, light/dark, contagion).

Purpose: Stress-test chain execution mechanics (many of these cascade) and surface gaps around passive-time triggers (tie to Phase 7 SIM-09).

Output: 7 new use-case markdown files, each passing the schema validator.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/use-cases/_README.md
@.planning/use-cases/_TEMPLATE.md
@.planning/use-cases/environmental/MANIFEST.md
@.planning/phases/03-design-validation/03-RESEARCH.md
@src/token_world/use_cases/loader.py
@src/token_world/mechanic/seeds/environmental_reaction/mechanic.py

<interfaces>
Same contract as plan 06. Every file:
- category: environmental
- id: UC-V01..UC-V07
- status: draft

Parallelism: 7 disjoint files.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author UC-V01..UC-V07 (7 environmental use cases)</name>
  <files>.planning/use-cases/environmental/UC-V01-fire-spread.md, .planning/use-cases/environmental/UC-V02-weather-change.md, .planning/use-cases/environmental/UC-V03-decay.md, .planning/use-cases/environmental/UC-V04-seasons.md, .planning/use-cases/environmental/UC-V05-terrain-effect.md, .planning/use-cases/environmental/UC-V06-light-and-dark.md, .planning/use-cases/environmental/UC-V07-contagion.md</files>
  <read_first>
    - .planning/use-cases/_TEMPLATE.md
    - .planning/use-cases/_README.md
    - .planning/use-cases/environmental/MANIFEST.md
    - src/token_world/mechanic/seeds/environmental_reaction/mechanic.py (what chain-execution seed covers)
  </read_first>
  <action>
    Author each file at the exact target path following plan 06 task 1's contract.

    **Per-file scenario guidance:**

    UC-V01 (fire-spread): Setup: torch entity with `on_fire=true` adjacent to wooden_table with `flammable=true`. Action: tick advance. Observation: wooden_table now `on_fire=true`. Gap (mechanic, defer): environmental_reaction seed likely covers basic spread — verify against the seed source. Flag any missing primitives (e.g., extinguish-over-time).

    UC-V02 (weather-change): Setup: world entity with `weather="clear"`, outdoor torch `on_fire=true`, fabric tent. Action: weather changes to "rain". Observation: torch's fire extinguished; fabric `wet=true`. Gap (engine, address-now): weather as global state — where does it live in the graph? Gap (mechanic, address-now): weather-triggered mechanics need global-tick hook.

    UC-V03 (decay): Setup: apple with `placed_at_tick=0` and `decay_period=100`. Action: tick advances 100 ticks. Observation: apple becomes rotten_apple (or gains `rotten=true`). Gap (mechanic, address-now): passive-time decay — no mechanic fires without an agent action today. Gap (engine, address-now): passive tick handling (tie to SIM-09 Phase 7).

    UC-V04 (seasons): Setup: world `season="summer"`, tree with `has_leaves=true`. Action: season advances to "autumn". Observation: tree `leaves_falling=true`, then `has_leaves=false`. Gap (mechanic, defer): season as special-case of weather, deferrable. Gap (engine, address-now): calendar/time-scale modeling.

    UC-V05 (terrain-effect): Setup: alice with `move_speed=10`, swamp entity with `terrain_type="swamp"`, alice located_in swamp. Action: alice moves to adjacent dry_land. Observation: action takes 2x normal time (or move succeeds with reduced range). Gap (mechanic, address-now): terrain modifiers on movement. Gap (graph, defer): terrain ontology — should subtype be enough?

    UC-V06 (light-and-dark): Setup: alice in dark_room with `illumination=0`, bob in same room, torch in alice's room but not held. Action: alice looks around. Observation: narrative says "too dark to see"; no entity details in observation. Then alice picks up torch. Action 2: alice looks again. Observation: now sees bob. Gap (engine, address-now): observation filtering by illumination (SIM-07). Gap (mechanic, address-now): illumination propagation from light sources.

    UC-V07 (contagion): Setup: alice `infected=true`, bob in same room. Action: alice coughs; tick advance. Observation: bob probabilistically `infected=true`. Gap (mechanic, address-now): contagion mechanic (probabilistic, proximity-dependent). Gap (graph, defer): probability-backed mutations — non-deterministic mechanics tension.

    Each file ≥40 lines, passes validator. At least 4 files must have address-now gaps. UC-V03 should reference SIM-09 in gap text (passive-time tie to Phase 7).
  </action>
  <verify>
    <automated>uv run pytest tests/test_design_validation/test_use_case_schema.py -v && python3 -c "
from pathlib import Path
from token_world.use_cases import load_use_case, validate_frontmatter
files = sorted(Path('.planning/use-cases/environmental').glob('UC-V*.md'))
assert len(files) == 7, f'expected 7, got {len(files)}'
errs = []
for f in files:
    fm, body = load_use_case(f)
    errs.extend(validate_frontmatter(fm, source=str(f)))
    if '## Vignette' not in body: errs.append(f'{f}: missing ## Vignette')
assert not errs, '\n'.join(errs)
addr = sum(1 for f in files for fm, _ in [load_use_case(f)] for g in fm.get('gaps', []) if g.get('severity') == 'address-now')
assert addr >= 4, f'expected >=4 address-now gaps, got {addr}'
v03 = Path('.planning/use-cases/environmental/UC-V03-decay.md').read_text()
assert 'SIM-09' in v03, 'UC-V03 must cite SIM-09 (passive-time tie to Phase 7)'
print(f'ok 7 environmental UCs, {addr} address-now gaps, UC-V03 cites SIM-09')
"</automated>
  </verify>
  <acceptance_criteria>
    - 7 target files exist
    - All pass validate_frontmatter
    - All have Vignette + Why-this-matters
    - Every actor/target in setup
    - ≥4 files have address-now gaps
    - UC-V03 references SIM-09 (Phase 7 requirement traceability)
    - All ≥40 lines
  </acceptance_criteria>
  <done>7 environmental UCs authored; chain + passive-time gaps surfaced with traceability to SIM-09.</done>
</task>

</tasks>

<threat_model>
Same as plan 06. T-03-01 accepted.
</threat_model>

<verification>
- 7 files validate, schema test green
- UC-V03 cites SIM-09
- ≥4 address-now gaps
</verification>

<success_criteria>
1. All 7 environmental UC files exist and validate.
2. UC-V03 cites SIM-09 for passive-time traceability.
3. At least 4 address-now gaps contributed.
4. Chain-cascading scenarios (fire, weather, contagion) properly modeled in structured observations.
</success_criteria>

<output>
Create `.planning/phases/03-design-validation/03-09-SUMMARY.md` listing UC-V0X entries and the cascade/passive-time gaps surfaced.
</output>
