---
phase: 03-design-validation
plan: 04
type: execute
wave: 1
depends_on: [01]
files_modified:
  - src/token_world/viz/graph_viz.py
  - src/token_world/viz/__init__.py
  - src/token_world/cli.py
  - tests/test_viz/test_viz_graph.py
  - tests/test_cli/test_viz_graph.py
  - tests/test_cli/__init__.py
  - docs/guides/viz-graph.md
autonomous: true
requirements:
  - AUTO-04
tags:
  - cli
  - mermaid
  - visualization

must_haves:
  truths:
    - "Running `token-world viz-graph <universe> --node alice --depth 2` emits a valid Mermaid flowchart to stdout"
    - "Running `token-world viz-graph <universe>` without any anchor flag exits non-zero with an error mentioning --node/--seed-query/--all-agents"
    - "Running on a subgraph that exceeds --max-nodes (default 150) exits non-zero and suggests tightening the filter"
    - "Node labels with dangerous characters (quotes, pipes, brackets, newlines) are escaped in Mermaid output"
    - "--type, --has-property, --exclude-property filters reduce the subgraph as expected"
    - "Whole-graph rendering is impossible by design (enforced by the anchor requirement)"
  artifacts:
    - path: "src/token_world/viz/graph_viz.py"
      provides: "extract_subgraph, to_mermaid, TooManyNodesError, render_node_label, render_edge_label"
      exports: ["extract_subgraph", "to_mermaid", "TooManyNodesError"]
      min_lines: 100
    - path: "src/token_world/cli.py"
      provides: "viz-graph Click subcommand registered on the cli group"
      contains: "viz-graph"
    - path: "docs/guides/viz-graph.md"
      provides: "User-facing guide: flags, examples, mcp-mermaid rendering, 150-node cap rationale"
      min_lines: 40
  key_links:
    - from: "src/token_world/cli.py"
      to: "src/token_world/viz/graph_viz.py"
      via: "import extract_subgraph, to_mermaid"
      pattern: "from token_world.viz"
    - from: "src/token_world/cli.py"
      to: "src/token_world/universe/manager.py"
      via: "UniverseManager.load(slug) to resolve universe folder + db path"
      pattern: "UniverseManager"
    - from: "src/token_world/viz/graph_viz.py"
      to: "networkx.ego_graph"
      via: "undirected=True for bidirectional neighborhood view"
      pattern: "ego_graph.*undirected=True"
    - from: "src/token_world/viz/graph_viz.py"
      to: "src/token_world/viz/mermaid.escape_label"
      via: "every node and edge label runs through escape_label before emission"
      pattern: "escape_label"
---

<objective>
Deliver `token-world viz-graph` — a Click subcommand that emits filtered Mermaid flowchart output from a universe's knowledge graph. Enforces mandatory anchor, caps subgraph size, and escapes Mermaid-hostile characters in labels.

Purpose: Let agents (and humans) inspect specific slices of large graphs during debugging and gap analysis. Closes the feedback loop on mechanic interactions — pipe output to `mcp-mermaid` to render visually.

Output: Working CLI command, viz module with ego-graph extraction and Mermaid emission, green smoke tests, and a short user guide.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/03-design-validation/03-CONTEXT.md
@.planning/phases/03-design-validation/03-RESEARCH.md
@src/token_world/graph/knowledge_graph.py
@src/token_world/universe/manager.py
@src/token_world/cli.py
@src/token_world/viz/mermaid.py
@tests/test_viz/test_viz_graph.py

