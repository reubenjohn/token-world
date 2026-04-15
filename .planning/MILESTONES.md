# Project Milestones: Token World

## v1.2 Quality + Depth (Shipped: 2026-04-15)

**Phases completed:** 19 phases, 79 plans, 92 tasks

**Key accomplishments:**

- Python src-layout package with XDG path resolution, UniverseManager CRUD (create/load/list/delete via python-slugify + SQLite), and Click CLI entry point
- Universe scaffold with CLAUDE.md template, AGENTS.md symlink, .mcp.json, git init, and MCP stdio server stub declaring 4 tools
- Mutation-mediated KnowledgeGraph wrapping NetworkX DiGraph with claim_id identity, event logging, SQLite persistence, and GraphBuilder test infrastructure
- Graph snapshot/restore with SQLite persistence, count-based retention (50 max), event compaction, and round-trip integrity verification
- Updated CLAUDE.md with graph architecture overview, conventions, validation protocols, script catalog, and critical constraints so any agent can work autonomously
- 1. [Rule 1 - Bug] Engine multi-target firing
- 1. [Rule 1 - Bug] Fixed monkeypatch target for CLI tests
- rtree dependency added, viz + use_cases packages scaffolded, and 10 Wave 0 test files landed — every Phase 3 capability now has a verify command waiting for its feature.
- R-tree-backed SpatialIndex exposed via lazy `ctx.spatial` accessor — 2D nearest/within/intersects queries with node_type+subtype filters, malformed-position tolerance, and zero-cost-when-unused semantics.
- Read-only `TemporalIndex` over EventStore + graph_events SQLite — query_history, query_changes, find_state_at_tick, last_change — exposed via lazy `ctx.temporal` accessor with zero-cost-when-unused and SQL-injection defense baked in.
- `token-world viz-graph` ships end-to-end: filtered ego-graph extraction, Mermaid flowchart emission with label/ID escaping, 150-node cap, and a 119-line user guide — rendered cleanly by `mmdc` on the first try.
- Use-case library skeleton shipped — README, template, and 5 category manifests pre-assign 35 stable UC IDs with no-seed-mechanic flags; Wave 2 can now fan out with zero collisions.
- Files created:
- Aggregated 104 inline gaps across 35 UCs into 5 CATEGORY-SUMMARY.md files (80 deduplicated entries), confirmed every UC's setup executes cleanly, and transitioned all 35 UCs from draft to reviewed.
- Synthesised 80 Wave-3 category-scoped gaps into 68 canonical cross-phase gaps with stable IDs, four-layer organisation, and three-way dispositions — transitioning the Wave-0 schema test from SKIPPED to PASSED and delivering Phase 3 success criterion #2 (DVAL-02).
- Gap closure for UAT#3: replaced `# type: ignore[return-value]` on `GraphPersistence.save_snapshot` with `typing.cast(int, …)`, cast the two `KnowledgeGraph` snapshot call sites through the `Any`-typed `_persistence` attribute, and added a pytest regression guard that shells out to mypy — `uv run mypy src/token_world/graph/` now reports "Success: no issues found in 8 source files".
- escape_label now entity-escapes `<` and `>` at the emission boundary, neutralising XSS-shaped payloads (`<script>`, `<img onerror=...>`, `<iframe>`) before they reach any downstream Mermaid renderer, while preserving genuine newline-to-`<br/>` rendering.
- `validate_frontmatter` now enforces the fixed 6-kind `graph_assertion` vocabulary (`has_node`, `has_edge`, `has_property`, `property_equals`, `not_has_edge`, `not_has_property`) at load time — closes UAT Test 8 schema-rot gap before Phase 04 harness consumes these UCs as integration fixtures.
- 1. [Rule 1 - Bug] mypy list[type] doesn't know `cls.id`
- 1. [Rule 1 - Bug] ``status`` stayed at the ``"pending"`` placeholder.
- 1. [Rule 2 - Style] Ruff format drift on newly authored skeleton code.
- Involuntary.
- 1. [Rule 3 - Blocking] Registry seed-universe test pinned the

6-seed list from 04-06.

