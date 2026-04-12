# viz-graph — Filtered Mermaid Diagrams of a Universe

`token-world viz-graph` emits a **filtered** Mermaid flowchart slice of a universe's
knowledge graph. Pipe the output into a Mermaid renderer (GitHub markdown, VS Code
preview, `mcp-mermaid`) to eyeball neighbourhoods during debugging and gap analysis.

## Why

Token World graphs grow to thousands of nodes (agents, entities, items, rooms, relations).
Whole-graph rendering produces an unreadable spaghetti. `viz-graph` is intentionally
filter-first: you must supply an **anchor** and the tool walks a bounded ego-graph from
there. No "render everything" mode exists — that is a design decision (see _Anchor is
mandatory_ below).

## Quick Examples

```bash
# One agent + their immediate neighbourhood
token-world viz-graph my-universe --node alice --depth 2

# Every agent-typed node and their direct neighbours
token-world viz-graph my-universe --all-agents

# Every node with property subtype=room, plus their depth-1 neighbours
token-world viz-graph my-universe --seed-query subtype=room --depth 1

# Write to file (good for diffs across ticks)
token-world viz-graph my-universe --node alice --output alice.mmd

# Minimal output (no emoji, no classDef) — machine-friendly
token-world viz-graph my-universe --node alice --depth 1 --no-style

# Multiple seed queries (repeatable flag) — union of matches
token-world viz-graph my-universe \
    --seed-query node_type=agent \
    --seed-query subtype=room \
    --depth 1
```

## Flags

| Flag                 | Purpose                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------ |
| `--node ID`          | Anchor for the ego-graph. Walks `--depth` hops (undirected) from this node.                |
| `--depth N`          | Hops from anchor(s). Default `1`.                                                          |
| `--seed-query K=V`   | Anchor = all nodes whose property `K` equals `V`. Repeatable; results are unioned.         |
| `--all-agents`       | Anchor = every node with `type=agent`.                                                     |
| `--type agent/entity`| Keep only this node type in the final subgraph (anchors are always preserved).             |
| `--has-property N`   | Keep only nodes that carry property `N` (anchors always preserved).                        |
| `--exclude-property N`| Drop nodes that carry property `N` (anchors always preserved).                            |
| `--max-nodes N`      | Hard cap on the filtered node count. Default `150`. Exceeds => exit 4.                     |
| `--output FILE`      | Write Mermaid to `FILE` instead of stdout. Prints a byte-count confirmation line.          |
| `--no-style`         | Emit minimal Mermaid (no `classDef`, no emoji) — easier to diff.                           |

## Anchor is mandatory

An anchor is **required**. Running without `--node`, `--seed-query`, or `--all-agents`
exits non-zero with a pointer to those flags. This is deliberate — rendering an
unfocused graph is almost never useful and the resulting diagram obscures rather than
illuminates.

**Exit codes:**

| Code | Meaning                                               |
| ---- | ----------------------------------------------------- |
| `0`  | Success (Mermaid written to stdout or `--output`).    |
| `1`  | Universe not found.                                   |
| `2`  | Missing anchor or malformed `--seed-query`.           |
| `3`  | Anchor set resolved to zero nodes (no matches).       |
| `4`  | Filtered subgraph exceeds `--max-nodes`.              |

## Rendering to PNG / preview

The command prints raw Mermaid text. You can:

- **Paste** the output into any Markdown viewer (GitHub, VS Code Mermaid preview,
  Obsidian) — Mermaid is rendered natively.
- **Pipe** to [`mcp-mermaid`](https://github.com/peng-shawn/mermaid-mcp-server) or
  the Mermaid CLI (`mmdc -i in.mmd -o out.png`) to generate a PNG/SVG.
- **Spot-check** programmatically: the first non-empty line is always `flowchart LR`.

## When rendering fails

The most common failure mode is hitting the `--max-nodes` cap on a dense graph. The
error message tells you exactly what to tighten. Ordered from cheapest to sharpest:

1. Drop `--depth` to `1` — big blast-radius reductions.
2. Add `--type agent` or `--type entity` to halve the node set.
3. Use `--exclude-property bbox` (or similar noisy spatial props) if your
   display-label heuristic matters.
4. Narrow `--seed-query KEY=VALUE` instead of `--all-agents`.
5. As a last resort, raise `--max-nodes` — but note that >150 nodes in a Mermaid
   flowchart is usually unreadable.

## Node label format

Each node renders as:

```
<emoji> <node_id><br/>
<subtype if present><br/>
<up to 1 additional scalar property>
```

- Agents get `👤`, entities get `🏛`. `--no-style` drops both emoji and `classDef`.
- `subtype` is always prioritised if present. Other properties are selected
  deterministically (sorted-key) from scalar values (`str/int/float/bool`).
- Noisy properties are skipped by default: `position`, `bbox`, `type`, `node_type`.
- Every segment passes through `escape_label()` with a 60-char truncation suffix (`…`).

## Security note

Node IDs and property values flow directly from the knowledge graph into Mermaid
syntax. Dangerous characters (`"`, `|`, `[`, `]`, newlines) are **automatically
escaped** to HTML entities in labels, and node IDs are **sanitised** to
alphanumerics + `_`, with a SHA-256 suffix appended when collisions are possible
(so `x"` and `x|` render as distinct Mermaid IDs). You can safely viz graphs
containing user-supplied node IDs — the Mermaid parser will not be confused and
injection attacks via crafted labels are mitigated (threat T-03-02).
