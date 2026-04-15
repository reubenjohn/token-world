# Phase 5: Simulation Engine - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning
**Mode:** `--auto` (autonomous pick of recommended options, no human in the loop)

> **Auto-mode note:** This CONTEXT was produced by `/gsd-discuss-phase 5 --auto`. Every decision below picks the recommended/first option for its gray area. Each decision is traceable to the source gap ID(s) in GAP-HANDOFF.md or a prior-phase decision. No human has reviewed the selections; research and planning will run against these directly.

<domain>
## Phase Boundary

Phase 5 delivers the simulation engine — the in-tool layer that consumes a resident-agent text action and drives it end-to-end:

1. **Classify** text → structured action (Haiku, raw Anthropic SDK per STACK.md)
2. **Match** structured action → existing mechanic (deterministic first-pass, LLM fallback for ties)
3. **Decide** execute / yield / refuse-with-narrative based on match outcome
4. **Execute** matched mechanic via the Phase 2 `ChainExecutionEngine`
5. **Project observations** — filter graph state through a visibility layer before synthesis (SIM-07, GAP-CROSS01)
6. **Synthesise** observation text (Sonnet, raw Anthropic SDK) with hard grounding constraints
7. **Enforce conservation** — block mutations that create matter/energy from nothing (SIM-08, GAP-ENG06)
8. **Sweep passive mechanics** at tick-end (GAP-ENG07 — decay, weather, fire spread, contagion)
9. **Emit a structured `YieldSignal`** (Phase 4.1 contract) when no mechanic matches a well-formed classified action
10. **Write a per-tick summary JSON** (SIM-11) and wire every LLM call into Phase 4's diagnostics substrate (AUTO-02)

Under the inversion-of-control model locked in Phase 4: **the engine never generates code.** When no mechanic matches, it halts and yields to the operator (handled by the Phase 4.1 harness); when the classifier decides the input is nonsense, it returns `no_viable_action` and the engine refuses without yielding.

Explicitly OUT of scope for Phase 5:
- **Resident agent / personality / memory** (Phase 6 — AGENT-01..04, TEST-04/05/07, AUTO-05/06/07, DVAL-03).
- **N-turn playtest runner, quality scoring, adversarial injection** (Phase 6).
- **Hierarchical tick summary compression** (SIM-12 — batch→epoch compression is Phase 6, DVAL-03 use-case regression is Phase 6).
- **Attention / consciousness / action duration / interruption thresholds** (SIM-09, SIM-10 — Phase 7).
- **Multi-agent turn ordering / conflict resolution (GAP-ENG13, GAP-ENG14)** — the engine sees one resident agent per tick in v1 (PROJECT.md "Single agent + engine for v1"); turn-ordering invariant is a single-liner policy decision, but the actual concurrent-actors conflict detector is deferred. **See D-17 below for the Phase-5 policy.**
- **Calendar / `day_of_year → season` derivation (GAP-ENG10)** — v2 scope. Phase 5 ships the `WorldPropertyMatcher` (GAP-ENG09) so a later phase can write calendar mechanics without engine changes.
- **Runtime sandboxing (RestrictedPython)** — v2.

</domain>

<decisions>
## Implementation Decisions

> **Decision log convention:** Each decision has a D-NN id, cites the source (requirement, gap ID, or prior-phase decision), states the choice, and notes the alternative that was considered but not chosen. Rationale matches CLAUDE.md Operating Principle 6 ("ground truth obsession") — no vague handwaves.

### Pipeline Architecture — Explicit Staged Pipeline

- **D-01** — *Source: SIM-01..SIM-05.* The engine is a sequence of five explicit stages, each a separately-testable function/class: `classify(action_text) → ClassifiedAction`, `match(classified) → MatchResult`, `decide(match, classified) → Decision`, `execute(decision, ctx) → ExecutionTrace + Mutations`, `observe(trace, ctx) → ObservationText`. A thin `SimulationEngine.run_tick(action_text, actor)` orchestrator calls them in order. Rejected: monolithic `engine.step()` method. Rationale: per-stage unit-testability + diagnostics fan-out (Phase 4 D-21 already assumes per-stage folders `classification/`, `matching.json`, `execution/`, `observation/`).
- **D-02** — *Source: Phase 4.1 D-08.* The orchestrator is **idempotent w.r.t. registry state**: on every `run_tick` call it lets the registry auto-scan pick up new mechanics (Phase 4 D-15). This is what makes `resume_tick` work after the operator writes a missing mechanic. No additional plumbing needed; we rely on Phase 4's behaviour.
- **D-03** — *Source: GAP-ENG18.* `max_chain_depth` is loaded from a universe-config key (`engine.max_chain_depth`, default `10`) not hardcoded. This makes the rationale documentable and per-universe-overridable.

