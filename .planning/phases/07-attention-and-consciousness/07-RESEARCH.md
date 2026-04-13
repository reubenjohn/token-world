---
phase: 07-attention-and-consciousness
researched: 2026-04-13
domain: Composable interruption threshold pattern — long-running actions, attention-modulated projection, engine hook
confidence: HIGH
requirements: SIM-09, SIM-10
---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (23 total — all must be honoured, no alternatives)

- **D-01** — All consciousness states are long-running actions with thresholds. No separate SleepState/DrunkState classes.
- **D-02** — State stored as `current_long_action` JSON dict on actor graph node via `kg.set()`.
- **D-03** — Thresholds are dicts: `{"property": "<node_id>.<prop_name>", "op": "<operator>", "value": <val>}`. Operators: `>`, `>=`, `<`, `<=`, `==`, `!=`. No lambda, no DSL.
- **D-04** — Single active long-running action per agent (v1). No concurrent actions.
- **D-05** — Mechanics return `LongRunningAction` alongside normal `Mutation` list. Not a new Mechanic subclass.
- **D-06** — Tick hook runs after primary execute, before passive sweep.
- **D-07** — Engine generates synthetic `continue_long_action` when long-running action is active; no resident agent call.
- **D-08** — Thresholds evaluated every tick (no batching).
- **D-09** — Thresholds evaluated against `VisibilityProjector.project_for(actor)` output. Dot-notation: `"node_id.prop_name"`. Missing = False (no fire).
- **D-10** — Interruption observation via existing `Observer.synthesize()` with interruption context dict in trace.
- **D-11** — New agent action clears `current_long_action` implicitly (detected in `run_tick`).
- **D-12** — Attention state: `attention_state: dict | None` added to `project_for(actor_id, attention_state=None)`. `{"suppress": [...], "boost": [...]}`. Stage 5 of projector.
- **D-13** — `turns_total: None` = indefinite; `turns_total: int` = bounded. `turns_elapsed` always advances.
- **D-14** — Testing: unit (pure), integration (FakeClassifier+FakeObserver), demonstration (live LLM, `@pytest.mark.integration`).
- **D-15** — New modules: `engine/long_running.py`, `engine/long_running_hook.py`. Extended: `engine/visibility.py`, `engine/engine.py`. Tests: `tests/test_engine/test_long_running.py`.
- **D-16** — `turns_total: None` = indefinite. Never auto-expires. `turns_elapsed` still advances.
- **D-17** — Tick summary extended with optional `long_running_action` object. `schema_version` stays 1 (additive).
- **D-18** — Three seed mechanics: `sleep` (bounded, noise/health thresholds), `autopilot_travel` (bounded, hazard thresholds), `drunk` (indefinite, sobriety threshold).
- **D-19** — `ThresholdSpec` field names: `property`, `op`, `value` (exact).
- **D-20** — `LongRunningHook` may be class or module functions; lives in `long_running_hook.py`.
- **D-21** — Interruption prompt phrasing is flexible; context dict shape is locked.
- **D-22** — "Time passes" observation: static template or Haiku. Recommended: static template.
- **D-23** — `LongRunningAction` and `ThresholdSpec` are frozen dataclasses (not Pydantic models).

### Claude's Discretion
- D-19: exact field aliases inside `ThresholdSpec` (field names property/op/value are locked; internal aliases flexible)
- D-20: class vs module functions for `LongRunningHook`
- D-21: exact interruption prompt phrasing
- D-22: static template vs Haiku for "time passes" observation
- D-23: frozen dataclass vs Pydantic (frozen dataclass recommended)

### Deferred Ideas (OUT OF SCOPE)
- Per-N-tick threshold evaluation
- Concurrent long-running actions per agent
- LLM-generated adversarial scenarios
- Calendar/season derivation (GAP-ENG10)
- Multi-agent long-running action conflicts (MULTI-01..03)
- Personality evolution during long-running states
- Stochastic threshold evaluation (ctx.rng is supported, but no v1 seed mechanic uses it)
- `turns_elapsed` visibility in agent observation
- `agent_id` field in BatchSummary (deferred from Phase 6)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SIM-09 | Action duration and attention threshold — long-running actions skip boring intermediate turns; engine only interrupts when significance exceeds agent's current attention level | LongRunningAction + ThresholdEvaluator + engine tick hook cover this entirely |
| SIM-10 | Attention/consciousness as a reusable mechanic pattern — sleep, daydreaming, drunkenness, autopilot all use the same interruption threshold infrastructure | D-01 composability + three seed mechanics (D-18) demonstrate pattern |
</phase_requirements>

---

## Summary

Phase 7 is a pure-Python, graph-mediated extension to the existing engine pipeline. All 23 decisions are locked; there are no technology choices to make — only correct implementation of what CONTEXT describes. The research task is to nail the exact integration points, data shapes, and edge cases so the planner can write wave-level tasks with zero ambiguity.

The three core technical concerns are: (1) the `LongRunningAction` dataclass shape and JSON-serialization contract, (2) the `ChainExecutionEngine`/`SimulationEngine` apply() return-value inspection pattern for planting the action on the actor node, and (3) the exact insertion point in `_handle_execute()` for the `LongRunningHook`. Everything else (threshold evaluation, attention modulation, seed mechanics) follows naturally from those three anchors.

**Primary recommendation:** Implement in strict dependency order — `long_running.py` (pure dataclasses + evaluator) → `long_running_hook.py` (hook using those) → `visibility.py` extension (attention stage) → `engine.py` integration (hook call + synthetic action routing) → seed mechanics → tests.

---

## Standard Stack

Phase 7 introduces NO new external dependencies. All work uses the existing stack.

[VERIFIED: codebase grep — no new imports beyond stdlib and project modules]

