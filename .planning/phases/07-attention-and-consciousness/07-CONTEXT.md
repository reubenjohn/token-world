# Phase 7: Attention & Consciousness - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning
**Mode:** `--auto` (autonomous pick of recommended options, no human in the loop)

> **Auto-mode note:** This CONTEXT was produced by `/gsd-discuss-phase 7 --auto`. Every decision below picks the recommended/pragmatic option consistent with PROJECT.md principles (especially Principle 8: composition over specialization) and prior-phase patterns. All 11 gray areas are locked. No human has reviewed the selections; research and planning will run against these directly.

<domain>
## Phase Boundary

Phase 7 delivers the **composable interruption threshold pattern** — one generic mechanism that makes the simulation feel temporally alive by handling multi-tick, interruptible actions across all consciousness states.

**What this phase delivers:**

1. **Long-running action infrastructure** (SIM-09) — actions that span N ticks, during which the engine projects observations and evaluates interruption thresholds each tick instead of requiring an explicit agent action.
2. **Unified interruption threshold pattern** (SIM-10) — a single declarative mechanism that covers sleep, autopilot travel, drunkenness, and daydreaming. One pattern for all interruptible states; no special-case handling per state.
3. **Attention-modulated projection** — `VisibilityProjector` extended to accept an `attention_state` that boosts or suppresses certain properties at projection time, making perception attenuated during drunk/daydream states.

**The three ROADMAP Phase 7 success criteria:**
1. Long-running actions skip boring intermediate turns and only interrupt the agent when significance exceeds the current attention threshold.
2. Sleep, daydreaming, and autopilot travel all use the same interruption threshold infrastructure, demonstrating composability.
3. An agent traveling a long distance experiences compressed time with interruptions only for significant events (demonstrating SIM-09 and SIM-10 together).

**Explicitly OUT of scope for Phase 7:**
- Multi-agent concurrent long-running action conflicts (MULTI-01..03 — v2).
- Sandboxing (HARD-01 — v2).
- LLM-generated adversarial scenarios (Phase 6 YAML-only deferred from Phase 6).
- Calendar/season derivation (GAP-ENG10 — v2).
- Personality evolution over time (v2).
- Per-N-tick threshold evaluation (performance optimization — deferred; every-tick is the v1 default).

</domain>

<decisions>
## Implementation Decisions

> **Decision log convention:** Each decision has a D-NN id, cites the source (requirement, gray area number, or prior-phase decision), states the choice, and notes the alternative(s) that were considered but not chosen. All gray areas from auto_mode_guidance are resolved here.

### Core Concept — One Composable Pattern for All States

- **D-01** — *Source: SIM-10; CLAUDE.md Principle 8 ("Composition over specialization"); ROADMAP.md Phase 7 goal.* "Asleep", "drunk", "daydreaming", and "autopilot traveling" are NOT separate code paths. They are all **long-running actions with interruption thresholds**. "Conscious and idle" is the absence of a long-running action. One `LongRunningAction` dataclass, one threshold evaluator, one engine hook. Rejected: separate `SleepState`, `DrunkState` classes. Rationale: CLAUDE.md Principle 8 explicitly names this pattern as the "core philosophy"; building per-state code would be a direct violation.
  - *Satisfies: SIM-09, SIM-10*

### Long-Running Action State — Graph Property on Actor Node

- **D-02** — *Source: Gray area #2; CLAUDE.md "Graph is ground truth" (Principle 9); SIM-09.* The long-running action state lives as a **graph property `current_long_action`** (a JSON dict) on the actor node. When no long-running action is active, the property is absent or `null`. Schema: `{"action_text": str, "turns_total": int, "turns_elapsed": int, "thresholds": list[ThresholdSpec], "payload": dict}`. Stored via `kg.set(actor_id, "current_long_action", {...})`. Rejected: separate SQLite table. Rationale: "If it's not in the graph, it doesn't exist" (CLAUDE.md Principle 9). Graph storage is automatically snapshotted, rollback-safe, and queryable via existing KnowledgeGraph API.
  - *Satisfies: SIM-09*

### Threshold Expression Language — Declarative Dict with Comparison Operators

