# Phase 6: Resident Agent & End-to-End Loop - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning
**Mode:** `--auto` (autonomous pick of recommended options, no human in the loop)

> **Auto-mode note:** This CONTEXT was produced by `/gsd-discuss-phase 6 --auto`. Every decision below picks the recommended/pragmatic option consistent with PROJECT.md principles and prior-phase patterns. No human has reviewed the selections; research and planning will run against these directly.

<domain>
## Phase Boundary

Phase 6 delivers three interlocking capabilities that together close the full simulation loop:

1. **Resident Agent** (AGENT-01..04) — A personality-driven LLM agent inhabits the world, issues text actions, receives grounded observations, persists memory across sessions, and can fork sessions for rollback.
2. **Quality Infrastructure** (TEST-04, TEST-05, TEST-07, AUTO-05, AUTO-06, AUTO-07, DVAL-03) — N-turn playtest runner with adversarial injection, deterministic quality scoring, system-prompt change detection, and use-case regression suite.
3. **Tick Summary Compression** (SIM-12) — Hierarchical online compression of tick-level summaries into batch and epoch summaries, keeping agent context bounded across long simulations.

The resident agent is **distinct from the operator agent**: the resident agent is a character inside the world (issues text actions, receives observations); the operator agent (Phase 4.1, Opus/Agent-SDK) sits outside the simulation authoring mechanics when the engine yields. Phase 6 builds the resident agent; the operator harness is already in place.

Explicitly OUT of scope for Phase 6:
- **Attention/consciousness/action duration** (SIM-09, SIM-10) — Phase 7.
- **Multi-agent coordination** (MULTI-01..03) — v2.
- **Sandboxing** (HARD-01) — v2.
- **Cost circuit breakers** (HARD-03) — v2.
- **Graph-based agent memory** (HARD-04) — v2; v1 uses SQLite table-based memory.
- **LLM-generated adversarial scenarios** — v1 uses scripted YAML scenarios only.

</domain>

<decisions>
## Implementation Decisions

> **Decision log convention:** Each decision has a D-NN id, cites the source (requirement, gap ID, or prior-phase decision), states the choice, and notes the alternative that was considered but not chosen. Rationale matches CLAUDE.md Operating Principle 6 ("ground truth obsession").

### Resident Agent Architecture — Raw Anthropic SDK Loop

- **D-01** — *Source: AGENT-01, AGENT-02; PROJECT.md Hybrid-SDK decision.* The resident agent is implemented with the **raw Anthropic Python SDK** (not Agent SDK) inside a simple synchronous `while` loop. Each iteration: build context (personality + rolling observation window + memory summary), call `client.messages.create(model="claude-sonnet-4-5", ...)`, extract the text response as the action. Rejected: Agent SDK for the resident agent. Rationale: Agent SDK is reserved for the operator (Opus authoring mechanics). The resident agent has no tools of its own — it only emits text actions. Using the raw SDK keeps it simple, deterministic, and cheap. The operator loop (Phase 4.1 `OperatorHarness`) handles yields from the engine; the resident agent loop handles action generation.
  - *Satisfies: AGENT-01, AGENT-02*

- **D-02** — *Source: AGENT-01; PROJECT.md "Budget: hobby project".* Resident agent model = **`claude-haiku-4-5`** (latest available Haiku) for normal turns; upgrade to `claude-sonnet-4-5` is a per-universe config key (`agent.model`, default `"claude-haiku-4-5"`). Rationale: Haiku is the cheapest capable model; the resident agent's action text doesn't require Sonnet-level quality — grounding quality comes from the engine, not the agent's words.
  - *Satisfies: AGENT-01*

- **D-03** — *Source: AGENT-01.* Personality is generated **once at agent creation** via a one-shot Sonnet call (structured output) producing a JSON personality bundle with fields: `name: str`, `archetype: str` (e.g. "curious wanderer", "cautious merchant"), `traits: list[str]` (3–5 adjectives), `backstory: str` (2–3 sentences), `speech_style: str` (e.g. "speaks in clipped sentences", "verbose and philosophical"). The bundle is stored as the `personality` property on the agent's graph node (JSON-serializable dict per CLAUDE.md property-value convention) AND mirrored as a dedicated `agent_personality` column in the `agent_memory` SQLite table (D-06) for fast retrieval without graph queries.
  - *Satisfies: AGENT-01*

