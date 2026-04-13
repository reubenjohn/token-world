---
phase: 04-llm-mechanic-generation
plan: 12
subsystem: phase-gate
tags: [phase-closeout, validation-finalization, retrospective, phase-5-handoff]
requires:
  - 04-01 (flat layout + 3-tool MCP + H-01/M-04 fixes)
  - 04-02 (6-stage validation pipeline + validate-mechanic CLI + registry auto-scan)
  - 04-03 (DiagnosticsSink substrate + prune-diagnostics CLI + D-15 closure)
  - 04-04 (integration harness parametrized over 35 UCs + manifest-outcomes invariant)
  - 04-05 (authoring guide + scaffold-mechanic CLI + D-38 blocked_by convention)
  - 04-06 (MECH01 passage_move / MECH05 terrain_move / MECH06 position_sync)
  - 04-07 (MECH02 look / MECH03 find_nearest / MECH04 aoe / MECH13 speak / MECH27 try_door)
  - 04-08 (MECH07 trade / MECH08 give / MECH14 craft / MECH15 consume / MECH16 pickup)
  - 04-09 (MECH10 tell / MECH11 teach / MECH25 belief_update + MECH09 persuade / MECH12 cooperate D-38 stubs)
  - 04-10 (MECH17 degrade / MECH18 fungible_pay)
  - 04-11 (MECH20 fire_spread / MECH22 decay_tick / MECH23 illumination / MECH24 contagion + MECH21 weather_reaction D-38 stub)
provides:
  - 04-VALIDATION.md flipped to nyquist_compliant=true, wave_0_complete=true, status=approved
  - Gap-closure matrix (28 Phase-4 gaps accounted for)
  - UC outcome tally (22 pass / 0 yield / 13 blocked of 35)
  - Framework-gap-stub registry for Phase 5 planner (3 stubs: MECH09/MECH12/MECH21)
  - Conventions inventory that Phase 5 must respect
  - Phase 4 retrospective (what worked / inefficiencies / lessons)
  - Open questions for Phase 5 planner
  - REQUIREMENTS.md: 8 requirements flipped to Complete (MECH-03/04/05/06, TEST-02, AUTO-02/03, UNIV-03)
  - ROADMAP.md: Phase 4 + all 12 plans checked off; Progress table updated
affects:
  - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md
  - .planning/phases/04-llm-mechanic-generation/04-12-SUMMARY.md (this file)
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
  - src/token_world/use_cases/loader.py (late-stage ruff format fix)
  - src/token_world/mechanic/seeds/fungible_pay.py (late-stage mypy narrowing)
tech-stack:
  added: []
  patterns:
    - "Nyquist compliance gate: plan's W8 check verifies every Wave 0 file exists on disk BEFORE flipping the frontmatter flag. All 7 files (test_validation, test_loader, test_diagnostics, test_integration/conftest, test_use_cases, test_manifest_outcomes, test_seeds/ dir) found via test -f / test -d."
    - "Integrate gate: after infra waves (04-01..04-05) the orchestrator paused, wrote a MechanicContext DSL freeze commit (e689bfd) + MechanicRegistry.get_class accessor (06fc528), centralized the harness matcher ownership (cc786db), and aligned all 6 seed plans (cc9a873). This is the pattern that prevented the 04-REVIEWS HIGH#3 'seeds invent slightly different adaptations' drift from materialising."
    - "Fork-bomb hotfix: stage-5 pytest-as-subprocess made opt-in via TOKEN_WORLD_RUN_TEST_STAGE=1 (7a81c31) after a 23x suite slowdown surfaced — scan-time subprocess invocations will never be the default again."
key-files:
  created:
    - .planning/phases/04-llm-mechanic-generation/04-12-SUMMARY.md
  modified:
    - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - src/token_world/use_cases/loader.py
    - src/token_world/mechanic/seeds/fungible_pay.py
