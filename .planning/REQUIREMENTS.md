# Requirements: Token World

**Defined:** 2026-04-11
**Core Value:** The simulation engine reliably interprets agent actions, generates coherent mechanics as executable Python code, and maintains a consistent knowledge graph

## v1 Requirements

### Knowledge Graph

- [ ] **GRAPH-01**: Knowledge graph supports arbitrary node/edge properties without schema declaration
- [ ] **GRAPH-02**: New concepts (temperature, inventory, currency) emerge dynamically when mechanics create them
- [ ] **GRAPH-03**: Graph state persists to SQLite and survives process restarts
- [ ] **GRAPH-04**: Graph state can be snapshotted at any point for later rollback
- [ ] **GRAPH-05**: Graph can be restored to any previous snapshot
- [ ] **GRAPH-06**: Optional spatial index primitive (R-tree) for efficient spatial queries by mechanics
- [ ] **GRAPH-07**: Optional temporal index primitive for efficient time-range queries by mechanics

### Mechanic Framework

- [ ] **MECH-01**: Mechanic protocol defines check(preconditions) and apply(side effects) against the graph
- [ ] **MECH-02**: Framework provides DSL-like primitives for graph queries and mutations
- [ ] **MECH-03**: LLM generates valid Python mechanics using the framework from agent action context
- [ ] **MECH-04**: Generated mechanics are validated (syntax, AST checks) before execution
- [ ] **MECH-05**: Mechanic changes are versioned with full history
- [ ] **MECH-06**: Mechanics can be listed, inspected, and queried programmatically

### Simulation Engine

- [ ] **SIM-01**: Engine interprets resident agent text output into structured actions
- [ ] **SIM-02**: Engine matches structured actions to existing mechanics
- [ ] **SIM-03**: Engine triggers mechanic generation when no existing mechanic matches
- [ ] **SIM-04**: Engine executes matched/generated mechanic and applies side effects to graph
- [ ] **SIM-05**: Observations returned to agents are grounded in graph state (no hallucinated state)
- [ ] **SIM-06**: Simulation history log records actions, mechanics used, mutations, and observations
- [ ] **SIM-07**: Observations are contextually filtered — only relevant properties appear (e.g. temperature not shown when looking at a keyboard)
- [ ] **SIM-08**: Conservation laws enforced — matter/energy cannot be created from nothing; mechanics must respect fundamental constraints
- [ ] **SIM-09**: Action duration and attention threshold — long-running actions skip boring intermediate turns; engine only interrupts when significance exceeds agent's current attention level
- [ ] **SIM-10**: Attention/consciousness as a reusable mechanic pattern — sleep, daydreaming, drunkenness, autopilot all use the same interruption threshold infrastructure

### Resident Agent

- [ ] **AGENT-01**: Agent initialized with randomly generated personality
- [ ] **AGENT-02**: Agent interacts with environment via text actions and receives text observations
- [ ] **AGENT-03**: Agent memory persists across sessions via Claude Code SDK session resumption
- [ ] **AGENT-04**: Agent session can be forked from a previous point for simulation rollback

### Testing

- [ ] **TEST-01**: Unit tests for mechanic preconditions/side effects against small hand-crafted graphs
- [ ] **TEST-02**: Integration tests for multi-mechanic chains with realistic graph state
- [ ] **TEST-03**: Snapshot/restore round-trip tests verify graph and mechanic state integrity
- [ ] **TEST-04**: LLM-verifier regression tests check observation grounding against rubric (large/expensive, run on milestone boundaries)
- [ ] **TEST-05**: System prompt change detection triggers grounding regression tests
- [ ] **TEST-06**: Convenience graph builder utilities for concise test setup (reduce test maintenance cost)
- [ ] **TEST-07**: Playtest runner that executes N simulation turns and produces structured quality reports

### Agent Autonomy & Tooling

- [ ] **AUTO-01**: CLAUDE.md with architecture overview, critical constraints, validation protocols, and script catalog
- [ ] **AUTO-02**: Diagnostics filesystem — each simulation turn can dump system prompts, raw responses, and parsed output to inspectable files
- [ ] **AUTO-03**: CLI scripts for common operations (run simulation, inspect graph, list mechanics, run playtests) so agents don't need to compose commands
- [ ] **AUTO-04**: Mermaid diagram generation for graph visualization (agent can render and review multimodally)
- [ ] **AUTO-05**: Simulation playtest with edge-case injection (adversarial inputs, nonsense, repeats) at configurable rates
- [ ] **AUTO-06**: Quality scoring per simulation turn (grounding accuracy, mechanic validity, observation relevance)
- [ ] **AUTO-07**: Prompt/instruction change detection triggers automated regression validation

