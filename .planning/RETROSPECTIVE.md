# Project Retrospective: Token World

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-04-14
**Phases:** 10 (0, 1, 2, 3, 4, 04.1, 5, 6, 7, 07.1) | **Plans:** 65 | **Sessions:** many (autonomous-agent-driven, spread across 3 calendar days)

### What Was Built

- **Knowledge graph foundation (Phase 1):** Schema-less NetworkX+SQLite persistence with snapshot/restore, tick-linked rollback, event audit log, JSON-only property constraint. `KnowledgeGraph` API as the single mutation-mediated access point (invariant maintained across milestone).
- **Mechanic framework (Phases 2+4):** Protocol (check/apply), `MechanicContext` DSL with graph queries + mutations (+ optional spatial/temporal indexes from Phase 3), 6-stage validation pipeline (syntax → AST → import → contract → tests → dry-execute), flat-Python layout (supersedes Phase 2 D-15 folder-per-mechanic). 34 seed mechanics authored.
- **Design validation corpus (Phase 3):** 35 use cases across 5 categories, 68 canonical GAP IDs with dispositions (52 address-now / 16 defer / 0 OOS), Mermaid graph viz with ego-graph filtering.
- **Operator harness (Phase 04.1):** Agent SDK driver that catches yield signals and spawns Opus mechanic-authoring subagent. Integration test authored a real mechanic (`meditate.py`) at $1.15/23 turns, first-pass validation.
- **Simulation engine (Phase 5):** Classifier (Haiku), deterministic matcher, VisibilityProjector with belief overlay, Sonnet observer with hard grounding (D-15), YAML conservation invariants, tick summary writer, 3-tool MCP server. **Inversion of control:** engine yields rather than generating code.
- **Resident agent + end-to-end loop (Phase 6):** Personality, SQLite memory, session forking via graph snapshots, TickCompressor hierarchical summaries, PlaytestRunner with quality scoring, 35-UC regression suite, PromptHashRegistry, AdversarialBank.
- **Attention & consciousness (Phase 7):** Single composable pattern (`LongRunningAction + ThresholdSpec + ThresholdEvaluator`) drives sleep, daydream, autopilot travel, drunkenness — validates the "composition over specialization" project principle.
- **claude-cli LLM backend (Phase 07.1):** Pluggable `LLMBackend` protocol with zero-cost UAT path via user's Claude subscription; unblocked Phase 6 live-API verification at $0 marginal cost.

### What Worked

- **Inversion of control (engine-yields, operator-authors) paid off enormously.** Avoided building a bespoke LLM mechanic-generation pipeline. The top-level coding agent (already the most capable code-author in the room) writes mechanics via normal Python SDLC; the framework's job collapsed to validate + yield. This was a late Phase-4 re-scoping that saved probably weeks.
- **Flat-Python mechanic layout (superseded folder-per-mechanic D-15).** Once the layout shifted, all the authoring feedback loops (git diff, refactoring, test co-location) started feeling natural instead of bespoke.
- **Composable interruption-threshold pattern (Phase 7) from a single primitive.** Sleep, daydream, autopilot, drunkenness all dropped out of one small set of dataclasses. This is the kind of emergence the project philosophy bets on — validates the "prefer composable primitives" principle.
- **35-UC corpus drove gap analysis which drove architecture.** Authoring the use cases in Phase 3 *before* the engine in Phase 5 meant the engine requirements were grounded in real interaction scenarios. The 68-gap taxonomy fed directly into phase plans.
- **Phase 04.1 insertion.** Noticing mid-Phase-4 that Phase 5's yield→author→resume loop had no operator-side phase, and inserting 04.1 as an urgent decimal phase, prevented a mid-Phase-5 blocker.
- **Phase 07.1 insertion for zero-cost UAT.** Cost of live-API verification was blocking Phase 6 closeout. The claude-cli backend closed this instead of deferring UAT. Direct evidence of "close the feedback loop" paying off.
- **Graph-is-ground-truth invariant held across the milestone.** All simulation responses derived from graph state + mechanic execution. No side channels, no hallucinated state. This is the project's core architectural bet and it survived 1687 tests' worth of pressure.
- **1687 tests + 36 integration-marked opt-in tests.** Test discipline stayed high; milestone shipped with all tests green.

### What Was Inefficient

- **REQUIREMENTS.md traceability table drift.** Checkboxes in the requirement sections were mostly kept current, but the traceability table at the bottom showed many "Pending" rows even after their phase completed. Required reconciliation work at milestone close. Needs either an automated check (e.g., a `scripts/check_requirements_traceability.py` run in CI) or a workflow rule (update both at phase close, not just one).
- **ROADMAP.md Progress table had stale counts.** Phase 0-3 showed 0/N plans complete despite being fully done. Same root cause as above — manual updates diverged from reality. See grounding-rule #4 (ad-hoc-bash-is-a-missing-tool-signal): a `scripts/check_roadmap_progress.py` comparing PLAN/SUMMARY pairs to the Progress table would have caught this.
- **Phase 04.1 SC-2 "interactive Claude Code smoke test" left as `human_needed`.** The programmatic path was verified; the interactive path through universe CLAUDE.md was not re-run. In retrospect, should have either (a) completed it in the same session that landed 07.1, or (b) scoped it out of 04.1 as a v1.1 audit item rather than leaving `human_needed` dangling.
- **Research docs (STACK.md, ARCHITECTURE.md, SUMMARY.md) drifted from authoritative docs.** Opus-vs-Sonnet for mechanic generation is the canonical example — authoritative docs right, research docs stale. No drift detection. Either mark research docs explicitly archival-timestamped, or refresh at milestone boundaries.
- **Phase 3 had 3 follow-up fix plans (13, 14, 15) that weren't part of the original 12.** Not a failure — they were genuine fixes — but a pattern to watch: if an author-phase ships and then immediately needs fix plans, the author-phase verification might have been too shallow. (Counter-argument: this is healthy iterative development.)

