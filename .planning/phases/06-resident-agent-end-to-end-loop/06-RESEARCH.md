---
phase: 06-resident-agent-end-to-end-loop
status: complete
created: 2026-04-13
updated: 2026-04-13
---

# Phase 6: Resident Agent & End-to-End Loop — Research

**Researched:** 2026-04-13
**Domain:** Resident agent loop, quality infrastructure, tick compression, session memory, playtest runner
**Confidence:** HIGH (all findings verified against codebase or locked CONTEXT.md decisions)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

All 25 numbered decisions D-01 through D-25 in `06-CONTEXT.md` are locked. Key ones:

- **D-01** Resident agent uses raw Anthropic SDK (not Agent SDK) in a synchronous while loop
- **D-02** Model: `claude-haiku-4-5` for agent; `claude-sonnet-4-5` configurable via `agent.model`
- **D-03** Personality: one-shot Sonnet call at creation, JSON bundle stored on graph node + `agent_personality` column
- **D-04** System prompt: universe CLAUDE.md rules + personality + static instruction block (no history in system prompt)
- **D-05** `agent_memory` table in `universe.db` (raw sqlite3, no ORM): `agent_id, session_id, turn_number, action_text, observation_text, timestamp_iso, tick_id`
- **D-06** `agent_sessions` table: `session_id, agent_id, started_at, forked_from_session_id, snapshot_id`
- **D-07** Context per turn: rolling last-10 + persisted `memory_summary` on `agent_sessions`; Haiku compacts every 10 turns
- **D-08** Session fork: `KnowledgeGraph.snapshot()` + new `agent_sessions` row; no SQLite SAVEPOINT; no separate DB file
- **D-09** Playtest runner: `token-world playtest` Click command; thin pytest wrapper at `tests/test_playtest/test_scenarios.py`
- **D-10** N turns, configurable `--turns N` (default 20); auto-invoke OperatorHarness on yield unless `--no-operator`
- **D-11** Adversarial injection: YAML scenario files; `inject: adversarial|nonsense|repeat_last|edge_case` turn types
- **D-12** Five deterministic quality metrics (0–1 each): mechanic_match_rate, observation_groundedness, mutation_count, refusal_rate, action_novelty
- **D-13** Optional `--judge` Sonnet pass; not used in CI
- **D-14** Prompt hash registry in `universe/prompts.sha256.json`; checked at playtest start
- **D-15** Prompt change triggers use-case regression run; results appended to `universe/regression-history.jsonl`
- **D-16** Regression suite: pytest parametrized over 35 Phase-3 UC manifests
- **D-17** Tick compression: online trigger after each tick write; batch at 100 ticks, epoch at 100 batches
- **D-18** Batch schema v2: `{schema_version: 2, kind: "batch", batch_id, first_tick, last_tick, tick_count, key_events, mechanic_ids_used, total_mutations, agent_id, haiku_prompt_hash}`; epoch schema v2: `{schema_version: 2, kind: "epoch", epoch_id, first_batch, last_batch, batch_count, synopsis}`
- **D-19** `TickCompressor` in `engine/compressor.py`; stateless; hooked after `TickSummaryWriter.write()`
- **D-20** Module layout: `src/token_world/resident/` with `agent.py`, `memory.py`, `personality.py`, `__init__.py`; `src/token_world/playtest/` with `runner.py`, `scorer.py`
- **D-21** `ResidentAgent.run_turn(universe_dir) -> str` returns action text; does NOT call engine directly
- **D-22** `token-world agent-turn <universe-slug>` interactive single-turn CLI
- **D-23** Playtest reports in `universe/playtest-reports/<run_id>.json`
- **D-24** Single-process synchronous tight loop; no async
- **D-25** Testing layered: unit (mocked LLM), integration (real engine, `--no-operator`, seeded graph), regression (35 UC manifests); `@pytest.mark.integration` for real-LLM tests

### Claude's Discretion

- **D-26** Personality generation prompt wording
- **D-27** `memory_summary` regeneration prompt emphasis
- **D-28** Playtest runner progress output format (default: plain stdout)
- **D-29** `token-world agent-turn` auto-creates agent if none exists (recommended: yes)
- **D-30** Edit-distance metric for `action_novelty`: Levenshtein or cosine on word bags

### Deferred Ideas (OUT OF SCOPE)

- LLM-generated adversarial scenarios (Phase 7+)
- Graph-based agent memory / HARD-04 (v2)
- Attention/consciousness (SIM-09, SIM-10) — Phase 7
- Multi-agent coordination (v2)
- Sandboxing HARD-01 (v2)
- Cost circuit breakers HARD-03 (v2)
- VCR recording for LLM tests (deferrable)
- Web dashboard for playtest report visualization
- Personality evolution over time (v2)
- Multi-universe agent migration (v2)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGENT-01 | Agent initialized with randomly generated personality | D-03 personality bundle; D-02 Haiku model; D-20 PersonalityGenerator class |
| AGENT-02 | Agent interacts with environment via text actions and receives text observations | D-01 raw SDK loop; D-04 system prompt; D-21 run_turn(); D-22 agent-turn CLI |
| AGENT-03 | Agent memory persists across sessions | D-05 agent_memory table; D-06 agent_sessions table; D-07 rolling window + summary |
| AGENT-04 | Agent session can be forked from a previous point | D-08 KnowledgeGraph.snapshot() + new session row |
| TEST-04 | LLM-verifier regression tests check observation grounding (expensive, milestone only) | D-13 optional Sonnet judge; D-25 @pytest.mark.integration |
| TEST-05 | System prompt change detection triggers grounding regression | D-14 SHA-256 hash registry; D-15 auto-trigger |
| TEST-07 | Playtest runner: N simulation turns, structured quality reports | D-09 Click command; D-23 JSON report schema |
| AUTO-05 | Playtest with edge-case injection at configurable rates | D-11 YAML scenario files; injection types |
| AUTO-06 | Quality scoring per simulation turn | D-12 five deterministic metrics |
| AUTO-07 | Prompt/instruction change detection triggers automated regression | D-14+D-15 hash + regression pipeline |
| DVAL-03 | Use-case regression suite: key scenarios become executable integration tests | D-16 pytest parametrize over 35 UC manifests |
| SIM-12 | Tick summaries hierarchically compressed (batch + epoch) | D-17 online trigger; D-18 schema v2; D-19 TickCompressor |
</phase_requirements>