- Five object-interaction seed mechanics (trade/give/craft/consume/pickup) with shared _count_holds + _refuse_with_narrative helpers; six UCs flipped to pass; full suite green.
- Three real social/belief mechanics (tell/teach/belief_update) + two framework-gap stubs (persuade/cooperate) per D-38; harness blocked_by routing wired end-to-end so UC-O02 surfaces GAP-ENG03 and UC-O06 surfaces GAP-ENG05; three UCs flipped to pass; full suite green at 686/15s/3xf.
- Two resource seed mechanics (MECH17 degrade, MECH18 fungible_pay) plus a backtracking _subset_sum helper; UC-R06 flipped yield -> pass; UC-R05 stays blocked with a refined dual-blocker rationale documented inline; full suite green at 722/16s/1xf.
- Five environmental seed mechanics (fire_spread/decay_tick/illumination/contagion real + weather_reaction D-38 stub); three UCs flipped to pass (V01/V06/V07); two stubs-block (V02/V04 via GAP-ENG09); one decision-tree blocked (V03 via GAP-ENG07); full suite green at 782/14s/0xf (+60 unit tests, -2 skips, -1 xfail from baseline).
- What worked:
- Locked the 7-field `YieldSignal` contract (frozen+slots dataclass with sort-stable JSON round-trip + version-rejecting `from_json` guard), shipped the throwaway `EngineStub` that fabricates validated instances, installed `claude-agent-sdk>=0.1.58`, and stood up the operator test tree with the `integration` pytest marker default-excluded.
- Operator-side `tick_<id>/operator/` subfolder substrate: atomic writers for yield_signal/validation/diff, append-only JSONL transcript, schema-versioned resume_outcome, and a sole-sanctioned reader (D-16) wired into Phase 4's DiagnosticsSink via `open_operator_session(tick_id)`.
- Shipped `OperatorHarness` — the Agent SDK driver that catches a YieldSignal, spawns the Opus mechanic-authoring subagent (via `AgentDefinition` + `mcp__validation__validate_mechanic` in-process @tool), captures every authoring attempt + per-attempt validation report into operator diagnostics, and parses the outer model's final JSON into an `OperatorResult`. Real-Opus integration test passes end-to-end at $1.15 / 23 turns / 4m43s.
- Shipped 4 new Click commands (`run-tick`, `inspect-yield`, `resume-tick`, `replay-tick`) that surface the Agent-SDK operator harness through a "type one word and go" developer interface. Universe resolution follows slug > env > cwd > error; `--stub KEY=VALUE` fabricates yields with BLOCKER-3 persistence semantics; path-traversal and stub-key whitelisting enforced. Zero new MCP tools (UNIV-03 preserved).
- Closed Phase 4.1 on the dev-UX side: scaffolded universes now ship `.claude/agents/mechanic-author.md` (Opus, tools whitelist excluding `Agent`) with its body sourced from the same `mechanic_author_prompt()` the programmatic harness uses — structural prompt-drift immunity (T-04.1-22). CLAUDE.md gains an Operator Flow section and drops stale `Not yet implemented` stamps. VALIDATION.md is audit-ready (nyquist_compliant: true, 12-row per-task map, marker canonicalised to `integration`). docs/design/architecture.md gains a Phase 4.1 Mermaid flowchart and key-contracts summary.
- 1. [Rule 1 - Bug] Migrated contagion.py from import random to ctx.rng
- 1. [Rule 1 - Bug] _node_type_matches checks type and subtype independently
- 1. [Rule 1 - Bug] CheckResult uses reasons: list[str], not narrative: str
- 1. [Rule 1 - Bug] KnowledgeGraph.add_edge uses `type=` kwarg, not `edge_type=`
- Post-execute mutation scanner with YAML-configured conserved properties; disabled-by-default via `conserved_properties: []` for zero-cost opt-out (D-16, GAP-ENG06)
- Atomic per-tick JSON writer (D-20/SIM-11) with execute/yield/refuse path factory and Haiku/Sonnet cost accounting, reusing Phase 4 atomic-write infrastructure
- SimulationEngine.run_tick() wiring classify→match→decide→execute→conservation→passive_sweep→observe→tick_summary across three terminal paths (ok/yielded/refused) with pre-tick snapshot rollback, D-17 passive sweep, D-02 idempotent registry, and Phase 4.1 YieldSignal contract validation
- Real SimulationEngine/KnowledgeGraph/MechanicRegistry implementations replace Phase 0 stubs in all three MCP tools with path-traversal defence, -32602/-32603 error routing, and no stack-trace leaks
- TickResult gains a `projected_state: dict | None` field populated on the execute path, exposing the VisibilityProjector output used by Observer.synthesize so Phase 6 Plan 05 (TurnScorer) can compute observation_groundedness without private-attribute access or duplicate projection work.
- Personality-driven LLM resident agent with SQLite memory, graph-snapshot session forking, and interactive agent-turn CLI — closing the resident-agent half of the Phase 6 loop
- One-liner:
- One-liner:
- 1. [Rule 1 - Bug] Fixed pytest summary regex for "N failed in Xs" pattern
- One-liner:
- Frozen dataclasses ThresholdSpec/LongRunningAction + pure-function ThresholdEvaluator with 6-operator dispatch, tuple-to-list serialization boundary, and 41 deterministic tests.
- Backward-compatible attention_state kwarg on VisibilityProjector.project_for: suppress removes properties from projection, boost copies them to a separate attention_boosted top-level key, with suppress-first deterministic ordering
- One-liner:
- `has_active_long_action(actor) -> bool`
- One-liner:
- One-liner:
- One-liner:
- Status:
- One-liner:
- One-liner:
- examine.py
- bench
- 1. [Rule 1 - Bug] Updated all test mock responses from old "classified" schema to new "actions" schema
- 1. [Rule 1 - Bug] Restored §E6 check-failed refusal for single-sub-action case
- SC-1 — Tick stage inspector:
- SC-3/OPS-01 — run_unattended.py hardening:
- SC-4 — agent_inspector.py:
- SC-5/EMERGE-01 — operator/overlap.py:

---

*Entries in reverse chronological order — newest first.*

## v1.1 Emergence Tooling (Shipped: 2026-04-14, retroactively archived)

**Delivered:** Three surfaces for unattended emergence — Operator CLI (8 commands),
NiceGUI Dashboard (4 panels), and Emergence Substrate (`ExternalOperator` file
protocol + unattended runner). An overnight run authored 11 novel mechanics
autonomously under the user's Claude subscription ($0 marginal). Four v1.0 Known
Gaps also closed out in a warm-up track.

**Phases completed:** 5 — 08, 09, 10, 11, 12 — 8 plans (retroactively counted;
v1.1 ran in hybrid mode per session-4 D-01)

**Key accomplishments:**

- **Emergence Substrate (Phase 08):** `ExternalOperator` file-based yield/resolve protocol (`8f1f18e`). Seed starter universe Willowbrook + `scripts/run_unattended.py` (`0a95763`). Classifier permissive-verb prompt + markdown-fence stripper + seed pruning so scripted scenarios don't get eaten by LRA mechanics (`3ffb9f5`, `ee0284b`).
- **Operator CLI Surface (Phase 09):** 8 commands — `inspect`, `tick`, `trace`, `mechanics`, `stats`, `watch`, `agents`, `diff`. Every command supports `--format json`. Canonical producer for the dashboard panels per the allocation principle (§G) that emerged during the work.
- **Warm-up Burn-down (Phase 10):** v1.0 Phase 04.1 SC-2 closed via claude-cli backend (`0ac7f38`). Traceability + roadmap-progress drift scripts with pytest integration (`acb9797`). Research docs refreshed + archival timestamps (`ff211b7`). `BatchSummary.agent_id` populated from first mutation (`97f9648`). Friction-reducer scripts documented.
- **NiceGUI Dashboard (Phase 11):** 4 panels — stats strip, live tick stream, graph canvas (Mermaid + property drawer), causal chain viewer. Localhost-only. Read-only; consumes CLI JSON rather than reimplementing logic. D-01 documents the NiceGUI adoption against the FastAPI transitive-ban question.
- **Overnight Orchestration (Phase 12, experiment):** Willowbrook overnight run — 11 novel mechanics authored autonomously (examine, pet, sharpen, walk, draw, plant, force, drop, water, hum, lift). Each mechanic arrived via yield → subagent → validated Python module → resumed tick. Narrative not scripted. Second unattended run (session-6 post-E6 fix) produced 15 more ticks with 0 yields and 4 *honest* refuses — proving the truthfulness fix in real execution.