| Module | Version | Purpose | Status |
|--------|---------|---------|--------|
| Python stdlib `dataclasses` | 3.12+ | `LongRunningAction`, `ThresholdSpec` frozen dataclasses | Already used (YieldSignal, Mutation, SnapshotInfo all use it) |
| `token_world.graph.KnowledgeGraph` | in-tree | `kg.set(actor_id, "current_long_action", dict)` storage | Already used |
| `token_world.engine.visibility.VisibilityProjector` | in-tree | Extended with `attention_state` param | Extended (not replaced) |
| `token_world.engine.observer.Observer` | in-tree | Reused for interruption observation (D-10) | Unchanged API |
| `token_world.mechanic.context.MechanicContext` | in-tree | Extended with `begin_long_action()` helper | Extended |
| `pytest` | in-tree | Unit + integration tests (D-14) | Already used |

---

## Architecture Patterns

### Recommended Module Layout (D-15)

```
src/token_world/engine/
├── long_running.py          # NEW: LongRunningAction, ThresholdSpec, ThresholdEvaluator
├── long_running_hook.py     # NEW: LongRunningHook (reads graph, evaluates, writes)
├── visibility.py            # EXTENDED: project_for(actor_id, attention_state=None)
└── engine.py                # EXTENDED: _handle_execute() hook call; synthetic action routing
tests/test_engine/
└── test_long_running.py     # NEW: unit + integration tests
```

### Pattern 1: LongRunningAction Dataclass Schema

The `current_long_action` graph property is a plain Python `dict` when stored in the graph (JSON-serializable), and a frozen dataclass when in-memory.

**Stored dict schema (D-02, D-03, D-13, D-16, D-19):**
```python
{
    "action_text": str,           # human-readable label ("sleeping", "traveling to market")
    "turns_total": int | None,    # None = indefinite (D-16)
    "turns_elapsed": int,         # always advances (D-13)
    "thresholds": [               # list of ThresholdSpec dicts (D-03)
        {"property": "bedroom.noise_level", "op": ">", "value": 0.7},
        {"property": "alice.health", "op": "<", "value": 0.2},
    ],
    "payload": {                  # mechanic-specific extras
        "attention_state": {      # optional (D-12): modulates projection
            "suppress": ["visual_detail", "smell"],
            "boost": ["noise_level"],
        }
    }
}
```

**In-memory dataclasses (D-23 frozen dataclass, D-15 lives in `long_running.py`):**
```python
# Source: CONTEXT.md D-03, D-23 + YieldSignal frozen dataclass pattern
@dataclass(frozen=True, slots=True)
class ThresholdSpec:
    property: str   # "node_id.prop_name" dot notation (D-09)
    op: str         # one of: ">", ">=", "<", "<=", "==", "!=" (D-03)
    value: Any      # threshold value — must be JSON-serializable

@dataclass(frozen=True, slots=True)
class LongRunningAction:
    action_text: str
    turns_total: int | None     # None = indefinite (D-16)
    turns_elapsed: int          # mutable per tick — planner must NOTE: frozen dataclass
                                # means turns_elapsed increments via graph.set(), not
                                # in-memory mutation; the stored dict is updated each tick
    thresholds: tuple[ThresholdSpec, ...]  # tuple (frozen-safe, JSON converts to list)
    payload: dict               # attention_state lives here (D-12)
```

**CRITICAL SERIALIZATION DETAIL:** [VERIFIED: knowledge_graph.py `_validate_value()`]
`tuple` is NOT in `ALLOWED_PROPERTY_TYPES`. The in-memory `LongRunningAction.thresholds` must be `tuple` for frozenness, but when writing to the graph it must be serialized as `list[dict]`. The `LongRunningHook` and `ctx.begin_long_action()` must convert to dict before `kg.set()`.

**ALLOWED_PROPERTY_TYPES** (from `src/token_world/graph/models.py`):
```python
ALLOWED_PROPERTY_TYPES = (str, int, float, bool, type(None), list, dict)
# tuple is NOT allowed — must serialize thresholds as list[dict]
```

### Pattern 2: Mechanic apply() Return Value — LongRunningAction Alongside Mutations

[VERIFIED: mechanic/protocol.py + mechanic/engine.py]

Current `apply()` signature: `def apply(self, ctx: MechanicContext) -> list[Mutation]`

D-05 says mechanics that start long-running actions return a `LongRunningAction` "alongside" mutations. The cleanest approach given the existing codebase:

