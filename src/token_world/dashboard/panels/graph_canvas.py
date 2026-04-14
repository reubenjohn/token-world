"""Graph canvas panel (Plan 11-03).

Renders the universe's knowledge graph as a Mermaid flowchart (we reuse
``ui.mermaid`` so we don't add a Cytoscape CDN dependency). Clicking a
node ID below the chart opens a drawer showing its full property bundle.

Implementation notes:

- NiceGUI's Mermaid element has some limitations around click handlers in
  server-side rendering. Rather than wiring Mermaid ``click`` callbacks
  (which require JS injection), we render the graph + a compact clickable
  node list — each list item is a NiceGUI button that drives the property
  drawer.
- Large graphs degrade: if the node count exceeds ``MAX_NODES`` we render
  only the first N by id-sort and surface the remainder count.
- Uses :meth:`KnowledgeGraph.ego_subgraph` for subgraph extraction when an
  anchor is supplied, else lists everything.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from token_world.graph import KnowledgeGraph
from token_world.viz.mermaid import escape_label

MAX_NODES = 60


def _color_for_node(props: dict[str, Any]) -> str:
    """Return a Mermaid ``classDef`` name for a node's type / subtype."""
    ntype = props.get("type", "unknown")
    subtype = props.get("subtype")
    if ntype == "agent":
        return "agent"
    if subtype == "container":
        return "container"
    if subtype == "location" or subtype == "room":
        return "location"
    if subtype in {"weapon", "tool", "item"}:
        return "item"
    return "entity"


def load_graph_snapshot(universe_dir: Path) -> dict[str, Any]:
    """Return a JSON-serializable snapshot of the knowledge graph.

    Shape::

        {
          "loaded": bool,
          "error": str | None,
          "nodes": [{"id", "type", "subtype", "properties"} ...],
          "edges": [{"src", "dst", "relation", "properties"} ...],
          "node_count": int,
          "edge_count": int,
          "truncated": bool,  # True if node_count > MAX_NODES
        }

    Swallows load errors and returns an empty snapshot with ``loaded=False``.
    """
    db_path = universe_dir / "universe.db"
    if not db_path.is_file():
        return {
            "loaded": False,
            "error": "universe.db not found",
            "nodes": [],
            "edges": [],
            "node_count": 0,
            "edge_count": 0,
            "truncated": False,
        }
    kg = KnowledgeGraph(db_path=db_path)
    try:
        kg.load()
    except (ValueError, OSError) as exc:
        return {
            "loaded": False,
            "error": f"{type(exc).__name__}: {exc}",
            "nodes": [],
            "edges": [],
            "node_count": 0,
            "edge_count": 0,
            "truncated": False,
        }

    all_nodes = sorted(kg.nodes())
    node_count = len(all_nodes)
    truncated = node_count > MAX_NODES
    node_ids = all_nodes[:MAX_NODES] if truncated else all_nodes

    nodes: list[dict[str, Any]] = []
    for nid in node_ids:
        props = kg.query(nid)
        nodes.append(
            {
                "id": nid,
                "type": props.get("type", "unknown"),
                "subtype": props.get("subtype"),
                "label_group": _color_for_node(props),
                "properties": props,
            }
        )

    # Collect edges among the rendered node set only — limiting to the
    # visible ids prevents dangling arrows on a truncated graph.
    visible = set(node_ids)
    edges: list[dict[str, Any]] = []
    # Private-graph access for edge enumeration is limited to read-only
    # inspection — mirrors :mod:`token_world.inspect.universe`.
    raw_graph = kg._graph  # noqa: SLF001 — read-only graph traversal.
    edge_count = int(raw_graph.number_of_edges())
    for src, dst in raw_graph.edges():
        if src in visible and dst in visible:
            edata = dict(raw_graph.edges[src, dst])
            edges.append(
                {
                    "src": src,
                    "dst": dst,
                    "relation": edata.get("relation", ""),
                    "properties": edata,
                }
            )

    return {
        "loaded": True,
        "error": None,
        "nodes": nodes,
        "edges": edges,
        "node_count": node_count,
        "edge_count": edge_count,
        "truncated": truncated,
    }


