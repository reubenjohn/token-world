---
phase: 03-design-validation
plan: 06
type: execute
wave: 2
depends_on: [05]
files_modified:
  - .planning/use-cases/spatial/UC-S01-movement-through-doorway.md
  - .planning/use-cases/spatial/UC-S02-line-of-sight-occlusion.md
  - .planning/use-cases/spatial/UC-S03-nearest-object-query.md
  - .planning/use-cases/spatial/UC-S04-area-of-effect.md
  - .planning/use-cases/spatial/UC-S05-containment-hierarchy.md
  - .planning/use-cases/spatial/UC-S06-traversal-across-terrain.md
  - .planning/use-cases/spatial/UC-S07-position-updating-on-move.md
autonomous: true
requirements:
  - DVAL-01
tags:
  - use-cases
  - authoring
  - spatial

must_haves:
  truths:
    - "7 spatial use case files exist, one per manifest row (UC-S01..UC-S07)"
    - "Each file parses via load_use_case and passes validate_frontmatter"
    - "Each file's setup.graph_builder creates a graph in which every referenced actor/target node exists"
    - "Each file has at least one inline gap (at least 3 of the 7 must have gaps with severity=address-now, per D-03)"
    - "Every file's narrative body has a Vignette section and a Why-this-matters section"
  artifacts:
    - path: ".planning/use-cases/spatial/UC-S01-movement-through-doorway.md"
      provides: "Authored UC-S01 with frontmatter + narrative"
      min_lines: 40
    - path: ".planning/use-cases/spatial/UC-S02-line-of-sight-occlusion.md"
      min_lines: 40
    - path: ".planning/use-cases/spatial/UC-S03-nearest-object-query.md"
      min_lines: 40
    - path: ".planning/use-cases/spatial/UC-S04-area-of-effect.md"
      min_lines: 40
    - path: ".planning/use-cases/spatial/UC-S05-containment-hierarchy.md"
      min_lines: 40
    - path: ".planning/use-cases/spatial/UC-S06-traversal-across-terrain.md"
      min_lines: 40
    - path: ".planning/use-cases/spatial/UC-S07-position-updating-on-move.md"
      min_lines: 40
  key_links:
    - from: "each UC-S*.md"
      to: ".planning/use-cases/_TEMPLATE.md"
      via: "copy template and fill per spatial/MANIFEST.md row"
      pattern: "category: spatial"
---

<objective>
Author the 7 spatial use case files pre-assigned in `.planning/use-cases/spatial/MANIFEST.md`. Each file combines narrative vignette + structured YAML frontmatter (setup.graph_builder + actions + expected_observations + inline gaps).

Purpose: Pressure-test the framework against spatial scenarios (positions, LOS, containment, nearest-queries, AoE, terrain, movement side-effects). Surface gaps that will feed Wave 4 synthesis.

Output: 7 new use-case markdown files, each passing the Wave 0 schema validator.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/use-cases/_README.md
@.planning/use-cases/_TEMPLATE.md
@.planning/use-cases/spatial/MANIFEST.md
@.planning/phases/03-design-validation/03-CONTEXT.md
@.planning/phases/03-design-validation/03-RESEARCH.md
@src/token_world/use_cases/loader.py
@src/token_world/graph/knowledge_graph.py
@src/token_world/mechanic/seeds/movement/mechanic.py
@src/token_world/mechanic/seeds/observation/mechanic.py

<interfaces>
Every file must have frontmatter with these keys (REQUIRED_KEYS from loader.py):
  id, category, title, status, setup, actions, expected_observations, gaps

Valid values:
  status: draft
  category: spatial
  id: UC-S01..UC-S07
  each gap: {layer in {graph, mechanic, engine}, severity in {address-now, defer, out-of-scope}, summary, proposed_fix}

graph_assertion kinds (fixed vocabulary from _README.md): has_node, has_edge, not_has_edge, has_property, property_equals, not_has_property.

setup.graph_builder is a Python string that will be exec'd with `kg` in scope in Phase 6 regression. It must use KnowledgeGraph API only: add_node, add_edge, set. All positions/bboxes are JSON-safe lists.