**Option A (recommended): `apply()` returns `list[Mutation | LongRunningAction]`** — the engine (in `_handle_execute()`) inspects elements: `Mutation` instances go to the conservation checker, `LongRunningAction` instances are written to the actor node via `kg.set()`. No protocol change on non-LRA mechanics (they return `list[Mutation]` which is already a valid `list[Mutation | LongRunningAction]` since it's a subtype).

**Option B: separate tuple** `-> tuple[list[Mutation], LongRunningAction | None]` — cleaner type but breaks the existing protocol ABC signature and requires every caller (`ChainExecutionEngine.execute()`, `_run_passive_sweep()`) to unpack.

**Planner should choose Option A** because:
- `ChainExecutionEngine.execute()` at line 61 calls `mutations = mechanic.apply(ctx)` and then passes `mutations` directly. With Option A, the engine inspects the return value before passing to the chain engine — no change to `ChainExecutionEngine`.
- The `_handle_execute()` method is the right inspection point: it already calls `chain_engine.execute(mechanic, ctx)` and receives an `ExecutionTrace`. The `LongRunningAction` can be extracted from the trace's mutations list before conservation checking.
- Alternatively: `begin_long_action()` on `MechanicContext` writes to the graph directly (the convenience helper D-15 describes). Then `apply()` still returns `list[Mutation]` and the `LongRunningAction` is in the graph already. This is actually cleanest.

**RECOMMENDED APPROACH (D-15 helper):** `ctx.begin_long_action(...)` writes `current_long_action` directly to the actor node and returns a `LongRunningAction` dataclass (for the hook to inspect from graph). The `apply()` method still returns `list[Mutation]` (the `begin_long_action` call returns the mutation for the graph property set, which is included in the list). The engine does not need to inspect return types at all — it just checks the actor node for `current_long_action` after execution.

```python
# Source: CONTEXT.md D-15 + MechanicContext pattern (context.py)
# In MechanicContext (context.py extension):
def begin_long_action(
    self,
    action_text: str,
    turns_total: int | None,
    thresholds: list[dict],      # already-serialized ThresholdSpec dicts
    attention_state: dict | None = None,
) -> Mutation:
    """Write current_long_action to the actor graph node. Returns the Mutation."""
    from token_world.engine.long_running import LongRunningAction  # avoid circular
    payload: dict = {}
    if attention_state is not None:
        payload["attention_state"] = attention_state
    action_dict = {
        "action_text": action_text,
        "turns_total": turns_total,
        "turns_elapsed": 0,
        "thresholds": thresholds,
        "payload": payload,
    }
    return self._graph.set(self.actor, "current_long_action", action_dict)
```

### Pattern 3: Engine Tick Hook — Exact Insertion Point

[VERIFIED: engine.py lines 444-535 — `_handle_execute()` flow]

Current execute path in `_handle_execute()`:
1. `chain_engine.execute(mechanic, ctx)` → `primary_trace`
2. Conservation check on `primary_mutations`
3. `_run_passive_sweep()` → `sweep_trace_nodes`
4. Conservation check on `all_mutations` (primary + sweep)
5. `_projector.project_for(actor)` → `projection`
6. `Observer.synthesize()` → `observation`
7. `_write_summary()` + return `TickResult.ok()`

**D-06 insertion point: between step 2 (conservation) and step 3 (passive sweep).**

Concretely, after `cons_verdict = self._conservation.verify(primary_mutations)` passes, before `self._run_passive_sweep(...)`:

```python
# After conservation check passes, before passive sweep:
hook_result = self._long_running_hook.process(
    actor=actor,
    tick_id_str=tick_id_str,
    projection=self._projector.project_for(actor, attention_state=self._get_attention_state(actor)),
)
if hook_result.interrupted:
    # Generate interruption observation and return TickResult
    ...
elif hook_result.active_and_continuing:
    # Suppress normal observation; return compressed "time passes" TickResult
    ...
# else: no long-running action — continue to passive sweep normally
```

**Why this placement is correct:**
- The primary mechanic has already executed and mutated the graph (e.g., sleep mechanics regenerates energy). The hook sees post-mutation state. [ASSUMED based on D-06 rationale]
- Conservation is verified first — if the LRA mechanic itself violates conservation, we refuse before the hook even runs.
- The passive sweep runs after the hook so that passive mechanics (decay, weather) still fire even during long-running actions — this is intentional per D-17 (world still changes while agent sleeps).

**PITFALL: Do not call `project_for()` twice.** The engine already calls it at step 5 for the observer. The hook must call it with `attention_state` (which may differ from the un-modulated projection for the observer). Store the hook's projection if needed for the observer, or call once with attention_state and pass to both hook and observer.

### Pattern 4: Synthetic Action Routing (D-07)

When `current_long_action` is set on the actor node, `run_tick` must detect this BEFORE the classifier and short-circuit to a built-in `LongRunningTickMechanic`.

**Detection point:** At the very top of `run_tick()`, after registry scan, before classification:

```python
# In run_tick() preamble (BEFORE Stage 1 Classify):
existing_lra = self._graph.query(actor, "current_long_action")
if existing_lra is not None:
    # Synthetic action: route to LongRunningTickMechanic, skip classify/match/decide
    return self._handle_long_running_tick(
        actor=actor,
        lra_dict=existing_lra,
        tick_id_str=tick_id_str,
        ...
    )
```

**Alternative: detect in `_handle_execute()` after mechanic fires** — but this means the classifier and matcher still run on the synthetic action, which is wasteful. Top-of-`run_tick` detection is cheaper and cleaner.

**D-11 cancellation:** If `action_text` is not the synthetic `"continue_long_action"` but a real agent action text, the engine clears `current_long_action` and processes normally. Detection: if `existing_lra is not None` AND `action_text` is NOT the internal synthetic token, clear the LRA first.

**Design tension:** D-07 says "PlaytestRunner passes this synthetic action transparently." This means the PlaytestRunner will call `engine.run_tick("continue_long_action", actor)` for long-running ticks, or the engine itself generates the synthetic action internally. The CONTEXT says the engine generates the synthetic action internally — the runner just calls `run_tick(None, actor)` or the runner is unaware. **Planner must decide:** either the runner is modified to pass `None` and the engine detects `current_long_action` at top of `run_tick`, or the engine exposes a `resume_long_action(actor)` method. The former (check in `run_tick`) is simpler and matches D-07 "no change to runner loop." The engine should accept `action_text=None` or `action_text=""` as a signal to check for active LRA.

### Pattern 5: VisibilityProjector Attention Stage (D-12)

Current `project_for(actor_id: str) -> dict`:
```python
# Source: visibility.py lines 41-81
def project_for(self, actor_id: str) -> dict[str, dict[str, Any]]:
    ...
    # Stage 1: containment walk
    # Stage 2: illumination filter
    # Stage 3: property visibility
    # Stage 4: belief overlay
```

Extension — backward-compatible signature change:
```python
def project_for(
    self,
    actor_id: str,
    attention_state: dict | None = None,  # NEW (D-12)
) -> dict[str, dict[str, Any]]:
    ...
    # Stage 5: attention modulation (NEW)
    if attention_state:
        projection = self._apply_attention_state(projection, attention_state)
    return projection
```

`_apply_attention_state` implementation:
```python
def _apply_attention_state(
    self, projection: dict, attention_state: dict
) -> dict:
    """Stage 5: suppress/boost properties based on attention_state (D-12)."""
    suppress = set(attention_state.get("suppress", []))
    boost = set(attention_state.get("boost", []))
    new_projection = {}
    for node_id, entry in projection.items():
        props = dict(entry.get("properties", {}))
        # Suppress: remove property from projection
        for prop in suppress:
            props.pop(prop, None)
        # Boost: copy boosted properties to top-level "boosted" key for Observer prominence
        boosted = {p: props[p] for p in boost if p in props}
        new_entry = dict(entry)
        new_entry["properties"] = props
        if boosted:
            new_entry["attention_boosted"] = boosted
        new_projection[node_id] = new_entry
    return new_projection
```

**All existing callers** of `project_for(actor)` continue to work unchanged (new param has default `None`). [VERIFIED: grep found 3 call sites in engine.py — all pass only `actor_id`]

### Pattern 6: ThresholdEvaluator — Pure Function

```python
# Source: CONTEXT.md D-03, D-09 + projection dict structure (visibility.py)
class ThresholdEvaluator:
    """Pure function: evaluate all thresholds against a projection dict."""

    _OPS = {
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }

    @classmethod
    def evaluate(
        cls,
        thresholds: list[dict],
        projection: dict,
    ) -> ThresholdSpec | None:
        """Return the first firing ThresholdSpec, or None if none fire.

        Property path format: "<node_id>.<prop_name>" (D-03, D-09).
        Missing node/property returns False (D-09 safe default).
        """
        for spec_dict in thresholds:
            spec = ThresholdSpec(**spec_dict)
            if cls._evaluate_one(spec, projection):
                return spec
        return None

    @classmethod
    def _evaluate_one(cls, spec: ThresholdSpec, projection: dict) -> bool:
        node_id, _, prop_name = spec.property.partition(".")
        node_entry = projection.get(node_id)
        if node_entry is None:
            return False  # safe default: missing node does not fire
        actual = node_entry.get("properties", {}).get(prop_name)
        if actual is None:
            return False  # safe default: missing property does not fire
        op_fn = cls._OPS.get(spec.op)
        if op_fn is None:
            return False  # unknown op: safe default
        try:
            return bool(op_fn(actual, spec.value))
        except TypeError:
            return False  # incompatible types: safe default
```

**Projection dict structure** (verified from visibility.py):
```
{
  "bedroom": {
    "type": "entity",
    "properties": {"noise_level": 0.3, "illumination": 0.8},
    "edges": [...]
  },
  "alice": {
    "type": "agent",
    "properties": {"health": 0.9, "energy": 0.4},
    "edges": [...]
  }
}
```
So `"bedroom.noise_level"` resolves to `projection["bedroom"]["properties"]["noise_level"]`.

### Pattern 7: HookResult and LongRunningHook

```python
# Source: CONTEXT.md D-06, D-20 integration point
@dataclass(frozen=True, slots=True)
class HookResult:
    active: bool                     # was a long-running action running?
    interrupted: bool                # did a threshold fire?
    completed: bool                  # did turns_elapsed reach turns_total?
    continuing: bool                 # action still running, no interruption
    fired_threshold: ThresholdSpec | None  # which threshold fired (if any)
    trigger_value: Any               # actual value that triggered it
    observation: str | None          # "time passes" or interruption narrative
    long_running_action: dict | None # current LRA dict at time of evaluation
```

`LongRunningHook.process(actor, projection, graph, tick_id, observer) -> HookResult`:
1. Read `current_long_action` from graph (None → return `HookResult(active=False, ...)`).
2. Advance `turns_elapsed` by 1 via `graph.set(actor, "current_long_action", updated_dict)`.
3. Evaluate thresholds via `ThresholdEvaluator.evaluate(thresholds, projection)`.
4. If threshold fires: clear `current_long_action`, generate interruption observation → `HookResult(interrupted=True, ...)`.
5. If `turns_total is not None` and `turns_elapsed >= turns_total`: clear, generate completion observation → `HookResult(completed=True, ...)`.
6. Else: return `HookResult(continuing=True, observation="Time passes...")`.

### Pattern 8: Tick Summary Extension (D-17)

```python
# Added to TickSummary model (models.py) as optional field:
long_running_action: dict | None = None
# Content when active:
# {
#   "active": True,
#   "turns_elapsed": 3,
#   "turns_total": 8,
#   "threshold_fired": {"property": "bedroom.noise_level", "op": ">", "value": 0.7} | None,
#   "interrupted": True | False,
# }
```

`schema_version` stays `1` per D-17 (additive field, backward-compatible).

### Pattern 9: Seed Mechanic Structure

[VERIFIED: mechanic/protocol.py `Mechanic` ABC; mechanic/matchers.py `VerbMatcher`]

All three seed mechanics live in the universe's `mechanics/` folder (not in the engine package — they are world mechanics, not engine code). They use `ctx.begin_long_action()` and return standard `list[Mutation]`.

**Sleep mechanic scaffold:**
```python
class Sleep(Mechanic):
    id = "sleep"
    description = "Agent goes to sleep; interrupted by loud noise or health crisis"
    voluntary = True
    tags = ["rest", "long_running"]

    def watches(self):
        return [VerbMatcher(verb="sleep")]

    def check(self, ctx):
        # Precondition: not already in a long-running action
        lra = ctx.query_node(ctx.actor, "current_long_action")
        if lra is not None:
            return ctx.refuse("mechanic_check_failed", {"reason": "already in long action"})
        return CheckResult(passed=True)

    def apply(self, ctx) -> list[Mutation]:
        mutations = []
        # Optional: set initial state (e.g., mark as sleeping)
        mutations.append(ctx.set(ctx.actor, "is_sleeping", True))
        # Begin the long-running action
        mutations.append(ctx.begin_long_action(
            action_text="sleeping",
            turns_total=8,
            thresholds=[
                {"property": f"{ctx.actor}.location_noise_level", "op": ">", "value": 0.7},
                {"property": f"{ctx.actor}.health", "op": "<", "value": 0.2},
            ],
            attention_state={
                "suppress": ["visual_detail", "smell"],
                "boost": ["noise_level"],
            },
        ))
        return mutations
```

**Note on threshold property path:** The thresholds reference projected state. `ctx.actor` is the actor node_id. Location noise level would be on the room node. The room node_id must be known at mechanic-write time OR the threshold can reference a property that the sleep mechanic copies to the actor node (e.g., `actor.nearby_noise`). This is a design choice the planner must resolve: either thresholds use static node_ids (e.g., "bedroom") or mechanics pre-write a denormalized property to the actor. The simpler v1 approach: thresholds reference the location room by its node_id. **If the actor moves rooms, the threshold references a node that may not be in the projection.** Projection only covers `location`, `contained`, and `held` nodes — so a threshold like `"bedroom.noise_level"` works only if the actor is currently in `bedroom`. For v1, this is acceptable.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Threshold expression safety | Python `eval()` or `exec()` for threshold predicates | Declarative dict with enum ops (D-03) | Security risk, not serializable |
| Observation synthesis for interruption | Hardcoded string templates | `Observer.synthesize()` with interruption context (D-10) | Grounding constraint (Phase 5 D-15) requires Observer |
| RNG for stochastic thresholds | `random.random()` | `ctx.rng` (Phase 5 D-19) | Determinism requirement |
| Long-running action storage | Separate SQLite table | `kg.set(actor, "current_long_action", dict)` (D-02) | "If not in graph, doesn't exist" |
| Attention state as separate node type | New graph node for consciousness state | `payload.attention_state` dict on `LongRunningAction` (D-12) | Two-node-types constraint |

---

## Common Pitfalls

### Pitfall 1: First-Tick Insta-Cancel
**What goes wrong:** A threshold fires on the same tick the action starts (e.g., `sleep` starts with room noise already at 0.8, which exceeds the 0.7 threshold).
**Why it happens:** The hook evaluates thresholds against the current projected state, which reflects the room state at the tick of sleep initiation.
**How to avoid:** The hook MUST NOT evaluate thresholds when `turns_elapsed == 0` (i.e., the tick the action started). Advance `turns_elapsed` first (1), then evaluate. Sleep starts at `turns_elapsed = 0`; first threshold evaluation is when `turns_elapsed = 1` after advancing.
**Warning signs:** Unit test where a loud room is initialized BEFORE sleep starts → expect continuation on tick 1, not interruption.

### Pitfall 2: Observation Flood During Long-Running Ticks
**What goes wrong:** 100-tick autopilot travel produces 100 `TickResult.ok()` observations, flooding the agent's context with "time passes..." messages.
**Why it happens:** Each tick produces a tick summary and an observation.
**How to avoid:** The "time passes" observation should be either a static template string ("You continue traveling...") or a Haiku-generated minimal summary. The BatchCompressor (Phase 6) will compress these ticks into a batch summary — so the agent context impact is bounded by batch size, not tick count. The observation per-tick is still written to diagnostics and tick summaries; only the agent's rolling window matters.
**Warning signs:** Agent context accumulates identical "time passes" strings over many ticks.

### Pitfall 3: State Stranding on Actor Node Removal
**What goes wrong:** An actor node is removed from the graph while `current_long_action` is set on it. The property disappears with the node — no cleanup needed. But if the engine has a reference to the actor_id and calls `project_for(actor_id)`, it gets `{}` (actor doesn't exist). The hook should handle this gracefully.
**Why it happens:** `kg.remove_node(actor_id)` removes all properties including `current_long_action`.
**How to avoid:** `LongRunningHook.process()` should call `graph.has_node(actor)` before reading `current_long_action`. If actor is gone, return `HookResult(active=False)`. The engine already has the `pre_tick_snapshot_id` and can rollback if needed.

### Pitfall 4: Projection Mismatch Between Hook and Observer
**What goes wrong:** The hook calls `project_for(actor, attention_state=some_state)` and gets a suppressed/boosted projection. The observer then calls `project_for(actor)` (no attention_state) and sees the full un-modulated projection. The observer's observation may mention properties the "sleeping" agent shouldn't perceive (e.g., visual_detail suppressed for sleeping).
**Why it happens:** Two separate `project_for()` calls with different signatures.
**How to avoid:** The observer call during long-running ticks must ALSO pass `attention_state`. The hook's `HookResult` can carry the attention_state for the engine to pass to the observer. Or: the engine reads `attention_state` from the actor's `current_long_action.payload` and passes it to both hook and observer calls.

### Pitfall 5: Cancellation Path Order
**What goes wrong:** Agent issues a new action while sleeping. Engine runs the classifier on the new action text, then detects `current_long_action` in the hook, and clears it. But the classified action has already been processed.
**Why it happens:** If cancellation is detected post-classification (in the hook) rather than pre-classification (top of `run_tick`).
**How to avoid:** D-11 says "engine clears `current_long_action` and processes the new action normally." The detection and clearing must happen at the TOP of `run_tick`, before the classifier runs. Implementation:
1. Top of `run_tick`: check if `current_long_action` is set.
2. If set AND `action_text` is a real user action (not the synthetic token): clear LRA, log cancellation, proceed with normal pipeline.
3. If set AND `action_text` is None/synthetic: run the synthetic long-action tick.
**Warning signs:** A test where sleep is followed by a real action — both the sleep continuation AND the new action fire in the same tick.

### Pitfall 6: Passive Mechanics Causing Threshold Fire — Whose Turn?
**What goes wrong:** A passive sweep mechanic (e.g., `noise_decay`) runs AFTER the hook, reducing noise level. But a different passive mechanic (e.g., `crowd_event`) runs BEFORE the hook (if order is wrong) and raises noise level, causing the sleep threshold to fire. The wake-up is attributed to the current actor's tick.
**Why it happens:** The hook runs between primary execute and passive sweep (D-06). Passive mechanics that fire AFTER the hook don't affect threshold evaluation for THIS tick — they affect the NEXT tick's evaluation. This is correct and intentional.
**How to avoid:** Preserve D-06 insertion order strictly: hook → passive sweep. The hook always evaluates against pre-sweep state. Document this in `long_running_hook.py` docstring.

### Pitfall 7: turns_elapsed Mutation and Conservation Check
**What goes wrong:** The hook's `graph.set(actor, "current_long_action", updated_dict)` is a mutation. If conservation is configured to check ALL mutations in a tick, this mutation appears post-conservation-check.
**Why it happens:** Conservation runs on primary mechanic mutations only (the `primary_mutations = _flatten_mutations(primary_trace)` list), not on mutations made by the hook directly.
**How to avoid:** The hook's graph mutation (advancing `turns_elapsed`) is NOT a conserved property — it's a bookkeeping property, not a game resource like `health` or `coin`. The conservation.yaml only lists conserved game-world properties. No conflict. [ASSUMED — needs verification that hook mutations don't accidentally trigger conservation checks]

### Pitfall 8: `apply()` Returns Non-list Type After LRA Extension
**What goes wrong:** A mechanic's `apply()` returns something that is not `list[Mutation]` due to the LRA integration. The `ChainExecutionEngine` at line 61 does `mutations = mechanic.apply(ctx)` and then uses `mutations` as `list[Mutation]` without type checking.
**Why it happens:** If the chosen implementation puts `LongRunningAction` in the return value.
**How to avoid:** Use the `ctx.begin_long_action()` helper approach (Pattern 2 above). The helper writes to the graph and returns a `Mutation` (for the graph property set). The mechanic's `apply()` includes this `Mutation` in its list, returns `list[Mutation]` as always. `ChainExecutionEngine` remains unchanged. The engine detects the LRA from the graph property, not from the return value.

### Pitfall 9: `turns_total: None` in JSON Serialization
**What goes wrong:** Python's `None` serializes to JSON `null`. When loading from graph storage, `null` becomes Python `None`. This is correct, but the hook must handle the `None` case explicitly: `if turns_total is None or turns_elapsed < turns_total` logic breaks if the `None` comparison isn't checked first.
**How to avoid:** In the hook: `if lra["turns_total"] is not None and turns_elapsed >= lra["turns_total"]: # completed`

---

## Validation Rubric (Nyquist D8)

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, configured via pyproject.toml) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run | `uv run pytest tests/test_engine/test_long_running.py -x -q` |
| Full suite | `uv run pytest -v` |
| Integration tests (live LLM) | `uv run pytest -m integration` (excluded from default run) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | File | Automated Command |
|--------|----------|-----------|------|-------------------|
| SIM-09 | ThresholdSpec evaluates correctly for all 6 operators | unit | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_threshold_evaluator_all_ops -x` |
| SIM-09 | Missing node/property returns False (safe default) | unit | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_threshold_evaluator_missing_node -x` |
| SIM-09 | LongRunningAction dict is JSON-round-trip-safe | unit | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_lra_json_roundtrip -x` |
| SIM-09 | `turns_elapsed` advances each tick | integration | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_turns_elapsed_advances -x` |
| SIM-09 | Threshold fires at correct tick (not tick 0) | integration | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_threshold_fires_not_on_tick_zero -x` |
| SIM-09 | Bounded LRA completes when `turns_elapsed >= turns_total` | integration | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_bounded_lra_completes -x` |
| SIM-09 | New agent action clears LRA (D-11) | integration | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_new_action_clears_lra -x` |
| SIM-09 | Hook runs after primary execute, before passive sweep | integration | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_hook_placement -x` |
| SIM-09 | Long-running tick produces TickResult.ok (no yield/refuse) | integration | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_long_running_tick_result_kind -x` |
| SIM-10 | Sleep: wakes on noise threshold | integration | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_sleep_wakes_on_noise -x` |
| SIM-10 | Drunk: indefinite, sobers on sobriety threshold | integration | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_drunk_indefinite -x` |
| SIM-10 | Attention suppression removes properties from projection | unit | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_attention_suppression -x` |
| SIM-10 | Attention boost copies properties to attention_boosted | unit | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_attention_boost -x` |
| SIM-09+10 | Full sleep → 3 ticks → wake cycle (deterministic) | integration | test_long_running.py | `pytest tests/test_engine/test_long_running.py::test_sleep_to_wake_cycle -x` |
| SIM-09+10 | Autopilot travel: completes without hazard | demo | test_long_running.py | `pytest -m integration tests/test_engine/test_long_running.py::test_autopilot_no_hazard` |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_engine/test_long_running.py -x -q`
- **Per wave merge:** `uv run pytest tests/test_engine/ -x -q`
- **Phase gate:** `uv run pytest -v` (full suite) + `uv run mypy src/token_world/graph/` green

### Wave 0 Gaps (test infrastructure to create before implementation)
- [ ] `tests/test_engine/test_long_running.py` — new file, covers all test IDs above
- [ ] Fixtures: `sleeping_actor_kg` (actor with `current_long_action` = sleep dict), `noisy_room_kg` (room with `noise_level = 0.9`)
- [ ] FakeClassifier + FakeObserver already exist in Phase 6 patterns — reuse from existing Phase 6 test infrastructure

---

## Specific Research Findings Per Question

### Q1: LongRunningAction Minimum-Viable Fields

[VERIFIED: CONTEXT.md D-02, D-03, D-13, D-16 + graph/models.py ALLOWED_PROPERTY_TYPES]

Fields (all JSON-serializable as dict for graph storage):
- `action_text: str` — human label, not a verb (e.g., `"sleeping"`, `"traveling to market"`)
- `turns_total: int | None` — None = indefinite (D-16)
- `turns_elapsed: int` — starts at 0, incremented by hook each tick
- `thresholds: list[dict]` — list of ThresholdSpec dicts (not ThresholdSpec objects — must be plain dicts for JSON)
- `payload: dict` — mechanic-specific extras; `attention_state` lives here

No `actor_id` in the LRA dict — it's stored ON the actor node, so the actor_id is implicit.
No `started_tick` — could be added to `payload` if needed for diagnostics but is not required by any locked decision.
No `interruption_narrative_prompt` — the interruption prompt is on the engine/observer, not per-LRA.

### Q2: ThresholdSpec Operators

[VERIFIED: CONTEXT.md D-03]

Operators: `>`, `>=`, `<`, `<=`, `==`, `!=` — exactly these six. No `in`, `not_in`, `exists`, `not_exists` in v1. The CONTEXT explicitly says "Operators: `>`, `>=`, `<`, `<=`, `==`, `!=`" — no others.

Safe to add `exists`/`not_exists` later (backward-compatible ThresholdEvaluator extension). For v1: six operators only.

### Q3: Threshold Property Path Language

[VERIFIED: CONTEXT.md D-03, D-09 + visibility.py projection structure]

Direct dot-notation: `"node_id.prop_name"`. Node_id is the exact graph node_id (e.g., `"bedroom"`, `"alice"`). Prop_name is the exact property key in `projection[node_id]["properties"]`.

**No nested path support in v1.** `"room.nested.prop"` is NOT supported. The `.partition(".")` split gives `("room", ".", "nested.prop")` — `prop_name` would be `"nested.prop"` which won't match any key. Safe (returns False = threshold doesn't fire). Could be addressed in v2 with a recursive resolver.

**Key constraint:** The node_id must be in the current projection (i.e., the actor's visible nodes: location, contained, held). A threshold referencing a distant room node will never fire. This is intentional — thresholds reflect the agent's perceptual world.

### Q4: Mechanic Returning LongRunningAction

[VERIFIED: mechanic/protocol.py + mechanic/engine.py + CONTEXT.md D-05, D-15]

**Chosen approach:** `ctx.begin_long_action()` helper method on `MechanicContext` (D-15). Returns a `Mutation` (the `kg.set()` call). Mechanics include this in their `list[Mutation]` return. `apply()` signature unchanged. `ChainExecutionEngine` unchanged.

The engine detects the LRA from the graph node property after execution, not from the return value.

### Q5: Engine Tick Hook Placement

[VERIFIED: engine.py `_handle_execute()` lines 338-535 + CONTEXT.md D-06]

**Exact line:** After `cons_verdict.is_violation` check passes (line ~420), before `self._run_passive_sweep()` call (line 445). The `projection` call at line 492 (`self._projector.project_for(actor)`) must be pulled up before the hook call so the hook reuses it.

**Hook returns `HookResult`.** If `interrupted=True` or `completed=True`, `_handle_execute()` returns a `TickResult.ok()` with the interruption/completion observation (not a refusal — the mechanic executed successfully; the LRA just ended).

### Q6: Continuation of Long-Running Action

[VERIFIED: CONTEXT.md D-07 + engine.py `run_tick()` structure]

When the actor has an active LRA and the runner passes `action_text=None` (or the engine checks at top of `run_tick`):
1. Engine skips classify/match/decide entirely.
2. Engine calls a minimal `_handle_long_running_tick()` path that:
   a. Calls `project_for(actor, attention_state)` with the LRA's attention_state.
   b. Calls `LongRunningHook.process()` → advances `turns_elapsed`, evaluates thresholds.
   c. If interrupted/completed: calls `Observer.synthesize()` with interruption context → returns `TickResult.ok(interruption_observation)`.
   d. If continuing: returns `TickResult.ok("Time passes. You continue sleeping.")` (static template, D-22).
3. Passive sweep still runs (D-17 — world changes while agent sleeps).

**No ChainExecutionEngine call** during a long-running tick continuation — unless the mechanic itself chains (which it won't, since we're not calling `mech.apply()`).

### Q7: VisibilityProjector Signature

[VERIFIED: visibility.py `project_for()` signature + all 3 call sites in engine.py]

Current call sites in engine.py:
1. Line 557: `self._projector.project_for(actor)` (in `_handle_yield`)
2. Line 492: `self._projector.project_for(actor)` (in `_handle_execute`, stage 5 observe)
3. (Additional calls exist in tests)

**Extension:** `project_for(actor_id: str, attention_state: dict | None = None) -> dict` — backward-compatible, all existing calls get `attention_state=None` by default (Stage 5 is a no-op). The engine's long-running tick path explicitly passes `attention_state` from `current_long_action.payload`.

### Q8: Seed Mechanic Behaviors

[VERIFIED: CONTEXT.md D-13, D-18]

| Mechanic | `turns_total` | Thresholds | `attention_state` |
|----------|--------------|------------|-------------------|
| `sleep` | 8 | `noise_level > 0.7` (room), `health < 0.2` (actor) | suppress: visual_detail, smell; boost: noise_level |
| `autopilot_travel` | path length | `hazard_level > 0.5` (current room) | suppress: fine_detail; boost: hazard_level |
| `drunk` | None | `sobriety_level > 0.8` (actor) | suppress: fine_detail, social_nuance; boost: aggression_level |

**Sleep mechanic threshold node resolution:** The `noise_level` threshold needs to reference the actor's current room. The room's node_id is not known at mechanic-write time in a generic mechanic. **Solution:** Write a denormalized `nearby_noise_level` property to the actor node in the sleep mechanic's `apply()`, and reference `alice.nearby_noise_level` in the threshold. Each LRA tick, a passive mechanic or the hook can update this property. **OR:** Use a special-case where the hook resolves `actor.current_location_node` dynamically. For v1, the simplest approach: the sleep mechanic checks the actor's `location` edge at `apply()` time and hardcodes the room_id into the threshold dict at creation time. This is acceptable for demonstrator mechanics.

### Q9: Memory Integration

[VERIFIED: CONTEXT.md (not explicitly addressed) + Phase 6 memory (agent_memory SQLite table)]

Phase 7 does NOT add special memory recording for interruptions. The interruption is recorded in:
1. The tick summary (`long_running_action.interrupted = true`).
2. The `agent_memory` table via the existing `PlaytestRunner` / `ResidentAgent` loop — the interruption observation is the `observation_text` column for that tick.
3. The rolling context window (last 10 turns) will naturally include the interruption observation.

The agent knows "I was sleeping and woke up" because the interruption observation says so (grounded narrative from the Observer). No special memory field needed.

### Q10: Testing Strategy

[VERIFIED: CONTEXT.md D-14 + tests/test_engine/conftest.py + Phase 6 FakeClassifier pattern]

**Unit tests** (no LLM, no graph):
- `ThresholdEvaluator` with mocked projection dicts.
- `LongRunningAction` / `ThresholdSpec` JSON round-trip.
- `attention_state` projection modulation.

**Integration tests** (FakeClassifier + FakeObserver, DB-backed KG):
- Full LRA lifecycle using the existing `MockAnthropicClient` test double from `tests/test_engine/conftest.py`.
- Fabricate `current_long_action` directly on actor node, call `run_tick(None, actor)` multiple times, assert `turns_elapsed` advances and threshold fires at correct tick.
- D-11 cancellation: set LRA, call `run_tick("go north", actor)`, assert LRA cleared and normal pipeline runs.

**Demonstration tests** (`@pytest.mark.integration`):
- Full sleep → interrupt → wake cycle with real LLM.
- Autopilot travel with hazard injection.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 7 introduces no external tools or services beyond the existing project stack. All dependencies are Python standard library + existing project packages (networkx, anthropic SDK, pytest, pydantic). No new CLI tools, databases, or services required.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Per-state code paths (SleepState, DrunkState) | One LongRunningAction dataclass + thresholds | Massive reduction in special-casing |
| Full observation every tick | Static "time passes" + interruption observation only | Context window efficiency |
| Agent must re-issue action every tick | Synthetic action loop in engine | Agent unaware of multi-tick actions |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The engine's conservation checker only checks primary mechanic mutations (not hook mutations). Hook's `kg.set()` to advance `turns_elapsed` doesn't trigger conservation. | Pitfall 7 | Hook mutations might violate conservation if checker runs on ALL mutations. Needs verification at implementation time. |
| A2 | `turns_elapsed` should start at 0 and be incremented BEFORE threshold evaluation on first continuation tick (to ensure first-tick non-cancellation). | Pitfall 1 | If incremented after evaluation, first-tick insta-cancel could occur. |
| A3 | `PlaytestRunner` passes `action_text=None` (or equivalent) for long-running ticks; the runner is unaware of LRA state. The engine handles the None input. | Q6 | If runner has no None-passing support, a protocol extension is needed. |
| A4 | The sleep mechanic hardcodes the actor's current room node_id into thresholds at apply() time. | Q8 seed mechanics | If actor moves rooms while sleeping, the threshold node_id is stale. Acceptable for v1 demonstrator. |

---

## Open Questions

1. **How does `action_text=None` integrate with `run_tick(action_text: str, actor: str)`?**
   - Current signature: `action_text: str` (required).
   - Long-running continuation needs either `action_text=None` (change signature) or a sentinel string `"__continue_long_action__"` (magic string).
   - **Recommendation:** Change signature to `action_text: str | None`. The existing callers all pass real strings. PlaytestRunner passes `None` when actor has an active LRA. This is a backward-incompatible signature change but the call sites are all internal. Alternative: add a separate `continue_tick(actor)` method that the runner calls when it detects an active LRA.

2. **Who detects the active LRA — engine or runner?**
   - If engine detects (top of `run_tick`): runner is unaware, passes action_text normally, engine checks for LRA first.
   - If runner detects (checks graph before calling `run_tick`): runner needs graph access, creates coupling.
   - **Recommendation:** Engine detects (cleaner separation). The runner just calls `run_tick(None, actor)` when the agent produced no action (or always calls with the agent's text; the engine checks for LRA overriding if active).

3. **Interruption observation: should it be `TickResult.ok` or a new kind?**
   - An interrupted sleep is not an error, not a yield, not a refusal — it's a successful transition.
   - **Recommendation:** `TickResult.ok()` with the interruption observation. The tick summary's `long_running_action.interrupted = True` distinguishes it from a normal ok tick.

4. **How does `autopilot_travel` advance location each tick?**
   - The mechanic starts a LRA with `turns_total = path_length`. But where does the location-advance per-tick happen?
   - Options: (a) a passive TickMatcher mechanic that detects an active autopilot LRA and moves the actor 1 step; (b) the LongRunningHook calls a callback from the LRA payload; (c) the LRA payload includes a `next_room` property that the hook sets on the actor.
   - **Recommendation:** Option (a) — a separate `autopilot_advance` involuntary TickMatcher mechanic. Cleanest separation of concerns; the hook just evaluates thresholds. The advance mechanic fires after hook if LRA is still active.

---

## Sources

### Primary (HIGH confidence)
- `07-CONTEXT.md` — 23 locked decisions, all extracted verbatim
- `src/token_world/engine/engine.py` — exact insertion point for hook; `_handle_execute()` flow verified line-by-line
- `src/token_world/engine/visibility.py` — `project_for()` signature and stage structure verified
- `src/token_world/graph/models.py` — `ALLOWED_PROPERTY_TYPES` verified (tuple excluded)
- `src/token_world/mechanic/protocol.py` — `apply()` signature verified
- `src/token_world/mechanic/context.py` — `MechanicContext` API verified; `begin_long_action()` extension point identified
- `src/token_world/mechanic/engine.py` — `ChainExecutionEngine.execute()` flow verified; no change required with `ctx.begin_long_action()` approach
- `src/token_world/operator/yield_signal.py` — frozen dataclass pattern for `LongRunningAction` / `ThresholdSpec` (D-23)

### Secondary (MEDIUM confidence)
- `.planning/phases/05-simulation-engine/05-CONTEXT.md` — Phase 5 D-06, D-14, D-15, D-17, D-19 verified for integration points
- `.planning/phases/06-resident-agent-end-to-end-loop/06-CONTEXT.md` — D-25 FakeClassifier/FakeObserver pattern confirmed available
- `tests/test_engine/conftest.py` — MockAnthropicClient test double pattern confirmed reusable

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — no new external dependencies; everything verified in codebase
- Architecture: HIGH — all integration points read from actual source code
- Pitfalls: HIGH (verified) + MEDIUM (A1-A4 assumptions flagged)
- Seed mechanics: MEDIUM — behaviors locked by D-18; exact threshold node_id strategy has an open question (Q8)

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable codebase; 30 day validity)
