# Authoring Mechanics

A guide for operators (Claude Code + Opus, or any capable coding agent) authoring mechanics as ordinary Python in a Token World universe.

This guide is deliberately explicit. Under Phase 4's inversion-of-control model (D-01), Phase 4 does **not** ship a prompt-assembly pipeline — this document IS the prompt (D-18). Read it end-to-end before writing your first mechanic.

---

## 1. Introduction

### The universe-as-codebase metaphor

A Token World universe is a self-contained Python codebase on disk:

```
<universe>/
├── CLAUDE.md                      # world rules + pointers
├── AGENTS.md                      # symlink to CLAUDE.md
├── .mcp.json                      # MCP server config
├── universe.db                    # SQLite knowledge-graph persistence
├── mechanics/                     # YOU author here
│   ├── movement.py
│   ├── observation.py
│   ├── environmental_reaction.py
│   └── _helpers.py                # shared helpers (registry-invisible)
├── tests/test_mechanics/          # mirrored test tree
│   ├── __init__.py
│   ├── test_movement.py
│   └── test_pickup.py
├── docs/authoring-mechanics.md    # copy of this guide
├── agents/
├── tick_summaries/
└── diagnostics/                   # per-tick and per-validation diagnostics
```

Every universe is a real git repo, scaffolded by `token-world create "<name>"`. Mechanics are first-class source files: normal `git log`, normal diffs, normal imports, normal tests.

### Inversion of control

The operator — Claude Code driven by Opus via the Agent SDK — **authors** mechanics. There is no bespoke generator and no prompt pipeline. When the simulation engine (Phase 5) meets an action it cannot match, it halts the tick and yields to the operator. The operator writes the mechanic as Python code, runs `validate-mechanic`, fixes any errors, then resumes the tick.

**What Phase 4 provides you (the operator):**

- A clean flat mechanic layout (D-03..D-08).
- A strict validation gate (D-12..D-16) that catches contract mistakes pre-runtime.
- This guide (D-30).
- A `scaffold-mechanic` CLI helper (D-32).
- A diagnostics filesystem (D-21..D-25) for post-hoc inspection.

**What Phase 4 does NOT provide:**

- Retry loops, prompt-repair plumbing, generation-failure auto-recovery. You read the validation errors and edit the code. That's the loop (D-17).
- Runtime sandboxing. See §6.
- Coherence checking across mechanics. That's v2 hardening.

---

## 2. File Layout

Mechanics are flat `.py` modules (D-03):

- `mechanics/<id>.py` — one `Mechanic` subclass per file **by default**. Multi-mechanic files are allowed only when two or more mechanics share tight code/intent. Keep the default: one file per mechanic.
- `mechanics/_helpers.py`, `mechanics/_spatial.py`, `mechanics/_social.py`, etc. — shared helpers (D-05). The underscore prefix is the registry's skip signal: these files are **not** scanned for mechanics, but sibling mechanic files CAN import from them.
- `mechanics/__init__.py` — **must not exist**. The destination is not a Python package; mechanics are loaded via `importlib.util.spec_from_file_location`, not `import`.

Tests live in the mirrored test tree (D-06):

- In a scaffolded universe: `tests/test_mechanics/test_<id>.py`.
- In the framework repo: `tests/test_mechanic/test_seeds/test_<id>.py`.

Tests are NEVER colocated with the mechanic module. The validation pipeline's "tests" stage (§6) knows to probe both layouts.

### How the registry discovers mechanics

`MechanicRegistry.scan()`:

1. Lists every `<name>.py` in `mechanics/` where `<name>` does not start with `_` and is not `__init__.py`.
2. Runs the validation pipeline on each candidate module (`validate(module_path)`).
3. For each passing module, imports it via `importlib.util.spec_from_file_location` and collects every class that subclasses `Mechanic` (excluding `Mechanic` itself) and is defined in that module.
4. Rejects duplicate `id` values with a `ValueError` naming both file paths (T-04-REGISTRY-SHADOWING).

Invalid modules are excluded from the live index; their `ValidationReport` is persisted under `diagnostics/validation/<timestamp>_<id>/report.json`.

---

## 3. Mechanic Class Contract

A mechanic is a subclass of `token_world.mechanic.protocol.Mechanic`.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class PickupMechanic(Mechanic):
    """Agent picks up a target entity if within reach and inventory allows."""

    id = "pickup"
    description = "Agent picks up an entity"
    voluntary = True
    tags: list[str] = ["object_interaction"]

    def check(self, ctx: "MechanicContext") -> CheckResult:
        if not ctx.has_node(ctx.actor) or not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["actor or target missing"])
        actor_loc = ctx.query_node(ctx.actor).get("location")
        target_loc = ctx.query_node(ctx.target).get("location")
        if actor_loc != target_loc:
            return CheckResult(passed=False, reasons=["not colocated"])
        return CheckResult(passed=True)

    def apply(self, ctx: "MechanicContext") -> list[Mutation]:
        return [ctx.add_edge(ctx.actor, ctx.target, relation="holds")]