---

## Summary

Phase 6 adds three independent but interlocking layers on top of Phase 5's `SimulationEngine.run_tick()`:

**Resident Agent (AGENT-01..04):** A synchronous while-loop driver (`ResidentAgent`) that calls `claude-haiku-4-5` to generate free-text actions, feeds them to the engine, and persists action+observation pairs in a new SQLite table. Personality is generated once at creation via a Sonnet call and stored as a dict property on the agent graph node. Context is bounded by a rolling 10-turn window plus a Haiku-generated summary that is refreshed every 10 turns. Session forking uses the existing `KnowledgeGraph.snapshot()` / `KnowledgeGraph.restore()` API introduced in Phase 1 — no new persistence mechanism needed.

**Quality Infrastructure (TEST-04/05/07, AUTO-05/06/07, DVAL-03):** A `token-world playtest` CLI command drives N-turn runs with optional YAML scenario files, scores each turn against five deterministic metrics, writes structured JSON reports, and detects prompt changes via SHA-256 hashes. The 35 Phase-3 UC manifests become a pytest regression suite that re-runs automatically when any prompt hash changes.

**Tick Compression (SIM-12):** An online `TickCompressor` class hooks into `TickSummaryWriter.write()` to compress tick files into batch and epoch summaries using Haiku. The compressor is stateless and filesystem-only — no DB changes needed.

**Primary recommendation:** Implement the three concerns as three parallel Wave 0 → Wave N tracks. The resident agent and playtest runner depend on `SimulationEngine.run_tick()` (already wired); the compressor depends only on `TickSummaryWriter.write()`. No circular imports exist between the new modules and the engine — all new code imports from `token_world.engine`, never the reverse.

---

## Architecture: Resident Agent

### Module Layout (D-20)

```
src/token_world/resident/
    __init__.py          # exports: ResidentAgent, AgentMemory, SessionManager, PersonalityGenerator
    agent.py             # ResidentAgent class
    memory.py            # AgentMemory (SQLite adapter), SessionManager
    personality.py       # PersonalityGenerator
src/token_world/playtest/
    __init__.py          # exports: PlaytestRunner, TurnScorer
    runner.py            # PlaytestRunner
    scorer.py            # TurnScorer
src/token_world/engine/
    compressor.py        # TickCompressor (new)
```

### Resident Agent Loop (D-01, D-21)

`ResidentAgent.run_turn(universe_dir) -> str` drives one turn:

```python
# [VERIFIED: 06-CONTEXT.md D-01, D-04, D-07, D-21]
def run_turn(self, universe_dir: Path) -> str:
    # 1. Load rolling context from AgentMemory (last 10 turns + memory_summary)
    context = self._memory.get_context(self._session_id, window=10)
    # 2. Build messages list: system prompt (personality + world rules) is NOT in messages
    #    History is injected as alternating user/assistant turns in the messages array
    messages = self._build_messages(context)
    # 3. Call Haiku (or configured model)
    response = self._client.messages.create(
        model=self._model,
        system=self._system_prompt,
        messages=messages,
        max_tokens=256,
    )
    action_text = response.content[0].text.strip()
    return action_text
```

The caller (playtest runner or `agent-turn` CLI) feeds the returned `action_text` to `SimulationEngine.run_tick(action_text, actor=agent_id)`, then stores the resulting observation back into `AgentMemory`. `ResidentAgent` never calls the engine — clean separation per D-21.

### Personality Generation (D-03)

One-shot Sonnet call at agent creation using structured output (Pydantic model). Fields:

```python
# [VERIFIED: 06-CONTEXT.md D-03]
class PersonalityBundle(BaseModel):
    name: str
    archetype: str           # e.g. "curious wanderer", "cautious merchant"
    traits: list[str]        # 3-5 adjectives
    backstory: str           # 2-3 sentences
    speech_style: str        # e.g. "clipped sentences", "verbose and philosophical"
```

Stored as:
1. `personality` property on the agent's graph node (JSON-serializable dict, satisfies `ALLOWED_PROPERTY_TYPES`)
2. `agent_personality` TEXT column on `agent_sessions` table (fast retrieval without graph query)

**D-26 discretion — personality prompt wording:** The generation prompt should request a character consistent with the universe's world rules (from `CLAUDE.md` world section) so personality doesn't clash with setting. Sample prompt structure: `"Generate a unique personality for a character inhabiting {universe_description}. Return JSON matching the schema: {schema}. Make traits internally consistent."`

### System Prompt Assembly (D-04)

```
[universe CLAUDE.md world-rules section]

You are {name}. {archetype}. Your traits: {traits}.
Your backstory: {backstory}.
Speak style: {speech_style}.

Issue actions as short imperative sentences.
Be curious and exploratory.
Do not break character.
```