**Stats:**

- 1687 → 1885 tests passing (+198 net)
- 5 phases, 8 plans, 42 commits over 3 calendar days
- 8 new CLI commands + 8 new scripts + 4 dashboard panels
- 11 mechanics authored autonomously in overnight experiment
- 0 API spend on the emergence run — all authoring ran under the Claude subscription via `ExternalOperator`

**Git range:** `c19fb8b docs(readme): v1.0 shipped — link to new guides + status section` → `152ce54 docs(handoff): §I mining results + §L operating notes for next agent`

**Verification status at close:**

- All 19 REQ-V11-* requirements delivered (OPCLI-01..07 + EMERGE-01..07 + DASH-01..06 + WARMUP-01..06)
- Dashboard scroll + truthfulness bugs surfaced in session-5 user feedback → closed in v1.2 warm-up (REQ-V12-DASHBOARD-01, REQ-V12-ENGINE-01..02)
- All tests green; CI green; prek hooks pass
- Mode note: hybrid (direct-edit + retroactive scaffolding), NOT `/gsd-new-milestone`-front-loaded. Retroactive REQUIREMENTS + ROADMAP archives landed at v1.2 open

### Known Gaps at v1.1 close (all carried into v1.2)

- **REQ-EMERGE-05 mechanic overlap detector** → REQ-V12-EMERGE-01
- **REQ-EMERGE-07 operator decision-log enrichment** → REQ-V12-EMERGE-02
- **Dashboard scroll-preservation bug (§A7)** → REQ-V12-DASHBOARD-01 (shipped in v1.2 warm-up `6101da0` + `d31090d`)
- **Engine primary-check-fail lied (§E6)** → REQ-V12-ENGINE-01 (shipped in v1.2 warm-up `afc5c73`)
- **Observer grounding drift (§E4)** → REQ-V12-ENGINE-02 (shipped in v1.2 warm-up `e110e2c`)
- **commit.sh swept parallel WIP (§Anti-Pattern 5)** → REQ-V12-TOOLING-01 (shipped `958a28b`)

**Verification:** all tests green, 1687 → 1885 passing, CI green.

---

## v1.0 MVP (Shipped: 2026-04-14)

**Delivered:** End-to-end LLM-powered universe simulator — operator-authored mechanics, grounded observations, resident agent with memory, composable attention/consciousness pattern — all persisted to a schema-less knowledge graph and verified by 1687 tests.

**Phases completed:** 10 total — 0, 1, 2, 3, 4, 04.1 (INSERTED), 5, 6, 7, 07.1 (INSERTED) — 63 plans

**Key accomplishments:**