```

### Required class attributes

| Attribute | Type | Required | Default | Purpose |
|-----------|------|----------|---------|---------|
| `id` | `str` | yes | — | Unique identifier; used for registry indexing, diagnostics, matching |
| `description` | `str` | yes | — | Human-readable one-liner; shown in `list-mechanics` output |
| `voluntary` | `bool` | no | `True` | Voluntary (agent-initiated) or involuntary (reactive) — see §5 |
| `tags` | `list[str]` | no | `[]` | Classification tags for filtering (`query_by_tag`) |

The validation pipeline's **contract stage** (§6) fails a mechanic that omits `id` or `description` or types them wrong. `voluntary` and `tags` are checked for sensible defaults but may be overridden freely.

### Required methods

```python
def check(self, ctx: MechanicContext) -> CheckResult: ...
def apply(self, ctx: MechanicContext) -> list[Mutation]: ...
```

Both must have **exactly** the signature `(self, ctx)`. The validation pipeline's contract stage rejects alternative signatures (e.g. `check(self, actor, target)`).

**Idiom:** all preconditions belong in `check`; `apply` assumes `check` passed and performs the mutations. Do not re-check in `apply`.

### Optional method: `watches`

```python
def watches(self) -> list[Matcher]:
    return []
```

Involuntary mechanics override `watches` to declare which graph mutations trigger them. Voluntary mechanics leave the default (empty list).

---

## 4. MechanicContext DSL Reference

`MechanicContext` is the DSL wrapper the engine hands to `check` and `apply`. **All graph access MUST go through the context** — that is how mutations are logged, snapshots stay consistent, and AST rules can enforce mutation discipline.

```python
class MechanicContext:
    actor: str         # the agent (or entity) that initiated the action
    target: str        # the entity or location the action is directed at
    spatial: SpatialIndex        # lazy R-tree (ctx.spatial builds on first use)
    temporal: TemporalIndex      # lazy event-log query facade

    # Queries
    def has_node(self, node_id: str) -> bool: ...
    def has_edge(self, src: str, dst: str) -> bool: ...
    def query_node(self, node_id: str, property: str | None = None) -> Any: ...
    def query_neighbors(self, node_id: str) -> list[str]: ...
    def neighbors(self, node_id: str, *, relation: str | None = None) -> list[str]: ...
    def find_nodes(self, **filters: Any) -> list[str]: ...

    # Mutations (each returns a Mutation record, which is also auto-logged)
    def mutate(self, node_id: str, property: str, value: Any) -> Mutation: ...
    def set(self, node_id: str, property: str, value: Any) -> Mutation: ...  # alias
    def add_node(self, node_id: str, *, node_type: str, **props: Any) -> Mutation: ...
    def remove_node(self, node_id: str) -> Mutation: ...
    def add_edge(self, src: str, dst: str, **props: Any) -> Mutation: ...
    def remove_edge(self, src: str, dst: str) -> Mutation: ...

    # Identity
    def claim_id(self, name: str) -> str: ...