### Classifier — Haiku, Structured Output, Four Verdicts

- **D-04** — *Source: SIM-01 + STACK.md model-routing decision.* Classifier uses `claude-haiku-4-5-20251001` via the raw Anthropic SDK (`client.messages.create(...)`). Structured output (JSON mode) enforced via Pydantic model. No tool use, no streaming.
- **D-05** — *Source: GAP-ENG02.* The classified-action schema has four fields: `verb: str`, `actor: str` (node id), `target: str | None` (node id if applicable), `indirect_object: str | None` (node id, for ditransitive verbs), plus `params: dict[str, Any]` (verb-specific). `indirect_object` is new this phase — GAP-ENG02 closure; seed mechanics MECH08 `give` / MECH11 `teach` / MECH_R03 `gift_currency` already expect it in their pre-conditions.
- **D-06** — *Source: GAP-ENG15, GAP-ENG11, GAP-ENG16 (Phase-5 half per 04-CONTEXT D-34), GAP-CROSS02.* Classifier returns one of four discriminated verdicts (Pydantic tagged union):
  - `ok(classified)` — well-formed classified action.
  - `no_viable_action(reason)` — action text is nonsense, empty, pure gibberish, or the structured verb isn't recognisable. Engine refuses with a narrative; does **NOT** yield to operator. *Covers GAP-ENG15 + GAP-ENG16 Phase-5 half.*
  - `no_such_target(target_text)` — classifier extracted a target but graph lookup fails. Engine refuses with grounded narrative. *Covers GAP-ENG11.*
  - `low_confidence(reason, best_guess)` — classifier confidence below threshold; engine refuses with narrative that repeats what it thought the agent meant. *Covers GAP-ENG15 "confidence threshold" aspect.*
- **D-07** — *Source: D-04 + cost discipline (PROJECT.md "Budget: hobby project").* Confidence is self-reported by Haiku in a 0.0–1.0 field; threshold for `low_confidence` is `0.6` (universe-config key `engine.classifier_min_confidence`). Rejected: running a second adversarial classifier pass. Rationale: Haiku self-report is cheap and sufficient for hobby-scale; threshold is tunable without code changes.
- **D-08** — *Source: GAP-ENG01 (trade multi-turn).* Classifier DOES NOT implement multi-turn offer/accept protocol in Phase 5. `trade` remains a single-tick mechanic that short-circuits on inter-agent-consent via an `offering` property; MECH07 (Phase 4) already works this way. GAP-ENG01 is **deferred to v2 (multi-agent)** — a single-agent v1 has no agent to trade with. Deferring this unblocks Phase 5 from building a stateful classifier.

### Matcher — Deterministic First-Pass, No LLM Fallback in v1

- **D-09** — *Source: SIM-02, MECH-02 (matcher primitives from Phase 2).* Matching is **deterministic** in v1: iterate registered voluntary mechanics, call their declared matcher (`VerbMatcher`, `WorldPropertyMatcher`, `NullMatcher`, etc.), score based on literal verb match + target-type match + actor-type match. Highest-score mechanic executes; ties broken alphabetically by mechanic id. Rejected: LLM-based semantic fallback matcher. Rationale: adds a third LLM call per tick, creates a second "did we match" axis, and the classifier already does the natural-language → verb translation. If no mechanic scores above zero, we yield.
- **D-10** — *Source: Phase 2 matcher primitives + GAP-ENG09.* Phase 5 adds `WorldPropertyMatcher` to the matcher vocabulary so world-level property changes (season, weather, day/night) can dispatch mechanics without a verb (GAP-ENG09 closure). Lives in `token_world.mechanic.matchers` next to existing matchers; no engine changes beyond consuming it.
- **D-11** — *Source: SIM-02.* `MatchResult` is a discriminated union: `matched(mechanic, score, reasoning)` | `no_match(classified_action, candidates: list[str])` where `candidates` is the top-K mechanic ids that scored above zero but below threshold. `candidates` feeds `YieldSignal.candidate_mechanic_ids` (Phase 4.1 contract).

### Yield Decision — Match-First, Narrative-Second, Yield-Last

- **D-12** — *Source: SIM-03 + Phase 4 D-34 + GAP-CROSS02.* The `decide` stage has a fixed precedence ladder:
  1. If classifier returned `no_viable_action` / `no_such_target` / `low_confidence` → `Refuse(narrative)`. No execution, no yield.
  2. If matcher returned `matched` → `Execute(mechanic)`.
  3. If matcher returned `no_match` with a well-formed classified action → `Yield(YieldSignal)`. Engine halts; Phase 4.1 harness takes over.
