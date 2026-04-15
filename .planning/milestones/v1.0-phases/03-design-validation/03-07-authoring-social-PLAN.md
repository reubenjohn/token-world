---
phase: 03-design-validation
plan: 07
type: execute
wave: 2
depends_on: [05]
files_modified:
  - .planning/use-cases/social/UC-O01-trade-negotiation.md
  - .planning/use-cases/social/UC-O02-persuasion-check.md
  - .planning/use-cases/social/UC-O03-give-sword-to-bob.md
  - .planning/use-cases/social/UC-O04-deception.md
  - .planning/use-cases/social/UC-O05-teaching.md
  - .planning/use-cases/social/UC-O06-cooperation-lift-heavy.md
  - .planning/use-cases/social/UC-O07-observation-of-agent.md
  - .planning/use-cases/social/UC-O08-speech-broadcast.md
autonomous: true
requirements:
  - DVAL-01
tags:
  - use-cases
  - authoring
  - social

must_haves:
  truths:
    - "8 social use case files exist (UC-O01..UC-O08), each parsing and validating"
    - "Every file's setup graph includes all referenced actors/targets"
    - "At least 4 files surface address-now gaps (multi-agent and indirect-object cases especially)"
    - "Narrative vignettes readable standalone"
  artifacts:
    - path: ".planning/use-cases/social/UC-O01-trade-negotiation.md"
      min_lines: 40
    - path: ".planning/use-cases/social/UC-O02-persuasion-check.md"
      min_lines: 40
    - path: ".planning/use-cases/social/UC-O03-give-sword-to-bob.md"
      min_lines: 40
    - path: ".planning/use-cases/social/UC-O04-deception.md"
      min_lines: 40
    - path: ".planning/use-cases/social/UC-O05-teaching.md"
      min_lines: 40
    - path: ".planning/use-cases/social/UC-O06-cooperation-lift-heavy.md"
      min_lines: 40
    - path: ".planning/use-cases/social/UC-O07-observation-of-agent.md"
      min_lines: 40
    - path: ".planning/use-cases/social/UC-O08-speech-broadcast.md"
      min_lines: 40
  key_links:
    - from: "each UC-O*.md"
      to: ".planning/use-cases/_TEMPLATE.md"
      via: "copy template and fill per social/MANIFEST.md row"
      pattern: "category: social"
---

<objective>
Author the 8 social use case files pre-assigned in `.planning/use-cases/social/MANIFEST.md`. Social cases stress the framework on multi-agent interaction: trade, persuasion, deception, teaching, cooperation, speech, and indirect-object grammar.

Purpose: Surface gaps around multi-agent action modeling, indirect objects, and semantic observation (e.g., "hearing", "being deceived by"). Feeds Wave 4 gap synthesis.

Output: 8 new use-case markdown files, each passing the schema validator.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/use-cases/_README.md
@.planning/use-cases/_TEMPLATE.md
@.planning/use-cases/social/MANIFEST.md
@.planning/phases/03-design-validation/03-RESEARCH.md
@src/token_world/use_cases/loader.py
@src/token_world/graph/knowledge_graph.py
@src/token_world/mechanic/seeds/observation/mechanic.py

<interfaces>
See _README.md for the authoritative frontmatter + narrative contract. Every file here must pass validate_frontmatter, and `setup.graph_builder` must define every actor/target referenced in actions/observations.

Parallelism: 8 tasks, disjoint files_modified. Run in parallel; zero write conflicts.

