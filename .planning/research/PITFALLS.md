# Domain Pitfalls

**Domain:** LLM-powered procedural universe simulation
**Researched:** 2026-04-11

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Mechanic Incoherence Spiral

**What goes wrong:** Generated mechanics contradict each other. A "fire" mechanic says wood burns, a "shelter" mechanic lets you build with burning wood. The world becomes logically inconsistent.

**Why it happens:** Each mechanic is generated independently without sufficient context about existing mechanics that touch the same concepts.

**Consequences:** Agent experiences a nonsensical world. Trust in the simulation breaks. Fixing requires rewriting or removing mechanics, which may cascade.

**Prevention:**
- When generating a new mechanic, include all existing mechanics that reference the same graph nodes/properties in the generation prompt.
- Add a validation step: after generation, ask the LLM "does this mechanic contradict any of these existing mechanics?" with the relevant set.
- Start with a small seed set of manually written core mechanics (physics basics) to establish ground truth.

**Detection:** Log mechanic generation prompts and outputs. Periodically review for contradictions. Build a simple "mechanic coverage" view showing which properties each mechanic reads/writes.

### Pitfall 2: Ungrounded Observation Drift

**What goes wrong:** The engine generates observations that do not match graph state. Agent acts on hallucinated information, creating a feedback loop of false state.

**Why it happens:** LLM generates plausible-sounding descriptions without being constrained by actual graph data. Observation prompt does not include enough graph context, or includes stale context.

**Consequences:** The simulation becomes a creative writing exercise rather than a grounded simulation. The knowledge graph becomes irrelevant.

**Prevention:**
- Every observation MUST be generated from a template that includes the current state of all relevant graph nodes.
- Consider a two-step process: (1) extract relevant facts from graph, (2) generate natural language from those facts.
- Add a grounding check: after generating observation, verify each claim against the graph.

**Detection:** Periodically sample observations and manually verify against graph state. Build a "grounding score" metric.

### Pitfall 3: Generated Code Execution Escapes

**What goes wrong:** A generated mechanic accesses the filesystem, makes network calls, or modifies Python internals through RestrictedPython gaps.

**Why it happens:** RestrictedPython is not a complete sandbox. It blocks common dangerous patterns but edge cases exist (e.g., CVE-2025-22153 with try/except*). LLMs can generate creative code that exploits gaps.

**Consequences:** Security breach. Data corruption. Unpredictable system behavior.

**Prevention:**
- RestrictedPython as first defense (compile-time restriction).
- Controlled namespace: only inject the mechanic framework API and safe builtins into the exec namespace. No `os`, `sys`, `subprocess`, `socket`, `importlib`.
- Validate generated code AST before execution: check for attribute access patterns that indicate escape attempts.
- Consider subprocess isolation for mechanics that fail RestrictedPython compilation.
- Pin RestrictedPython version and monitor CVEs.

**Detection:** Log all mechanic executions. Monitor for unexpected exceptions. Periodically audit generated mechanic code.

### Pitfall 4: Graph State Corruption Without Recovery

**What goes wrong:** A mechanic applies malformed mutations (wrong types, missing required properties, orphaned edges), and the corruption propagates through subsequent steps.

**Why it happens:** Generated code produces mutations that pass basic validation but create logically invalid graph states. No invariant checking on the graph.

**Consequences:** Cascading errors. Hard to diagnose because corruption happened N steps ago. Must manually find and fix or roll back to a known-good state.

**Prevention:**
- Define graph invariants (e.g., every edge connects existing nodes, certain properties must be numeric) and check after every mutation batch.
- Validate mutations BEFORE applying: check that target nodes exist, property types match expectations.
- Event log + snapshots enable rollback to last known-good state.
- Consider "dry run" mode: apply mutations to a graph copy, validate, then apply to real graph.

**Detection:** Graph invariant checks after each simulation step. Log validation failures.

## Moderate Pitfalls

### Pitfall 5: Token Cost Explosion

**What goes wrong:** Cost per simulation step grows unbounded as the graph and mechanic set grow, because more context must be included in each LLM call.

**Prevention:**
- Use Haiku for simple tasks (classification, matching). Only use Sonnet for generation.
- Limit graph context to relevant subgraph, not full dump.
- Summarize mechanic descriptions rather than including full source code in selection prompts.
- Set hard token budgets per call type. Monitor and alert on cost per step.
- Cache mechanic selections for repeated action patterns.

