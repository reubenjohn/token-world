# Phase 5: Simulation Engine — Research

**Researched:** 2026-04-13
**Domain:** Anthropic raw-SDK (structured outputs) + Pydantic + pipelined action classification + mechanic matching + observation projection + conservation checking + passive-tick sweeps + diagnostics wiring
**Confidence:** HIGH (every decision maps to stdlib, Pydantic, or existing in-tree primitives; no new frameworks required beyond already-adopted Anthropic SDK)

## Summary

Phase 5 is the largest phase in the project by file count but the least exotic technically. Every decision in 05-CONTEXT.md maps onto:

- **Python stdlib** (`dataclasses`, `enum`, `pathlib`, `json`, `yaml` via `PyYAML` already in `pyproject.toml`, `random.Random`).
- **Pydantic v2.12+** (already in use for mechanic DSL and use-case manifests) for structured LLM output schemas.
- **Raw Anthropic SDK** (`client.messages.create` with tool-less structured output per Phase 4 stack research) for the two LLM stages — classifier (Haiku) and observer (Sonnet).
- **Existing primitives:** Phase 1 `KnowledgeGraph` + `GraphPersistence` (snapshots for conservation rollback); Phase 2 `ChainExecutionEngine` (chain execution already handles `max_depth` + truncation); Phase 2 `MechanicContext` DSL (extend with `ctx.rng`, `ctx.refuse`); Phase 3 use-case manifests (end-to-end regression inputs); Phase 4 `DiagnosticsSink` (already atomic, schema-versioned); Phase 4.1 `YieldSignal` (LOCKED contract).

The highest-leverage research findings:

1. **The staged pipeline is essentially already drawn.** Phase 4 D-21 prescribed the exact diagnostics filesystem shape (`classification/`, `matching.json`, `execution/`, `observation/`, `summary.json`) before Phase 5 was planned. The stages in 05-CONTEXT D-01 map 1:1 onto those folders. Researcher confidence that "the right decomposition" is uncontroversial: very high. The planner's job is mechanical decomposition and interface-contract definition, not architecture invention.

2. **Classifier = Pydantic-validated JSON output from Haiku with discriminated-union verdict.** Anthropic SDK supports `response_format={"type": "json_object"}` plus a schema-hint system prompt. Alternative tool-use-based extraction is heavier and doesn't pay for itself at hobby scale. We ship a `ClassifierVerdict` tagged-union Pydantic model with four variants (ok, no_viable_action, no_such_target, low_confidence per D-06) and a minimal Haiku wrapper that parses the raw JSON and validates through the model. Parse failures → retry once with a corrective prompt; second failure → emit `no_viable_action(reason="classifier output malformed")`.

3. **Matcher = deterministic scoring, no LLM.** Per D-09, matching is a loop over registered voluntary mechanics + their declared matcher (`VerbMatcher` already exists; `WorldPropertyMatcher`/`DecayMatcher`/`TickMatcher` are three ~30-LOC new matcher classes added to `token_world.mechanic.matchers`). Scoring formula: `score = 3*verb_match + 2*target_type_match + 1*actor_type_match`, ties broken alphabetically by mechanic id. **Result:** if best score > 0 → `matched(mechanic, score, reasoning)`; else `no_match(candidates=top_K_scored_zero_or_positive_mechanics)`. A "full ban" mode is NOT needed because the registry is always complete; candidates list is for `YieldSignal.candidate_mechanic_ids`.

4. **Visibility projection is a pure function.** Per D-14, `VisibilityProjector(graph).project_for(actor)` walks containment edges outward from `actor.location`, adds actor's `holds`, applies illumination filter (room.illumination < threshold + actor lacks light-source node type → room's interior dimmed to just "dark"), and overlays `actor.beliefs` on top of ground truth for nodes the actor has direct evidence of. Output: a JSON-serializable dict keyed by node id, each containing {properties: {visible}, edges: [visible neighbors]}. No LLM here — grounding happens by construction. The Sonnet observer consumes this dict, not the raw graph.

5. **Conservation checker is YAML-config-driven.** Per D-16, at startup engine reads `universe/conservation.yaml` (optional; empty default). For each listed property name (e.g., `coin`, `health`), every `set_property` mutation that changes that property is recorded with its delta. After a tick completes, sums-per-property are verified to be zero (modulo explicit "sources" / "sinks" which are deferred to v2 — v1 requires strict conservation). On violation: restore snapshot (Phase 1), return refusal narrative via shared `RefusalTemplate` (D-13). Empty config = no enforcement = no overhead for universes that don't care.

6. **Passive tick sweep is one more loop.** After the chain finishes, engine iterates `registry.involuntary_mechanics()` and invokes any whose matcher is `TickMatcher`, `DecayMatcher`, or `WorldPropertyMatcher` (and whose preconditions pass). Same `ChainExecutionEngine` drives this; the sweep uses a sentinel actor (`_engine_tick_sentinel` per Phase 3 validator_exception pattern). Chain depth limits apply. Truncation events surface via D-17b.

7. **`YieldSignal` already locked.** Phase 5 imports `from token_world.operator.yield_signal import YieldSignal` and constructs instances. Zero contract re-design. Plan 05-08 integration tests verify the shape is byte-identical to what Phase 4.1's `EngineStub` fabricated, replacing only the producer.

8. **Diagnostics wiring is straight plumbing.** `DiagnosticsSink` already has `open_tick(tick_id) -> TickContext` with `write_prompt(stage, text)`, `write_response(stage, text)`, `write_parsed(stage, obj)`. Engine calls these at classifier + observer boundaries. `matching.json` and `execution/` are written as the matcher / ChainExecutionEngine return. `summary.json` is written in `close_tick`. No schema changes needed — Phase 4 defined it for Phase 5 to populate.

