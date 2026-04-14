# Session 3 Overnight Report — 2026-04-14

**Duration:** ~2 hours (03:30 → 05:45 UTC)
**Starting HEAD:** `75fa563` — start of session (master = prior session's MORNING-HANDOFF commit)
**Ending HEAD:** `1ef16d8` — belief overlay structural-key filter (all changes pushed, CI green)
**Model profile:** balanced (Opus orchestrator; Sonnet executors + subagents)
**Git tag:** `v1.0` created and pushed

## Outcome: Milestone v1.0 Archived + Phase 07.1 Shipped + 5 Tech-Debt Items Closed

The session opened with milestone v1.0 feature-complete but 4 loose ends open (3 Phase 6 live-API UAT items + 1 Phase 7 daydream substitution). Those closed within the first hour via a new-phase-insertion (07.1) to ship the claude-cli LLM backend, then live UAT execution through that backend, then full milestone archival.

The remaining ~1 hour was spent on §6 tech-debt closure and polish — all 5 deferred items from MORNING-HANDOFF §6 are now fixed.

| Deliverable | Status | Commit(s) |
|---|---|---|
| Daydream seed (4th composability demonstrator) | SHIPPED | `5efac0f..2a45e55` |
| Phase 07.1 claude-cli LLM backend (Waves 1 + 2) | SHIPPED | `0085216..b5656e1` |
| Phase 07.1 planning docs pushed | DONE | `512cdb6` |
| Phase 6 Live UAT — all 3 items PASSED | DONE | `6333b0f` |
| Milestone v1.0 archive + git tag `v1.0` | DONE | `984ee0a..bfabf4c` |
| `docs/guides/claude-cli-backend.md` guide | DONE | `b8f936f` |
| `token-world cost <slug>` CLI subcommand | SHIPPED | `1348f19` |
| Tech debt IN-01 — `NoMatchResult.candidates` populated | CLOSED | `8b4ce97` |
| Tech debt IN-02 — trace-walker dedup → `mechanic.trace` | CLOSED | `5803ecd` |
| Tech debt IN-03 — `adversarial_rate` now consumed | CLOSED | `22c29fe` |
| Tech debt minor — CLI `_load_or_create_agent` dedup | CLOSED | `2d078a9` |
| Tech debt IN-02 (P5 W1) — belief overlay structural filter | CLOSED | `1ef16d8` |

**Test suite:** 1645 → 1743 (+98 new tests this session; +2 new from daydream + 29 backend + 13 integration + 24 cost + 6 NoMatch + 11 trace + 8 adversarial + 4 CLI helper + 3 belief = 100; Actual diff 98 — the dedup refactor caused a couple of consolidated fixtures). Zero regressions across all 13 commits.

**Source + test LOC changed:** ~150 files touched; net additions across code + tests ≈ 4k lines. Docs ≈ 700 lines.

---

## What the User Sees Wake-Up Morning

**Git log (last 13 commits, master = `1ef16d8`, all pushed, all CI green):**

```
1ef16d8 fix(visibility): filter structural keys from belief overlay merge
2d078a9 refactor(cli): dedup _load_or_create_agent between agent-turn and playtest
22c29fe feat(playtest): consume scenario.adversarial_rate in PlaytestRunner
5803ecd refactor(mechanic): extract trace-tree walker to mechanic.trace
8b4ce97 fix(engine): populate NoMatchResult.candidates with top-K mechanic IDs
1348f19 feat(cli): add token-world cost subcommand — per-universe cost dashboard
b8f936f docs(guides): add claude-cli backend guide for zero-cost UAT
bfabf4c docs: add RETROSPECTIVE.md for v1.0 milestone
ff48a37 chore: complete v1.0 milestone
c24b69b docs(milestones): archive v1.0 ROADMAP and REQUIREMENTS
984ee0a docs(roadmap): add inserted Phase 04.1 line to top-level phase list
6333b0f docs(06): close Phase 6 VERIFICATION — 3/3 live UAT items PASSED
512cdb6 docs(07.1): add phase 07.1 planning docs + UAT helpers
```

**Milestone v1.0 archived:**
- `.planning/milestones/v1.0-ROADMAP.md` — full phase breakdown
- `.planning/milestones/v1.0-REQUIREMENTS.md` — 52 requirements final status
- `.planning/MILESTONES.md` — delivery summary
- `.planning/RETROSPECTIVE.md` — what worked / lessons / cross-milestone trends
- git tag `v1.0` (annotated, pushed)
- `.planning/REQUIREMENTS.md` deleted (fresh one expected for v1.1 via `/gsd-new-milestone`)

---

## Phase 07.1: claude-cli LLM Backend (NEW this session)

**The user asked last session:** "how easy would it be to do `claude --model ... -p '...'` with a cost effective model like haiku?"

**Answer shipped:** 2 plans, 7 commits, `TOKEN_WORLD_BACKEND=claude-cli` env var switches the whole simulation to use the user's Claude subscription at zero marginal cost.

**3 live UAT items run through it (all PASSED, documented in `06-VERIFICATION.md`):**
1. 5-turn playtest → personality-coherent text: `"freshly wiped partition—no artifacts, no footprints, no tell-tale fragment..."` — the agent is a tech-paranoid character and speaks like one.
2. Prompt change → regression triggered → `regression-history.jsonl` entry written with `trigger: "prompt_hash_change"`.
3. `--judge` flag → Sonnet judge returns scored rubric: `{coherence: 0.2, personality_consistency: 0.4, world_rule_adherence: 0.1}` with sensible rationale prose.

**Noteworthy design choices (locked in `.planning/phases/07.1-.../07.1-CONTEXT.md` D-01..D-10):**
- `LLMBackend` Protocol with 2 impls (`AnthropicSDKBackend`, `ClaudeCLIBackend`) — env-var-switched
- Backward-compatible refactor: `Classifier`, `Observer`, `ResidentAgent` keep their `client` field, add `backend: LLMBackend | None = None` kwarg
- CLI wraps JSON in ```json fences — a `_strip_markdown_fences()` helper handles it
- Full model IDs required (`claude-haiku-4-5-20251001`, `claude-sonnet-4-5`); aliases (`haiku-4-5`) fail

**Guide published at `docs/guides/claude-cli-backend.md`** — 244 lines, covers setup, UAT commands, model IDs, tradeoffs, troubleshooting.

---

## New `token-world cost <slug>` CLI Command (NEW this session)

**What it does:** aggregates per-tick USD cost + token counts from a universe's `tick_summaries/` directory. Auto-detects backend (`anthropic-sdk` / `claude-cli` / `mixed`) so CLI-subscription runs don't falsely appear free.

**Example:**
```
$ uv run token-world cost uatworld
=== Cost Dashboard: uatworld ===
Ticks analyzed:    11 (tick range: 1..11)
Duration:          26.2 seconds (11 ticks)

Model                                        Calls    Input tok   Output tok     Cost USD
classifier (claude-haiku-4-5-20251001)          11            0            0 $     0.0000
observer (claude-sonnet-4-5-20250929)           11            0            0 $     0.0000
-----------------------------------------------------------------------------------------
Total                                           22            0            0 $     0.0000

Backend used:      claude-cli
CLI-subscription calls (zero marginal cost): 22
```

**Flags:** `--since N` (last N ticks), `--format table|json`. 405 LOC + 517 LOC tests.

---

## Tech Debt Closure

All 5 deferred items from MORNING-HANDOFF §6 are now fixed:

| Item | What it was | Fix |
|---|---|---|
| P5 W1 IN-01 | `NoMatchResult.candidates` always empty | `difflib.SequenceMatcher`-ranked top-K mechanic IDs (K=3) via verb similarity |
| P5 W2 IN-02 | Trace-tree walker duplicated across 3 files | Extracted to `src/token_world/mechanic/trace.py`; iterative DFS (no recursion blow-up risk); also refactored a 4th call site in `playtest/scorer.py` |
| P6 IN-03 | `adversarial_rate` field loaded but not consumed | Now drives per-turn `_rng.random()` coin flip; `adversarial_categories` filter added; TurnRecord gains `adversarial_injected: bool` field; 8 new tests |
| P6 minor | CLI `_load_or_create_agent` duplicated between `agent-turn` and `playtest` | Helper now has `agent_id=None` kwarg + internal explicit-id branch; both callers use it; existing stderr messages preserved verbatim |
| P5 W1 IN-02 | Belief overlay could override `type`/`hidden_properties`/`beliefs` | `_BELIEF_STRUCTURAL_KEYS = {"type", "hidden_properties", "beliefs"}` filtered out pre-merge; 3 regression tests |

Each fix is its own atomic commit with a TDD-first test, pushed to master individually, CI green.

---

## Daydream Seed — Phase 7 SC2 Closed Literally

**Prior session's substitution:** Phase 7 shipped with `drunk` in place of `daydream` (auto-mode D-18) — the ROADMAP SC2 literally names "sleep, daydreaming, autopilot travel."

**This session's fix:** added `src/token_world/mechanic/seeds/daydream.py` as a **4th seed** (not replacement — drunk stays). turns_total=4 bounded short; noise threshold >0.4; suppress [ambient_sound, peripheral_vision], boost [noise_level]; companion `is_daydreaming` property; `clear_on_end` pattern.

**Result:** Phase 7 VERIFICATION flipped from `human_needed` to `passed`, overrides_applied counter increments to 1, narrative updated to describe 4-seed composability across 4 distinct state categories (physiological / cognitive / chemical / movement).

---

## UAT Artifact Note — `uatworld` universe preserved

The test universe at `/home/reuben/.local/share/token_world/universes/uatworld/` was created for live UAT. It contains:
- The 3 UAT run artifacts: `tick_summaries/`, `diagnostics/`, `prompts.sha256.json`, `regression-history.jsonl`
- Baseline prompt hashes restored after the Wave-2 classifier edit (via new `scripts/update_prompt_hashes.py` utility)

Safe to delete via `token-world delete uatworld` when no longer needed, or rerun UAT against it any time.

---

## Transient Events

- **One pre-commit hook reformat cycle** on the belief overlay fix — ruff-format re-wrapped the `_BELIEF_STRUCTURAL_KEYS` comprehension. Re-staged and committed on retry.
- **One test failure** during the belief overlay regression tests — used an agent as the target but agents aren't visible to each other by default (co-location doesn't imply visibility). Switched test setup to use an entity NPC with `subtype="npc"` and containment edge; all 9 belief tests then passed.
- **Two commit_msg.txt path clashes** — /tmp/commit_msg.txt is reused across sessions; Wave 1 tech-debt agent noted that `Write` tool won't overwrite without prior `Read`. Resolved by using unique /tmp paths per commit.
- **No API 500s, no rate-limit hits** — the claude-cli backend insulates the simulation from Anthropic API issues during UAT. All 3 UAT runs completed on first try.

---

## What's Next

Milestone v1.0 is fully archived. The next cycle is **v1.1 scoping** — the user's call.

**Candidate themes surfaced during v1.0 close (documented in PROJECT.md §Active + ROADMAP.md §v1.1):**
- Close Phase 04.1 SC-2 interactive smoke test (now zero-cost via `ClaudeCLIBackend`)
- Refresh stale research docs on Opus-vs-Sonnet model routing
- Populate `agent_id` correctly in BatchSummary
- Second-agent experimentation (precursor to v2's MULTI-01)
- Cost monitoring / circuit breakers (HARD-03)
- Dashboard / graph visualizer (previously out-of-scope; reconsider)
- Use-case regression green-up (35 seed mechanics to flip 0/35 → 35/35)

**User action:** `/gsd-new-milestone` to scope v1.1 when ready. Candidate themes are pre-populated above.

---

## Files the User Should Skim

| File | Why |
|------|-----|
| `.planning/MILESTONES.md` | v1.0 delivery summary (stats, known gaps, v1.1 candidates) |
| `.planning/RETROSPECTIVE.md` | What worked / lessons / cross-milestone trends |
| `.planning/phases/06-resident-agent-end-to-end-loop/06-VERIFICATION.md` | 3 live UAT items now PASSED with evidence |
| `.planning/phases/07.1-.../07.1-CONTEXT.md` | 10 locked design decisions for the claude-cli backend |
| `docs/guides/claude-cli-backend.md` | Published user-facing guide |
| `src/token_world/engine/llm_backend.py` | New backend module (147 LOC) |
| `.planning/PROJECT.md` | v1.0 retrospective-informed rewrite; v1.1 candidates in §Active |

Good morning. Everything is pushed, everything is green, milestone v1.0 is shipped. 🚀
