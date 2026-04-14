---
Status: canonical / adopted 2026-04-15
Scope: every overnight / multi-hour simulation run
Companion: [dashboard-qa-checklist.md](dashboard-qa-checklist.md)
---

# Simulation Quality Rubric

## Why this exists

Tick 34 of the Willowbrook round-2 run was recorded as `EXECUTED`. The
agent had asked to unlock a chest; the mechanic's `check()` returned
False because the chest was already unlocked. The engine correctly
refused, but the *tick summary* serialised the refusal into the same
`status` field as a real execution. Nothing failed in the test suite
because no test asserted "refused ticks are distinct from executed
ticks."

That's the pattern this rubric exists to catch. Unit tests answer
"does this function do what its docstring says?" The rubric answers
**"is the run as a whole behaving like a healthy simulation?"**

The two measurements are not substitutes. A run can pass every test
and still be degenerate — a character breaking immersion for 40 ticks,
a mechanic silently violating conservation, an exponentially-growing
set of duplicate edges. Tests do not catch those; the rubric does.

Every overnight run ends with `token-world quality <slug>` printing
the scorecard below. CI gates release-tier runs on the scorecard
staying in the green ranges for the last 50 ticks. The morning report
flags any run that degraded and names the failing dimension.

---

## Dimensions

Seven dimensions. Each has an intuition (what we're actually trying
to measure), a source/formula (where the number comes from), a green
range (healthy), and a red range (alarm).

### 1. Groundedness

- **Intuition:** the observation the agent receives must not contradict
  the projected_state computed from the mechanic's mutations. If the
  observation says "you unlock the chest" but the graph says
  `chest.locked == True`, the simulation lied to the agent. Ungrounded
  observations corrupt agent memory on every subsequent tick.
- **Source:** `playtest.scorer.groundedness` — already computed per
  tick. Extend with per-tick observer cross-check: after Sonnet
  generates the observation, diff the claimed state-changes against
  the actual `Mutation` list produced by the mechanic.
- **Formula:** `groundedness = 1 - (ungrounded_ticks / total_ticks)`
  over the last 50 ticks.
- **Green:** `>= 0.95` — at most 2 ungrounded ticks per 50.
- **Red:** `< 0.85` — more than 7 ungrounded ticks per 50. Halt
  autonomous runs; the observer model is drifting from ground truth.

### 2. Character stability