### Patterns Established

- **Decimal phase insertion for urgent mid-milestone work** (Phase 04.1, 07.1). Worked well — gave us a way to course-correct without re-numbering everything downstream. Naming pattern stabilised in the roadmap.
- **Flat mechanic module + shared helper underscore-prefix convention** (`mechanics/<id>.py` + `mechanics/_helpers.py`). Emerged from Phase 4 and spread organically to all subsequent seed clusters.
- **Yield signal as engine↔operator contract** (`YieldSignal` frozen+slots dataclass, 7 fields, version-guarded). Stable across 04.1 and Phase 5. Same pattern should recur wherever cross-subsystem state is serialised.
- **Diagnostics substrate populated by multiple subsystems** (Phase 4 `DiagnosticsSink`, Phase 4.1 operator namespace, Phase 5 per-tick tickdirs). The "populate a shared sink" pattern handled cross-phase wiring without god-objects.
- **Single composable primitive for multiple concrete behaviors** (Phase 7's `LongRunningAction + ThresholdSpec`). Canonical example of "composition over specialization" — should be the first pattern we reach for when a new feature looks superficially specialised.
- **Zero-cost UAT via user's LLM subscription** (Phase 07.1 `ClaudeCLIBackend`). Applicable to future verification work that would otherwise blow budget. Pluggable-backend pattern is the mechanism.

### Key Lessons

1. **Inversion of control is a tool for scoping, not just architecture.** Phase 4's reframe from "build a generator" to "yield + author via SDLC" collapsed an entire subsystem. When a phase plan looks large, ask: is there a who-does-what reversal that eliminates work entirely?
2. **Insert decimal phases early, not late.** Phase 04.1 was inserted mid-milestone and took the rest of Phase 5's timeline in stride. Phase 07.1 was inserted just before milestone close and *also* worked, but was riskier. Insert as soon as the gap is visible.
3. **Track traceability mechanically, not manually.** REQUIREMENTS.md table + ROADMAP.md Progress table drift proves human-updated cross-file state is unreliable. For v1.1, promote ad-hoc reconciliation bash into `scripts/check_*.py` with CI integration (grounding rule #4).
4. **Close the feedback loop on verification.** Phase 04.1 SC-2 sat `human_needed` because it required a live session; 07.1 retroactively removed the cost barrier. Leaving verification dangling even on a "technically-complete" phase adds end-of-milestone archival friction — finish verification in the phase it belongs to.
5. **Composable primitives justify their upfront cost.** Phase 7's `LongRunningAction` primitive took extra design effort relative to "just code the sleep mechanic"; paid back 5x within the same phase. The project's composition-over-specialization principle is empirically correct.
6. **Research docs need an archival date or a live owner.** Drift is inevitable. Either stamp them "research snapshot YYYY-MM-DD; superseded by PROJECT.md" or refresh at milestone boundaries.
7. **The graph-is-ground-truth invariant is the project's single most important structural property.** Every time we tried to take a side-channel shortcut, tests rejected it. Keep this invariant absolute — do not soften it for convenience in v1.1.

### Cost Observations

- **Model mix:** Haiku (classifier, many per tick) > Sonnet (observer, once per tick) > Opus (mechanic authoring, rare but hundreds of turns when it fires). Playtest runs stayed cheap via Haiku dominance.
- **Integration-test costs:** Opus integration test `test_operator/test_integration.py` observed at $1.15/23 turns (Phase 04.1 Plan 03 Task 3). Excluded from default pytest run (integration marker); opt-in only. Kept CI cheap.
- **Zero-cost verification unlocked late:** Phase 07.1's `ClaudeCLIBackend` makes live-API UAT free via user's subscription. Significant cost lever for v1.1.
- **Session count:** Autonomous-agent-driven across many phases; user-visible session count in the Git commit log is 434 commits over 3 calendar days. Actual agent wall-time is higher than calendar time because of parallelism.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | Autonomous (434 commits, 3 days) | 10 | Inversion of control (engine-yields, operator-authors) reframed the whole architecture at Phase 4 |

### Cumulative Quality

| Milestone | Tests | Src LOC | Seed Mechanics | Notable |
|-----------|-------|---------|----------------|---------|
| v1.0 | 1687 | 18,736 | 34 | Graph-is-ground-truth invariant held throughout |

### Top Lessons (Verified Across Milestones)

1. (v1.0 only — single-milestone project so far) Inversion-of-control scoping wins out over building bespoke generators when a capable upstream agent already exists.
2. (v1.0 only) Composable primitives with deliberate design effort repay themselves within the same phase they're introduced.
3. (v1.0 only) Manual cross-file state drift is inevitable; promote it to scripts with CI integration.

*These will be re-evaluated against v1.1 to produce verified cross-milestone lessons.*