decisions:
  - "Treated late-stage regressions (use_cases/loader.py format drift + fungible_pay.py mypy narrowing) as Rule-1 Bug deviations owned by 04-12. They blocked the phase gate; fixing them inline was the only way to reach nyquist_compliant=true."
  - "Deferred-items.md pre-existing E501 drift in validation.py is ALREADY RESOLVED. When 04-12 ran `ruff check src/` the tree was clean — the drift noted in 04-02/04-03/04-05 deferred sections has been incidentally fixed by a downstream formatter run, probably in 04-09's `f824be3 style(04-09): ruff format + SIM300 yoda fix...`. Leaving deferred-items.md intact as historical record per the plan spec."
  - "Wave 0 plan entry `test_loader_flat.py` corrected to `test_loader.py` — the actual file name shipped by 04-01. Noted inline in VALIDATION.md Wave 0 list so future planners don't hunt for the non-existent file."
  - "ROADMAP.md Progress table row renamed from 'LLM Mechanic Generation' to 'Mechanic Authoring & Validation Infrastructure' — the phase's actual reframed title per ROADMAP line 19 and GAP-HANDOFF front-note."
  - "STATE.md explicitly not touched — orchestrator owns it per the plan prompt."
metrics:
  duration: ~25 min
  completed: 2026-04-13
  test_delta: 782 passed, 14 skipped, 0 xfailed (identical to 04-11 baseline; no new tests in this plan)
  lint: ruff check src/ clean; ruff format --check src/ clean; mypy src/token_world/ clean (64 files)
---

# Phase 4 Plan 12: Phase gate — VALIDATION finalization + retrospective — Summary

Closes Phase 4. `04-VALIDATION.md` is now approved (`nyquist_compliant: true`, `wave_0_complete: true`, `status: approved`); every Phase 4 requirement is marked Complete in REQUIREMENTS.md; ROADMAP.md Phase 4 is checked off with all 12 plans; and this document captures the retrospective + Phase 5 handoff.

## 1. Phase 4 Deliverables

Infrastructure (plans 04-01..04-05):

| Deliverable | Plan | Description |
|-------------|------|-------------|
| Flat mechanic layout | 04-01 | `mechanics/<id>.py` modules; no subfolders / meta.yaml; supersedes Phase 2 D-15 |
| 3-tool MCP surface | 04-01 | `resume_tick`, `rollback`, `list_mechanics` — `register_mechanic` dropped |
| Mirrored test tree | 04-01 | `tests/test_mechanic/test_seeds/test_<id>.py`; scaffold creates `tests/test_mechanics/` |
| Phase 3 code fixes | 04-01 | H-01 (temporal index add_node replay) + M-04 (CRLF frontmatter) — fixes upstream, regression tests local |
| Validation pipeline | 04-02 | 6-stage: syntax → AST → import → contract → tests → smoke; D-14 AST rules |
| `validate-mechanic` CLI | 04-02 | Human + JSON formats; exit codes 0 pass / 1 fail / 2 resolver error |
| Registry auto-scan | 04-02 | `MechanicRegistry.scan()` runs validation; invalid modules excluded from index |
| DiagnosticsSink substrate | 04-03 | `AUTO-02`; per-tick + per-validation diagnostics; `SCHEMA_VERSION=1` |
| Atomic JSON writes | 04-03 | `tempfile.mkstemp + os.fsync + os.replace`; boot-time `.tmp` sweep |
| `prune-diagnostics` CLI | 04-03 | Dry-run default; `--confirm` deletes; symlink-safe |
| D-15 wiring closure | 04-03 | `MechanicRegistry.scan(diagnostics_sink=...)` persists failing reports |
| Integration harness | 04-04 | `tests/test_integration/test_use_cases.py`; parametrized over 35 UCs |
| Tri-state outcomes | 04-04 | `pass` / `yield` / `blocked`; explicit body branching (pytest.xfail/fail/skip) |
| Manifest-outcomes invariant | 04-04 | `tests/test_use_cases/test_manifest_outcomes.py`; pytest-enforced (W7) |
| Manifest annotator script | 04-04 | `scripts/annotate_use_case_outcomes.py` — CLAUDE.md bash-hygiene compliant |
| Authoring guide | 04-05 | `docs/guides/authoring-mechanics.md` (665 lines, 15 `##` headings); D-30/D-31 |
| `scaffold-mechanic` CLI | 04-05 | `^[a-z][a-z0-9_]*$` regex; scaffolded skeleton passes validation |
| `blocked_by` convention | 04-05 | D-38 framework-gap-stub pattern (§8 of guide) |
| Universe guide copy | 04-05 | Byte-identical `<universe>/docs/authoring-mechanics.md` via scaffold |

Seed mechanics (plans 04-06..04-11):

