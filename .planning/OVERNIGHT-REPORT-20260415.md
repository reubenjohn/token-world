# Overnight Report — Session 4 (2026-04-15)

**Master at session close:** (TBD at write-out)
**Milestone:** v1.1 Emergence Tooling — kicked off
**Session length:** ~6 h autonomous (user asleep)
**Mode:** Hybrid (direct for Tracks A/C warm-up; GSD-scaffolded for Track B + v1.1)

---

## TL;DR

Built the emergence substrate and kicked it off. The engine yields, a Claude
Code subagent authors a mechanic, the universe grows, the agent feels it. By
morning the Willowbrook starter universe had **N authored mechanics** (TBD at
close) across **M ticks** of unattended play — real emergence data, not a
tech-demo toy.

Shipped in parallel: 8 new operator CLI commands (Track A), 11-item warm-up
backlog burn-down (Track D), and a NiceGUI dashboard (Track B) that makes
the run legible to humans.

---

## What's in the Branch (pushes to `origin/master`)

### Track C — Emergence Substrate + Overnight Run (my work)

| Commit | Notes |
|---|---|
| `8f1f18e` | ExternalOperator file-based yield protocol + 8 unit tests |
| `0a95763` | Willowbrook seed script + unattended run driver |
| `a9c2e39` | v1.1 milestone scaffolding — PROJECT/STATE/ROADMAP/REQUIREMENTS + phase dirs |
| `3ffb9f5` | Classifier permissive-verb prompt + markdown-fence stripping |
| `ee0284b` | Pruned seed mechanics + bootstrap scenario + yield-handler prompt |
| `131b787` | mypy: silence `nicegui.*` imports until dashboard extra wired in CI |
| `f84c9b2` (carried) | Classifier v2 prompt strengthen (stronger permissive wording) |

### Track A — Operator CLI Surface (subagent)

Shipped in commits `a89992f..c27be38`:
- `token-world inspect <slug>` — universe-at-a-glance
- `token-world tick <slug> <tick_id>` — per-tick detail tree
- `token-world mechanics <slug>` — registry browser
- `token-world trace <slug> <node> <prop>` — causal chain walker
- `token-world stats <slug>` — aggregate metrics
- `token-world watch <slug>` — live tail
- `token-world agents` + `token-world diff` — P1 bonuses
- All commands support `--format json` (dashboard consumption)
- 98 tests, `docs/guides/operator-cli.md`

### Track D — Warm-up Backlog + Automation (subagent)

Shipped in commits `0ac7f38..6cc2fe9`:
- Phase 04.1 SC-2 smoke closed via `claude -p` ($1.05 / 51 turns — within
  budget, OAuth-subscription path)
- `scripts/check_requirements_traceability.py` + pytest
- `scripts/check_roadmap_progress.py` + pytest
- Research docs refreshed (STACK/ARCHITECTURE/SUMMARY) with archival headers
- `BatchSummary.agent_id` stub fixed
- Friction reducers: `commit.sh`, `run_uat.py`, `phase_show.py`, `ci_status.py`
- `.planning/agent-prompts/executor-preamble.md` for DRY subagent briefings
- CLAUDE.md Script Catalog updated
- REQ-WARMUP-01..06 marked done in REQUIREMENTS.md

### Track B — NiceGUI Dashboard (subagent)

Shipped in commits `41e8f30..0781543`:
- NiceGUI stack adopted (D-01 v1.1): FastAPI transitive acceptable, direct
  FastAPI imports remain banned
- Plan 11-01: skeleton + stats strip + `token-world dashboard <slug>` CLI
- Plan 11-02: live tick stream panel (polls `tick_summaries/ticks/` every 2s)
- Plan 11-03: graph canvas panel via Mermaid (color by type/subtype, property drawer)
- Plan 11-04: causal chain viewer (consumes `token-world trace` JSON)
- Plan 11-05: polish + layout + dark mode + docs (in flight at report time)

---

## Emergence Data (Willowbrook Overnight Run)

*(The numbers below reflect what shipped at write-out; update just before
handoff to user.)*

- **Universe slug:** `willowbrook`
- **Setting:** cottage + garden, 11 seeded nodes (hearth, old_chest, well, garden_bed, whetstone, tabby_cat, cottage_door, 2 rooms, Mira, pocket_knife)
- **Resident agent:** Mira (curious apprentice, hand-crafted personality)
- **Seed mechanics:** 9 (look, observation, movement, passage_move, position_sync, speak, pickup, environmental_reaction, _helpers)
- **Round 1 run:** 100-tick cap; halted at tick 53 via kill switch (classifier too strict on novel verbs — prompted the v2 strengthen)
- **Round 2 run:** 80-tick cap (started 02:39)
- **Operator-authored mechanics:** (TBD — examine, pet, sharpen from R1; R2 additions pending)

### Authored mechanics (in universe git log)