### Design Validation

- [ ] **DVAL-01**: Use case library covering spatial, social, resource, environmental, and edge-case interaction scenarios
- [ ] **DVAL-02**: Gap analysis — review use cases against architecture and requirements to surface missing mechanics or framework capabilities
- [ ] **DVAL-03**: Use case regression suite — key scenarios become executable integration tests that validate the core loop end-to-end

## v2 Requirements

### Multi-Agent

- **MULTI-01**: Multiple resident agents interacting in the same simulation
- **MULTI-02**: Agent-agent interaction mechanics (communication, trade, conflict)
- **MULTI-03**: Turn ordering and conflict resolution for concurrent actions

### Monitoring

- **MON-01**: Review agents observing simulation at bird's eye view
- **MON-02**: Dashboard for knowledge graph visualization
- **MON-03**: Temporal views (timeline of events and mechanic creation)

### Hardening

- **HARD-01**: Sandboxed mechanic execution (RestrictedPython)
- **HARD-02**: Mechanic coherence checking (new mechanics vs existing)
- **HARD-03**: Cost monitoring and circuit breakers for LLM usage
- **HARD-04**: Graph-based agent memory (inspectable, queryable)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Game adaptation / playable game | v1 is a simulation, not a game |
| Web UI / dashboard | Prove core loop first; CLI is sufficient |
| Visual output (images, maps) | Text-first simulation |
| Real-time simulation | Turn-based is simpler and sufficient |
| Civic simulation scenarios | Requires mature mechanics ecosystem |
| Contributor onboarding / CI/CD | Premature until core is stable |
| Distributed graph / sharding | Graph will be small for years |
| Authentication / multi-user | Local hobby project |
| Plugin system for mechanics | Framework IS the plugin API |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GRAPH-01 | Phase 1 | Pending |
| GRAPH-02 | Phase 1 | Pending |
| GRAPH-03 | Phase 1 | Pending |
| GRAPH-04 | Phase 1 | Pending |
| GRAPH-05 | Phase 1 | Pending |
| GRAPH-06 | Phase 3 | Pending |
| GRAPH-07 | Phase 3 | Pending |
| MECH-01 | Phase 2 | Pending |
| MECH-02 | Phase 2 | Pending |
| MECH-03 | Phase 4 | Pending |
| MECH-04 | Phase 4 | Pending |
| MECH-05 | Phase 2 | Pending |
| MECH-06 | Phase 2 | Pending |
| SIM-01 | Phase 5 | Pending |
| SIM-02 | Phase 5 | Pending |
| SIM-03 | Phase 5 | Pending |
| SIM-04 | Phase 5 | Pending |
| SIM-05 | Phase 5 | Pending |
| SIM-06 | Phase 5 | Pending |
| SIM-07 | Phase 5 | Pending |
| SIM-08 | Phase 5 | Pending |
| SIM-09 | Phase 7 | Pending |
| SIM-10 | Phase 7 | Pending |
| AGENT-01 | Phase 6 | Pending |
| AGENT-02 | Phase 6 | Pending |
| AGENT-03 | Phase 6 | Pending |
| AGENT-04 | Phase 6 | Pending |
| TEST-01 | Phase 2 | Pending |
| TEST-02 | Phase 4 | Pending |
| TEST-03 | Phase 1 | Pending |
| TEST-04 | Phase 6 | Pending |
| TEST-05 | Phase 6 | Pending |
| TEST-06 | Phase 1 | Pending |
| TEST-07 | Phase 6 | Pending |
| AUTO-01 | Phase 1 | Pending |
| AUTO-02 | Phase 4 | Pending |
| AUTO-03 | Phase 2 | Pending |
| AUTO-04 | Phase 3 | Pending |
| AUTO-05 | Phase 6 | Pending |
| AUTO-06 | Phase 6 | Pending |
| AUTO-07 | Phase 6 | Pending |
| DVAL-01 | Phase 3 | Pending |
| DVAL-02 | Phase 3 | Pending |
| DVAL-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 44 total
- Mapped to phases: 44
- Unmapped: 0

---
*Requirements defined: 2026-04-11*
*Last updated: 2026-04-11 after roadmap creation*
