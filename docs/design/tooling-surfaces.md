# Tooling Surfaces — CLI / MCP / Dashboard Allocation Principle

## 1. Purpose

Token World exposes functionality through three complementary surfaces: a
**CLI** (`token-world ...`), an **MCP** server (live-run operator tools like
`resume_tick`, `rollback`, `list_mechanics`), and a **Dashboard** (the NiceGUI
read-only web UI). These are not redundant views of the same thing. Every new
tool feature's primary home is **one** of these three surfaces; the others
consume its output if they need it. This doc captures the rule-of-thumb so new
features are allocated deliberately instead of reflexively landing wherever
the current PR happens to touch.

## 2. The three surfaces

| Surface | Best when… | Strengths | Weaknesses |
|---|---|---|---|
| **CLI** | stateless query, scripting, subagent consumption, morning review, diff/audit | pipe-composable; uniform `--format json`; fast; text-centric; Git-friendly | not visual; not live |
| **MCP** | operator mutates a running simulation (resume/rollback); the operator's "hands" | fits inside Claude Code + Agent SDK; LLM-native invocation; narrow surface area | narrow by design — only the live-run actions; not a general query layer |
| **Dashboard** | continuous monitoring, spatial/visual views, non-developer audience, comparison over time, shareable | visual; reactive; low-friction for non-devs | browser required; not scriptable; not pipe-composable |

**Token World context per row:**

- **CLI.** ~80% of daily orchestration traffic in session 4 went through the
  CLI even while the dashboard was being built — because subagents, morning
  review passes, and cost/stats audits all want `--format json` output that
  `jq` or another agent can consume. The CLI is the scripting backbone.
- **MCP.** Intentionally narrow: it exists because Claude Code (the operator)
  needs to *mutate* a running simulation without shelling out. If a feature
  is a query, it probably does not belong here; if it changes live-run state,
  it probably does.
- **Dashboard.** Built for the human review pass *after* automated work
  settles. The graph canvas, live tick stream, and property-history panel
  are shapes a terminal cannot convey — that is the dashboard's unique value.

## 3. Decision rules

Each rule below is followed by a Token World example taken from recent
sessions (see `MORNING-HANDOFF.md §F` for the full gap table).

1. **Is it a precise, scripted query — and/or will a subagent consume it?
   → CLI.**
   *Example:* "See the classifier's raw response for a refused tick." A
   subagent debugging a refusal needs machine-readable stage output. The
   right shape is `token-world tick <slug> <id> --stage classification --raw`,
   not a new dashboard panel. Agents and humans both consume the same JSON.

2. **Does it mutate a running simulation? → MCP.**
   *Example:* `resume_tick` after the engine yielded for operator approval,
   or `rollback` to a prior snapshot. These only make sense against a live
   engine; they are the operator's "hands on the wheel" and belong where
   Claude Code can invoke them directly.

3. **Does it help a human observer watching the run unfold, or is it
   inherently visual/spatial? → Dashboard.**
   *Example:* "Spot Mira decompensating before it's 10 turns of gibberish."
   A refusal-cluster KPI tile, or a red dot on the stats strip, catches the
   eye in a way that re-running `inspect --last 10` never will. Also:
   "Is the engine progressing right now?" — a live `Run status` indicator
   driven by the runner's PID file is a dashboard concern, not a CLI one.

4. **Does it live in more than one bucket? → CLI first; dashboard consumes
   CLI JSON. Do not re-implement in the dashboard.**
   *Example:* "Follow a property's history backward." `token-world trace`
   already walks `graph_events` and enriches each hop with tick context. The
   dashboard's property-history panel (see §A5a) reads that same pipeline
   and renders it as a tree. One computation, two front-ends.

