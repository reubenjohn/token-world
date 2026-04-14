# Morning Handoff — Token World

**Current as of**: 2026-04-15 post-demo (session 4 closed, session 5 feedback captured, NOT yet implemented)
**Last coordinator**: Claude Opus 4.6 (1M context)
**Master HEAD**: `0ff528d` — all session-4 work pushed and CI green
**Milestone:** v1.1 Emergence Tooling — **substrate live**, **dashboard live**, **first emergence captured**
**v1.2 scope**: driven by §"Session 5 Feedback — Next Mandate" below; nothing in that section is shipped yet.

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

## Session 5 Feedback — Next Mandate

User walked the demo and gave structured feedback. Categorised below, with
my own reflection on tooling gaps observed while investigating during
session 4 + the CLI/MCP/Dashboard allocation principle that emerged from
the work. Everything here is **not yet implemented** — it is the next
session's starting line.

### A. Dashboard UX fixes (quick wins; do these first)

**A1. Tick-card expansion renders full action + observation, not truncated.**
Current collapsed card shows `tick 50 · refuse · no_viable_action` — no
preview. Expanded shows a truncated action ("…Th…") and truncated
observation, then dumps the full JSON below. User expects the expanded
drawer to show the *full* narrative text, not a re-truncated version.

**A2. Tick expansion shows structured sections, not raw JSON.** Users
shouldn't have to read a JSON dump to understand a tick. Sections should
include: **Classification** (verb / actor / target / confidence),
**Decision** (exec / yield / refuse + mechanic id or reason), **Mutations**
(grouped by target — "old_chest.locked: True → False"), **Observation**
(full text), **Metadata** (duration, cost, tokens). Raw JSON stays as a
collapsed sub-section for dev use.

**A3. Graph canvas agent labels display `&[agent&]`.** The `escape_label`
function entity-escapes `[` / `]` to `&#91;` / `&#93;` which the current
Mermaid renderer leaves partially unescaped. Fix: prefer parentheses or a
colon-delimited label (`mira : agent`) in `panels/graph_canvas.py::build_mermaid`.

**A4. Graph canvas is missing the agent ↔ room edge.** Mira's
`located_in = "cottage_interior"` is stored as a *property* rather than an
edge, so the Mermaid graph shows her dangling off the diagram with only her
`carries → pocket_knife` edge. Fix: after loading the snapshot, synthesise
dashed "located_in" pseudo-edges from every agent node whose properties
name a room. Similar treatment for any property that references a known
node id (this is a small refactor — see A8 below for a richer version).

**A5. Tick-card expansion should show the mechanic side-effect chain.**
Mutations list is flat today. When a mechanic triggers downstream mechanics
(via `ChainExecutionEngine` children), the tree should be rendered as a
tree — "force_lock triggered: unlock_chest → set locked=False → observe(chest)".
Related to backlog §E mutation-chain visibility.

**A6. `token-world inspect` table is missing column headers.** Rows show up
as `17 refuse - (0 mut) ...` with no `TICK STATUS MECHANIC MUT OBSERVATION`
header. One line fix in `src/token_world/inspect/universe.py`'s table
renderer.

### B. Multi-agent — design question

Current state: single-agent only (D-17 invariant). Willowbrook has Mira.
User's question: how do we plan to expand the dashboard for multi-agent?

**Recommendation (agent-centric with fallback):**

- **Agent selector at the top.** Dropdown defaulting to "All" (or the only
  agent if single). Changing the selector filters the tick stream + scopes
  the causal chain + highlights the agent in the graph canvas.
- **Per-tick agent badge on the card.** Small left-bordered stripe or chip
  `· mira` / `· bran` so chronological view still works when the selector
  is "All".
- **Graph canvas highlight.** Selected agent's node gets a thicker outline,
  and the `located_in` edge (see A4) highlights as an indicator of "where
  the agent is right now."
- **KPIs per agent** (not universe-wide). Yield rate for Mira vs yield rate
  for Bran tells you who's pushing the world's vocabulary harder.

This is roughly one session of work after A1–A5 land because the card now
has an `actor` field to badge against. Multi-agent engine support is still
v2 (D-17), but the dashboard can be *ready* for it.

