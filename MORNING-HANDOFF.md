# Morning Handoff — Token World

**Current as of**: 2026-04-14 ~05:45 UTC (end of session 3)
**Last coordinator**: Claude Opus 4.6 (1M context), balanced profile
**Master HEAD**: `1ef16d8` — pushed to `origin/master`, CI ✅ GREEN
**Git tag**: `v1.0` — milestone v1.0 shipped and archived

---

## TL;DR (Read First)

**Milestone v1.0 is SHIPPED, TAGGED, and ARCHIVED.** All 10 phases verified, 1743 tests passing, 5 deferred tech-debt items closed tonight, 3 live UAT items run via the new claude-cli backend, and full retrospective + archive artifacts written.

**The project is now between milestones.** Next action is `/gsd-new-milestone` to scope v1.1 — the user's call on which candidate themes to prioritize.

**Session 3's narrative:** `.planning/OVERNIGHT-REPORT-20260414.md` (read this if you're the next Claude session).

---

## Your Mandate (If The User Hands You Autonomous Time Again)

**Autonomy rules** (unchanged from prior sessions):
- **Take action.** Don't ask "should I proceed?" — just proceed on routine decisions.
- **Document decisions.** If a choice isn't in PROJECT.md / CONTEXT.md, pick pragmatic and record it. Only surface truly ambiguous high-stakes decisions.
- **Self-correct.** Fix your own mistakes. Only bubble up what you've tried and failed to resolve.
- **Only stop for**: architectural forks that lock in a hard direction, corrupted state you cannot safely recover from, rate-limit ceilings `ScheduleWakeup` can't clear.

**Profile**: `balanced` (Opus orchestrator + planner; Sonnet executors + verifier + reviewer). Do not switch without reason.

**Default budget stance:** The user confirmed in session 3 to **leave UAT as human_needed if CLI path fails** — do NOT fall back to direct SDK for expensive (>~$0.50) runs without explicit permission. CLI backend is the standard path now.

**Push policy:** Push to master as you go (the user approved this in session 3). Green CI before next commit. No need to stage branches for review.

---

## Current State

**Phases (all verified):**

