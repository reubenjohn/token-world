---
phase: 03-design-validation
plan: 10
type: execute
wave: 2
depends_on: [05]
files_modified:
  - .planning/use-cases/edge-case/UC-E01-action-against-nonexistent-target.md
  - .planning/use-cases/edge-case/UC-E02-concurrent-actors.md
  - .planning/use-cases/edge-case/UC-E03-partial-knowledge.md
  - .planning/use-cases/edge-case/UC-E04-nonsense-input.md
  - .planning/use-cases/edge-case/UC-E05-circular-chain.md
  - .planning/use-cases/edge-case/UC-E06-move-into-locked-room.md
autonomous: true
requirements:
  - DVAL-01
tags:
  - use-cases
  - authoring
  - edge-case
  - robustness

must_haves:
  truths:
    - "6 edge-case use case files exist (UC-E01..UC-E06), each parsing and validating"
    - "Each file's setup graph includes all referenced actors/targets (even for nonexistent-target UCs, setup creates the graph context)"
    - "All 6 files surface address-now gaps (edge cases are inherently framework-stressing)"
    - "UC-E05 (circular chain) must flag a concrete gap around cycle detection in chain execution"
  artifacts:
    - path: ".planning/use-cases/edge-case/UC-E01-action-against-nonexistent-target.md"
      min_lines: 40
    - path: ".planning/use-cases/edge-case/UC-E02-concurrent-actors.md"
      min_lines: 40
    - path: ".planning/use-cases/edge-case/UC-E03-partial-knowledge.md"
      min_lines: 40
    - path: ".planning/use-cases/edge-case/UC-E04-nonsense-input.md"
      min_lines: 40
    - path: ".planning/use-cases/edge-case/UC-E05-circular-chain.md"
      min_lines: 40
    - path: ".planning/use-cases/edge-case/UC-E06-move-into-locked-room.md"
      min_lines: 40
  key_links:
    - from: "each UC-E*.md"
      to: ".planning/use-cases/_TEMPLATE.md"
      via: "copy template, fill per edge-case/MANIFEST.md row"
      pattern: "category: edge-case"
---

<objective>
Author the 6 edge-case use case files. Edge cases test framework robustness against bad input, adversarial scenarios, and execution hazards (nonexistent targets, concurrent actors, partial knowledge, nonsense, cycles, access denial).

Purpose: Force the framework to confront failure modes and adversarial inputs. Every gap here is a robustness gap — these likely produce the most "address-now" entries in the final gap analysis.

Output: 6 new use-case markdown files, each passing the schema validator.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/use-cases/_README.md
@.planning/use-cases/_TEMPLATE.md
@.planning/use-cases/edge-case/MANIFEST.md
@.planning/phases/03-design-validation/03-RESEARCH.md
@src/token_world/use_cases/loader.py
@src/token_world/mechanic/engine.py

<interfaces>
Same contract as plan 06. Every file:
- category: edge-case
- id: UC-E01..UC-E06
- status: draft

Note: For UC-E01 (action against nonexistent target), the target node is deliberately NOT in the setup graph — but the actor IS. The action's `classified.target` will point to an ID that doesn't exist, and the expected observation asserts the engine's failure mode (error message, no graph mutations). The static "every target exists in setup" check does NOT apply to UC-E01 — validators should allow this (document as an exception in the frontmatter via a `validator_exception: target_may_not_exist` key, OR structure the action so the target ID is literally `null`/`""` — executor choose cleanest approach and document).

