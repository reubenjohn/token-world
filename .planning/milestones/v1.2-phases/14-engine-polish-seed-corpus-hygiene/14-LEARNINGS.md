---
phase: 14
phase_name: "Engine Polish + Seed Corpus Hygiene"
project: "Token World"
generated: "2026-04-14"
counts:
  decisions: 4
  lessons: 3
  patterns: 1
  surprises: 1
missing_artifacts: []
---

# Phase 14 Learnings

## Decisions

**DECISION: RefusalTemplate.render() made idempotent via _strip_wrapper()**
- `_strip_wrapper()` is a module-level helper in `refusal.py` that collapses any number of leading "You try, but " prefixes using a while-loop, then strips residual ". " padding.
- Applied to `format_map["reason"]` before `template.format_map()` — safe for all templates (no-op on templates that don't use `{reason}`).
- Consequence: `RefusalTemplate.render()` is now safe to call on pre-wrapped reason strings without producing a doubled wrapper. Callers never need to sanitize input.
- Source: 14-01-SUMMARY.md

**DECISION: drop.py keeps id="drop"; scaffold test updated to use --id toss (reserved name protection works correctly)**
- The scaffold CLI's collision guard correctly refuses to overwrite a seed mechanic. When `drop.py` was promoted to seeds/, `test_scaffold_mechanic.py` was using `--id drop` as its test fixture — now a reserved name.
- Fix: changed the test fixture to `--id toss` (a non-seed name) and updated the docstring to explain the collision-avoidance intent.
- The seed mechanic itself retains `id = "drop"` as the roadmap specifies. "toss" is purely a test artifact ID.
- Source: 14-02-SUMMARY.md, 14-VERIFICATION.md (SC-2 Drop-vs-Toss Finding)

**DECISION: Drop mechanic uses "carrying" relation (not "holds") to remain independent of pickup.py**
- Unification of carrying/holds vocabulary deferred to a future refactor. Keeping `drop.py` self-contained avoids a hard dependency on pickup.py's graph conventions at promotion time.
- Source: 14-02-SUMMARY.md

**DECISION: seed() takes preserve_mechanics kwarg; main() passes args.preserve_mechanics**
- Flag wires through without globals — `seed()` is testable in isolation with `preserve_mechanics=True/False` without needing to mock argparse.
- `_prune_seed_mechanics` collects `to_remove` list first, prints WARNING before any unlink — warning is always accurate even if an unlink subsequently fails.
- Source: 14-03-SUMMARY.md

## Lessons

**LESSON: Waves 1+2 ran parallel (disjoint files) — confirm the pattern for future parallel dispatch**
- Plan 14-01 (refusal.py + test_refusal_wrapper.py) and Plan 14-02 (seeds/*.py + test_seed_mechanics.py) touch fully disjoint file sets. Both completed in the same session without merge conflicts.
- The disjoint-file check (via `scripts/phase_waves.py`) is the right pre-dispatch gate for future parallel subagent sessions.
- Rule of thumb: plans touching the same module or test file must be sequenced; plans touching different subsystems can be parallelized.

**LESSON: _KEEP_MECHANICS must be updated whenever new seed mechanics are added — otherwise prune deletes them on re-seed**
- During 14-02, the 5 new seed mechanics (`examine`, `pet`, `sharpen`, `hum`, `drop`) were written first, then `_KEEP_MECHANICS` was updated in the GREEN gate commit. The RED gate confirmed 5 import failures before the frozenset was populated.
- Future seed mechanics must always be added to `_KEEP_MECHANICS` in `scripts/seed_starter_universe.py` as part of the same commit that creates the mechanic file. Omitting this causes `seed_starter_universe.py` (without `--preserve-mechanics`) to silently delete the new file on the next seed run.
- The `test_keep_mechanics_contains_new_seeds` AST-based test guards this invariant going forward.

**LESSON: Pre-existing traceability drift (test_no_traceability_drift[active-milestone]) must not be treated as a phase regression**
- This failure was present before Phase 14 started (confirmed by git stash check in 14-02). It spans phases 13–19 across REQUIREMENTS.md vs ROADMAP.md.
- Pattern: always run the full suite on the base commit before starting a phase, so pre-existing failures are documented as out-of-scope rather than discovered mid-phase and misattributed.

## Patterns

**PATTERN: TDD for engine bugs — write the test that catches the doubled output FIRST, then locate and fix the source**
- 14-01 followed strict RED/GREEN: `test_refusal_wrapper.py` was committed with 5 failing tests before `refusal.py` was touched. The RED phase confirmed the test correctly caught the doubled-wrapper bug.
- Value: the test spec is committed before the fix, so the fix cannot accidentally satisfy a different invariant. The GREEN phase is a provable contract, not an assumed one.
- Apply this pattern whenever an engine bug surfaces via production observation (e.g., willowbrook tick 61 showed doubled wrapper in a live run). Write the regression test from the production artifact before touching source.

## Surprises

**SURPRISE: "drop" ID appeared reserved (scaffold test used it) — actually the protection was correct behavior, not a bug**
- When `drop.py` was promoted to `src/token_world/mechanic/seeds/`, the existing `test_scaffold_mechanic.py` fixture used `--id drop` to test scaffold collision detection. After promotion, the test itself became the collision.
- Initial read: "the scaffold CLI is refusing a valid test ID." Actual read: the protection was working exactly as designed — `drop` is now a real seed, and the test needed a different fixture ID.
- Takeaway: when the scaffold collision guard fires unexpectedly, check whether the ID was just promoted to seeds rather than assuming the guard is buggy. The guard is correct by design.