| Phase | Status | Key Deliverable |
|-------|--------|-----------------|
| 0–4, 04.1 | ✅ Passed | Infrastructure, graph, mechanic framework, LLM mechanic generation, operator harness |
| 5 | ✅ Passed | SimulationEngine.run_tick pipeline + MCP tools |
| 6 | ✅ Passed (live UAT closed 2026-04-14) | ResidentAgent + PlaytestRunner + TickCompressor + regression suite |
| 7 | ✅ Passed | Composable interruption-threshold pattern (sleep + daydream + autopilot + drunk = 4 seeds) |
| 07.1 | ✅ Passed | claude-cli LLM backend (zero-cost UAT via user's Claude subscription) |

**Test suite:** 1743 passing, 14 skipped, 36 regression-marker-deselected. Zero regressions. ruff + mypy clean. CI green across the session's 13 commits.

**Uncommitted changes:** None (aside from runtime `.claude/scheduled_tasks.lock`, expected).

---

## If The User Says "Scope v1.1"

Run `/gsd-new-milestone`. Candidate themes surfaced during v1.0 close are pre-populated in:
- `.planning/PROJECT.md` §Active
- `.planning/ROADMAP.md` §v1.1 (Not Yet Scoped) section

**Pre-scoped candidate themes (rank by ROI before picking):**
1. **Close Phase 04.1 SC-2 interactive smoke test** — now zero-cost via `ClaudeCLIBackend`. Probably 1 plan, <1h.
2. **Second-agent experimentation** — precursor to v2's MULTI-01 (multi-agent). This is where the belief overlay structural-key filter (closed tonight) pays off.
3. **Use-case regression green-up** — 35 seed mechanics to flip the regression suite from 0/35 → 35/35 pass. Scope-heavy (several hours); split across multiple phases if attempted.
4. **Cost monitoring / circuit breakers** — HARD-03; builds on tonight's `token-world cost` CLI.
5. **Dashboard / graph visualizer** — builds on existing `viz-graph` CLI from Phase 3.
6. **Populate `agent_id` correctly in BatchSummary** — small tech debt; ties to second-agent work.
7. **Refresh stale research docs** on Opus-vs-Sonnet model routing — housekeeping.

The `.planning/RETROSPECTIVE.md` from v1.0 close has more detail on what worked / what to avoid in v1.1.

---

## If The User Says "Something Else" — Starter Moves

### "Show me what you did overnight"
→ `cat .planning/OVERNIGHT-REPORT-20260414.md` (full session 3 narrative)

### "Run the UAT again"
```bash
export TOKEN_WORLD_BACKEND=claude-cli
uv run token-world playtest uatworld --turns 5 --no-operator
uv run token-world playtest uatworld --turns 3 --no-operator --judge
```
(The `uatworld` universe is the one created for session 3's UAT. See `docs/guides/claude-cli-backend.md`.)

### "Look at costs"
```bash
uv run token-world cost uatworld
```
(New CLI subcommand added tonight.)

### "Delete the test universe"
```bash
uv run token-world delete uatworld
```

### "What was deferred?"
All 5 Phase-5/Phase-6 §6 tech-debt items are CLOSED tonight. The remaining deferrals (from `.planning/milestones/v1.0-REQUIREMENTS.md` + RETROSPECTIVE):
- RestrictedPython CVE review (v2 sandboxing concern — PROJECT.md blocker)
- Research docs mention Sonnet for mechanic gen, but user's decision is Opus — research docs are stale
- Phase 04.1 SC-2 interactive smoke (now unblocked via claude-cli)

---

## ⚠ Critical Context (Anti-Patterns — DO NOT REPEAT)

### Anti-Pattern 1 — Worktree base-mismatch BUG in GSD executor spawn

Still unresolved. `execute-phase` workflow's `<worktree_branch_check>` fallback uses `git reset --soft` which leaves working tree stale. Executor commits post-HEAD files as DELETIONS.

**Mitigation:** spawn all executors in **no-worktree sequential mode** on main tree — omit `isolation="worktree"` from Task calls. Session 3 used this throughout (11 commits, zero file-deletion incidents).

### Anti-Pattern 2 — Executors sneak edits outside plan scope

Still observed occasionally — session 3's trace-walker dedup subagent found a 4th call site in `playtest/scorer.py` that wasn't in the original plan. It correctly noted the deviation in the commit message. That's the right behavior — not a bug.

**Mitigation pattern (keep using):** Every executor prompt must include a `<CRITICAL_FILE_SCOPE_GUARDRAIL>` block enumerating forbidden files. Without it, silent scope violations happen.

### Anti-Pattern 3 — Re-using `/tmp/commit_msg.txt` across sessions

Session 3 caught this: the `Write` tool refuses to overwrite a file not-yet-read in the current session. Solution: use UNIQUE tmp paths per commit (`/tmp/commit_wave1.txt`, `/tmp/commit_belief.txt`, etc.) OR `Read` the file first before `Write`.

### Anti-Pattern 4 — Heredoc commit messages are blocked by a hook

There's a `deny-ad-hoc-bash.js` hook that blocks any bash command over ~300 chars with inline `<<HEREDOC`. Use `Write` to a tmp file + `git commit -F <tmp-file>` pattern instead.

### Don'ts (From Project CLAUDE.md + Observed Issues)

- Don't call `nx.DiGraph` methods directly — always through `KnowledgeGraph` API
- Don't use `pickle`, SQLAlchemy, LangChain, MongoDB, CrewAI (see PROJECT.md tech-stack restrictions)
- Don't write `random` in mechanics — use `ctx.rng` (Phase 5 D-19)
- Don't extend `match_mechanic_for_verb` in plan code (Phase 4 contract)
- Don't call `validate(run_tests=True)` from a test fixture (fork-bomb)
- Don't touch frozen MechanicContext DSL surface without updating `tests/test_mechanic/test_context_api.py::EXPECTED_CALLABLES`

---

## Session 3 Recap (What I Did)

13 commits on master (`75fa563..1ef16d8`). 1645 → 1743 tests (+98).

### Phase 07.1 — claude-cli LLM Backend (NEW PHASE)
Inserted via `/gsd-insert-phase`. 2 plans in 2 waves:
- Wave 1: `llm_backend.py` module + 29 unit tests + engine exports (3 commits)
- Wave 2: Classifier + Observer + ResidentAgent refactored backward-compat + 13 integration tests (4 commits)

### Phase 6 Live UAT — all 3 items PASSED
Ran via `TOKEN_WORLD_BACKEND=claude-cli`:
1. 5-turn playtest → personality-coherent text confirmed
2. Classifier prompt edited → regression-history.jsonl entry appended
3. `--judge` flag → Sonnet rubric scores returned

### Milestone v1.0 Archive
- `.planning/milestones/v1.0-ROADMAP.md` + `v1.0-REQUIREMENTS.md` archived
- `.planning/MILESTONES.md` created (with known gaps, v1.1 candidates)
- `.planning/RETROSPECTIVE.md` written
- `.planning/PROJECT.md` rewritten (post-retrospective)
- `.planning/STATE.md` now `status: milestone_closed`
- `.planning/REQUIREMENTS.md` deleted (will be recreated for v1.1)
- git tag `v1.0` (annotated, pushed)

### Tech Debt — All 5 §6 Items Closed
- IN-01: `NoMatchResult.candidates` now top-K mechanic IDs
- IN-02 (P5 W2): trace walker → `mechanic.trace` module
- IN-03: `adversarial_rate` now consumed
- Minor: CLI `_load_or_create_agent` deduped
- IN-02 (P5 W1): belief overlay structural-key filter

### Polish
- `docs/guides/claude-cli-backend.md` (244 lines, covers setup + UAT + troubleshooting)
- `token-world cost <slug>` CLI (405 LOC + 24 tests; auto-detects backend)
- `scripts/inspect_playtest_report.py` + `scripts/update_prompt_hashes.py` (UAT dev-ergonomics utilities)
- Daydream seed mechanic (4th composability demonstrator; Phase 7 SC2 now literal)

---

## Final Git State

```
master = 1ef16d8
origin/master = 1ef16d8 (pushed)
tag v1.0 (annotated) — pushed to origin
CI = green (5 jobs across 13 commits)
Tests = 1743 passed, 14 skipped, 36 deselected
Lint + format + mypy = clean
```

No uncommitted changes. `.claude/scheduled_tasks.lock` is runtime state (untracked, expected).

---

## Handoff Files To Skim Before Starting Next Session

Priority order:

1. **`.planning/OVERNIGHT-REPORT-20260414.md`** — session 3 narrative (THIS was my session)
2. **`.planning/MILESTONES.md`** — v1.0 delivery summary
3. **`.planning/RETROSPECTIVE.md`** — v1.0 lessons learned
4. **`.planning/PROJECT.md`** — post-retrospective rewrite; §Active has v1.1 candidates
5. **`.planning/ROADMAP.md`** — reorganized with Milestones section
6. **`.planning/STATE.md`** — `status: milestone_closed`, awaiting `/gsd-new-milestone`
7. **`.planning/phases/07.1-.../07.1-CONTEXT.md`** — 10 locked D-NN decisions for the claude-cli backend
8. **`docs/guides/claude-cli-backend.md`** — user-facing guide; use this to bootstrap any future UAT
9. **`src/token_world/engine/llm_backend.py`** — the new backend module (147 LOC)

Good luck, next session. The project is healthy and shipped. 🎉
