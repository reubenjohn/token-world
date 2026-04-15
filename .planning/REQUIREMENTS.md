# Requirements — Token World v1.2 (Quality + Depth)

*Scoped by MORNING-HANDOFF §§I–J after session 5 feedback + session-4 close.
This document **supersedes** the v1.1 REQUIREMENTS (REQ-OPCLI / REQ-EMERGE /
REQ-DASH / REQ-WARMUP) which all landed in session 4. The v1.1 requirements
are archived in git at commit `152ce54`; the current focus is v1.2.*

**Milestone vision:** v1.1 proved emergence works — 11 mechanics authored
autonomously in Willowbrook overnight. v1.2 hardens the truthfulness of the
loop (engine bugs, observability, energy economy, dashboard UX) and opens the
door to richer play (composite actions, multi-agent scaffold, KPIs).

Everything here is derived from MORNING-HANDOFF §I (deferred sweep, 16 →
4 v1.2 candidates) and §J (prioritised v1.2 backlog, 17 ranked items).

---

## v1.2.0 Warm-up Delivered

These §J items landed via direct-edit / GSD-quick passes *before* the v1.2
milestone was formally scoped. They are listed here for traceability so the
REQ-V12-* namespace covers everything delivered under the v1.2 banner.

### REQ-V12-ENGINE-01 — Convert primary-mechanic check failure into RefuseDecision

The engine recorded `status=executed, refused=false` for ticks where the
primary mechanic's `check()` returned `passed=False` — a lie in the tick
summary. Downstream KPIs, scorers and CI gates were corrupted by these
false-EXECUTED records. MORNING-HANDOFF §E6 documented the fix path.

**Acceptance criteria:**
- `engine.py::_handle_execute` branches on `primary_trace.root.check_result.passed`
  and emits a `RefuseDecision(reason_code="mechanic_check_failed", ...)` when
  the primary check fails.
- Tick summary JSON for primary-check-fail ticks records `refused=true`.
- Existing tests updated; regression test added for the failing-check path.
- Downstream consumers (`playtest.scorer`) stop double-counting refused
  mechanics as "zero mutations + low groundedness".

**Status:** Shipped
**Source:** MORNING-HANDOFF §J #1, §E6 ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD (shipped via commit `afc5c73` pre-milestone-scaffolding)

### REQ-V12-DASHBOARD-01 — Scroll + focus preservation across poll cycles

`panels/tick_stream.py` and `panels/graph_canvas.py` called
`outer.clear()` / `chart_col.clear()` on every 2–5s poll, rebuilding the
entire DOM subtree and resetting every user scroll/focus/selection state.
This made the dashboard unusable for any reading task longer than one poll
interval (§A7, §K1).

**Acceptance criteria:**
- Tick stream polls prepend new cards without clearing existing ones.
- Graph canvas skips Mermaid re-render when `(node_count, edge_count,
  max_node_mtime)` is unchanged.
- Property drawer never rebuilds on poll — only on user node-click.
- Playwright QA routine from §K1 documents what "no scroll regression"
  means at CI time.

**Status:** Shipped
**Source:** MORNING-HANDOFF §J #2, §A7, §K1 ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD (shipped via commit `d31090d` pre-milestone-scaffolding)

### REQ-V12-CLI-01 — `token-world inspect` table column headers

The recent-ticks table rendered as `17 refuse - (0 mut) ...` with no
`TICK STATUS MECHANIC MUT OBSERVATION` header row (§A6). A fresh reader
could not decode the columns.

**Acceptance criteria:**
- `inspect` table renderer emits a header row for the recent-ticks
  block.
- JSON output unchanged.

**Status:** Shipped
**Source:** MORNING-HANDOFF §J #3, §A6 ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD (shipped via commit `fa68200` pre-milestone-scaffolding)

### REQ-V12-DASHBOARD-02 — Tick expansion renders structured sections + full text

Expanded tick cards were showing re-truncated observations and dumping raw
JSON (§A1, §A2). The expanded view should carry: Classification, Decision,
Mutations, Observation (full, untruncated), Metadata, and a collapsed Raw
JSON for dev use.

**Acceptance criteria:**
- Tick expansion renders six clearly-labelled sections.
- Observation text is never truncated inside the expansion; newlines
  preserved via `white-space: pre-wrap` (or equivalent).
- Mutations grouped by target as `target.prop: old → new`.
- Raw JSON is a collapsed sub-expansion.

**Status:** Shipped
**Source:** MORNING-HANDOFF §J #4, §A1, §A2 ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD (shipped via commit `d31090d` pre-milestone-scaffolding)

### REQ-V12-DASHBOARD-03 — Side-effect chain tree in tick expansion + rename causal panel

A5 wanted forward-propagation-within-a-tick visibility of the
`ExecutionTrace` tree. A5a clarified the naming:
- `token-world trace` + the existing panel walk **backward through a
  single property's mutation history** → rename to *property history*.
- The new tick-expansion view walks **forward through one tick's full
  mechanic chain** → new *side-effect chain* panel.

**Acceptance criteria:**
- New `panels/side_effect_chain.py` mounts inside the tick-card
  expansion; reads `diagnostics/tick_<id>/execution/trace.json` and
  renders the `ExecutionTrace` as a tree with depth-indent styling.
