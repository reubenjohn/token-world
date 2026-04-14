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

**A5. Tick-card expansion should show the side-effect chain tree (per
tick, forward propagation).** Mutations list is flat today. When a
mechanic triggers downstream mechanics (via `ChainExecutionEngine`
children), the tree should be rendered as a tree —
`force_lock(check_pass) → mutates(old_chest.locked=False) → triggered
unlock_chest → mutates(...) → triggered observe_chest`. The
`ExecutionTrace` already carries this; the panel just needs a tree
renderer.

**A5a. Naming clarification — distinguish "side-effect chain" from
"property history".** Today the dashboard has a panel labelled "Causal
chain" — that's `token-world trace <slug> <node> <prop>`, which walks
**backward** through mutations on a single property on a single node:
"why does `mira.energy = 0.72`? Because tick 35 force decremented from
0.75. Because tick 21 water decremented from … " etc. That's a property
history walker.

The new view A5 wants is **forward** propagation **within a single
tick** — which mechanics fired, which mutations they emitted, which
mechanics they in turn triggered. That's a side-effect chain.

These are two distinct surfaces. Recommend renaming:

| Surface | Today's name | Better name | Direction | Scope |
|---|---|---|---|---|
| `token-world trace` + dashboard panel | "Causal chain" | **"Property history"** | backward in time | single property on a single node, all-time |
| Tick expansion side-effect tree (A5) | (does not exist yet) | **"Side-effect chain"** or **"Mechanic chain (this tick)"** | forward within a tick | one tick's full execution tree |

Action: rename `panels/causal_chain.py` → `panels/property_history.py`
(or keep filename, change UI label) and add a new
`panels/side_effect_chain.py` mounted inside the tick-card expansion
(A5). The `token-world trace` CLI may also benefit from a rename to
`token-world history`, but that's a public-API change — flag it but
don't auto-rename without user sign-off.

**A6. `token-world inspect` table is missing column headers.** Rows show up
as `17 refuse - (0 mut) ...` with no `TICK STATUS MECHANIC MUT OBSERVATION`
header. One line fix in `src/token_world/inspect/universe.py`'s table
renderer.

**A7. Dashboard live-refresh resets scroll position inside any scrollable
region.** Confirmed via interactive Playwright walk-through. Both
`panels/tick_stream.py:117 outer.clear()` and
`panels/graph_canvas.py:237 chart_col.clear() + _rebuild_drawer(drawer_col)`
nuke the entire DOM subtree on every poll cycle (2 s for tick stream, 5 s
for graph canvas). Side effects: scroll resets to top inside the tick-card
JSON expansion; scroll resets inside the graph node property drawer; any
text-selection / focus state is lost. **Right pattern:**

- Detect "is anything actually different?" before clearing. Tick stream
  already does a coarse `last_ids` check but still rebuilds inside the
  expansion. Graph canvas doesn't compare at all.
- For change-only deltas, only mount the new tick cards (newest-first
  prepend) and re-bind handlers — don't touch existing cards.
- For the property drawer specifically, NEVER rebuild on poll. The drawer
  contents are user-state; the user is reading them. They should only
  change on a node-click event.
- For the graph canvas Mermaid render, only re-emit `ui.mermaid()` when the
  graph snapshot's `(node_count, edge_count, max_node_mtime)` changes.
  Static graphs render once and stay.

This is a correctness bug, not a polish item — it makes the dashboard
unusable for any reading task longer than 2 seconds. Bump it to the top of
the dashboard fixes.

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

**E1. Composite actions / one-action → many-mechanics.** *Confirmed by
user that this is the intended model:* one resident-agent action can fire
multiple mechanics, and each mechanic's side effects can trigger more
mechanics within the same tick-agent step, bounded by a max chain depth.

State of the implementation:

- ✅ **Side-effect chains exist.** `ChainExecutionEngine` already cascades —
  when M1's mutations match another mechanic's `watches()` (e.g.
  `PropertyChangeMatcher(temperature)`, `EdgeMatcher(located_in)`), that
  mechanic fires too. Bounded by `engine.max_chain_depth=10` from
  `universe.yaml`. Recursion is also DAG-checked via the `seen` set in
  `mechanic.engine._evaluate_chain` to prevent infinite loops.
- ❌ **Multiple PRIMARY mechanics per action does NOT exist.** Today's
  flow: classifier → ONE classified action → `DeterministicMatcher.match()`
  picks ONE winning mechanic by score → that one mechanic runs (then its
  cascades). For "I open the chest and take the key" → two real intents,
  the pipeline collapses to one verb (whichever wins the classifier's
  pick) and the second never fires.

Design choices for closing the gap (v1.2 D-01):

1. **Classifier emits an `actions: [...]` list.** Backward-compatible:
   single-action wraps as a 1-element list. Engine iterates each, matching
   and applying in order. Each sub-action carries its own verb / target /
   indirect_object / params.
2. **Matcher returns top-K mechanics whose check passes.** Score still
   orders, but instead of picking 1 winner, the decider runs the top-K
   sequentially (with K bounded). Riskier — `check()` may pass for
   accidentally-overlapping mechanics that weren't meant to fire together.
3. **New `ActionDecomposer` stage** between classifier and matcher. Its
   job: take "I open the chest and take the key" and split into
   `[(open, chest), (take, key)]`. Costs an extra LLM call per multi-verb
   action but keeps the matcher contract clean.

Recommended: option 1 (classifier emits list). Lowest blast radius — the
classifier already understands sequential English ("and", "then"); no new
component; the matcher and chain engine are unchanged. Bumps
`SCHEMA_VERSION` on the classifier output. Subagent prompts for mechanic
authoring should also be updated to expect to be invoked once per
sub-action when a yield happens within a multi-action tick.

**E2. Mutation chains / propagating side effects — visibility.** The
chain mechanism (above) is built; what's missing is **observability**.
Today the dashboard flattens the chain. Action items:

- Render the `ExecutionTrace` tree in the tick-card expansion (A5):
  `force_lock(check_pass) → mutates(old_chest.locked=False) → triggered
  unlock_chest(check_pass) → mutates(...) → ...`. Include the
  `truncated`/`max_depth_reached` flags as warnings when chains hit the
  cap.