### Pitfall 6: Mechanic Framework API Instability

**What goes wrong:** The mechanic framework API changes, breaking all previously generated mechanics.

**Prevention:**
- Design the framework API carefully before generating any mechanics. Iterate on it with manually-written test mechanics first.
- Version the framework API. When it changes, regenerate affected mechanics (or write migration code).
- Keep the API surface small: graph query, graph mutation, and context access. Fewer functions = fewer breaking changes.

### Pitfall 7: Agent Memory Explosion

**What goes wrong:** Agent conversation history grows without bound, eventually exceeding context limits or becoming too expensive.

**Prevention:**
- Implement a memory management strategy from the start: recent history (last N turns) + summarized long-term memory.
- Store full history in SQLite for replay, but only include a summary in the LLM prompt.
- Set a maximum context budget for agent memory (e.g., 2000 tokens).

### Pitfall 8: Mechanic Naming Collisions

**What goes wrong:** Two independently generated mechanics claim the same trigger concepts and conflict with each other.

**Prevention:**
- Before generating a new mechanic, always check the registry for existing mechanics with overlapping triggers.
- When a conflict is found, present both to the LLM and ask it to either merge or specialize them.
- Use specific trigger naming: `fire_starting_with_sticks` not just `fire`.

### Pitfall 9: Over-Engineering the Persistence Layer

**What goes wrong:** Building a full event-sourcing framework with projections, read models, and CQRS for what is fundamentally a small hobby project.

**Prevention:**
- Start with the simplest thing: JSON snapshots + append-only event table.
- Do not build read projections. Query the in-memory graph directly.
- Do not build CQRS. Single writer, single reader.
- Add complexity only when the simple approach breaks.

## Minor Pitfalls

### Pitfall 10: Brittle Action Parsing

**What goes wrong:** Agent says something the classifier cannot parse, engine falls through to a "I don't understand" response too often.

**Prevention:** Design a generous classifier that maps to broad categories, then narrow within those. Include a "general_interaction" catch-all that at least acknowledges the action.

### Pitfall 11: Empty World Bootstrap Problem

**What goes wrong:** Agent spawns in an empty graph with no objects, no mechanics, no concepts. Nothing to interact with. Engine cannot ground anything.

**Prevention:** Create a small seed world: a location, a few objects with basic properties, and 2-3 core mechanics (movement, observation, basic interaction). This bootstraps the first meaningful agent-world interaction.

### Pitfall 12: Testing Generated Code

**What goes wrong:** No way to verify that generated mechanics actually work correctly beyond "it did not crash."

**Prevention:** Each generated mechanic should come with test scenarios (part of the generation prompt). After generation, run the test scenarios against a test graph. If tests fail, regenerate or flag for human review.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Knowledge Graph setup | Over-engineering schema (ironic given schema-less goal) | Start with zero schema. Let mechanics define what properties exist. |
| Mechanic Framework | API too complex, too many primitives | Start with 3 operations: query_node, query_neighbors, mutate. Add more only when needed. |
| Mechanic Generation | LLM generates code that does not use the framework correctly | Include 3-4 example mechanics in the generation prompt. Use structured output for the code structure. |
| Simulation Engine | Trying to handle every edge case in v1 | Happy path first. Unknown actions get a generic "nothing happens" response. Iterate. |
| Persistence | Building replay/rollback UI before the data is there | Build the event log and snapshot data model first. UI/tooling comes after the loop works. |
| Agent | Personality feels flat or repetitive | Invest in the personality prompt. Include specific quirks, speech patterns, goals. Test with multiple personas. |

## Sources

- [RestrictedPython CVE-2025-22153](https://pypi.org/project/RestrictedPython/) - HIGH confidence
- [LLM sandbox best practices](https://amirmalik.net/2025/03/07/code-sandboxes-for-llm-ai-agents) - MEDIUM confidence
- [Setting up secure Python sandbox for LLM agents](https://dida.do/blog/setting-up-a-secure-python-sandbox-for-llm-agents) - MEDIUM confidence
- [Event sourcing patterns](https://eventsourcing.readthedocs.io/en/stable/topics/introduction.html) - MEDIUM confidence
- [Automated KG pipeline with LangGraph/NetworkX](https://kiadev.net/news/2025-05-15-automated-knowledge-graph-pipeline-langgraph-networkx) - MEDIUM confidence