- **D-13** — *Source: GAP-CROSS02.* Refusal narratives use a shared `RefusalTemplate` with three slots: what the actor tried, why it failed, what the actor now perceives (e.g., "You try to gragh the rock, but nothing about the rock suggests it can be graghed."). Sonnet-generated from a template prompt; not free-generation. Mechanics that themselves refuse (e.g., pickup at inventory cap per MECH16) use the **same** narrative template via a `ctx.refuse(reason_code, details)` helper added to `MechanicContext`. One refusal surface across classifier-refusal, match-refusal, and mechanic-refusal.

### Observation Projection — Visibility Layer Before Synthesis

- **D-14** — *Source: SIM-07 + GAP-CROSS01 ("highest-leverage cross-cutting gap").* Observations are **projected** (not dumped). New module `token_world.engine.observation` implements a `VisibilityProjector` that, given an actor node, returns a "visible state dict" by composing:
  - **Containment walk** — only properties of nodes in the actor's current location (`location` edge), plus nodes held by the actor (`holds` edge).
  - **Illumination filter** — nodes in rooms where `illumination` (property on the room) is below a threshold are excluded unless the actor holds a light source. *Feeds MECH23 illumination seed behaviour; no retroactive changes to MECH23.*
  - **Property visibility classes** — every property has an implicit visibility class; `hidden_properties: list[str]` on a node is honoured. Unknown properties default to visible to keep v1 simple.
  - **Belief overlay (GAP-GRAPH04)** — if the actor has a `beliefs` dict, beliefs override ground-truth values in the projection **for properties the actor has direct evidence of**; for properties the actor has never observed, ground truth is shown. Minimal implementation: `beliefs[node_id] = {prop: value}`. Not a full epistemic logic; just enough to make MECH10 `tell` / MECH25 `partial_knowledge_update` work (GAP-GRAPH04 closure).
- **D-15** — *Source: SIM-05 (grounded observations) + GAP-ENG12.* The Sonnet observer receives the projected state dict + the mechanic's execution trace, and synthesises prose under a **hard grounding constraint**: the system prompt enumerates "use only facts that appear in the provided state dict; if a property isn't present, don't mention it." Test: a rubric test (deferred to Phase 6 TEST-04 as LLM-verifier regression) checks phrases against the state dict. Phase 5 ships the constraint + one pytest-level cheap grounding assertion (substring-check against projected state); full rubric is Phase 6. Covers GAP-ENG12 (hard-constraint template).

### Conservation Enforcement — Post-Execution, YAML-Configured

- **D-16** — *Source: SIM-08 + GAP-ENG06.* A `ConservationChecker` runs **after** `execute` and **before** observation synthesis. Input: the `list[Mutation]` produced by the chain. It scans mutations for a configured set of `conserved_properties` (YAML at `universe/conservation.yaml`, e.g., `[health, coin, mass]`) and requires every increment to have a matching decrement of the same magnitude within the same tick's mutations. Violation → re-raise as `ConservationError`, rollback the tick's mutations via the existing snapshot mechanism (Phase 1), and return a refusal narrative. Default `conservation.yaml` is empty (no enforcement) — mechanics opt in per universe. Rejected: per-mechanic inline assertions. Rationale: YAML keeps it declarative and lets the operator add conserved properties without editing mechanic code.

### Passive Tick Sweep — Tick-End Hook

- **D-17** — *Source: GAP-ENG07 + GAP-ENG09.* After the primary action's chain completes, the engine runs a **passive sweep**: iterate all `involuntary` mechanics whose matcher is `WorldPropertyMatcher`, `DecayMatcher` (new — matches any node with a `decay_period` property), or `TickMatcher` (new — always matches once per tick). Each is executed with a dummy actor/target (`_engine_tick_sentinel` node per Phase 3 validator_exception pattern). Chain depth policy and conservation apply to sweep mutations too. Rejected: running passives before the action. Rationale: matches the "reaction to state" mental model; action first, world reacts after. Closes GAP-ENG07 + feeds GAP-MECH20/21/22/24 correctness.
- **D-17b** — *Source: GAP-ENG17 + GAP-ENG18.* Chain truncation events (cycle detected or `max_chain_depth` hit) are surfaced as a `chain_truncated` entry in the execution trace AND as a one-line mention in the observation ("Time blurs as events cascade..."). Closes GAP-ENG17. `max_chain_depth` respects D-03 universe-config key (closes GAP-ENG18).

### Turn Ordering — Single-Agent Invariant in v1

