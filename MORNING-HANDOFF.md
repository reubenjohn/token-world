# Morning Handoff — Token World

**Current as of**: 2026-04-14 ~05:55 UTC (end of session 3)
**Last coordinator**: Claude Opus 4.6 (1M context), balanced profile
**Master HEAD**: `c19fb8b` — pushed to `origin/master`, CI ✅ GREEN
**Git tag**: `v1.0` — milestone v1.0 shipped and archived

---

## The Vision (Read First — Everything Else Flows From This)

**Token World is an engine for emergent universes.** A resident agent inhabits a world. They do something the world has no rule for — *"I want to teach the baker's son to read,"* *"I throw the coin into the fountain and make a wish,"* *"I sharpen my knife on the whetstone for an hour."* The engine doesn't flinch. It **yields to an operator** (an Opus-level LLM with Agent SDK tools), and the operator **authors a new Python mechanic on the fly**, validates it against the existing graph, and resumes the tick. The world grows.

Give the engine a handful of entities and a personality. Let agents play. Watch what happens.

**Culture emerges.** Agriculture emerges (one agent starts planting; another operator authors `grow_crop`). Economy emerges (someone barters; mechanics for `exchange`, `value`, `debt` accrete). Language drift emerges. Religion emerges. Conflict. Myths. Architecture. **You do not script any of it.** You write the engine, seed the garden, and the universes that bloom are not yours anymore.

This is *Dwarf Fortress for LLM agents* — except the rules of physics are procedurally authored by an LLM in response to what the inhabitants actually try to do. No schema. No game-design document. No content team. Just a knowledge graph, a mechanic authoring loop, and time.

**What's thrilling about where we are now:**
- The substrate is real. 1743 tests. `claude -p` backend that costs $0/run. Composable mechanics framework. Grounded observation. No hallucinated world state.
- v1.0 shipped the **plumbing**. It is possible — right now — for a human to sit and drive an agent through a universe and watch the operator author new physics. The feedback loop works end to end.
- **What's missing is the stage for the show.** Specifically:
  1. An **operator-eye view** — a way to *watch a universe evolve* that isn't scrolling raw JSON tick files.
  2. **Causal traceability** — given a weird state, walk backward: which mechanic? which agent action? which classifier verdict?
  3. **Aggregate stats** — tick throughput, yield rate, novel-mechanic rate, agent boredom proxy, conservation violations, emergent concept discovery.
  4. A **web dashboard** that makes all three shareable. Because *people will not believe this is happening without seeing it move in real time.*
  5. An **unattended run loop** — set an agent loose, let the operator auto-author mechanics, come back in an hour and find a new civilization.

**This project could inspire a lot of people.** Large language models as simulated inhabitants of procedurally-authored worlds is genuinely new territory. The plumbing works. Now we need to show it off, and we need to make sure a universe can run without anyone hand-holding it for a nontrivial amount of time.

---

## What The Next Session Is For

**Mandate (in ranked order):**

1. **Operator-eye tooling** — the CLI queries + causal tracer + stats aggregator that let an operator (human OR agent) inspect what's happening in a universe without archaeology.
2. **Web dashboard** — a shareable visualization that makes the emergence legible. Live tail, graph canvas, tick scrubber, mechanic registry browser, causal chain viewer, stats panels. (Sec. §Dashboard below is opinionated about what it shows; the tech stack is open within constraints.)
3. **Emergence infrastructure** — the missing glue that lets a universe run **unattended**: the yield-to-operator loop is wired, but it's currently human-driven via `resume_tick` MCP. Automate the operator loop so an LLM can propose + validate + integrate new mechanics without a human clicking "resume." This is where universes actually start emerging.
4. **Seed a demo universe** designed to invite emergence — a starter village with a handful of entities, 2-3 resident agents with contrasting personalities, and minimal mechanics. Run it overnight (literally, in the next session). See what happens.

The rest of this document is the operational detail the next session needs to execute on this mandate. **Read §The Dashboard We Want, §Operator CLI Surface, §Emergence Loop before coding anything new.**

---

## Autonomy Rules (Unchanged — Mode: "Dark Factory")

- **Take action.** Don't ask "should I proceed?" on routine decisions. Just proceed.
- **Document decisions.** If a choice isn't in `PROJECT.md` / `CONTEXT.md` / this handoff, pick pragmatic and record in the relevant artifact.
- **Self-correct.** Fix your own mistakes. Only bubble up what you've tried and failed to resolve.
- **Only stop for**: architectural forks that lock in a hard direction, corrupted state you cannot safely recover from, rate-limit ceilings `ScheduleWakeup` can't clear.
- **Push to master as you go.** The user approved this pattern; keep it. Green CI before next commit.
- **Profile**: `balanced` (Opus orchestrator + planner; Sonnet executors + verifier + reviewer). Do not switch without reason.
- **Budget**: leave expensive (>$0.50) live-API runs as `human_needed` if the `claude-cli` backend path fails. Don't silently escalate to direct SDK.
- **Aggressive subagent delegation.** Orchestrator context is precious — delegate research, planning, execution, verification. Never do work a subagent could do.
- **No worktrees** — the base-mismatch bug causes spurious deletions. Sequential executors on main tree. Proven pattern; session 3 landed 17 commits with zero incidents.

