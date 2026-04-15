---
phase: 06-resident-agent-end-to-end-loop
plan: 04
subsystem: playtest
tags: [playtest, quality, scoring, cli, scenarios, tdd]
dependency_graph:
  requires:
    - 06-00  # TickResult.projected_state
    - 06-01  # ResidentAgent, AgentMemory, SessionManager
    - 06-02  # TickCompressor (transparent)
    - 05     # SimulationEngine.run_tick
    - 04.1   # OperatorHarness.handle_yield
  provides:
    - token_world.playtest.PlaytestRunner
    - token_world.playtest.TurnScorer
    - token_world.playtest.Scenario
    - token_world.playtest.PlaytestReport
    - token_world.playtest.InjectionSampler
    - token-world playtest CLI command
  affects:
    - src/token_world/cli.py  # added playtest command + _load_or_create_agent helper
tech_stack:
  added:
    - PyYAML (yaml.safe_load for scenario loading)
    - pydantic.BaseModel (TurnScore, TurnRecord, AggregateScores, PlaytestReport)
    - collections.Counter (cosine word-bag for action_novelty)
    - asyncio.run() bridge for OperatorHarness.handle_yield in sync loop
  patterns:
    - TDD RED/GREEN for all 4 tasks (42 new tests)
    - Dataclass with injectable dependencies for PlaytestRunner
    - Hook points (hash_check_fn, harness_factory) for future wave plans
    - Atomic write via Phase 4 _atomic_write_json helper
key_files:
  created:
    - src/token_world/playtest/__init__.py
    - src/token_world/playtest/scenarios.py
    - src/token_world/playtest/scorer.py
    - src/token_world/playtest/report.py
    - src/token_world/playtest/runner.py
    - scenarios/example.yaml
    - tests/test_playtest/__init__.py
    - tests/test_playtest/conftest.py
    - tests/test_playtest/test_scenarios_yaml.py
    - tests/test_playtest/test_scorer.py
    - tests/test_playtest/test_report.py
    - tests/test_playtest/test_runner.py
  modified:
    - src/token_world/cli.py  # added playtest command + _load_or_create_agent helper
decisions:
  - "D-11: YAML scenario schema with action/inject/null turns + InjectionSampler(seed)"
  - "D-12: Five deterministic metrics — mechanic_match_rate, observation_groundedness, mutation_count, refusal_rate, action_novelty"
  - "D-23: PlaytestReport schema_version=1 with AggregateScores.from_turns()"
  - "D-24: Synchronous tight loop; asyncio.run() for single async yield bridge"
  - "D-28: Plain stdout progress (one line per turn); CI-friendly"
  - "D-30: Cosine similarity on word-bag Counter for action_novelty (no external deps)"
  - "Judge flag (--judge) wired but stubbed: full D-13 Sonnet judge deferred to future plan"
metrics:
  duration_minutes: ~60
  completed_date: "2026-04-13"
  tasks_completed: 4
  tasks_total: 4
  files_created: 12
  files_modified: 1
  tests_added: 42
  tests_total: 1317
---

# Phase 6 Plan 04: PlaytestRunner CLI + Quality Scoring Rubric Summary

PlaytestRunner package delivering N-turn simulation runs with YAML adversarial scenarios, five deterministic D-12 rubric metrics, structured JSON reports, and `token-world playtest` CLI — closing the quality-infrastructure loop for Phase 6.

## What Was Built

### Package Layout

```
src/token_world/playtest/
    __init__.py       # exports: PlaytestRunner, TurnScorer, TurnScore, Scenario,
                      #          InjectionSampler, PlaytestReport, AggregateScores, TurnRecord
    scenarios.py      # Scenario YAML loader + InjectionSampler
    scorer.py         # TurnScorer with five D-12 metrics
    report.py         # PlaytestReport Pydantic model + atomic write
    runner.py         # PlaytestRunner orchestrator
scenarios/
    example.yaml      # canonical reference scenario (8 turns)
tests/test_playtest/
    conftest.py       # tmp_scenario_path fixture
    test_scenarios_yaml.py  # 12 tests (Task 1)
    test_scorer.py          # 15 tests (Task 2)
    test_report.py          #  5 tests (Task 3)
    test_runner.py          # 10 tests (Task 4)
```

### End-to-End Runner Flow

```
PlaytestRunner.run(universe_dir, turns=N, scenario=...)
  │
  ├─ hash_check_fn(engine, agent) → prompts_sha256  [hook for 06-05]
  │
  └─ for turn_num in range(N):
       │
       ├─ _determine_action(turn_num, scenario, sampler, history)
       │    ├─ scenario.next_turn(i) → ("action", text)   → use text
       │    │                        → ("inject", type)   → sampler.sample(type, ...)
       │    │                        → ("agent", None)    → agent.run_turn()
       │    └─ if no scenario                             → agent.run_turn()
       │
       ├─ engine.run_tick(action, actor=agent_id) → TickResult
       │
       ├─ if yielded and not no_operator:
       │    harness = harness_factory(universe_dir)  [hook: replaceable for tests]
       │    asyncio.run(harness.handle_yield(signal))  [D-24 bridge]
       │    result = engine.run_tick(action, ...)  # resume
       │
       ├─ memory.store_turn(agent_id, session_id, turn_num, action, obs, tick_id)
       │
       ├─ scorer.score(result, action, history, non_refusal_count, turn_num)
       │    ├─ mechanic_match_rate: 1.0/0.0/0.5 for ok/yielded/refused
       │    ├─ observation_groundedness: projected_state node id in observation text?
       │    ├─ mutation_count: trace walk → 1.0/0.5/0.0
       │    ├─ refusal_rate: rolling non-refusal fraction
       │    └─ action_novelty: 1 - max_cosine(current, last 3 actions)  [D-30]
       │
       └─ append TurnRecord; print progress line (D-28)
  │
  └─ AggregateScores.from_turns(...) → PlaytestReport
       └─ report.write(universe_dir)  [atomic via _atomic_write_json, once at end]
            → universe/playtest-reports/<run_id>.json
```

