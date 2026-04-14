# Phase 08 — Emergence Substrate (Track C groundwork)

**Milestone:** v1.1 Emergence Tooling
**Mode:** Retroactively phased — code already shipped under direct-edit
**Commits:** `8f1f18e` (ExternalOperator + 8 tests), `0a95763` (seed + unattended runner)

## What shipped

1. **`src/token_world/operator/external.py`** — File-based yield→resolution
   protocol. `ExternalOperator.handle_yield(signal)` writes the yield JSON
   to `<universe>/operator_inbox/<tick_id>.yield.json` and blocks polling
   for `.resolved` / `.rejected` marker files written by an out-of-process
   orchestrator.
2. **`tests/test_operator/test_external.py`** — 8 tests: happy path, reject,
   timeout, kill-switch, malformed-resolution recovery, log append, factory
   env overrides.
3. **`scripts/seed_starter_universe.py`** — Creates Willowbrook: 2 rooms,
   7 entities with emergent hooks (locked chest, stone well, garden bed,
   whetstone, tabby cat, hearth), one resident agent (Mira). Handcrafted
   PersonalityBundle — deterministic, zero LLM cost.
4. **`scripts/run_unattended.py`** — PlaytestRunner driver wired to
   `external_operator_factory`. Safety rails: `--tick-budget`,
   `--yield-budget`, `--cost-ceiling` (refuses to start), `--timeout-per-yield`
   (forwards to env), `<universe>/.stop` kill switch.

## Why this is a GSD phase and not just "scripts we wrote"

The `ExternalOperator` protocol is a stable engine↔orchestrator contract. Future
phases (dashboard, overnight orchestration) depend on it. Documenting it as a
phase gives downstream work a PLAN/VERIFY surface to cite.

## Decisions (D-01, D-02)

- **D-01:** File-based protocol over shared-memory / IPC / database. Rationale:
  simple to reason about, trivially inspectable from the shell, no new runtime
  dependency, kill-switch by touching a file, JSON already the lingua franca
  of tick summaries.
- **D-02:** `ExternalOperator` lives alongside `OperatorHarness` rather than
  replacing it. Both implement the "harness" surface (shape-compatible
  `OperatorResult` / `ExternalOperatorResult`). `PlaytestRunner.harness_factory`
  chooses at wire-time.

## Verification (done via smoke + unit tests)

- Unit tests: 8/8 passing
- Smoke: `TOKEN_WORLD_BACKEND=claude-cli token-world playtest willowbrook --turns 2 --no-operator` completes clean
- Full suite: pending re-run post-Track-A/warmup landings

## Known gaps (deferred to Phase 12)

- `ExternalOperator` exists but nothing drives the inbox end of the protocol yet.
  Phase 12 builds the Claude Code orchestration loop that spawns authoring
  subagents per yield.
- `scripts/run_unattended.py` hasn't been exercised end-to-end against an
  active orchestrator. Phase 12 does.