**Primary recommendation:** Treat Phase 5 as **3 waves, 12 plans**:
- **Wave 0 (sequential, 1 plan)**: core scaffolding + classifier + RNG + config loader. Gates all Wave 1 work.
- **Wave 1 (6-way parallel, 6 plans)**: matcher, decider+refusal, visibility projector, observer, conservation checker, passive sweep. Each is independently testable.
- **Wave 2 (sequential, 5 plans)**: engine orchestrator + tick summary writer, engine-stub swap, MCP tool wiring, optional CLI command, verification + docs + retro.

This matches the 05-CONTEXT.md decomposition proposal (D-25..D-37 "Proposed Plan Decomposition") modulo numbering — the planner accepted the CONTEXT author's strawman. No deviations from locked decisions. All 19 Phase-5 gap IDs from GAP-HANDOFF.md are explicitly addressed.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Every decision below is authoritative. Plans MUST implement it exactly.

- **D-01 — Staged pipeline.** Five explicit stages (classify → match → decide → execute → observe) with a thin `SimulationEngine.run_tick(action_text, actor)` orchestrator. No monolithic step method.
- **D-02 — Idempotent w.r.t. registry.** Every `run_tick` lets the registry auto-scan (Phase 4 D-15). Resume after operator authors mechanic: zero plumbing.
- **D-03 — `max_chain_depth` from universe-config.** `engine.max_chain_depth` in `universe/universe.yaml`, default 10. Closes GAP-ENG18.
- **D-04 — Haiku classifier.** `claude-haiku-4-5-20251001` via raw Anthropic SDK (`client.messages.create`). Pydantic-validated JSON output.
- **D-05 — Classified-action schema.** Four fields: `verb`, `actor`, `target` (optional), `indirect_object` (optional), `params` (dict). `indirect_object` is new; closes GAP-ENG02.
- **D-06 — Four classifier verdicts.** `ok(classified)` | `no_viable_action(reason)` | `no_such_target(target_text)` | `low_confidence(reason, best_guess)`. Pydantic tagged union. Closes GAP-ENG11 + GAP-ENG15 + Phase-5 half of GAP-ENG16.
- **D-07 — Confidence threshold.** Universe-config `engine.classifier_min_confidence`, default 0.6.
- **D-08 — Trade multi-turn deferred.** GAP-ENG01 remains v2 scope (multi-agent). MECH07 trade stays single-tick.
- **D-09 — Deterministic matcher.** Scoring formula: verb-match + target-type-match + actor-type-match. Ties broken alphabetically by mechanic id. No LLM fallback matcher.
- **D-10 — WorldPropertyMatcher.** New matcher primitive added to `token_world.mechanic.matchers`. Closes GAP-ENG09.
- **D-11 — `MatchResult` discriminated union.** `matched(mechanic, score, reasoning)` | `no_match(classified_action, candidates: list[str])`.
- **D-12 — Precedence ladder.** `decide()`: classifier-refusal → execute → yield. Yield only if both classifier AND matcher pass except no match found.
- **D-13 — Shared `RefusalTemplate`.** One narrative template across classifier-refusal, match-refusal (mechanic `check` returns `CheckResult(passed=False)`), and `ctx.refuse(reason_code, details)` helper for mechanics. Sonnet-rendered from template.
- **D-14 — VisibilityProjector.** Containment walk + illumination filter + property visibility classes + belief overlay (GAP-GRAPH04). Closes GAP-CROSS01.
- **D-15 — Hard grounding constraint.** Observer system prompt enumerates "use only facts in the provided state dict." Cheap substring grounding assertion ships in Phase 5; full rubric Phase 6 (TEST-04). Closes GAP-ENG12.
- **D-16 — ConservationChecker.** Post-execution, pre-observation. YAML config at `universe/conservation.yaml`. Empty default = no enforcement. Violation = snapshot-restore + refusal narrative. Closes GAP-ENG06.
- **D-17 — Passive tick sweep.** Tick-end, iterate involuntary mechanics matched by `WorldPropertyMatcher` / `DecayMatcher` / `TickMatcher`. Uses `_engine_tick_sentinel` sentinel actor. Closes GAP-ENG07.
- **D-17b — Chain truncation surfaced.** Truncation entry in execution trace + one-line observation mention. Closes GAP-ENG17 + GAP-ENG18.
- **D-18 — Single-agent invariant.** GAP-ENG13/GAP-ENG14 deferred to v2. Docstring documents invariant only.
- **D-19 — Seeded RNG.** `ctx.rng` = `random.Random(seed=(universe_seed, tick_id))`. `import random` banned in mechanics via AST rule extension (Phase 4 D-14 extended). Closes GAP-GRAPH05.
- **D-20 — Tick summary JSON.** `universe/tick_summaries/tick_<tick_id>.json` with schema-version-1 JSON per D-20 field list.
- **D-21 — Forward-compatible tick summary.** Schema must survive Phase 6 SIM-12 compression.
- **D-22 — Diagnostics wiring.** Every LLM call writes to `DiagnosticsSink` per Phase 4 D-21 schema. No schema additions.
- **D-23 — No mocking the sink.** Real sink against tmp dir in tests.
- **D-24 — Log cost, no circuit breakers.** HARD-03 remains v2.

### Claude's Discretion

- **D-25** — Classifier prompt exact wording (schema locked).
- **D-26** — Observer prompt exact wording (grounding constraint locked).
- **D-27** — Scoring algorithm weights/tie-break details.
- **D-28** — `token_world/engine/` submodule layout. *Recommendation:* split into `classifier.py`, `matcher.py`, `decider.py`, `visibility.py`, `observer.py`, `conservation.py`, `passive_sweep.py`, `tick_summary.py`, `engine.py`. One concern per file matches Phase 4 `mechanic/` pattern. One thin `models.py` holding shared Pydantic types.
- **D-29** — Ship `token-world engine-turn` CLI. *Recommendation:* yes; one more Click command on existing `cli.py` group; dev UX win that doesn't cost much.
- **D-30** — Pydantic models layout — inside `engine/models.py`.