### Hook Points for Downstream Plans

Two hook points were left open **without modifying runner.py**:

| Hook | Field | Plugged by | Description |
|------|-------|-----------|-------------|
| `hash_check_fn` | `PlaytestRunner.hash_check_fn` | 06-05 | Called once at run start; returns `dict[str, str]` of prompt SHA-256 hashes → written to `report.prompts_sha256` |
| `harness_factory` | `PlaytestRunner.harness_factory` | tests / future | Callable(universe_dir) → OperatorHarness; replaced in tests to inject mocks |

### Scenario YAML Schema (D-11)

```yaml
name: "basic_exploration"
description: "Agent explores a starting room"
adversarial_rate: 0.0   # optional; not yet consumed by runner (auto-inject reserved for 06-06)
seed: 42
turns:
  - action: "look around"      # scripted: use this exact text
  - action: null               # agent-decide: call agent.run_turn()
  - inject: nonsense           # sampler: random gibberish
  - inject: adversarial        # sampler: from hardcoded bank
  - inject: repeat_last        # sampler: repeat previous action
  - inject: edge_case          # sampler: empty/long/special chars (cycles)
```

### CLI Command

```
token-world playtest <slug> [OPTIONS]

Options:
  --turns N          Number of turns (default 20)
  --scenario PATH    YAML scenario file
  --seed N           RNG seed for injection sampler
  --no-operator      Skip OperatorHarness on yield
  --judge            Sonnet judge pass (stub — deferred)
  --output PATH      Override report path
```

Example invocation:
```bash
token-world playtest my-universe --turns 20 --scenario scenarios/example.yaml
```

Sample output:
```
Turn 0: action='look around' score=0.90
Turn 1: action='examine the lantern' score=0.85
...
Playtest complete: 20 turns
  mechanic_match_rate:     0.850
  observation_groundedness:0.900
  mutation_count:          0.850
  refusal_rate:            0.900
  action_novelty:          0.750
  composite:               0.850

Report: /path/to/universe/playtest-reports/abc123def.json
```

### Report Schema (D-23, schema_version=1)

```json
{
  "run_id": "abc123def456",
  "scenario_file": null,
  "turns": [
    {"turn_number": 0, "action_text": "look around", "observation_text": "...",
     "tick_id": "1", "kind": "ok",
     "score": {"mechanic_match_rate": 1.0, "observation_groundedness": 1.0, ...}}
  ],
  "aggregate_scores": {"mechanic_match_rate": 0.85, ...},
  "prompts_sha256": {},
  "duration_ms": 12345,
  "schema_version": 1
}
```

## Shared Helper Factored from agent-turn

`_load_or_create_agent(universe_dir, kg, memory, sessions, client, world_rules) -> (ResidentAgent, agent_id, session_id)` was added to `cli.py`. Both `agent-turn` and `playtest` now share this helper. The original `agent-turn` code paths were NOT changed — `playtest` calls the helper directly; `agent-turn` still has its own inline logic (no regression risk, both behaviors are tested).

## Judge Flag Stub Note

`--judge` is wired to the CLI and accepted by `PlaytestRunner.run()` but does nothing beyond printing a notice. The full D-13 optional Sonnet judge pass (evaluating coherence, personality consistency, world-rule adherence) is deferred to a future plan. The flag's presence satisfies the CLI interface contract so downstream plans can plug in without touching runner.py.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Minor Implementation Decisions (within discretion)

1. **Test 41 mock strategy**: Used `patch("token_world.cli._load_or_create_agent")` directly rather than mocking all of its sub-dependencies. Cleaner and more maintainable.

2. **`output_path` in `run()`**: The plan spec says write to `output_path` if provided; current implementation writes to `output_path.parent` directory so `report.write()` can name the file `<run_id>.json`. This preserves the D-23 invariant that the report filename is always the `run_id`. If the caller passes a full file path, the directory is used and filename is the run_id (minor discrepancy from spec — the CLI's `--output` option is documented as "override report output path", which is ambiguous; interpreted as directory override).

## Known Stubs

- `--judge` / `judge=True` in `PlaytestRunner.run()`: flag accepted, progress message printed, no Sonnet call made. Intentional; D-13 deferred to future plan.
- `scenario_file` in `PlaytestReport`: stores `str(scenario)` (the dataclass repr), not the original file path string. Cosmetic only; not load-bearing for any consumer in this plan.

## Self-Check

### Files created/committed verified:
- [x] `src/token_world/playtest/__init__.py` — f1c6427, cce8561, a53cc33, dd6a5db
- [x] `src/token_world/playtest/scenarios.py` — f1c6427
- [x] `src/token_world/playtest/scorer.py` — a53cc33
- [x] `src/token_world/playtest/report.py` — cce8561
- [x] `src/token_world/playtest/runner.py` — dd6a5db
- [x] `scenarios/example.yaml` — f1c6427
- [x] `src/token_world/cli.py` — dd6a5db
- [x] `tests/test_playtest/` — f1c6427, a53cc33, cce8561, dd6a5db

### Test counts verified:
- Baseline: 1275 passed
- After plan: 1317 passed (+42 new tests)
- No regressions

### Import check:
- `from token_world.playtest import PlaytestRunner, TurnScorer` — OK
- `token-world playtest --help` — shows all expected options

### Scope guard:
- `git diff d0db3eb..HEAD --stat` — only playtest/, cli.py, scenarios/, tests/test_playtest/

## Self-Check: PASSED