def build_mermaid(snapshot: dict[str, Any]) -> str:
    """Render a graph snapshot as a Mermaid ``flowchart`` source string."""
    if not snapshot.get("nodes"):
        return 'flowchart LR\n    empty["(empty graph)"]'

    lines: list[str] = ["flowchart LR"]

    # Node declarations with class tags.
    for node in snapshot["nodes"]:
        safe_id = _safe_mermaid_id(node["id"])
        label_parts = [node["id"]]
        if node.get("subtype"):
            label_parts.append(f"({node['subtype']})")
        elif node.get("type"):
            label_parts.append(f"[{node['type']}]")
        label = escape_label(" ".join(label_parts), max_len=40)
        lines.append(f'    {safe_id}["{label}"]:::{node["label_group"]}')

    # Edges.
    for edge in snapshot["edges"]:
        src = _safe_mermaid_id(edge["src"])
        dst = _safe_mermaid_id(edge["dst"])
        relation = escape_label(edge.get("relation") or "", max_len=20)
        if relation:
            lines.append(f"    {src} -- {relation} --> {dst}")
        else:
            lines.append(f"    {src} --> {dst}")

    # Class definitions (colors).
    lines.append("    classDef agent fill:#1e3a8a,stroke:#60a5fa,color:#f1f5f9")
    lines.append("    classDef entity fill:#374151,stroke:#9ca3af,color:#f1f5f9")
    lines.append("    classDef container fill:#78350f,stroke:#fbbf24,color:#fef3c7")
    lines.append("    classDef location fill:#064e3b,stroke:#34d399,color:#d1fae5")
    lines.append("    classDef item fill:#581c87,stroke:#c084fc,color:#f5d0fe")
    return "\n".join(lines)


def _safe_mermaid_id(raw: str) -> str:
    """Mermaid-safe identifier (alpha/num/underscore)."""
    import string

    safe = "".join(c if c in (string.ascii_letters + string.digits + "_") else "_" for c in raw)
    if not safe or safe[0].isdigit():
        safe = f"n_{safe}"
    return safe


def mount_graph_panel(universe_dir: Path, slug: str) -> Any:  # noqa: ARG001 — slug for future label.
    """Mount the graph canvas + clickable node list + drawer."""
    from nicegui import ui

    container = ui.column().classes("w-full gap-2")
    selected: dict[str, Any] = {"node_id": None, "properties": None}

    def _rebuild_drawer(drawer_column: Any) -> None:
        drawer_column.clear()
        with drawer_column:
            nid = selected.get("node_id")
            if nid is None:
                ui.label("Click a node to inspect its properties.").classes(
                    "text-xs text-slate-400"
                )
                return
            ui.label(f"Node: {nid}").classes("text-base font-semibold text-slate-100")
            props = selected.get("properties") or {}
            if not props:
                ui.label("(no properties)").classes("text-xs text-slate-400")
                return
            import json

            pretty = json.dumps(props, indent=2, sort_keys=True, default=str)
            ui.code(pretty, language="json").classes("w-full text-xs max-h-[380px] overflow-auto")

    with container:
        status_label = ui.label("Loading graph…").classes("text-xs text-slate-400")
        canvas_row = ui.row().classes("w-full gap-4 items-start")
        with canvas_row:
            chart_col = ui.column().classes("flex-1 min-w-[320px] max-w-[640px]")
            drawer_col = ui.column().classes("flex-1 min-w-[280px] bg-slate-900 p-3 rounded-md")

    def _on_node_click(nid: str, properties: dict[str, Any]) -> None:
        selected["node_id"] = nid
        selected["properties"] = properties
        _rebuild_drawer(drawer_col)

    def _rebuild() -> None:
        snapshot = load_graph_snapshot(universe_dir)
        if not snapshot["loaded"]:
            status_label.text = f"Graph unavailable: {snapshot['error']}"
        elif snapshot["truncated"]:
            status_label.text = (
                f"Graph: {snapshot['node_count']} nodes, "
                f"{snapshot['edge_count']} edges "
                f"(showing first {MAX_NODES}, {snapshot['node_count'] - MAX_NODES} hidden)"
            )
        else:
            status_label.text = (
                f"Graph: {snapshot['node_count']} nodes, {snapshot['edge_count']} edges"
            )

        chart_col.clear()
        mermaid_src = build_mermaid(snapshot)
        with chart_col:
            ui.mermaid(mermaid_src).classes("w-full")
            ui.separator()
            ui.label("Click a node:").classes("text-xs text-slate-400")
            with ui.row().classes("flex-wrap gap-1"):
                for node in snapshot["nodes"]:
                    nid_outer = node["id"]
                    props_outer = node["properties"]
                    ui.button(
                        nid_outer,
                        on_click=lambda _e, nid=nid_outer, props=props_outer: _on_node_click(
                            nid, props
                        ),
                    ).classes("text-xs").props("size=sm dense")

        _rebuild_drawer(drawer_col)

    _rebuild()
    ui.timer(5.0, _rebuild)  # Graph changes slowly vs ticks; poll every 5s.
    return container
