# Morning Handoff — Token World

**Current as of**: 2026-04-14 ~03:30 UTC
**Last coordinator**: Claude Opus 4.6 (1M context), balanced profile
**Master HEAD**: `4021de6` — pushed to `origin/master`, CI ✅ GREEN

---

## Your Mandate

The user ("GSD to take over from here. It will have until tomorrow morning again.") wants you to continue work autonomously overnight. You have one full cycle (~12-20 hours) before the next morning check-in.

**Autonomy rules** (unchanged from prior session):
- **Take action.** Don't ask "should I proceed?" — just proceed.
- **Document decisions.** If a choice isn't in PROJECT.md/CONTEXT.md, pick the pragmatic option and record it in the relevant artifact. Only surface genuinely ambiguous or high-stakes decisions via BLOCKER.md.
- **Self-correct.** Diagnose and fix your own mistakes. Only bubble up problems you've tried and failed to resolve.
- **Only stop for**: architectural forks that lock in a hard direction, corrupted state you cannot safely recover from, rate-limit ceilings `ScheduleWakeup` can't clear.

**Profile**: `balanced` (Opus orchestrator + planner; Sonnet executors + verifier + reviewer). Do not switch without reason.

---

## TL;DR (Read First)

**Milestone v1.0 is feature-complete** — all 9 phases verified:

| Phase | Status | Key Deliverable |
|-------|--------|-----------------|
| 00–04, 04.1 | ✅ Done in prior sessions | Infrastructure, graph, mechanic framework, LLM mechanic generation, operator harness |
| **05** | ✅ Passed | SimulationEngine.run_tick pipeline (classify → match → decide → execute → conservation → sweep → observe → tick_summary), MCP tools |
| **06** | ✅ human_needed | ResidentAgent + PlaytestRunner + TickCompressor + regression suite (3 live-API UAT items open) |
| **07** | ✅ human_needed | Composable interruption-threshold pattern (sleep, autopilot, drunk seed mechanics) |

**Test suite**: 1640 passing, 14 skipped, 36 regression-marker-deselected. Zero regressions. ruff + mypy clean. CI green.

**What's NOT done** (your backlog — see "Prioritized Work" below):
1. 3 Phase 6 live-API UAT items (need real LLM calls — see §4)
2. Phase 7 "daydream" vs "drunk" substitution note (trivial — either write daydream seed or accept substitution)
3. `/gsd-complete-milestone` to archive v1.0
4. Optional: 5+ "going beyond" ideas from `.planning/OVERNIGHT-REPORT.md`

---

## Prioritized Work (What To Tackle, In Order)

### Priority 1 — Close the last two verifications

**Phase 6 UAT** (status `human_needed` on 3 live-API items):
1. `token-world playtest <slug> --turns 5 --no-operator` — verify personality-coherent actions + JSON report written
2. Modify a classifier/observer prompt, re-run playtest → verify `.planning/prompt-regression-history.jsonl` gains a triggered entry
3. `token-world playtest <slug> --judge` — verify report contains coherence/personality_consistency/world_rule_adherence scores

**⚠ Budget gate for UAT**: these hit real Anthropic API. The user flagged in the final conversation that they'd like us to explore `claude --model haiku-4-5 -p "..."` subprocess as a zero-direct-cost alternative (uses their Claude subscription). **Do NOT run the live UAT via raw SDK without confirming the user is OK with the API cost** (estimate ~$0.50 per 5-turn playtest). Safer route: implement the claude-cli subprocess backend first (see §5), then run UAT through it.

**Phase 7 substitution** (status `human_needed` on 1 trivial item):
- ROADMAP SC2 names "sleep, daydreaming, autopilot travel" as the composability proof. I (prior coordinator) substituted **drunk** for **daydreaming** via 07-CONTEXT D-18. Options:
  - (a) Accept the substitution — update `07-VERIFICATION.md` status to `passed` with a rationale comment, done.
  - (b) Write a `daydream` seed mechanic — ~30 min executor work, one new seed file following the pattern in `07-CONTEXT.md` and the three existing seeds.