- **D-18** — *Source: GAP-ENG13, GAP-ENG14.* v1 is single-agent (PROJECT.md). Engine invariant: **at most one resident-agent action per tick**. GAP-ENG13/GAP-ENG14 conflict-detection is deferred to v2 multi-agent. Phase 5 documents this invariant in the engine's docstring and in `docs/design/architecture.md`. No code changes beyond the docstring.

### Determinism — Seeded RNG on MechanicContext

- **D-19** — *Source: GAP-GRAPH05.* Phase 5 adds `ctx.rng` — a seeded `random.Random` instance, seed derived deterministically from `(universe_seed, tick_id)`. Universe seed stored at `universe/universe.yaml` (new, created on scaffold with a random seed; existing universes get a seed on first `run_tick`). Contagion (MECH24), fire-spread probability, any future stochastic mechanic uses `ctx.rng` instead of `random.random()`. AST rule (extend Phase 4 D-14): `import random` is forbidden in mechanics — must use `ctx.rng`. Closes GAP-GRAPH05.

### Tick Summary Writer (SIM-11)

- **D-20** — *Source: SIM-11 + PROJECT.md "hierarchical tick summaries".* After every `run_tick`, engine writes `universe/tick_summaries/tick_<tick_id>.json` with fields:
  - `tick_id`, `timestamp_iso`, `action_text`, `classified_action`, `matched_mechanic_id_or_null`, `yielded` (bool), `refused` (bool), `refusal_reason_or_null`, `mutations` (count + list of [node, property, old, new] tuples), `observation_text`, `duration_ms`, `llm_tokens_by_stage` (classifier, observer), `llm_cost_usd_by_stage`.
- **D-21** — *Source: PROJECT.md SIM-12 (deferred to Phase 6).* Phase 5 writes tick-level summaries only; batch (100 ticks) and epoch (100 batches) compression is Phase 6 (SIM-12). But Phase 5's tick schema MUST be forward-compatible — the batch compressor consumes these files. Schema version `1` declared in the JSON.

### Diagnostics Wiring (AUTO-02 End-to-End)

- **D-22** — *Source: AUTO-02 + Phase 4 D-21/D-23.* Every LLM call in the pipeline writes to the `DiagnosticsSink` per Phase 4's schema:
  - `classification/{prompt.txt, response.txt, parsed.json}` — one per tick.
  - `matching.json` — scoring reasoning, candidate list.
  - `execution/{trace.json, mutations.jsonl}` — from `ChainExecutionEngine` (Phase 2).
  - `observation/{prompt.txt, response.txt, parsed.json}` — one per tick.
  - `summary.json` — the tick summary (same content as tick_summaries/ but scoped to diagnostics).
- **D-23** — *Source: AUTO-02.* No mocking the diagnostics sink in Phase 5 tests — run it for real against a temp directory. Phase 4's sink already handles atomic writes + symlink safety.

### Cost & Telemetry

- **D-24** — *Source: PROJECT.md "Budget: hobby project" + HARD-03 (deferred to v2).* Phase 5 logs token counts and cost per stage to `tick_summary.json` (D-20) but does NOT introduce circuit breakers or cost caps per-universe. HARD-03 remains v2. Rationale: visibility beats automation at hobby scale; operator-user can notice a rogue universe from tick summaries.

### Claude's Discretion (planner + researcher have flexibility here)

- **D-25** — Classifier system prompt exact wording (structured-output schema is locked per D-05, but prompt phrasing is tuneable).
- **D-26** — Observer system prompt exact wording (grounding constraint language is locked per D-15, but phrasing is tuneable).
- **D-27** — `scoring` algorithm in the deterministic matcher (D-09 picks "verb-match + target-type-match + actor-type-match weighted sum"; exact weights/tie-break are implementation details).
- **D-28** — Exact layout of `token_world/engine/` subpackage — whether to split into `classifier.py`, `matcher.py`, `decider.py`, `observer.py`, `conservation.py`, `visibility.py`, `tick_summary.py`, `engine.py`, or cluster related bits. Planner picks.
- **D-29** — Whether to ship a thin `run-engine-turn <universe> "<action>"` CLI (not in SIM-01..11, but natural extension). Recommended: yes, add to `token-world` Click group as `engine-turn`; Claude discretion on whether to include it in Phase 5 or defer.
- **D-30** — Pydantic models for classifier response / classified action / match result / decision / observation output — planner picks module layout. Locked: they exist and are used for all structured LLM outputs.

### Proposed Plan Decomposition (informative; planner has final say)

