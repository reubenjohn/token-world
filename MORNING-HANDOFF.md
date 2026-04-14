# Morning Handoff — Token World

**Current as of**: 2026-04-15 ~03:10 UTC (end of session 4)
**Last coordinator**: Claude Opus 4.6 (1M context)
**Master HEAD**: `ceea3a7` (will be slightly newer at handoff finalization)
**Milestone:** v1.1 Emergence Tooling — **substrate live**, **dashboard live**, **first emergence captured**

---

## TL;DR — What Shipped Overnight

**11 mechanics authored autonomously by Claude Code subagents in the
Willowbrook starter universe.** Mira (the resident agent) examined a
cottage, walked to the garden, drew water, planted a seed, forced open a
locked chest, dropped a pebble in the well, watered the planted seed,
hummed at the hearth, and *lifted the chest lid when she heard the lock
give way*. Each of those verbs had no mechanic when she tried it; the
engine yielded, an out-of-process subagent (subscription-covered, $0
marginal) authored a Python mechanic that validated against the existing
graph, and the tick resumed. The narrative wasn't scripted.

**See `.planning/OVERNIGHT-REPORT-20260415.md` for the full session detail.**

### Demo it in 3 commands

```bash
# 1. Inspect the run
uv run token-world inspect willowbrook --last 30
uv run token-world stats willowbrook        # 11 novel mechanics, 15.4% yield rate

# 2. See the universe move (browser opens automatically)
uv run token-world dashboard willowbrook --port 8080

# 3. Walk the causal chain
uv run token-world trace willowbrook old_chest locked
```

The dashboard is a 4-panel NiceGUI surface (tick stream + Mermaid graph
canvas + stats strip + causal-chain viewer). Take a screenshot for
sharing — the live tick stream auto-refreshes every 2 s.

---

## What's New Since v1.0 (Session 4)

| Track | Status | Notes |
|---|---|---|
| **Track A — Operator CLI surface** | ✅ shipped | 8 commands: `inspect`, `tick`, `trace`, `stats`, `mechanics`, `watch`, `agents`, `diff`. All `--format json`. 98 tests. |
| **Track B — NiceGUI dashboard** | ✅ shipped | 5 plans landed (skeleton, tick stream, graph canvas, causal chain, polish). 26 tests. D-01 documented. |
| **Track C — Emergence substrate** | ✅ shipped | `ExternalOperator` file-based protocol. Seed Willowbrook universe + run driver. 11 mechanics emerged across two runs. |
| **Track D — Warm-up backlog** | ✅ shipped | All 11 backlog items. Friction reducers (`commit.sh`, `run_uat.py`, `phase_show.py`, `ci_status.py`). Research docs refreshed. CI checks for traceability + roadmap drift. |
| **Engine fixes** | ✅ shipped | Permissive-verb classifier prompt + markdown-fence stripping. Required for emergence — without these the classifier refused all novel verbs. |
| **v1.1 milestone scaffolding** | ✅ shipped | PROJECT.md / STATE.md / ROADMAP.md / REQUIREMENTS.md retro-fitted; phases 08–12 scaffolded. |

42 commits since v1.0, 1885 tests passing (+142), CI green.

---

## What's Active and Unfinished

### Still pending in v1.1

- **REQ-EMERGE-05 — mechanic overlap detector**: before authoring, the operator should diff a proposed verb+watches against existing mechanics; prefer edit-existing when overlap exceeds threshold. Emergent universes will eventually accumulate near-duplicates without this.
- **REQ-EMERGE-07 — operator decision log richness**: `<universe>/operator-log.jsonl` exists but only contains yield/resolve events. Phase 12 was supposed to enrich with the subagent's reasoning. Each authoring subagent's final JSON summary should land here.
- **Multi-agent rotation in PlaytestRunner**: still v2-scoped per D-17. Could re-scope to v1.1 if the next session wants a richer narrative — pair Mira with a contrasting agent (Old Bran the cautious elder?).

### Tooling debt + improvements