### Deferred Ideas (OUT OF SCOPE)

- GAP-ENG01 multi-turn trade (v2, multi-agent).
- GAP-ENG05 intent-fusion (v2, multi-agent).
- GAP-ENG10 calendar formalisation (v2; `WorldPropertyMatcher` hooks it).
- GAP-ENG13/14 turn ordering (v2, multi-agent).
- GAP-MECH12 multi-actor mechanic runtime (v2; stub exists).
- LLM-based semantic fallback matcher (rejected per D-09).
- SIM-12 tick-summary compression (Phase 6).
- TEST-04 LLM-verifier rubric (Phase 6).
- HARD-02 coherence checking (v2).
- HARD-03 circuit breakers (v2).
- RestrictedPython runtime sandboxing (v2).
- Phase 6 resident-agent + personality + memory + session forking.
- Phase 7 attention / consciousness / duration-aware actions.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **SIM-01** | Engine interprets text output into structured actions | Haiku classifier (D-04, D-05, D-06). `ClassifierVerdict` Pydantic tagged union. Plan 05-01. |
| **SIM-02** | Engine matches structured actions to existing mechanics | Deterministic scoring matcher (D-09, D-10, D-11). `MatchResult` discriminated union. Plan 05-02. |
| **SIM-03** | Engine triggers mechanic generation when no mechanic matches | **Reframed per Phase 4 D-01/D-02:** engine emits `YieldSignal` (Phase 4.1 contract); operator harness handles mechanic authoring. Plans 05-03 (decider precedence) + 05-08 (orchestrator emits yield). |
| **SIM-04** | Engine executes matched mechanic and applies side effects | Phase 2 `ChainExecutionEngine` reused. Plan 05-08 (orchestrator wires it in). |
| **SIM-05** | Observations grounded in graph state | `VisibilityProjector` (D-14) + Sonnet observer grounding constraint (D-15). Plans 05-04 + 05-05. |
| **SIM-06** | Simulation history log records actions, mechanics used, mutations, observations | Tick summary writer (D-20) + diagnostics per-tick folder (D-22). Plans 05-08 + historical Phase-4 diagnostics substrate. |
| **SIM-07** | Observations contextually filtered — only relevant properties appear | Visibility projection property visibility classes (D-14). Plan 05-04. |
| **SIM-08** | Conservation laws enforced | `ConservationChecker` YAML-config (D-16). Plan 05-06. |
| **SIM-11** | Per-tick summary JSON persisted | Tick summary writer (D-20). Plan 05-08. |
| **GAP-ENG16 (P5 half)** | Classifier returns `no_viable_action` for nonsense | `ClassifierVerdict.no_viable_action` variant (D-06). Plan 05-01. |
| **AUTO-02** (end-to-end wiring) | Every LLM call writes to diagnostics | `DiagnosticsSink` wiring at classifier + observer boundaries (D-22, D-23). Plan 05-08. |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

Plans MUST honor:

- **Python 3.12+.** `from __future__ import annotations` in every new module. `|` union syntax.
- **Graph mutations only through `KnowledgeGraph` API.** Engine does NOT mutate the graph directly; mutations come from mechanics via `MechanicContext`. Conservation rollback uses `GraphPersistence.restore_snapshot` (Phase 1 API).
- **JSON-serializable properties only.** `ALLOWED_PROPERTY_TYPES` constraint extends to tick summary + diagnostics JSON. `YieldSignal.classified_action["params"]` is `dict[str, Any]` but practically must survive `json.dumps`.
- **Two node types:** `agent`, `entity`. Engine sentinel `_engine_tick_sentinel` is an `agent` for consistency with Phase 3 validator_exception pattern (same as used for UC-V01..V04).
- **Raw `sqlite3` only — no ORM.** Engine does not introduce SQL; all persistence via existing Phase 1 API.
- **No pickle.** Tick summaries and diagnostics JSON only.
- **`uv` for deps.** No new dependencies expected — Anthropic SDK + Pydantic + PyYAML already installed.
- **`ruff`/`mypy`/`prek`/`pytest`.** `tests/test_engine/` mirrors `src/token_world/engine/`.
- **Node IDs via `kg.claim_id()`.** Engine claims `_engine_tick_sentinel` once at startup if it doesn't exist.
- **Hybrid SDK split preserved.** Engine uses raw Anthropic SDK (classifier + observer) — it's inside the simulation-tool layer, NOT the operator. Phase 4.1 owns Agent SDK surface.
- **Composition over specialization.** `RefusalTemplate` (D-13) routes three refusal sources through one surface. `VisibilityProjector` is one function called from multiple places. Three new matchers share `Matcher` abstract base.

**No CLAUDE.md directive conflicts with any locked decision.**

## Standard Stack