---

## The Dashboard We Want

A web-first, read-only observer for a running or completed universe. **The moment of truth is when a friend clicks a link and sees an LLM agent making decisions in a world where another LLM is authoring the physics on the fly. That moment has to be beautiful.**

### Required panels (ranked by impact)

1. **Live tick stream** — newest tick first, card-like: agent intent → classifier verdict → mechanic chosen (or yielded) → observation. Stream over Server-Sent Events or WebSocket from the engine.
2. **Graph canvas** — interactive node-link diagram of the knowledge graph. Agents + entities + edges. Click a node → property drawer. Filter by type / subtype / "recently mutated." Snap to the active agent by default. (Cytoscape.js, Sigma.js, or d3-force — all MIT-friendly, no banned deps.)
3. **Tick timeline + scrubber** — horizontal lane showing tick numbers, coloured by outcome (ok / yielded / refused / long-running-continuation). Click a tick → graph canvas rewinds (via snapshot/restore) + tick detail pane lights up.
4. **Mechanic registry** — table of all mechanics in the universe, grouped by author (seed vs operator-authored), call count, last invoked tick, success rate. Click a mechanic → source viewer + diff-from-previous-version + call trace.
5. **Causal chain viewer** — given a property change (e.g., "why is alice.hp now 3?"), walk backward: mutation → mechanic → classified action → agent turn → observation → prior tick's observation. This is the "trace tree" you already have under the hood; the dashboard just renders it.
6. **Stats strip** — a thin header band always visible. Live numbers: tick #, ticks/min, yield rate %, novel-mechanic rate (per 10 ticks), emergent concept count (new `subtype` values this run), conservation violations, cost (USD or "via CLI").
7. **Agent inspector** — for any agent: personality bundle, rolling 10-turn memory window, active LRA (if any), attention state, tick-by-tick action/observation pairs, belief overlay diff vs ground truth.

### Optional panels (time permitting)

- **Mechanic dependency graph** — static mermaid-ish render showing which mechanics call `ctx.begin_long_action`, which produce mutations that other mechanics watch for, etc.
- **"Universe diff" view** — compare two snapshots: what nodes/edges/properties changed between tick X and tick Y.
- **Cost pie** — breakdown of LLM spend by stage (classifier / observer / agent / operator / judge).
- **Regression-history viewer** — decorate ticks where a prompt-hash regression fired.

### Tech constraints (inherited from CLAUDE.md, with one open question)