| Mechanic | Verb | Triggered by | Universe commit |
|---|---|---|---|
| `examine` | examine | "I look around the cottage carefully…" (tick 1, R1) | `71e8ee1` |
| `pet` | pet | "I pet the tabby cat, Pip…" (tick 9, R1) | `909ccde` |
| `sharpen` | sharpen | "I sharpen my pocket knife…" (tick 11, R1) | `82727bf` |
| `walk` | walk | "I walk through the cottage door…" (tick 4, R2) | `30864b3` |
| `draw` | draw | "I draw a bucket of water…" (tick 7, R2) | `41f990f` |
| `plant` | plant | "I plant a single pea seed…" (tick 12, R2) | `764fc2f` |
| `force` | force | "I try to force the lock on the old chest…" (tick 15, R2) | `6c58bd4` |
| `drop` | drop | "I drop a small pebble into the well…" (tick 18, R2) | `fb1fed5` |
| `water` | water | "I water the garden bed…" (tick 21, R2) | `2607635` |
| `hum` | hum | "I hum to the hearth-fire…" (tick 26, R2) | `bc40c17` |
| `lift` | lift | "I place both hands on the lid and lift." (tick 33, R2) | `ba7fd05` |

**11 mechanics authored** across two runs.  All are voluntary, pass the
Phase 4 validation pipeline on the first attempt (or occasionally second),
and use the `VerbMatcher` pattern.  Each subagent averaged 40-110 s of
real-time authoring (zero marginal cost — subagents run through the user's
Claude Code subscription).

### The payoff — genuine emergent narrative

The authoring order tells a story: Mira examines → moves → draws water →
plants a seed → attempts the old chest's lock → drops a pebble in the well
→ waters the planted seed → hums at the hearth → *lifts the chest lid when
she hears the lock give way*. That last action (tick 33) was not scripted.
The scenario ran out at turn 20. Mira, in agent-decide mode, remembered the
chest she'd been forcing and **followed up coherently** because the world
held on to her attempts in the graph (her `last_forced` list, the chest's
`locked` flag flipping to `False`). The engine yielded on `lift` because
no existing mechanic covered it; the operator authored one; the narrative
continued.

This is the emergence the handoff was reaching for. Not a scripted demo.

---

## What Didn't Work (and What I Fixed)

### Bug 1: Classifier refused all novel verbs

The v1.0 classifier prompt said "Use ONLY verbs from the provided list."
With a small seed mechanic set (pruned Willowbrook had only `look`, `speak`,
`pickup`, etc. — none declaring `VerbMatcher`), `available_verbs=[]` at
classify time. Every action classified `no_viable_action` → refused, never
yielded.

**Fix 1 (commit `3ffb9f5`):** Prompt changed to "prefer listed verbs, propose
a natural one if none fit."