### Core — already in project

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` | ≥0.80 | Raw SDK for classifier (Haiku) + observer (Sonnet) | Already in `pyproject.toml` (Phase 4 / 4.1). Structured JSON via `response_format={"type": "json_object"}`. Per-call model routing. [VERIFIED: `pyproject.toml`, Phase 4 stack research] |
| `pydantic` | ≥2.12 | Structured LLM output schemas + tagged unions for `ClassifierVerdict` / `MatchResult` / `Decision` | Already in project (use-case manifests + STACK.md decision). v2 supports discriminated unions and `model_validate_json`. [VERIFIED: pyproject.toml] |
| `PyYAML` | ≥6 | Load `universe/universe.yaml` + `universe/conservation.yaml` | Already installed (transitive; Phase 4 use-case loader also uses it). [VERIFIED: `uv pip list`] |
| `random` (stdlib) | 3.12 | `Random` class with seeded RNG for `ctx.rng` | Seed = `hashlib.blake2b((universe_seed + str(tick_id)).encode(), digest_size=8).digest()` → `Random(seed=int.from_bytes(...))`. Deterministic, cheap, fast. [VERIFIED: stdlib standard pattern] |
| `click` | 8.3.2 | Optional `engine-turn` CLI command (D-29) | Existing CLI framework. Add as `@cli.command("engine-turn")`. [VERIFIED: `pyproject.toml`, `src/token_world/cli.py`] |
| `dataclasses` (stdlib) | 3.12 | Non-Pydantic value types (`Decision`, `EngineConfig`) — but lean toward Pydantic when validated from JSON | Stdlib. Already used throughout. |
| `pathlib` (stdlib) | 3.12 | Path handling | Stdlib |
| `json` (stdlib) | 3.12 | Tick summary + diagnostics JSON | Stdlib; atomic writes via Phase 4 `_atomic_write_json` helper already in `token_world.mechanic.diagnostics`. |
| `hashlib` (stdlib) | 3.12 | Blake2b for deterministic RNG seed derivation | Stdlib |

### New dependency

**None.** Every Phase 5 concern is covered by existing libraries.

### Supporting — in-tree primitives (reuse)

| Primitive | Location | Purpose |
|-----------|----------|---------|
| `KnowledgeGraph` | `src/token_world/graph/knowledge_graph.py` | Graph queries + mutations (via `MechanicContext`). |
| `GraphPersistence.restore_snapshot(snapshot_id)` | `src/token_world/graph/persistence.py` | Conservation violation rollback (D-16). |
| `GraphPersistence.create_snapshot(summary)` | `src/token_world/graph/persistence.py` | Pre-tick snapshot so we can restore on conservation failure. |
| `MechanicContext` | `src/token_world/mechanic/context.py` | Engine extends with `ctx.rng` (D-19) + `ctx.refuse(reason_code, details)` (D-13). |
| `ChainExecutionEngine` | `src/token_world/mechanic/engine.py` | Execute matched mechanic + involuntary chain. |
| `MechanicRegistry` | `src/token_world/mechanic/registry.py` | Auto-scan + voluntary/involuntary indexes. |
| `Mechanic`, `CheckResult`, `Mutation` | `src/token_world/mechanic/` | Contract surface. |
| `Matcher` ABC + `VerbMatcher` | `src/token_world/mechanic/matchers.py` | Base + existing matchers; plan 05-02 adds 3 more. |
| `DiagnosticsSink`, `TickContext` | `src/token_world/mechanic/diagnostics.py` | Plan 05-08 wires engine LLM calls into it. |
| `YieldSignal` | `src/token_world/operator/yield_signal.py` | **LOCKED contract.** Phase 5 imports, does not duplicate. |
| `EngineStub` | `src/token_world/operator/testing.py` | Test-only; swapped out in plan 05-09. Retained for deterministic yield fabrication in unit tests. |
| `use_cases/loader.py` | `src/token_world/use_cases/loader.py` | Use-case manifest loader; Plan 05-12 verification runs all 35 use cases through the real engine. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw Anthropic SDK for classifier/observer | Claude Agent SDK | Violates Hybrid-SDK split (CLAUDE.md Technology Stack). Agent SDK is for operator layer; simulation-tool LLM calls are deterministic pipeline calls. |
| Pydantic-validated structured output | Free-text JSON parsing + manual `json.loads` | Pydantic v2 gives free schema generation + validation errors with field path. ~15 LOC saved per validator. |
| Deterministic matcher (D-09) | LLM-based semantic matcher | Rejected in CONTEXT.md. Adds a third LLM call per tick; classifier already handles natural-language → verb. |
| Sonnet observer | Haiku observer | Sonnet per CONTEXT.md + STACK.md; observer needs more linguistic capability than classifier. Cost difference negligible at hobby scale. |
| YAML conservation config | Inline mechanic assertions | Declarative config matches "universe as codebase" philosophy. Empty default = opt-in. |
| Belief overlay as part of projection (D-14) | Separate belief-resolution stage | Keeping it inside the projector means downstream code (observer) sees a single "projected state" dict; no composition concerns. |
| Snapshot rollback for conservation | Per-mutation transaction machinery | Phase 1 already ships snapshots; no new rollback primitive needed. Cost: one extra snapshot per tick (cheap; already linked to tick IDs). |
| Sentinel `_engine_tick_sentinel` actor for passive sweep | None — run sweep without actor context | Phase 3 validator_exception pattern already uses this approach for UC-V01..V04 passive tick tests; consistency matters. |
| Pass `VisibilityProjection` dict to observer | Pass raw graph snapshot | Grounding by construction. Observer can hallucinate properties only if they exist in the projection — impossible without graph changes. |

## Architecture Patterns

### Recommended File Layout (Phase 5 additions)

```
src/token_world/
├── engine/                             # NEW subpackage
│   ├── __init__.py                     # Public API re-exports
│   ├── models.py                       # Pydantic models: ClassifierVerdict, ClassifiedAction, MatchResult, Decision, TickSummary
│   ├── config.py                       # EngineConfig loader (universe/universe.yaml)
│   ├── classifier.py                   # Haiku classifier via raw Anthropic SDK
│   ├── matcher.py                      # Deterministic scoring matcher
│   ├── decider.py                      # Precedence ladder: refuse | execute | yield
│   ├── refusal.py                      # RefusalTemplate + ctx.refuse helper (inserted into MechanicContext)
│   ├── visibility.py                   # VisibilityProjector
│   ├── observer.py                     # Sonnet observer via raw Anthropic SDK
│   ├── conservation.py                 # ConservationChecker + conservation.yaml loader
│   ├── passive_sweep.py                # Tick-end passive sweep
│   ├── tick_summary.py                 # Tick summary JSON writer
│   └── engine.py                       # SimulationEngine.run_tick orchestrator
├── mechanic/
│   ├── context.py                      # MODIFIED — add ctx.rng property (D-19) + ctx.refuse helper (D-13)
│   ├── matchers.py                     # MODIFIED — add WorldPropertyMatcher / DecayMatcher / TickMatcher (D-10, D-17)
│   └── validation.py                   # MODIFIED — AST rule: forbid `import random` in mechanics (D-19)
├── universe/
│   ├── scaffold.py                     # MODIFIED — seed universe.yaml (with universe_seed) + empty conservation.yaml
│   └── templates/
│       ├── claude_md.py                # MODIFIED — describe engine behaviour + config files
│       ├── universe_yaml.py            # NEW — universe.yaml template
│       └── conservation_yaml.py        # NEW — conservation.yaml template (empty by default)
├── mcp_server.py                       # MODIFIED — replace 3 stub tools with real implementations (plan 05-10)
├── cli.py                              # MODIFIED — add `engine-turn` command (D-29, plan 05-11)
└── operator/testing.py                 # UNCHANGED — EngineStub retained for tests