Parallelism note: tasks in this plan have DISJOINT files_modified (one file per task) so executors can run them in parallel with zero write conflicts.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author UC-S01..UC-S07 (7 spatial use cases in parallel)</name>
  <files>.planning/use-cases/spatial/UC-S01-movement-through-doorway.md, .planning/use-cases/spatial/UC-S02-line-of-sight-occlusion.md, .planning/use-cases/spatial/UC-S03-nearest-object-query.md, .planning/use-cases/spatial/UC-S04-area-of-effect.md, .planning/use-cases/spatial/UC-S05-containment-hierarchy.md, .planning/use-cases/spatial/UC-S06-traversal-across-terrain.md, .planning/use-cases/spatial/UC-S07-position-updating-on-move.md</files>
  <read_first>
    - .planning/use-cases/_TEMPLATE.md (the copy-from)
    - .planning/use-cases/_README.md (format spec)
    - .planning/use-cases/spatial/MANIFEST.md (id, slug, scenario, no-seed-mechanic flag per row)
    - .planning/phases/03-design-validation/03-RESEARCH.md §Use case file template
    - src/token_world/mechanic/seeds/movement/mechanic.py (what basic movement already handles)
  </read_first>
  <action>
    For each of the 7 manifest rows, author one file at the exact target path. Use the MANIFEST as authoritative for id/title/slug. For each file:

    **Frontmatter requirements (all 7 files):**
    - `id:` matches manifest
    - `category: spatial`
    - `title:` matches manifest
    - `status: draft`
    - `setup:` with `graph_builder: |` multi-line string that creates all entities referenced in actions/observations. Use `kg.add_node(...)`, `kg.add_edge(...)`, `kg.set(...)`. All property values JSON-safe.
    - `actions:` list of ≥1 entries, each with `{actor, intent, classified: {verb, target, ...}}`. Multi-step scenarios may have 2-3 actions.
    - `expected_observations:` list paired with actions, each with `{actor, narrative_contains: [str], graph_assertions: [{kind, ...}]}`. Use ≥2 graph_assertions per observation.
    - `gaps:` list (may be empty for UCs that map cleanly to seed mechanics — but at least 4 of the 7 must have non-empty gaps, and at least 3 must have severity=address-now). Each gap: `{layer, severity, summary, proposed_fix}`.

    **Narrative body (all 7 files):**
    - `# UC-S0X: Title`
    - `## Vignette` — 2-3 paragraph readable English; a human non-developer should understand what's happening. Target 120-200 words.
    - `## Why this matters` — 1 paragraph on what this case pressure-tests about the framework.
    - `## Related use cases` — cross-references to other UC IDs (any category) if relevant.

    **Per-file specifics (execution guidance — author can refine but must match IDs):**

    UC-S01 (movement-through-doorway): Setup: alice agent at position [0,0] in room_a, doorway_1 entity connecting room_a↔room_b, room_b bbox on east side. Action: alice intents "walk east through doorway". Observation: alice now located_in room_b, no longer in room_a. Gap (mechanic, address-now): movement seed may only handle direct room-to-room edges, not passage through intermediate doorway entities.

    UC-S02 (line-of-sight-occlusion): Setup: alice in room_a, bob in room_b, wall entity between them. Action: alice intents "look at bob". Observation: narrative contains "cannot see" / "obscured"; graph shows alice did not gain a `saw=bob` property. Gap (mechanic, address-now): no LOS mechanic; observation seed just reports neighbors. Gap (graph, address-now): needs spatial index for occluder detection (ties to GRAPH-06).

    UC-S03 (nearest-object-query): Setup: alice at [0,0]; weapons scattered at various positions. Action: alice intents "find the nearest weapon". Observation: narrative names the nearest weapon. Gap (graph, address-now): requires GRAPH-06 spatial index (ctx.spatial.nearest). Gap (mechanic, address-now): no find-nearest mechanic.

    UC-S04 (area-of-effect): Setup: 5 entities scattered in a 10x10 grid. Action: explosion at [5,5] radius 3. Observation: all entities within radius 3 have `damaged=true`; others do not. Gap (graph, address-now): GRAPH-06 within() query. Gap (mechanic, address-now): no AoE mechanic; conservation-of-damage check needed.

    UC-S05 (containment-hierarchy): Setup: sword inside chest, chest inside room_a. Action: alice intents "look at sword". Observation: narrative describes containment chain; graph has edges sword -[inside]→ chest -[inside]→ room_a. Gap (engine, address-now): observation filtering for nested-containment (SIM-07 anticipation); recursive neighbor traversal.

    UC-S06 (traversal-across-terrain): Setup: alice in room_a, river entity between room_a and room_b, bridge entity spanning river. Action: alice crosses via bridge. Observation: alice now in room_b via bridge. Gap (mechanic, address-now): movement needs to recognize traversal entities (bridges, stairs, ladders). Gap (graph, defer): terrain typing system.

    UC-S07 (position-updating-on-move): Setup: alice at position [0,0] in room_a with centroid [0,0], room_b with centroid [10,0]. Action: alice moves to room_b. Observation: alice's position updated to [10,0]. Gap (mechanic, address-now): movement seed may not update continuous position when moving between discrete rooms; needs a hook.

    Each file must be ≥40 lines (frontmatter + body combined).

    **Self-check after writing each file:**
    - Confirm `uv run python -c "from pathlib import Path; from token_world.use_cases import load_use_case, validate_frontmatter; fm, body = load_use_case(Path('.planning/use-cases/spatial/UC-S0X-slug.md')); errors = validate_frontmatter(fm); assert not errors, errors"` passes.
    - Confirm every `actions[].actor` and every `actions[].classified.target` appears in the `setup.graph_builder` text (static sanity check; strict runtime check comes in Wave 3).
  </action>
  <verify>
    <automated>uv run pytest tests/test_design_validation/test_use_case_schema.py -v && python3 -c "