All 8 files use:
- category: social
- id: UC-O01..UC-O08 (matches MANIFEST)
- status: draft
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author UC-O01..UC-O08 (8 social use cases)</name>
  <files>.planning/use-cases/social/UC-O01-trade-negotiation.md, .planning/use-cases/social/UC-O02-persuasion-check.md, .planning/use-cases/social/UC-O03-give-sword-to-bob.md, .planning/use-cases/social/UC-O04-deception.md, .planning/use-cases/social/UC-O05-teaching.md, .planning/use-cases/social/UC-O06-cooperation-lift-heavy.md, .planning/use-cases/social/UC-O07-observation-of-agent.md, .planning/use-cases/social/UC-O08-speech-broadcast.md</files>
  <read_first>
    - .planning/use-cases/_TEMPLATE.md
    - .planning/use-cases/_README.md
    - .planning/use-cases/social/MANIFEST.md
    - src/token_world/mechanic/seeds/observation/mechanic.py (what observation seed already handles)
  </read_first>
  <action>
    For each manifest row, author one file. Follow the general authoring rules from plan 06 (plan 03-06 task 1) — same frontmatter requirements, same narrative sections.

    **Per-file guidance (scenario shapes; authors may refine wording):**

    UC-O01 (trade-negotiation): Setup: alice agent, bob agent, sword entity held_by alice, bob has `inventory=["coin:10"]`. Action: alice offers sword for 10 coin. Observation: after acceptance, sword held_by bob, alice `inventory=["coin:10"]`. Gap (mechanic, address-now): no trade mechanic; requires transactional exchange. Gap (engine, address-now): action classification must model offer/acceptance two-step protocol.

    UC-O02 (persuasion-check): Setup: alice, bob, door entity with `locked=true`. Action: alice intents "convince bob to unlock the door". Observation: narrative describes bob's reaction (convinced/refuses); graph may or may not show door `locked=false`. Gap (engine, address-now): persuasion is a probabilistic social action — how does engine model outcome? Gap (mechanic, defer): charisma/reputation attributes.

    UC-O03 (give-sword-to-bob): Setup: alice holds sword, bob in same room. Action: alice intents "give sword to bob" — a multi-object action with direct object (sword) AND indirect object (bob). Observation: sword held_by bob. Gap (engine, address-now): ActionClassification needs `indirect_object` field. Gap (mechanic, address-now): give-to mechanic.

    UC-O04 (deception): Setup: alice, bob, chest with 100 coin. Action: alice tells bob "the chest is empty". Observation: narrative records the utterance; bob has a belief/memory property `believes_empty: chest`. Gap (mechanic, address-now): belief-tracking mechanic. Gap (graph, defer): agent mental-state representation.

    UC-O05 (teaching): Setup: alice has `knows_skill=["lockpicking"]`, bob does not. Action: alice teaches bob lockpicking. Observation: bob has `knows_skill=["lockpicking"]`. Gap (mechanic, address-now): teach/learn mechanic. Gap (engine, defer): knowledge as first-class graph state.

    UC-O06 (cooperation-lift-heavy): Setup: boulder entity with `mass=500`, alice `strength=200`, bob `strength=200`. Action: alice + bob jointly lift boulder. Observation: boulder `lifted_by=[alice, bob]`. Gap (engine, address-now): multi-actor action interpretation. Gap (mechanic, address-now): cooperative-action mechanic.

    UC-O07 (observation-of-agent): Setup: alice and bob in room_a, bob has `hp=80`. Action: alice looks at bob. Observation: narrative describes bob's visible state (hp if visible indicator, posture, etc.). Gap (engine, address-now): which properties are "visible"? SIM-07 observation filtering. Gap: may be fully handled by observation seed for simple props — flag ambiguity.

    UC-O08 (speech-broadcast): Setup: alice in room_a, bob in room_a (within 10m), charlie in room_b (30m away), wall between. Action: alice shouts "help!". Observation: bob hears; charlie does not (through wall + distance). Gap (graph, address-now): requires GRAPH-06 spatial for earshot range. Gap (mechanic, address-now): speech-propagation mechanic with occlusion.

    Each file ≥40 lines, passes validator, has Vignette + Why-this-matters. Authors may enrich with 1-2 graph_assertions per observation and multi-step action chains where realistic.

    **At least 4 of the 8 must have a gap with severity=address-now** (most social scenarios are genuinely unsupported today, so this should be easy).
  </action>
  <verify>
    <automated>uv run pytest tests/test_design_validation/test_use_case_schema.py -v && python3 -c "
from pathlib import Path
from token_world.use_cases import load_use_case, validate_frontmatter
files = sorted(Path('.planning/use-cases/social').glob('UC-O*.md'))
assert len(files) == 8, f'expected 8, got {len(files)}'
errs = []
for f in files:
    fm, body = load_use_case(f)
    errs.extend(validate_frontmatter(fm, source=str(f)))
    if '## Vignette' not in body: errs.append(f'{f}: missing ## Vignette')
    if '## Why this matters' not in body: errs.append(f'{f}: missing ## Why this matters')
assert not errs, '\n'.join(errs)
addr = sum(1 for f in files for fm, _ in [load_use_case(f)] for g in fm.get('gaps', []) if g.get('severity') == 'address-now')
assert addr >= 4, f'expected >=4 address-now gaps, got {addr}'
print(f'ok 8 social UCs, {addr} address-now gaps')
"</automated>
  </verify>
  <acceptance_criteria>
    - 8 target files exist at the exact manifest paths
    - All 8 pass `validate_frontmatter`
    - All 8 have `## Vignette` and `## Why this matters` sections
    - Every action's actor/target resolvable in the corresponding `setup.graph_builder`
    - ≥4 files have at least one gap with severity=address-now
    - `wc -l` on every file ≥ 40
  </acceptance_criteria>
  <done>8 social UCs authored; all pass schema validation and cover the multi-agent/indirect-object gap surface.</done>
</task>

</tasks>

<threat_model>
Same as plan 06: author-controlled, in-repo, no trust boundary crossed. T-03-01 accepted.
</threat_model>

<verification>
- 8 files exist, validate green
- Schema test passes
- ≥4 address-now gaps
</verification>

<success_criteria>
1. All 8 social UC files exist, ≥40 lines each.
2. All pass validate_frontmatter.
3. Every action actor/target exists in the same file's setup.
4. At least 4 files surface address-now gaps.
5. Narrative readable without consulting the frontmatter.
</success_criteria>

<output>
Create `.planning/phases/03-design-validation/03-07-SUMMARY.md` listing each UC-O0X with title, file path, and key gaps.
</output>