tests/
└── test_engine/                        # NEW
    ├── __init__.py
    ├── conftest.py                     # universe fixture, mock-haiku/mock-sonnet fixtures, seeded-rng fixture
    ├── test_models.py                  # Pydantic roundtrip + tagged-union discriminator
    ├── test_config.py                  # universe.yaml loader + defaults
    ├── test_classifier.py              # Classifier verdicts + malformed-output fallback
    ├── test_matcher.py                 # Scoring + ties + new matcher dispatch
    ├── test_decider.py                 # Precedence ladder + three refusal sources
    ├── test_refusal.py                 # RefusalTemplate + ctx.refuse
    ├── test_visibility.py              # Containment walk + illumination + beliefs
    ├── test_observer.py                # Grounding constraint + substring assertion
    ├── test_conservation.py            # Violation rollback + empty-config no-op
    ├── test_passive_sweep.py           # Decay/tick/world-property dispatch
    ├── test_tick_summary.py            # Schema-version-1 JSON write
    ├── test_engine.py                  # End-to-end run_tick (happy path + yield + refuse)
    ├── test_engine_integration.py      # Integration with real Haiku/Sonnet (@pytest.mark.integration)
    └── test_use_case_regression.py     # Run 35 UCs through real engine (@pytest.mark.integration)
```

### Pattern 1: Pydantic Tagged Union for `ClassifierVerdict` (D-05, D-06)

**What:** Discriminated union of four verdict types, each a dedicated Pydantic model.

**When to use:** Anywhere the code must reason about which kind of classifier output happened. Switch-case on `verdict.kind` is exhaustive and type-safe under mypy.

**Why:** Pydantic v2 generates an OpenAPI-compatible schema we include in the Haiku system prompt; the raw JSON response parses back into the same model. Ties the wire format, the type system, and the classifier prompt into a single source of truth.

```python
# src/token_world/engine/models.py
from __future__ import annotations

from typing import Any, Literal, Union
from pydantic import BaseModel, Field


class ClassifiedAction(BaseModel):
    """D-05: four structural fields for a classified action."""
    verb: str
    actor: str
    target: str | None = None
    indirect_object: str | None = None  # GAP-ENG02 closure
    params: dict[str, Any] = Field(default_factory=dict)


class VerdictOk(BaseModel):
    kind: Literal["ok"] = "ok"
    classified: ClassifiedAction
    confidence: float = Field(ge=0.0, le=1.0)


class VerdictNoViableAction(BaseModel):
    kind: Literal["no_viable_action"] = "no_viable_action"
    reason: str  # human-readable; e.g., "input is gibberish"


class VerdictNoSuchTarget(BaseModel):
    kind: Literal["no_such_target"] = "no_such_target"
    target_text: str  # the text the classifier tried to resolve


class VerdictLowConfidence(BaseModel):
    kind: Literal["low_confidence"] = "low_confidence"
    reason: str
    best_guess: ClassifiedAction | None = None
    confidence: float = Field(ge=0.0, le=1.0)


ClassifierVerdict = Union[  # type: ignore[valid-type]
    VerdictOk, VerdictNoViableAction, VerdictNoSuchTarget, VerdictLowConfidence
]
```

**Parse from Haiku:** `TypeAdapter(ClassifierVerdict).validate_json(raw_response_text)`. Ambiguity resolved by the `kind` discriminator field.

### Pattern 2: `MatchResult` Discriminated Union (D-11)

```python
# src/token_world/engine/models.py
from pydantic import BaseModel
from typing import Literal

class MatchedResult(BaseModel):
    kind: Literal["matched"] = "matched"
    mechanic_id: str
    score: int
    reasoning: str


class NoMatchResult(BaseModel):
    kind: Literal["no_match"] = "no_match"
    classified: ClassifiedAction
    candidates: list[str]  # top-K mechanic ids with score > 0 below threshold


MatchResult = Union[MatchedResult, NoMatchResult]  # type: ignore
```

### Pattern 3: Deterministic Matcher Scoring (D-09)

**Signature:** `score(mechanic: Mechanic, classified: ClassifiedAction, graph: KnowledgeGraph) -> int`.

**Formula:**
```python
score = 0
for matcher in mechanic.watches():
    if isinstance(matcher, VerbMatcher) and matcher.verb == classified.verb:
        score += 3
    # target type matcher (existing matcher primitive)
    if target_matches_mechanic_types(matcher, classified.target, graph):
        score += 2
    # actor type matcher
    if actor_matches_mechanic_types(matcher, classified.actor, graph):
        score += 1