- Audit which mechanics declare `watches()` beyond `VerbMatcher` —
  `environmental_reaction` watches `PropertyChangeMatcher(temperature)`,
  `position_sync` watches `EdgeMatcher(located_in)`. Only a few. More
  seeded chains would make emergence richer (e.g. a watcher that fires
  when any agent's `mood` changes, or when a `contains` edge appears).

**E5. Energy-economy coherence in Willowbrook authored mechanics.** User
asked for an audit of how the autonomously-authored mechanics handle
`mira.energy`. Findings (read directly from
`~/.local/share/token_world/universes/willowbrook/mechanics/`):

| Mechanic | Reads `energy`? | Writes `energy`? | Δ | Direction | Clamp | Read-before-write | Default-on-missing |
|---|:-:|:-:|---|---|---|:-:|---|
| `force` | yes (used as skill proxy) | yes | −0.03 | spend | `[0,1]` via `_clamp` | yes | **no — skips entirely** |
| `sharpen` | no (only writes) | yes | −0.05 | spend | `[0,1]` | yes | **no — skips** |
| `pet` | no | yes | +0.02 | recover | `[0,1]` | yes | **yes — seeds 0.02** |
| `hum` | no | yes | +0.02 | recover | `[0,1]` | yes | **yes — seeds 0.02** |
| `walk`, `draw`, `plant`, `drop`, `water`, `lift`, `examine` | no | no | — | — | — | — | — |

**(1) Scale consistency:** ✅ All values float in `[0,1]`; clamps are
identical (`_clamp(value, 0.0, 1.0)`). No floor/ceiling violations
possible. Step sizes (0.02 / 0.03 / 0.05) are coherent and small enough
that the gauge changes meaningfully but not jarringly across a session.

**(2) Independent or copied?** Mostly independent, with one likely copy.
Each subagent invented its own constant name:
- `force.py`: `_ENERGY_COST: float = 0.03`
- `sharpen.py`: `_ENERGY_DECREMENT: float = 0.05`
- `pet.py`: `_ENERGY_INCREMENT: float = 0.02`
- `hum.py`: `_ENERGY_INCREMENT: float = 0.02` ← same name AND value as
  `pet.py`. `hum.py` was authored AFTER `pet.py` per the universe git log
  → likely the subagent copied the pet pattern. Otherwise the four
  mechanics arrived at the gauge convention independently — which is
  remarkable but also a smell: there's no shared convention to hold the
  line as the corpus grows.

**(3) Floor/ceiling violations:** ✅ None. Every mutation passes through
`_clamp(value, 0.0, 1.0)`. Energy cannot escape `[0, 1]`.

**(4) Reads current value before writing?** ✅ All four read first, only
emit a mutation if the clamped result is different from the current value.
This avoids spurious mutations and matches the "read-modify-write" pattern
the seeds taught.

**Coherence issues / missing guard rails:**

- **No shared constant or shared module.** Each `_ENERGY_*` lives in its
  own file. Tweaking the economy (e.g. "make all costs 1.5×") requires
  editing N files. Recommend a universe-local
  `<universe>/mechanics/_economy.py` (already follows the `_helpers.py`
  underscore-skip convention) defining `ENERGY_COST_LIGHT = 0.02`,
  `ENERGY_COST_HEAVY = 0.05`, etc. Existing mechanics get migrated in a
  separate authoring pass.
- **Inconsistent naming.** COST / INCREMENT / DECREMENT all describe the
  same concept. Standardize on `ENERGY_COST_*` (positive deltas =
  spending) or `ENERGY_DELTA_*` (signed).
- **`pet` and `hum` seed `energy=Δ` on a missing property.** If a non-agent
  entity ever ended up as an actor (e.g. via mechanic chain), `pet`/`hum`
  would conjure an `energy` gauge on it. Should be gated on
  `actor_props.get("type") == "agent"`.
- **No mechanic uses low energy as a precondition.** `force` uses energy
  to compute success *probability*, but a totally exhausted Mira
  (`energy=0`) can still attempt to force a lock. Decision: should low
  energy gate certain actions (e.g. force, sharpen) rather than just
  reduce success rate? Surface for v1.2.
- **6 of 11 mechanics don't touch energy at all** (`walk`, `draw`, `plant`,
  `drop`, `water`, `lift`, `examine`). Most of these are physical
  exertions and probably should have a small cost. Indicates the subagents
  weren't told "every primary action costs energy" — only included a cost
  when the prompt explicitly asked. If we want a coherent economy, the
  yield-handler subagent prompt
  (`.planning/agent-prompts/yield-handler.md`) should mention "consider an
  appropriate energy cost".
- **Force's "energy-as-skill" model is one-off.** Only `force` uses
  energy as a probability scaler. If "energy gates skill" is a desired
  recurring pattern, formalize as a helper in `_economy.py` so future
  mechanics can opt in without re-deriving the formula.

**Risk:** As emergent mechanics arrive, every new author will reinvent the
gauge. Today's coherence (everyone happens to land in `[0,1]`) is luck
plus the seed mechanics' cited example. Promote `_economy.py` before the
corpus diverges.

**E6. Tick 33–35 ordering anomaly — REAL ENGINE BUG.** User flagged.
Investigation finding: tick ordering is *reliable*, but there is a real
engine-level bug in how primary-mechanic check failures are recorded.

Sequence (verified via `token-world tick willowbrook 33/34/35`):

