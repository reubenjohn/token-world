# Phase 2: Mechanic Framework - Research

**Researched:** 2026-04-12
**Domain:** Python mechanic protocol, chain execution engine, CLI tooling, git-based versioning
**Confidence:** HIGH

## Summary

Phase 2 builds the mechanic framework on top of the existing KnowledgeGraph (Phase 1). The core deliverables are: (1) a Mechanic protocol with check/apply lifecycle, (2) a MechanicContext providing DSL primitives that wrap the KnowledgeGraph API, (3) a chain execution engine for involuntary mechanics with declarative matchers, (4) three seed mechanics proving the API, (5) a file-scanning registry with git-based version history, and (6) three CLI commands extending the existing Click group.

The architecture is straightforward Python -- abstract base class, dataclasses for results, and a context object that mediates all graph access. The most complex piece is the chain execution engine (D-09) which must handle recursive mechanic triggering with cycle detection and depth limits. The matcher system (D-08) for involuntary mechanics needs careful design as it bridges graph mutations to mechanic activation.

**Primary recommendation:** Build bottom-up -- protocol and context first, then seed mechanics that validate the API, then chain execution engine tested via the Environmental Reaction seed mechanic, then registry and CLI last.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Mechanic base class with `check(ctx) -> CheckResult` and `apply(ctx) -> list[Mutation]`. CheckResult contains `passed: bool` and `reasons: list[str]`.
- D-02: apply() returns `list[Mutation]` only. No observation hints.
- D-03: Every mechanic has `id: str` and `description: str` as class-level attributes.
- D-04: Read-only mechanics use same check/apply with apply() returning empty list.
- D-05: MechanicContext wraps graph with DSL methods: `query_node()`, `query_neighbors()`, `mutate()`, `add_node()`, `remove_node()`, `add_edge()`, `remove_edge()`.
- D-06: Context carries `actor` and `target` attributes set by engine before invocation.
- D-07: Mechanics have `voluntary: bool` flag (default True).
- D-08: Involuntary mechanics declare matchers via `watches()` method returning declarative matcher objects.
- D-09: Full chain execution engine in Phase 2. Configurable max depth (default 10), cycle detection, execution trace tree.
- D-10: Execution trace is a tree recording which mechanic triggered which, with mutation details.
- D-11: Three seed mechanics: Movement (voluntary), Observation (voluntary, read-only), Environmental Reaction (involuntary).
- D-12: Environmental reaction validates chain execution end-to-end.
- D-13: Git commit = version. No semver. Registry queries git log.
- D-14: Lightweight in-memory registry built by scanning mechanic folders.
- D-15: Each mechanic is a folder: `mechanic.py`, `tests/`, `meta.yaml`.
- D-17: `list-mechanics <universe>` CLI command.
- D-18: `run-mechanic <universe> <mechanic-id> --actor <id> --target <id>` CLI command.
- D-19: `query-graph <universe>` with filters CLI command.
- D-20: No `inspect-mechanic` command.

### Claude's Discretion
- D-16: meta.yaml content and depth
- Mechanic folder location strategy (built-in seed mechanics bundled in package vs universe-only)
- Matcher primitive API design (what declarative matcher types to support)
- Execution trace data structure details
- query-graph output format and filter syntax

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MECH-01 | Mechanic protocol defines check(preconditions) and apply(side effects) against the graph | Protocol pattern (ABC + dataclasses), CheckResult/Mutation types, MechanicContext DSL |
| MECH-02 | Framework provides DSL-like primitives for graph queries and mutations | MechanicContext wrapping KnowledgeGraph API, query_node/query_neighbors/mutate/add_node etc. |
| MECH-05 | Each mechanic lives in its own folder versioned by universe git repo | Folder structure pattern, meta.yaml schema, git log for version history |
| MECH-06 | Mechanic registry indexes mechanic folders; list, inspect, query programmatically | File-scanning registry, importlib for dynamic loading, git subprocess for history |
| TEST-01 | Unit tests for mechanic preconditions/side effects against small hand-crafted graphs | GraphBuilder reuse, MechanicContext test fixtures, per-seed-mechanic test suites |
| AUTO-03 | CLI scripts for common operations | Click commands extending existing cli.py group |
</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12+ | Runtime | Project constraint [VERIFIED: pyproject.toml] |
| NetworkX | 3.6.1 | Graph backend (via KnowledgeGraph) | Already installed, Phase 1 [VERIFIED: runtime import] |
| Click | 8.3.2 | CLI framework | Already installed, existing CLI [VERIFIED: runtime import] |
| Pydantic | 2.12.5 | Data validation (optional for models) | Already installed [VERIFIED: runtime import] |
| pytest | 9.0+ | Testing | Already in dev deps [VERIFIED: pyproject.toml] |

