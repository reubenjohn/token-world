# Architecture Patterns

**Domain:** LLM-powered procedural universe simulation
**Researched:** 2026-04-11

## Recommended Architecture

### High-Level Structure

```
+------------------+     action text      +--------------------+
|  Resident Agent  | ------------------> |  Simulation Engine  |
|  (LLM + memory)  | <------------------ |  (LLM + tools)      |
+------------------+     observation      +--------------------+
                                                |
                                    +-----------+-----------+
                                    |                       |
                              +-----v------+    +-----------v-----------+
                              |  Mechanic   |    |  Mechanic Generator   |
                              |  Registry   |    |  (LLM code gen)       |
                              +-----+------+    +-----------+-----------+
                                    |                       |
                              +-----v-----------------------v-----+
                              |        Mechanic Framework          |
                              |  (preconditions + side effects)    |
                              +-----+-----------------------------+
                                    |
                              +-----v------+
                              |  Knowledge  |
                              |  Graph      |
                              |  (NetworkX) |
                              +-----+------+
                                    |
                              +-----v------+
                              |  SQLite     |
                              |  Persistence|
                              +-------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With | Implementation |
|-----------|---------------|-------------------|----------------|
| Resident Agent | Generates actions based on personality/memory, receives observations | Simulation Engine (text in/out) | Anthropic SDK, Haiku model, system prompt with personality |
| Simulation Engine | Interprets actions, selects/triggers mechanics, formats observations | Agent, Mechanic Registry, Generator, Graph | Anthropic SDK, Sonnet/Haiku models, tool-use pipeline |
| Mechanic Registry | Stores and indexes mechanics by concept/trigger | Engine, Framework, SQLite | Python dict + SQLite persistence |
| Mechanic Generator | Generates new mechanic code when no existing mechanic matches | Engine, Framework | Anthropic SDK, Sonnet model, structured output |
| Mechanic Framework | Defines API for preconditions and side effects | All mechanic code, Graph | Pure Python classes and functions |
| Knowledge Graph | In-memory graph state with arbitrary properties | Framework, Persistence | NetworkX DiGraph |
| Persistence Layer | Durable storage of all state | Graph, Registry, Agent state | SQLite via stdlib sqlite3 |

### Data Flow

**Normal simulation step (existing mechanic):**
1. Agent outputs action text: "I try to light a fire with the sticks"
2. Engine classifies action: `{verb: "ignite", subject: "agent_1", object: "sticks_3", context: "fire_starting"}`
3. Engine queries registry for matching mechanics: finds `fire_starting` mechanic
4. Engine executes mechanic preconditions against graph: checks `sticks_3.flammable == true`
5. Mechanic applies side effects: creates `fire_7` node, sets `fire_7.temperature = 500`, adds edge `fire_7 -[located_at]-> clearing_2`
6. Persistence layer logs mutations as events
7. Engine formats observation grounded in new graph state: "The dry sticks catch fire. A small campfire crackles in the clearing, radiating warmth."
8. Agent receives observation, updates memory

**New mechanic step (no matching mechanic):**
1-2. Same as above
3. Engine queries registry: no matching mechanic found
4. Engine sends generation request to Mechanic Generator with: action context, relevant graph state, existing related mechanics
5. Generator produces Python code using framework API, returns structured output
6. Engine validates generated code (RestrictedPython compile, type check)
7. Engine executes new mechanic (same as steps 4-8 above)
8. New mechanic is persisted to registry with version 1

## Patterns to Follow

### Pattern 1: Mechanic as Pure Function

**What:** Mechanics are stateless functions that take graph state and return mutations. They never modify the graph directly.

**When:** Always. Every mechanic follows this pattern.

**Why:** Enables rollback (don't apply mutations), logging (record intended mutations), validation (check mutations before applying), and testing (assert on returned mutations without touching real graph).

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass
class Mutation:
    """A single graph mutation."""
    type: str  # "add_node", "add_edge", "set_property", "remove_node", etc.
    target: str  # node_id or edge tuple
    data: dict  # properties to set

class Mechanic(Protocol):
    """Interface for all mechanics."""
    name: str
    version: int
    triggers: list[str]  # concepts this mechanic handles

    def check(self, graph: nx.DiGraph, context: dict) -> bool:
        """Return True if preconditions are met."""
        ...

    def apply(self, graph: nx.DiGraph, context: dict) -> list[Mutation]:
        """Return list of mutations to apply. Do NOT modify graph directly."""
        ...
```

### Pattern 2: Graph Mutation via Event Log

**What:** Every graph change goes through a central mutator that logs the event before applying it.

**When:** Always. Never call `graph.add_node()` directly outside the mutator.

**Why:** Enables event sourcing, time-travel debugging, and audit trails.