| Tick | UTC | Action verb | Decision | Mutations | Observation |
|---|---|---|---|---|---|
| 33 | 10:00:18 | `lift` | **YIELDED** to operator (no `lift` mechanic existed yet) | — | — |
| 34 | 10:05:14 | `lift` (re-run after operator authored `lift.py`) | **status:EXECUTED, refused:false, matched=lift** | **0** | "The chest remains as it was — squat, iron-bound, and locked tight." |
| 35 | 10:05:20 | `force` | EXECUTED, mechanic=force | 3 (chest.locked True→False, mira.last_forced, mira.energy 0.75→0.72) | (success narrative) |

**Tick ordering:** ticks 34 and 35 differ by 6 seconds, not the same as
user remembered. So no race / flush ordering issue — ticks 33→34→35 are
chronologically and causally correct.

**Mechanic logic:** `lift.py:176-180` correctly checks
`target_props.get("locked") is True` and returns
`ctx.refuse("mechanic_check_failed", {"reason": "target is locked"})` —
which yields a `CheckResult(passed=False)`. This is the right behaviour.
`lift` did NOT silently succeed — it correctly produced zero mutations
and an honest observation that the chest stayed shut.

**Engine bug:** `engine.py::_handle_execute` does NOT branch on
`primary_trace.root.check_result.passed`. After the primary mechanic's
check fails, the code path continues normally to the observer + writes
the tick summary with `refused: false` and `matched_mechanic_id: "lift"`.
There's no `if not primary_trace.root.check_result.passed: convert to
RefuseDecision` branch — only `conservation_violation` and `engine_error`
trigger the refuse path inside `_handle_execute`. So a primary-check
failure is recorded as "executed with no mutations," which is a lie.

This is the same root cause as user's earlier intuition about tick 35
("the observation said locked"). Tick 34's observation was correct given
graph state ("the chest remains locked"); the *tick summary record* is
what's wrong (says EXECUTED when functionally REFUSED).

**Fix:** in `engine.py::_handle_execute`, after `primary_trace = chain_engine.execute(...)`,
check `primary_trace.root.check_result.passed`. If `False`, write a
`RefuseDecision(reason_code="mechanic_check_failed", details={"reason": ...,
"mechanic_id": decision.mechanic_id})` instead of continuing to passive
sweep + observer-as-execute. The observer can still synthesize a refusal
observation, but the tick summary records the truth: refused, not
executed.

This is a small, contained engine fix. Affects:
- `src/token_world/engine/engine.py::_handle_execute` — add the branch
- `src/token_world/playtest/scorer.py` — score should not double-count
  refused mechanics as "no mutations + low groundedness"; this is now an
  honest refuse
- Existing tests that depend on a mechanic with failing check returning
  `kind="ok"` will need updating
- Several recently-authored Willowbrook ticks (e.g. 22 `sharpen` against
  the chest, 38 `examine` of the well from inside cottage) likely have
  the same false-EXECUTED record. Optional: re-run those tick summaries
  with a corrected engine to clean the historical record.

This bug + the observation-grounding question (E4) both point to the
same systemic issue: the engine treats "check failed at execution time"
as a soft no-op rather than a hard refusal. Surface as v1.2 D-03.

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

Ranked for one-session execution (pick top N). **A7 leapfrogs to top —
the scroll-reset bug makes the dashboard unusable for any reading task
longer than 2 seconds.**

1. **E6 engine: convert primary check-fail into RefuseDecision** — 30 min
   + tests. Fixes tick-summary lying about EXECUTED ticks that actually
   refused at check time. Foundational; downstream KPIs and scorer all
   depend on truthful tick records.
2. **A7 dashboard scroll-preservation on poll** — 60 min. Stop blowing
   away DOM in tick stream + graph canvas. Drawer never rebuilds on poll.
3. **A6 inspect headers** — 5 min, trivial polish.
4. **A1 + A2 tick-expansion full text + structured sections** — 45 min.
4a. **A5 + A5a side-effect chain tree in tick expansion + rename "causal chain" → "property history"** — 60 min. Renaming is mostly mechanical (panel file + UI label, leave CLI alone for now); side-effect tree renders the existing `ExecutionTrace`.
4. **A3 + A4 graph canvas bracket fix + located_in pseudo-edges** — 30 min.
5. **F row 1 — `token-world yield` CLI + dashboard "Active Yield" panel** — 45 min.
6. **C Mira-character-break mitigation (prompt tighten OR auto-halt)** — 30 min.
7. **E5 `_economy.py` extraction in Willowbrook + migration of force/sharpen/pet/hum** — 30 min.
8. **K1 + K2 process artefacts: write `docs/quality/dashboard-qa-checklist.md` + `docs/quality/sim-quality-rubric.md`** — 30 min.
9. **I deferred-items sweep + v1.2 REQUIREMENTS assembly** — 45 min.
10. **G tooling-surfaces.md doc + CLAUDE.md pointer** — 20 min.
11. **B multi-agent dashboard scaffold (selector + per-tick badge)** — 90 min.
12. **D KPIs panel (quality subpackage + CLI + dashboard)** — 2 h.
13. **E4 observation-drift debug (tick 35)** — 30–60 min depending on root cause.
14. **E3 locked/blocked/inventory_full audit** — 30 min discovery, then variable.
15. **H Willowbrook refinement + extract emergent-as-seed** — 1 h.
16. **E1 composite actions (D-01 design first, then implementation)** — design 1 h, implementation 3-4 h. Architectural; do not rush.
17. **E2 mutation-chain visibility in dashboard (depends on A5)** — 1 h.

---

## K. Process Gaps — Why I Missed These Bugs Myself (and Tools To Add)

Honest reflection. User flagged six issues during the demo that I should
have caught before claiming the dashboard was "shipped." For each I owe
the next session both the *why* and the *fix*.

| Bug | Why I missed it | Tool / instruction to add |
|---|---|---|
| **A7 scroll-reset on poll** | I treated `playwright_take_screenshot` as the entire validation step. Never scrolled inside any panel, never waited through a refresh cycle. Code review of `outer.clear()` on every `ui.timer` tick would have flagged "this kills scroll" — but I didn't read the panel code with a "live UI hostility" lens. | **K1.** Write `docs/quality/dashboard-qa-checklist.md` — required for every dashboard PR: scroll inside each scrollable region, wait through 2 refresh cycles, click each interactive element, resize viewport, assert against a design-intent rubric. Convert the checklist to a Playwright test file (`tests/test_dashboard/test_qa_interactive.py`) that fails CI when poll-rebuild kills focus or scroll. |
| **A1/A2 tick truncation in expansion** | Builder-mode reading. Screenshot literally showed `"…Th…"` and I parsed it as "the label is rendered, fine." Never asked "would a user expect the full thing here?" | **K1** covers it. Plus add to checklist: "compare what the user expects against what the panel shows; do they match?" |
| **A3 `mira &[agent&]` escape bug** | Saw it, classified as cosmetic, moved on. | **K2** rubric — define what counts as "rendering correctness." Includes: no entity-escape leakage in any user-facing label. |
| **A4 missing `located_in` edge in graph** | I had no rubric for "what semantic edges should an observer expect?" Read the graph by what's *drawn*, not what's *missing*. | **K2** — list expected semantic surfaces per panel. Graph canvas: every property whose value is a known node id should render as an edge (or be explicitly excluded). |
| **A6 inspect lacks headers** | Used CLI as an oracle, not a UX surface. Never read its output as a fresh user. | **K1** also covers CLI: include "run each command, read its output as someone seeing it for the first time" in the QA pass. |
| **E4 tick-35 unlocked-but-locked** | Focused on yield-rate / mechanic-count, not narrative-graph consistency. | **K2** sim-quality rubric: per-tick check "does the observation contradict the projected_state?" If yes, score it as a grounding violation. The current `playtest.scorer.groundedness` partially does this; need to extend + surface as a CI-level check on every overnight run. |
| **C Mira character-break** | Noticed it, mentioned in report, framed as "natural wind-down" instead of "quality bug." | **K2** rubric again: meta-narration markers ("framework", "yield", "system", "mechanic", "operator", "scenario") in agent action_text are red-flags. Track per-run; alarm at threshold. |

### K1. `docs/quality/dashboard-qa-checklist.md` — to-write

Required passes before claiming a dashboard panel "shipped":

1. **Initial render** — page loads at intended viewport (1280, 1440), no
   layout breakage.
2. **Scroll preservation** — scroll to mid-position inside each
   scrollable region, wait 3 × poll interval, scroll position must not
   change.
3. **Focus / selection preservation** — click into a text input, wait 3 ×
   poll interval, focus must persist; same for text selection in any
   read-only region.
4. **Interactive elements** — every button, expansion arrow, dropdown,
   click-target gets clicked at least once. Capture screenshot in each
   triggered state.
5. **Drawer / modal state** — open the property drawer, wait 3 × poll
   interval, drawer must stay open with same content.
6. **Polling no-op** — instrument `_rebuild` to log when it actually
   changes the DOM. During a 30s idle window with no new ticks, log line
   count must be 0.
7. **Empty / missing universe** — point dashboard at non-existent slug,
   page must render a friendly error rather than a stack trace.
8. **Rendering correctness** — labels must not contain entity-escape
   leakage (`&lt;`, `&#91;`); colors map to the documented `classDef`;
   graph contains every semantic edge implied by node properties (e.g.
   any property whose value is a known node id).