Parallelism: 6 disjoint files.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author UC-E01..UC-E06 (6 edge-case use cases)</name>
  <files>.planning/use-cases/edge-case/UC-E01-action-against-nonexistent-target.md, .planning/use-cases/edge-case/UC-E02-concurrent-actors.md, .planning/use-cases/edge-case/UC-E03-partial-knowledge.md, .planning/use-cases/edge-case/UC-E04-nonsense-input.md, .planning/use-cases/edge-case/UC-E05-circular-chain.md, .planning/use-cases/edge-case/UC-E06-move-into-locked-room.md</files>
  <read_first>
    - .planning/use-cases/_TEMPLATE.md
    - .planning/use-cases/_README.md
    - .planning/use-cases/edge-case/MANIFEST.md
    - src/token_world/mechanic/engine.py (chain execution — how cycles would be detected or not)
  </read_first>
  <action>
    Author each file following plan 06 task 1's contract.

    **Per-file scenario guidance:**

    UC-E01 (action-against-nonexistent-target): Setup: alice agent, empty world. Action: alice intents "attack the dragon" (no dragon exists). Observation: narrative reports "no dragon here"; graph assertion: `not_has_node "dragon"` (unchanged). Gap (engine, address-now): action classifier must return graceful failure when target lookup fails. Gap (engine, address-now): narrative response for nonexistent target — hallucinated dragon would violate grounding (SIM-05).

    UC-E02 (concurrent-actors): Setup: alice, bob, apple entity (last one). Action 1: alice picks up apple. Action 2: bob picks up apple (same tick). Observation: one succeeds deterministically; narrative explains to the other. Gap (engine, address-now): turn ordering / concurrent action resolution — v1 simulation is turn-based so this may route to Phase 5 ordering gap. Gap (mechanic, defer): conflict-resolution policy.

    UC-E03 (partial-knowledge): Setup: alice, chest with `locked=true`, but alice has NOT been told chest is locked. Action: alice intents "open chest". Observation: narrative describes alice's attempt failing; alice now has `believes: {chest: "locked"}`. Gap (mechanic, address-now): agent belief state separate from world state. Gap (engine, address-now): observation filtering — alice shouldn't know chest is locked until attempting.

    UC-E04 (nonsense-input): Setup: alice, simple room. Action: alice intents "gragh flibble xyzzy rutabaga" (pure gibberish). Observation: narrative is a coherent response (e.g., "alice tries to do something incomprehensible" or asks for clarification); graph unchanged; narrative does NOT hallucinate a new entity. Gap (engine, address-now): action classification must return a "no viable action" verdict, not fabricate. Gap (engine, address-now): LLM-generation guardrails for nonsense inputs — don't generate mechanics for gibberish.

    UC-E05 (circular-chain): Setup: two hand-crafted mechanics A and B where A triggers B and B triggers A. Action: alice triggers A. Observation: engine detects cycle, halts chain with a bounded depth, narrative explains; graph reflects only the effects of the first N iterations. Gap (engine, address-now): cycle detection in chain execution — does existing engine have a depth limit? Gap (mechanic, address-now): mechanic authoring guidelines to avoid cycles.

    UC-E06 (move-into-locked-room): Setup: alice in room_a, door entity with `locked=true` between room_a and room_b. Action: alice moves east toward room_b. Observation: alice stays in room_a; narrative describes the locked door. Gap (mechanic, address-now): movement seed must respect blocking entities — currently may just follow edge. Gap (graph, defer): door state as a property on the edge vs on an entity node.

    Every file must have at least one gap with severity=address-now (edge cases are inherently framework-stressing). UC-E05 gap must specifically mention "cycle detection" or "chain depth limit" in its summary or proposed_fix (traceability).

    For UC-E01, use `classified.target: "dragon"` with setup NOT creating a dragon node. Add a narrative note in the file body explaining this is intentional.
  </action>
  <verify>
    <automated>uv run pytest tests/test_design_validation/test_use_case_schema.py -v && python3 -c "
from pathlib import Path
from token_world.use_cases import load_use_case, validate_frontmatter
files = sorted(Path('.planning/use-cases/edge-case').glob('UC-E*.md'))
assert len(files) == 6, f'expected 6, got {len(files)}'
errs = []
for f in files:
    fm, body = load_use_case(f)
    errs.extend(validate_frontmatter(fm, source=str(f)))
    if '## Vignette' not in body: errs.append(f'{f}: missing ## Vignette')
    # Every edge-case file should have ≥1 address-now gap
    if not any(g.get('severity') == 'address-now' for g in fm.get('gaps', [])):
        errs.append(f'{f}: edge cases must have at least one address-now gap')
assert not errs, '\n'.join(errs)
e05 = Path('.planning/use-cases/edge-case/UC-E05-circular-chain.md').read_text()
assert 'cycle' in e05.lower() or 'depth' in e05.lower(), 'UC-E05 must mention cycle detection / chain depth'
print('ok 6 edge-case UCs, each with address-now gaps, UC-E05 mentions cycle/depth')
"</automated>
  </verify>
  <acceptance_criteria>
    - 6 target files exist
    - All pass validate_frontmatter
    - All have Vignette + Why-this-matters
    - Every file has at least one gap with severity=address-now
    - UC-E05 mentions cycle detection or chain depth limit
    - UC-E01 setup does NOT create a `dragon` node (deliberate; the test of nonexistent-target handling)
    - All ≥40 lines
  </acceptance_criteria>
  <done>6 edge-case UCs authored; robustness gaps surfaced; UC-E01 nonexistent-target scenario and UC-E05 cycle scenario both concrete.</done>
</task>

</tasks>

<threat_model>
Same as plan 06. T-03-01 accepted.
</threat_model>

<verification>
- 6 files validate, schema test green
- Every file has address-now gap
- UC-E05 flags cycle detection
</verification>

<success_criteria>
1. All 6 edge-case UC files exist and validate.
2. Every file contributes at least one address-now gap.
3. UC-E01 exercises nonexistent-target handling (no dragon in setup).
4. UC-E05 flags cycle detection / chain depth.
</success_criteria>

<output>
Create `.planning/phases/03-design-validation/03-10-SUMMARY.md` listing UC-E0X entries and the robustness gaps they expose (all likely address-now).
</output>