| Cluster | Plan | Mechanics |
|---------|------|-----------|
| Spatial movement | 04-06 | MECH01 passage_move, MECH05 terrain_move, MECH06 position_sync |
| Spatial queries + speech/try_door | 04-07 | MECH02 look, MECH03 find_nearest, MECH04 aoe, MECH13 speak, MECH27 try_door |
| Object interaction | 04-08 | MECH07 trade, MECH08 give, MECH14 craft, MECH15 consume, MECH16 pickup |
| Social + belief + D-38 stubs | 04-09 | MECH10 tell, MECH11 teach, MECH25 belief_update + MECH09 persuade STUB, MECH12 cooperate STUB |
| Resource durability + currency | 04-10 | MECH17 degrade, MECH18 fungible_pay |
| Environmental family + D-38 stub | 04-11 | MECH20 fire_spread, MECH22 decay_tick, MECH23 illumination, MECH24 contagion + MECH21 weather_reaction STUB |

Total seed modules: **28** (`ls src/token_world/mechanic/seeds/*.py | grep -v "_"` → 28 files). Of these, **25 are real mechanics** (3 pre-existing from Phase 2 + 22 authored in Phase 4) and **3 are D-38 framework-gap stubs** (persuade, cooperate, weather_reaction).

## 2. Gap Closure Matrix

All 28 Phase-4 gap IDs from the 04-12 frontmatter `gap_ids:` list:

| Gap ID | Status | Plan | Notes |
|--------|--------|------|-------|
| GAP-MECH01 | closed | 04-06 | MECH01 passage_move — accepts both direct connects and mediated (doorway/bridge) |
| GAP-MECH02 | closed | 04-07 | MECH02 look — room-local scan as GAP-GRAPH02 workaround (documented; retires with ray-check) |
| GAP-MECH03 | closed | 04-07 | MECH03 find_nearest — ctx.spatial.nearest + brute-force fallback |
| GAP-MECH04 | closed | 04-07 | MECH04 aoe — bbox over-approximation + Euclidean post-filter |
| GAP-MECH05 | closed | 04-06 | MECH05 terrain_move — movement_cost_multiplier or terrain_type lookup; max(source, target) |
| GAP-MECH06 | closed | 04-06 | MECH06 position_sync — reactive EdgeMatcher on add_edge located_in |
| GAP-MECH07 | closed | 04-08 | MECH07 trade — single-tick atomic mirrored pending_trade swap |
| GAP-MECH08 | closed | 04-08 | MECH08 give — pending_give dict (scalar + item forms) |
| GAP-MECH09 | stub | 04-09 | MECH09 persuade — `blocked_by="GAP-ENG03"` llm_adjudicated category (D-38) |
| GAP-MECH10 | closed | 04-09 | MECH10 tell — pending actor.utterance → recipient.beliefs write |
| GAP-MECH11 | closed | 04-09 | MECH11 teach — co-located single-recipient via _find_sole_recipient |
| GAP-MECH12 | stub | 04-09 | MECH12 cooperate — `blocked_by="GAP-ENG05"` intent-fusion pre-pass (D-38) |
| GAP-MECH13 | closed | 04-07 | MECH13 speak — room-filter + earshot-radius fan-out |
| GAP-MECH14 | closed | 04-08 | MECH14 craft — recipe-on-workstation (target.recipe dict) |
| GAP-MECH15 | closed | 04-08 | MECH15 consume — remove held food + hunger delta (floored at 0) |
| GAP-MECH16 | closed | 04-08 | MECH16 pickup — inventory_cap-bounded via _count_holds + refusal narrative |
| GAP-MECH17 | closed | 04-10 | MECH17 degrade — use-on-tool durability decrement; remove-at-zero |
| GAP-MECH18 | closed | 04-10 | MECH18 fungible_pay — subset-sum exact-change via _subset_sum helper |
| GAP-MECH19 | absorbed | 04-05 | D-35: trust-boundary concept obsolete under inversion of control; guide §10 documents rationale |
| GAP-MECH20 | closed | 04-11 | MECH20 fire_spread — single-hop spread with reactive-cycle guard (T-04-CYCLE) |
| GAP-MECH21 | stub | 04-11 | MECH21 weather_reaction — `blocked_by="GAP-ENG09"` WorldPropertyMatcher primitive (D-38) |
| GAP-MECH22 | closed | 04-11 | MECH22 decay_tick — voluntary Phase-4 wrapper; GAP-ENG07 reactive sweep deferred to Phase 5 |
| GAP-MECH23 | closed | 04-11 | MECH23 illumination — idempotent room-lighting recompute with cycle guard |
| GAP-MECH24 | closed | 04-11 | MECH24 contagion — probabilistic transmission w/ GAP-GRAPH05 seeded-RNG workaround |
| GAP-MECH25 | closed | 04-09 | MECH25 belief_update — fixed observable-property set (retires with GAP-GRAPH04) |
| GAP-MECH26 | absorbed | 04-05 | Authoring guide §9 "Reactive-Cycle Cautions" covers the lint-intent as prose |
| GAP-MECH27 | closed | 04-07 | MECH27 try_door — unlock-or-refuse; established refusal-narrative pattern |
| GAP-ENG16 | closed | 04-02 | Validation gate (D-14 AST rules + pipeline exclusion) handles the Phase-4 half of D-34. Phase 5 classifier owns the `no_viable_action` verdict half. |