```

### Query methods

| Method | Returns | Common use | Gotchas |
|--------|---------|------------|---------|
| `has_node(id)` | `bool` | Gate every other query; nodes may not exist | Cheap; always call before `query_node` |
| `has_edge(src, dst)` | `bool` | Reachability check | Directed — `has_edge(a,b)` ≠ `has_edge(b,a)` |
| `query_node(id)` | `dict[str, Any]` | Fetch all properties on a node | Raises `KeyError` if node missing; check `has_node` first |
| `query_node(id, "prop")` | `Any` | Fetch one property | Raises `KeyError` if property missing; use `query_node(id).get("prop")` for safe lookup |
| `query_neighbors(id)` | `list[str]` | Adjacent-node IDs | Returns out-neighbors only (directed graph) |
| `find_nodes(**filters)` | `list[str]` | Find nodes by property equality | Filters are AND-ed; `find_nodes(type="agent")` works |
| `ctx.spatial` | `SpatialIndex` | R-tree spatial queries | Lazy; first access rebuilds from the graph — avoid in hot paths that don't need it |
| `ctx.temporal` | `TemporalIndex` | Historical graph state | Lazy; queries walk the event log |

### Mutation methods

| Method | Purpose | Notes |
|--------|---------|-------|
| `mutate(id, prop, value)` | Set/update a property | Value must be JSON-serializable (str, int, float, bool, None, list, dict) |
| `add_node(id, node_type="...", **props)` | Create a new node | `node_type` must be `"agent"` or `"entity"` — NO other values |
| `remove_node(id)` | Delete node and all its edges | Cascades on edges; event log records each removal |
| `add_edge(src, dst, **props)` | Create a directed edge | Edge properties stored on the edge; common key: `relation="holds"` |
| `remove_edge(src, dst)` | Delete a directed edge | Removes only the forward edge |

### Node IDs

Never hardcode node IDs that might collide with operator-authored content. Use `kg.claim_id("<readable_name>")` when creating new nodes — it returns `"wallet"`, `"wallet_a7"`, `"wallet_a7z6"`, etc., progressively suffixed on collision. Mechanics usually claim IDs at the `KnowledgeGraph` boundary (outside `MechanicContext`) when seeding new entities; inside a mechanic you typically already have the target ID.

### Property values

**All property values must be JSON-serializable**: `str, int, float, bool, None, list, dict`. This is enforced by `ALLOWED_PROPERTY_TYPES` inside `KnowledgeGraph`. Sets, tuples, bytes, custom objects, `datetime` objects — not allowed. Store ISO strings for times; store lists for sets.

### MechanicContext DSL Surface (Frozen)

The public surface of `MechanicContext` is **frozen** and pinned by `tests/test_mechanic/test_context_api.py`. Seed mechanics may rely on exactly these names and signatures; anything not listed here is either private, a known gap, or a yet-to-be-added method that requires a paired test + docs update to land.

Additions must:
1. Land with a delegator implementation in `src/token_world/mechanic/context.py`,
2. Be added to `EXPECTED_CALLABLES` / `EXPECTED_ATTRS` in the test, AND
3. Be documented in this section.

Silent drift fails the test. If the test fails, read it — the failure message points at what changed.

#### Core graph API (always available)

| Symbol | Signature | Purpose | Example |
|---|---|---|---|
| `ctx.actor` | `str` | Node ID of the action initiator | `ctx.query_node(ctx.actor)` |
| `ctx.target` | `str` | Node ID / string of the action's object | `ctx.has_node(ctx.target)` |
| `has_node` | `(node_id) -> bool` | Existence check; always gate before `query_node` | `if not ctx.has_node(x): ...` |
| `has_edge` | `(src, dst) -> bool` | Directed-edge existence | `ctx.has_edge("alice", "sword")` |
| `query_node` | `(node_id, property=None) -> Any` | Fetch all props or one | `ctx.query_node("alice", "hunger")` |
| `query_neighbors` | `(node_id) -> list[str]` | All out-neighbors | `ctx.query_neighbors("room_a")` |
| `neighbors` | `(node_id, *, relation=None) -> list[str]` | Out-neighbors filtered by edge `relation` property | `ctx.neighbors(actor, relation="holds")` |
| `find_nodes` | `(**filters) -> list[str]` | Nodes matching property equality (AND-ed) | `ctx.find_nodes(subtype="weapon")` |
| `mutate` | `(node_id, property, value) -> Mutation` | Set/update a property | `ctx.mutate(actor, "hp", 10)` |
| `set` | `(node_id, property, value) -> Mutation` | Alias for `mutate` (matches `KnowledgeGraph.set` naming) | `ctx.set(actor, "hunger", 0)` |
| `add_node` | `(node_id, *, node_type, **props) -> Mutation` | Create node; `node_type` must be `"agent"` or `"entity"` | `ctx.add_node(new_id, node_type="entity", subtype="sword")` |
| `remove_node` | `(node_id) -> Mutation` | Delete node + cascade edges | `ctx.remove_node(target)` |
| `add_edge` | `(src, dst, **props) -> Mutation` | Directed edge with arbitrary props (common: `relation="..."`) | `ctx.add_edge(a, b, relation="holds")` |
| `remove_edge` | `(src, dst) -> Mutation` | Remove forward edge only | `ctx.remove_edge(a, b)` |
| `claim_id` | `(name) -> str` | Unique readable ID (delegates to `KnowledgeGraph.claim_id`) | `new_id = ctx.claim_id(recipe.output_subtype)` |

#### Spatial queries (lazy — `ctx.spatial`)

First access builds a `SpatialIndex` (R-tree over the graph) and caches it on the context. Mechanics that never touch spatial queries pay zero rtree cost.

| Symbol | Signature | Purpose |
|---|---|---|
| `ctx.spatial.nearest` | `(point, *, k=1, node_type=None, subtype=None) -> list[str]` | k nearest node IDs (Euclidean, post-filtered) |
| `ctx.spatial.within` | `(bbox, *, node_type=None, subtype=None) -> list[str]` | Node IDs intersecting a bbox |
| `ctx.spatial.intersects` | `(node_id, *, node_type=None, subtype=None) -> list[str]` | Node IDs overlapping another node's bbox (excluding self) |

#### Temporal queries (lazy — `ctx.temporal`)

Present and callable; see `src/token_world/graph/temporal.py` for available methods. Not exhaustively pinned by the surface test — the temporal facade is less heavily consumed by Phase 4 seed mechanics.

#### Known gaps — plans MUST stub these

These are **referenced by plans 04-06..04-11 but intentionally absent from `MechanicContext`**. A mechanic that needs one must ship as a framework-gap stub (§8): class-level `blocked_by`, `check()` returns `passed=False` with the gap ID in `reason`, `apply()` returns `[]`. Adding one of these to the framework is a scoped follow-up, not a Phase 4 seed-plan concern.

| Missing symbol | Blocked by | Used by | Stub pattern |
|---|---|---|---|
| `ctx.actors` | GAP-ENG02 | MECH12 (broadcast) | `blocked_by = ["GAP-ENG02"]`; check returns `passed=False, reasons=["blocked_by GAP-ENG02"]` |
| `ctx.spatial.segment_intersections` | GAP-GRAPH02 | MECH02 (look with occluders) | Stub mechanic OR fall back to neighbor-by-subtype scan (documented in module docstring) |
| `ctx.seed` / `ctx._seed` | GAP-GRAPH05 | MECH21 (fire_spread), any sampling mechanic | Stub OR seed Python `random` with `tick_id` and document nondeterminism |

Do not reach into `ctx._graph` or any other private attribute to paper over these gaps — mechanics caught doing so fail the `forbidden` AST rules in the validation gate (D-14).

---

## 5. Voluntary vs Involuntary — Matcher Declaration

### Voluntary mechanics

The default. Triggered by resident-agent actions. The simulation engine classifies the action, picks the voluntary mechanic whose `check` passes, and calls `apply`. `voluntary = True`; `watches()` returns `[]`.

### Involuntary mechanics

Reactive. Triggered by graph mutations (set-property, add/remove node, add/remove edge). The chain-execution engine watches every mutation that results from an `apply`, and for each involuntary mechanic whose `watches()` matchers match the mutation, it invokes `check(ctx)`; if passing, it calls `apply(ctx)` as a chained tick. This is how `environmental_reaction.py` spreads fire to neighbours when a node's temperature rises past 100.

```python
from token_world.mechanic.matchers import (
    PropertyChangeMatcher, EdgeMatcher, NodeMatcher, Matcher,
)