Wave 0 (foundation; sequential):
1. **05-01 — Core scaffold + classifier** — `token_world.engine/` subpackage skeleton, `ClassifiedAction` + `ClassifierVerdict` Pydantic models (D-05, D-06), Haiku wrapper via raw SDK (D-04), universe-config loader extension for `engine.*` keys (D-03, D-07), `ctx.rng` seeded RNG (D-19) + AST rule update (D-19) to forbid `import random` in mechanics, `universe.yaml` seed field + scaffold update. Tests: classifier verdicts, RNG determinism, AST rejection.

Wave 1 (parallel — can run concurrently):
2. **05-02 — Matcher + WorldPropertyMatcher** — `Matcher` interface, deterministic scoring implementation (D-09), `WorldPropertyMatcher` + `DecayMatcher` + `TickMatcher` (D-10, D-17), `MatchResult` discriminated union (D-11). Tests: scoring ties, candidates list, new matcher dispatch.
3. **05-03 — Decider + RefusalTemplate + ctx.refuse helper** — `decide()` precedence ladder (D-12), shared `RefusalTemplate` (D-13), `MechanicContext.refuse()` helper wires into the same template. Tests: precedence (no_viable → refuse beats no_match → yield); refusal narrative stability across three refusal sources.
4. **05-04 — Observation projection (visibility + belief overlay)** — `VisibilityProjector` (D-14), belief overlay, containment walk, illumination filter, property visibility classes. Tests: UC-S05 / UC-V06 / UC-O07 / UC-E03 projection cases. Closes GAP-CROSS01 + GAP-GRAPH04.
5. **05-05 — Observation synthesiser (Sonnet)** — Observer wrapper via raw SDK, grounding constraint prompt (D-15), substring grounding assertion (Phase-5 cheap version of TEST-04). Tests: hallucination-prevention smoke test, trace→observation correctness.
6. **05-06 — Conservation checker + YAML config** — `ConservationChecker`, `conservation.yaml` parser, rollback-on-violation via snapshot (D-16). Tests: UC-R07 (attempted conservation violation), empty config = no enforcement, matched increment/decrement pairs pass.
7. **05-07 — Passive tick sweep** — Tick-end hook, sweep across `WorldPropertyMatcher` / `DecayMatcher` / `TickMatcher` mechanics (D-17), chain truncation events surfaced (D-17b). Tests: UC-V01/V02/V03 passive-tick behaviour; MECH20/21/22/24 now fire on tick.

Wave 2 (integration; sequential):
8. **05-08 — Engine orchestrator + tick summary writer** — `SimulationEngine.run_tick(action_text, actor)` wires all stages (D-01, D-02), tick summary writer (D-20, D-21), diagnostics sink wiring (D-22, D-23), chain_depth config (D-03), cost accounting (D-24). Tests: end-to-end happy path, end-to-end yield path (feeds Phase 4.1 harness), end-to-end refuse path.
9. **05-09 — Real engine replaces Phase 4.1 engine stub** — Swap `EngineStub` out; Phase 4.1 integration test now drives through the real classifier/matcher; engine stub retained in `src/token_world/operator/testing.py` for backwards compat with tests that want deterministic yield fabrication. Tests: Phase 4.1 harness integration test (real Opus, marked `integration`) still passes against real engine.
10. **05-10 — MCP tool wiring** — `resume_tick` MCP tool (Phase 0 stub) now calls `SimulationEngine.run_tick`; `list_mechanics` reads from registry; `rollback` calls `GraphPersistence.restore_snapshot`. Replaces all three Phase 0 stubs with real implementations. Tests: mcp_server.py integration tests updated from "not implemented" assertions.
11. **05-11 — `token-world engine-turn` CLI (optional per D-29)** — Thin CLI over the engine for dev-UX: `token-world engine-turn <universe> <actor> "<action>"` runs one tick and prints classified / matched / mutations / observation. Tests: CLI smoke test.
12. **05-12 — Verification & docs + retro** — Run all 35 UCs through the real engine; update `.planning/GAP-HANDOFF.md` dispositions (mark Phase-5 gaps CLOSED); update `docs/design/architecture.md` with engine component diagram; `VALIDATION.md` finalisation; retrospective.

Wave count: 3 (Wave 0 sequential → Wave 1 six-way parallel → Wave 2 sequential integration). Planner may merge/split; this is a strawman.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Vision & Decisions
- `.planning/PROJECT.md` §Key Decisions — Hybrid SDK, model routing, single-agent v1, hierarchical tick summaries
- `.planning/PROJECT.md` §Constraints — Python, flexible schema, persistence, hobby-project budget, grounding obsession
- `.planning/DECISIONS.md` — chronological decision log (will be updated by Phase 5)
- `CLAUDE.md` — conventions, graph-is-ground-truth invariant, JSON-serializable properties, two-node-types, operating principles