<interfaces>
Target module API (from RESEARCH.md §Mermaid Graph Visualization):
```python
class TooManyNodesError(Exception):
    """Raised when filtered subgraph exceeds --max-nodes."""

def extract_subgraph(
    kg: KnowledgeGraph,
    *,
    anchor: str | None = None,
    anchors: list[str] | None = None,
    depth: int = 1,
) -> nx.DiGraph:
    """NetworkX ego_graph (undirected=True) from a single anchor, or union from a list."""

def to_mermaid(
    kg: KnowledgeGraph,
    sub: nx.DiGraph,
    *,
    max_nodes: int = 150,
    style: bool = True,
    type_filter: str | None = None,
    has_property: str | None = None,
    exclude_property: str | None = None,
) -> str:
    """Emit a `flowchart LR` Mermaid document. Raises TooManyNodesError if too big."""
```

CLI (extends src/token_world/cli.py):
```
token-world viz-graph <universe> [OPTIONS]
  --node ID                 Anchor for ego-graph
  --depth N                 Hops (default 1)
  --seed-query KEY=VALUE    Anchors: nodes with property match (repeatable)
  --all-agents              Use all agent-typed nodes (depth 1)
  --type {agent|entity}     Keep only this node type (besides anchors)
  --has-property NAME       Keep only nodes with this property
  --exclude-property NAME   Drop nodes with this property
  --max-nodes N             Hard cap (default 150)
  --output FILE             Write to file, else stdout
  --no-style                Emit minimal Mermaid (no classDef, no emoji)
```