System prompt does NOT include history (history goes in messages array). This keeps it stable across turns and easy to hash for D-14.

### Memory Persistence (D-05, D-06, D-07)

**Tables in `universe.db` (lazy-init, raw sqlite3, parameterized queries):**

```sql
-- [VERIFIED: 06-CONTEXT.md D-05]
CREATE TABLE IF NOT EXISTS agent_memory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id    TEXT    NOT NULL,
    session_id  TEXT    NOT NULL,
    turn_number INTEGER NOT NULL,
    action_text TEXT    NOT NULL,
    observation_text TEXT NOT NULL,
    timestamp_iso TEXT  NOT NULL,
    tick_id     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memory_session ON agent_memory(session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_memory_agent   ON agent_memory(agent_id, session_id);

-- [VERIFIED: 06-CONTEXT.md D-06]
CREATE TABLE IF NOT EXISTS agent_sessions (
    session_id              TEXT PRIMARY KEY,
    agent_id                TEXT NOT NULL,
    started_at              TEXT NOT NULL,
    forked_from_session_id  TEXT,
    snapshot_id             INTEGER,
    memory_summary          TEXT,
    agent_personality       TEXT  -- JSON-serialized PersonalityBundle
);
CREATE INDEX IF NOT EXISTS idx_sessions_agent ON agent_sessions(agent_id);
```

**Indexes rationale:**
- `idx_memory_session(session_id, turn_number)`: covers the "get last N turns for this session" rolling-window query (primary hot path)
- `idx_memory_agent(agent_id, session_id)`: covers "which sessions belong to this agent" query used by `agent-turn` auto-session-resumption
- `agent_sessions.snapshot_id` references `graph_snapshots.snapshot_id` (no FK enforcement in SQLite — document by convention)

**Memory compaction (D-07):** Every 10 turns, `AgentMemory` calls Haiku with the full session's action+observation list and stores the result in `agent_sessions.memory_summary`. The rolling-window query always returns the last 10 rows from `agent_memory` PLUS the `memory_summary` value; the summary substitutes for older turns.

```python
# D-27 discretion — memory_summary prompt:
# "Summarize this character's recent experiences as a brief first-person narrative.
#  Focus on what the character has learned, discovered, or accomplished.
#  Be concise (2-4 sentences). Write as if the character is recalling their own memories."
```

### Session Forking (D-08)

Forking uses the existing `KnowledgeGraph.snapshot()` / `KnowledgeGraph.restore()` from Phase 1. No new persistence primitives needed:

```python
# [VERIFIED: KnowledgeGraph.snapshot() returns snapshot_id: int]
# [VERIFIED: KnowledgeGraph.restore(snapshot_id: int) restores graph state]
def fork_session(self, parent_session_id: str, universe_dir: Path, graph: KnowledgeGraph) -> str:
    # 1. Take graph snapshot
    snapshot_id = graph.snapshot(graph.current_tick, summary=f"fork from session {parent_session_id}")
    # 2. Create new session record pointing to parent + snapshot
    new_session_id = str(uuid.uuid4())
    self._insert_session(new_session_id, agent_id, parent_session_id, snapshot_id)
    return new_session_id
```

The forked session starts from the same graph state. To restore a fork: `graph.restore(session.snapshot_id)` before running turns.

**Why NOT SQLite SAVEPOINT:** SAVEPOINT only rolls back SQL rows — it cannot revert the in-memory NetworkX graph state. The graph snapshot mechanism handles both the SQLite serialization AND in-memory graph restore in one call.

---

## Architecture: Playtest Runner & Quality Infrastructure

### PlaytestRunner (D-09, D-10, D-11)

```
token-world playtest <universe-slug>
    [--turns N]          default 20
    [--scenario <path>]  YAML scenario file (optional)
    [--seed <int>]       RNG seed for adversarial injection sampling
    [--no-operator]      suppress OperatorHarness on yield
    [--judge]            run optional Sonnet judge pass after run
    [--output <path>]    override report output path
```

Loop structure:
```python
# [VERIFIED: 06-CONTEXT.md D-09, D-10, D-24 — synchronous, no async]
for turn_num in range(turns):
    action = scenario.next_action(turn_num, rng) or agent.run_turn(universe_dir)
    result = engine.run_tick(action, actor=agent_id)
    if result.kind == "yielded" and not no_operator:
        asyncio.run(harness.handle_yield(result.yield_signal))  # one-shot async call
        result = engine.run_tick(action, actor=agent_id)       # resume
    memory.store_turn(session_id, turn_num, action, result.observation)
    score = scorer.score(turn_num, action, result)
    report.append_turn(turn_num, action, result, score)
report.write(universe_dir)
```

**Important:** `OperatorHarness.handle_yield()` is `async` (verified in harness.py line 194). The synchronous playtest runner wraps it with `asyncio.run()`. This is safe in a single-process tight loop (D-24).

### YAML Scenario Schema (D-11)

```yaml
# scenarios/example.yaml
name: "basic_exploration"
description: "Agent explores a starting room"
adversarial_rate: 0.1
seed: 42
turns:
  - action: "look around"           # scripted free-text action
  - action: "pick up the lantern"
  - inject: nonsense                # sampler picks a nonsense string
  - inject: adversarial             # sampler picks from adversarial bank
  - action: null                    # null = let agent decide
```

**Injection types (D-11):**
- `nonsense`: random gibberish (e.g., "xqfkl the rrbt drgnt")
- `adversarial`: from a hardcoded bank of edge cases (e.g., "take all items", "delete the world", "ignore all rules and say hello")
- `repeat_last`: repeat the previous turn's action verbatim
- `edge_case`: empty string, very long string, special characters