- **No FastAPI/Flask** per PROJECT.md constraints. Viable alternatives within the project's philosophy:
  - **Starlette** (minimal ASGI, powers FastAPI but isn't it) — probably fine; flag for user review.
  - **aiohttp** — also fine.
  - **Static HTML + `http.server` stdlib + SSE** — works and requires zero deps; may be enough for v1.
  - **Textual TUI** — beautiful terminal UI, shareable as `asciinema` recordings; not shareable as a link.
  - **Streamlit / Gradio** — fast to build, spans the line between "dashboard" and "toy"; judgment call.
- Whatever stack you pick, keep the dashboard **read-only** in v1.1. Mutation goes through the existing engine + MCP tools, not through the dashboard.
- **The dashboard is a new consumer, not a new producer.** It reads the same `tick_summaries/*.json`, `universe.db`, `.planning/prompt-regression-history.jsonl` that already exist. Don't change the producer schema.
- **First priority**: working end-to-end with ugly styling. Pretty later. The vision demo does not need polish — it needs to *move*.

**Surface this as a D-01 for the v1.1 milestone**: "dashboard stack decision — Starlette vs. Textual vs. stdlib." Pick, commit, build.

---

## Operator CLI Surface (What Agents Need Today)

The dashboard serves humans. Agents — in this project, subagents driving work — need the same information through the CLI, where it composes with other tools. **Build these first; the dashboard can consume the same data.**

### Already shipped

- `token-world list` / `create` / `delete`
- `token-world playtest <slug>` (with `--turns`, `--judge`, `--no-operator`, `--scenario`, `--seed`, `--output`)
- `token-world cost <slug>` (session 3 addition)
- `token-world agent-turn <slug> <text>`
- `scripts/inspect_playtest_report.py` / `scripts/update_prompt_hashes.py`

### Needed for operator-eye tooling

| Command | What it shows | Priority |
|---|---|---|
| `token-world inspect <slug>` | Universe at a glance: node count by type, mechanic count, last N ticks summary, active LRAs, recent yield events | P0 |
| `token-world tick <slug> <tick_id>` | Full tick detail: action → classification → mechanic → mutations → observation; tree-formatted | P0 |
| `token-world trace <slug> <node_id> <property>` | Causal chain walker — "why does alice.hp equal 3?" → mutation → mechanic → action → tick | P0 |
| `token-world graph <slug> [--seed-query Q] [--format mermaid\|json]` | Emit graph (or ego-subgraph) — `viz-graph` already exists; add universe-slug ergonomics | P1 |
| `token-world mechanics <slug> [--author seed\|operator]` | Registry browser with call counts, last-invoked tick, version | P1 |
| `token-world agents <slug> [--id X]` | Agent inspector: personality bundle, rolling memory, active LRA, stats | P1 |
| `token-world stats <slug> [--since N] [--stream]` | Aggregate metrics: tick/min, yield rate, novel-mechanic rate, emergent subtype count, conservation violations | P1 |
| `token-world diff <slug> <tick_a> <tick_b>` | Snapshot diff — nodes/edges/properties that changed between two ticks | P2 |
| `token-world watch <slug>` | Live tail of tick events to stdout (poll `tick_summaries/ticks/` for new files) | P2 |

**All commands should support `--format json`** so the dashboard (and other tools) can consume them.

**Pattern established (session 3)**: the `token-world cost` command lives in `src/token_world/playtest/cost.py` with a thin Click wrapper in `cli.py`. Mirror that pattern: aggregator module under `src/token_world/`, Click wiring in `cli.py`, JSON + table output modes, tests in `tests/test_*`.

---

## Emergence Loop (The Missing Glue)

Right now, when `run_tick` yields, the operator layer handles it via Claude Code + MCP `resume_tick` — a human clicks, approves, resumes. That's fine for development. **It's not emergence.**

For a universe to evolve unattended, we need:

### 1. Automated Operator

An **Opus-level Agent SDK-driven loop** that:
- Watches the tick summary stream for `yielded` events
- For each yield, reads the full context (classified action, candidate mechanic IDs, graph projection, prior ticks)
- Decides: (a) propose a new mechanic, (b) refine an existing mechanic, (c) refuse the action as genuinely incoherent
- Authors the mechanic file under `<universe>/mechanics/` using the existing validation pipeline (`uv run token-world validate` — Phase 4)
- Commits the mechanic to the universe's git repo
- Calls `resume_tick` via MCP
- Logs the decision to `<universe>/operator-log.jsonl`

This already has most of its pieces (Phase 4 validation pipeline, Phase 4.1 operator harness, Phase 5 yield mechanism). **What's missing is wiring them into a self-driving loop.** Current operator harness is invoked per-tick via MCP; it needs a "run autonomously until blocked" mode.

### 2. Mechanic Dedup + Evolution

When the operator proposes a new mechanic, the system should:
- Check for **semantic overlap** with existing mechanics (share a verb? overlapping watches? already implementable with existing DSL?)
- Prefer **editing an existing mechanic** over creating a new one when the overlap exceeds a threshold
- Track **version history** (already present — git-based)
- Produce a **mechanic change feed** in the dashboard so humans can audit what the operator decided

### 3. Safety Rails for Unattended Runs

- **Tick budget** — `token-world run <slug> --ticks 100` auto-stops after N ticks.
- **Yield budget** — stop if operator has been consulted N times (indicates thrashing).
- **Cost ceiling** — refuse to start a run if estimated cost exceeds $X.
- **Mechanic-author rate limiter** — cap new mechanics per hour to prevent runaway authoring.
- **Snapshot every N ticks** — rollback-able if the universe drifts into incoherence.
- **Kill switch** — a file `<universe>/.stop` halts the loop at the next checkpoint.

### 4. Starter Universe Designed For Emergence

Current demo universes (`demo-tavern`, `uatworld`) are too empty for interesting emergence. A seed universe optimized for play:
- 3-5 entities with emergent hooks (a well with `water_level`, a chest with `locked=True`, a garden with `fertility`)
- 2 agents with contrasting personalities (e.g., *curious child* + *cautious elder*)
- 5-8 seed mechanics covering: movement, observation, basic interaction, sleep, speak
- `starter_scenario.yaml` that triggers 1-2 adversarial injections to kick-start the unexpected
- A `seed_universe.py` script that scaffolds it reproducibly

Then: `token-world run starter --ticks 200 --operator auto` and come back tomorrow to see what emerged.

**This is the demo we want to share.**

---

## Starter Moves for Session 4 (Ranked by ROI)

### Track A: Operator CLI Surface (do this first — dashboard consumes its output)

1. **`token-world inspect <slug>`** — universe at a glance. ~1h with subagent. Blocker for everything else.
2. **`token-world trace <slug> <node> <prop>`** — causal chain walker. Leverages existing `collect_mutations` from `mechanic.trace`. ~1h.
3. **`token-world tick <slug> <id>`** — pretty-print a single tick's full detail tree. ~30min.
4. **`token-world stats <slug>`** — aggregate metrics. Composes with `cost`; some metrics need new emergent-concept tracking. ~1h.
5. **`token-world mechanics <slug>`** — registry browser. Registry code exists in Phase 2; just needs CLI wrapper. ~30min.

**At the end of Track A**, an agent can fully understand any universe via CLI. This unblocks dashboard consumption and emergence loop decisions.

### Track B: Dashboard (the stage for the show)

1. **D-01: tech stack decision** — Starlette vs. stdlib vs. Textual vs. Streamlit. Document rationale; build prototype.
2. **Minimum viable dashboard** — read-only, loads universe state from disk, shows tick stream + graph canvas + stats strip. Ugly styling OK.
3. **SSE/polling live tail** — stream new tick files into the UI without refresh.
4. **Graph canvas** — Cytoscape.js or Sigma.js; hook up to the existing graph JSON export.
5. **Causal chain viewer panel** — consumes `token-world trace` JSON output.
6. **Styling + polish** — after functionality lands.

### Track C: Emergence Loop (the interesting part)

1. **Autonomous operator mode** — extend `OperatorHarness` with `run_until_blocked()`. Wire in Agent SDK with full tool list (`read_file`, `write_file`, `validate_mechanic`, `resume_tick`).
2. **Mechanic dedup pre-check** — before authoring, diff against existing mechanics by verb + watches overlap.
3. **Safety rails** — tick budget, yield budget, cost ceiling, kill switch.
4. **Seed universe script** — `scripts/seed_starter_universe.py` or a CLI subcommand.
5. **First unattended run** — `token-world run starter --ticks 200 --operator auto` → observe, document, share.

### Track D: Tech Debt & Polish (between sprints)

- Phase 04.1 SC-2 interactive smoke test — now zero-cost via `ClaudeCLIBackend`; 1 hour to close.
- `agent_id` stub in `BatchSummary` — tied to multi-agent prep.
- Per-module mermaid diagrams for ResidentAgent / PlaytestRunner / TickCompressor (if the dashboard doesn't obsolete them).
- Refresh research docs on Opus-vs-Sonnet model routing.

### Ranking rationale

Track A → Track C → Track B. **CLI first** because it's what agents consume and what humans prototype with. **Emergence loop next** because it turns the engine from "developer toy" to "self-running experiment." **Dashboard last** because it's the presentation layer and needs the data to be right first.

**Cheat move**: if overnight, do Tracks A and C in parallel via subagents, then kick off a 200-tick unattended run, and use the remaining time to build the dashboard *while* the run progresses — so the morning demo includes real emergence data.

---

## Complete Tooling Inventory (What It Takes To Get To Emergence)

Full brainstorm of what needs to exist for universes to *reliably emerge from play* and be *legible to observers*. Grouped by audience. Mark P0 / P1 / P2 — P0 is emergence-blocking, P1 is emergence-amplifying, P2 is polish.

### A. Operator Tools (what the authoring LLM needs)

| Tool | Purpose | Status | Priority |
|---|---|---|---|
| `token-world inspect <slug>` | Universe overview — node/mechanic/agent counts, last N ticks, active LRAs, recent yields | missing | **P0** |
| `token-world tick <slug> <id>` | Full tick detail — action → classification → match → mutations → observation tree | missing | **P0** |
| `token-world trace <slug> <node.prop>` | Causal chain — "why does alice.hp=3?" → mutation → mechanic → action → tick | missing | **P0** |
| `token-world mechanics <slug>` | Registry browser — verb, tags, call count, last invoked, source path | partial (Phase 2 registry exists) | **P0** |
| `validate_mechanic <path>` | Run existing Phase 4 pipeline as CLI step so operator can verify before committing | exists in Phase 4, needs CLI expose | **P0** |
| `token-world mechanic-diff <mechanic-id>` | Show version history + diff between versions | missing | P1 |
| `token-world agent <slug> <id>` | Personality + rolling memory + active LRA + attention state | missing | P1 |
| `token-world graph <slug> [--seed-query Q]` | Mermaid / JSON export — `viz-graph` already exists, needs universe-slug ergonomics | partial | P1 |
| `token-world stats <slug> [--stream]` | Tick/min, yield %, novel-mechanic rate, cost, emergent-subtype count | missing | **P0** |
| `token-world diff <slug> <tick_a> <tick_b>` | Snapshot delta — nodes/edges/properties changed between two ticks | missing (graph snapshots exist) | P1 |
| `token-world search <slug> --verb X --since N` | Find ticks matching a predicate — debug a recurring failure | missing | P2 |
| `token-world mechanic-lint <path>` | Style + convention check for a proposed mechanic before validation | missing | P1 |
| `token-world mechanic-dedup <slug> <proposed-verb>` | Check if existing mechanic already covers the verb/watches intent | missing | **P0** |
| Mechanic template library | Copy-paste-adapt snippets for common patterns (LRA, TickMatcher, AOE, etc.) | implicit in seeds/; promote to docs/templates/ | P1 |
| MCP tools on engine | Add `inspect_universe`, `trace_property`, `stats` alongside `resume_tick`/`rollback`/`list_mechanics` | partial | P1 |

### B. Observer Tools (humans and non-authoring agents)

| Tool | Purpose | Status | Priority |
|---|---|---|---|
| Web dashboard — tick stream | Live card feed: agent intent → verdict → mechanic → observation | missing | **P0** |
| Web dashboard — graph canvas | Interactive node-link view of current graph state | missing | **P0** |
| Web dashboard — causal chain panel | Click a property → walk back through mutations → mechanic → action | missing | **P0** |
| Web dashboard — stats strip | Live numbers (always visible): tick #, tick/min, yield %, novel mechanics, cost | missing | **P0** |
| Web dashboard — tick scrubber | Horizontal timeline; click tick → rewind graph canvas via snapshot | missing | P1 |
| Web dashboard — mechanic registry table | List mechanics + call counts + author (seed vs operator) | missing | P1 |
| Web dashboard — agent inspector drawer | Personality / memory / active LRA / attention state for any agent | missing | P1 |
| Web dashboard — styling + polish | Dark mode, typography, motion design — matters for sharing | missing | P2 |
| `token-world watch <slug>` | Terminal live-tail — stdout stream as new ticks land | missing | **P0** |
| `token-world replay <slug> --speed Nx` | Play back historical ticks with timing | missing | P2 |
| `token-world export <slug> --format html` | Standalone shareable HTML page of a completed universe | missing | P2 |

### C. Emergence Loop (the missing glue)

| Tool | Purpose | Status | Priority |
|---|---|---|---|
| Autonomous operator mode | `OperatorHarness.run_until_blocked()` — Agent SDK drives yield→author→validate→resume without human clicks | partial (single-tick harness exists) | **P0** |
| Mechanic overlap detector | Before authoring, diff proposed verb+watches against existing mechanics; prefer edit-existing over create-new | missing | **P0** |
| Mechanic quality gate | Linter + validator + TDD test-run pass required before commit | Phase 4 pipeline exists; wire as gate | **P0** |
| Tick budget | `--ticks N` auto-stops after N ticks | missing | **P0** |
| Yield budget | Stop if operator consulted >N times in last M ticks (thrashing protection) | missing | **P0** |
| Cost ceiling | Refuse to start if estimated cost > $X; abort mid-run if exceeded | missing | **P0** |
| Kill switch | `<universe>/.stop` file halts loop at next checkpoint | missing | **P0** |
| Snapshot cadence | Auto-snapshot every N ticks for rollback-ability | partial (manual snapshots exist) | **P0** |
| Resume from crash | Next invocation picks up from last snapshot | missing | P1 |
| Operator decision log | `<universe>/operator-log.jsonl` — what the operator chose and why, per yield | missing | **P0** |
| Operator health check | Heartbeat — "is the simulation actually progressing?" vs stuck in a classify-retry loop | missing | P1 |

### D. Seed Universe Infrastructure (inviting interesting emergence)

| Tool | Purpose | Status | Priority |
|---|---|---|---|
| `scripts/seed_starter_universe.py` | Reproducible starter: 3-5 entities with emergent hooks, 2 agents with contrasting personalities, 5-8 seed mechanics | missing | **P0** |
| Multi-agent support (2-3 agents in same universe) | Two agents with different personalities in one tick cycle | partial — single-agent is v1 baseline; MULTI-01 is v2 | **P0** for emergence; re-scope from v2 |
| Personality diversity sampler | Generate contrasting personalities from archetype set (curious child, cautious elder, mercurial trickster, methodical scholar, etc.) | missing | P1 |
| Starter-scenario catalog | A handful of seeds with known-interesting outcomes for replay + regression | missing | P1 |

### E. Emergence Detection (proving it's working)

| Tool | Purpose | Status | Priority |
|---|---|---|---|
| Novel-subtype tracker | Count distinct `subtype` values per run; flag first-occurrences; emit events to dashboard | missing | **P0** |
| Novel-mechanic tracker | Count operator-authored mechanics per run; tag source (seed vs emergent) | missing | **P0** |
| Novel-verb tracker | Track first time each verb is used + first mechanic match | missing | P1 |
| Vocabulary growth curve | Plot: distinct verbs, subtypes, edge types vs tick number — convexity = emergence | missing | P1 |
| Agent divergence metric | How differently do two agents behave given identical universe? (personality effect) | missing | P2 |
| Conservation violation log | Ticks that hit `ConservationChecker` — root-cause tag | partial (checker exists, log surfaces are incomplete) | P1 |

### F. Sharing & Demo Infrastructure

| Tool | Purpose | Status | Priority |
|---|---|---|---|
| Hosted dashboard (public URL) | Click a link, see a universe move. GitHub Pages or Cloudflare Pages static SPA reading live data | missing | P1 |
| `token-world archive <slug> --out foo.tar.gz` | Full universe export (graph + mechanics + tick_summaries + operator-log) for sharing | missing | P1 |
| `token-world import foo.tar.gz` | Reproduce a shared universe locally | missing | P1 |
| Recording mode | Headless tick run + asciinema/MP4 capture for embedding in blog posts | missing | P2 |
| Gallery of emergent universes | Curated set of shipped universe archives with notes on what emerged | missing | P2 |
| README demo GIF | 10-second animation of the dashboard for the top of README.md | missing | P2 |
| Blog post scaffold | Draft + screenshots + a "try it yourself" button | missing | P2 |

### G. Developer / Research Infrastructure

| Tool | Purpose | Status | Priority |
|---|---|---|---|
| Deterministic universe seed | Given seed X + initial state + tick count, final state should be reproducible (modulo LLM nondeterminism — use `claude-cli` backend + fixed temperature) | partial (RNG via ctx.rng) | P1 |
| Snapshot regression tests | After N ticks from seed S, expected graph structure holds | missing | P1 |
| Fuzz testing for mechanic authoring | Generate random action texts, confirm engine never crashes (only yields or refuses) | missing | P1 |
| Performance benchmarks | ticks/sec by (node count, mechanic count, LRA count) — track over time | missing | P2 |
| Cost-per-tick benchmark | $ per tick across backend + model combos | missing (partial via `cost` CLI) | P1 |
| `scripts/test_emergence.py` | Bootstrap a starter universe, run N ticks, assert M novel mechanics authored — integration test for the whole loop | missing | P1 |

---

### Tooling Stack: What To Build, In What Order

**Phase 1 (overnight / few hours)**: Everything marked **P0** above, plus the `token-world watch` terminal live-tail. At the end of Phase 1, an operator agent can drive a universe to emergence AND a human can follow along from the terminal.

**Phase 2 (next overnight)**: The P0 dashboard panels (tick stream, graph canvas, causal chain, stats strip). At the end of Phase 2, you can share a link.

**Phase 3 (next milestone)**: P1s — tick scrubber, mechanic registry table, agent inspector, replay mode, sharing exports, emergence detection metrics.

**Phase 4 (polish milestone)**: P2s — styling, dark mode, motion design, recording mode, gallery, blog.

**Principle: elegance comes from the engine, not the tooling.** The project must stay clean; the universes it births can be as spaghetti as they want. Tooling is scaffolding — make each tool single-purpose, composable (every CLI has `--format json`), and documented in the Script Catalog. Think of the CLI surface as a **query language for universes**, not a collection of one-off scripts.

---

## Friction Reduction + Backlog Cleanup (Good Warm-Up For Session 4)

Tonight — before you start on Tracks A/B/C — is a great opportunity to burn down accumulated paper cuts and dangling deferrals. Closing these first makes everything downstream smoother. Budget ~1-2 hours; parallelize via subagents where possible.

### Known Dangling Items (from `.planning/RETROSPECTIVE.md`)

| Item | Root cause | Fix | Priority |
|---|---|---|---|
| **Phase 04.1 SC-2 interactive smoke test** left `human_needed` | Needed live-API session at v1.0 close time; now zero-cost via `ClaudeCLIBackend` | Run the interactive smoke via `TOKEN_WORLD_BACKEND=claude-cli`, flip verification to `passed`, commit | **P0** — 20 min |
| **REQUIREMENTS.md traceability drift** (during v1.0) | Manual checkboxes diverged from phase completion | Build `scripts/check_requirements_traceability.py` (parses REQUIREMENTS + phase summaries, diffs status) + wire into CI | **P0** — ~1 h |
| **ROADMAP.md Progress table stale** (during v1.0) | Same root cause — manual updates drift | Build `scripts/check_roadmap_progress.py` (diffs PLAN/SUMMARY pairs vs Progress table) + wire into CI | **P0** — ~1 h |
| **Research docs drift** (`STACK.md`, `ARCHITECTURE.md`, `SUMMARY.md` under `.planning/research/`) — Opus-vs-Sonnet model routing is stale; more are probably stale | No timestamp or drift-detection | Add archival-timestamp header to each; refresh the canonically-stale claims (Opus is the mechanic generator, not Sonnet) | P1 — 30 min |
| **`agent_id` stub in `BatchSummary`** (`"unknown"` — P6 known gap) | Phase 6 shipped pre-multi-agent; `TickSummary` has no actor field | Add `actor_id` to `TickSummary` schema bump OR populate from first mutation's actor in `BatchSummary.maybe_compress` | P1 — 30 min |
| **`.planning/research/` docs** not scanned for obsolete Phase 2 D-15 folder-per-mechanic references | Supersession from Phase 4 | Grep + flag + rewrite the still-referring-to-folders passages | P2 — 20 min |
| **REQUIREMENTS.md was deleted at v1.0 close**, needs recreation for v1.1 | Expected on `/gsd-new-milestone` but there's no scaffold | When `/gsd-new-milestone` fires, confirm the new REQUIREMENTS.md is templated from v1.0 carry-forward + v1.1 new requirements | P1 — will happen naturally |

### Agent-Workflow Friction Observed Tonight (Candidates For Automation)

These are process nits that slow every session down. Fix them once, every future session is faster.

| Friction | Root cause | Proposed fix |
|---|---|---|
| `git commit` with heredoc messages blocked by `deny-ad-hoc-bash` hook | 300+ char bash commands blocked to prevent opaque pipelines | `scripts/commit.sh <message-file>` — a 3-line wrapper (`git commit -F "$1" && git push origin master`). Document in CLAUDE.md Bash Hygiene. Removes the "write to /tmp first" dance. |
| `/tmp/commit_msg.txt` reuse across sessions (Write tool refuses overwrite pre-Read) | `Write` safety — won't overwrite unseen file | Always use UNIQUE tmp paths (`/tmp/commit_wave1.txt`); OR wrapper that always starts clean; OR let the wrapper take the message inline as an arg |
| UAT 3-item flow is error-prone manually (create universe, run, edit prompt, run again, revert prompt, run --judge, inspect reports) | No encapsulation | `scripts/run_uat.py <slug>` — creates a test universe if needed, runs all 3 UAT items in sequence, edits+reverts the classifier prompt, asserts all 3 pass, prints verdict. Rerunning UAT becomes one command. |
| Finding files across `.planning/phases/` + reading CONTEXT/PLAN/SUMMARY for each | Manual directory hopping | `scripts/phase_show.py <N>` — prints a phase's CONTEXT + all PLAN titles + all SUMMARY headlines + VERIFICATION status in one scrollable block |
| CLAUDE.md Script Catalog drifts when scripts land but nobody updates it | Manual table maintenance | Either: (a) `scripts/check_catalog.py` CI check that parses `scripts/` dir and diffs against Catalog table, OR (b) convention that every `scripts/*.py` has a docstring-parseable header and Catalog is regenerated |
| Subagent prompts keep restating `CRITICAL_FILE_SCOPE_GUARDRAIL`, no-worktree mode, prev-session anti-patterns | Copy-paste every time | Extract reusable prompt fragments to `.planning/agent-prompts/` (e.g., `executor-preamble.md`) — each subagent spawn includes via `@.planning/agent-prompts/executor-preamble.md` — DRY for agent briefings |
| Reading CI status across many commits is tedious | `gh run list` returns raw table | `scripts/ci_status.py [--since SHA]` — since last deploy, show green/red per commit with links to failing jobs |
| Every new overnight session re-reads 6+ handoff files to get oriented | Handoff-file sprawl | Consolidate onboarding into a single `.planning/ONBOARDING.md` that links + excerpts the 6 files rather than forcing re-read. Keep MORNING-HANDOFF as the session-specific addendum. |

### Proposed Execution

**Session 4 warm-up (~2 h)**:

1. Spawn one subagent to close the 5 P0/P1 backlog items above (04.1 SC-2, 2 CI checker scripts, research doc refresh, `agent_id` fix).
2. Spawn a second subagent to build the automation artifacts (`scripts/commit.sh`, `scripts/run_uat.py`, `scripts/phase_show.py`, extract agent-prompt fragments).
3. Once both land, update CLAUDE.md Script Catalog with the new tools.
4. Then proceed with Track A/B/C from §Starter Moves.

**Low-risk. High leverage.** Every subsequent session benefits.

### Future-Self Note

After this cleanup sweep, the project should be close to the state where *the work an agent does that isn't "building emergence tooling" feels like it's literally zero friction.* If future sessions find NEW friction, add to this section and close in the next warm-up.

---

## Session 3 Summary (What Just Shipped)

17 commits (`75fa563..c19fb8b`). 1645 → 1743 tests (+98). Milestone v1.0 tagged, archived, retrospective written.

| Commit | What |
|---|---|
| `5efac0f..2a45e55` | Daydream seed mechanic — 4th composability demonstrator |
| `0085216..b5656e1` | Phase 07.1: LLMBackend Protocol + AnthropicSDKBackend + ClaudeCLIBackend; refactored Classifier/Observer/ResidentAgent |
| `512cdb6` | Phase 07.1 planning docs + helpers (inspect_playtest_report.py) |
| `6333b0f` | Phase 6 VERIFICATION — 3/3 live UAT items PASSED via claude-cli backend |
| `984ee0a..bfabf4c` | Milestone v1.0 archive (MILESTONES.md, RETROSPECTIVE.md, v1.0-ROADMAP.md, v1.0-REQUIREMENTS.md, git tag) |
| `b8f936f` | `docs/guides/claude-cli-backend.md` user-facing guide (244 LOC) |
| `1348f19` | `token-world cost` CLI command (405 LOC + 24 tests) |
| `8b4ce97` | Tech debt: `NoMatchResult.candidates` → top-K mechanic IDs |
| `5803ecd` | Tech debt: trace walker → `mechanic.trace` module (+ 4th call site consolidated) |
| `22c29fe` | Tech debt: `adversarial_rate` now consumed in PlaytestRunner |
| `2d078a9` | Tech debt: CLI `_load_or_create_agent` dedup |
| `1ef16d8` | Tech debt: belief overlay structural-key filter (v2 multi-agent prep) |
| `bb3076a` | Session 3 OVERNIGHT-REPORT + refreshed handoff |
| `7149267` | CLAUDE.md Script Catalog expanded |
| `c19fb8b` | README.md — v1.0 status + new guide links |

All MORNING-HANDOFF §6 tech debt items from prior session are closed. Full narrative: `.planning/OVERNIGHT-REPORT-20260414.md`.

---

## ⚠ Anti-Patterns (DO NOT REPEAT)

### Anti-Pattern 1 — Worktree base-mismatch BUG

`execute-phase` workflow's `<worktree_branch_check>` fallback uses `git reset --soft` which leaves working tree stale. Executor commits post-HEAD files as deletions.

**Mitigation:** spawn all executors in **no-worktree sequential mode** on main tree — omit `isolation="worktree"` from Task calls. Session 3 landed 17 commits with zero incidents using this pattern.

### Anti-Pattern 2 — Executors sneak edits outside plan scope

**Mitigation:** every executor prompt must include a `<CRITICAL_FILE_SCOPE_GUARDRAIL>` block enumerating forbidden files. Without it, silent scope violations happen.

### Anti-Pattern 3 — Re-using `/tmp/commit_msg.txt` across sessions

The `Write` tool refuses to overwrite a file not-yet-read in the current session. Use UNIQUE tmp paths per commit (e.g., `/tmp/commit_wave1.txt`, `/tmp/commit_belief.txt`) OR `Read` the file first before `Write`.

### Anti-Pattern 4 — Heredoc commit messages are blocked by a hook

There's a `deny-ad-hoc-bash.js` hook that blocks any bash command over ~300 chars with inline `<<HEREDOC`. Use `Write` to a tmp file + `git commit -F <tmp-file>` pattern instead.

### Don'ts (From Project CLAUDE.md)

- Don't call `nx.DiGraph` methods directly — always through `KnowledgeGraph` API
- Don't use `pickle`, SQLAlchemy, LangChain, MongoDB, CrewAI, `FastAPI`/`Flask` (see PROJECT.md tech-stack restrictions) — **but the dashboard may force a revisit of the web-framework ban; surface this as D-01 in v1.1**
- Don't write `random` in mechanics — use `ctx.rng` (Phase 5 D-19)
- Don't extend `match_mechanic_for_verb` in plan code (Phase 4 contract)
- Don't call `validate(run_tests=True)` from a test fixture (fork-bomb)
- Don't touch frozen MechanicContext DSL surface without updating `tests/test_mechanic/test_context_api.py::EXPECTED_CALLABLES`

---

## If The User Says "Show Me What Happened Overnight"

```bash
# State summary
git log --oneline v1.0..HEAD        # all session 3/4 work
cat .planning/OVERNIGHT-REPORT-20260414.md  # session 3 narrative
# session 4 will write .planning/OVERNIGHT-REPORT-20260415.md

# Run a demo
export TOKEN_WORLD_BACKEND=claude-cli
uv run token-world playtest uatworld --turns 5 --no-operator
uv run token-world cost uatworld

# After session 4 (if it ships any)
uv run token-world inspect uatworld
uv run token-world trace uatworld alice health
uv run token-world stats uatworld --stream
```

---

## Final Git State (End of Session 3)

```
master = c19fb8b
origin/master = c19fb8b (pushed)
tag v1.0 (annotated) — pushed to origin
CI = green (5 jobs across 17 commits)
Tests = 1743 passed, 14 skipped, 36 deselected
Lint + format + mypy = clean
```

No uncommitted changes. `.claude/scheduled_tasks.lock` is runtime state (untracked, expected).

---

## Handoff Files To Skim Before Starting Next Session

Priority order:

1. **This document (`MORNING-HANDOFF.md`)** — the vision + v1.1 mandate + starter moves (§Dashboard, §Operator CLI, §Emergence Loop)
2. **`.planning/OVERNIGHT-REPORT-20260414.md`** — session 3 narrative
3. **`.planning/MILESTONES.md`** + **`.planning/RETROSPECTIVE.md`** — v1.0 delivery summary + lessons
4. **`.planning/PROJECT.md`** — post-v1.0 rewrite; §Active has the original v1.1 candidates (this handoff reframes them into Tracks A-D)
5. **`.planning/phases/07.1-.../07.1-CONTEXT.md`** — claude-cli backend locked decisions
6. **`docs/guides/claude-cli-backend.md`** — user-facing guide for the zero-cost UAT backend
7. **`src/token_world/engine/llm_backend.py`** — the new backend abstraction (147 LOC)
8. **`src/token_world/mechanic/trace.py`** — the trace walker (session 3 extraction; useful building block for causal chain CLI)

---

**Go build the stage. Seed the garden. Let the universes bloom.** 🌱🌌

*— Session 3, signing off.*