Totals: **24 closed, 3 stubs, 2 absorbed = 27 addressed mechanic gaps** + **1 cross-phase gap (GAP-ENG16) closed for Phase 4's half**. All 28 accounted for.

## 3. UC Outcome Tally

Final harness state after 04-11: **782 passed, 14 skipped, 0 xfailed** (from a post-04-04 baseline of 445 passed / 21 skipped / 14 xfailed).

| Outcome | Count | UCs |
|---------|-------|-----|
| pass | 22 | UC-E03, UC-E06, UC-O01, UC-O03, UC-O04, UC-O05, UC-O08, UC-R01, UC-R02, UC-R03, UC-R04, UC-R06, UC-S01, UC-S02, UC-S03, UC-S04, UC-S06, UC-S07, UC-V01, UC-V05, UC-V06, UC-V07 |
| yield | 0 | (none — every yield UC from 04-04 has been closed by a seed plan) |
| blocked | 13 | UC-E01, UC-E02, UC-E04, UC-E05, UC-O02, UC-O06, UC-O07, UC-R05, UC-R07, UC-S05, UC-V02, UC-V03, UC-V04 |
| **total** | **35** | |

Blocked UCs routed to Phase-5 framework extensions:

| UC | Blocker | Route |
|----|---------|-------|
| UC-O02 | GAP-ENG03 | via MECH09 persuade D-38 stub |
| UC-O06 | GAP-ENG05 | via MECH12 cooperate D-38 stub |
| UC-V02 | GAP-ENG09 | via MECH21 weather_reaction D-38 stub |
| UC-V04 | GAP-ENG09 | via MECH21 weather_reaction D-38 stub |
| UC-R05 | GAP-ENG02 + threshold-flag semantics | Inline 25-line rationale in manifest (plan 04-10 decision tree) |
| UC-V03 | GAP-ENG07 (passive-tick) + world.current_tick | Inline 25-line rationale in manifest (plan 04-11 decision tree) |
| UC-S05 | Engine-layer gap (containment hierarchy) | Phase 5 |
| UC-O07 | Engine-layer gap (observation-of-agent) | Phase 5 |
| UC-R07 | Engine-layer gap (conservation violation) | Phase 5 (GAP-ENG06) |
| UC-E01 | GAP-ENG11/12 (nonexistent-target verdicts) | Phase 5 |
| UC-E02 | GAP-ENG13/14 (concurrent actors) | Phase 5 |
| UC-E04 | GAP-ENG15 (nonsense classifier verdict) | Phase 5 |
| UC-E05 | GAP-ENG17/18 (circular chain hardening) | Phase 5 |

## 4. Framework-Gap Stubs for Phase 5

Three D-38 stubs ship through the Phase-4 registry. Phase 5 planner uses this table to schedule gap-closure work:

| Mechanic | blocked_by | Plan | Unblocking work for Phase 5 |
|----------|-----------|------|-----------------------------|
| persuade | GAP-ENG03 | 04-09 | Introduce `llm_adjudicated` mechanic category (probabilistic/social-check resolution) |
| cooperate | GAP-ENG05 | 04-09 | Intent-fusion pre-pass (multi-actor mechanic dispatch); pairs with GAP-MECH12 |
| weather_reaction | GAP-ENG09 | 04-11 | `WorldPropertyMatcher` primitive; canonical `world` node |

Unblock protocol: when the framework extension lands, the stub is **rewritten in place** — delete `blocked_by`, implement real `check`/`apply`, run the unit test file as a RED test, and flip the gated UC's harness routing. The stub skeleton (§8 of the authoring guide) is the known-good template — don't copy a different pattern.

## 5. Conventions Established (Phase 5 must respect)

Code/organisation conventions:

- **`_helpers.py` module** (D-05, D-11): underscore-prefix, sibling imports, skipped by registry discovery. Mechanics may import from `_*.py` siblings. Graduate helpers when ≥2-3 mechanics share them (_find_open_passage, _current_location, _find_matching_key, _count_holds, _refuse_with_narrative, _find_sole_recipient, _subset_sum).
- **`blocked_by` class attribute** (D-38): string constant on a Mechanic subclass; read by the harness via `MechanicRegistry.get_class(id).blocked_by`. Stubs NEVER import absent symbols (Pitfall 6).
- **Refusal narrative via actor property**: mechanics that refuse inside `apply` write `last_refusal_narrative` + `last_refusal_target` on the actor through `_refuse_with_narrative`. Partial GAP-CROSS02 surface until Phase 5 adds `(ok=False, narrative=...)` to the engine contract.
- **pending_\* dict convention (GAP-ENG02 workaround)**: manifests pre-stage `actor.pending_give / pending_trade / pending_payment / utterance`; mechanics read them in `apply` and clear with `ctx.set(..., None)`. Swaps for `ctx.claim` / `ctx.indirect_object` when GAP-ENG02 lands.
- **Strict-int property sieve**: `isinstance(x, int) and not isinstance(x, bool)` — Python's bool-is-int relation means a typo like `durability=True` would pass a naive int check. Adopted by degrade, fungible_pay.
- **Reactive-cycle guard** (T-04-CYCLE mitigation): mechanics that iterate neighbours and flip reactive properties MUST refuse in `check()` when every candidate is already in the target state, AND skip already-state nodes in `apply`. Adopted by fire_spread, illumination, contagion.
- **voluntary-for-routing + involuntary_intent tag**: Phase-4 harness routes only voluntary mechanics; seeds that are semantically involuntary (fire_spread, illumination, weather_reaction, reactive stubs) ship with `voluntary=True` + `"involuntary_intent"` in `tags` + retained `watches()` matcher for Phase-5 reactive-registration. Phase 5 will flip them back.

API-contract conventions:

- **`DiagnosticsSink` API shape** (D-23): `open_tick(tick_id)` ctx manager yielding `TickDiagnostics`; `open_validation(mechanic_id) -> Path`; `prune(before_tick=|before_date=, confirm=)`. `TickDiagnostics` methods: `write_action / write_classification / write_matching / append_mutation / write_execution_trace / write_observation / set_summary / finalize`. `SCHEMA_VERSION=1` is stamped into every `summary.json`.
- **`ValidationReport` shape**: `.to_dict()` returns `{module_path, passed, findings}` where each finding is `{stage, rule, severity, message, path, line, col}`. Consumed directly by `DiagnosticsSink.open_validation` → `validation/<ts>_<id>/report.json`.
- **Single matcher helper**: `tests/test_integration/test_use_cases.py::match_mechanic_for_verb` is the harness's sole verb→mechanic router. Extension policy (04-04 SUMMARY §Harness Matcher): changes must re-plan 04-04 with a corresponding test case in `tests/test_mechanic/test_harness_matcher.py`. Phase 5's classifier replaces this stub end-to-end.

D-14 AST rules (Phase 5 should NOT expand without plan decision):

- **Forbidden calls**: `eval`, `exec`, `__import__`, `compile`, `globals`, `open` (only bare-name; `foo.eval()` attribute access allowed)
- **Forbidden imports**: `networkx`, `networkx.*`, `token_world.graph.knowledge_graph`
- **Allowed imports**: `token_world.mechanic.*` public API, sibling `_*.py` helpers, Python stdlib
- These rules are enforced BEFORE `importlib` runs (defense-in-depth); NOT a sandbox (T-04-AST-BYPASS accepted + disclosed in guide §6)

## 6. Lessons Learned (Retrospective)

**What worked:**