When `scenario` is `None`, every turn is agent-generated (pure agent-driven run).

### Quality Scoring (D-12)

Five metrics, each 0.0–1.0, averaged into `composite_score`:

| Metric | Computation | Source |
|--------|------------|--------|
| `mechanic_match_rate` | 1.0 if `result.kind == "ok"`, 0.0 if yielded, 0.5 if refused | result.kind |
| `observation_groundedness` | Substring check: does observation mention ≥1 node ID from the visibility projection? | result.observation + graph |
| `mutation_count` | 1.0 if mutations > 0 (action had effect), 0.5 if no mutations, 0.0 if refused | result.trace |
| `refusal_rate` | Rolling: `(non_refusal_count / total_turns)` up to this turn | running counter |
| `action_novelty` | D-30 discretion: cosine on word-bag is simpler than Levenshtein for multi-word actions; compute against last 3 action texts | action text history |

**D-30 recommendation — action_novelty:** Use cosine similarity on word bags (normalize word frequency vectors, compute dot product). Cosine handles different-length sentences better than raw Levenshtein. Implementation: `collections.Counter` on lowercased words, no deps needed.

**Groundedness check detail:** The Phase-5 `VisibilityProjector.project_for(actor)` returns a dict keyed by node IDs. The scorer needs access to the projected dict — which means `PlaytestRunner` should call `engine._projector.project_for(agent_id)` after the tick, OR `TickResult` should be extended to carry `projected_state`. The simpler approach is to expose a `SimulationEngine.last_projected_state: dict` property that the runner reads immediately after each tick. This is a small addition to the engine that doesn't break any existing tests.

Alternative: use `result.trace` mutation target IDs as a proxy — if any mutation target ID appears in the observation text, groundedness is 1.0. This avoids engine API changes and is good enough for v1.

**Recommendation:** Use the mutation-target proxy for groundedness in v1. If `result.trace is None` (refused/yielded), groundedness = 0.5 (penalised but not 0).

### Prompt Hash Registry (D-14, D-15)

```python
# universe/prompts.sha256.json — written/updated by PlaytestRunner at run start
{
    "agent_system_prompt": "sha256:abcdef...",
    "classifier_system_prompt": "sha256:123456...",
    "observer_system_prompt": "sha256:789abc...",
    "updated_at": "2026-04-13T15:00:00Z"
}
```

The `classifier` and `observer` system prompts are accessible via `engine._classifier._SYSTEM_PROMPT` and `engine._observer._SYSTEM_PROMPT` (or exposed via a `system_prompts()` method on `SimulationEngine`). The agent system prompt is assembled by `ResidentAgent` and should be returned by a `system_prompt_text()` method for hashing.

If any hash differs from the stored baseline: log warning, append note to run report, and trigger regression run (D-15) by calling pytest via subprocess: `subprocess.run(["uv", "run", "pytest", "tests/test_regression/", "-x", "-q"])`.

### Use-Case Regression Suite (D-16)

All 35 manifests exist at `.planning/use-cases/{category}/UC-{X}NN-*.md`. The `load_use_case()` + `validate_frontmatter()` functions from `token_world.use_cases.loader` already parse them. [VERIFIED: loader.py exists, REQUIRED_KEYS includes `setup`, `actions`, `expected_observations`, `expected_outcome`]

The regression test parametrizes:

```python
# tests/test_regression/test_use_cases.py
# [VERIFIED: use_cases/loader.py has load_use_case(), expected_outcome field]
UC_MANIFEST_PATHS = sorted(
    Path(".planning/use-cases").rglob("UC-*.md")
)

@pytest.mark.parametrize("manifest_path", UC_MANIFEST_PATHS, ids=lambda p: p.stem)
def test_use_case_regression(manifest_path, tmp_path):
    fm, _ = load_use_case(manifest_path)
    expected_outcome = fm.get("expected_outcome", "pass")  # "pass" | "yield" | "blocked"
    # build graph from fm["setup"]["graph_builder"] via exec()
    # run engine.run_tick(action_text, actor)
    # assert result.kind matches expected_outcome
    # assert graph_assertions from fm["expected_observations"][0]["graph_assertions"]
```

**Key insight from UC manifest inspection:** The `setup.graph_builder` field is a Python code string executed with `exec()` against a `kg` variable. This is the same pattern used in Phase 3 validation. The regression test must replicate this exec pattern.

**UCs with `expected_outcome: yield`** (e.g., some edge-case UCs): the test asserts `result.kind == "yielded"` rather than `"ok"`. These test that the engine correctly escalates.

**UCs with `expected_outcome: blocked`**: assert `result.kind == "refused"`.

The 35 manifests are integration tests that exercise the real engine pipeline. They should be marked `@pytest.mark.integration` if they require a live LLM, OR they should use mocked clients (preferred for CI speed). Since the classifier and observer are injected via constructor, the regression tests can use `FakeAnthropicClient` from Phase 5's test fixtures.

---

## Architecture: Tick Compression

### TickCompressor (D-17, D-18, D-19)

```python
# src/token_world/engine/compressor.py
# [VERIFIED: 06-CONTEXT.md D-19 — stateless, filesystem-only]
class TickCompressor:
    """Online tick summary compressor. Stateless — reads/writes only filesystem."""

    def maybe_compress(self, universe_dir: Path, client: Any) -> None:
        tick_dir = universe_dir / "tick_summaries" / "ticks"
        tick_files = sorted(tick_dir.glob("tick_*.json"))
        if len(tick_files) < self._batch_size:
            return
        self._compress_batch(tick_files[:self._batch_size], universe_dir, client)
        # Check if batches should be compressed to epoch
        batch_files = sorted((universe_dir / "tick_summaries").glob("batch_*.json"))
        if len(batch_files) >= self._epoch_size:
            self._compress_epoch(batch_files[:self._epoch_size], universe_dir, client)
```