- Warning chips for `truncated` / `max_depth_reached` flags.
- `panels/causal_chain.py` → `panels/property_history.py` (git mv
  preserved). UI label "Causal chain" → "Property history".
- `token-world trace` CLI intentionally keeps its name (public API
  stability); documented that the dashboard label has diverged.

**Status:** Shipped
**Source:** MORNING-HANDOFF §J #4a, §A5, §A5a ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD (shipped via commit `d31090d` pre-milestone-scaffolding)

### REQ-V12-DASHBOARD-04 — Graph canvas label escape + located_in pseudo-edges

`escape_label` partially-escaped `[` / `]` in agent labels, producing
`&[agent&]`. Mira's `located_in=cottage_interior` was stored as a property
rather than an edge, so the Mermaid graph showed her dangling off the
diagram (§A3, §A4).

**Acceptance criteria:**
- No entity-escape leakage in any user-facing graph label.
- Agent labels render via parentheses or a colon-delimited form
  (`mira : agent`).
- Synthesised dashed `located_in` pseudo-edges appear between any agent
  node whose property names a known room node. Generalise to any
  property whose value matches a known node id (small refactor).

**Status:** Shipped
**Source:** MORNING-HANDOFF §J #4, §A3, §A4 ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD (shipped via commit `6101da0` pre-milestone-scaffolding)

### REQ-V12-PLAYTEST-01 — Resident in-character recovery + auto-halt on K refuses

