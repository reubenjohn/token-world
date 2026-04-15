# Phase 14: Engine Polish + Seed Corpus Hygiene — Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous smart discuss)

<domain>
## Phase Boundary

Three requirements:

**REQ-V12-ENGINE-05** — Refused tick observation contains "You try, but" wrapper exactly once. Currently may appear twice (doubled-wrapper bug: engine wraps, mechanic may also pre-wrap). Regression test on willowbrook tick 61 fixture.

**REQ-V12-SEEDS-01** — 5 framework-level seed mechanics (examine, pet, sharpen, hum, drop) promoted from Willowbrook overnight run into `src/token_world/mechanic/seeds/`. New universes get them without a yield. Also SC-3: seed_starter_universe.py adds bench (weathered=True), chicken coop, broken gate entities with hook properties.

**REQ-V12-TOOLING-02** — `seed_starter_universe.py --preserve-mechanics` flag: skip `_prune_seed_mechanics()` when set; without flag, print loud stderr warning naming every mechanic that would be overwritten.

</domain>

<decisions>
## Implementation Decisions

### ENGINE-05 fix strategy
- Write regression test first (assert single "You try, but" in observation_text for a refused tick fixture)
- Locate duplication: likely mechanics return pre-wrapped reasons that refusal.py wraps again
- Fix: strip wrapper from mechanic reason before re-wrapping, OR make refusal.py idempotent
- Source of truth: `src/token_world/engine/refusal.py` + `src/token_world/engine/engine.py`

### SEEDS-01 mechanic locations
- New files in `src/token_world/mechanic/seeds/examine.py`, `pet.py`, `sharpen.py`, `hum.py`, `drop.py`
- Add all 5 to `_KEEP_MECHANICS` frozenset in `scripts/seed_starter_universe.py`
- Each mechanic: standard Mechanic subclass with check() + apply(), sensible defaults
- SC-3 entities: add to universe scaffold in seed_starter_universe.py entity creation section

### TOOLING-02 flag
- Add `--preserve-mechanics` boolean flag to seed_starter_universe.py argparse
- Without flag: print stderr warning listing each mechanics/*.py file that would be overwritten
- With flag: skip _prune_seed_mechanics() entirely; preserve all authored mechanics

### Test approach
- ENGINE-05: fixture with a refused tick, assert single wrapper occurrence
- SEEDS-01: test that 5 mechanics are importable and registered in MechanicRegistry
- TOOLING-02: test --preserve-mechanics skips deletion; test without flag prints warning

</decisions>

<code_context>
## Existing Code Insights

- `src/token_world/engine/refusal.py` — RefusalTemplate, render() method
- `src/token_world/engine/engine.py` line ~715 — _handle_refuse() calls RefusalTemplate.render()
- `src/token_world/engine/observer.py` — synthesize() short-circuits on refusal, returns verbatim
- `src/token_world/mechanic/seeds/` — ~36 existing seed files; missing examine/pet/sharpen/hum/drop
- `scripts/seed_starter_universe.py` — _KEEP_MECHANICS frozenset, _prune_seed_mechanics()

</code_context>

<specifics>
## Specific Requirements (from ROADMAP SC-*)

- SC-1: Single "You try, but" wrapper — regression test on fixture
- SC-2: 5 new mechanics importable, no yield needed for these verbs on first tick
- SC-3: bench (weathered=True), chicken coop, broken gate in seed script with hook properties
- SC-4: --preserve-mechanics preserves mechanics/*.py; without flag, loud stderr warning names each file

</specifics>

<deferred>
## Deferred Ideas

- Generalizing the seed corpus to arbitrary universes (v2.0)

</deferred>