- **D-04** — *Source: AGENT-02.* The resident agent's **system prompt** is assembled from: (1) the universe's `CLAUDE.md` world-rules section, (2) the personality bundle from D-03, (3) a static instruction block ("You are {name}. Issue actions as short imperative sentences. Be curious and exploratory."). The system prompt does NOT include history — history is in the user-turn context window (D-07).
  - *Satisfies: AGENT-02*

### Memory Persistence — SQLite `agent_memory` Table

- **D-05** — *Source: AGENT-03; CLAUDE.md "No ORM; raw sqlite3; universe.db".* Agent memory persists via a new **`agent_memory` SQLite table** in `universe.db`. Raw `sqlite3` with parameterized queries; no ORM. Schema: `agent_id TEXT, session_id TEXT, turn_number INTEGER, action_text TEXT, observation_text TEXT, timestamp_iso TEXT, tick_id TEXT`. Rejected: JSONL file per session. Rationale: `universe.db` is already the universe's persistent store; adding a table keeps all state in one file, queryable with standard SQL, consistent with the project's no-ORM raw sqlite3 convention.
  - *Satisfies: AGENT-03*

- **D-06** — *Source: AGENT-03; D-03.* A second table **`agent_sessions`** tracks session metadata: `session_id TEXT PRIMARY KEY, agent_id TEXT, started_at TEXT, forked_from_session_id TEXT NULLABLE, snapshot_id TEXT NULLABLE`. This is the session registry; `agent_memory` rows reference `session_id`. New session = new UUID. Fork = new session with `forked_from_session_id` set (D-08).
  - *Satisfies: AGENT-03, AGENT-04*

- **D-07** — *Source: AGENT-03; Phase 5 D-15 (bounded context principle).* Context delivered to the resident agent per turn = **rolling window of the last 10 turns** (action + observation pairs from `agent_memory`) + a **persisted memory summary** (a compressed narrative written by Haiku after every 10 turns, stored as `memory_summary TEXT` on `agent_sessions`). Rolling window + summary keeps context bounded regardless of session length. The `memory_summary` is regenerated (Haiku, cheap) every 10 turns from the full session history up to that point. Rejected: full session history (unbounded context growth). Rejected: graph-based memory (HARD-04 is v2).
  - *Satisfies: AGENT-03*

### Session Forking — Graph Snapshot + SQLite Savepoint