Mira decompensated around tick 44 of round 2 ("I notice the universe
framework has been activated…"). §C proposed four mitigations; two landed
as the quick win: a system-prompt recovery clause and an auto-halt when
the last K observations are all refused.

**Acceptance criteria:**
- Resident system prompt contains an in-character recovery clause
  ("stay in character when nothing responds; never narrate the simulation
  framework itself").
- `scripts/run_unattended.py` halts cleanly when the last K observations
  are all `refused=true`. K is configurable.
- Tests cover both prompts and the halt condition.

**Status:** Shipped
**Source:** MORNING-HANDOFF §J #6, §C ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD (shipped via commit `0fcd614` pre-milestone-scaffolding)

### REQ-V12-ECONOMY-01 — Willowbrook `_economy.py` shared constants module

6 of 11 authored mechanics don't touch `energy` at all; 4 reinvented
their own `_ENERGY_COST` / `_ENERGY_DECREMENT` / `_ENERGY_INCREMENT`
constants. §E5's audit flagged that the corpus will diverge as new
mechanics arrive. Shared constants live in a universe-local
`_economy.py` (follows the `_*.py` underscore-skip convention).

**Acceptance criteria:**
- `<universe>/mechanics/_economy.py` defines canonical constants
  (`ENERGY_COST_LIGHT`, `ENERGY_COST_HEAVY`, …).
- Existing `force.py`, `sharpen.py`, `pet.py`, `hum.py` import from the
  module; per-file constants are deleted.
- Yield-handler prompt hints at the convention so new authors opt in.

**Status:** Shipped
**Source:** MORNING-HANDOFF §J #7, §E5 ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD (shipped pre-milestone-scaffolding; `_economy.py`
observed at `~/.local/share/token_world/universes/willowbrook/mechanics/`)

### REQ-V12-QUALITY-01 — Dashboard QA checklist + sim-quality rubric docs

§K1 and §K2 were process gaps: "why did I miss these bugs?". The answer
is codifying the QA pass as a written checklist + rubric that CI /
future agents can run mechanically instead of via instinct.

**Acceptance criteria:**
- `docs/quality/dashboard-qa-checklist.md` captures the 9-point
  Playwright routine from §K1.
- `docs/quality/sim-quality-rubric.md` captures groundedness / character
  stability / action coherence / vocabulary growth / conservation /
  graph fan-out dimensions from §K2.
- Both are linked from `docs/design/architecture.md` and CLAUDE.md so
  future agents find them.

**Status:** Shipped
**Source:** MORNING-HANDOFF §J #8, §K1, §K2 ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD (shipped via commit `890b464` pre-milestone-scaffolding)

### REQ-V12-DOCS-01 — `docs/design/tooling-surfaces.md` allocation principle

§G crystallised the "CLI vs MCP vs Dashboard" decision rule: every
feature's primary home is exactly one surface; the others consume. The
rule needed a home so future phases reach for it deliberately.

**Acceptance criteria:**
- `docs/design/tooling-surfaces.md` documents the allocation principle
  and the decision rules.
- CLAUDE.md §Documentation Maintenance links to it.
- Future phase CONTEXT.md files reference the rule when introducing a
  new user-facing feature.

**Status:** Shipped
**Source:** MORNING-HANDOFF §J #10, §G ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD (shipped via commit `3eec1c5` pre-milestone-scaffolding)

### REQ-V12-TOOLING-01 — `scripts/commit.sh` accepts explicit paths

`git add -A` inside `commit.sh` swept another subagent's WIP into
commits twice in session 4 (Anti-Pattern 5). The fix: accept an optional
paths list and delegate to targeted `git add`.

**Acceptance criteria:**
- `scripts/commit.sh <msg-file> [paths...]` signature.
- Without paths, behaviour unchanged (back-compat).
- With paths, only those paths are staged.
- CLAUDE.md Script Catalog row updated.

**Status:** Shipped
**Source:** MORNING-HANDOFF §J (tooling debt), Anti-Pattern 5
([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD (shipped via commit `958a28b` pre-milestone-scaffolding)

### REQ-V12-CLI-02 — `token-world yield` CLI + dashboard "Active Yield" banner

While orchestrating, the author reached for `cat /.../operator_inbox/N.yield.json`
because there was no tool to inspect a pending yield mid-run (§F row 1).
Belongs on the CLI per §G (stateless query) with a complementary sticky
banner in the dashboard.

**Acceptance criteria:**
- `token-world yield <slug> [--tick N | --pending]` command.
- `--format json` uniform.
- Dashboard "Active Yield" banner renders while a yield is unresolved,
  sticky across poll cycles (hides when inbox empties).
- Test: smoke test against a fixture universe with a staged yield JSON.

**Status:** Shipped (session 6)
**Source:** MORNING-HANDOFF §J #5, §F row 1; SESSION-6-REPORT commit row
**Target phase:** TBD (shipped via commit `7435536` pre-milestone-scaffolding)

### REQ-V12-ENGINE-02 — Observation-grounding drift investigation (tick 35)

The chest was unlocked by `force` at tick 15 but tick 35's observation
still said "locked" (§E4). Root cause landed in session 6: observer was
narrating from the intent `action_text` rather than the applied mutation
list, so it pattern-matched the stale `description` string over the fresh
`projected_state.locked=False`. Fix in commit `e110e2c` added per-mutation
bullets to the observer prompt and an OUTCOME CONSISTENCY system-prompt
clause; three regression tests added; universe prompt hashes refreshed.

**Acceptance criteria:**
- Root cause identified via `token-world tick <id> --format json` + trace
  walk. **Done — narrated from `action_text`, not mutations.**
- Observer prompt receives per-mutation `target.prop: old -> new` bullets.
- Observer system prompt contains an OUTCOME CONSISTENCY clause forbidding
  contradiction of the mutation list.
- Regression tests: 3 scenarios cover mutation-consistent narration,
  refuse-narrative flavour preservation, and no-mutation idle flavour.

**Status:** Shipped (session 6)
**Source:** MORNING-HANDOFF §J #13, §E4; SESSION-6-REPORT commit row
**Target phase:** TBD (shipped via commit `e110e2c` pre-milestone-scaffolding)

---

## v1.2.0 Active Backlog

Not yet landed. Ordered roughly by §J priority. Each requirement lists a
target phase of `TBD` until a ROADMAP row lands. The user's session-6
mandate was **inclusive**: every remaining requirement across the project
goes here unless it's truly far-fetched (those live in
`.planning/backlog/v2.0-REQUIREMENTS.md` as REQ-V20-*).

### REQ-V12-DASHBOARD-05 — Multi-agent scaffold (selector + per-tick badge)

Dashboard should be *ready* for multi-agent even while D-17 keeps the
engine single-agent. §B proposes an agent selector + per-card agent
badge + graph-canvas selected-agent outline + per-agent KPIs.

**Rationale:** richer emergence arrives with Bran-the-cautious-elder or
similar. Single-agent is still the v1.x baseline (D-17); the dashboard
needs the hooks so landing multi-agent in the engine is a small cutover
instead of a re-architecture.

**Acceptance criteria:**
- Agent-selector dropdown above the tick stream, default "All" (or the
  only agent).
- Per-tick `· actor_id` badge on every card.
- Graph-canvas selected-agent node outline + highlighted `located_in`
  edge (reuses pseudo-edges from REQ-V12-DASHBOARD-04).
- Per-agent KPI rollup (yield rate per agent) surfacing in the stats
  strip when >1 agent exists.
- Tests: fixture universe with two agent nodes; Playwright selector
  change filters the tick feed.

**Status:** Active
**Source:** MORNING-HANDOFF §J #11, §B ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD

### REQ-V12-QUALITY-02 — Simulation-quality KPIs (subpackage + CLI + panel)

§D proposed eight KPIs covering groundedness, character stability,
action coherence, refusal cluster alarms, vocabulary growth, novel
subtype rate, graph fan-out, and conservation drift. Surface allocation:
CLI is the canonical producer (`token-world quality <slug>`); the
dashboard renders a Quality panel consuming its JSON. Do not duplicate.

**Rationale:** overnight runs need an automatable scorecard; CI must be
able to gate a release on the rubric staying above thresholds (§K2).
E6 and C both trace to this systemic gap.

**Acceptance criteria:**
- `src/token_world/quality/` subpackage owns the KPI definitions.
- `token-world quality <slug>` prints the scorecard; `--format json`
  for scriptability.
- Dashboard "Quality" panel consumes the JSON; never re-computes.
- CI wires a threshold check into overnight-run post-processing.
- Unit tests per KPI, integration test against a fixture universe.

**Status:** Active
**Source:** MORNING-HANDOFF §J #12, §D, §K2 ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD

### REQ-V12-ENGINE-03 — Engine audit: `locked` / `blocked` / `inventory_full` must be emergent

§E3 flagged a smell: any engine-level logic that hard-codes these
property names betrays the graph-is-ground-truth invariant. The audit
needs to replace each such reference with a mechanic-level assertion.

**Rationale:** emergent universes must not see the engine privilege
specific property names. Mechanics should own the semantics.

**Acceptance criteria:**
- Grep sweep against `src/token_world/engine/` and
  `src/token_world/mechanic/` (excluding `seeds/`) produces zero
  semantic references to `locked` / `blocked` / `inventory_full`.
- Any legitimate reads (framework-level visibility filters, etc.) are
  documented as reads-only with a code comment.
- Regression test: a mechanic can use an arbitrary property name
  (`warded`, `trapped`) and receive identical engine treatment.

**Status:** Active
**Source:** MORNING-HANDOFF §J #14, §E3 ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD

### REQ-V12-SEEDS-01 — Willowbrook refinement + extract emergent-as-seed

§H: keep Willowbrook; promote universe-agnostic overnight-authored
mechanics (examine, pet, sharpen, hum, drop) back into
`src/token_world/mechanic/seeds/`. Universe-specific ones (force, plant,
water, draw-with-buckets) stay universe-local. Add a bench with
`weathered=True`, a chicken coop (feed/collect-egg hooks), a broken
gate (fix/jam hooks).

**Rationale:** session 5 user liked Willowbrook and wants it refined as
the canonical seed universe. Promoting agnostic mechanics reduces the
cold-start authoring load for new universes.

**Acceptance criteria:**
- 5 agnostic mechanics added to `src/token_world/mechanic/seeds/` with
  tests.
- 3 new entities in `scripts/seed_starter_universe.py` (bench + coop
  + gate) with hook properties.
- Seed-starter output has a `--preserve-mechanics` flag so re-seeding
  doesn't delete authored mechanics (anti-pattern captured in §L).
- Regression test: reseeding with `--preserve-mechanics` preserves the
  authored corpus.

**Status:** Active
**Source:** MORNING-HANDOFF §J #15, §H ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD

### REQ-V12-ENGINE-04 — Composite actions (one-action → many-mechanics)

§E1 confirmed the intended model: one agent action can fire multiple
primary mechanics within a tick. Today's pipeline collapses to one
verb (classifier picks one winner). Recommended: option 1 — classifier
emits an `actions: [...]` list; engine iterates each, matching and
applying in order. Design + implementation.

**Rationale:** "I open the chest and take the key" is a single agent
utterance with two intents. Composite actions unblock richer narrative
without changing the mechanic protocol.

**Acceptance criteria:**
- Design doc (v1.2 D-01) chooses between the three options in §E1.
- Classifier emits `actions: [...]`; single-action wraps as 1-element.
- Engine iterates each sub-action; back-compat preserved via the wrap.
- Classifier `SCHEMA_VERSION` bumped.
- Yield-handler prompt updated so mechanic-authoring subagents know
  they're invoked once per sub-action.
- Tests: multi-verb inputs produce multi-mechanic traces; back-compat
  preserved for single-verb inputs.

**Status:** Active
**Source:** MORNING-HANDOFF §J #16, §E1 ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD

### REQ-V12-DASHBOARD-06 — Mutation-chain tree visibility in dashboard

§E2: chain mechanism is built (`ChainExecutionEngine`); the dashboard
flattens it. After REQ-V12-DASHBOARD-03 lands the `ExecutionTrace` tree
renderer, audit which seed mechanics declare `watches()` beyond
`VerbMatcher`. Currently only `environmental_reaction` and
`position_sync`. Seeding more chain-producing mechanics makes emergence
richer.

**Rationale:** forward-propagation visibility lands with
REQ-V12-DASHBOARD-03; the richness of the chains depends on the seed
corpus itself. This requirement tracks the seed audit, not a new
renderer.

**Acceptance criteria:**
- Registry audit report: every seed mechanic's `watches()` spec
  documented.
- At least 3 new `PropertyChangeMatcher` / `EdgeMatcher` seed mechanics
  land (e.g. mood-change watcher, contains-edge watcher, temperature
  watcher).
- Willowbrook overnight-run sample shows non-trivial chain depth in the
  dashboard tree.

**Status:** Active (depends on REQ-V12-DASHBOARD-03 — shipped; this
requirement is the seed-corpus half)
**Source:** MORNING-HANDOFF §J #17, §E2 ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD

### REQ-V12-ENGINE-05 — Collapse doubled "You try, but" in refuse observation template

Session 6 second unattended run produced tick-61 observation reading
*"You try, but You try, but no passage supplied via params['path'].."*.
The observer template is double-wrapping the refuse narrative —
likely a 2-line fix in `engine.py` or `observer.py` where both the
refuse branch and the observer template add the "You try, but" wrapper.

**Rationale:** presentation bug surfaces right after REQ-V12-ENGINE-01
lands (honest refuses now reach the observer path where old EXECUTED-lies
used to dodge it). Minor user-visible quality issue; cheap to fix.

**Acceptance criteria:**
- Grep confirms single source of truth for the "You try, but" wrapper.
- Regression test on a refuse tick asserts the wrapper appears exactly
  once in the observation text.
- willowbrook tick 61 (or equivalent fixture) round-trips cleanly.

**Status:** Active
**Source:** SESSION-6-REPORT "Remaining Work" follow-ups section
**Target phase:** TBD

### REQ-V12-CLI-03 — `token-world tick --stage <name> --raw` flags

During session 4 orchestration the author repeatedly reached for
`cat diagnostics/tick_N/classification/response.txt` because the
existing `tick` CLI surfaces the parsed summary but not the raw
intermediate pipeline I/O (§F row 2). Add `--stage <classification
| matcher | observer>` + `--raw` flags so operators can inspect the
raw prompt + response at any pipeline stage without leaving the CLI.

**Rationale:** diagnosis gap captured in §F. Extends the existing
`token-world tick` command rather than adding a new one. Unblocks
classifier / matcher / observer debugging during mechanic-authoring
sessions.

**Acceptance criteria:**
- `token-world tick <slug> <id> --stage classification [--raw]` prints
  the parsed or raw classifier payload for that tick.
- Same flags work for `--stage matcher` (DeterministicMatcher winner +
  candidates) and `--stage observer` (Sonnet prompt + response).
- `--format json` respects the stage filter.
- Tests: fixture universe with a completed tick exercises each stage.

**Status:** Active
**Source:** MORNING-HANDOFF §F row 2, §G allocation rules
**Target phase:** TBD

### REQ-V12-CLI-04 — `token-world mechanics --history` flag

§F row 3 captured the "what emerged since yesterday?" investigation the
author did by running `git log --oneline mechanics/` inside the universe
repo. Promote to the CLI so the registry browser can show the mechanic
timeline without shelling into git.

**Rationale:** every universe is a git repo by construction; exposing
that history under the `mechanics` command closes the investigation
loop. Complements REQ-V12-DASHBOARD-09 (registry panel "Last invoked"
column) — the CLI is canonical producer; dashboard consumes its JSON.

**Acceptance criteria:**
- `token-world mechanics <slug> --history` prints a chronological view:
  mechanic id, first-authored commit + timestamp, last-invoked tick.
- `--format json` mirrors the above as array of objects.
- Tests: fixture universe with N commits on `mechanics/` verifies ordering.

**Status:** Active
**Source:** MORNING-HANDOFF §F row 3
**Target phase:** TBD

### REQ-V12-DASHBOARD-07 — Run-status indicator

§F row 4 captured the "is `run_unattended.py` still running?" ask that
sent the author back to `ps aux | grep` repeatedly. The right fix: the
runner writes a PID file on start, removes it on exit, and the dashboard
stats strip renders a green/yellow/red dot reading that file.

**Rationale:** data-sourcing gap; also a session-4 process-hygiene
improvement — stale `.stop` and stale PID files both benefit from being
surfaced. Dashboard is the right surface per §G (continuous monitoring
for a human observer).

**Acceptance criteria:**
- `scripts/run_unattended.py` writes `<universe>/.run-pid` on start,
  removes on normal exit, handles SIGINT gracefully.
- Dashboard stats strip renders a green dot if PID file exists and
  process is alive; yellow if PID file exists but process dead; red
  (or hidden) if no PID file. Hover tooltip shows PID + start time.
- Tests: mock PID file states; assert the indicator correctly
  classifies each.

**Status:** Active
**Source:** MORNING-HANDOFF §F row 4
**Target phase:** TBD

### REQ-V12-DASHBOARD-08 — Agent inspector drawer

§F row 7 and session-5 feedback: Mira's `last_observed`, `last_moved`,
active LRA, attention state are all in the graph but terse when surfaced
via `token-world agents`. The dashboard needs a structured panel — a
drawer that opens when the user clicks an agent node and renders the
agent's full internal state as labelled sections, not raw JSON.

**Rationale:** promoted from v1.1 Phase 11 out-of-scope. Extends the
existing graph-canvas property drawer (already ships per REQ-V11-DASH-03)
with an agent-specific layout. Multi-agent scaffold (REQ-V12-DASHBOARD-05)
will need this surface when >1 agent exists.

**Acceptance criteria:**
- Clicking an agent node opens an inspector drawer (reuse existing
  drawer component from REQ-V12-DASHBOARD-01 non-rebuild guarantee).
- Sections: Identity (id, personality summary), Location (rendered from
  `located_in` pseudo-edge), Memory (recent tick summaries), Active LRA,
  Attention state, Recent actions (last 10 action_texts).
- Playwright test verifies drawer opens, sections render, scroll
  preserves across poll cycles (reuses REQ-V12-DASHBOARD-01 guarantee).

**Status:** Active
**Source:** MORNING-HANDOFF §F row 7; session-5 feedback
**Target phase:** TBD

### REQ-V12-DASHBOARD-09 — Mechanic timeline column in registry panel

§F row 3 overlap: the registry browser today shows mechanic id, call
count, and author (seed vs operator). Add a "Last invoked" (most recent
tick id) column and a "First authored" (git commit + timestamp) column so
the registry tells the *lifecycle* of each mechanic, not just its
cumulative stats.

**Rationale:** low-cost add on top of REQ-V12-CLI-04 (which provides the
history JSON). Dashboard consumes CLI JSON per §G allocation rules.

**Acceptance criteria:**
- Registry panel table includes "First authored" (commit hash + date)
  and "Last invoked" (tick id + age) columns.
- Columns sortable.
- Consumes `token-world mechanics <slug> --history --format json`
  rather than re-walking the git log.
- Tests: fixture universe with synthesized history JSON verifies
  column rendering + sort.

**Status:** Active (depends on REQ-V12-CLI-04)
**Source:** MORNING-HANDOFF §F row 3
**Target phase:** TBD

### REQ-V12-EMERGE-01 — Mechanic overlap detector (carried from v1.1)

Originally REQ-EMERGE-05 under v1.1 — did not land before v1.1 close.
Before authoring a new mechanic, the operator subagent should diff the
proposed verb + watches against the existing registry and prefer
editing an existing mechanic when overlap exceeds a threshold. Without
this, emergent universes will accumulate near-duplicates (two `pet`
variants, three `examine` variants) and the corpus grows chaotic.

**Rationale:** explicit carry-forward from v1.1; see milestones/v1.1
archive for original framing. Infrastructure for keeping the emergent
corpus coherent as the overnight runs scale.

**Acceptance criteria:**
- `src/token_world/operator/overlap.py` (or equivalent) computes an
  overlap score between a proposed verb+watches spec and the existing
  registry.
- Yield-handler subagent prompt (`.planning/agent-prompts/yield-handler.md`)
  includes the overlap report and a "prefer edit-existing when overlap
  exceeds X" instruction.
- Subagent's final JSON summary records the decision (new vs edit +
  overlap score).
- Tests: overlap score matches intuition on synthetic cases; integration
  test exercises the subagent decision path.

**Status:** Active (carried from v1.1)
**Source:** v1.1 REQ-EMERGE-05; MORNING-HANDOFF "Still pending in v1.1"
**Target phase:** TBD

### REQ-V12-EMERGE-02 — Operator decision-log enrichment (carried from v1.1)

Originally REQ-EMERGE-07 under v1.1 — did not land before v1.1 close.
`<universe>/operator-log.jsonl` today contains only yield/resolve
events; each authoring subagent's final JSON summary (reasoning,
overlap-check outcome, test-pass/fail history, cost) should also land
there so emergence runs are fully audit-trailed.