- **D-03** — *Source: Gray area #1; SIM-09, SIM-10.* Interruption thresholds are **declarative dicts** with three keys: `{"property": "<node_id>.<prop_name>", "op": "<operator>", "value": <threshold_value>}`. Operators: `">"`, `">="`, `"<"`, `"<="`, `"=="`, `"!="`. Evaluated against the `VisibilityProjector.project_for(actor)` output each tick. Example: `{"property": "room.noise_level", "op": ">", "value": 0.7}`. Rejected: Python lambda (eval() security risk, not serializable to graph). Rejected: domain-specific rules DSL (over-engineered). Rationale: declarative dicts are JSON-serializable (required for graph property storage per D-02), safe, and readable. Mechanic authors write thresholds as plain Python dicts — no new syntax to learn.
  - *Satisfies: SIM-09, SIM-10*

### Multiple Concurrent Long-Running Actions — Single Active Action Per Agent (v1)

- **D-04** — *Source: Gray area #4; PROJECT.md "Single agent + engine for v1".* Each agent may have **at most one active long-running action** at a time (v1). Concurrent long-running actions (e.g., "simultaneously sleeping and drunk") are deferred to v2. Composability in v1 is achieved via interruption chains: action A fires a threshold → engine ends A → agent (or a mechanic) may immediately start action B in the next tick. The `current_long_action` graph property is singular (not a list). Rejected: list of concurrent long-running actions. Rationale: keeping v1 single-action prevents turn-ordering conflicts while still demonstrating the pattern's composability via interruption chaining.
  - *Satisfies: SIM-09*

### New Mechanic Primitive — LongRunningAction Return Value, No New Mechanic Type

- **D-05** — *Source: Gray area #7; CLAUDE.md Principle 8 ("Composition over specialization"); SIM-09.* Long-running actions are NOT a new mechanic type. Instead, a mechanic's `apply()` method may return (or include) a **`LongRunningAction` dataclass** in its result alongside normal `Mutation` objects. The engine inspects the apply() result; if a `LongRunningAction` is present, it writes `current_long_action` to the actor's graph node (D-02). The `LongRunningAction` dataclass lives in `src/token_world/engine/long_running.py` alongside the `ThresholdSpec` dataclass. Rejected: new `Mechanic` subclass type (adds type proliferation; breaks existing registry). Rejected: new `apply()` protocol (breaks all existing mechanics). Rationale: existing `check()/apply()` contract is preserved — mechanics that don't want long-running behaviour are untouched. One new return value type enables the pattern without protocol churn.
  - *Satisfies: SIM-09, SIM-10*

### Tick Hook — Post-Execute, Pre-Passive-Sweep