### Requirements (owned by this phase)
- `.planning/REQUIREMENTS.md` §Simulation Engine — SIM-01..SIM-08, SIM-11 (Phase 5 scope per traceability table)
- `.planning/REQUIREMENTS.md` §Agent Autonomy — AUTO-02 (diagnostics fully wired; Phase 4 built the sink, Phase 5 wires the engine LLM calls)

### Requirements (explicitly deferred out of Phase 5)
- SIM-09, SIM-10 → Phase 7 (attention/consciousness)
- SIM-12 → Phase 6 (tick-summary compression)
- AGENT-01..04, TEST-04/05/07, AUTO-05/06/07, DVAL-03 → Phase 6

### Phase 3 Outputs — Primary Inputs to Phase 5
- `.planning/GAP-ANALYSIS.md` — canonical gap synthesis; 20 gaps (19 P5 + GAP-ENG16 split-ownership) route to Phase 5
- `.planning/GAP-HANDOFF.md` §Phase 05 — **19 gap rows the engine must close**: GAP-GRAPH04/05, GAP-ENG01..GAP-ENG18 (minus ENG16 Phase-4 half), GAP-CROSS01/02. Every Phase 5 plan MUST cite the relevant gap IDs in frontmatter.
- `.planning/use-cases/` — 35 manifest files across spatial/social/resource/environmental/edge-case. Plan 05-12 verification runs the engine against each; manifests already declare expected mechanic + expected observation.
- `.planning/phases/03-design-validation/03-CONTEXT.md` — use-case format
- `.planning/phases/03-design-validation/03-RESEARCH.md` — gap-elicitation method

### Phase 4 Outputs — Primary Inputs to Phase 5
- `.planning/phases/04-llm-mechanic-generation/04-CONTEXT.md` §Decisions:
  - D-12..D-16 validation pipeline (engine calls this transitively via registry auto-scan)
  - D-21..D-25 diagnostics substrate schema (Phase 5 is the per-tick populator)
  - D-34 GAP-ENG16 Phase-4/Phase-5 split — Phase 5 classifier must return `no_viable_action` on nonsense; validation gate (Phase 4 side) is already shipped
  - D-36..D-38 seed mechanics — 27 seed mechanics live in `mechanics/`; engine matches against them
- `.planning/phases/04-llm-mechanic-generation/04-RESEARCH.md` — MECH-03/04 research; same research discusses classifier/observer design
- `.planning/phases/04-llm-mechanic-generation/04-VERIFICATION.md` — Phase 4 verification report (what the engine inherits)

### Phase 4.1 Outputs — Primary Inputs to Phase 5
- `.planning/phases/04.1-operator-agent-harness/04.1-CONTEXT.md` §Decisions:
  - D-07 `YieldSignal` contract — **Phase 5 MUST produce yield signals of exactly this shape.** Locked contract.
  - D-08 `resume_tick` idempotence w.r.t. registry
  - D-09/D-10 Engine stub → replaced by Phase 5 real engine
- `src/token_world/operator/yield_signal.py` — **the locked contract**. Phase 5's yield emission MUST import this and produce instances; no divergence.
- `src/token_world/operator/testing.py` — `EngineStub.fabricate_yield` shows the shape by example; retained for tests even after Phase 5 lands (per D-29 in 04.1-CONTEXT)

### Stack & Architecture
- `.planning/research/STACK.md` §Agent Framework — model routing (Haiku classifier, Sonnet observer); MCP tool list (`resume_tick`, `rollback`, `list_mechanics` — Phase 5 replaces stubs)
- `.planning/research/ARCHITECTURE.md` — architecture considerations (pre-Phase-5; will need update post-phase)
- `.planning/research/SDK-SESSIONS.md` — Anthropic SDK patterns; structured output handling
- `.planning/research/THEACT-PATTERNS.md` — universe-as-codebase pattern; engine fits inside
- `.planning/research/PITFALLS.md` — hallucination risks, grounding failures
- `docs/design/architecture.md` — system component diagrams (will need update showing engine pipeline + observation projector + conservation checker)