return score
```

**Loop:**
```python
scored = [
    (mechanic.id, score(mechanic, classified, graph))
    for mechanic in registry.voluntary_mechanics()
]
scored.sort(key=lambda t: (-t[1], t[0]))  # descending score, ascending id
top = scored[0]
if top[1] == 0:
    candidates = [mid for mid, sc in scored[:5] if sc == 0]  # top-5 to help debugging
    return NoMatchResult(classified=classified, candidates=[])  # empty list — nothing scored
if top[1] > 0 and (len(scored) < 2 or scored[1][1] < top[1]):
    # clear winner
    return MatchedResult(mechanic_id=top[0], score=top[1], reasoning="clear winner")
# tie at top — alphabetical tie-breaker (already sorted)
return MatchedResult(mechanic_id=top[0], score=top[1], reasoning=f"tie-break vs {scored[1][0]}")
```

### Pattern 4: `VisibilityProjector` — Projected State Dict (D-14)

**Signature:** `VisibilityProjector(graph).project_for(actor_id: str) -> dict[str, dict]`.

**Algorithm (containment walk):**
1. Start with empty `projection: dict[str, dict] = {}`.
2. Seed with actor's own node.
3. Find actor's `location` edge → add the room node.
4. For the room node, add all nodes connected via `inside`, `on`, `contains` edges (containment walk, depth 1).
5. For the actor, add all nodes connected via `holds` edge.
6. For each added node, check illumination: if node is a room with `illumination` property, apply filter — if illumination < threshold AND actor holds no `light_source` entity, dim the room (exclude contained nodes' detailed properties).
7. Apply property visibility classes: for each node, filter out any property listed in node's `hidden_properties` (if the property exists).
8. Overlay belief dict: if `actor.beliefs[node_id]` exists, its properties override ground truth in the projection.
9. Return: `{ node_id: {"type": ..., "properties": {...}, "edges": [...]} for each projected node }`.

**No LLM.** Pure function over graph.

### Pattern 5: Conservation Checker with Snapshot Rollback (D-16)

**Config:** `universe/conservation.yaml`:
```yaml
# Empty = no enforcement
conserved_properties: []
# or:
conserved_properties: [coin, health]
```

**Algorithm:**
```python
class ConservationChecker:
    def __init__(self, conserved: list[str]):
        self._conserved = set(conserved)

    def verify(self, mutations: list[Mutation]) -> ConservationVerdict:
        if not self._conserved:
            return ConservationVerdict.ok()
        deltas: dict[str, int | float] = defaultdict(float)  # property -> sum of deltas
        for m in mutations:
            if m.event_type == "set_property" and m.property_name in self._conserved:
                old = m.old_value or 0
                new = m.new_value or 0
                deltas[m.property_name] += (new - old)
        violations = {p: d for p, d in deltas.items() if d != 0}
        if violations:
            return ConservationVerdict.violation(violations)
        return ConservationVerdict.ok()
```

**On violation:** Engine calls `GraphPersistence.restore_snapshot(pre_tick_snapshot_id)` (Phase 1 API), emits refusal narrative via `RefusalTemplate`, writes diagnostics `summary.json["outcome"] = "conservation_violated"`.

### Pattern 6: Seeded RNG on MechanicContext (D-19)

```python
# src/token_world/mechanic/context.py (modification)
import hashlib
import random
from typing import Any

class MechanicContext:
    def __init__(self, graph, actor, target, *, tick_id: str | None = None, universe_seed: int | None = None):
        # existing init …
        self._tick_id = tick_id
        self._universe_seed = universe_seed
        self._rng: random.Random | None = None

    @property
    def rng(self) -> random.Random:
        if self._rng is None:
            if self._tick_id is None or self._universe_seed is None:
                raise RuntimeError("ctx.rng requires tick_id + universe_seed on context creation")
            seed_bytes = hashlib.blake2b(
                f"{self._universe_seed}:{self._tick_id}".encode(), digest_size=8
            ).digest()
            self._rng = random.Random(int.from_bytes(seed_bytes, "big"))
        return self._rng
```

**AST rule (extends Phase 4 D-14):** `import random` in a mechanic module is a forbidden import. Mechanics use `ctx.rng`.

### Pattern 7: Tick Summary JSON (D-20, D-21)

**Filename:** `universe/tick_summaries/tick_<tick_id>.json`.

**Schema v1:**
```json
{
  "schema_version": 1,
  "tick_id": "tick_42",
  "timestamp_iso": "2026-04-13T12:34:56Z",
  "action_text": "pick up the rock",
  "classified_action": {"verb": "pickup", "actor": "alice", "target": "rock_1", "indirect_object": null, "params": {}},
  "matched_mechanic_id": "pickup",
  "yielded": false,
  "refused": false,
  "refusal_reason": null,
  "mutations": {
    "count": 2,
    "list": [["alice", "holds", null, "rock_1"], ["rock_1", "location", "room_1", null]]
  },
  "observation_text": "You bend down and lift the rock. It's cold in your hand.",
  "duration_ms": 1247,
  "llm_tokens_by_stage": {"classifier": {"in": 320, "out": 42}, "observer": {"in": 890, "out": 120}},
  "llm_cost_usd_by_stage": {"classifier": 0.0001, "observer": 0.0023}
}
```

**Write via Phase 4's `_atomic_write_json` helper** (or equivalent — atomic rename).

### Pattern 8: Engine Orchestrator (D-01)

```python
# src/token_world/engine/engine.py
from __future__ import annotations