class Ignites(Mechanic):
    id = "ignites"
    description = "Hot adjacent entities ignite flammables"
    voluntary = False
    tags: list[str] = ["environmental", "reactive"]

    def watches(self) -> list[Matcher]:
        return [
            PropertyChangeMatcher(property_name="temperature"),
            PropertyChangeMatcher(property_name="on_fire", node_type="entity"),
            EdgeMatcher(event_type="add_edge", edge_label="holds"),
            NodeMatcher(event_type="add_node", node_type="entity"),
        ]
    ...
```

**Matcher primitives:**

- `PropertyChangeMatcher(property_name, node_type=None)` — matches `set_property` mutations on `property_name`. `node_type` (optional: `"agent"` or `"entity"`) filters by the target node's type.
- `EdgeMatcher(event_type, edge_label=None)` — `event_type` is `"add_edge"` or `"remove_edge"`. `edge_label` (optional) filters by the edge's `relation` property.
- `NodeMatcher(event_type, node_type=None)` — `event_type` is `"add_node"` or `"remove_node"`. `node_type` (optional) filters by the node's type.

The engine's `max_chain_depth=10` caps chain recursion. Beyond it, the chain execution emits a truncation warning; your mechanics should not assume unbounded cascades.

---

## 6. The Validation Gate (D-14)

Before any mechanic loads or runs, it passes through a six-stage validation pipeline (`token_world.mechanic.validation.validate(module_path)`):

| Stage | Check | Hard fail → halts pipeline |
|-------|-------|-----------------------------|
| 1. syntax | `ast.parse` succeeds | yes |
| 2. ast | D-14 AST rules (forbidden imports, forbidden calls, at least one `Mechanic` subclass) | yes |
| 3. import | `importlib` executes module top-level code without raising | yes |
| 4. contract | Each concrete Mechanic subclass has `id: str`, `description: str`, `check(self, ctx)`, `apply(self, ctx)` | yes |
| 5. tests | If a mirrored `test_<id>.py` exists, it passes under pytest | yes |
| 6. smoke | Class instantiates; `check(ctx)` on an empty fixture doesn't raise | yes |

Findings within a stage accumulate; you see every AST rule violation on a single run, not just the first.

### Forbidden imports (FORBIDDEN_IMPORT_PREFIXES)

```
networkx
networkx.*
token_world.graph.knowledge_graph
```

**Why:** mechanics must go through `MechanicContext` so all mutations are logged, snapshotted, and rollback-safe. Direct `networkx.DiGraph` access bypasses the event store and leaves the SQLite persistence inconsistent.

### Forbidden calls (FORBIDDEN_CALL_NAMES, bare-name only)

```
eval, exec, __import__, compile, globals, open
```

**Why:** authoring discipline. These names never appear in legitimate mechanic code. A mechanic that needs to read a file should accept a path parameter or use a properly scoped helper; a mechanic that needs dynamic dispatch should use a dispatch table, not `eval`.

Only **bare-name** calls are flagged. Attribute forms (`foo.eval()`, `self.exec()`) are intentionally permitted — the flag exists to surface obvious misuses, not to pattern-match every possible Python construct.

### CRITICAL: AST rules are NOT a sandbox (T-04-AST-BYPASS)

These AST rules are a **reasonable-effort pre-runtime control, NOT a sandbox.** Dynamic imports via `importlib` or attribute access like `sys.modules['networkx']` WILL bypass them. v1 runs mechanic code directly; snapshots and rollback are the runtime safety net. Runtime sandboxing (RestrictedPython) is a v2 concern.

The `subprocess` invocation for the tests stage uses `argv` lists (`shell=False`), so mechanic IDs are never interpolated into a shell string (T-04-TEST-EXEC). That is also accepted-and-documented, not a sandboxing boundary.

### Running the validator

```bash
# Direct-path mode (ideal for framework-repo seeds)
uv run token-world validate-mechanic src/token_world/mechanic/seeds/movement.py

