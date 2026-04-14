# Project Milestones: Token World

*Entries in reverse chronological order — newest first.*

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