class SimulationEngine:
    def __init__(self, universe_path: Path, *, anthropic_client: Anthropic | None = None):
        self._universe_path = universe_path
        self._config = load_engine_config(universe_path)
        self._graph = load_or_init_graph(universe_path)
        self._persistence = GraphPersistence(universe_path / "universe.db")
        self._registry = MechanicRegistry(universe_path / "mechanics")
        self._diagnostics = DiagnosticsSink(universe_path / "diagnostics")
        self._classifier = Classifier(anthropic_client or Anthropic())
        self._observer = Observer(anthropic_client or Anthropic())
        self._conservation = ConservationChecker.from_yaml(universe_path / "conservation.yaml")
        self._projector = VisibilityProjector(self._graph)

    def run_tick(self, action_text: str, actor: str) -> TickResult:
        tick_id = claim_tick_id(...)
        with self._diagnostics.open_tick(tick_id) as tick_ctx:
            self._registry.scan()  # D-02: idempotent w.r.t. registry
            pre_tick_snapshot = self._persistence.create_snapshot(f"pre-tick {tick_id}")

            # Stage 1: Classify
            verdict = self._classifier.classify(action_text, actor, tick_ctx=tick_ctx)

            # Stage 2+3: Decide (includes match)
            decision = decide(verdict, self._registry, self._graph, actor, tick_ctx=tick_ctx)

            # Stage 4: Execute (or yield/refuse)
            if isinstance(decision, ExecuteDecision):
                trace, mutations = self._execute(decision.mechanic, actor, tick_id, tick_ctx)
                # Conservation
                cons_verdict = self._conservation.verify(mutations)
                if cons_verdict.is_violation:
                    self._persistence.restore_snapshot(pre_tick_snapshot.id)
                    return TickResult.refused(
                        reason=RefusalTemplate.conservation_violation(cons_verdict),
                        tick_id=tick_id,
                    )
                # Passive sweep
                sweep_trace, sweep_mutations = run_passive_sweep(self._registry, self._graph, tick_id)
                # Observation
                projection = self._projector.project_for(actor)
                observation = self._observer.synthesize(projection, trace + sweep_trace, tick_ctx=tick_ctx)
                # Tick summary
                write_tick_summary(self._universe_path, tick_id, ...)
                return TickResult.ok(tick_id=tick_id, observation=observation, trace=trace, ...)
            elif isinstance(decision, YieldDecision):
                yield_signal = YieldSignal(
                    tick_id=tick_id,
                    universe_path=str(self._universe_path),
                    classified_action=verdict.classified.model_dump(),
                    action_text=action_text,
                    candidate_mechanic_ids=decision.candidates,
                    actor_state=self._projector.project_for(actor).get(actor, {}),
                )
                write_tick_summary(self._universe_path, tick_id, yielded=True, ...)
                return TickResult.yielded(tick_id=tick_id, signal=yield_signal)
            elif isinstance(decision, RefuseDecision):
                observation = RefusalTemplate.render(decision.reason_code, decision.details)
                write_tick_summary(self._universe_path, tick_id, refused=True, ...)
                return TickResult.refused(tick_id=tick_id, observation=observation)
```

### Pattern 9: Passive Sweep (D-17)

```python
def run_passive_sweep(registry, graph, tick_id, *, universe_seed):
    traces = []
    all_mutations = []
    sentinel = "_engine_tick_sentinel"
    kg = graph  # shorthand
    if not kg.has_node(sentinel):
        kg.add_node(sentinel, type="agent", _system=True)

    for mech in registry.involuntary_mechanics():
        matchers = mech.watches()
        if not any(isinstance(m, (TickMatcher, DecayMatcher, WorldPropertyMatcher)) for m in matchers):
            continue
        ctx = MechanicContext(
            graph, actor=sentinel, target=sentinel, tick_id=tick_id, universe_seed=universe_seed
        )
        check = mech.check(ctx)
        if not check.passed:
            continue
        mutations = mech.apply(ctx)
        for m in mutations:
            graph.apply_mutation(m)  # canonical mutation dispatch
        all_mutations.extend(mutations)
        traces.append(SweepTraceEntry(mechanic_id=mech.id, mutations=mutations))
    return traces, all_mutations