### C. Simulation quality — Mira breaking character

Ticks 44–47 of round 2: "I notice the universe framework has been
activated but no mechanic…", "I recognize we've hit the yield boundary
repeatedly…", "I need to step completely out of character…". Mira
decompensates once the scripted scenario exhausts and several consecutive
refuses stack up.

**Mitigations (pick 1–2 for v1.2):**

- **Tighten the resident-agent system prompt.** Add an in-character recovery
  clause: "If nothing in the world responds, stay in character and try a
  different small action. Never narrate the simulation framework itself."
- **Auto-halt on N-consecutive-refuses.** `scripts/run_unattended.py` halts
  when the last K observations are all `refused=True`. Avoids generating
  meaningless ticks.
- **Provide a "nudge" mechanic.** When the agent's recent-refuse count
  crosses a threshold, the engine can synthesise a low-stakes observation
  prompt ("a faint breeze stirs the curtain") rather than refusing —
  pulling the agent back toward grounded action.
- **Richer observation even on refuse.** Today's refuse observation is
  "You try to X but the attempt is incoherent." Make it mention one or two
  things in the agent's visible state ("You stand in the cottage, the fire
  still warm, but your attempt to X finds no purchase") so she has
  something concrete to orient from.

### D. Simulation-quality KPIs (new dashboard panel / CLI command)

User asked for KPIs to track simulation quality. Candidates:

| KPI | Intuition | Source |
|---|---|---|
| **Groundedness score** (existing) | observation text vs projected_state match | `playtest.scorer` already computes this |
| **Character stability** | % of recent agent turns that don't contain meta-narration markers ("framework", "yield", "mechanic", "system prompt") | new — scan agent turns' action_text |
| **Action coherence streak** | longest consecutive run without a refuse | new — scan tick_summaries |
| **Refusal cluster alarm** | K consecutive refuses → alarm | new — single counter |
| **Vocabulary growth rate** | novel verbs introduced per 10 ticks | already in `stats` |
| **Novel subtype rate** | distinct `subtype` values introduced per 10 ticks | already in `stats` (currently 0 because no mechanic mutates subtype) |
| **Graph fan-out** | avg edges/node over time — richer world = higher | new — cheap graph scan |
| **Conservation drift** | ticks that rolled back conservation | already in `engine.conservation` |

**Surface allocation:** KPI *definition* lives in a new `src/token_world/quality/` subpackage; CLI wrapper is `token-world quality <slug>` (scriptable); dashboard renders a "Quality" panel consuming its JSON. Do not duplicate the computation in two places — CLI is the canonical producer.

### E. Architectural depth (bigger v1.2+ items)

**E1. Composite actions / action → chain-of-mechanics.** Today the matcher
picks one mechanic per classified action. Realistic actions often decompose
into sequence: "sharpen and examine my knife" or "open the chest and take
the key". Ideas: let the classifier output a list of sub-actions with
ordering; or let the decider score the top-K mechanics and run them in
sequence when their checks agree. Design work needed — surface it as a
v1.2 decision D-01.