# Universe-slug mode (ideal for operator-authored universe mechanics)
uv run token-world validate-mechanic my_universe pickup

# JSON output (for scripting, diagnostics, or piping to `jq`)
uv run token-world validate-mechanic my_universe pickup --format json
```

**Exit codes:**

- `0` — pass
- `1` — validation failed (inspect stderr for `[severity] [stage:rule] file:line:col — message`)
- `2` — resolver error (slug not found, mechanic file missing, usage error)

Read the error, edit the code, re-run. That's the loop (D-17).

---

## 7. The `_helpers.py` Convention (D-05, D-11)

Shared code lives in sibling `_*.py` modules:

```
mechanics/
├── pickup.py             # imports `_find_reachable` from _spatial
├── drop.py               # imports `_find_reachable` from _spatial
├── craft.py
└── _spatial.py           # def _find_reachable(ctx, src, dst) -> bool: ...
```

**Rules:**

- Underscore-prefixed modules are **not** registered as mechanics. They're invisible to the registry.
- Sibling mechanic files CAN import from them (`from mechanics._spatial import _find_reachable` — or, inside a scaffolded universe, via the universe's package path).
- AST rules allow imports from `token_world.mechanic.*` and sibling `_*.py` helpers within the same mechanics directory.

**Style guidance (D-11):** default to free functions in `_helpers.py`-style modules. Introduce base classes like `SpatialMechanic(Mechanic)` ONLY when a clear shared pattern emerges across ≥3 mechanics and the inheritance pays for itself. Refactor opportunistically as the mechanic library grows; early premature abstraction is the cardinal sin here.

**Example — shared helper:**

```python
# mechanics/_spatial.py
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


def _find_open_passage(ctx: "MechanicContext", src: str, dst: str) -> bool:
    """Returns True if `src -> dst` is a passable edge (no `blocked=True`)."""
    if not ctx.has_edge(src, dst):
        return False
    # Edge properties aren't exposed through MechanicContext yet; query the
    # source node's neighbors + neighbor properties.
    return True
```

Both `passage_move.py` and `try_door.py` can import `_find_open_passage` — no duplication, no base class ceremony.

---

## 8. Framework-Gap-Stub Convention (D-38)

**Problem.** Some mechanics need framework extensions that haven't shipped yet. A cooperative mechanic might need `ctx.actors: list[NodeId]` (multiple actors per tick — GAP-ENG05). An LLM-adjudicated outcome might need a new `llm_adjudicated` category on the chain engine (GAP-ENG03). Authoring these mechanics today without the extension would mean either importing a symbol that doesn't exist (validation stage 3 fails) or hacking around the missing framework.

**Solution.** Ship the mechanic as a **stub** with a `blocked_by` class attribute. The integration test harness (04-04) reads `blocked_by` and records these as `blocked_by_framework_gap` outcomes, distinct from correctness failures.

```python
class CooperateMechanic(Mechanic):
    """Multi-actor cooperative action (MECH12; blocked on GAP-ENG05)."""

    id = "cooperate"
    description = "Multi-actor cooperative action (blocked on GAP-ENG05)"
    voluntary = True
    tags: list[str] = ["social", "cooperation"]
    blocked_by = "GAP-ENG05"  # integration harness reads this class attribute

    def check(self, ctx: "MechanicContext") -> CheckResult:
        return CheckResult(
            passed=False,
            reasons=[f"blocked by framework gap {self.blocked_by}"],
        )

    def apply(self, ctx: "MechanicContext") -> list[Mutation]:
        return []