```

### Pattern 10: `engine-turn` CLI Command (D-29)

```python
# src/token_world/cli.py (addition)
@cli.command("engine-turn")
@click.argument("universe_slug")
@click.argument("actor")
@click.argument("action_text")
@click.option("--format", type=click.Choice(["human", "json"]), default="human")
def engine_turn_cmd(universe_slug: str, actor: str, action_text: str, format: str):
    """Run one engine tick against a universe."""
    universe_path = UniverseManager().path_for(universe_slug)
    engine = SimulationEngine(universe_path)
    result = engine.run_tick(action_text, actor)
    if format == "json":
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        click.echo(result.render_human())
```

## Pitfalls

| # | Pitfall | Mitigation |
|---|---------|-----------|
| 1 | **Pydantic parsing strictness rejects minor Haiku deviations.** Haiku might produce `{"kind":"ok","classified":{...},"confidence":0.95}` with an unexpected extra field. | Use `model_config = ConfigDict(extra="ignore")` on all verdict models. Ignore unknown fields rather than fail; plan 05-01 explicitly tests this. |
| 2 | **`ctx.rng` determinism broken by `random.Random` instance state leaking between ticks.** If the same MechanicContext is reused, RNG state persists. | Construct a fresh `MechanicContext` per tick (which we do already); `_rng` is a private attribute, not a class-level. |
| 3 | **Snapshot rollback during conservation violation also rolls back authoring session state.** If the operator was in the middle of a yield flow when we violated conservation... | Conservation runs ONLY inside a matched-mechanic tick; yielded ticks never execute mechanics, so never reach conservation. Snapshot rollback applies only to graph state, not diagnostics or operator session. |
| 4 | **`import random` AST rule false-positives on `import random_library_with_prefix`.** | AST walker checks `node.names[0].name == "random"` (exact match), not prefix. Stdlib import only. |
| 5 | **Haiku classifier confidence self-report is meaningless if we don't calibrate.** The model can say `0.99` for garbage. | D-07 threshold is `0.6` with opt-in raising. Plan 05-01 ships one calibration test (feed 10 nonsense inputs, check ≥8 return `no_viable_action` OR `low_confidence`). |
| 6 | **Observer hallucination slips past substring grounding check.** "The room is dimly lit" might pass "dim" substring even if the graph never mentioned dimming. | Phase 5's substring check is DEMONSTRABLY weak — it catches obvious hallucinations only. Full rubric testing is Phase 6 (TEST-04). Plan 05-05 explicitly documents this limitation. |
| 7 | **VisibilityProjector performance at scale.** Containment walk is O(nodes_in_room) — typically small, but a giant warehouse could be slow. | Hobby scale — not a concern. Documented in 05-04. |
| 8 | **Passive sweep runs on yielded ticks, clashing with operator flow.** If the engine yields, should passive sweep run? | No — D-17 says "after the action's chain completes." A yielded tick has no chain, so no sweep. Plan 05-08 explicitly sequences this. |
| 9 | **`_engine_tick_sentinel` accumulates properties over time.** Passive mechanics might set properties on it. | `_engine_tick_sentinel` node should be treated as ephemeral: engine clears non-system properties on it before passive sweep each tick. Plan 05-07 handles. |
| 10 | **Universe seed scaffold collision.** If universe scaffold runs twice, creating two `universe_seed` values, determinism breaks. | Scaffolding only creates `universe.yaml` if it doesn't exist; existing seeds are never overwritten. Plan 05-01 test covers. |
| 11 | **Pre-tick snapshot accumulates.** Phase 1 retains max 50 snapshots; heavy tick rate could evict pre-tick snapshots before rollback. | Phase 1 retention is FIFO; pre-tick snapshots are always the latest, so retained. Worst case: rollback-to-yielded-pre-tick-snapshot is impossible if 50 ticks have elapsed — acceptable hobby-scale tradeoff. |
| 12 | **`universe.yaml` parse failures crash the engine at startup.** | `EngineConfig.from_path(universe_path)` with defensive defaults: if `universe.yaml` missing or malformed, use built-in defaults + warn to stderr. Plan 05-01 tests each failure path. |
| 13 | **Classifier receives a tick_id from a previous yielded tick, producing stale diagnostics.** | Tick IDs are claimed by the engine per-call; every `run_tick` claims a fresh one (incremented). Resume after yield uses the SAME tick_id (that's the whole point of resume). Plan 05-08 explicitly handles both paths. |
| 14 | **Sonnet observer refuses to synthesize when projection is empty (dark room, no vision).** | Degenerate case: projection returns actor-only. Observer prompt MUST handle — include fallback "you see nothing but darkness" style phrasing. Plan 05-05. |
| 15 | **Belief overlay for a non-existent node creates a phantom entry in projection.** `actor.beliefs["ghost_id"] = {...}` might leak into observation as if ghost_id exists. | Projection only overlays beliefs for nodes already in the projection (containment walk came first). Orphan beliefs are silently ignored. Plan 05-04 test. |
| 16 | **Registry auto-scan on every `run_tick` is slow.** | Phase 4 registry uses import caching. Re-scans typically cost < 50ms. If this becomes a hotspot, optimize later. Documented in 05-08. |

## Validation Architecture

Every Phase 5 plan produces testable artifacts. Validation strategy:

**Per-plan (unit scope):**
- Each `token_world/engine/*.py` module has a dedicated `tests/test_engine/test_*.py` mirror.
- Pure functions (matcher scoring, visibility projection, conservation verification, tick summary) tested without LLM mocking.
- LLM wrappers (classifier, observer) tested with a `MockAnthropic` fixture that returns canned responses; diagnostics sink uses real tmp dir.

**Per-wave (integration scope):**
- Wave 1 plans each ship 5–10 unit tests.
- Wave 2 engine orchestrator (05-08) has integration tests that wire stages end-to-end using mocked LLMs — covers classify+match+execute+observe, classify+no-match→yield, classify-refuse paths.

**Phase-level (end-to-end):**
- Plan 05-09 runs Phase 4.1's existing `EngineStub` integration test through the real engine; should pass with `yield_signal` byte-identical to what the stub fabricated.
- Plan 05-12 runs all 35 Phase 3 use cases through the real engine via `tests/test_engine/test_use_case_regression.py`; expected outcomes per UC (pass / yield / blocked-by-framework-gap) are declared in the UC manifests.
- Two real-LLM integration tests marked `@pytest.mark.integration`, excluded from `pytest -q`.
- `uv run ruff check src/` + `uv run mypy src/token_world/engine/` + `uv run pytest tests/test_engine -q` — ALL required to pass per plan.

**Verification inputs for 05-12 retrospective:**
- All 19 GAP-HANDOFF Phase-5 gaps marked CLOSED with specific plan reference.
- All 9 Phase-5 requirements verified against success criteria.
- `docs/design/architecture.md` updated with pipeline diagram (Mermaid).
- STATE.md updated via tool.
- VALIDATION.md finalized.

---

## RESEARCH COMPLETE

All CONTEXT.md decisions have stdlib/in-tree implementations. No new dependencies required. File layout, patterns, and pitfalls documented. Planner can proceed to create 12 plans across 3 waves.
