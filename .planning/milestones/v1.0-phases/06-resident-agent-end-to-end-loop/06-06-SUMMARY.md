---
phase: 06-resident-agent-end-to-end-loop
plan: "06"
title: "Adversarial scenario pack + expanded AdversarialBank"
subsystem: playtest
tags: [adversarial, testing, injection, AUTO-05, D-11]
dependency_graph:
  requires: [06-04-SUMMARY.md]
  provides: [adversarial-bank, adversarial-scenario-pack]
  affects: [playtest-runner, injection-sampler]
tech_stack:
  added: []
  patterns: [categorized-corpus, tdd-red-green, yaml-scenario-files]
key_files:
  created:
    - src/token_world/playtest/adversarial.py
    - scenarios/adversarial/nonsense_barrage.yaml
    - scenarios/adversarial/rule_violation.yaml
    - scenarios/adversarial/repetition_loop.yaml
    - scenarios/adversarial/edge_case_stress.yaml
    - scenarios/adversarial/mixed_chaos.yaml
    - scenarios/adversarial/README.md
    - tests/test_playtest/test_adversarial.py
    - tests/test_playtest/test_scenarios_adversarial_pack.py
  modified:
    - src/token_world/playtest/scenarios.py
    - src/token_world/playtest/__init__.py
    - tests/test_playtest/test_scenarios_yaml.py
decisions:
  - "AdversarialBank uses ClassVar list of frozen dataclasses — stateless, instantiation is cheap, deterministic via caller-supplied RNG"
  - "InjectionSampler.sample adversarial path: single-line swap from hardcoded list to AdversarialBank().sample(local_rng)"
  - "Scenario YAML seeds 100-104 (one per file) — small, memorable, reproducible across CI"
metrics:
  duration_minutes: 22
  completed_date: "2026-04-13"
  tasks_completed: 2
  tasks_total: 2
  files_created: 9
  files_modified: 3
  tests_added: 20
  test_baseline: 1342
  test_final: 1362
---

# Phase 06 Plan 06: Adversarial scenario pack + expanded AdversarialBank — Summary

**One-liner:** Categorized AdversarialBank (55 entries, 5 categories, difficulty 1–3) replaces hardcoded 12-phrase list; 5 canonical adversarial scenario YAMLs cover nonsense barrage, rule-violation probing, repetition loops, edge-case stress, and mixed chaos.

---

## What Was Built

### AdversarialBank corpus (`src/token_world/playtest/adversarial.py`)

55 entries across 5 categories:

| Category | Count | Difficulty range |
|---|---|---|
| nonsense | 10 | 1–2 |
| rule_violation | 11 | 2–3 |
| boundary_probe | 11 | 1–3 |
| role_break | 9 | 1–3 |
| recursive_meta | 10 | 2–3 |
| extras | 4 | 1–3 |
| **Total** | **55** | |

All entries are narrative/simulation-level. The bank verifies no shell-injection patterns (`rm -rf`, backtick, `$(`, `&&`, `|| rm`) appear in any entry.

`AdversarialEntry` is a frozen dataclass with `text: str`, `category: Category`, `difficulty: Difficulty`. `AdversarialBank.sample(rng, *, category=None, max_difficulty=3)` provides filtered deterministic sampling.

### InjectionSampler swap (`src/token_world/playtest/scenarios.py`)

Single-line change in `_sample_adversarial`: replaced `local_rng.choice(_ADVERSARIAL_BANK)` with `AdversarialBank().sample(local_rng)`. The 12-phrase hardcoded list was removed. All existing InjectionSampler tests updated to verify against the bank's actual corpus.

### Adversarial scenario YAML files (`scenarios/adversarial/`)