- Recommend (b) if API budget is tight (deterministic, no LLM calls) — it literally exercises the same `ctx.begin_long_action()` primitive.

### Priority 2 — Close milestone v1.0

After Priority 1:
- `/gsd-complete-milestone` (archive v1.0, prep v1.1)
- Update PROJECT.md "Current focus" line
- Create `.planning/archive/v1.0/` folder per GSD convention

### Priority 3 — "Going Beyond" (from OVERNIGHT-REPORT.md)

Pick 1-2 based on remaining budget. All are small and self-contained:

1. **`claude --model haiku -p` subprocess backend** (~1h) — See §5. Makes live UAT run-for-free via user's Claude subscription. HIGH LEVERAGE — unblocks real E2E testing.
2. **Cost dashboard CLI** (`token-world cost <universe>`) — aggregate per-tick USD from `tick_summaries/`. ~30min, pure-Python, no LLM.
3. **Close technical debt** (from review-fix deferrals — see §6). Trace-tree walker dedup, `NoMatchResult.candidates`, CLI `_load_or_create_agent` dedup, etc.
4. **Use-case regression green-up** — implement 35 seed mechanics matching the UC manifests so the regression suite flips from 0/35 to 35/35. SCOPE-HEAVY (multiple hours) — don't start without quick feasibility check per UC category first. Suggest `/gsd-add-phase` for a new phase `8` (or polish phase `07.1`) if you proceed.
5. **Mermaid architecture diagrams** — already added `docs/design/simulation-pipeline.md`. Could add per-module diagrams (ResidentAgent state machine, PlaytestRunner lifecycle, TickCompressor hierarchy). Low-value; skip unless bored.

---

## ⚠ Critical Context (Gotchas That Burned The Previous Session)

### Anti-Pattern 1 — Worktree base-mismatch BUG in the GSD workflow

The `execute-phase` workflow's `<worktree_branch_check>` fallback uses `git reset --soft` which leaves the working tree stale after a base mismatch. The executor then commits post-HEAD files as DELETIONS.

**Symptom**: Executor's first commit shows large numbers of unrelated files being deleted (PLAN.md files, CONTEXT.md, MORNING-HANDOFF.md, etc.).

**Mitigation used**: Ran all executors in **no-worktree sequential mode** on main tree (omit `isolation="worktree"` from Task calls). Slower but correct. A proper fix to the workflow is out-of-scope for you — just avoid worktrees until/unless this is fixed upstream.

**If you see the bug**: `git checkout <pre-execution-SHA> -- <missing-file>` to restore, then commit a `chore` message acknowledging the restoration.

### Anti-Pattern 2 — Executors sneak edits outside plan scope

Multiple times the Sonnet executor touched files not in its `files_modified` list (registry.py, REQUIREMENTS.md, pre-existing tests). All were caught via `git diff --cached --stat` checks before commit.

**Mitigation**: Every executor prompt now includes a `<CRITICAL_FILE_SCOPE_GUARDRAIL>` block enumerating forbidden files. Keep this pattern — without it, silent scope violations happen.

### Anti-Pattern 3 — Stale `roadmap_complete` flags break `/gsd-autonomous`

Phase 04.1 has `disk_status: complete` but `roadmap_complete: false` because the ROADMAP markdown text wasn't updated. `/gsd-autonomous` would re-execute 04.1. Avoid by using `/gsd-autonomous --from N` or invoking discuss→plan→execute manually per phase.

### Anti-Pattern 4 — `uv run` with parallel worktrees races on `.git/config.lock`

If you DO use worktrees for parallel executor spawn, dispatch the `Task()` calls one-at-a-time with `run_in_background: true` — never multiple in a single message. Otherwise `git worktree add` deadlocks on the config lock.