- **D-08** — *Source: AGENT-04; Phase 1 snapshot infrastructure.* Session forking uses the **existing graph snapshot mechanism** (Phase 1 `GraphPersistence.restore_snapshot` / `take_snapshot`) combined with the `forked_from_session_id` field in `agent_sessions` (D-06). To fork: (1) call `GraphPersistence.take_snapshot(summary="fork: <reason>")`, (2) create a new session record pointing to the parent session and snapshot_id, (3) the forked session begins from the same graph state as the fork point. The mechanics/ folder is NOT reverted on fork — only graph state. Rejected: git branch per fork (overkill for in-process forks; git history is still used by the mechanic versioning). Rejected: separate `.db` files per fork (unnecessary complexity; snapshot is sufficient). Rejected: SQLite SAVEPOINT/ROLLBACK TO (doesn't help with graph state which is in the graph layer, not raw SQL rows).
  - *Satisfies: AGENT-04*

### Playtest Runner — Separate CLI + Pytest Wrapper

- **D-09** — *Source: TEST-07, AUTO-05.* The playtest runner is implemented as a **separate CLI command** `token-world playtest <universe-slug> [--turns N] [--scenario <yaml>] [--seed <int>]` added to the existing Click group in `src/token_world/cli.py`. It orchestrates: load universe → create/resume agent session → for each turn: generate agent action (D-01) + run engine tick (call `SimulationEngine.run_tick`) + handle yield (call `OperatorHarness.handle_yield` if needed) + score turn (D-12) + write to playtest report. A thin pytest wrapper `tests/test_playtest/test_scenarios.py` invokes `token-world playtest` via subprocess for CI. Rejected: pure pytest implementation. Rationale: CLI is reusable from operator command line and agent scripts; pytest is just a CI caller.
  - *Satisfies: TEST-07, AUTO-05*

- **D-10** — *Source: AUTO-05; AGENT-02.* The resident agent loop inside the playtest runner uses **structured turns** with a configurable `--turns N` limit (default 20). Each turn is one call to `SimulationEngine.run_tick`. If the engine yields (no mechanic), the `OperatorHarness` is invoked automatically (unless `--no-operator` flag suppresses it). This makes the playtest runner self-healing: it can run unattended and author missing mechanics via Opus, then continue.
  - *Satisfies: AUTO-05, TEST-07*

- **D-11** — *Source: AUTO-05; PROJECT.md "Composition over specialization".* Adversarial scenario injection uses **YAML scenario files** (`scenarios/`) with a `turns:` list, each turn being either `action: "<text>"` (scripted) or `inject: adversarial|nonsense|repeat_last|edge_case` (injection type sampled by the runner). Injection rates are configurable per scenario (`adversarial_rate: 0.1`). Rejected: LLM-generated adversarial scenarios. Rationale: YAML scenarios are reproducible (same seed = same turns), cheap (no extra LLM call), and directly comparable to Phase 3 use-case manifests. LLM adversarial generation deferred to Phase 7+.
  - *Satisfies: AUTO-05*

### Quality Scoring — Deterministic Rubric with Optional LLM Judge

- **D-12** — *Source: AUTO-06, TEST-04.* Quality scoring is **rubric-based and deterministic** per turn: five heuristic metrics scored 0–1 each, averaged into a composite score written to the playtest report. Metrics: (1) `mechanic_match_rate` — was a mechanic matched (1.0) or did engine yield/refuse (0.0)?; (2) `observation_groundedness` — does observation text reference properties present in the projected state dict (substring check inherited from Phase 5 D-15)?; (3) `mutation_count` — are there mutations (1.0) vs empty tick (0.5)?; (4) `refusal_rate` — inverse of refusals per N turns (lower = better grounding); (5) `action_novelty` — edit-distance from previous 3 actions (prevents agent repetition loops). Rejected: LLM-judge (optional, see D-13).
  - *Satisfies: AUTO-06, TEST-04*

- **D-13** — *Source: TEST-04; AUTO-06.* An **optional Sonnet-judge pass** (`--judge` flag on `token-world playtest`) evaluates the full transcript after the run against a structured rubric (JSON output): coherence, personality consistency, world-rule adherence. Not run by default (costs ~$0.01/20 turns). CI does not use `--judge`. Human operator uses it for milestone reviews. Optional pass means TEST-04 "LLM-verifier regression tests" is satisfied at the expensive-run boundary.
  - *Satisfies: TEST-04*

### System Prompt Change Detection — File Hash + Git Diff

- **D-14** — *Source: TEST-05, AUTO-07.* System prompt change detection is implemented via a **hash registry** `prompts.sha256.json` written alongside each prompt artifact in the diagnostics substrate (Phase 4 D-21). At the start of each playtest run, the runner computes SHA-256 of the current classifier system prompt, observer system prompt, and agent system prompt (from D-04). If any hash differs from the stored baseline (persisted in `universe/prompts.sha256.json`), the runner logs a warning and automatically triggers a grounding regression run (D-15). No user intervention needed for detection.
  - *Satisfies: TEST-05, AUTO-07*

- **D-15** — *Source: TEST-05, AUTO-07; DVAL-03.* The **grounding regression run** is the use-case regression suite (D-16) re-run automatically whenever a system prompt hash changes (D-14). Detection triggers regression; regression results are appended to `universe/regression-history.jsonl`. This closes AUTO-07 ("prompt/instruction change detection triggers automated regression validation").
  - *Satisfies: AUTO-07, TEST-05*

### Use-Case Regression Suite — Phase 3 Manifests as E2E Tests

- **D-16** — *Source: DVAL-03; Phase 3 use-case library.* The use-case regression suite re-uses the **35 Phase 3 use-case manifests** (`use_cases/`) as end-to-end integration tests. Each manifest declares an `action` and an `expected_observation` pattern. The suite runs each action through `SimulationEngine.run_tick` against a pre-seeded graph (per manifest's `setup` section) and asserts (1) no yield (mechanic was matched), (2) observation contains expected pattern. A new pytest file `tests/test_regression/test_use_cases.py` parametrizes over all 35 manifests. Rejected: hand-authored E2E test cases. Rationale: Phase 3 already authored 35 manifests; reusing them is zero-duplication.
  - *Satisfies: DVAL-03*

### Tick Summary Compression — Online Batch→Epoch Pipeline (SIM-12)

- **D-17** — *Source: SIM-12; PROJECT.md "hierarchical tick summaries".* Tick summary compression is **online**, triggered after every tick-write by checking `len(list(universe/tick_summaries/ticks/*.json))`. When the count exceeds `compression.batch_size` (universe-config key, default 100), the compressor runs: (a) read the oldest 100 `ticks/*.json` files, (b) call Haiku once with all 100 summaries and produce a single `batch_<N>.json` (timestamp + key events + mutation counts + mechanic ids used), (c) delete the 100 individual tick files. When `len(batch_*.json) >= compression.epoch_size` (default 100), a similar epoch pass produces `epoch_<N>.json` from all batch files and deletes them. Rejected: deferred batch job (harder to trigger; easier to miss). Rejected: scheduled cron (adds infrastructure for a hobby project). Rationale: online compression is triggered by the normal write path; no separate daemon needed.
  - *Satisfies: SIM-12*

- **D-18** — *Source: SIM-12; Phase 5 D-21 (schema version).* Batch summary schema: `{schema_version: 2, kind: "batch", batch_id: N, first_tick: str, last_tick: str, tick_count: 100, key_events: list[str], mechanic_ids_used: list[str], total_mutations: int, agent_id: str, haiku_prompt_hash: str}`. Epoch summary schema: `{schema_version: 2, kind: "epoch", epoch_id: N, first_batch: N, last_batch: N, batch_count: 100, synopsis: str}`. Both extend `schema_version: 1` tick schema (Phase 5 D-21) with `kind` discriminator — forward-compat with any consumer that reads tick-level files.
  - *Satisfies: SIM-12*

- **D-19** — *Source: SIM-12; AGENT-03 (bounded context).* The compressor is implemented as a new module `src/token_world/engine/compressor.py` (`TickCompressor` class). The `TickSummaryWriter.write()` method (Phase 5) calls `TickCompressor.maybe_compress(universe_dir)` after each write — one conditional count check, <1ms when below threshold. Compressor uses Haiku (raw Anthropic SDK) for batch synthesis. `TickCompressor` is stateless; it reads/writes only filesystem files.
  - *Satisfies: SIM-12*

### Resident Agent Module Layout

- **D-20** — *Source: AGENT-01..04; CLAUDE.md "Imports: use public __init__.py APIs".* The resident agent lives in `src/token_world/resident/`. Public API via `__init__.py`: `ResidentAgent` class, `AgentMemory` storage class, `SessionManager` (create/fork/resume sessions), `PersonalityGenerator` (one-shot generation). CLI commands wired into existing `token-world` Click group.
  - *Satisfies: AGENT-01, AGENT-02, AGENT-03, AGENT-04*

- **D-21** — *Source: AGENT-01..04.* `ResidentAgent.run_turn(universe_dir) -> str` drives one turn: build context (D-07), call Haiku/Sonnet (D-01, D-02), return action text. Caller (playtest runner or interactive CLI) feeds the action to `SimulationEngine.run_tick` and stores result. `ResidentAgent` does NOT call the engine directly — clean separation of concerns.
  - *Satisfies: AGENT-01, AGENT-02*

### Interactive Single-Turn CLI

- **D-22** — *Source: AGENT-02; CLAUDE.md Script Catalog.* A `token-world agent-turn <universe-slug> [--agent <id>]` CLI command runs one interactive turn: agent generates action → engine executes → observation printed. If yield occurs, operator harness is invoked automatically. Enables manual stepping through a simulation without a playtest runner. Satisfies the "agent interacts via text actions" requirement at interactive granularity.
  - *Satisfies: AGENT-02*

### Playtest Report Format

- **D-23** — *Source: TEST-07; AUTO-06.* Playtest reports are written to `universe/playtest-reports/<run_id>.json` (structured JSON, schema-versioned) and a human-readable summary to stdout after the run. JSON schema includes: `run_id`, `scenario_file`, `turns` (list with `turn_number`, `action`, `observation`, `tick_id`, `score` fields per D-12), `aggregate_scores` (averages of all five metrics), `prompts_sha256` (snapshot of D-14 hashes at run start), `duration_ms`. Machine-readable report enables trend analysis across runs.
  - *Satisfies: TEST-07, AUTO-06*

### E2E Loop Scheduling — Single-Process Tight Loop

- **D-24** — *Source: AGENT-02; PROJECT.md "Single agent + engine for v1".* The end-to-end simulation loop is a **single-process synchronous tight loop** (no async, no queues). Agent generates action → engine runs tick → result stored → repeat. All three components (resident agent, simulation engine, operator harness) are called synchronously in sequence. Rejected: async/queued architecture. Rationale: hobby project, single agent in v1; async deferred to multi-agent v2. The engine is already synchronous; no reason to introduce async complexity.
  - *Satisfies: AGENT-02*

### Testing Strategy

- **D-25** — *Source: TEST-04, TEST-05, TEST-07; CLAUDE.md "Quick test: uv run pytest tests/ -x -q".* Testing is layered: (1) Unit tests for `ResidentAgent`, `AgentMemory`, `SessionManager`, `TickCompressor` in isolation with mocked LLM clients; (2) Integration tests for the playtest runner with real engine (cheapest path: haiku-only, no operator invocation, existing mechanics only — use `--no-operator` + seeded graph); (3) Regression tests (D-16) parametrized over 35 use-case manifests. Real LLM integration tests (`@pytest.mark.integration`) are kept in the `test_playtest/` tree and run manually or on milestone CI boundary.
  - *Satisfies: TEST-04, TEST-05, TEST-07*

### Claude's Discretion (planner + researcher have flexibility here)

- **D-26** — Exact personality generation prompt wording (schema is locked per D-03; prompt phrasing is tunable).
- **D-27** — `memory_summary` regeneration prompt (Haiku, every 10 turns — what to emphasize: recent events vs. long-arc narrative).
- **D-28** — Playtest runner progress output format (rich progress bar vs. plain stdout; default plain for CI compatibility).
- **D-29** — Whether `token-world agent-turn` auto-creates a new agent if no agent exists in the universe, or requires explicit `token-world agent-create` first. Recommended: auto-create with random personality.
- **D-30** — Exact edit-distance metric for `action_novelty` scoring (D-12 item 5): Levenshtein or cosine on word bags — planner picks cheapest.

</decisions>

<specifics>
## Specific Ideas

- The resident agent loop should feel like an LLM roleplay session: personality shapes the agent's word choices, and the rolling memory window gives it coherent recall of recent events. The grounding comes entirely from the engine/graph layer — the agent just generates plausible action text.
- The playtest runner is the "happy-path demo": a fresh universe, a generated personality agent, 20 turns, structured report. This is what closes the loop end-to-end and makes the simulation "real".
- Phase 3's 35 use-case manifests are a gold mine for regression testing — they already define action + expected observation; the regression suite just executes them through the real engine.
- `token-world playtest` with no scenario file should still work (pure agent-driven turns with no adversarial injection) — the scenario file is optional.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Vision & Decisions
- `.planning/PROJECT.md` §Key Decisions — Hybrid SDK (operator/tool-layer split); resident agent is raw-SDK, NOT Agent SDK
- `.planning/PROJECT.md` §Constraints — Python, flexible schema, persistence, hobby-project budget, grounding obsession
- `CLAUDE.md` — conventions, graph-is-ground-truth, JSON-serializable properties, two-node-types, operating principles

### Requirements (owned by this phase)
- `.planning/REQUIREMENTS.md` §Resident Agent — AGENT-01..04
- `.planning/REQUIREMENTS.md` §Testing — TEST-04, TEST-05, TEST-07
- `.planning/REQUIREMENTS.md` §Agent Autonomy — AUTO-05, AUTO-06, AUTO-07
- `.planning/REQUIREMENTS.md` §Design Validation — DVAL-03
- `.planning/REQUIREMENTS.md` §Simulation Engine — SIM-12 (tick summary compression)

### Phase 5 Outputs — Primary Inputs to Phase 6
- `.planning/phases/05-simulation-engine/05-CONTEXT.md` — engine decisions, especially D-20 (`TickSummary` schema schema_version=1 that batch compressor must extend), D-15 (grounding constraint Phase-5 cheap version deferred to TEST-04 here), D-21 (batch/epoch deferred to Phase 6)
- `.planning/phases/05-simulation-engine/05-VERIFICATION.md` — 7/7 success criteria verified; engine is end-to-end capable
- `src/token_world/engine/engine.py` — `SimulationEngine.run_tick(action_text, actor) -> TickResult` — the entry point Phase 6 calls
- `src/token_world/engine/summary_writer.py` — `TickSummaryWriter.write()` — Phase 6 hooks `TickCompressor.maybe_compress()` after this
- `src/token_world/engine/models.py` — `TickResult`, `ClassifiedAction`, `VerdictOk` — shapes Phase 6 consumes

### Phase 4.1 Outputs — Operator Harness
- `.planning/phases/04.1-operator-agent-harness/04.1-CONTEXT.md` — D-03 (scope boundary: Phase 4.1 is one-tick loop; Phase 6 builds N-turn runner on top), D-05 (dual entry points), D-07 (`YieldSignal` contract)
- `src/token_world/operator/harness.py` — `OperatorHarness.handle_yield(signal) -> OperatorResult` — called by playtest runner when engine yields
- `src/token_world/operator/yield_signal.py` — `YieldSignal` dataclass — contract for yield detection

### Phase 1 Outputs — Graph Snapshot (Session Forking)
- `.planning/phases/01-graph-foundation/01-CONTEXT.md` — snapshot/restore decisions; D-08 here extends this for session forking
- `src/token_world/graph/persistence.py` — `GraphPersistence.take_snapshot()`, `restore_snapshot()` — used by `SessionManager.fork_session()`

### Phase 3 Outputs — Use-Case Regression Suite
- `.planning/use-cases/` — 35 manifest files (spatial/social/resource/environmental/edge-case) — D-16 regression suite parametrizes over these
- `.planning/GAP-HANDOFF.md` — gap closure status; Phase 6 regression confirms Phase 5 closures are stable

### Stack & Architecture
- `.planning/research/STACK.md` — model routing (Haiku for resident agent per D-02; Haiku for batch compressor per D-19); Agent SDK only at operator layer

### New Code (this phase creates)
- `src/token_world/resident/__init__.py` — public API: `ResidentAgent`, `AgentMemory`, `SessionManager`, `PersonalityGenerator`
- `src/token_world/resident/agent.py` — `ResidentAgent` class (raw Anthropic SDK loop, D-01)
- `src/token_world/resident/memory.py` — `AgentMemory` SQLite adapter (D-05), `SessionManager` (D-06, D-08)
- `src/token_world/resident/personality.py` — `PersonalityGenerator` (D-03)
- `src/token_world/engine/compressor.py` — `TickCompressor` (D-17, D-18, D-19)
- `src/token_world/playtest/runner.py` — `PlaytestRunner` (D-09, D-10, D-11, D-23)
- `src/token_world/playtest/scorer.py` — `TurnScorer` rubric implementation (D-12)
- `tests/test_regression/test_use_cases.py` — use-case regression suite parametrized over 35 manifests (D-16)
- `tests/test_playtest/` — playtest integration tests (D-25)
- Additions to `src/token_world/cli.py` — `token-world playtest`, `token-world agent-turn` commands

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`SimulationEngine.run_tick(action_text, actor) -> TickResult`** (`src/token_world/engine/engine.py`) — the complete engine pipeline; Phase 6's playtest runner calls this in a loop.
- **`OperatorHarness.handle_yield(signal) -> OperatorResult`** (`src/token_world/operator/harness.py`) — already implemented; playtest runner calls this when `TickResult.yielded` is True.
- **`GraphPersistence.take_snapshot() / restore_snapshot()`** (`src/token_world/graph/persistence.py`) — session forking (D-08) reuses these directly.
- **`TickSummaryWriter.write()`** (`src/token_world/engine/summary_writer.py`) — Phase 6 hooks `TickCompressor.maybe_compress()` after each call; no changes to the writer itself.
- **`TickSummary` schema with `schema_version: 1`** — `D-18` extends to v2 for batch/epoch; individual tick files retain v1.
- **Phase 3 use-case manifests** (`.planning/use-cases/*.yaml`) — D-16 regression suite parametrizes over these; no new manifest authoring needed.
- **Phase 4 `DiagnosticsSink`** (`src/token_world/mechanic/diagnostics.py`) — playtest runner can write playtest diagnostics to the same substrate for consistency.
- **Raw `sqlite3` table pattern** (existing `graph_state`, `graph_events`, `graph_snapshots`) — `agent_memory` and `agent_sessions` tables follow the same lazy-init, parameterized-query pattern.
- **`ALLOWED_PROPERTY_TYPES`** (`src/token_world/graph/models.py`) — personality bundle (D-03) stored as a `dict` property on the graph node, which is allowed.

### Established Patterns
- **Raw Anthropic SDK call pattern** (see `src/token_world/engine/classifier.py`, `src/token_world/engine/observer.py`) — `ResidentAgent` follows the same `client.messages.create(...)` pattern.
- **Universe-config keys** (`src/token_world/engine/config.py`) — `agent.model`, `compression.batch_size`, `compression.epoch_size` follow the same `engine.*` namespace pattern.
- **Click command group** (`src/token_world/cli.py`) — `token-world playtest` and `token-world agent-turn` added as new Click commands in the existing group.
- **`@pytest.mark.integration` for LLM tests** (Phase 4.1 pattern) — real-LLM playtest tests use the same marker and are excluded from quick runs.

### Integration Points
- `TickSummaryWriter.write()` → call `TickCompressor.maybe_compress(universe_dir)` after write (D-19).
- `ResidentAgent.run_turn()` → output fed to `SimulationEngine.run_tick()` → `TickResult` stored in `AgentMemory`.
- If `TickResult.yielded` → `OperatorHarness.handle_yield(result.signal)` → await mechanic authoring → re-run tick.
- `PlaytestRunner.run()` → calls `TurnScorer.score(turn)` → appends to report JSON.

</code_context>

<deferred>
## Deferred Ideas

- **LLM-generated adversarial scenarios** — Phase 7+. Phase 6 uses scripted YAML only (D-11).
- **Graph-based agent memory** (HARD-04) — v2. Phase 6 uses SQLite table-based memory (D-05).
- **Attention/consciousness/interruption thresholds** (SIM-09, SIM-10) — Phase 7.
- **Multi-agent coordination** (MULTI-01..03) — v2.
- **Sandboxing** (HARD-01) — v2.
- **Cost circuit breakers** (HARD-03) — v2.
- **VCR recording for LLM playtest tests** — deferrable; Phase 4.1 D-13 already noted this.
- **Web dashboard for playtest report visualization** — out of scope for v1 (PROJECT.md "no Web UI").
- **Personality evolution over time** — interesting but scope-expanding; v2.
- **Multi-universe agent migration** — v2.

</deferred>

---

*Phase: 06-resident-agent-end-to-end-loop*
*Context gathered: 2026-04-13*