- **Knowledge graph (Phase 1):** Schema-less NetworkX+SQLite with snapshot/restore, tick-linked rollback, event audit log, JSON-serializable property constraint. All graph mutations go through `KnowledgeGraph` API (ground-truth invariant maintained).
- **Mechanic framework (Phases 2+4):** Protocol (check/apply), `MechanicContext` DSL, 6-stage validation pipeline (syntax → AST → import → contract → tests → dry-execute), flat-Python layout (supersedes original folder-per-mechanic D-15), `validate-mechanic`/`scaffold-mechanic` CLIs. 34 seed mechanics authored.
- **Design validation (Phase 3):** 35 use cases (spatial/social/resource/environmental/edge-case), gap analysis with 68 canonical GAP IDs (52 address-now / 16 defer / 0 OOS), R-tree spatial index + temporal index as optional DSL primitives, Mermaid graph viz CLI with ego-graph filtering.
- **Operator harness (Phase 04.1):** Agent SDK driver catches yield signals and spawns Opus mechanic-authoring subagent; end-to-end integration test authored mechanic `meditate.py` at $1.15/23 turns, passed Phase 4 validation on first attempt. `YieldSignal` dataclass locked as engine↔operator contract.
- **Simulation engine (Phase 5):** Haiku classifier, deterministic matcher (WorldPropertyMatcher/DecayMatcher/TickMatcher), VisibilityProjector with belief overlay, Sonnet observer synthesizer (D-15 hard grounding), YAML-defined conservation invariants, tick summary writer (atomic JSON), 3-tool MCP server (resume_tick/rollback/list_mechanics). Under inversion of control: engine yields to operator rather than generating code.
- **Resident agent + end-to-end loop (Phase 6):** Randomly-generated personality, SQLite-backed memory with session forking (via graph snapshot/restore, no git branch), TickCompressor for hierarchical (tick→batch→epoch) summary compression, PlaytestRunner with quality scoring rubric, 35-UC regression suite, PromptHashRegistry for automated grounding regression, expanded AdversarialBank with scenario pack.
- **Attention & consciousness (Phase 7):** Single composable pattern (`LongRunningAction` + `ThresholdSpec` + `ThresholdEvaluator`) drives sleep, daydream, autopilot travel, drunkenness. VisibilityProjector attention_state extension (suppress/boost). Validates project philosophy of "composition over specialization."
- **claude-cli LLM backend (Phase 07.1):** Pluggable `LLMBackend` protocol with `AnthropicSDKBackend` (default) + `ClaudeCLIBackend` (zero-cost live UAT via user's Claude subscription). Classifier, Observer, ResidentAgent all route through backend. Unblocked Phase 6 live-API UAT at $0 marginal cost.

**Stats:**

- 18,736 LOC Python (src) + 31,078 LOC tests
- 10 phases, 63 plans, 1687 tests passing (14 skipped, 36 deselected integration)
- 434 commits over 3 days (2026-04-11 to 2026-04-14)
- 34 seed mechanics shipped

**Git range:** `2fcb4b0 docs: initialize project` → `c24b69b docs(milestones): archive v1.0 ROADMAP and REQUIREMENTS`

**Verification status at close:**

- Phase 00: passed | Phase 01: passed | Phase 02: passed | Phase 03: passed (prev gaps_found)
- Phase 04: passed | Phase 04.1: `human_needed` (see Known Gaps) | Phase 05: passed (prev gaps_found)
- Phase 06: passed (3/3 live UAT closed via 07.1 claude-cli backend) | Phase 07: passed | Phase 07.1: passed

### Known Gaps

These were judged not-blocking for v1.0 close. All are documented and recoverable:

- **Phase 04.1 SC-2 (interactive Claude Code smoke test) left as `human_needed`:** The programmatic end-to-end path was verified at $1.15/23 turns with real Opus authoring `meditate.py`. The interactive path through universe CLAUDE.md's Operator Flow section was not manually re-run after 07.1 landed. Post-hoc runnable at zero cost via `ClaudeCLIBackend`; recommended for the v1.1 kickoff audit.
- **REQUIREMENTS.md traceability table stale at close:** Several rows showed "Pending" status despite their phase completing (GRAPH-01..05, MECH-01..02, SIM-01..12, AGENT-01..04, UNIV-01..02/04..06, TEST-01/03/06/07, AUTO-01/06, DVAL-03). The live REQUIREMENTS.md checkboxes in the Requirements sections above the traceability table were correctly marked, and all phase VERIFICATION.md files confirm delivery. The traceability table was just not mechanically updated tick-by-tick. The archive (`milestones/v1.0-REQUIREMENTS.md`) captures the corrected final status.
- **Research docs (`.planning/research/STACK.md`, `ARCHITECTURE.md`, `SUMMARY.md`) stale on model routing:** These recommend Sonnet for mechanic generation. Authoritative docs (CLAUDE.md, PROJECT.md) correctly say Opus, and the delivered 04.1 harness uses Opus. Research docs should be refreshed or explicitly marked historical in v1.1.
- **`agent_id` stubbed to `'unknown'` in BatchSummary v1:** TickSummary had no actor field. Carry into v1.1 planning as a concrete improvement.
- **ROADMAP.md Progress table had stale 0/N counts for phases 0-3 at close:** Cosmetic; didn't affect correctness of phase completion tracking (which lives in per-phase VERIFICATION.md + STATE.md).

**What's next:** v1.1 — milestone definition pending user kickoff via `/gsd-new-milestone`. Likely themes: second-agent experimentation (MULTI-01), cost monitoring / circuit breakers (HARD-03), consolidation of the Known Gaps above, research-doc refresh.

---