- **Flat module layout simplified every downstream tool.** Scaffold, registry discovery, `git log -- mechanics/<id>.py`, per-file git history: all dropped out "for free" once the Phase-2 folder-per-mechanic was removed (D-03..D-08). 04-01 was near-mechanical because the constraint collapsed.
- **Thematic clustering kept per-plan context under 40%.** 04-06..04-11 each authored 2-5 mechanics + tests + UC flips in ≤45 minutes. Helpers graduated naturally as clusters overlapped (`_find_open_passage` from 04-06 → 04-07; `_refuse_with_narrative` from 04-07 → 04-08).
- **Integrate gate between infra and authoring waves** (orchestrator checkpoint). After 04-05 the orchestrator paused, wrote `MechanicContext` DSL freeze (e689bfd), added `MechanicRegistry.get_class` accessor (06fc528), centralized harness matcher ownership (cc786db), and aligned 6 seed plans (cc9a873). This prevented the 04-REVIEWS HIGH #3 "DSL ambiguity → seeds invent slightly different adaptations" drift. **Phase 5 should pattern-match this**: after its infra plans ship (classifier, observer, conservation engine), PAUSE before domain plans start; freeze the new engine surface.
- **D-29b tri-state outcome model (`pass/yield/blocked`)** + explicit body branching (W5) made incremental UC flips a 1-line edit. 22 UCs flipped from `yield`/`blocked` → `pass` without any harness churn.
- **Authoring-guide dogfooding.** 04-05's guide was used by the operator for 04-06..04-11 — the stub skeleton, `blocked_by` convention, `_helpers.py` graduation rule, and refusal narrative pattern all came out of the guide's §3/§8/§11/§9.

**What was inefficient:**

- **Harness verb→mechanic matcher stub was naive.** 04-04's `match_mechanic_for_verb` only matches `info.voluntary and info.id == verb`. Every seed plan then aligned `classified.verb` to the mechanic id in its UCs, meaning every UC now has an "obvious" verb. This works but is fragile — Phase 5's classifier must route "walk/move" to a movement mechanic regardless of surface form. The earlier classifier would have let seeds use natural verbs. Lesson: accept the stub's friction as a deliberate choice, don't grow it.
- **D-38 stub-probe ordering required a harness rewrite in 04-09** (Task 2) that should have landed in 04-04 alongside the outcome dispatcher. The probe needs to run BEFORE manifest-outcome early-skip, and getting that right mid-seed-wave forced a cross-plan extension. Lesson: harness extensions have to be planned ahead of the seed plans that depend on them.
- **Fork-bomb near-miss.** 04-02's stage-5 (run mechanic's own tests via `pytest` subprocess) was enabled by default; when the main `uv run pytest` picked up a seed test that imported the registry, the registry scanned seeds, validation ran the per-seed test via subprocess, which itself imported the registry, which scanned… Suite wall-clock went from ~11s to ~250s. Hotfix: `TOKEN_WORLD_RUN_TEST_STAGE=1` opt-in (7a81c31). **Scan-time subprocess invocations are dangerous; default them off.**
- **3 manifest rewrites (UC-O01 single-tick, UC-V06 single-action, UC-R05 / UC-V03 blocked rationale)** were deferred to execution-time decision trees rather than being resolved in the plans themselves. 04-REVIEWS MEDIUM flagged this. Lesson: the planner should read target UCs up-front.
- **Pre-existing deferred-items.md entries** (validation.py E501, test ruff drift across 04-01/04-06/04-09) turned out to be incidentally fixed by a downstream `ruff format` run (likely 04-09 commit `f824be3`). The deferred list drifted out of sync with reality. Lesson: re-verify deferred items at the next plan's start rather than trusting stale entries.

**Cost patterns:**

- **4-8 mechanics per plan × 6 seed plans = 28 mechanics in ~5 hours total.** Parallelisable because thematic clusters share a helper but not state. Best ROI: plans like 04-10 (2 mechanics, 35 new unit tests, 9 minutes) — small cluster, deep coverage.
- **Infrastructure plans (04-01..04-05) took ~2 hours total.** Mostly because 04-04's harness needed 4 W-prefixed iterations (W2/W5/W7/W9) to handle the outcome-dispatch correctness.
- **Phase gate (04-12) took ~25 min** because 04-11 already had the suite green and VALIDATION rows populated through 04-11-T3. Task 1 was a frontmatter flip + status cleanup; Task 2 was trivial edits. Most of the time went into the retrospective.

**Discovery:**

- **Integration harness matcher extension for `blocked_by` routing was cleaner than expected.** 04-09 added a `_resolve_blocked_by` helper that the harness runs BEFORE manifest-outcome dispatch. One integer-sized change surfaced the GAP-ENG03/05 gap reasons on every harness run. Phase 5's classifier can absorb this pattern.
- **The "refusal narrative on actor" pattern doubles as Phase 5 grounding data.** Phase 5 observation synthesis will read `actor.last_refusal_narrative` for failure-case observations without needing a new API. This was an unplanned win from 04-07 try_door.

## 7. Open Questions for Phase 5