```python
class GraphMutator:
    def __init__(self, graph: nx.DiGraph, event_store: EventStore):
        self.graph = graph
        self.event_store = event_store

    def apply_mutations(self, mutations: list[Mutation], source: str) -> int:
        """Apply mutations and log events. Returns event sequence number."""
        seq = self.event_store.next_sequence()
        for m in mutations:
            self._apply_single(m)
            self.event_store.log(seq, m, source)
        return seq

    def _apply_single(self, m: Mutation):
        if m.type == "add_node":
            self.graph.add_node(m.target, **m.data)
        elif m.type == "set_property":
            self.graph.nodes[m.target].update(m.data)
        # ... etc
```

### Pattern 3: Model Selection by Task

**What:** Use different Claude models for different tasks based on complexity and cost.

**When:** Every LLM call should explicitly choose its model.

**Why:** Cost efficiency. Haiku is roughly 10x cheaper than Sonnet. Classification tasks do not need Sonnet-level reasoning.

```python
MODELS = {
    "classify_action": "claude-haiku-4-5-20250315",
    "select_mechanic": "claude-haiku-4-5-20250315",
    "generate_mechanic": "claude-sonnet-4-5-20250514",
    "format_observation": "claude-haiku-4-5-20250315",
    "agent_personality": "claude-haiku-4-5-20250315",
}
```

### Pattern 4: Structured Output for All LLM Calls

**What:** Every LLM call that returns data (not prose) uses Pydantic models as structured output schemas.

**When:** Action classification, mechanic selection, mechanic generation, observation formatting.

**Why:** Eliminates JSON parsing errors. Anthropic's structured outputs guarantee schema compliance.

```python
from pydantic import BaseModel

class ActionClassification(BaseModel):
    verb: str
    subject: str
    object: str | None
    context: str
    confidence: float

class MechanicCode(BaseModel):
    name: str
    triggers: list[str]
    code: str  # Python source code string
    description: str
    precondition_summary: str
    side_effect_summary: str
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Direct Graph Modification

**What:** Mechanics calling `graph.add_node()` directly instead of returning mutations.

**Why bad:** Breaks event logging, makes rollback impossible, makes testing harder.

**Instead:** Mechanics return `list[Mutation]`, and the GraphMutator applies them.

### Anti-Pattern 2: Ungrounded Observations

**What:** Engine asks LLM to generate an observation without providing the current graph state as context.

**Why bad:** LLM will hallucinate world state that does not match the graph. Agents will act on false information.

**Instead:** Always include relevant graph context in the observation generation prompt. "Given these nodes and properties, describe what the agent observes."

### Anti-Pattern 3: Global Mechanic Namespace

**What:** Storing mechanics in a flat list, searching linearly for matches.

**Why bad:** As mechanics grow, lookup becomes slow and collisions increase.

**Instead:** Index mechanics by trigger concepts. Use a dict keyed by concept, with lists of mechanics per concept.

### Anti-Pattern 4: Monolithic Prompts

**What:** One massive system prompt for the simulation engine that handles classification, selection, generation, and observation.

**Why bad:** Expensive (all tokens sent on every call), hard to debug, impossible to use different models per task.

**Instead:** Separate LLM calls per task with focused prompts. Pipeline: classify -> select -> (generate?) -> execute -> observe.

### Anti-Pattern 5: Storing Generated Code as Pickled Functions

**What:** Using pickle to serialize generated mechanic functions.

**Why bad:** Security risk (pickle executes arbitrary code on load), version-fragile, not human-readable.

**Instead:** Store mechanics as source code strings. Compile with RestrictedPython and exec in controlled namespace at load time.

## Scalability Considerations

| Concern | v1 (1 agent) | v2 (5-10 agents) | Future (100+ agents) |
|---------|--------------|-------------------|----------------------|
| Graph size | Hundreds of nodes, in-memory | Thousands, still in-memory | Consider graph partitioning or embedded graph DB |
| Mechanic count | Tens | Hundreds | Index by concept, consider caching compiled mechanics |
| LLM calls per step | 3-5 (classify, select, generate?, observe) | 3-5 per agent, agents can share mechanics | Batch classification calls, cache selections |
| Persistence | Single SQLite file, synchronous writes | WAL mode, consider async writes | Separate read/write connections, periodic compaction |
| Agent memory | Simple text context | Per-agent memory tables | Summarization to bound context length |
| Cost | ~$0.01-0.05 per step (Haiku-heavy) | ~$0.10-0.50 per round | Model distillation, mechanic caching |

## Sources

- [NetworkX tutorial - attributes](https://networkx.org/documentation/stable/tutorial.html) - HIGH confidence
- [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - HIGH confidence
- [Anthropic tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use) - HIGH confidence
- [RestrictedPython overview](https://restrictedpython.readthedocs.io/) - HIGH confidence
- [Event sourcing patterns](https://eventsourcing.readthedocs.io/en/stable/topics/introduction.html) - MEDIUM confidence