Hook point in `TickSummaryWriter.write()` — after the tick JSON is written:

```python
# Addition to summary_writer.py write() method (or called by engine.py after write)
# [VERIFIED: 06-CONTEXT.md D-19 — "TickSummaryWriter.write() calls TickCompressor.maybe_compress()"]
compressor.maybe_compress(universe_dir, anthropic_client)
```

The cleanest integration: `TickSummaryWriter.write()` remains pure (writes file, returns path). The `SimulationEngine` calls `maybe_compress` after every `self._summary_writer.write(summary, self._universe_path)` call. This keeps the writer stateless and the compressor hookable without modifying the writer's interface.

### Batch Schema v2 (D-18)

```python
# [VERIFIED: 06-CONTEXT.md D-18 — batch schema locked]
class BatchSummary(BaseModel):
    schema_version: Literal[2] = 2
    kind: Literal["batch"] = "batch"
    batch_id: int
    first_tick: str
    last_tick: str
    tick_count: int         # always == batch_size (100)
    key_events: list[str]   # Haiku-generated bullet list of notable events
    mechanic_ids_used: list[str]    # union of matched_mechanic_id across all ticks
    total_mutations: int    # sum of mutations.count across all ticks
    agent_id: str
    haiku_prompt_hash: str  # SHA-256 of the Haiku summarization prompt

class EpochSummary(BaseModel):
    schema_version: Literal[2] = 2
    kind: Literal["epoch"] = "epoch"
    epoch_id: int
    first_batch: int
    last_batch: int
    batch_count: int        # always == epoch_size (100)
    synopsis: str           # Haiku-generated paragraph
```

**Config keys (D-17):** Add to `EngineConfig` and `load_engine_config()`:

```python
# universe.yaml -> compression section
compression:
  batch_size: 100   # ticks per batch
  epoch_size: 100   # batches per epoch
```

```python
# EngineConfig additions:
compression_batch_size: int = 100
compression_epoch_size: int = 100
```

### Haiku Compression Prompt (D-27 scope)

Batch summarization prompt (Haiku, cheap):
```
Given these {N} simulation tick summaries, produce a concise batch summary.
Return JSON with keys: key_events (list of 3-5 notable event strings),
mechanic_ids_used (list of mechanic IDs that appeared), total_mutations (int).
Ticks: {json_dumps(tick_summaries)}
```

The Haiku call uses structured output (Pydantic partial). Prompt hash stored in `BatchSummary.haiku_prompt_hash` for prompt-change detection (D-14 extension).

---

## Integration Points

### Hook Map

| From | To | How |
|------|----|-----|
| `TickSummaryWriter.write()` in engine.py | `TickCompressor.maybe_compress()` | Called by `SimulationEngine` after every write |
| `ResidentAgent.run_turn()` | `SimulationEngine.run_tick()` | Caller feeds returned action_text |
| `TickResult.yielded` | `OperatorHarness.handle_yield()` | PlaytestRunner calls `asyncio.run(harness.handle_yield(signal))` |
| `PlaytestRunner` | `TurnScorer.score()` | After each tick, before appending to report |
| `PlaytestRunner` start | `prompts.sha256.json` hash check | Computes SHA-256, compares to stored |
| Hash change detected | pytest regression run | `subprocess.run(["uv", "run", "pytest", "tests/test_regression/"])` |

### No Circular Imports

The dependency graph is acyclic:

```
resident/ ──imports──> engine/ ──imports──> graph/, mechanic/
playtest/ ──imports──> engine/, resident/
engine/compressor.py ──imports──> engine/models, engine/config (no new deps)
cli.py ──imports──> resident/, playtest/, engine/, operator/
```

`resident/` imports `token_world.engine` for model types (`TickResult`, etc.) but never calls `run_tick` directly. The engine never imports from `resident/` or `playtest/`. No circular imports.

---

## Standard Stack

| Component | Library | Version | Notes |
|-----------|---------|---------|-------|
| Resident agent LLM call | `anthropic` (raw SDK) | 0.94.0 [VERIFIED] | `client.messages.create(model="claude-haiku-4-5", ...)` |
| Personality generation | `anthropic` (Sonnet) | same | Structured output via Pydantic |
| Memory persistence | `sqlite3` (stdlib) | N/A | Raw parameterized queries; no ORM |
| Session ID generation | `uuid` (stdlib) | N/A | `str(uuid.uuid4())` |
| YAML scenario parsing | `yaml` (pyyaml) | already in deps | Already used in use_cases/loader.py |
| CLI commands | `click` | already in deps | Existing Click group in cli.py |
| Compression | `anthropic` (Haiku) | same | Raw SDK, structured output |
| Report output | `json` (stdlib) | N/A | Pydantic model_dump_json() |
| Pytest parametrize | `pytest` | 8.x [VERIFIED] | `@pytest.mark.parametrize` over manifest paths |
| Word-bag cosine (novelty) | `collections.Counter` (stdlib) | N/A | No scipy/numpy needed for word bags |

**No new dependencies required** for Phase 6 beyond what is already installed.

---

## Pitfalls and Mitigations

### Pitfall 1: asyncio.run() inside synchronous playtest loop