**Rationale:** explicit carry-forward from v1.1. Completes the
observability loop — without the subagent's reasoning in the log, you
cannot retrospectively diagnose why a given mechanic took the shape it
took.

**Acceptance criteria:**
- Subagent final JSON (reasoning + overlap + test history + cost) is
  appended to `<universe>/operator-log.jsonl` on every yield resolution.
- Existing yield/resolve events preserved (schema additive).
- CLI `token-world yield <slug> --history` optionally surfaces the log.
- Tests: end-to-end yield run verifies the log entry contains the
  expected fields.

**Status:** Active (carried from v1.1)
**Source:** v1.1 REQ-EMERGE-07; MORNING-HANDOFF "Still pending in v1.1"
**Target phase:** TBD

### REQ-V12-OPS-01 — `run_unattended.py` prints visible `.stop` warning at startup

Session 6 hit a stale `<universe>/.stop` kill-switch that silently
halted the first run attempt. The runner currently exits without a
loud log message when `.stop` is present at startup. Fix: print
`WARNING: .stop file present; delete before running` and exit with
non-zero. Prevents the confusing silent-halt failure mode when a
previous run left the file behind.

**Rationale:** small ops win; saved the author a 5-minute diagnosis
during session 6. Follow-up captured in SESSION-6-REPORT "Remaining
Work".