### New Dependency Required
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML | 6.0.3 | Parse meta.yaml in mechanic folders | Registry loads meta.yaml for mechanic metadata [VERIFIED: pip index, NOT currently installed] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyYAML | tomllib (stdlib) | YAML is more natural for human-edited metadata; tomllib is stdlib but TOML is noisier for simple metadata |
| PyYAML | Pure dict in mechanic.py | Avoids dependency but mixes metadata with code; meta.yaml is the locked decision (D-15) |
| ABC (stdlib) | Protocol (typing) | ABC enforces inheritance which is appropriate here -- mechanics ARE-A base type; Protocol is structural subtyping which is too loose |

**Installation:**
```bash
uv add pyyaml
```

## Architecture Patterns

### Recommended Project Structure
```
src/token_world/mechanic/
    __init__.py          # Public API: Mechanic, MechanicContext, CheckResult, etc.
    protocol.py          # Mechanic ABC, CheckResult dataclass
    context.py           # MechanicContext wrapping KnowledgeGraph
    matchers.py          # Declarative matcher primitives for involuntary mechanics
    engine.py            # Chain execution engine (evaluate matchers, recurse, trace)
    trace.py             # ExecutionTrace tree dataclass
    registry.py          # File-scanning registry, git version queries
    loader.py            # Dynamic mechanic loading from folders (importlib)

tests/test_mechanic/
    conftest.py          # MechanicContext fixtures, test graph builders
    test_protocol.py     # Mechanic ABC contract tests
    test_context.py      # DSL primitive tests
    test_matchers.py     # Matcher evaluation tests
    test_engine.py       # Chain execution, depth limit, cycle detection
    test_trace.py        # Execution trace structure tests
    test_registry.py     # Registry scanning, git history tests
    test_seed_movement.py
    test_seed_observation.py
    test_seed_environmental.py
```

### Pattern 1: Mechanic Protocol (ABC)
**What:** Abstract base class defining the mechanic contract
**When to use:** Every mechanic inherits from this
**Example:**
```python
# Source: Derived from D-01, D-03, D-04, D-07, D-08
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass(frozen=True)
class CheckResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)

class Mechanic(ABC):
    """Base class for all mechanics."""
    id: str           # Class-level, required (D-03)
    description: str  # Class-level, required (D-03)
    voluntary: bool = True  # Default True (D-07)

    @abstractmethod
    def check(self, ctx: MechanicContext) -> CheckResult:
        """Check preconditions. Return CheckResult."""
        ...

    @abstractmethod
    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        """Apply side effects. Return list of Mutations."""
        ...

    def watches(self) -> list[Matcher]:
        """Declare mutation matchers for involuntary mechanics.

        Override in involuntary mechanics. Default returns empty
        (voluntary mechanics don't watch anything).
        """
        return []
```