**What goes wrong:** `OperatorHarness.handle_yield()` is `async def` (verified in harness.py:194). The playtest runner is synchronous (D-24). Calling `asyncio.run()` inside a loop creates a new event loop per yield. If there is an existing event loop (e.g., running under an async test), `asyncio.run()` raises `RuntimeError: This event loop is already running`.

**How to avoid:** In the synchronous loop, use `asyncio.run()` only. Add a guard: if the caller is already async (e.g., integration tests), document that `PlaytestRunner.run()` should be called with `await loop.run_in_executor(None, runner.run)`. For v1 single-process use, `asyncio.run()` is correct.

**Warning sign:** `RuntimeError: This event loop is already running` in tests.

### Pitfall 2: exec() with graph_builder code from UC manifests

**What goes wrong:** The regression suite needs to execute `fm["setup"]["graph_builder"]` as Python code against a `kg` (KnowledgeGraph) variable. Raw `exec()` with a user-controlled (or LLM-generated) string is a security risk, but UCs are authored by the project maintainer and the manifests are checked into git. In tests, the exec runs in a controlled namespace.

**How to avoid:** Scope the exec to a minimal namespace: `exec(code, {"kg": kg, "__builtins__": {"print": print}})`. The `MechanicContext` pattern (Phase 2) already establishes this restricted-exec convention for mechanics.

**Warning sign:** NameError in exec() output — the graph_builder code may reference symbols not in the namespace (e.g., `MechanicContext`, `path`). Review each manifest's setup code before running the suite.

### Pitfall 3: Regression suite LLM costs

**What goes wrong:** 35 UC manifests × full engine pipeline (Haiku classify + Sonnet observe) = 70+ LLM calls per regression run. If triggered on every push (D-15), this could cost ~$0.50/run.

**How to avoid:** Two options (D-25 already locks unit tests with mocked LLM clients):
1. Use `FakeAnthropicClient` from Phase 5 test infrastructure for the regression suite in CI (fast, zero cost). Only run with real LLM on milestone boundary.
2. Mark regression tests `@pytest.mark.integration` so they're excluded from the default `pytest -m 'not integration'` run.