UniverseManager.load(slug) → universe_dir path. The universe DB lives at `<universe_dir>/universe.db` (verified via `src/token_world/universe/paths.py`).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement viz/graph_viz.py (extract_subgraph, to_mermaid, label rendering, node cap)</name>
  <files>src/token_world/viz/graph_viz.py, src/token_world/viz/__init__.py, tests/test_viz/test_viz_graph.py</files>
  <read_first>
    - src/token_world/graph/knowledge_graph.py (for `._graph` access convention — or use `.nodes()` / `.neighbors()` public API; if ego_graph needs the raw DiGraph, document using internal attr)
    - src/token_world/viz/mermaid.py (for escape_label import)
    - tests/test_viz/test_viz_graph.py (Wave 0 stubs — the contract)
    - tests/test_viz/conftest.py (for small_graph fixture)
    - .planning/phases/03-design-validation/03-RESEARCH.md §Mermaid Visualization (full section)
  </read_first>
  <behavior>
    - `extract_subgraph(kg, anchor="alice", depth=2)` → nx.ego_graph on kg's underlying DiGraph, undirected=True, radius=2, centered on "alice".
    - `extract_subgraph(kg, anchors=["alice", "bob"], depth=1)` → union of ego_graphs from each anchor.
    - `to_mermaid(kg, sub)` emits:
      ```
      flowchart LR
          escaped_id["label"]:::type
          ...
          src -- "relation" --> dst
          classDef agent fill:#cfe,stroke:#063,color:#000
          classDef entity fill:#fec,stroke:#630,color:#000
      ```
    - `max_nodes` check: if `len(sub.nodes) > max_nodes`, raise `TooManyNodesError("subgraph has N nodes (> max_nodes M); tighten filter with --depth, --type, --has-property")`.
    - Node label format: `👤 alice<br/>hp=100` for agent, `🏛 alice<br/>subtype=room` for entity with subtype. Property selection: type (as style class, not in label), subtype (if present), 1-2 scalar props not in skip list `{position, bbox}`, truncated per escape_label.
    - Node IDs must also be escaped/sanitized — Mermaid IDs can't contain quotes, pipes, brackets, spaces. Use a deterministic sanitizer (replace unsafe chars with `_`, append short hash if collision).
    - Edge labels: if edge has `relation` property, render as `src -- "escaped_relation" --> dst`; else `src --> dst`.
    - `style=False` (when `--no-style` CLI flag given): skip the emoji, skip classDef, skip `:::agent`/`:::entity` suffix.
    - Filters: before counting for max_nodes, apply `type_filter`, `has_property`, `exclude_property` — but never drop anchors (preserve the user's explicit focus).
  </behavior>
  <action>
    1. Create `src/token_world/viz/graph_viz.py`:
       - Imports: `from __future__ import annotations`, `import hashlib`, `import networkx as nx`, `from token_world.graph import KnowledgeGraph`, `from token_world.viz.mermaid import escape_label`.
       - `class TooManyNodesError(Exception): ...`
       - `_MERMAID_ID_SAFE = set(string.ascii_letters + string.digits + "_")` and a `_sanitize_mermaid_id(raw: str) -> str` that keeps safe chars, replaces others with `_`, and appends a short sha256-based suffix when substitution happened (to prevent collisions between e.g. `alice"` and `alice|`).
       - `extract_subgraph(kg, *, anchor=None, anchors=None, depth=1) -> nx.DiGraph`:
         - Exactly one of `anchor` / `anchors` must be provided (ValueError otherwise).
         - For single anchor: return `nx.ego_graph(kg._graph, anchor, radius=depth, undirected=True).copy()`.
         - For multiple: compose by `nx.compose_all([ego_graph(kg._graph, a, radius=depth, undirected=True) for a in anchors])`.
       - `_pick_display_props(props: dict, limit: int = 2) -> list[tuple[str, str]]`:
         - Priority: `subtype` first, then scalar-valued (str/int/float/bool) props excluding `position`, `bbox`, `node_type`.
         - Returns up to `limit` (k, v_str) pairs.
       - `_render_node_label(node_id: str, props: dict, *, style: bool) -> str`:
         - Uses emoji prefix keyed on node_type (`👤` for agent, `🏛` for entity) when style=True.
         - Builds `"{emoji} {node_id}<br/>{kv1}<br/>{kv2}"` where each segment is individually escaped with `escape_label(..., max_len=60)`.
         - When style=False: plain `escape_label(f"{node_id} {kv1} {kv2}", max_len=60)`.
       - `to_mermaid(kg, sub, *, max_nodes=150, style=True, type_filter=None, has_property=None, exclude_property=None) -> str`:
         - Apply filters to `sub.nodes()` — keep a node if it matches all filters. Record anchors (from `sub.graph.get('anchors', ())` — set in extract_subgraph via `G.graph['anchors'] = (anchor,) or tuple(anchors)`).
         - Raise TooManyNodesError if remaining count > max_nodes, with message including `count`, `max_nodes`, and suggestion.
         - Build lines: `["flowchart LR"]`, one line per kept node (`    safe_id["label"]:::type_class`), one line per kept edge (`    safe_src -- "rel" --> safe_dst` or plain arrow).
         - If `style=True`, append the two `classDef` lines at the end.
         - Return `"\n".join(lines) + "\n"`.

    2. Update `src/token_world/viz/__init__.py` to re-export `extract_subgraph`, `to_mermaid`, `TooManyNodesError`, and keep `escape_label`:
       ```python
       from token_world.viz.mermaid import escape_label
       from token_world.viz.graph_viz import extract_subgraph, to_mermaid, TooManyNodesError
       __all__ = ["escape_label", "extract_subgraph", "to_mermaid", "TooManyNodesError"]
       ```

    3. Extend `tests/test_viz/test_viz_graph.py` (beyond the Wave 0 stubs) with:
       - `test_edge_label_uses_relation_property` — edge with `relation="located_in"` shows `"located_in"` in output.
       - `test_no_style_emits_minimal_output` — `to_mermaid(..., style=False)` has no `classDef` or emoji.
       - `test_multi_anchor_union` — `extract_subgraph(kg, anchors=["alice", "bob"], depth=1)` contains both anchors and their respective neighborhoods.
       - `test_filter_by_type` — `to_mermaid(..., type_filter="agent")` only includes agent nodes (plus anchors).
       - `test_anchor_preserved_through_filter` — even if anchor doesn't match filter, it is preserved.
       - `test_mermaid_id_collision_hash_suffix` — two nodes `x|` and `x"` produce different sanitized IDs in output (verifies hash suffix on sanitize).

    4. The existing `test_injection_safe_node_id` stub should now pass (dangerous chars escaped both in label and ID).
  </action>
  <verify>
    <automated>uv run pytest tests/test_viz/ -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "^class TooManyNodesError" src/token_world/viz/graph_viz.py` passes
    - `grep -q "^def extract_subgraph\|^def to_mermaid" src/token_world/viz/graph_viz.py` shows both
    - `grep -q "ego_graph.*undirected=True" src/token_world/viz/graph_viz.py` passes
    - `grep -q "escape_label" src/token_world/viz/graph_viz.py` passes
    - `uv run pytest tests/test_viz/ -v` — all tests pass (no skips, no failures)
    - `uv run mypy src/token_world/viz/` exits 0
    - Running against fixture small_graph produces output starting with `flowchart LR\n`
  </acceptance_criteria>
  <done>extract_subgraph and to_mermaid work. Injection-safe labels and IDs. 150-node cap enforced. All viz module tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Register `viz-graph` Click subcommand + CLI smoke tests</name>
  <files>src/token_world/cli.py, tests/test_cli/__init__.py, tests/test_cli/test_viz_graph.py</files>
  <read_first>
    - src/token_world/cli.py (locate end of file for appending the new command; match existing style)
    - src/token_world/universe/manager.py (UniverseManager.load signature — returns a path or Universe object?)
    - src/token_world/universe/paths.py (to resolve `<universe_dir>/universe.db`)
    - src/token_world/viz/graph_viz.py (Task 1 output)
    - src/token_world/viz/__init__.py
    - tests/test_viz/test_viz_graph.py (the existing `test_cli_requires_anchor` smoke test)
  </read_first>
  <behavior>
    - `token-world viz-graph SLUG` with no anchor flag → exits non-zero, stderr mentions one of `--node` / `--seed-query` / `--all-agents`.
    - `token-world viz-graph SLUG --node alice --depth 1` → loads `<slug>/universe.db`, constructs KnowledgeGraph, extracts subgraph, emits Mermaid to stdout. Exit 0.
    - `--output PATH` → writes to file, exits 0, stdout contains a confirmation line (e.g. `Wrote N bytes to PATH`).
    - `--max-nodes 2` on a large subgraph → exits non-zero with a message mentioning "tighten" or "max-nodes".
    - `--seed-query node_type=entity` → uses all nodes with that property as anchor set.
    - `--all-agents` → anchors = all nodes where `node_type == "agent"`, depth defaults to 1.
    - CLI validates: if multiple anchor modes supplied, prefer explicit `--node`; print a warning if that happens (or just document precedence).
  </behavior>
  <action>
    1. Edit `src/token_world/cli.py` — append at the bottom:
       ```python
       @cli.command("viz-graph")
       @click.argument("universe")
       @click.option("--node", "anchor_node", default=None, help="Anchor node for ego-graph.")
       @click.option("--depth", type=int, default=1, show_default=True, help="Hops from anchor(s).")
       @click.option("--seed-query", "seed_queries", multiple=True,
                     help="KEY=VALUE; anchor set is nodes where property KEY equals VALUE. Repeatable.")
       @click.option("--all-agents", is_flag=True, default=False, help="Use all agent-typed nodes as anchors.")
       @click.option("--type", "type_filter", type=click.Choice(["agent", "entity"]), default=None)
       @click.option("--has-property", "has_property", default=None)
       @click.option("--exclude-property", "exclude_property", default=None)
       @click.option("--max-nodes", type=int, default=150, show_default=True)
       @click.option("--output", type=click.Path(dir_okay=False, writable=True), default=None)
       @click.option("--no-style", "no_style", is_flag=True, default=False)
       def viz_graph(
           universe: str,
           anchor_node: str | None,
           depth: int,
           seed_queries: tuple[str, ...],
           all_agents: bool,
           type_filter: str | None,
           has_property: str | None,
           exclude_property: str | None,
           max_nodes: int,
           output: str | None,
           no_style: bool,
       ) -> None:
           """Emit a filtered Mermaid flowchart for a universe's knowledge graph.

           An anchor is REQUIRED — provide --node, --seed-query, or --all-agents.
           Whole-graph rendering is not supported (use filters to focus).
           """
           if not (anchor_node or seed_queries or all_agents):
               click.echo(
                   "Error: an anchor is required. Use --node <id>, "
                   "--seed-query KEY=VALUE, or --all-agents.",
                   err=True,
               )
               raise SystemExit(2)

           from token_world.graph import KnowledgeGraph
           from token_world.universe.manager import UniverseManager
           from token_world.viz import extract_subgraph, to_mermaid, TooManyNodesError

           manager = UniverseManager()
           try:
               universe_dir = manager.load(universe)
           except FileNotFoundError as e:
               click.echo(f"Error: {e}", err=True)
               raise SystemExit(1) from e

           # Resolve DB path — pattern from existing list-mechanics command
           db_path = universe_dir / "universe.db"  # confirm against paths.py
           kg = KnowledgeGraph(db_path=db_path)
           kg.load()

           anchors: list[str] = []
           if anchor_node:
               anchors.append(anchor_node)
           for sq in seed_queries:
               if "=" not in sq:
                   click.echo(f"Error: --seed-query must be KEY=VALUE (got {sq!r})", err=True)
                   raise SystemExit(2)
               k, v = sq.split("=", 1)
               anchors.extend(kg.nodes(**{k: v}))  # Phase 1 exposes .nodes(**filters)
           if all_agents:
               anchors.extend(kg.nodes(node_type="agent"))

           anchors = list(dict.fromkeys(anchors))  # dedupe preserving order
           if not anchors:
               click.echo("Error: anchor set is empty (no matching nodes).", err=True)
               raise SystemExit(3)

           sub = extract_subgraph(kg, anchors=anchors, depth=depth)

           try:
               mermaid = to_mermaid(
                   kg, sub,
                   max_nodes=max_nodes,
                   style=not no_style,
                   type_filter=type_filter,
                   has_property=has_property,
                   exclude_property=exclude_property,
               )
           except TooManyNodesError as e:
               click.echo(f"Error: {e}", err=True)
               raise SystemExit(4) from e

           if output:
               from pathlib import Path as _P
               _P(output).write_text(mermaid, encoding="utf-8")
               click.echo(f"Wrote {len(mermaid)} bytes to {output}")
           else:
               click.echo(mermaid)
       ```
       If `kg.nodes(**filters)` is not the Phase 1 API (verify via knowledge_graph.py), adapt to whatever `find_nodes` or equivalent exists. Executor: read `knowledge_graph.py` to find the actual property-filter API before wiring.

    2. Create `tests/test_cli/__init__.py` (empty) and `tests/test_cli/test_viz_graph.py`:
       ```python
       """CLI-level smoke tests for viz-graph."""
       from __future__ import annotations

       from pathlib import Path
       import pytest
       from click.testing import CliRunner

       from token_world.cli import cli


       @pytest.fixture
       def populated_universe(tmp_path, monkeypatch):
           """Create a universe with a small graph, return its slug."""
           from token_world.universe.manager import UniverseManager
           # Redirect XDG to tmp_path so universe is created in-test
           monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
           mgr = UniverseManager()
           path = mgr.create("viz-smoke")
           # Populate universe.db with a handful of nodes
           from token_world.graph import KnowledgeGraph
           kg = KnowledgeGraph(db_path=path / "universe.db")
           kg.add_node("alice", node_type="agent")
           kg.add_node("room_a", node_type="entity", subtype="room")
           kg.add_node("sword", node_type="entity", subtype="weapon")
           kg.add_edge("alice", "room_a", relation="located_in")
           kg.add_edge("sword", "alice", relation="held_by")
           kg.save()
           return "viz-smoke"


       def test_requires_anchor(populated_universe) -> None:
           r = CliRunner().invoke(cli, ["viz-graph", populated_universe])
           assert r.exit_code != 0
           assert "anchor" in r.output.lower() or "--node" in r.output


       def test_node_anchor_emits_flowchart(populated_universe) -> None:
           r = CliRunner().invoke(
               cli, ["viz-graph", populated_universe, "--node", "alice", "--depth", "1"]
           )
           assert r.exit_code == 0, r.output
           assert r.output.lstrip().startswith("flowchart"), r.output[:100]
           assert "alice" in r.output
           assert "room_a" in r.output


       def test_max_nodes_cap(populated_universe) -> None:
           r = CliRunner().invoke(
               cli,
               ["viz-graph", populated_universe, "--node", "alice",
                "--depth", "3", "--max-nodes", "1"],
           )
           assert r.exit_code != 0
           assert "max" in r.output.lower() or "tighten" in r.output.lower()


       def test_output_file(populated_universe, tmp_path) -> None:
           out = tmp_path / "out.mmd"
           r = CliRunner().invoke(
               cli, ["viz-graph", populated_universe,
                     "--node", "alice", "--output", str(out)]
           )
           assert r.exit_code == 0, r.output
           assert out.exists()
           assert out.read_text().lstrip().startswith("flowchart")


       def test_type_filter(populated_universe) -> None:
           r = CliRunner().invoke(
               cli, ["viz-graph", populated_universe,
                     "--node", "alice", "--type", "entity"]
           )
           assert r.exit_code == 0
           # Output has entity nodes and the anchor agent (anchor always preserved)
           assert "room_a" in r.output


       def test_seed_query(populated_universe) -> None:
           r = CliRunner().invoke(
               cli,
               ["viz-graph", populated_universe,
                "--seed-query", "subtype=room"],
           )
           assert r.exit_code == 0
           assert "room_a" in r.output


       def test_all_agents(populated_universe) -> None:
           r = CliRunner().invoke(
               cli, ["viz-graph", populated_universe, "--all-agents"]
           )
           assert r.exit_code == 0
           assert "alice" in r.output
       ```
  </action>
  <verify>
    <automated>uv run pytest tests/test_cli/ tests/test_viz/ -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q '@cli.command("viz-graph")' src/token_world/cli.py` passes
    - `grep -q "\-\-node\|\-\-seed-query\|\-\-all-agents" src/token_world/cli.py` shows all three anchor modes
    - `uv run token-world viz-graph --help` exit 0 and mentions `--node`
    - `uv run pytest tests/test_cli/test_viz_graph.py -v` — all 7 tests pass
    - `uv run mypy src/token_world/cli.py` exits 0
  </acceptance_criteria>
  <done>`token-world viz-graph` works end-to-end against a real universe. All CLI smoke tests green.</done>
</task>

<task type="auto">
  <name>Task 3: Author docs/guides/viz-graph.md user guide + end-to-end mcp-mermaid verification</name>
  <files>docs/guides/viz-graph.md</files>
  <read_first>
    - docs/ (existing guide structure — match tone and length)
    - .planning/phases/03-design-validation/03-RESEARCH.md §Mermaid Graph Visualization
    - src/token_world/cli.py (confirm actual flag names)
  </read_first>
  <action>
    1. Create `docs/guides/viz-graph.md` with sections:
       - `# viz-graph — Filtered Mermaid Diagrams of a Universe`
       - `## Why` — knowledge graphs have thousands of nodes; whole-graph rendering is useless; always filter.
       - `## Quick Examples` — 3–5 runnable commands:
         ```
         token-world viz-graph my-universe --node alice --depth 2
         token-world viz-graph my-universe --all-agents
         token-world viz-graph my-universe --seed-query subtype=room --depth 1
         token-world viz-graph my-universe --node alice --output alice.mmd
         token-world viz-graph my-universe --node alice --depth 1 --no-style
         ```
       - `## Flags` — table of all options with one-line purpose.
       - `## Anchor is mandatory` — document the design decision (D-14) and the exit codes.
       - `## Rendering to PNG` — pipe output to `mcp-mermaid` or paste into any Markdown viewer (GitHub, VS Code).
       - `## When rendering fails` — the 150-node cap message; tightening strategies.
       - `## Node label format` — explain emoji + property selection heuristic.
       - `## Security note` — labels with `" | [ ] \n` are automatically escaped; safe to viz graphs with user-supplied node ids.

    2. Use mcp-mermaid to render a small sample and visually confirm it works. Commit a link to the rendered sample in the doc (no PNG check-in — render on demand per CLAUDE.md).
  </action>
  <verify>
    <automated>test -f docs/guides/viz-graph.md &amp;&amp; grep -qE "^## (Why|Quick Examples|Flags|Anchor is mandatory|Rendering|When rendering fails|Node label format|Security note)" docs/guides/viz-graph.md</automated>
  </verify>
  <acceptance_criteria>
    - `wc -l docs/guides/viz-graph.md` ≥ 40
    - All 8 section headings present
    - At least 3 concrete `token-world viz-graph …` example commands
    - Document mentions `mcp-mermaid` for rendering
    - Document mentions 150-node cap
  </acceptance_criteria>
  <done>User-facing guide complete; anyone reading it can use viz-graph productively without reading the source.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI args → graph queries | `--node`, `--seed-query` values flow into graph node lookups and are emitted in Mermaid labels. |
| Graph state → Mermaid output | Node IDs and property values flow into Mermaid syntax; unsanitized strings can break the parser or cause label injection. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03-02 | Injection | Mermaid label/ID output in `graph_viz.py` | mitigate | Every label emission uses `escape_label()` (replaces `" \n [ ] |`). Node IDs run through `_sanitize_mermaid_id` (keeps alphanumerics + `_`; other chars → `_` + hash suffix). Verified by `test_injection_safe_node_id` and `test_mermaid_id_collision_hash_suffix`. |
| T-03-03 | Injection | CLI arg `--node` passed to graph lookup | mitigate | Arg is used as a dict key / node_id string — does not flow into SQL, does not touch the filesystem except via `UniverseManager.load` which validates slug. No path traversal vector. |
| T-03-09 | DoS | Very deep `--depth` on huge graphs | mitigate | 150-node cap + error message. `ego_graph` with large radius on thousands of nodes bounded by the graph size (internal). |
</threat_model>

<verification>
- `uv run pytest tests/test_viz/ tests/test_cli/ -v` is green
- `uv run ruff check src/ && uv run mypy src/token_world/viz/ src/token_world/cli.py` is green
- `uv run token-world viz-graph --help` shows `--node`, `--seed-query`, `--all-agents`
- End-to-end manual spot-check: render a sample via `mcp-mermaid` to confirm the output is visually sane
</verification>

<success_criteria>
1. `token-world viz-graph my-universe --node alice --depth 2` prints a valid `flowchart LR ...` block to stdout.
2. Running without any anchor flag exits non-zero with a message pointing at `--node`/`--seed-query`/`--all-agents`.
3. Exceeding `--max-nodes` exits non-zero with a clear "tighten the filter" message.
4. Node IDs or labels containing `"`, `|`, `[`, `]`, or newlines are escaped; Mermaid parses the output without error.
5. A `--no-style` run omits classDefs and emoji.
6. Writing to `--output FILE` creates the file and exits 0.
7. `docs/guides/viz-graph.md` is ≥40 lines with all required sections.
</success_criteria>

<output>
After completion, create `.planning/phases/03-design-validation/03-04-SUMMARY.md` listing viz module, CLI command registration, docs guide, and the security mitigations (label + ID escaping).
</output>
