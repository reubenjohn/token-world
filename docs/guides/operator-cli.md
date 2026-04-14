# Operator CLI Surface

These are the read-only inspection commands an operator (human or
subagent) uses to understand a universe's state without launching the
dashboard. Every command supports `--format table|json`; the JSON shape
is the stable contract that the dashboard and other scripts consume.

All commands live under the `token-world` Click group and resolve the
universe through `UniverseManager.load(slug)`.

## `inspect`

Universe-at-a-glance. One screen of: graph shape (node counts by
type, edge count), mechanic count split by author (seed/operator),
last N ticks summarised one-line each, active long-running actions,
recent yield events, and operator-log status.

```
token-world inspect demo-tavern
token-world inspect demo-tavern --last 25
token-world inspect demo-tavern --format json | jq .ticks.recent
```

The author classification is a heuristic: a mechanic counts as
"operator-authored" when its module sets `__author__ = "operator"`
or the first git commit that introduced the file has a subject
starting with `operator:`.

## `tick`

Pretty-print a single tick's full detail tree.

```
token-world tick demo-tavern 42
token-world tick demo-tavern 42 --format json
```

Tree sections: action_text → classification (verb/subject/object/
modifier/confidence) → decision (executed/yielded/refused) →
mutations → observation → metadata (duration_ms, llm tokens & cost
per stage). JSON output is the on-disk TickSummary v1 payload
verbatim.

Exit codes: `0` ok / `1` universe not found / `2` tick id not found
on disk / `3` tick file is malformed JSON.

## `trace`

Causal-chain walker. Given a node id and property, walks the
`graph_events` SQLite table backward and enriches each hop with the
surrounding tick context (action text, classified action, matched
mechanic, observation).

```
token-world trace demo-tavern alice health
token-world trace demo-tavern alice health --hops 5
token-world trace demo-tavern alice health --format json
```

Hops are emitted oldest-first so the chain reads forward in time.
`--hops N` caps the walk (default 10). Graceful boundaries:
`db_missing` (no `universe.db`), `not_found` (no events ever touched
the property), `tick_missing` per-hop (event references a tick file
that no longer exists).

## `mechanics`

Registry browser with call counts, last-invoked tick, tags, source
path, and author classification.

```
token-world mechanics demo-tavern
token-world mechanics demo-tavern --author operator
token-world mechanics demo-tavern --format json
```

Call counts come from a single pass over `tick_summaries/ticks/`
counting `matched_mechanic_id` occurrences. The `--author` filter
applies AFTER enrichment so call counts always reflect the unfiltered
registry.

## `stats`

Aggregate metrics: throughput, yield/refuse rates, novel-mechanic
rate, distinct emergent subtype count, conservation violations, and
cost (composed with `token-world cost`).

```
token-world stats demo-tavern
token-world stats demo-tavern --since 100
token-world stats demo-tavern --stream --interval 2.0
token-world stats demo-tavern --format json
```

`--since N` scopes ALL metrics (including the cost block) to the last
N ticks. `--stream` re-emits the full stats block whenever the ticks
directory mtime advances (poll-based; no fsnotify dependency).

The novel-mechanic-per-10-ticks metric is derived from
`matched_mechanic_id` first-occurrences within the scanned window.
The distinct-subtype metric counts unique values written via
`subtype` mutations — a cheap proxy for the "is the universe growing
new concepts?" question.

## `watch`

Live tail of newly-written tick summaries to stdout. Polls
`<universe>/tick_summaries/ticks/` at a configurable interval and
emits one line per newly-appeared tick.

```
token-world watch demo-tavern
token-world watch demo-tavern --interval 0.5
```

Existing files at startup are pre-seeded into the "seen" set so they
are NOT re-emitted. Ctrl-C to exit. The output line shape is:

```
[tick_id] timestamp status (N mut) observation_excerpt
```

## `agents`

Inspect agent-typed nodes. Without `--id`, summarises every agent in
the graph. With `--id alice`, returns the full property bundle for
that single agent.

```
token-world agents demo-tavern
token-world agents demo-tavern --id alice
token-world agents demo-tavern --format json
```

Properties are bucketed into well-known groups: `personality`,
`persona_text`, `memory_entries`, `current_long_action`,
`attention_state` (D-12 nested in the LRA `payload`), plus
`other_properties` for everything else. Exit code `4` when `--id`
doesn't match any agent (distinct from `1` = universe not found).

## `diff`

Show graph changes between two ticks via `graph_events` replay.

```
token-world diff demo-tavern 10 20
token-world diff demo-tavern 100 50    # auto-swapped to 50..100
token-world diff demo-tavern 10 20 --format json
```

Reports: nodes added/removed, edges added/removed, property changes
(`old -> new`). When the same property is mutated multiple times in
the window, the change row is marked `(multi)` to signal that
intermediate values were elided. The half-open interval is
`(tick_a, tick_b]` so events at `tick_a` are excluded — they
established the baseline, not the diff.

## Composing commands

The JSON output of each command is the stable consumer contract. To
pipe between commands or feed a dashboard:

```
# Recent tick IDs across the last 50 ticks, oldest-first.
token-world inspect demo-tavern --last 50 --format json \
  | jq -r '.ticks.recent[] | .tick_id'

# Cost per agent action across the entire run.
token-world stats demo-tavern --format json | jq .cost_total_usd

# Yields with their classified action text.
for id in $(token-world inspect demo-tavern --last 100 --format json \
              | jq -r '.recent_yields[].tick_id'); do
  token-world tick demo-tavern "$id" --format json | jq '.action_text'
done
```