### Pattern 2: MechanicContext (DSL Wrapper)
**What:** Context object that wraps KnowledgeGraph and provides DSL methods
**When to use:** Passed to every mechanic's check() and apply()
**Example:**
```python
# Source: Derived from D-05, D-06
from token_world.graph import KnowledgeGraph, Mutation

class MechanicContext:
    """DSL context for mechanic execution.

    Wraps KnowledgeGraph to provide a clean API for mechanics.
    Mechanics NEVER access KnowledgeGraph directly.
    """
    def __init__(self, graph: KnowledgeGraph, *, actor: str, target: str) -> None:
        self._graph = graph
        self.actor = actor    # D-06
        self.target = target  # D-06

    # --- Query DSL ---
    def query_node(self, node_id: str, property: str | None = None) -> Any:
        """Query node properties. Delegates to KnowledgeGraph.query()."""
        return self._graph.query(node_id, property)

    def query_neighbors(self, node_id: str) -> list[str]:
        """Get neighbors. Delegates to KnowledgeGraph.neighbors()."""
        return self._graph.neighbors(node_id)

    def has_node(self, node_id: str) -> bool:
        return self._graph.has_node(node_id)

    def has_edge(self, src: str, dst: str) -> bool:
        return self._graph.has_edge(src, dst)

    def find_nodes(self, **filters: Any) -> list[str]:
        """Find nodes matching property filters."""
        return self._graph.nodes(**filters)

    # --- Mutation DSL ---
    def mutate(self, node_id: str, property: str, value: Any) -> Mutation:
        """Set a property. Delegates to KnowledgeGraph.set()."""
        return self._graph.set(node_id, property, value)

    def add_node(self, node_id: str, *, node_type: str, **props: Any) -> Mutation:
        return self._graph.add_node(node_id, node_type=node_type, **props)

    def remove_node(self, node_id: str) -> Mutation:
        return self._graph.remove_node(node_id)

    def add_edge(self, src: str, dst: str, **props: Any) -> Mutation:
        return self._graph.add_edge(src, dst, **props)

    def remove_edge(self, src: str, dst: str) -> Mutation:
        return self._graph.remove_edge(src, dst)
```