### Don'ts (from project CLAUDE.md, reinforced by observed issues)

- Don't call `nx.DiGraph` methods directly — always through `KnowledgeGraph` API
- Don't use `pickle`, SQLAlchemy, LangChain, MongoDB, CrewAI (see PROJECT.md tech-stack restrictions)
- Don't write `random` in mechanics — use `ctx.rng` (Phase 5 D-19)
- Don't extend `match_mechanic_for_verb` in plan code (Phase 4 contract)
- Don't call `validate(run_tests=True)` from a test fixture (fork-bomb)
- Don't touch frozen MechanicContext DSL surface without updating `tests/test_mechanic/test_context_api.py::EXPECTED_CALLABLES`

---

## Session 2 Recap (What I Did)

118 commits on master (`84fca1e..4021de6`). 1007 → 1640 tests (+633).

**Phase 5** — 4 initial plans only covered classifier/matcher/decider/visibility. Phase goal required the full pipeline. I drafted 5 additional gap-closure plans (05-05..05-09) covering Observer, ConservationChecker, TickSummaryWriter, SimulationEngine orchestrator, MCP wiring. All verified.

**Phase 6** — 7 plans across 5 waves. Resident agent (personality/memory/session), TickCompressor (batch→epoch), use-case regression suite, PlaytestRunner+Scorer+Scenario+Injection+Judge, AdversarialBank. Three live-API UAT items deferred (see Priority 1).

**Phase 7** — 7 plans across 4 waves. LongRunningAction + ThresholdEvaluator + VisibilityProjector attention_state + ctx.begin_long_action + engine hook + 3 seed mechanics. Drunk-vs-daydream substitution per auto-mode D-18 (see Priority 1).

**Review-fix cycles** — 4 cycles across phases 5 (Wave 1 + Waves 2-4), 6, 7. 15 total warnings fixed with TDD (~40 regression tests added). Zero critical findings.

**Documentation** — added `docs/design/simulation-pipeline.md` with 3 mermaid diagrams (all render cleanly via mcp-mermaid).

**Notable bugs caught in review-fix** (worth knowing):
- P6 `runner.py --output` flag ignored caller path (fixed)
- P6 `memory.maybe_compact_summary()` never called in playtest loop (fixed)
- P6 unguarded `response.content[0]` in 3 places → IndexError risk (fixed)
- P7 LRA companion flags (`is_sleeping`/`is_drunk`/`is_traveling`) never cleared on termination → `sober_up` fired forever (fixed via `clear_on_end` payload convention)
- P7 `autopilot_travel.py` used `assert` in production path → silent-degrade under `-O` (fixed)

**Transient events**:
- 1× API 500 error mid-plan (06-01) — executor had committed 2 of 5 tasks; fresh executor picked up tasks 3-5 cleanly
- 1× rate-limit hit at 06-05 start — user sent "continue", retry completed

---

## User's Final Question (Your Starting Point)

Before signing off the user asked:

> "How did you proceed without a live API for residents? You couldn't do realistic playtesting right? For now, how easy would it be to do `claude --model ... -p "..."` with a cost effective model like haiku?"

**I answered**: Correct — all tests used mocked Anthropic clients. The Phase 6 `human_needed` UAT items are the real-playtest gap. I offered to wire up a claude-cli subprocess backend (~1h) but stopped short of implementing without the user's go-ahead (it's a design addition, not a planned deliverable).

**Your call**: The user may have greenlit this by the time you start (check the conversation start). If ambiguous, treat as "yes, proceed" — they explicitly said to take autonomous action on reasonable decisions. The backend is ~3 swap points: `resident/agent.py`, `engine/classifier.py`, `engine/observer.py`. Pattern sketched below in §5.

---

## §5 — Proposed `claude-cli` Backend (Copy-Paste Starter)