from pathlib import Path
from token_world.use_cases import load_use_case, validate_frontmatter
import sys
files = sorted(Path('.planning/use-cases/spatial').glob('UC-S*.md'))
assert len(files) == 7, f'expected 7, got {len(files)}'
errs = []
for f in files:
    fm, body = load_use_case(f)
    for e in validate_frontmatter(fm, source=str(f)):
        errs.append(e)
    if '## Vignette' not in body:
        errs.append(f'{f}: missing ## Vignette')
    if '## Why this matters' not in body:
        errs.append(f'{f}: missing ## Why this matters')
assert not errs, '\n'.join(errs)
# At least 3 files must have gaps with severity=address-now
addr_now_count = sum(1 for f in files for fm, _ in [load_use_case(f)] for g in fm.get('gaps', []) if g.get('severity') == 'address-now')
assert addr_now_count >= 3, f'expected >=3 address-now gaps across spatial UCs, got {addr_now_count}'
print(f'ok: 7 spatial UCs valid, {addr_now_count} address-now gaps')
"</automated>
  </verify>
  <acceptance_criteria>
    - All 7 target files exist at the exact paths listed in `files_modified`
    - `ls .planning/use-cases/spatial/UC-S*.md | wc -l` = 7
    - Every file passes `validate_frontmatter` (no errors)
    - Every file has `## Vignette` and `## Why this matters` narrative sections
    - At least 3 files have at least one gap with `severity: address-now`
    - Every `actions[].classified.target` string appears in the corresponding `setup.graph_builder` string
    - `wc -l` on every file ≥ 40
    - `uv run pytest tests/test_design_validation/test_use_case_schema.py -v` passes (no longer skipped since files exist)
  </acceptance_criteria>
  <done>7 valid, gap-rich spatial use cases authored. Schema validator test passes on them.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

None at author time. `setup.graph_builder` Python is executed only by the Phase 6 regression harness, which treats use-case files as committed code (RESEARCH.md §Security Domain).

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03-01 | Tampering | Use-case YAML/Python | accept | Authored in-repo by developers; reviewed in Wave 3. Same trust as test code. |
</threat_model>

<verification>
- 7 files exist, parse, validate
- Schema validator pytest green
- ≥3 address-now gaps across the 7 files
</verification>

<success_criteria>
1. All 7 spatial UC files exist, each ≥40 lines.
2. Every file passes `validate_frontmatter` with zero errors.
3. Every action's actor/target is defined by the same file's `setup.graph_builder`.
4. At least 3 files contribute address-now gaps to the Phase 3 gap backlog.
5. Narrative vignettes readable without reading the structured frontmatter.
</success_criteria>

<output>
After completion, create `.planning/phases/03-design-validation/03-06-SUMMARY.md` listing each UC-S0X with its file path, title, and the gaps it surfaces (one-line each).
</output>