1. **Does Phase 5 assume every seed has `blocked_by=None`, or does it scan for stubs?** — The harness reads `MechanicRegistry.get_class(id).blocked_by`; Phase 5's classifier needs to pick up stubs with the same API. Recommend: single `is_stubbed(mechanic_id)` helper in `registry.py` so both layers call the same predicate.

2. **Verb→mechanic matching handoff protocol.** — The harness's `match_mechanic_for_verb` is exact-id only. Phase 5's classifier will route natural verbs ("walk", "move", "step") to `terrain_move` via LLM dispatch. When the classifier is wired end-to-end, does the harness matcher get deleted, or does it remain as a stub test for classifier-bypass scenarios? Recommend: keep as a fallback, document that classifier-routing is authoritative; harness matcher only fires when `TOKEN_WORLD_SKIP_CLASSIFIER=1`.

3. **`DiagnosticsSink` contract: sufficient for Phase 5's writes?** — Current methods: `write_action / write_classification / write_matching / append_mutation / write_execution_trace / write_observation / set_summary / finalize`. Phase 5's classifier needs prompt/response/parsed triples (covered); observer needs same (covered); conservation enforcer may need a new `write_conservation_check` method. Recommend: add if/when needed; `TickDiagnostics` is a small class and the schema-version bump is cheap.

4. **Stubs' `voluntary=True` + `involuntary_intent` tag retirement.** — Fire_spread, illumination, weather_reaction all ship as `voluntary=True` so the Phase-4 verb matcher can route them. When Phase 5's reactive-registration lands, these flip back to `voluntary=False`. The pattern is explicit — but which Phase 5 plan owns the flip?

5. **Pre-existing UCs (UC-R05, UC-V03) with inline "stays blocked" rationale** — these have 25-line frontmatter comments documenting the blocker. When the blocker closes in Phase 5, the comment blocks must be deleted AND the manifest rewritten to the passable shape. Recommend: Phase 5 planner treats these as "author this mechanic AND rewrite the UC" — two-step deliverable, not a one-step flip.

6. **Framework assumption: `ctx.temporal` availability for GAP-GRAPH05 workaround in contagion.** — `_resolve_seed` in contagion.py reads `ctx.temporal.current_tick` best-effort with a class-level fallback. If Phase 5 reorganises `MechanicContext` (indirect_object, claim, per-step observation), does `ctx.temporal` stay? Recommend: preserve `ctx.temporal` as part of the DSL freeze; contagion retires its workaround when GAP-GRAPH05 introduces a proper `ctx.seed(scope=...)`.

## 8. Files Modified Summary

Phase 4 scope (Apr 12-13, 2026):

- **Commits since 2026-04-12** (spanning src/tests/docs/.planning): **163** (via `git log --oneline --since=2026-04-12 -- src/ tests/ docs/ .planning/ | wc -l`).
- **Seed modules**: **28** (`ls src/token_world/mechanic/seeds/*.py | grep -v "_"` → 28 files). 3 are D-38 framework-gap stubs (persuade, cooperate, weather_reaction).
- **Test files created** (seed tests only): 27 in `tests/test_mechanic/test_seeds/` (mirrored tree).
- **New infrastructure files**: `src/token_world/mechanic/{validation.py, diagnostics.py}`; `tests/test_integration/{conftest.py, test_use_cases.py}`; `tests/test_use_cases/test_manifest_outcomes.py`; `tests/test_mechanic/test_{validation, diagnostics, harness_matcher}.py`; `tests/test_cli/test_{validate_mechanic, scaffold_mechanic, prune_diagnostics}.py`.
- **Documentation**: `docs/guides/authoring-mechanics.md` (665 lines, 15 `##` headings).
- **Scripts**: `scripts/{annotate_use_case_outcomes.py, check_worktree_base.sh}`.
- **Manifests annotated**: 35/35 in `.planning/use-cases/` via `scripts/annotate_use_case_outcomes.py`.
- **CLI surface** (via `token-world`): `create`, `list`, `delete` (pre-existing from Phase 0) + `validate-mechanic`, `scaffold-mechanic`, `prune-diagnostics` (added in Phase 4).

Phase-gate state at commit time:

- `uv run pytest -q` → **782 passed, 14 skipped, 0 xfailed**.
- `uv run ruff check src/` → clean.
- `uv run ruff format --check src/` → clean.
- `uv run mypy src/token_world/` → clean (64 source files).

## Deviations from Plan

### Auto-fixed