### Pattern 3: Declarative Matchers for Involuntary Mechanics
**What:** Matcher objects that declaratively specify which mutations an involuntary mechanic cares about
**When to use:** Returned by `watches()` on involuntary mechanics
**Recommendation (Claude's Discretion):**
```python
# Source: Designed per D-08 constraints
from dataclasses import dataclass

@dataclass(frozen=True)
class PropertyChangeMatcher:
    """Matches when a specific property changes on any node (or a filtered set)."""
    property_name: str
    node_type: str | None = None  # Optional filter: only "agent" or "entity"

@dataclass(frozen=True)
class EdgeMatcher:
    """Matches when an edge is added or removed."""
    event_type: str  # "add_edge" or "remove_edge"
    edge_label: str | None = None  # Optional filter on edge properties

@dataclass(frozen=True)
class NodeMatcher:
    """Matches when a node is added or removed."""
    event_type: str  # "add_node" or "remove_node"
    node_type: str | None = None

# Union type for all matchers
Matcher = PropertyChangeMatcher | EdgeMatcher | NodeMatcher
```

**Matching logic:** After apply() produces mutations, the engine iterates registered involuntary mechanics. For each, it checks if ANY of its matchers match ANY of the produced mutations. A match means the mechanic's check() is called (which may still reject). This is O(involuntary_mechanics * mutations * matchers_per_mechanic) but with small numbers this is fine -- optimization deferred to when needed.

### Pattern 4: Chain Execution Engine
**What:** Recursively executes involuntary mechanics triggered by mutations
**When to use:** After every apply() call
**Key design:**
```python
@dataclass
class TraceNode:
    """A single node in the execution trace tree."""
    mechanic_id: str
    actor: str
    target: str
    check_result: CheckResult
    mutations: list[Mutation]
    children: list[TraceNode]  # Mechanics triggered by this one's mutations

@dataclass
class ExecutionTrace:
    """Full execution trace for a single action."""
    root: TraceNode
    total_mechanics_executed: int
    max_depth_reached: int
    truncated: bool  # True if max depth was hit
```

**Chain execution algorithm:**
1. Execute initial mechanic's apply() -> get mutations
2. Collect all mutations into a batch
3. For each registered involuntary mechanic, check if any matcher matches any mutation in the batch
4. For matching mechanics: call check(), if passed call apply()
5. Collect new mutations from step 4
6. If new mutations exist and depth < max_depth: recurse from step 3
7. Cycle detection: track (mechanic_id, target) pairs per chain; skip if already seen
8. Build trace tree as execution proceeds

### Pattern 5: Registry with Git Versioning
**What:** Scans mechanic folders, loads metadata, queries git for history
**When to use:** CLI commands, programmatic mechanic discovery
```python
import subprocess
import importlib.util

def _git_log_for_path(universe_dir: Path, mechanic_path: Path, limit: int = 10) -> list[dict]:
    """Get git history for a mechanic folder."""
    result = subprocess.run(
        ["git", "log", f"--max-count={limit}", "--format=%H|%ai|%s",
         "--", str(mechanic_path.relative_to(universe_dir))],
        cwd=universe_dir,
        capture_output=True, text=True
    )
    # Parse output into list of {hash, date, message}
    ...

def _load_mechanic_class(mechanic_dir: Path) -> type[Mechanic]:
    """Dynamically load a Mechanic subclass from mechanic.py."""
    spec = importlib.util.spec_from_file_location(
        f"mechanic_{mechanic_dir.name}",
        mechanic_dir / "mechanic.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Find the Mechanic subclass in the module
    ...
```

### Anti-Patterns to Avoid
- **Direct KnowledgeGraph access in mechanics:** Always go through MechanicContext. This is the critical invariant -- it allows future sandboxing and ensures mechanics are testable in isolation.
- **Mutable state in mechanics:** Mechanics should be stateless. All state lives in the graph. Mechanic instances should be reusable across multiple invocations.
- **Implicit mechanic registration:** Don't use decorators or import-time registration. The registry scans folders explicitly -- this is deterministic and debuggable.
- **Polling all mechanics:** Don't check every involuntary mechanic against every mutation. Use the matcher system (D-08) to pre-filter.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Custom parser | PyYAML 6.0.3 | meta.yaml is human-edited; YAML parsing is deceptively complex |
| Dynamic module loading | Custom import system | `importlib.util` (stdlib) | Standard Python mechanism for loading modules from file paths |
| Git history queries | Custom git parsing | `subprocess.run(["git", "log", ...])` | Git CLI is the stable interface; no need for gitpython dependency |
| CLI framework | Argparse from scratch | Click (already installed) | Existing CLI uses Click; extend the group |
| Cycle detection in chains | Custom graph traversal | Set of `(mechanic_id, target)` tuples | Simple and correct; no need for a graph library |

**Key insight:** The mechanic framework is mostly protocol and plumbing. The complexity is in getting the abstractions right, not in any single library. The only new dependency needed is PyYAML.

## Common Pitfalls

### Pitfall 1: Mutation Accumulation in Chain Execution
**What goes wrong:** Each chain step produces mutations that modify the graph. If a later step fails or the chain is truncated, the graph has partial mutations from the chain.
**Why it happens:** Mutations are applied directly to KnowledgeGraph in real-time.
**How to avoid:** This is actually the desired behavior per the design -- mutations ARE applied as they happen. The execution trace records everything. If rollback is needed, use the snapshot system. The engine should NOT try to buffer/commit mutations atomically -- that adds complexity without value in v1.
**Warning signs:** Tests that assume mutations are atomic across a chain.

### Pitfall 2: Infinite Chain Loops
**What goes wrong:** Mechanic A triggers B which triggers A which triggers B...
**Why it happens:** Two involuntary mechanics watching each other's output.
**How to avoid:** D-09 specifies max depth (default 10) and cycle detection. Cycle detection should track `(mechanic_id, target)` pairs -- the SAME mechanic on the SAME target in one chain is a cycle. Different targets are OK (fire spreading to multiple entities is not a cycle).
**Warning signs:** Tests hitting depth limit unexpectedly.

### Pitfall 3: importlib Module Caching
**What goes wrong:** After loading a mechanic module, Python caches it in `sys.modules`. Reloading a modified mechanic (e.g., after git checkout of a different version) returns stale code.
**Why it happens:** Python's module import system caches aggressively.
**How to avoid:** Use unique module names per load (e.g., `mechanic_{universe}_{id}_{hash}`) or don't cache -- always create fresh spec/module. For the registry's purpose (scanning on startup), this isn't a problem. It becomes a problem only if hot-reloading mechanics.
**Warning signs:** Mechanic changes not taking effect.

### Pitfall 4: Git Subprocess in Tests
**What goes wrong:** Tests that query git history fail because the test's temp directory isn't a git repo.
**Why it happens:** Registry git queries assume they're inside a universe's git repo.
**How to avoid:** Registry tests need a fixture that creates a temp git repo, adds mechanic folders, and commits them. Or mock subprocess calls. The former is more reliable.
**Warning signs:** `fatal: not a git repository` errors in test output.

### Pitfall 5: Matcher Evaluation Performance
**What goes wrong:** O(involuntary_mechanics * mutations * matchers) evaluation after every apply().
**Why it happens:** Brute-force matching.
**How to avoid:** For v1, this is fine -- the number of involuntary mechanics and mutations per tick will be tiny. If it becomes a problem later, build an index from property_name -> list[mechanic]. Don't optimize prematurely.
**Warning signs:** Noticeable lag in chain execution with many mechanics.

### Pitfall 6: Context `actor`/`target` for Chain-Triggered Mechanics
**What goes wrong:** When an involuntary mechanic is triggered by a chain, what should actor/target be?
**Why it happens:** The original actor triggered the first mechanic, but the involuntary mechanic needs a different target (the node whose mutation triggered it).
**How to avoid:** For chain-triggered mechanics: `actor` stays the same (the original agent), `target` becomes the node that triggered the matcher. The engine must set these correctly before calling check/apply on chain-triggered mechanics.
**Warning signs:** Involuntary mechanics getting wrong actor/target.

## Code Examples

### Seed Mechanic: Movement (Voluntary)
```python
# Source: Derived from D-11, D-01, D-05
class MovementMechanic(Mechanic):
    id = "movement"
    description = "Agent moves between connected locations"
    voluntary = True

    def check(self, ctx: MechanicContext) -> CheckResult:
        # Actor must exist and have a location
        try:
            actor_props = ctx.query_node(ctx.actor)
        except KeyError:
            return CheckResult(passed=False, reasons=["Actor does not exist"])

        location = actor_props.get("location")
        if not location:
            return CheckResult(passed=False, reasons=["Actor has no location"])

        # Target must be a connected location
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["Target location does not exist"])

        if not ctx.has_edge(location, ctx.target):
            return CheckResult(passed=False, reasons=[
                f"No path from {location} to {ctx.target}"
            ])

        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return [ctx.mutate(ctx.actor, "location", ctx.target)]
```

### Seed Mechanic: Environmental Reaction (Involuntary)
```python
# Source: Derived from D-11, D-12, D-07, D-08
class EnvironmentalReactionMechanic(Mechanic):
    id = "environmental_reaction"
    description = "Fire spreads to adjacent flammable entities when temperature changes"
    voluntary = False

    def watches(self) -> list[Matcher]:
        return [PropertyChangeMatcher(property_name="temperature")]

    def check(self, ctx: MechanicContext) -> CheckResult:
        # Target (node with temp change) must have high temperature
        try:
            temp = ctx.query_node(ctx.target, "temperature")
        except KeyError:
            return CheckResult(passed=False, reasons=["No temperature"])

        if temp < 100:
            return CheckResult(passed=False, reasons=["Temperature too low for fire spread"])

        # Must have flammable neighbors
        neighbors = ctx.query_neighbors(ctx.target)
        flammable = [n for n in neighbors
                     if ctx.query_node(n).get("flammable", False)]
        if not flammable:
            return CheckResult(passed=False, reasons=["No flammable neighbors"])

        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        neighbors = ctx.query_neighbors(ctx.target)
        mutations = []
        for n in neighbors:
            props = ctx.query_node(n)
            if props.get("flammable", False) and props.get("temperature", 0) < 100:
                mutations.append(ctx.mutate(n, "temperature", 150))
                mutations.append(ctx.mutate(n, "on_fire", True))
        return mutations
```

### meta.yaml Schema (Claude's Discretion - D-16)
```yaml
# Recommended meta.yaml content -- lightweight per D-16
id: movement
description: Agent moves between connected locations
voluntary: true
tags:
  - spatial
  - core
```

**Rationale:** id, description, and voluntary are the minimum the registry needs for listing and filtering. Tags enable future query-by-tag. No version field (git is the version system per D-13). No dependencies or configuration -- keep it minimal.

### Mechanic Folder Location (Claude's Discretion)
**Recommendation:** Seed mechanics are bundled as package data under `src/token_world/mechanic/seeds/` and copied into the universe `mechanics/` folder during `scaffold_universe()`. This way:
1. Seeds are part of the installable package (testable in CI)
2. Each universe has its own copy that can be modified independently
3. The registry only scans universe folders -- no special "built-in" path logic

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `typing.Protocol` for structural typing | ABC for nominal typing | N/A (design choice) | ABC enforces inheritance, which is correct here -- mechanics must explicitly opt in |
| `importlib.import_module` | `importlib.util.spec_from_file_location` | Python 3.4+ | spec_from_file_location works with arbitrary file paths, not just installed packages |
| `os.popen("git log")` | `subprocess.run(["git", "log"])` | Python 3.5+ | subprocess.run is the modern interface with proper error handling |

**Deprecated/outdated:**
- `imp` module: Replaced by `importlib` in Python 3.12. Do not use.
- `yaml.load()` without Loader: PyYAML 6.0+ requires explicit `yaml.safe_load()` to avoid arbitrary code execution.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PyYAML 6.0.3 is the latest stable version | Standard Stack | Low -- version is verified via pip index |
| A2 | `importlib.util.spec_from_file_location` is sufficient for dynamic mechanic loading without import side effects | Architecture Patterns | Medium -- if mechanics import heavy dependencies, loading could be slow or have side effects |
| A3 | O(involuntary_mechanics * mutations) matching is acceptable for v1 | Pitfall 5 | Low -- universe will have few mechanics initially |
| A4 | Cycle detection via `(mechanic_id, target)` pairs is sufficient | Pitfall 2 | Medium -- more complex cycles (A->B->C->A with different targets) might not be caught; but max depth is the safety net |

## Open Questions (RESOLVED)

1. **Seed mechanic bundling strategy** (RESOLVED)
   - What we know: Seeds need to exist in universe `mechanics/` folders. They also need to be testable in the main package.
   - Resolution: Copy during scaffold. Seeds live in `src/token_world/mechanic/seeds/` for development/testing, and `scaffold_universe()` copies them into each new universe's `mechanics/` folder via `shutil.copytree`. The registry only ever scans universe folders. Implemented in Plan 02 Task 1.

2. **Chain execution: target assignment for involuntary mechanics** (RESOLVED)
   - What we know: D-06 says context has actor and target. For chain-triggered mechanics, the target should be the node whose mutation triggered the match.
   - Resolution: For edge mutations (target format "src->dst"), use the source node as the target. For property/node mutations, use mutation.target directly. This convention is implemented in Plan 01 Task 1 engine.py `_evaluate_chain` step 3.

3. **query-graph output format** (RESOLVED)
   - What we know: D-19 specifies filters but not output format.
   - Resolution: Default to human-readable tabular output via Click's echo (one line per node: `id: prop1=val1, prop2=val2`). `--json` flag for machine-readable JSON array output. `--stats` mode outputs counts only. Implemented in Plan 03 Task 2.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.12+ | -- |
| git | Mechanic versioning (D-13) | Yes | 2.25.1 | -- |
| PyYAML | meta.yaml parsing | No | -- | Must install: `uv add pyyaml` |
| NetworkX | KnowledgeGraph | Yes | 3.6.1 | -- |
| Click | CLI | Yes | 8.3.2 | -- |
| pytest | Testing | Yes | 9.0+ | -- |

**Missing dependencies with no fallback:**
- PyYAML: Required for meta.yaml. Must be added to pyproject.toml.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_mechanic/ -x -q` |
| Full suite command | `uv run pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MECH-01 | Mechanic ABC enforces check/apply contract | unit | `uv run pytest tests/test_mechanic/test_protocol.py -x` | No -- Wave 0 |
| MECH-02 | MechanicContext DSL methods delegate to KnowledgeGraph correctly | unit | `uv run pytest tests/test_mechanic/test_context.py -x` | No -- Wave 0 |
| MECH-05 | Mechanic folder structure loads correctly; git history retrievable | integration | `uv run pytest tests/test_mechanic/test_registry.py -x` | No -- Wave 0 |
| MECH-06 | Registry scans folders, lists/queries mechanics | unit | `uv run pytest tests/test_mechanic/test_registry.py -x` | No -- Wave 0 |
| TEST-01 | Seed mechanics pass precondition checks and produce correct mutations | unit | `uv run pytest tests/test_mechanic/test_seed_*.py -x` | No -- Wave 0 |
| AUTO-03 | CLI commands execute correctly | integration | `uv run pytest tests/test_mechanic/test_cli.py -x` | No -- Wave 0 |
| D-09 | Chain execution with depth limit and cycle detection | unit | `uv run pytest tests/test_mechanic/test_engine.py -x` | No -- Wave 0 |
| D-12 | Environmental reaction triggers chain from temperature change | integration | `uv run pytest tests/test_mechanic/test_seed_environmental.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_mechanic/ -x -q`
- **Per wave merge:** `uv run pytest -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_mechanic/__init__.py` -- package init
- [ ] `tests/test_mechanic/conftest.py` -- MechanicContext fixtures, graph builders for mechanic testing
- [ ] `tests/test_mechanic/test_protocol.py` -- ABC contract enforcement
- [ ] `tests/test_mechanic/test_context.py` -- DSL primitive delegation
- [ ] `tests/test_mechanic/test_matchers.py` -- Matcher evaluation
- [ ] `tests/test_mechanic/test_engine.py` -- Chain execution
- [ ] `tests/test_mechanic/test_registry.py` -- Registry scan + git history
- [ ] `tests/test_mechanic/test_seed_movement.py` -- Movement mechanic
- [ ] `tests/test_mechanic/test_seed_observation.py` -- Observation mechanic
- [ ] `tests/test_mechanic/test_seed_environmental.py` -- Environmental reaction + chain
- [ ] `tests/test_mechanic/test_cli.py` -- CLI commands
- [ ] PyYAML dependency: `uv add pyyaml`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A -- local hobby project |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | Yes | Pydantic/dataclass validation for CheckResult, Mutation. PyYAML safe_load for meta.yaml. |
| V6 Cryptography | No | N/A |

### Known Threat Patterns for Python mechanic loading

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Arbitrary code execution via mechanic.py | Elevation of Privilege | No sandboxing in v1 (explicit decision). importlib loads arbitrary Python. Accepted risk for hobby project. |
| YAML deserialization attack | Tampering | Always use `yaml.safe_load()`, never `yaml.load()` without SafeLoader |
| Path traversal in mechanic folder scanning | Information Disclosure | Validate mechanic paths are under universe `mechanics/` directory |
| Git command injection via mechanic names | Tampering | Sanitize mechanic IDs before passing to subprocess (no shell=True, use list args) |

## Sources

### Primary (HIGH confidence)
- `src/token_world/graph/knowledge_graph.py` -- Full KnowledgeGraph API verified via codebase read
- `src/token_world/graph/models.py` -- Mutation dataclass structure verified
- `src/token_world/cli.py` -- Existing Click CLI structure verified
- `src/token_world/universe/scaffold.py` -- Universe scaffolding structure verified
- `pyproject.toml` -- Current dependencies and versions verified
- Runtime imports -- Click 8.3.2, Pydantic 2.12.5, NetworkX 3.6.1 verified

### Secondary (MEDIUM confidence)
- `pip index versions pyyaml` -- 6.0.3 confirmed as latest [VERIFIED: pip index]
- Python stdlib `importlib.util` -- spec_from_file_location API [VERIFIED: stdlib, stable since 3.4]

### Tertiary (LOW confidence)
- None. All claims verified against codebase or runtime.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified against installed packages and pip index
- Architecture: HIGH -- derived directly from locked decisions (D-01 through D-20) and verified KnowledgeGraph API
- Pitfalls: HIGH -- derived from known Python patterns (importlib caching, subprocess in tests, YAML safe_load)
- Chain execution: MEDIUM -- algorithm design is sound but the matcher/target assignment edge cases (Open Question 2) need resolution during implementation

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable Python patterns, no fast-moving dependencies)