### Existing Code (consumed by this phase)
- `src/token_world/graph/*` — KnowledgeGraph, EventStore, snapshots (Phase 1); engine uses snapshots for conservation-violation rollback (D-16)
- `src/token_world/mechanic/context.py` — `MechanicContext`; Phase 5 extends with `ctx.rng` (D-19) and `ctx.refuse` (D-13)
- `src/token_world/mechanic/engine.py` — `ChainExecutionEngine`; Phase 5 calls this inside its `execute` stage (D-01)
- `src/token_world/mechanic/matchers.py` — Phase 5 adds `WorldPropertyMatcher`, `DecayMatcher`, `TickMatcher` (D-10, D-17)
- `src/token_world/mechanic/validation.py` — Phase 5 extends AST rules to forbid `import random` (D-19)
- `src/token_world/mechanic/diagnostics.py` — Phase 5 populates the sink (D-22, D-23)
- `src/token_world/mechanic/registry.py` — Phase 5 depends on auto-scan (D-02)
- `src/token_world/mechanic/seeds/*` — 27 seed mechanics; engine matches against these
- `src/token_world/operator/yield_signal.py` — Phase 5 imports, does not duplicate
- `src/token_world/mcp_server.py` — Phase 5 replaces "not implemented" stubs (plan 05-10)
- `src/token_world/cli.py` — Phase 5 adds `engine-turn` command (optional; D-29)
- `src/token_world/universe/scaffold.py` — Phase 5 extends to seed `universe.yaml` with `universe_seed` and optional `conservation.yaml` (D-16, D-19)
- `src/token_world/universe/templates/claude_md.py` — updated for engine behaviour description + conservation.yaml authoring note

### New Code (this phase creates)
- `src/token_world/engine/__init__.py` — public API (`SimulationEngine`, models, exceptions)
- `src/token_world/engine/engine.py` — orchestrator `SimulationEngine.run_tick`
- `src/token_world/engine/classifier.py` — Haiku wrapper + Pydantic models for verdicts
- `src/token_world/engine/matcher.py` — deterministic matcher + `MatchResult`
- `src/token_world/engine/decider.py` — precedence ladder + `RefusalTemplate`
- `src/token_world/engine/visibility.py` — `VisibilityProjector` (containment + illumination + beliefs)
- `src/token_world/engine/observer.py` — Sonnet wrapper + grounding constraint
- `src/token_world/engine/conservation.py` — `ConservationChecker` + YAML config loader
- `src/token_world/engine/passive_sweep.py` — tick-end passive mechanic dispatcher
- `src/token_world/engine/tick_summary.py` — tick summary JSON writer
- `tests/test_engine/*` — unit tests per stage (Wave 1 plans); integration tests (Wave 2 plans)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Phase 1 graph + snapshots** — conservation rollback (D-16) uses `GraphPersistence.restore_snapshot` directly; no new rollback primitive needed.
- **Phase 2 `ChainExecutionEngine`** — engine.execute() stage is a thin wrapper over this; chain depth, involuntary chaining, trace emission all already work.
- **Phase 2 matcher primitives** — `VerbMatcher`, `NullMatcher` exist; Phase 5 adds three more (`WorldPropertyMatcher`, `DecayMatcher`, `TickMatcher`) in the same module.
- **Phase 4 validation pipeline** — AST rules extended for `import random` ban (D-19); same code path, one rule added.
- **Phase 4 `DiagnosticsSink`** — Phase 5 is the populator; no schema changes (Phase 4 D-21 already describes the engine-populated layout).
- **Phase 4.1 `YieldSignal`** — imported and produced; Phase 5 does not define a new contract.
- **Phase 4 registry auto-scan** — `resume_tick` picks up newly-authored mechanics for free; Phase 5 just calls the registry.

### Established Patterns
- Raw Anthropic SDK for deterministic inner-loop calls (classifier, observer). Pattern established by STACK.md model-routing decision.
- Pydantic for structured LLM outputs. Pattern established by STACK.md supporting libraries.
- `sqlite3` context manager for persistence, JSON-serializable properties, `claim_id` for unique IDs.
- Ruff + mypy clean; prek pre-commit hooks.
- pytest parametrisation with use-case manifests (Phase 4 D-26..D-29).
- Universe folder self-contained; engine config lives in `universe/universe.yaml` + `universe/conservation.yaml` (new; both operator-editable).

### Integration Points
- `universe/diagnostics/tick_<id>/` — fully populated per D-22 schema; existing Phase 4.1 `operator/` subfolder coexists.
- `universe/tick_summaries/tick_<id>.json` — new per D-20; consumed by Phase 6 SIM-12 compressor.
- `universe/universe.yaml` — new config file; `engine.max_chain_depth`, `engine.classifier_min_confidence`, `universe_seed` keys.
- `universe/conservation.yaml` — new optional config file; list of conserved properties (D-16).
- `src/token_world/mcp_server.py` — the 3 stubs become real in plan 05-10.