- **D-06** — *Source: Gray area #3; SIM-09; Phase 5 engine architecture (D-17).* Each tick, the engine checks the actor's `current_long_action` graph property **after** primary mechanic execution and **before** the passive sweep. Hook position:
  1. Primary action classified → matched → executed (existing pipeline).
  2. **Long-running action check**: if `current_long_action` is set, evaluate thresholds against the new projected state (D-09). If a threshold fires, transition to interrupted state and generate interruption observation (D-10). If no threshold fires, advance `turns_elapsed`, suppress normal agent observation (return a compressed "time passes" observation instead), skip the passive sweep tick contribution.
  3. Passive sweep runs.
  Rejected: pre-execute hook (action's own effect, e.g., sleep regenerating energy, must apply first). Rationale: "action first, world reacts after" matches Phase 5 D-17 reasoning.
  - *Satisfies: SIM-09*

### Agent Long-Running Turn — Implicit Action, No New Agent Call

- **D-07** — *Source: Gray area #1 (related); SIM-09; Phase 6 ResidentAgent (06-CONTEXT.md D-01).* When a long-running action is active, the engine **does not call the resident agent** for that tick's action text. Instead, `SimulationEngine.run_tick` internally generates a synthetic action (e.g., `"continue_long_action"`) that the engine resolves to a built-in `LongRunningTickMechanic`. This mechanic advances `turns_elapsed`, fires threshold evaluation, and either: (a) returns a compressed "time passes" observation, or (b) interrupts. The `PlaytestRunner` passes this synthetic action transparently — no change to the runner loop. Rejected: requiring the playtest runner to have special knowledge of long-running turns. Rationale: keeping the "caller passes action text" contract intact keeps Phase 6 components unchanged.
  - *Satisfies: SIM-09*

### Threshold Evaluation Granularity — Every Tick

- **D-08** — *Source: Gray area #5; SIM-09.* Thresholds are evaluated **every tick** during a long-running action. No N-tick batching in v1. Simple, predictable, debuggable. Performance optimization (evaluate every N ticks) deferred to v2. Rationale: at hobby project scale (single agent, slow LLM calls dominate wall time), per-tick evaluation has negligible overhead.
  - *Satisfies: SIM-09*

### Threshold Evaluation Input — VisibilityProjector Output

- **D-09** — *Source: Gray area #3; SIM-09; Phase 5 D-14 (VisibilityProjector).* Thresholds are evaluated against the **`VisibilityProjector.project_for(actor)` output** for the current tick. Property references in threshold specs use dot notation: `"<node_id>.<property_name>"` (e.g., `"bedroom.noise_level"`, `"alice.energy"`). The evaluator resolves `node_id` against projection keys and `property_name` against the `properties` subdict. Missing nodes or properties evaluate as `None`; comparisons against `None` return False (safe default — threshold does not fire on missing data). This reuses the already-computed projection from the existing pipeline without an extra projector call.
  - *Satisfies: SIM-09*

### Interruption Observation — Structured Sonnet Synthesis Reusing Observer

- **D-10** — *Source: Gray area #6; SIM-09, SIM-10; Phase 5 D-15 (Observer/grounding constraint).* When a threshold fires and interrupts a long-running action, the engine synthesises an **interruption observation** using the existing `Observer.synthesize()` call with: (1) the current projected state, (2) an interruption context dict `{"interrupted_by": ThresholdSpec, "trigger_value": observed_value, "long_action": action_text}` passed as part of the trace, (3) a modified observer prompt that outputs a "you were interrupted because..." narrative. The interruption narrative is grounded in graph state (inheriting Phase 5's hard grounding constraint). Rejected: free-form LLM generation of interruption. Rejected: hardcoded narrative template (too rigid for diverse interruption contexts). Rationale: reusing Observer keeps grounding guarantees; the interruption context dict provides the "why" without hallucination.
  - *Satisfies: SIM-09, SIM-10*

### Action Cancellation By Agent — New Action Implicitly Cancels

- **D-11** — *Source: Gray area #8; SIM-09; Phase 6 ResidentAgent.* If the resident agent emits a new text action while a long-running action is active (only possible if the agent is externally controlled or the runner passes a non-synthetic action), the engine **clears `current_long_action`** and processes the new action normally. This is an implicit cancellation — no explicit "cancel sleep" verb needed. Documented coherence cost: "agent woke up and acted in the same tick" — acceptable for hobby v1. Rejected: requiring an explicit "cancel" verb. Rationale: simplicity; the cost is a minor simulation fidelity issue that does not affect grounding guarantees.
  - *Satisfies: SIM-09*

### Attention (Selective Observation) — Filter at Projection Time

- **D-12** — *Source: Gray area #10; SIM-10; Phase 5 D-14 (VisibilityProjector).* Attention state modulates the `VisibilityProjector.project_for(actor)` call by accepting an optional **`attention_state: dict | None`** parameter. `attention_state` maps property names to boost/suppress factors: `{"suppress": ["visual_detail"], "boost": ["noise_level"]}`. The projector applies suppression (removes or zeroes the property from the projection) and boost (copies property to the top-level of projected entry for prominence). The actor's `current_long_action.payload` may include an `attention_state` dict; the engine reads it and passes it to the projector. Rejected: synthesis-time filtering (harder to audit; breaks grounding constraint which is enforced at projection not synthesis). Rationale: projection is the existing grounding boundary (Phase 5 D-14); extending it is the correct hook, not adding a second filtering layer.
  - *Satisfies: SIM-10*

### Consciousness States — Unified as Long-Running Actions

- **D-13** — *Source: Gray area #9; SIM-10; CLAUDE.md Principle 8.* There is NO separate consciousness state mechanism. "Drunk" = a long-running action with `turns_total: None` (indefinite until sobering threshold fires) and `payload: {"attention_state": {"suppress": ["fine_detail"], "boost": ["aggression_level"]}}`. "Asleep" = a long-running action with `turns_total: 8` (8-tick sleep cycle, e.g.) and thresholds like `{"property": "room.noise_level", "op": ">", "value": 0.7}`. "Daydreaming" = a long-running action with `turns_total: 3` and a different threshold. "Autopilot travel" = a long-running action with `turns_total: travel_distance` and terrain hazard thresholds. One `LongRunningAction` dataclass covers all. `turns_total: None` means "indefinite" — only interruption or explicit cancellation ends it.
  - *Satisfies: SIM-10*

### Testing Strategy — Deterministic Mocks for Mechanism, Live LLM Gated

- **D-14** — *Source: Gray area #11; CLAUDE.md "Quick test: uv run pytest tests/ -x -q".* Testing is layered:
  1. **Unit tests** for `LongRunningAction` dataclass, `ThresholdSpec` evaluation, threshold evaluator logic — fully deterministic, no LLM.
  2. **Integration tests** for the engine hook (D-06) using `FakeClassifier` + `FakeObserver` patterns from Phase 6 (06-CONTEXT.md D-25): fabricate a long-running action, advance ticks, assert threshold fires at the correct tick and produces an interruption observation.
  3. **Demonstration tests** (`@pytest.mark.integration`) that run the full sleep/travel/drunk scenarios end-to-end with real LLM calls — gated by opt-in marker; not run in CI by default.
  Rejected: live LLM for all threshold tests (too slow, too expensive for rapid iteration). Rationale: the mechanism is deterministic; only the narrative synthesis benefits from live LLM testing, and that's already covered by Phase 6's regression suite.
  - *Satisfies: SIM-09, SIM-10*

### New Module Layout

- **D-15** — *Source: CLAUDE.md "Imports: use public __init__.py APIs"; SIM-09, SIM-10.* New code lives in:
  - `src/token_world/engine/long_running.py` — `LongRunningAction` dataclass, `ThresholdSpec` dataclass, `ThresholdEvaluator` class (pure function evaluator against projection dict).
  - `src/token_world/engine/long_running_hook.py` — `LongRunningHook` class: reads `current_long_action` from graph, evaluates thresholds, advances `turns_elapsed`, clears state on completion/interruption. Called by `SimulationEngine._handle_execute()` post-execution.
  - `src/token_world/engine/visibility.py` — extended: `VisibilityProjector.project_for(actor_id, attention_state=None)` (backward-compatible signature extension; D-12).
  - `src/token_world/engine/engine.py` — extended: `SimulationEngine._handle_execute()` gains a `LongRunningHook` call after primary chain + conservation, before passive sweep (D-06). Long-running state cleared when new agent action detected (D-11).
  - `tests/test_engine/test_long_running.py` — unit + integration tests (D-14).
  Rejected: putting all new code in `engine.py` (monolithic; hard to test in isolation).
  - *Satisfies: SIM-09, SIM-10*

### `turns_total: None` Semantics — Indefinite Duration

- **D-16** — *Source: D-13; SIM-10.* `turns_total: None` in `LongRunningAction` means indefinite duration — the action continues until a threshold fires or the agent explicitly cancels via a new action (D-11). The engine never auto-expires an indefinite action. Mechanics authors use `turns_total: None` for consciousness states like drunkenness that persist until a sobering event. Mechanics authors use `turns_total: int` for bounded sleeps and timed travel. The `turns_elapsed` counter still advances each tick for diagnostics regardless of `turns_total` value.
  - *Satisfies: SIM-10*

### Tick Summary Schema Extension — Long-Running Action Fields

- **D-17** — *Source: Phase 5 D-20 (tick summary schema); Phase 6 D-18 (batch summary schema_version: 2); SIM-09.* Per-tick summary JSON is extended with an optional `long_running_action` object: `{"active": bool, "turns_elapsed": int, "turns_total": int | null, "threshold_fired": ThresholdSpec | null, "interrupted": bool}`. This is backward-compatible (optional field; consumers that don't know about long-running actions ignore it). The `schema_version` field in tick summaries remains `1` (field is additive; no break). Batch/epoch schema_version: 2 (Phase 6 D-18) is unchanged. `agent_id` stub in BatchSummary ("unknown" per Phase 6 notes) is NOT resolved in Phase 7 — deferred.
  - *Satisfies: SIM-09*

### Seed Mechanics for Long-Running Pattern — Three Demonstrators

- **D-18** — *Source: ROADMAP.md Phase 7 success criteria #2 and #3; SIM-10.* Phase 7 authors exactly **three seed long-running mechanics** to demonstrate the composable pattern:
  1. **`sleep` mechanic** — agent initiates sleep; `turns_total: 8`; thresholds: `noise_level > 0.7` (light sleeper) and `health < 0.2` (distress wake). `attention_state: {"suppress": ["visual_detail", "smell"], "boost": ["noise_level"]}`.
  2. **`autopilot_travel` mechanic** — agent sets travel destination; `turns_total` = path length; thresholds: `hazard_level > 0.5` on current room OR `curiosity_trigger` property on any contained entity. `attention_state: {"suppress": ["fine_detail"], "boost": ["hazard_level"]}`.
  3. **`drunk` mechanic** — agent consumes alcohol; `turns_total: None` (indefinite); thresholds: `sobriety_level > 0.8` (sobered up). `attention_state: {"suppress": ["fine_detail", "social_nuance"], "boost": ["aggression_level"]}`.
  These three demonstrate: bounded/indefinite, physical/cognitive/movement, different threshold types.
  - *Satisfies: SIM-10 (composability)*

### Claude's Discretion (planner + researcher have flexibility here)

- **D-19** — Exact `ThresholdSpec` dataclass field names (property, op, value are fixed per D-03; internal implementation details like field aliases are flexible).
- **D-20** — Whether `LongRunningHook` is a standalone class or a set of module-level functions. Either is fine as long as it's in the separate `long_running_hook.py` module (D-15).
- **D-21** — Exact wording of the interruption observer prompt extension (D-10). The structured context dict shape is locked; the prompt phrasing is tunable.
- **D-22** — Whether the "time passes" observation during non-interrupted long-running ticks is generated by Haiku (cheap) or is a static template string. Recommended: static template for hobby budget; planner picks.
- **D-23** — Whether `LongRunningAction` and `ThresholdSpec` are frozen dataclasses or Pydantic models. Recommended: frozen dataclasses (consistent with `YieldSignal`, `Mutation`; Pydantic reserved for LLM-output parsing).

</decisions>

<specifics>
## Specific Ideas

- The "one composable pattern" is the central design statement of Phase 7. Every implementation decision must preserve this — no special-casing sleep vs. drunk vs. travel at the engine level.
- Thresholds reference projected state via dot notation (`room.noise_level`) to stay grounded — no threshold can fire on hallucinated state that isn't in the graph.
- The `turns_total: None` (indefinite) case is critical for modeling drunkenness and other lingering states. Sleep is finite; drunkenness is not (until the sobering mechanic fires).
- The autopilot travel demonstrator (D-18 #2) is the most compelling v1 showcase: an agent crosses a dangerous dungeon corridor, "waking up" only when a hazard appears. This directly shows SIM-09 and SIM-10 together.
- The attention_state suppression/boost mechanism (D-12) is purposefully minimal. It does not model full perceptual psychology — it modulates the projection dict, which is what the Observer sees. "Drunk agent doesn't notice fine_detail" = `fine_detail` property absent from projection. Simple and grounded.
- Phase 6 note: `agent_id` stubbed to `'unknown'` in BatchSummary — this is a known limitation, NOT resolved in Phase 7. Documented here so the planner does not inadvertently scope it in.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Vision & Decisions
- `.planning/PROJECT.md` §Key Decisions — Composition over specialization (the founding principle of Phase 7's design); graph is ground truth; single agent v1
- `.planning/PROJECT.md` §Constraints — JSON-serializable properties (critical: `current_long_action` dict must survive json roundtrip; list/dict/str/int/float/bool/None only)
- `CLAUDE.md` — Principle 8 (composition over specialization), Principle 9 (graph is ground truth), two-node-types, mutation-mediated access

### Requirements (owned by this phase)
- `.planning/REQUIREMENTS.md` §Simulation Engine — SIM-09 (action duration + attention threshold), SIM-10 (reusable mechanic pattern for consciousness states)

### Phase 5 Outputs — Primary Engine Integration Points
- `.planning/phases/05-simulation-engine/05-CONTEXT.md` — D-01 (staged pipeline — hook insertion point), D-14 (VisibilityProjector — attention extension point), D-15 (grounding constraint — interruption observation must satisfy same constraint), D-17 (passive sweep — Phase 7 hook runs before sweep), D-19 (seeded RNG pattern on MechanicContext — Phase 7 mechanics use same pattern)
- `src/token_world/engine/engine.py` — `SimulationEngine._handle_execute()` — Phase 7 inserts `LongRunningHook.process()` call here
- `src/token_world/engine/visibility.py` — `VisibilityProjector.project_for()` — Phase 7 extends signature with `attention_state=None` (D-12)
- `src/token_world/engine/models.py` — `TickResult`, `ExecutionTrace` — Phase 7 reads `TickResult.projected_state` for threshold evaluation

### Phase 6 Outputs — Testing Patterns
- `.planning/phases/06-resident-agent-end-to-end-loop/06-CONTEXT.md` — D-25 (FakeClassifier + FakeObserver pattern for deterministic integration tests — Phase 7 tests reuse this), D-01 (ResidentAgent issues action text — Phase 7 must not break this contract)
- `src/token_world/resident/agent.py` — `ResidentAgent.run_turn()` — must remain unchanged by Phase 7 (D-07 ensures no interface change)
- `tests/test_engine/` — existing engine test patterns; Phase 7 adds `test_long_running.py` here

### Mechanic Framework — apply() Contract Extension
- `src/token_world/mechanic/engine.py` — `ChainExecutionEngine.execute()` — Phase 7 returns mutations + optionally `LongRunningAction`; engine.py must handle the new return type
- `src/token_world/mechanic/context.py` — `MechanicContext` — mechanic authors need to know how to return a `LongRunningAction` from `apply()`; Phase 7 adds a helper `ctx.begin_long_action(...)` convenience method
- `src/token_world/graph/models.py` — `ALLOWED_PROPERTY_TYPES` — `current_long_action` stored as dict; must be confirmed JSON-serializable

### Stack & Architecture
- `.planning/research/STACK.md` — model routing (Haiku for cheap synthesis of "time passes" observations; Sonnet for interruption narrative synthesis)

### New Code (this phase creates)
- `src/token_world/engine/long_running.py` — `LongRunningAction`, `ThresholdSpec`, `ThresholdEvaluator` (D-15)
- `src/token_world/engine/long_running_hook.py` — `LongRunningHook` (D-15)
- `src/token_world/engine/visibility.py` — extended with `attention_state` param (D-12, D-15)
- `src/token_world/engine/engine.py` — extended `_handle_execute()` with long-running hook call (D-06, D-07, D-11, D-15)
- Three seed mechanics demonstrating the pattern (D-18): `sleep`, `autopilot_travel`, `drunk`
- `tests/test_engine/test_long_running.py` — unit + integration tests (D-14)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`VisibilityProjector.project_for(actor_id)`** (`src/token_world/engine/visibility.py`) — Phase 7 extends this method's signature with `attention_state=None` (backward-compatible). The projector already applies 4 stages (containment → illumination → hidden_properties → belief overlay); attention modulation is stage 5.
- **`SimulationEngine._handle_execute()`** (`src/token_world/engine/engine.py`) — Phase 7 inserts a `LongRunningHook.process()` call between conservation check and passive sweep (line ~450-487 in current codebase). The engine already pre-computes `projection = self._projector.project_for(actor)` for the Observer; the hook reuses this same projection for threshold evaluation (no extra projector call).
- **`KnowledgeGraph.set(node_id, prop, value)`** — `current_long_action` dict stored via this existing API. All mutations are logged as events (audit trail). Snapshot/restore (Phase 1) automatically includes `current_long_action` state.
- **`FakeClassifier` / `FakeObserver`** (Phase 6 test infrastructure) — reused for Phase 7 deterministic integration tests (D-14).
- **`YieldSignal` dataclass** (`src/token_world/operator/yield_signal.py`) — frozen dataclass pattern; `LongRunningAction` and `ThresholdSpec` follow the same pattern (D-23).
- **`MechanicContext.rng`** (Phase 5 D-19) — Phase 7 stochastic thresholds (e.g., probabilistic wake) can use `ctx.rng` to stay deterministic. No new RNG surface needed.
- **Phase 6 `@pytest.mark.integration` marker** — Phase 7 live-LLM tests use the same marker; no new marker registration needed.

### Established Patterns
- **Frozen dataclass for engine contracts** — `YieldSignal`, `Mutation`, `SnapshotInfo` are all frozen dataclasses. `LongRunningAction` and `ThresholdSpec` follow suit (D-23).
- **Raw `anthropic` SDK in engine** — Classifier and Observer use `client.messages.create(...)`. Any Haiku call for "time passes" synthesis follows the same pattern.
- **Universe-config keys** (`src/token_world/engine/config.py`) — `engine.max_chain_depth`, `engine.classifier_min_confidence` follow this pattern. Phase 7 may add `engine.default_sleep_turns` if needed.
- **`@pytest.mark.integration`** — real-LLM tests; excluded from `uv run pytest -x -q` by default.
- **Phase 4 `DiagnosticsSink` wiring** — interruption observations and long-running-action state transitions written to diagnostics substrate consistently with existing LLM call patterns.

### Integration Points
- `SimulationEngine._handle_execute()` → after conservation check, before passive sweep: call `LongRunningHook.process(actor, projection, graph)` → returns `HookResult(interrupted: bool, observation: str | None, cleared: bool)`.
- `VisibilityProjector.project_for(actor)` → called with `attention_state` from `current_long_action.payload` if present.
- `MechanicContext` → `ctx.begin_long_action(action_text, turns_total, thresholds, attention_state)` helper writes `current_long_action` to the actor graph node (convenience wrapper over `ctx.graph.set()`).
- `apply()` result inspection: `ChainExecutionEngine` or `SimulationEngine` inspects return value of `mech.apply(ctx)` — if it contains a `LongRunningAction`, the engine sets `current_long_action` on the actor node.

</code_context>

<deferred>
## Deferred Ideas

- **Per-N-tick threshold evaluation** — performance optimization; v1 evaluates every tick (D-08). Defer until scale demands it.
- **Concurrent long-running actions per agent** — v2 multi-agent architecture (D-04). v1 is single-action-per-agent.
- **LLM-generated adversarial scenarios for long-running actions** — Phase 6 deferred this; still deferred. YAML scenarios sufficient.
- **Calendar/season derivation (GAP-ENG10)** — v2; would interact with `autopilot_travel` travel duration, but that's acceptable.
- **Multi-agent long-running action conflicts** (MULTI-01..03) — v2. Single-agent invariant holds.
- **Graph-based agent memory (HARD-04)** — v2; `current_long_action` in graph IS a graph-based state, but full graph memory is larger scope.
- **`agent_id` field in BatchSummary** — stubbed to `'unknown'` in Phase 6. NOT resolved here; deferred until a clear use case emerges.
- **Personality evolution during long-running states** — interesting idea (sleep changes personality subtly over time); v2.
- **Stochastic threshold evaluation** — `ctx.rng` supports it, but no v1 seed mechanic uses it. Design supports it; authoring deferred.
- **`turns_elapsed` visibility in agent observation** — agent currently does not perceive "I have been asleep for 4 hours". Could be interesting but adds complexity; deferred to v2.
- **Restoring long-running action state across process restarts** — `current_long_action` IS in the graph and therefore IS persisted. This works already by design (D-02); no additional work needed, but worth verifying in integration tests.

</deferred>

---

*Phase: 07-attention-and-consciousness*
*Context gathered: 2026-04-13*