| File | Turns | Seed | Purpose |
|---|---|---|---|
| `nonsense_barrage.yaml` | 20 | 100 | All inject:nonsense — stress classifier refusal path |
| `rule_violation.yaml` | 15 | 101 | 11 inject:adversarial + 4 scripted — probe conservation enforcement |
| `repetition_loop.yaml` | 10 | 102 | 1 scripted + 9 inject:repeat_last — drive action_novelty to 0 |
| `edge_case_stress.yaml` | 20 | 103 | All inject:edge_case — empty/long/special-char boundary testing |
| `mixed_chaos.yaml` | 30 | 104 | All 4 inject types + agent-decided — realistic combined pressure |

Each scenario can be run with:
```
token-world playtest <universe-slug> --scenario scenarios/adversarial/<name>.yaml
```

### README (`scenarios/adversarial/README.md`)

Documents each scenario's purpose, primary D-12 metric stressed, and how to interpret the playtest report aggregate scores (mechanic_match_rate, refusal_rate, action_novelty, composite).

---

## Test Coverage

20 new tests added across 2 test files:

**`tests/test_playtest/test_adversarial.py`** (8 tests):
- Category counts per bank (≥8 each, ≥50 total)
- Sample returns corpus entry text
- Deterministic with seed
- Category filter (`category="role_break"` returns only role_break)
- Difficulty filter (`max_difficulty=1` returns only difficulty-1)
- Unique entries (no duplicate text)
- No shell-injection patterns in corpus
- InjectionSampler adversarial inject uses bank corpus

**`tests/test_playtest/test_scenarios_adversarial_pack.py`** (12 tests):
- Load assertions for all 5 YAML files (turn counts, seeds, inject type presence)
- End-to-end integration: mixed_chaos drives PlaytestRunner 30 turns, no crash, 30 TurnRecords in report
- Parametrized seed range check (all seeds in [100, 110])
- README mentions all 5 scenario names

---

## AUTO-05 Satisfaction

AUTO-05 requires adversarial injection capability for the playtest runner. Combined with 06-04 (InjectionSampler + 4 inject types + Scenario YAML loader), this plan closes AUTO-05:

- 06-04 delivered the injection mechanism and runner integration
- 06-06 delivers the enriched adversarial content corpus (55 entries vs. 12) and 5 canonical test scenarios covering the full adversarial surface

---

## Verification: runner.py Not Modified

```
git diff HEAD src/token_world/playtest/runner.py
```
Output: empty — runner.py was not modified. Wave-3 parallel safety preserved.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_injection_sampler_adversarial_from_bank assertion**
- **Found during:** Task 1 GREEN phase
- **Issue:** The existing test in `test_scenarios_yaml.py` checked for phrases from the old 12-entry hardcoded list (e.g., "delete the world", "take all items"). After the swap to `AdversarialBank`, those phrases no longer appear in sampled output since the bank has different entries.
- **Fix:** Updated assertion to verify sampled strings are members of `AdversarialBank._ENTRIES` text set — a stronger, future-proof check.
- **Files modified:** `tests/test_playtest/test_scenarios_yaml.py`
- **Commit:** `442b0a8`

**2. [Rule 1 - Bug] Fixed test_mixed_chaos_scenario_drives_runner_end_to_end field name**
- **Found during:** Task 2 GREEN phase
- **Issue:** Test asserted `"action" in turn_record` but `TurnRecord` serializes as `action_text` (per `report.py` schema).
- **Fix:** Changed assertion to `"action_text" in turn_record`.
- **Files modified:** `tests/test_playtest/test_scenarios_adversarial_pack.py`
- **Commit:** `21f75df`

---

## Known Stubs

None — all scenario YAML files are fully specified with concrete turns; bank entries are complete strings with no placeholder text.

---

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. `AdversarialBank` is a local, deterministic, read-only data structure.

---

## Self-Check: PASSED

- adversarial.py: FOUND
- nonsense_barrage.yaml: FOUND
- mixed_chaos.yaml: FOUND
- README.md: FOUND
- test_adversarial.py: FOUND
- test_scenarios_adversarial_pack.py: FOUND
- Commit 442b0a8: FOUND
- Commit 21f75df: FOUND
- runner.py diff: CLEAN (not modified)
- Test count: 1362 passed (baseline 1342, +20 new)