**Acceptance criteria:**
- `scripts/run_unattended.py` detects `<universe>/.stop` at startup.
- Prints a warning line (stderr) naming the file path.
- Exits with code != 0.
- Tests: fixture universe with `.stop` present; assert stderr + exit code.

**Status:** Active
**Source:** SESSION-6-REPORT "Remaining Work" section
**Target phase:** TBD

### REQ-V12-OPS-02 — Historical tick-summary migration script (OPTIONAL)

SESSION-6-REPORT flagged that willowbrook ticks 22, 34, and 38 may have
the same false-EXECUTED record as tick 34 did before REQ-V12-ENGINE-01
landed (`status=executed, refused=false, matched_mechanic_id=X,
mutations=0` for ticks where the mechanic's `check()` actually refused).
A migration script can re-run those historical ticks through the fixed
engine logic and rewrite their tick-summary JSON files to reflect the
honest `refused=true` state.

**Rationale:** optional because the bug is forward-only fixed; historical
records are archaeological. Still worth having the script available
because downstream KPIs + playtest scorer will double-count those false
EXECUTED records as "zero mutations + low groundedness" forever
otherwise.

**Acceptance criteria:**
- `scripts/migrate_tick_summaries.py <slug>` walks every tick summary
  whose primary-mechanic check would have failed under current engine
  logic; rewrites the summary JSON with honest `refused=true`.
- Dry-run mode (default) prints the planned changes without writing.
- `--apply` flag commits the rewrites.
- Idempotent — re-running against already-migrated summaries is a no-op.
- Tests: fixture with mixed honest + false-EXECUTED records; assert
  correct classification.

**Status:** Done — Phase 19 (`956ff43`)
**Source:** SESSION-6-REPORT "Remaining Work" section
**Target phase:** 19

### REQ-V12-TOOLING-02 — `seed_starter_universe.py --preserve-mechanics` flag

Anti-pattern 6 (captured in MORNING-HANDOFF §L): re-running the seed
script on an existing universe silently deletes any mechanics the
authored subagents landed since the last seed. The fix is covered by
REQ-V12-SEEDS-01's acceptance criteria but promoted to its own REQ
entry because it defends against a distinct failure mode (destructive
re-seed) independent of the seed-corpus refinement work itself. An
operator can ship the preserve flag without touching the agnostic-seed
promotion lane.

**Rationale:** anti-pattern 6 protection; independent of the
seed-corpus refinement. Agents who re-seed should get a clear opt-in
for preservation rather than discovering they wiped a day's authoring.

**Acceptance criteria:**
- `scripts/seed_starter_universe.py --preserve-mechanics` leaves any
  existing mechanic modules in `<universe>/mechanics/` untouched.
- Without the flag, behaviour unchanged (back-compat); but script
  prints a loud warning naming every mechanic that would be
  overwritten, with a "pass --preserve-mechanics to keep" hint.
- Tests: fixture universe with authored mechanics; assert preserve
  mode leaves them; assert default mode warns.

**Status:** Active
**Source:** MORNING-HANDOFF §L anti-pattern 6; covered also by
REQ-V12-SEEDS-01 acceptance criteria
**Target phase:** TBD

---

## v1.2.0 Graph Conventions

From §I's deferred-sweep: four items have concrete Willowbrook traction
and should be promoted into v1.2 rather than held for v2. Cross-linked
to REQ-V12-ENGINE-03 (the `locked`/`blocked`/`inventory_full` audit) —
these conventions are the positive half of the same smell.

### REQ-V12-GRAPH-01 — Door state canonical representation

Willowbrook's `cottage_door` carries `locked` + `connects: [...]` as
ad-hoc properties. GAP-GRAPH18 asked for a canonical representation.
Aligns with REQ-V12-ENGINE-03: a door is an entity; its state is
emergent properties; the engine never privileges them.

**Rationale:** the engine audit (REQ-V12-ENGINE-03) naturally surfaces
the convention. Document as part of the same PR so mechanics know what
shape to target.

**Acceptance criteria:**
- `docs/design/graph-conventions.md` (new) documents the door
  representation: `subtype=door | passage`, `locked: bool`,
  `connects: [node_id, node_id]`.
- Willowbrook's `cottage_door` conforms (already does).
- Cross-linked from REQ-V12-ENGINE-03.

**Status:** Active
**Source:** MORNING-HANDOFF §I (GAP-GRAPH18), cross-ref §E3
**Target phase:** TBD (co-lands with REQ-V12-ENGINE-03)

### REQ-V12-GRAPH-02 — Container subtype + capacity convention

`old_chest` is `subtype=container` with implicit semantics. GAP-GRAPH14
asked for formalization: `capacity`, `contents`, `open`, `locked`
as canonical properties.

**Rationale:** inventory-like patterns will recur. Codify now to stop
the corpus drifting into N slightly-different container semantics.

**Acceptance criteria:**
- `docs/design/graph-conventions.md` §Containers captures the canonical
  property set.
- Willowbrook's `old_chest` conforms.
- Seed mechanic for `open_container` (generic, universe-agnostic) added
  with tests.

**Status:** Active
**Source:** MORNING-HANDOFF §I (GAP-GRAPH14)
**Target phase:** TBD

### REQ-V12-GRAPH-03 — Portal / passage vocabulary

Willowbrook uses `subtype='passage'` ad-hoc (cottage_door). Three
mechanics (walk, passage_move, movement) touch it with slightly different
conventions. GAP-GRAPH06 asked for canonicalization.

**Rationale:** small doc decision. Canonicalize before more
passage-verbs arrive so the three existing mechanics converge instead of
diverge.

**Acceptance criteria:**
- `docs/design/graph-conventions.md` §Portals documents the vocabulary
  (`passage` vs `door`, `connects`, `traversable`).
- Existing walk / passage_move / movement mechanics audited for
  conformance; drift fixed.

**Status:** Active
**Source:** MORNING-HANDOFF §I (GAP-GRAPH06)
**Target phase:** TBD

### REQ-V12-GRAPH-04 — Fungible amount representation convention

Mira's `drawn_water` bucket is an ad-hoc amount-as-dict. Not urgent —
commerce hasn't emerged — but GAP-GRAPH10 asked for a documented
convention before ambiguity hardens.

**Rationale:** low urgency; include while adjacent conventions are being
written. Defer actual migration until commerce drives the need.

**Acceptance criteria:**
- `docs/design/graph-conventions.md` §Amounts captures the tradeoff
  (amount-as-property vs amount-as-entities) with a recommended default.
- Willowbrook's `drawn_water` annotated with the chosen convention or
  flagged as a known exception.

**Status:** Active
**Source:** MORNING-HANDOFF §I (GAP-GRAPH10)
**Target phase:** TBD

---

## v2.0+ Deferred

These 12 items from §I's sweep are correctly deferred per D-06. The next
session should NOT pull them into v1.2 without a strong v1 use case. One
line per item explains why. (Original IDs from
[.planning/backlog/phase-03-gap-deferrals.md](backlog/phase-03-gap-deferrals.md);
surfaced here as bullets rather than a REQ-table so the traceability
script doesn't flag them as orphan requirements of v1.2 — they remain
owned by the v2+ backlog.)

- **graph-terrain-typing** (was GAP-GRAPH07): Cross-category terrain
  typing (water/wall/floor/bridge/stair) — wait for Phase 4+ mechanic
  authoring to force the ontology decision.
- **graph-containment-chain** (was GAP-GRAPH08): `inside` vs
  `located_in` containment split + `containment_chain(node)` helper —
  narrow helper; ship when multi-agent containment patterns emerge.
- **graph-position-accessor** (was GAP-GRAPH09): `position_of(node)`
  accessor — ergonomic helper; defer until multiple mechanics need the
  centroid abstraction.
- **graph-reputation-edges** (was GAP-GRAPH11): Reputation / relationship
  edges — requires v2 multi-agent; single-agent v1 doesn't exercise
  trust graphs.
- **graph-condition-vocab** (was GAP-GRAPH12): Condition tracking
  vocabulary (durability / integrity / charges / uses) — wait for
  multiple concrete examples.
- **graph-crafted-from-edge** (was GAP-GRAPH13): `crafted_from`
  provenance edge — scheduled for Phase 8+ history tooling; not in v1
  scope.
- **graph-outdoor-derivation** (was GAP-GRAPH15): `outdoor=True` derived
  through containment — overlaps with the containment-chain item; ship
  together when needed.
- **graph-transform-convention** (was GAP-GRAPH16): In-place property
  transformation vs node-swap convention — documentation gap; resolve
  during Phase 4 mechanic-authoring wave, not standalone.
- **graph-transactional-primitive** (was GAP-GRAPH17): Transactional /
  compare-and-swap graph primitive — required for v2 multi-agent;
  single-agent v1 doesn't interleave.
- **mech-partial-consumption** (was GAP-MECH28): Partial / portioned
  consumption (half-eaten apple) — narrow enrichment; ship when
  authoring needs it.
- **mech-making-change** (was GAP-MECH29): Making-change in
  `fungible_pay` — defer until commerce is exercised.
- **eng-multi-party-commit** (was GAP-ENG19): Multi-party commit /
  consent / listener-reaction primitive — observer-belief propagation
  is v2 multi-agent territory.

---

## Non-Requirements (explicitly out of scope for v1.2)

- **Multi-agent simulation engine** — still v2 (D-17). Dashboard scaffold
  in REQ-V12-DASHBOARD-05 lands first; engine cutover follows in v2.
- **Hosted public dashboard URL** — still local-only; cloud hosting is v2+.
- **Mechanic versioning UI** — registry browser already ships with call
  counts; version-history UI deferred.
- **RestrictedPython sandboxing** — still v2+.
- **Gallery / sharing export** — v2 candidate.
- **Agent SDK overnight runs** — explicitly forbidden per §L cost rails;
  subagents under the subscription are the blessed shape.

---

## Traceability

| Requirement | Phase | Status | Commit / Plan |
|---|---|---|---|
| REQ-V12-ENGINE-01 | TBD | done | `afc5c73` |
| REQ-V12-ENGINE-02 | TBD | done | `e110e2c` |
| REQ-V12-DASHBOARD-01 | TBD | done | `d31090d` |
| REQ-V12-DASHBOARD-02 | TBD | done | `d31090d` |
| REQ-V12-DASHBOARD-03 | TBD | done | `d31090d` |
| REQ-V12-DASHBOARD-04 | TBD | done | `6101da0` |
| REQ-V12-CLI-01 | TBD | done | `fa68200` |
| REQ-V12-CLI-02 | TBD | done | `7435536` |
| REQ-V12-PLAYTEST-01 | TBD | done | `0fcd614` |
| REQ-V12-ECONOMY-01 | TBD | done | (Willowbrook `_economy.py` landed; universe commit `ce671cd`) |
| REQ-V12-QUALITY-01 | TBD | done | `890b464` |
| REQ-V12-DOCS-01 | TBD | done | `3eec1c5` |
| REQ-V12-TOOLING-01 | TBD | done | `958a28b` |
| REQ-V12-ENGINE-03 | Phase 18 | active | — |
| REQ-V12-ENGINE-04 | Phase 16 | active | — |
| REQ-V12-ENGINE-05 | Phase 14 | active | — |
| REQ-V12-DASHBOARD-05 | Phase 15 | active | — |
| REQ-V12-DASHBOARD-06 | Phase 18 | active | — |
| REQ-V12-DASHBOARD-07 | Phase 17 | active | — |
| REQ-V12-DASHBOARD-08 | Phase 17 | active | — |
| REQ-V12-DASHBOARD-09 | Phase 17 | active | — |
| REQ-V12-CLI-03 | Phase 17 | active | — |
| REQ-V12-CLI-04 | Phase 17 | active | — |
| REQ-V12-QUALITY-02 | Phase 13 | done | `44361da` |
| REQ-V12-SEEDS-01 | Phase 14 | active | — |
| REQ-V12-EMERGE-01 | Phase 17 | active | — |
| REQ-V12-EMERGE-02 | Phase 17 | active | — |
| REQ-V12-OPS-01 | Phase 17 | active | — |
| REQ-V12-OPS-02 | Phase 19 | done | `956ff43` |
| REQ-V12-TOOLING-02 | Phase 14 | active | — |
| REQ-V12-GRAPH-01 | Phase 18 | active | — |
| REQ-V12-GRAPH-02 | Phase 18 | active | — |
| REQ-V12-GRAPH-03 | Phase 18 | active | — |
| REQ-V12-GRAPH-04 | Phase 18 | active | — |

---

*Last updated: 2026-04-14 (v1.2 milestone formally opened; inclusive scope
pass per user's session-6 mandate). Source-of-truth handoff:
[../MORNING-HANDOFF.md](../MORNING-HANDOFF.md) §§F/I/J + SESSION-6-REPORT.
Far-fetched items parked at
[backlog/v2.0-REQUIREMENTS.md](backlog/v2.0-REQUIREMENTS.md) as REQ-V20-*.*