**1. [Rule 1 - Bug] Pre-commit late-stage regressions in `src/token_world/use_cases/loader.py` (ruff format drift) and `src/token_world/mechanic/seeds/fungible_pay.py` (mypy narrowing on `Any | None`).**
- **Found during:** Task 1 (running the phase gate's `ruff format --check src/` and `mypy src/token_world/`).
- **Issue:** loader.py had an over-wrapped f-string that `ruff format` would collapse; fungible_pay.py's `apply` read `kind` and `amount` via `.get()` (Any | None) and passed them into `_eligible_coins(str)` and `int(...)` without narrowing.
- **Fix:** Collapsed the loader.py f-string to one line; added `assert isinstance(kind, str)` + `assert isinstance(amount, int) and not isinstance(amount, bool)` after the get()s in fungible_pay.apply() (the equivalent guards already ran in check()).
- **Files modified:** `src/token_world/use_cases/loader.py`, `src/token_world/mechanic/seeds/fungible_pay.py`.
- **Commit:** `41680c6`.

### Adapted (plan accuracy)

**2. Wave 0 plan entry `tests/test_mechanic/test_loader_flat.py` corrected to `tests/test_mechanic/test_loader.py`.**
- **Found during:** Task 1 W8 gate.
- **Issue:** The plan text refers to `test_loader_flat.py` but the actual file 04-01 created is `test_loader.py` (the file provides new module-based discovery test coverage for MECH-03). Flagged as LOW severity by 04-REVIEWS.
- **Fix:** Updated VALIDATION.md's Wave 0 Requirements bullet to use the real filename plus a one-line note.

**3. Deferred-items.md drift (pre-existing validation.py E501 + ruff drift in test files) was incidentally resolved mid-phase.**
- **Found during:** Task 1 phase-gate (`ruff check src/` returned clean).
- **Issue:** deferred-items.md §04-02/04-03/04-05 flagged validation.py E501 as "awaiting 04-12 cleanup"; deferred-items.md §04-07 flagged ruff drift in test_seeds/ tests. 04-12's `ruff check src/` returns no errors — a downstream `ruff format` run (likely 04-09's `f824be3`) fixed the src drift; the test-tree drift remains a candidate for a future tooling plan if it ever fails a gate.
- **Decision:** Per the plan's optional-cleanup note, leave deferred-items.md intact as historical record (the entries still document what was found and why it was deferred at the time). No action needed for the src/ tree; test-tree ruff drift is still out of scope per CLAUDE.md §4.

No other deviations. No architectural changes, no checkpoints.

## Threat Flags

None. This plan only edits `.planning/**` artefacts (VALIDATION, REQUIREMENTS, ROADMAP, SUMMARY) plus the two Rule-1 regression fixes to clear the phase gate. No new network endpoints, auth paths, schema changes, or shell interpolation surface.

## Commits

| Task | Commit | Type | Summary |
|------|--------|------|---------|
| pre-gate fix | 41680c6 | fix | clear late-stage ruff-format + mypy regressions |
| T1 | 43c4616 | docs | flip VALIDATION.md to nyquist_compliant + approve phase gate |
| T2 | 7188dd4 | docs | mark Phase 4 complete in REQUIREMENTS.md + ROADMAP.md |
| T3 | (this commit) | docs | write 04-12-SUMMARY.md + phase retrospective notes for Phase 5 planner |

## Self-Check

- VALIDATION.md: `grep -c "nyquist_compliant: true"` → 2 (frontmatter + checkbox); `grep -c "wave_0_complete: true"` → 1; `grep -c "status: approved"` → 1; `grep -c "⬜ pending"` → 0.
- REQUIREMENTS.md: `grep -c "\- \[x\] \*\*MECH-03|MECH-04|MECH-05|MECH-06|TEST-02|AUTO-02|AUTO-03|UNIV-03"` → 8.
- ROADMAP.md: `grep -c "\- \[x\] \*\*Phase 4:"` → 1; `grep -cE "\[x\] 04-0[1-9]|\[x\] 04-1[0-2]"` → 12.
- Full suite: 782 passed, 14 skipped, 0 xfailed.
- Lint/format/mypy: all clean on `src/` tree.
- All 3 Task commits present in `git log --oneline` (41680c6, 43c4616, 7188dd4).
- STATE.md untouched (orchestrator owns it).
- 28 gap IDs accounted for in §2 (24 closed + 3 stub + 2 absorbed + 1 cross-phase).
- 3 D-38 stubs documented in §4 for Phase 5 planner.