### Scale Consideration
- Classifier + observer = 2 LLM calls per tick. Budget implication: ~$0.001–$0.01 per tick at Haiku+Sonnet prices. Well within hobby budget for 10^4 ticks. D-24 logs token use so regressions are visible.
- Passive sweep complexity is `O(involuntary_mechanics × world_properties)` per tick. At hobby scale (tens of mechanics, tens of world properties) this is milliseconds. Scale-up concerns deferred to v2.

</code_context>

<specifics>
## Specific Ideas

- **"Grounding is non-negotiable."** CLAUDE.md operating principle 9 ("graph is ground truth") + GAP-CROSS01 + SIM-05/SIM-07 all point to the same thing: observations derive from projected graph state, not free generation. The observer prompt enforces this, the visibility projector implements it, the tick summary records what was projected for audit.
- **"The engine orchestrates; it does not decide what's possible."** Every "what actions are valid?" question resolves to "what mechanics are in the registry?" — and the registry is ground truth. Engine is a pipeline, not a policy maker.
- **"Refusals are first-class, not exceptions."** Three refusal surfaces (classifier-refusal, match-refusal, mechanic-refusal) all route through `RefusalTemplate` (D-13). From the resident agent's perspective, "you can't do that" is indistinguishable across the three — the world simply doesn't permit it, same narrative family. This matters for Phase 6 agent memory: the agent learns "graghing doesn't work" the same way it learns "lifting this rock doesn't work because it's too heavy."
- **"Yield is a last resort, not a default."** D-12's precedence ladder: classifier refuses first, mechanic decides second, yield only if both pass. The yield pipe is the expensive one (operator spins up an Opus subagent); we keep it narrow on purpose.
- **"Conservation is opt-in."** D-16 ships an empty default `conservation.yaml`. Universes that don't care about matter-accounting don't pay for it. Universes that do can start with one property (coin) and grow. This matches the "emergent properties" philosophy.
- **"Passive mechanics are first-class."** GAP-ENG07 is closed by making "decay / weather / fire / contagion" run automatically every tick without the resident agent needing to invoke them. World reacts to state even when no one is looking — closes the "mechanism to make the world feel alive" hole.
- **"Universe-as-codebase principle still holds at the engine layer."** Config in YAML files the operator edits (`universe.yaml`, `conservation.yaml`), not hardcoded constants. Every engine behaviour the operator might want to tune is in a config file.

</specifics>

<deferred>
## Deferred Ideas

- **Multi-turn offer/accept protocol for trade (GAP-ENG01)** — v2, requires multi-agent.
- **Multi-actor mechanics / intent fusion pass (GAP-ENG05, GAP-MECH12 runtime)** — v2, requires multi-agent. MECH12 stub from Phase 4 remains a stub until v2.
- **Turn ordering / concurrent-actor conflict detection (GAP-ENG13, GAP-ENG14)** — v2, requires multi-agent. Phase 5 documents single-agent invariant (D-18) but doesn't enforce via code beyond the docstring.
- **Calendar / `day_of_year → season` formalisation (GAP-ENG10)** — v2 scope. `WorldPropertyMatcher` (D-10) is the hook that makes it a later mechanic authoring task, not an engine change.
- **LLM-based semantic fallback matcher** — rejected per D-09; revisit if deterministic matching proves insufficient in practice.
- **Hierarchical tick summary compression (SIM-12)** — Phase 6. Phase 5 writes tick-level only; format is forward-compatible per D-21.
- **LLM-verifier rubric test for observation grounding (TEST-04)** — Phase 6. Phase 5 ships a cheap substring grounding assertion per D-15.
- **Circuit breakers / cost caps (HARD-03)** — v2. Phase 5 logs telemetry per D-24 without enforcing caps.
- **Runtime sandboxing (RestrictedPython)** — v2 per PROJECT.md.
- **Coherence checking between new and existing mechanics (HARD-02)** — v2.
- **Playtest runner + quality scoring + regression suite (AUTO-05/06/07, TEST-07, DVAL-03)** — Phase 6.
- **Resident agent with personality + memory + session forking (AGENT-01..04, TEST-04/05)** — Phase 6.
- **Attention / consciousness / duration-aware actions (SIM-09, SIM-10)** — Phase 7.

</deferred>

---

*Phase: 05-simulation-engine*
*Context gathered: 2026-04-13 via `/gsd-discuss-phase 5 --auto` — autonomous selection of recommended options for every gray area*
*Prior context integrated: Phase 0, 1, 2, 3, 4, 4.1 CONTEXT.md files; GAP-HANDOFF.md Phase-5 handoff; PROJECT.md; REQUIREMENTS.md; STACK.md*