1. **`scripts/commit.sh` accepts paths** — the warm-up subagent flagged that `git add -A` swept other agents' WIP into commits twice this session. Fix: change `commit.sh` signature to `commit.sh <message-file> [paths...]`.
2. **Seed mechanics need `VerbMatcher` declarations** — currently only 4 of 30+ seed mechanics declare verbs (the LRA ones). Other voluntary mechanics rely on protocol-default empty `watches()` and contribute nothing to the classifier vocabulary. Adding explicit VerbMatchers to look/speak/pickup/give/teach/etc. would let the permissive-classifier patch retire.
3. **Resident agent system-prompt tightening** — Mira broke character around tick 44 of round 2 ("I recognize we've hit the yield boundary repeatedly"). Either tighten her system prompt or treat consecutive-refuses as a halt signal in the runner.
4. **`run_unattended.py` heuristic auto-stop** — if N consecutive ticks refuse, halt cleanly with a noted reason. Avoids burning credits on degenerate scenarios.

---

## What To Do First This Morning

1. **Run the demo above.** Five minutes; gives you the visceral sense of what's now possible.
2. **Skim `OVERNIGHT-REPORT-20260415.md`** in full. Section "What Didn't Work (and What I Fixed)" has the lessons.
3. **Make the call on multi-agent for v1.1** — re-scope from v2, or stay single-agent for v1.1 close. Multi-agent unlocks richer emergence (two characters with contrasting personalities); single-agent ships sooner.

---

## Vision (Unchanged from v1.0 Close)

Token World is an engine for emergent universes. A resident agent inhabits a
world. They do something the world has no rule for. The engine yields to an
operator. The operator authors a Python mechanic on the fly. The world grows.
Last night, that loop ran unattended for the first time, and 11 mechanics
emerged from the play of one curious 11-year-old apprentice in a tiny
cottage with a garden, a chest, a well, and a cat.

The substrate works. The stage is built. The garden bloomed.

---

## Anti-Patterns (Updated — Session 4 Additions)

1. **Worktree base-mismatch BUG** *(carried from session 3)*. Don't use worktrees for execute-phase. Sequential subagents on main tree.
2. **Executor file-scope drift** *(carried)*. Always include CRITICAL_FILE_SCOPE_GUARDRAIL in subagent prompts. (Now extracted to `.planning/agent-prompts/executor-preamble.md`.)
3. **Re-using `/tmp/commit_msg.txt`** *(carried)*. Use unique tmp paths per commit OR Read the file before Write.
4. **Heredoc commit messages over 300 chars** *(carried)*. Blocked by hook. Use `Write` to tmp + `git commit -F`.
5. **NEW: Unstaged edits sweep into another subagent's commit.** `git add -A` in `scripts/commit.sh` (also seen in subagents) can pull in another worker's WIP. Mitigation: add explicit `paths...` arg to `commit.sh`, or use targeted `git add` directly.
6. **NEW: Scripted scenarios get eaten by LRAs.** If you keep `daydream`/`sleep`/`autopilot` seeds in a starter universe, Mira's first introspective action triggers a 4-turn LRA that consumes scripted turns. Mitigation already shipped in `scripts/seed_starter_universe.py::_KEEP_MECHANICS`.
7. **NEW: GSD bypassed for velocity.** Direct-edit + subagent dispatch worked but skipped `/gsd-new-milestone`. User chose hybrid mode (option `c`); next session should declare v1.1 milestone formally if desired.

---

## Files To Read In Priority Order

1. **`.planning/OVERNIGHT-REPORT-20260415.md`** — full session 4 narrative + what didn't work
2. **This document** — vision + tactical mandate
3. **`.planning/STATE.md`** — progress snapshot
4. **`.planning/REQUIREMENTS.md`** — v1.1 traceability table
5. **`docs/guides/dashboard.md`** — how to run the dashboard
6. **`docs/guides/operator-cli.md`** — 8 new CLI commands
7. **`src/token_world/operator/external.py`** — the protocol every overnight run uses
8. **`scripts/run_unattended.py`** — driver
9. **`scripts/seed_starter_universe.py`** — Willowbrook
10. **`scenarios/willowbrook_bootstrap.yaml`** — bootstrap scenario

---

## Final Git State

```
master = ceea3a7  (push final morning commit before signing off)
origin/master = synced
tag v1.0 = pushed
CI = green (last 8 commits)
Tests = 1885 passed, 14 skipped, 36 deselected
Lint + format + mypy = clean (mypy nicegui ignored via override)
```

No uncommitted changes (assuming the morning final commit lands).

---

**Go look at it move.** 🌱🌌

*— Session 4, signing off.*
