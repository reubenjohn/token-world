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

---

## v1.2.0 Active Backlog

Not yet landed. Ordered roughly by §J priority. Each requirement lists a
target phase of `TBD` until a ROADMAP row lands.

### REQ-V12-CLI-02 — `token-world yield` CLI + dashboard "Active Yield" banner

While orchestrating, the author reached for `cat /.../operator_inbox/N.yield.json`
because there was no tool to inspect a pending yield mid-run (§F row 1).
Belongs on the CLI per §G (stateless query) with a complementary sticky
banner in the dashboard.

**Rationale:** operators + subagents need to see the classified action
that caused a yield without rooting through inbox files. Driven by §F's
data-sourcing gap + the allocation-principle decision.

**Acceptance criteria:**
- `token-world yield <slug> [--tick N | --pending]` command.
- `--format json` uniform.
- Dashboard "Active Yield" banner renders while a yield is unresolved,
  sticky across poll cycles (hides when inbox empties).
- Test: smoke test against a fixture universe with a staged yield JSON.

**Status:** Active
**Source:** MORNING-HANDOFF §J #5, §F row 1 ([handoff](../MORNING-HANDOFF.md))
**Target phase:** TBD

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

### REQ-V12-ENGINE-02 — Observation-grounding drift investigation (tick 35)

The chest was unlocked by `force` at tick 15 but tick 35's observation
still said "locked" (§E4). Likely cause: observer's prompt grounding
pattern-matched the stale `description` string rather than
`projected_state.locked=False`. Could instead be
`projected_state` built from pre-apply snapshot. Requires
investigation then a targeted fix (either prompt hardening or pipeline
ordering).

**Rationale:** observation drift is a grounding-invariant violation;
groundedness is a core simulation property (D-15). Every occurrence
poisons downstream KPIs.

**Acceptance criteria:**
- Root cause identified via `token-world tick 35 --format json` and
  `token-world trace old_chest locked`.
- Fix lands with a regression test that reproduces the drift.
- Observer prompt hardened: must never contradict `projected_state`;
  `description` field is cosmetic, not canonical.

**Status:** Active
**Source:** MORNING-HANDOFF §J #13, §E4 ([handoff](../MORNING-HANDOFF.md))
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
| REQ-V12-DASHBOARD-01 | TBD | done | `d31090d` |
| REQ-V12-CLI-01 | TBD | done | `fa68200` |
| REQ-V12-DASHBOARD-02 | TBD | done | `d31090d` |
| REQ-V12-DASHBOARD-03 | TBD | done | `d31090d` |
| REQ-V12-DASHBOARD-04 | TBD | done | `6101da0` |
| REQ-V12-PLAYTEST-01 | TBD | done | `0fcd614` |
| REQ-V12-ECONOMY-01 | TBD | done | (Willowbrook `_economy.py` landed) |
| REQ-V12-QUALITY-01 | TBD | done | `890b464` |
| REQ-V12-DOCS-01 | TBD | done | `3eec1c5` |
| REQ-V12-TOOLING-01 | TBD | done | `958a28b` |
| REQ-V12-CLI-02 | TBD | active | — |
| REQ-V12-DASHBOARD-05 | TBD | active | — |
| REQ-V12-QUALITY-02 | TBD | active | — |
| REQ-V12-ENGINE-02 | TBD | active | — |
| REQ-V12-ENGINE-03 | TBD | active | — |
| REQ-V12-SEEDS-01 | TBD | active | — |
| REQ-V12-ENGINE-04 | TBD | active | — |
| REQ-V12-DASHBOARD-06 | TBD | active | — |
| REQ-V12-GRAPH-01 | TBD | active | — |
| REQ-V12-GRAPH-02 | TBD | active | — |
| REQ-V12-GRAPH-03 | TBD | active | — |
| REQ-V12-GRAPH-04 | TBD | active | — |

---

*Last updated: 2026-04-14 (v1.2 assembly session, post-session-5
feedback). Source-of-truth handoff:
[../MORNING-HANDOFF.md](../MORNING-HANDOFF.md) §I + §J.*