5. **Is it a one-off tooling gap I hit while investigating? → Promote to
   CLI or dashboard per rules 1–3. Never leave as ad-hoc bash.**
   *Example:* "Check what just emerged in the universe git log" started as
   `cd <universe>; git log --oneline mechanics/` and should be promoted to
   `token-world mechanics <slug> --history`. The test is simple: if the
   bash would help the next agent too, it is already code — commit it. This
   is the same rule as CLAUDE.md principle 4 ("ad-hoc bash is a missing-tool
   signal").

## 4. Worked examples

### 4a. Scripted query — `token-world trace` (property history)

**Primary home: CLI.** `trace` walks `graph_events` backward for a given
(node, property) pair and enriches each hop with the surrounding tick
summary. It is stateless, deterministic, and returns structured JSON — which
is exactly what a subagent asking "why is `mira.energy = 0.72`?" needs.

**Dashboard consumes, does not reimplement.** The dashboard's
property-history panel (renamed from "causal chain" per §A5a to disambiguate
it from the per-tick forward side-effect chain) loads the same
`trace(slug, node, property)` output and renders it as a visual tree. The
computation lives exactly once; the dashboard is a view.

**MCP: not involved.** `trace` does not mutate anything.

### 4b. Live-run mutation — `resume_tick` (MCP)

**Primary home: MCP.** When the engine yields for operator approval, the
operator (Claude Code) must be able to resume, rollback, or patch via tools
available in-session. `resume_tick(universe, tick_id, decision)` is exactly
the shape the MCP surface is built for: a mutating action against a live
process, scoped narrowly to live-run operations.

**CLI: complements via observation.** `token-world yield <slug> --pending`
(proposed, §F row 1) shows what *would* be resumed — a read-only snapshot
of the pending yield payload — but the actual resume call goes through MCP.
This keeps the mutation path singular and auditable.

**Dashboard: complements via a sticky "Active Yield" banner** that surfaces
the pending decision visually, but does not itself perform the resume.

### 4c. Monitoring view — live tick stream (Dashboard)

**Primary home: Dashboard.** A scrolling, reactive feed of new tick
summaries — with colour coding for yields, refusals, and novel mechanics —
is inherently a visual-observer feature. A human watching a run for five
minutes learns more from the visual feed than from scrolling a log file.

**CLI complements for scripting: `token-world watch <slug> --interval S`.**
Same underlying event source, different front-end. The CLI variant is what
you run over SSH, pipe into another process, or tail from a subagent. The
dashboard variant is what you leave up on a second monitor during a run.

**MCP: not involved.** Observation is not mutation.

## 5. Anti-patterns

- **Re-implementing the same computation in two surfaces.** If the dashboard
  walks `graph_events` itself instead of calling `token-world trace`, the
  two implementations will drift and one will silently become wrong. Compute
  once, render twice. (This applies to stats aggregation, cost rollups,
  mechanic history — anywhere a CLI command already produces the JSON.)
- **Treating the dashboard as a CLI replacement for automation.** The
  dashboard is not scriptable. If a workflow wants "tail ticks, grep for
  refusals, alert," that belongs in the CLI (`watch` piped to `jq`) or in
  a dedicated script under `scripts/`. Forcing automation through a browser
  UI is how you end up with Selenium scripts nobody can debug.
- **One-off ad-hoc bash that should have been promoted.** Pipelines like
  `cat diagnostics/tick_N/classification/response.txt` or
  `ls <universe>/tick_summaries/ticks/*.json | wc -l` are a signal that a
  tool is missing. Per CLAUDE.md principle 4, promote them the first time
  you reach for them — to CLI, dashboard, or `scripts/`, per the decision
  rules above. Never leave them in shell history as "the way we check X."

## 6. How to use this doc in a GSD phase

Every phase `CONTEXT.md` that adds a user-facing tooling or UX feature must
**name the primary surface** (CLI, MCP, or Dashboard) and **justify via one
of the decision rules in §3**. If the feature spans surfaces, say which one
is the computation's home and which are consumers. This is a one-paragraph
addition to CONTEXT — cheap to write, and it forces the surface choice to
be deliberate rather than accidental. When a rule no longer fits a new
situation, flag it and propose an edit to this doc in the same PR rather
than silently working around it.