- **Intuition:** the resident agent must stay inside the fiction.
  Meta-narration markers ("framework", "yield", "mechanic", "system
  prompt", "operator", "scenario") in `action_text` are a direct
  signal that the agent has become self-aware of the scaffolding. See
  Mira's tick 44 — "I recognize we've hit the yield boundary
  repeatedly" — exactly the kind of break that ruins the subsequent
  observation chain.
- **Source:** new — scan `action_text` of every recent agent turn for
  marker substrings. Configurable list at
  `src/token_world/quality/markers.py` (forward-referenced — not yet
  implemented).
- **Formula:** `stability = 1 - (turns_with_markers / total_turns)`
  over the last 50 ticks.
- **Green:** `>= 0.98` — at most 1 marker-containing turn per 50.
- **Red:** `< 0.90` — 5+ breaks per 50. Tighten the system prompt or
  auto-halt on the next break.

### 3. Action coherence

- **Intuition:** a healthy simulation has long runs of successful
  action. Frequent refuses mean the classifier vocabulary is too
  narrow, the agent is confused, or both. Clusters of refuses are
  a leading indicator of an impending character break.
- **Source:** scan `tick_summaries/` for refuse status. Existing
  per-tick data; no new instrumentation needed.
- **Formulas:**
  - `longest_coherent_streak` = longest run of non-refuse ticks in
    the window.
  - `refuse_rate_10tick` = mean refuses per 10-tick window.
- **Green:** `longest_streak >= 15` AND `refuse_rate_10tick <= 1.5`.
  Occasional refuses (vocabulary exploration) are healthy; long
  streaks of refuses are not.
- **Red:** `longest_streak < 5` OR `refuse_rate_10tick >= 4`. The
  agent has lost grip on the action space. Halt, review, adjust
  seed mechanics or prompt.

### 4. Refusal cluster alarm

- **Intuition:** a single refuse is normal; three in a row is the
  agent stuck; five in a row is a wedge. This dimension is distinct
  from #3 because it's a *real-time* alarm — the moment the cluster
  hits K, the runner halts.
- **Source:** single running counter in the PlaytestRunner /
  `run_unattended.py`. Resets to zero on any non-refuse tick.
- **Formula:** `consecutive_refuses`; alarm when `>= 5`.
- **Green:** `consecutive_refuses <= 2` at all times in the window.
- **Red:** `consecutive_refuses >= 5` at any point. Runner auto-halts
  with a noted reason; cluster tick ids logged for post-mortem.

### 5. Vocabulary growth

- **Intuition:** a healthy emergent simulation introduces novel verbs
  at a steady trickle. Zero novel verbs means the agent is stuck in
  a local action loop; too many novel verbs means the classifier is
  fabricating rather than matching, which breaks the matcher's
  ability to reach the same mechanic twice.
- **Source:** existing `stats` aggregator — `novel_verbs_per_10_ticks`.
- **Formula:** `novel_verbs / (window_size / 10)` — average per
  10-tick bucket.
- **Green:** `0.5 <= rate <= 2.5`. One novel verb every 4-20 ticks.
- **Red:** `rate == 0` for 30+ consecutive ticks (simulation is
  stagnant) OR `rate > 4` sustained (classifier is fabricating).

### 6. Conservation drift

- **Intuition:** the engine rolls back any tick where a registered
  conservation invariant fails (e.g. total items in inventory
  preserved across pickup/drop pairs). Rollbacks are expected
  occasionally — mechanics authored by subagents sometimes miscount.
  Frequent rollbacks mean the mechanic library has accumulated bugs.
- **Source:** existing `engine.conservation` counters.
- **Formula:** `rollback_rate = rollback_ticks / total_ticks` over
  the last 50 ticks.
- **Green:** `<= 0.02` (1 rollback per 50 ticks or fewer).
- **Red:** `>= 0.10` (5+ rollbacks per 50 ticks). Audit recently
  authored mechanics for conservation regressions.

### 7. Graph fan-out

- **Intuition:** a world getting richer is adding nodes and edges.
  Average edges per node should trend up slowly over a long run; a
  flat or decreasing curve means the agent is only interacting with
  the existing structure, not expanding it.
- **Source:** new — cheap graph scan. Run once per N ticks (e.g.
  every 10) and record `avg_edges_per_node` to a run-scoped
  time-series.
- **Formula:** `fan_out = edges / nodes` at checkpoint; track slope
  across the last 5 checkpoints (`(last - first) / elapsed_ticks`).
- **Green:** slope `>= 0` (flat or growing). Early ticks may grow
  fast; late ticks may flatten — both acceptable.
- **Red:** slope `< -0.02` per 10 ticks sustained over 3 checkpoints.
  The graph is shrinking — mechanics are removing nodes/edges faster
  than they add, which usually means an unbalanced cleanup mechanic.

---

## Scorecard format

The output of `token-world quality <slug>` (TODO, forward-referenced)
prints one line per dimension plus an overall verdict:

```
Willowbrook · last 50 ticks

  [OK]    Groundedness       0.96    (48/50 grounded)
  [OK]    Character          1.00    (0 breaks)
  [WARN]  Action coherence   streak=7  refuse_rate=2.1
  [OK]    Refusal cluster    max=2  (< 5)
  [OK]    Vocabulary         1.4 novel-verbs/10t
  [OK]    Conservation       0.00    (0/50 rollbacks)
  [WARN]  Graph fan-out      slope=-0.008  (trending down)

  Verdict: DEGRADED — action coherence and graph fan-out in warn.
```

- **[OK]**: dimension in green range.
- **[WARN]**: dimension between green and red — not a halt but
  flagged in morning report.
- **[FAIL]**: dimension in red range.
- **Verdict**:
  - `HEALTHY`: all dimensions OK.
  - `DEGRADED`: one or more WARN, zero FAIL.
  - `FAILED`: any FAIL.

---

## CI gate

A run is healthy if **all seven dimensions stay in green ranges for
the last 50 ticks.**

- **Release-tier runs** (the overnight runs that feed the morning
  report) gate on this. A `FAILED` verdict blocks the run from being
  recorded as a reference sample.
- **Development runs** (operator-driven manual ticks) do not gate,
  but the scorecard still prints — operator can see at a glance
  whether a session has drifted into a bad regime.
- **Phase verification**: any phase whose acceptance criteria mentions
  "simulation behaviour" must run `token-world quality` as a
  pre-merge check. See `docs/design/simulation-pipeline.md` for the
  full tick flow this rubric observes.

---

## Target surface

### `token-world quality <slug>` (CLI) — TODO

Not yet implemented. Forward-referenced. When built:

- **Inputs:** slug, optional `--window N` (default 50), optional
  `--format json`.
- **Outputs:** the scorecard above (table format) or a JSON
  equivalent for CI consumption.
- **Location:** implementation lands in `src/token_world/quality/`
  subpackage. CLI wrapper in `src/token_world/cli/quality.py`.
- **Data source:** existing `tick_summaries/*.json`, `stats`
  aggregator, `engine.conservation` counters, plus the new
  per-tick observer cross-check for groundedness.
- **Canonical producer rule:** the rubric is computed **once**, in
  `quality/`. The dashboard quality panel (also TODO) consumes the
  same JSON output — no duplicated logic across CLI + dashboard.

### Dashboard quality panel — TODO

Consumes `token-world quality --format json` and renders a quality
strip above the existing stats strip:

- Seven coloured cells, one per dimension, green/amber/red.
- Click a cell to expand the underlying time series.
- Refreshes every 10 seconds (slower than stats — quality is a
  slower-moving signal).

When this panel lands, it is subject to
[dashboard-qa-checklist.md](dashboard-qa-checklist.md) like every
other panel. No shortcuts.

---

## Out of scope (for now)

- **Per-agent rubrics**: when multi-agent rotation lands (D-17), each
  agent will need its own character-stability dimension. Deferred
  until then.
- **LLM-cost pressure as a dimension**: cost is tracked separately in
  `token-world cost`. It is a budget concern, not a quality concern
  — a run can be over budget and still healthy, or on budget and
  degenerate.
- **Emergence depth**: "how interesting is the emergent behaviour?" is
  a qualitative judgement that currently rests with the operator.
  Until we have a robust proxy, no automated dimension.

---

## Related

- [dashboard-qa-checklist.md](dashboard-qa-checklist.md) — sibling
  rubric for dashboard PR gating. The dashboard's quality panel is
  subject to both: the checklist gates the *panel* code; this rubric
  gates the *numbers* it displays.
- `MORNING-HANDOFF.md` §K2, §D — the discussion this rubric codifies
  and the KPI table it systematises.
- `src/token_world/playtest/scorer.py` — existing groundedness
  scoring; this rubric extends it into a full scorecard.
- `docs/design/simulation-pipeline.md` — the tick flow this rubric
  observes from the outside.