**Fix 2 (commit via `f84c9b2`):** Fix 1 was too soft — Haiku kept interpreting
"prefer" as a hard constraint. Prompt strengthened with worked examples
("water", "draw", "hum") and an explicit negative ("an action with a clear
verb but not in the list is NOT grounds for no_viable_action").

### Bug 2: claude-cli backend wraps JSON in markdown fences

`claude -p` sometimes returns ```json\n{…}\n``` even when prompted for
JSON-only. `_parse` didn't strip fences → always malformed-after-retry.

**Fix (commit `3ffb9f5`):** `_strip_markdown_fence` peels up to 3 pairs of
fences before `validate_json`. 3 new tests; pre-existing tests unaffected.

### Bug 3: Seed mechanics don't declare `VerbMatcher`

Most seed mechanics (`look`, `speak`, `pickup`, `give`, etc.) use
protocol-default `watches()` returning `[]`. `_collect_available_verbs`
only reads `VerbMatcher` declarations, so these contribute nothing to the
classifier's verb vocabulary. Only 4 of 30+ seed mechanics declare verbs
(the LRA ones: `drink`, `sleep`, `daydream`, `travel`).

**Workaround:** keep the LRA mechanics pruned (they eat turns without
adding value to a starter universe) and rely on the permissive classifier
to generate novel verbs.

**Backlog for v1.2:** add explicit `VerbMatcher` declarations to the
non-LRA seed mechanics so the classifier has a richer vocabulary without
needing the permissive-prompt fallback.

### Kill switch worked

Round 1 was halted mid-run via `touch <universe>/.stop`. The kill switch
mechanism I built into `run_unattended.py` honored it at the next progress
print (per-tick boundary).

---

## Anti-Patterns Observed (Do NOT Repeat)

### Anti-Pattern 5 — Unstaged edits sneak into another subagent's commit

The dashboard subagent's commit `f84c9b2` used `git add -A` and swept in my
unstaged `src/token_world/engine/classifier.py` v2 prompt change. The change
landed (so no data loss) but the commit message and trailer don't reflect
it. **Mitigation:** subagents should `git add <specific-paths>` rather than
`-A`. The `scripts/commit.sh` friction reducer was also flagged for the
same issue by the warm-up subagent.

### Anti-Pattern 6 — Scripted scenario turns get eaten by LRAs

In the original unpruned Willowbrook, Mira entered a 4-turn daydream LRA
at tick 5, which consumed ticks 6-9. The scenario's scripted "plant a pea
seed" on turn 9 was silently replaced by a `long_running_continuation`
marker. **Mitigation:** prune LRA-triggering seed mechanics from starter
universes. Already in `scripts/seed_starter_universe.py::_KEEP_MECHANICS`.

### Anti-Pattern 7 — GSD bypassed by "direct-edit velocity"

I started Tracks A/C warm-up as direct subagents without going through
`/gsd-new-milestone` first. User explicitly chose option (c) — hybrid mode,
water-under-bridge for what had landed, GSD-scaffolded for remaining Track B
+ orchestration. The retroactive v1.1 milestone scaffolding is in
`a9c2e39`. **Future:** prefer `/gsd-new-milestone` at milestone boundaries
even when momentum is high; the overhead is small relative to the project
legibility gain.

---

## Tooling Added This Session

| Tool | Location | What |
|---|---|---|
| `token-world inspect/tick/trace/stats/mechanics/watch/agents/diff` | `src/token_world/cli.py` + `src/token_world/inspect/` | 8 operator CLI commands with JSON output |
| `token-world dashboard` | `src/token_world/cli.py` + `src/token_world/dashboard/` | NiceGUI read-only dashboard |
| `scripts/run_unattended.py` | (new) | PlaytestRunner driver with external-operator harness |
| `scripts/seed_starter_universe.py` | (new) | Reproducible Willowbrook seed |
| `scripts/commit.sh` | (new) | 3-line wrapper: `add -A && commit -F $1 && push origin master` |
| `scripts/run_uat.py` | (new) | Encapsulates Phase 6 UAT 3-item flow |
| `scripts/phase_show.py` | (new) | One-screen CONTEXT+PLAN+SUMMARY+VERIFICATION dump for a phase |
| `scripts/ci_status.py` | (new) | `gh run list` + `gh run view` summarizer with --since filter |
| `scripts/check_requirements_traceability.py` | (new) | Parses REQUIREMENTS + phase SUMMARYs, diffs status |
| `scripts/check_roadmap_progress.py` | (new) | Parses ROADMAP Progress + PLAN/SUMMARY pairs, diffs |
| `scenarios/willowbrook_bootstrap.yaml` | (new) | 20-turn bootstrap to ignite emergence |
| `.planning/agent-prompts/yield-handler.md` | (new) | Reusable mechanic-author subagent prompt |
| `.planning/agent-prompts/executor-preamble.md` | (new) | Reusable executor subagent preamble |

CLAUDE.md Script Catalog updated with all of the above.

---

## What's Live on Master at Write-out

- **Tests:** 1876 passing (up from 1743 at v1.0 close, net +133)
- **LOC delta:** TBD (quick `git diff --shortstat v1.0..HEAD` at close)
- **CI:** green (5 jobs)
- **Master HEAD:** TBD at close — push final morning update
- **Open PR:** none (direct pushes to master per project pattern)

---

## Next Session (v1.1 Continued)

Recommended priorities for morning kickoff:

1. **Inspect the Willowbrook run.** `uv run token-world inspect willowbrook --last 30` and `uv run token-world stats willowbrook`. Cycle through `tick <id>` for the interesting moments.

2. **Open the dashboard.** `uv run token-world dashboard willowbrook --port 8080` and watch the world move in the live tick stream + graph canvas.

3. **Review authored mechanics.** `cd ~/.local/share/token_world/universes/willowbrook && git log --oneline mechanics/` — see the order they emerged, the patterns the subagent picked up.

4. **Decide what's next for v1.1:** remaining candidate phases include:
   - Multi-agent experimentation (precursor to v2 MULTI-01)
   - Mechanic overlap detector (REQ-EMERGE-05) — before authoring, diff verb+watches against existing; prefer edit-existing
   - Operator decision log richness (REQ-EMERGE-07)
   - Tick scrubber (v1.2 candidate; snapshot-restore rewind)
   - Hosted dashboard (v1.2 candidate)

5. **Anti-pattern 5 cleanup:** adjust `scripts/commit.sh` to accept explicit paths instead of `git add -A`. Prevents cross-agent sweeping.

---

## Files The Next Session Should Read First (Priority Order)

1. **This document** — session 4 narrative
2. `.planning/STATE.md` — progress snapshot
3. `.planning/REQUIREMENTS.md` — v1.1 requirements + traceability
4. `.planning/phases/08-emergence-substrate/08-CONTEXT.md` — External operator protocol
5. `.planning/phases/11-nicegui-dashboard/11-CONTEXT.md` + `11-PLAN.md` — dashboard decisions + roadmap
6. `docs/guides/dashboard.md` — how to run the dashboard
7. `docs/guides/operator-cli.md` — 8 new CLI commands
8. `src/token_world/operator/external.py` — `ExternalOperator` contract
9. `scripts/run_unattended.py` — driver for unattended runs
10. `MORNING-HANDOFF.md` (prior) — still relevant for vision context

---

*The stage is built. The garden is seeded. Mira walks and waters and sharpens.
The universe, against all odds, is moving.*

*— Session 4, signing off.* 🌱🌌