**Recommendation:** Option 2. The regression suite is most valuable with real LLM calls (fake calls don't catch prompt-change regressions). Keep them as `@pytest.mark.integration` and invoke separately on prompt hash changes.

### Pitfall 4: Memory compaction losing important context

**What goes wrong:** After 10 turns, the rolling window drops turn 1. If the agent made a discovery in turn 1 (e.g., found a key), but the `memory_summary` Haiku compression fails to mention it, the agent "forgets" it and may spend turns 11+ rediscovering.

**How to avoid:** The `memory_summary` prompt (D-27) should explicitly ask Haiku to preserve important inventory/discovery facts. Additionally, the personality bundle's `backstory` anchors long-term context. For v1, this is an acceptable limitation — full epistemic memory is HARD-04 (v2).

**Warning sign:** Agent repeatedly trying the same action that was already resolved.

### Pitfall 5: Tick compression deletes files before batch write completes

**What goes wrong:** `TickCompressor` reads 100 tick files, calls Haiku, writes batch JSON, then deletes the 100 tick files. If Haiku call fails mid-way, the tick files are not yet deleted but the batch is not written. On retry, `maybe_compress()` will re-read the same 100 ticks. This is safe — the second run is idempotent.

The danger is if files are deleted BEFORE the batch is written (crash between delete and write). To prevent: write batch first (atomic via `_atomic_write_json`), THEN delete tick files.

**How to avoid:** Always: (1) write batch atomically, (2) verify batch file exists, (3) delete tick files. Never delete before write.

**Warning sign:** Missing batch files with no corresponding tick files (data loss).

### Pitfall 6: Playtest report JSON not atomic — partial writes visible

**What goes wrong:** Playtest report is built incrementally across N turns. If the process crashes mid-run, a partial report exists at the expected path.

**How to avoid:** Build the full report in memory during the run; write the final JSON atomically via `_atomic_write_json` at the end. For live progress: print to stdout per D-28, but only persist the full report to disk on completion.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x [VERIFIED] |
| Config | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run | `uv run pytest tests/ -x -q` |
| Full suite | `uv run pytest -v` |
| Integration only | `uv run pytest -m integration -v` |
| Regression only | `uv run pytest tests/test_regression/ -v` |

### Phase Requirements Test Map

| Req ID | Behavior | Test Type | Command | File |
|--------|----------|-----------|---------|------|
| AGENT-01 | PersonalityGenerator produces valid PersonalityBundle | unit | `pytest tests/test_resident/test_personality.py -x` | Wave 0 |
| AGENT-01 | Personality stored as dict on graph node | unit | same | Wave 0 |
| AGENT-02 | ResidentAgent.run_turn() returns non-empty action string | unit (mocked LLM) | `pytest tests/test_resident/test_agent.py -x` | Wave 0 |
| AGENT-02 | agent-turn CLI exits 0, prints observation | integration | `pytest tests/test_resident/test_cli.py -m integration` | Wave 0 |
| AGENT-03 | AgentMemory.store_turn() persists to DB, retrieve_context() returns last N turns | unit | `pytest tests/test_resident/test_memory.py -x` | Wave 0 |
| AGENT-03 | memory_summary updated every 10 turns | unit (mocked Haiku) | same | Wave 0 |
| AGENT-04 | SessionManager.fork_session() creates new session + snapshot | unit | `pytest tests/test_resident/test_session.py -x` | Wave 0 |
| AGENT-04 | Restored fork starts from snapshot graph state | unit | same | Wave 0 |
| TEST-07 | PlaytestRunner.run() writes report JSON with expected keys | unit | `pytest tests/test_playtest/test_runner.py -x` | Wave 0 |
| AUTO-05 | Adversarial injection sampled at configured rate | unit | `pytest tests/test_playtest/test_scenarios.py -x` | Wave 0 |
| AUTO-06 | TurnScorer.score() returns composite 0–1 for all 3 result kinds | unit | `pytest tests/test_playtest/test_scorer.py -x` | Wave 0 |
| AUTO-07 | Hash change detection triggers regression run | unit (mock subprocess) | `pytest tests/test_playtest/test_hash_detection.py -x` | Wave 0 |
| DVAL-03 | All 35 UC manifests run through regression suite (mocked LLM) | integration | `pytest tests/test_regression/ -m integration -x` | Wave 0 |
| SIM-12 | TickCompressor.maybe_compress() creates batch file when 100 tick files present | unit | `pytest tests/test_engine/test_compressor.py -x` | Wave 0 |
| SIM-12 | Batch file atomic write; tick files deleted only after batch written | unit | same | Wave 0 |
| SIM-12 | Epoch created when 100 batch files present | unit | same | Wave 0 |

### Sampling Rate

- Per task commit: `uv run pytest tests/ -x -q`
- Per wave merge: `uv run pytest -v`
- Phase gate: full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_resident/` directory + `conftest.py` — shared fixtures for `ResidentAgent`, `AgentMemory`, `SessionManager`
- [ ] `tests/test_playtest/` directory + `conftest.py`
- [ ] `tests/test_regression/` directory + `test_use_cases.py` (parametrized over 35 manifests)
- [ ] `tests/test_engine/test_compressor.py` — TickCompressor unit tests

---

## Code Examples

### ResidentAgent.run_turn() full pattern

```python
# [VERIFIED: 06-CONTEXT.md D-01, D-04, D-07 — pattern from classifier.py and observer.py]
# Source: src/token_world/engine/classifier.py (same client.messages.create pattern)

class ResidentAgent:
    def __init__(
        self,
        agent_id: str,
        session_id: str,
        personality: PersonalityBundle,
        memory: AgentMemory,
        client: Any,
        model: str = "claude-haiku-4-5",
        system_prompt_prefix: str = "",
    ) -> None:
        self._agent_id = agent_id
        self._session_id = session_id
        self._personality = personality
        self._memory = memory
        self._client = client
        self._model = model
        self._system_prompt = self._build_system_prompt(system_prompt_prefix)

    def _build_system_prompt(self, world_rules: str) -> str:
        p = self._personality
        return (
            f"{world_rules}\n\n"
            f"You are {p.name}, a {p.archetype}.\n"
            f"Traits: {', '.join(p.traits)}.\n"
            f"Backstory: {p.backstory}\n"
            f"Speech style: {p.speech_style}\n\n"
            "Issue actions as short imperative sentences. "
            "Be curious and exploratory. Do not break character."
        )

    def run_turn(self) -> str:
        context = self._memory.get_context(self._session_id, window=10)
        messages = _build_messages(context)
        response = self._client.messages.create(
            model=self._model,
            system=self._system_prompt,
            messages=messages,
            max_tokens=256,
        )
        return response.content[0].text.strip()
```

### AgentMemory schema and key query

```python
# [VERIFIED: 06-CONTEXT.md D-05, D-06, D-07 — raw sqlite3 pattern]
# Source: existing graph/persistence.py context manager pattern

def get_context(
    self, session_id: str, window: int = 10
) -> tuple[list[tuple[str, str]], str]:
    """Returns (turns_list, memory_summary).
    turns_list: [(action_text, observation_text), ...] last `window` turns.
    """
    with sqlite3.connect(str(self._db_path)) as conn:
        rows = conn.execute(
            """
            SELECT action_text, observation_text
            FROM agent_memory
            WHERE session_id = ?
            ORDER BY turn_number DESC
            LIMIT ?
            """,
            (session_id, window),
        ).fetchall()
        summary_row = conn.execute(
            "SELECT memory_summary FROM agent_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    turns = list(reversed(rows))  # chronological order
    summary = (summary_row[0] or "") if summary_row else ""
    return turns, summary
```

### TickCompressor.maybe_compress() structure

```python
# [VERIFIED: 06-CONTEXT.md D-17, D-18, D-19]
def maybe_compress(self, universe_dir: Path, client: Any) -> None:
    tick_dir = universe_dir / "tick_summaries" / "ticks"
    if not tick_dir.exists():
        return
    tick_files = sorted(tick_dir.glob("tick_*.json"))
    if len(tick_files) < self._batch_size:
        return
    # Take oldest batch_size files
    to_compress = tick_files[:self._batch_size]
    batch_id = self._next_batch_id(universe_dir)
    # Call Haiku; write batch file atomically FIRST
    batch = self._synthesize_batch(to_compress, batch_id, client)
    out_path = universe_dir / "tick_summaries" / f"batch_{batch_id}.json"
    _atomic_write_json(out_path, json.loads(batch.model_dump_json()))
    # Only delete after successful write
    for f in to_compress:
        f.unlink()
    # Check for epoch compression
    batch_files = sorted((universe_dir / "tick_summaries").glob("batch_*.json"))
    if len(batch_files) >= self._epoch_size:
        self._compress_epoch(batch_files[:self._epoch_size], universe_dir, client)
```

---

## State of the Art

| Old Pattern | Current Pattern | When Changed | Impact |
|-------------|----------------|--------------|--------|
| Full session history in context | Rolling window + compressed summary (D-07) | Phase 6 decision | Bounded context cost |
| All tick files forever | Hierarchical compression (D-17) | Phase 6 decision | Bounded disk use; agent catch-up enabled |
| Pure agent-authored scenarios | YAML declarative scenarios + injection | Phase 6 decision | Reproducible, seeded adversarial testing |
| Session fork = copy DB file | Snapshot + session row (D-08) | Phase 6 decision | Uses existing Phase-1 infrastructure |

---

## Open Questions

1. **`observation_groundedness` implementation detail**
   - What we know: Phase 5 `VisibilityProjector` returns a projected state dict. We need to check if observation text references projected entities.
   - What's unclear: Should the scorer call `engine._projector.project_for(actor)` directly (private attribute access), or should `TickResult` be extended with a `projected_state` field?
   - Recommendation: Add `projected_state: dict | None` to `TickResult` (set on the `ok` path only). This is a small, clean API change that avoids private attribute access. The planner can make this a Wave-0 task that modifies `engine.py` and `models.py` minimally.

2. **Regression suite: mock vs real LLM**
   - What we know: 35 UCs × Haiku + Sonnet = costly if real. But fake clients don't test prompt change detection.
   - What's unclear: Can the regression suite use real Haiku only (no Sonnet), by mock-returning a fixed observation string from Observer, to test mechanic matching without observation cost?
   - Recommendation: Use `FakeObserver` (returns a fixed string like "The action succeeded.") but real `Classifier` (Haiku is cheap). This tests mechanic matching and graph assertions without Sonnet cost.

3. **`agent_sessions.agent_personality` column type**
   - What we know: `PersonalityBundle` is a Pydantic model serializable to JSON string.
   - What's unclear: Should it be TEXT (JSON string) or stored as separate columns?
   - Recommendation: TEXT column containing `personality_bundle.model_dump_json()`. Consistent with the existing `graph_state` pattern of storing JSON blobs in TEXT columns.

---

## Environment Availability

Step 2.6: SKIPPED for external dependencies beyond Python. All required libraries (anthropic 0.94.0, sqlite3, click, pyyaml, pytest) are verified present in the existing project environment. No new dependencies required.

---

## Security Domain

The `workflow.nyquist_validation` key is `true` in `.planning/config.json`, so security is considered. However, this phase adds no authentication surfaces, no network endpoints, and no user input beyond the existing CLI. Relevant security considerations:

- `exec()` in regression tests runs manifest `graph_builder` code from git-committed files (trusted source). Namespace scoped to `{"kg": kg}` — no builtins pollution.
- Playtest YAML scenarios: no `exec()` — only YAML deserialization. PyYAML `safe_load` prevents arbitrary object construction.
- `agent_sessions` and `agent_memory` tables contain no secrets — only simulation text.
- Operator harness `asyncio.run()` wrapping: single-process, no concurrent session risk in v1.

---

## Sources

### Primary (HIGH confidence)

- `06-CONTEXT.md` — 30 locked decisions for this phase [VERIFIED: read in full]
- `src/token_world/engine/engine.py` — `SimulationEngine.run_tick()` API, `TickResult` shape [VERIFIED: read]
- `src/token_world/engine/summary_writer.py` — `TickSummaryWriter.write()` hook point [VERIFIED: read]
- `src/token_world/graph/knowledge_graph.py` — `snapshot(tick_id, summary) -> int`, `restore(snapshot_id)` [VERIFIED: read]
- `src/token_world/operator/harness.py` — `handle_yield` is `async def` [VERIFIED: line 194]
- `src/token_world/use_cases/loader.py` — `load_use_case()`, `REQUIRED_KEYS`, `expected_outcome` field [VERIFIED: read]
- `.planning/use-cases/spatial/UC-S01-movement-through-doorway.md` — manifest schema sample [VERIFIED: read]
- `src/token_world/engine/config.py` — `EngineConfig` dataclass, `universe.yaml` config key pattern [VERIFIED: read]
- `src/token_world/engine/models.py` — `TickSummary(schema_version: Literal[1] = 1)` [VERIFIED: read]
- `pyproject.toml [tool.pytest]` — markers, addopts, `@pytest.mark.integration` pattern [VERIFIED: read]
- `tests/test_graph/conftest.py` — `GraphBuilder`, `kg` fixture pattern [VERIFIED: read]

### Secondary (MEDIUM confidence)

- `src/token_world/operator/yield_signal.py` — `YieldSignal` shape for playtest runner integration [VERIFIED: read]
- `src/token_world/engine/__init__.py` — exported API surface [VERIFIED: read]
- `05-VERIFICATION.md` — Phase 5 delivered 7/7 success criteria; 1219 tests passing [VERIFIED: read]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `collections.Counter` cosine is sufficient for `action_novelty` without scipy | Architecture: Quality Scoring | Low — fallback is any string similarity; swap implementation in scorer.py |
| A2 | `asyncio.run()` wrapping `handle_yield` is safe in single-process synchronous loop | Pitfall 1 | Low — only fails if PlaytestRunner is called from async context (e.g., some test frameworks); mitigatable with run_in_executor |
| A3 | `VisibilityProjector` project_for(actor) dict keys are node IDs usable for groundedness substring check | Architecture: Quality Scoring | Low — if keys are something else, mutation target IDs are the fallback |

**If this table is empty in production:** All claims were verified against the codebase. The three ASSUMED items above are discretion-area implementation choices, not architectural risks.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified all existing code, no new deps
- Architecture: HIGH — all patterns established by prior phases, decisions locked
- Pitfalls: HIGH — verified from codebase inspection (async handle_yield, exec pattern, file ordering)

**Research date:** 2026-04-13
**Valid until:** Stable — 06-CONTEXT.md decisions are locked; only implementation details may change