**E2. Mutation chains / propagating side effects.** The `ChainExecutionEngine`
already supports chains (a mechanic's mutation can trigger another
mechanic's `watches()`), but the dashboard flattens them. First action
item: make the dashboard show the chain tree (see A5). Second: audit where
mechanics declare `watches()` beyond `VerbMatcher` — `environmental_reaction`
watches `PropertyChangeMatcher(temperature)`; `position_sync` watches
`EdgeMatcher(located_in)`. Only a few. More seeded chains would make
emergence richer.

**E3. `locked` / `blocked` / `inventory_full` should be emergent, not
engine-coded.** User called this out as a smell — any engine logic that
hard-codes these properties is a betrayal of the graph-is-ground-truth
invariant. Audit:

```bash
grep -rn "locked\|blocked\|inventory_full" src/token_world/engine/
grep -rn "locked\|blocked\|inventory_full" src/token_world/mechanic/ | grep -v seeds/
```

Any reference that decides semantics (not just "reads a property") in the
engine or framework should be replaced by a mechanic-level assertion.
Surface as v1.2 decision D-02.

**E4. Observation grounding drift (tick 35 bug).** User flagged: the chest
was unlocked by the `force` mechanic, but a later observation still said
`locked`. Candidate root causes:

- `force.py::apply()` returned a mutation but the engine ran it before
  writing? (unlikely — mutations are applied eagerly)
- Observer's `projected_state` was built from a pre-apply snapshot?
- `examine.py`'s description cached via the entity's `description` property
  (which still says "The lock is tarnished")?

Investigation plan:
```bash
uv run token-world tick willowbrook 35 --format json
uv run token-world tick willowbrook 36 --format json
uv run token-world trace willowbrook old_chest locked
```
If `locked` transitioned `True → False` at tick 15 (`force`) but the
observation at tick 35 still says locked, the bug is likely in the
observer's prompt grounding — it was given `locked=False` but pattern-matched
the stale description string. Prompt hardening: observer must NEVER
contradict the projected_state, and the description field should be
considered cosmetic, not canonical.

### F. Data sourcing gaps I hit during session 4 (tooling investigation reflection)

While orchestrating, there were several times I had to read files or the
DB directly because no tool existed for the lookup. Each of these is a
candidate for promotion — and for each I'll name the right surface:

| Investigation | What I did | Right surface → add as |
|---|---|---|
| **Inspect a pending yield's classified action mid-run** | `cat /path/operator_inbox/N.yield.json \| grep ...` | CLI `token-world yield <slug> [--tick N \| --pending]` (live observer) + dashboard "Active Yield" banner (sticky until resolved) |
| **See the classifier's raw response for a refused tick** | `cat diagnostics/tick_N/classification/response.txt` | CLI `token-world tick <slug> <id> --stage classification --raw` (add `--stage` + `--raw` flags to existing command) |
| **Check what just emerged in the universe git log** | `cd <universe>; git log --oneline mechanics/` | CLI `token-world mechanics <slug> --history` (builds on existing `mechanics` command) + dashboard "Mechanic Timeline" column in the registry panel |
| **Check if the run process is still alive** | `ps aux \| grep run_unattended` | Dashboard "Run status" dot (green/yellow/red) in the stats strip — driven by PID file `<universe>/.run-pid` the runner writes on start/removes on exit |
| **Is the engine progressing? tick count / mechanics / inbox in one view** | `ls <universe>/{tick_summaries/ticks,operator_inbox,mechanics}/*.py \| wc -l` | **Dashboard** — always-visible "Run status" panel. CLI `inspect` already provides this one-shot; the gap was a live view. |
| **Spot Mira decompensating before it's 10 turns of gibberish** | re-ran `inspect --last 10` | KPI on the dashboard (see §D — refusal cluster alarm) |
| **Diagnose why a mechanic's check is failing during authoring** | subagent did its own thing | Subagent already has this; the gap would be for a HUMAN author to share the same surface → CLI `token-world validate-mechanic` already exists |
| **Follow Mira's inner state (last_observed, last_moved lists)** | `uv run token-world query-graph willowbrook mira` | That works but is terse. Dashboard "Agent inspector drawer" (listed in v1.1 Phase 11 out-of-scope) would help. Bump to v1.2. |

**Meta-observation:** I reached for the CLI ~80% of the time even while
building a dashboard, because I was automating and scripting. The dashboard
is for the human review pass *after* the work settles. Designing the two
surfaces to complement rather than compete is the real win.

### G. CLI vs MCP vs Dashboard — allocation principle (document this!)

**Rule of thumb (write this into `docs/design/tooling-surfaces.md` next
session):** every feature's primary home is one of CLI / MCP / Dashboard.
Don't duplicate. The other surfaces consume if needed.

| Surface | Best when… | Strengths | Weaknesses |
|---|---|---|---|
| **CLI** | stateless query, scripting, subagent consumption, morning review, diff/audit | pipe-composable; `--format json` uniform; fast; text-centric | not visual; not live |
| **MCP** | operator mutates running simulation (resume/rollback); the operator's "hands" | fits inside Claude Code + Agent SDK surface; LLM-native | narrow — only the live-run actions; not for general queries |
| **Dashboard** | continuous monitoring, spatial/visual, non-developer audience, comparison over time, shareable | visual; reactive; low-friction for non-devs | browser required; not scriptable |

**Decision rules for new features:**

1. Is it a **precise, scripted query** (and/or will a subagent consume it)? → **CLI**.
2. Does it **mutate a running simulation**? → **MCP**.
3. Does it help a **human observer watching the run unfold**, or is it
   inherently **visual/spatial**? → **Dashboard**.
4. Does it live in **more than one bucket**? → **CLI first, dashboard
   consumes CLI JSON.** Do not re-implement in the dashboard.
5. Is it a **one-off tooling gap** I hit while investigating? → promote
   to either CLI or dashboard per rules 1–3. Never leave as ad-hoc bash.

**Next session:** write this as `docs/design/tooling-surfaces.md` and link
from CLAUDE.md (§Documentation Maintenance). Reference it in every phase
CONTEXT.md that adds new features so the surface choice is deliberate.

### H. Willowbrook as a canonical seed universe

User liked Willowbrook. Keep it, refine it. Candidates:

- Add a second agent ("Old Bran") once multi-agent lands. Contrast Mira's
  curiosity against Bran's caution.
- Add a few more entities — a bench with `weathered=True` (inviting repair),
  a chicken coop (inviting feed/collect-egg verbs), a broken gate between
  rooms (inviting fix/jam verbs).
- Extract the emergent mechanics authored overnight (examine, pet, sharpen,
  walk, draw, plant, force, drop, water, hum, lift) back into
  `src/token_world/mechanic/seeds/` so future universes can opt in. The
  ones that are universe-agnostic (examine, pet, sharpen, hum, drop) go
  into the framework; Willowbrook-specific ones (force, plant, water,
  draw with buckets) stay universe-local.

### I. Other deferred items — mine `.planning/`

User asked for a sweep of past planning docs to catch deferred items worth
picking up now. That was not done in session 4. Next session **first thing**:

```bash
# Grep for deferral markers
grep -rn "TODO\|DEFERRED\|backlog\|v1\.2\|v2+\|follow-up" .planning/phases/*/
# Look at phase verification sections
for f in .planning/phases/*/*-VERIFICATION.md; do echo "=== $f ==="; grep -A2 "Known Gap\|Deferred\|Follow-up" "$f" 2>/dev/null; done
# Retrospective candidates
cat .planning/RETROSPECTIVE.md | grep -A3 "Carry"
```

Consolidate into v1.2 REQUIREMENTS candidates. Some likely hits from a quick
mental scan:
- Phase 04.1 IN-04 style cleanup (noted at milestone close)
- Phase 6 belief-overlay structural-key filter v2 integration
- Phase 7 LRA threshold-evaluator expansion
- Phase 5 D-11 NoMatchResult top-K tuning

### J. Prioritised v1.2 backlog

Ranked for one-session execution (pick top N):

1. **A6 inspect headers** — 5 min, trivial polish.
2. **A1 + A2 tick-expansion full text + structured sections** — 45 min, shippable.
3. **A3 + A4 graph canvas bracket fix + located_in edges** — 30 min.
4. **F row 1 — `token-world yield` CLI + dashboard "Active Yield" panel** — 45 min.
5. **C Mira-character-break mitigation (prompt tighten OR auto-halt)** — 30 min.
6. **I deferred-items sweep + v1.2 REQUIREMENTS assembly** — 45 min.
7. **G tooling-surfaces.md doc + CLAUDE.md pointer** — 20 min.
8. **B multi-agent dashboard scaffold (selector + per-tick badge)** — 90 min.
9. **D KPIs panel (quality subpackage + CLI + dashboard)** — 2 h.
10. **E4 observation-drift debug (tick 35)** — 30–60 min depending on root cause.
11. **E3 locked/blocked/inventory_full audit** — 30 min discovery, then variable.
12. **H Willowbrook refinement + extract emergent-as-seed** — 1 h.
13. **E1 + E2 composite actions + mutation-chain visibility** — serious design work; v1.2 decision D-01/D-02 required; parked until reviewed.

---

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