Add env flag `TOKEN_WORLD_BACKEND` with values `anthropic-sdk` (default) or `claude-cli`. New module `src/token_world/engine/llm_backend.py`:

```python
import os
import subprocess
from typing import Protocol

class LLMBackend(Protocol):
    def call(self, system: str, prompt: str, model: str) -> str: ...

class ClaudeCLIBackend:
    def call(self, system: str, prompt: str, model: str) -> str:
        full = f"{system}\n\n{prompt}"
        result = subprocess.run(
            ["claude", "--model", model, "-p", full],
            capture_output=True, text=True, timeout=60, check=True,
        )
        return result.stdout.strip()

class AnthropicSDKBackend:
    def __init__(self, client):
        self._client = client
    def call(self, system: str, prompt: str, model: str) -> str:
        resp = self._client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()

def get_backend() -> LLMBackend:
    if os.environ.get("TOKEN_WORLD_BACKEND") == "claude-cli":
        return ClaudeCLIBackend()
    from anthropic import Anthropic
    return AnthropicSDKBackend(Anthropic())
```

Then refactor `Classifier`, `Observer`, `ResidentAgent` to accept a backend via constructor (default to `get_backend()`). Existing tests still inject a FakeClient; new integration tests can set `TOKEN_WORLD_BACKEND=claude-cli` and hit the real CLI.

Token telemetry will be rough — `claude -p` doesn't expose input/output tokens directly. Estimate from word count × 1.3 or skip telemetry for CLI backend (TurnScorer stays on word-count metrics, USD cost estimate shows `$0.00 (via CLI subscription)`).

Treat this as a **new plan** under phase 07.1 or in a new v1.1 milestone — do NOT graft it onto completed Phase 6/7 SUMMARY files. Proper path: `/gsd-add-phase` → `/gsd-plan-phase <N>` → execute.

---

## §6 — Technical Debt Punch List (Deferred from Review-Fix Cycles)

From `.planning/OVERNIGHT-REPORT.md`:

- [ ] Trace-tree walker duplication across `summary_writer.py`, `engine.py`, `observer.py` (P5W2 IN-02) — promote to `token_world.mechanic.trace`
- [ ] `NoMatchResult.candidates` always empty (P5W1 IN-01, D-11) — spec says top-K mechanic IDs
- [ ] `adversarial_rate` field loaded from scenario YAML but never consumed (P6 IN-03)
- [ ] CLI `_load_or_create_agent` duplication between `agent-turn` and `playtest` (P6 minor)
- [ ] Belief overlay `visibility.py` can override structural projection fields (P5W1 IN-02) — tighten before multi-agent v2

Each is small (~30-60min). Bundle them as a single "polish" plan under v1.1 milestone if you want to knock them out quickly.

---

## Final Git State

```
master = 4021de6
origin/master = 4021de6 (pushed)
CI = green
Tests = 1640 passed, 14 skipped, 36 deselected
```

No uncommitted changes. `.claude/scheduled_tasks.lock` is runtime state (untracked, expected).

---

## Handoff Files You Should Skim Before Starting

Priority order:

1. **`.planning/OVERNIGHT-REPORT.md`** — session 2 narrative, decisions made, what the user sees
2. **`.planning/STATE.md`** — authoritative position tracker
3. **`.planning/phases/06-.../06-VERIFICATION.md`** — 3 UAT items detail
4. **`.planning/phases/07-.../07-VERIFICATION.md`** — daydream note detail
5. **`.planning/phases/06-.../06-CONTEXT.md`** — 30 auto-mode decisions (flag any you'd reverse)
6. **`.planning/phases/07-.../07-CONTEXT.md`** — 23 auto-mode decisions (flag any you'd reverse)
7. **`.planning/REQUIREMENTS.md`** — may have stale labels (verifier flagged); clean up if you touch it
8. **`docs/design/simulation-pipeline.md`** — your model of the v1 pipeline

Good luck. Close the feedback loop.