9. **Run as automated test.** The above is encoded as
   `tests/test_dashboard/test_qa_interactive.py`. It runs Playwright
   against a fixture universe + a synthetic poll cycle, asserts each
   item.

### K2. `docs/quality/sim-quality-rubric.md` — to-write

A formal "is the simulation healthy?" definition. Every overnight run
ends with `token-world quality <slug>` printing the rubric scorecard.
CI gates a release on the scorecard staying above thresholds.

Dimensions:

- **Groundedness** — observation must not contradict projected_state.
  Source: Phase 6 scorer + per-tick observer cross-check.
- **Character stability** — agent action_text must not contain
  meta-narration markers (configurable list). Score = 1 − fraction of
  recent turns containing markers.
- **Action coherence** — longest streak without a refuse; mean refuse
  rate per 10-tick window.
- **Vocabulary growth** — novel verbs / 10 ticks (not too low, not too
  high — both are bad).
- **Conservation** — count of conservation-violation rollbacks; should
  trend to zero.
- **Graph fan-out** — average edges/node over time; richer worlds
  trend up.

CI gate: a run is "healthy" if all dimensions stay in green ranges for
the last 50 ticks. Otherwise the morning report flags the run as
degraded with the failing dimension named.

### K3. Playwright tool routine (instruction artefact)

The Playwright MCP routine I used (`navigate → screenshot → close`) is
insufficient. Standard routine going forward:

```
navigate(url)
resize(1280, 800) AND resize(1920, 1080)  # responsiveness
for each scrollable region:
    scroll(region, 50%)
    wait(2 × poll_interval)
    assert(scroll position unchanged)
for each interactive element:
    click()
    wait_for(visible_change)
    screenshot(state_name)
take_screenshot(fullPage=true)  # final overall
close()
```

Document this in `docs/quality/playwright-routine.md` and reference from
the K1 checklist.

### K4. End-of-build cooldown — "user pass"

After completing a build (especially UI work), explicitly switch from
**builder mode** to **user mode** for a 5-minute pass. Sit with the
output, click around, look for surprise. The discipline: assume nothing,
question every truncation / shorthand / clipped label as "would a real
person expect this?"

This is hard to enforce as a tool, but writing the K1/K2 checklists puts
the pattern in our muscle memory. Future overnight orchestrators should
spawn a dedicated "QA subagent" that runs the K1 + K2 routines after
each build subagent reports done.

---

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