```

**Critical constraints:**

- The stub MUST NOT import a symbol that does not yet exist. That would break validation stage 3 (import). Keep imports to what is already shipping.
- `check()` MUST return `CheckResult(passed=False, ...)` with a standardized reason containing `"blocked by framework gap <GAP-ID>"`. The integration test harness greps for this.
- `apply()` MUST be a no-op returning `[]`. A stub should never mutate the graph.
- `blocked_by` is a plain class attribute (string). No helper, no framework contract beyond the convention.

When the framework gap closes, the stub is rewritten in place: `blocked_by` is deleted; `check` and `apply` get real bodies; no further scaffolding changes are needed.

---

## 9. Reactive-Cycle Cautions (GAP-MECH26 absorbed)

Involuntary mechanics that mutate properties they also watch can cause **infinite cycles**. The engine's `max_chain_depth=10` backstops runaway loops, but relying on the backstop is a code smell — the mechanic is implicitly broken even when it terminates.

**Rules of thumb:**

1. **Before writing an involuntary mechanic, write down its trigger set AND its side-effect set.** If the two overlap, you're staring at a potential cycle. Reconsider.

   *Example.* A mechanic watches `PropertyChangeMatcher(property_name="temperature")` and inside `apply` sets `temperature` on neighbours. If neighbours are interconnected flammables, every ignition re-triggers the same mechanic. The mitigation is the `if current_temperature < 100` guard inside `apply` — the reactive cycle terminates because there are only finitely many not-yet-ignited neighbours.

2. **Prefer property-transition matchers over "every set_property of X."** If you care about "went from False to True," you can express that in the `check` by inspecting both `ctx.query_node(...)` and the recent event log via `ctx.temporal`. The matcher fires on every property change; the `check` is where you discriminate transitions.

3. **Use `ExecutionTrace` in tests to inspect the chain tree.** The chain execution engine produces a tree of firings; your tests can assert the tree's shape (no unintended re-firings; no chains deeper than expected). See `ExecutionTrace.max_depth_reached`, `ExecutionTrace.total_mechanics_executed`, `ExecutionTrace.truncated`.

4. **Idempotence is cheap insurance.** Write `apply` so that a second identical invocation is a no-op. An idempotent `apply` can never drive an unbounded cycle.

---

## 10. Trust Boundary Rationale (GAP-MECH19 absorbed)

Earlier drafts of Phase 4 proposed tracking a mechanic's `source` (`llm_generated` vs `human`) and a `reviewed=true/false` metadata flag, on the theory that LLM-authored mechanics needed a separate trust tier. D-35 obsoletes that framing.

**Under inversion of control, ALL mechanics are operator-authored.** Whether the operator is Claude Code + Opus, a human, or a mix, every mechanic flows through:

1. The filesystem (files land in `mechanics/<id>.py`).
2. The AST gate (forbidden imports, forbidden calls).
3. The import gate (the module loads cleanly).
4. The contract gate (class has `id`, `description`, `check`, `apply`).
5. The tests gate (sibling test file passes).
6. The smoke gate (`check(ctx)` on an empty fixture does not raise).

There is no `source='llm_generated'` distinction. There is no `reviewed=true/false` metadata. The validation gate IS the review step; passing validation IS "reviewed." GAP-MECH19 closes without additional code.

---

## 11. Testing Conventions

### Where tests live

- Framework seeds: `tests/test_mechanic/test_seeds/test_<id>.py` (mirrored against `src/token_world/mechanic/seeds/<id>.py`).
- Universe-local mechanics: `<universe>/tests/test_mechanics/test_<id>.py`.

The validation pipeline's tests stage (§6) probes both layouts and runs the first one that exists. If no sibling test file exists, the validation pipeline emits a `no_tests_found` **warning** (not an error). Warnings do not fail validation, but you should ship tests regardless.

### The standard pattern

```python
"""Tests for the pickup mechanic."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from mechanics.pickup import PickupMechanic   # import depends on universe package layout


@pytest.fixture
def kg() -> KnowledgeGraph:
    g = KnowledgeGraph()
    g.add_node("room_a", node_type="entity")
    g.add_node("alice", node_type="agent", location="room_a")
    g.add_node("rock", node_type="entity", location="room_a")
    return g


def test_pickup_passes_when_colocated(kg: KnowledgeGraph) -> None:
    ctx = MechanicContext(kg, actor="alice", target="rock")
    assert PickupMechanic().check(ctx).passed is True


def test_pickup_fails_when_not_colocated(kg: KnowledgeGraph) -> None:
    kg.set("rock", "location", "room_b")
    kg.add_node("room_b", node_type="entity")  # ensure target location exists
    ctx = MechanicContext(kg, actor="alice", target="rock")
    result = PickupMechanic().check(ctx)
    assert result.passed is False
    assert any("colocated" in r for r in result.reasons)


def test_pickup_adds_holds_edge(kg: KnowledgeGraph) -> None:
    ctx = MechanicContext(kg, actor="alice", target="rock")
    mutations = PickupMechanic().apply(ctx)
    assert kg.has_edge("alice", "rock")
    assert any(m.type == "add_edge" for m in mutations)
```

Framework seeds may prefer the `GraphBuilder` fluent helper (`tests/test_graph/conftest.py`). Universe tests typically use plain `KnowledgeGraph()` fixtures — simpler, closer to the ground truth.

### Chain testing

Multi-mechanic chain tests use `ChainExecutionEngine`:

```python
from token_world.mechanic import ChainExecutionEngine, MechanicContext
from mechanics.environmental_reaction import EnvironmentalReactionMechanic

def test_fire_spreads_two_hops(kg):
    ctx = MechanicContext(kg, actor="scientist", target="log_1")
    engine = ChainExecutionEngine([EnvironmentalReactionMechanic()])
    trace = engine.execute(voluntary=some_voluntary_mech, ctx=ctx)
    assert trace.max_depth_reached >= 2
    assert not trace.truncated
```

---

## 12. Common Anti-Patterns

- **Direct `kg._graph.add_node(...)`** — violates mutation-mediated access. Use `ctx.add_node(...)` so the mutation is logged and snapshotted.
- **Mutable class attributes as containers** — `queue: list = []` on the class is shared across instances. Use instance state inside `check`/`apply` (or avoid state entirely; mechanics should be stateless between ticks).
- **`assert` statements for validation** — users can run Python with `-O`, which strips asserts. Use `CheckResult(passed=False, reasons=[...])` for validation-like behaviour.
- **Non-JSON-serializable values in graph props** — sets, tuples, bytes, custom objects, `datetime`. Enforced by `ALLOWED_PROPERTY_TYPES`. Store ISO strings for times; store lists for sets.
- **Hardcoded node IDs that could collide** — use `kg.claim_id("name")` for new nodes.
- **Blocking external IO** — HTTP calls, `time.sleep`, filesystem scans (via bare `open` — also forbidden by AST rules). The execution model doesn't support blocking.
- **Re-checking preconditions inside `apply`** — `check` passed, so `apply` assumes success. A mechanic whose `apply` guards against its own `check` failure is either missing a precondition or papering over a concurrency assumption that doesn't exist.
- **Using `print` for diagnostics** — write to the diagnostics sink (post-Phase 5) or return rich `CheckResult` reasons. `print` bypasses structured logging.

---

## 13. Worked Examples

Three framework seeds live under `src/token_world/mechanic/seeds/` and ship with every scaffolded universe. Each illustrates a distinct pattern.

### 13.1 `movement.py` — voluntary, mutating

```python
class MovementMechanic(Mechanic):
    id = "movement"
    description = "Agent moves between connected locations"
    voluntary = True
    tags = ["spatial", "core"]

    def check(self, ctx):
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["Actor does not exist"])
        actor_props = ctx.query_node(ctx.actor)
        location = actor_props.get("location")
        if not location:
            return CheckResult(passed=False, reasons=["Actor has no location"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["Target location does not exist"])
        if not ctx.has_edge(location, ctx.target):
            return CheckResult(passed=False, reasons=[f"No path from {location} to {ctx.target}"])
        return CheckResult(passed=True)

    def apply(self, ctx):
        return [ctx.mutate(ctx.actor, "location", ctx.target)]
```

Reads actor's `location` property, writes a new `location`. Textbook voluntary mechanic: one precondition chain, one mutation.

### 13.2 `observation.py` — voluntary, read-only

```python
class ObservationMechanic(Mechanic):
    id = "observation"
    description = "Agent observes entities and properties at current location"
    voluntary = True
    tags = ["perception", "core"]

    def check(self, ctx):
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["Actor does not exist"])
        if "location" not in ctx.query_node(ctx.actor):
            return CheckResult(passed=False, reasons=["Actor has no location"])
        return CheckResult(passed=True)

    def apply(self, ctx):
        # Read-only mechanic: no mutations. Observation content is synthesized
        # by the simulation engine from graph state (Phase 5).
        return []
```

Read-only mechanics return `[]` from `apply`. The simulation engine renders the observation; the mechanic's role is to confirm the action is legal.

### 13.3 `environmental_reaction.py` — involuntary, matcher-driven

```python
class EnvironmentalReactionMechanic(Mechanic):
    id = "environmental_reaction"
    description = "Fire spreads to adjacent flammable entities when temperature changes"
    voluntary = False
    tags = ["environmental", "reactive", "core"]

    def watches(self):
        return [PropertyChangeMatcher(property_name="temperature")]

    def check(self, ctx):
        # Target is the node whose temperature changed.
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["Target does not exist"])
        try:
            temp = ctx.query_node(ctx.target, "temperature")
        except KeyError:
            return CheckResult(passed=False, reasons=["No temperature property"])
        if not isinstance(temp, (int, float)) or temp < 100:
            return CheckResult(passed=False, reasons=[f"Temperature {temp} too low for fire spread"])
        neighbors = ctx.query_neighbors(ctx.target)
        flammable = [n for n in neighbors if ctx.query_node(n).get("flammable", False)]
        if not flammable:
            return CheckResult(passed=False, reasons=["No flammable neighbors"])
        return CheckResult(passed=True)

    def apply(self, ctx):
        mutations = []
        for n in ctx.query_neighbors(ctx.target):
            props = ctx.query_node(n)
            if props.get("flammable", False) and props.get("temperature", 0) < 100:
                mutations.append(ctx.mutate(n, "temperature", 150))
                mutations.append(ctx.mutate(n, "on_fire", True))
        return mutations
```

Classic reactive mechanic. Watches `temperature` changes; fires when the target is hot enough AND has flammable neighbours; ignites those neighbours. The `< 100` guard inside `apply` keeps the reactive cycle bounded — a node that is already ignited is not re-ignited, so the chain terminates when every flammable neighbour reaches 150.

---

## 14. Workflow

```bash
# 1. Scaffold a new mechanic skeleton
token-world scaffold-mechanic my_universe --id pickup

# Emits:
#   <universe>/mechanics/pickup.py           (skeleton)
#   <universe>/tests/test_mechanics/test_pickup.py  (pytest.skip stub)

# 2. Edit the skeleton — fill in check() and apply()
$EDITOR <universe>/mechanics/pickup.py

# 3. Write tests — flip the pytest.skip stub to real tests
$EDITOR <universe>/tests/test_mechanics/test_pickup.py

# 4. Validate
token-world validate-mechanic my_universe pickup
# PASS <path>                                           → exit 0 (ship it)
# FAIL <path>                                           → exit 1 (read findings, edit, retry)
#   [error] [ast:forbidden_import] <path>:1:0 -- Forbidden import: 'networkx'
#   [error] [contract:missing_id_attr] <path> -- PickupMechanic missing required class attribute 'id: str'
# Error: ...                                            → exit 2 (resolver error — slug or file missing)

# 5. Iterate. The loop is: read errors → edit → re-run. No retry plumbing needed (D-17).

# 6. Run the universe tick (Phase 5) — the registry auto-scans mechanics/ on every resume_tick.

# 7. Inspect diagnostics
ls <universe>/diagnostics/tick_<N>/
# action.txt  classification/  matching.json  execution/  observation/  summary.json

# Prune old diagnostics as the universe accumulates ticks
token-world prune-diagnostics my_universe --before-tick 1000            # dry-run listing
token-world prune-diagnostics my_universe --before-tick 1000 --confirm  # actually delete
```

---

## Reference

- **Source of truth:** `src/token_world/mechanic/protocol.py` (`Mechanic` ABC + `CheckResult`), `src/token_world/mechanic/context.py` (`MechanicContext` DSL), `src/token_world/mechanic/matchers.py` (matcher primitives), `src/token_world/mechanic/validation.py` (AST rules + stage implementations).
- **Seeds:** `src/token_world/mechanic/seeds/{movement,observation,environmental_reaction}.py`.
- **CLI:** `src/token_world/cli.py` (`validate-mechanic`, `scaffold-mechanic`, `list-mechanics`, `prune-diagnostics`).
- **Decisions:** `.planning/phases/04-llm-mechanic-generation/04-CONTEXT.md` — D-01 (inversion of control), D-11 (code-reuse style), D-17 (no retry loop), D-18 (docs replace prompts), D-30 (this guide), D-31 (universe-local copy), D-32 (scaffold-mechanic), D-35 (trust-boundary rationale, absorbing GAP-MECH19), D-38 (framework-gap-stub convention).
