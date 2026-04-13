"""Mermaid flowchart emission for knowledge graph subgraphs.

The whole-graph view is intentionally unsupported — callers must provide an anchor
(single node or union of anchors) and a depth. A hard node cap (default 150)
prevents accidentally rendering massive subgraphs.

All node IDs and labels pass through escaping:
- Labels: :func:`token_world.viz.mermaid.escape_label` (HTML entities + truncation).
- IDs: :func:`_sanitize_mermaid_id` (alphanum + ``_`` only, hash suffix on collision).
"""

from __future__ import annotations

import hashlib
import string
from typing import Any

import networkx as nx

from token_world.graph import KnowledgeGraph
from token_world.viz.mermaid import escape_label

__all__ = ["extract_subgraph", "to_mermaid", "TooManyNodesError"]


class TooManyNodesError(Exception):
    """Raised when the filtered subgraph exceeds ``max_nodes``."""


# ---------------------------------------------------------------------------
# ID sanitisation
# ---------------------------------------------------------------------------

_MERMAID_ID_SAFE = frozenset(string.ascii_letters + string.digits + "_")


def _sanitize_mermaid_id(raw: str) -> str:
    """Sanitise a raw node ID so it is safe to use as a Mermaid node ID.

    Mermaid node IDs must not contain quotes, pipes, brackets, whitespace, etc.
    Unsafe characters are replaced with ``_``. When substitution happened, a
    short hash of the original string is appended so that two distinct dangerous
    IDs (``x"`` vs ``x|``) do not collide onto the same sanitised ID (``x_``).
    """
    safe_chars = [c if c in _MERMAID_ID_SAFE else "_" for c in raw]
    safe = "".join(safe_chars)
    if safe != raw:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:6]
        safe = f"{safe}_{digest}"
    if not safe or safe[0].isdigit():
        safe = f"n_{safe}"
    return safe


# ---------------------------------------------------------------------------
# Subgraph extraction
# ---------------------------------------------------------------------------


def extract_subgraph(
    kg: KnowledgeGraph,
    *,
    anchor: str | None = None,
    anchors: list[str] | None = None,
    depth: int = 1,
) -> nx.DiGraph:
    """Extract an ego-graph (or union of ego-graphs) around one or more anchors.

    Exactly one of ``anchor`` / ``anchors`` must be provided. The resulting
    graph uses :func:`networkx.ego_graph` with ``undirected=True`` so edges
    in either direction contribute to the neighbourhood.

    Delegates to :meth:`KnowledgeGraph.ego_subgraph` (public API) rather than
    reaching into the private ``_graph`` attribute (review finding M-02).
    """
    if anchor is None and anchors is None:
        raise ValueError("extract_subgraph requires either `anchor` or `anchors`.")
    if anchor is not None and anchors is not None:
        raise ValueError("Provide only one of `anchor` or `anchors`, not both.")

    if anchor is not None:
        return kg.ego_subgraph(anchor, depth=depth, undirected=True)

    assert anchors is not None  # narrow for type-checker
    if not anchors:
        raise ValueError("`anchors` must be a non-empty list.")
    return kg.ego_subgraph(anchors, depth=depth, undirected=True)


# ---------------------------------------------------------------------------
# Label rendering
# ---------------------------------------------------------------------------

_LABEL_SKIP_PROPS: frozenset[str] = frozenset({"position", "bbox", "type", "node_type"})
_SCALAR_TYPES = (str, int, float, bool)
_EMOJI_AGENT = "\U0001f464"  # 👤
_EMOJI_ENTITY = "\U0001f3db"  # 🏛


def _pick_display_props(props: dict[str, Any], *, limit: int = 2) -> list[tuple[str, str]]:
    """Pick up to ``limit`` (key, value_str) pairs for the node label.

    ``subtype`` (if present) is prioritised. Remaining slots come from
    scalar-typed properties, sorted by key for determinism.
    """
    picks: list[tuple[str, str]] = []
    if "subtype" in props and isinstance(props["subtype"], _SCALAR_TYPES):
        picks.append(("subtype", str(props["subtype"])))

    for key in sorted(props):
        if len(picks) >= limit:
            break
        if key in _LABEL_SKIP_PROPS or key == "subtype":
            continue
        value = props[key]
        if isinstance(value, bool | str | int | float):
            picks.append((key, str(value)))
    return picks[:limit]


def _node_type(props: dict[str, Any]) -> str | None:
    """Return the node_type ('agent' | 'entity') if known."""
    # KnowledgeGraph stores node type under key "type" (see add_node).
    t = props.get("type") or props.get("node_type")
    if t == "agent" or t == "entity":
        return str(t)
    return None


def render_node_label(node_id: str, props: dict[str, Any], *, style: bool) -> str:
    """Render the label text for a node (already escape_label'd)."""
    kvs = _pick_display_props(props)
    ntype = _node_type(props)

    if style:
        emoji = _EMOJI_AGENT if ntype == "agent" else _EMOJI_ENTITY if ntype == "entity" else ""
        head = f"{emoji} {node_id}".strip()
        segments = [escape_label(head)]
        for k, v in kvs:
            segments.append(escape_label(f"{k}={v}"))
        return "<br/>".join(segments)

    # Minimal: single-line, no emoji, no classDef
    flat = node_id
    for k, v in kvs:
        flat += f" {k}={v}"
    return escape_label(flat)


def render_edge_label(edge_props: dict[str, Any]) -> str | None:
    """Return the escaped relation label for an edge, or ``None`` if no label."""
    rel = edge_props.get("relation")
    if rel is None:
        return None
    escaped: str = escape_label(str(rel))
    return escaped


# ---------------------------------------------------------------------------
# Mermaid emission
# ---------------------------------------------------------------------------


def _keep_node(
    node_id: str,
    props: dict[str, Any],
    *,
    type_filter: str | None,
    has_property: str | None,
    exclude_property: str | None,
) -> bool:
    if type_filter is not None and _node_type(props) != type_filter:
        return False
    if has_property is not None and has_property not in props:
        return False
    return not (exclude_property is not None and exclude_property in props)


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
    """Emit a ``flowchart LR`` Mermaid document from a subgraph.

    Raises :class:`TooManyNodesError` if the filtered node set exceeds
    ``max_nodes`` — callers should tighten their filter and retry.
    """
    anchors: set[str] = set(sub.graph.get("anchors", ()))

    kept: list[str] = []
    for node_id in sub.nodes:
        props = dict(sub.nodes[node_id])
        if node_id in anchors or _keep_node(
            node_id,
            props,
            type_filter=type_filter,
            has_property=has_property,
            exclude_property=exclude_property,
        ):
            kept.append(node_id)

    if len(kept) > max_nodes:
        raise TooManyNodesError(
            f"subgraph has {len(kept)} nodes (> max_nodes {max_nodes}); "
            f"tighten filter with --depth, --type, --has-property, "
            f"--exclude-property, or --max-nodes"
        )

    kept_set = set(kept)
    # Deterministic ID mapping (first-seen order)
    safe_ids: dict[str, str] = {}
    used: dict[str, int] = {}
    for node_id in kept:
        base_safe = _sanitize_mermaid_id(node_id)
        # Guarantee uniqueness even across collisions not caught by hash (rare)
        candidate = base_safe
        suffix = used.get(base_safe, 0)
        while candidate in safe_ids.values():
            suffix += 1
            candidate = f"{base_safe}_{suffix}"
        used[base_safe] = suffix
        safe_ids[node_id] = candidate

    lines: list[str] = ["flowchart LR"]

    # Nodes
    for node_id in kept:
        props = dict(sub.nodes[node_id])
        label = render_node_label(node_id, props, style=style)
        safe = safe_ids[node_id]
        ntype = _node_type(props)
        if style and ntype in ("agent", "entity"):
            lines.append(f'    {safe}["{label}"]:::{ntype}')
        else:
            lines.append(f'    {safe}["{label}"]')

    # Edges
    for src, dst in sub.edges:
        if src not in kept_set or dst not in kept_set:
            continue
        edge_props = dict(sub.edges[src, dst])
        rel = render_edge_label(edge_props)
        s_safe = safe_ids[src]
        d_safe = safe_ids[dst]
        if rel is not None:
            lines.append(f'    {s_safe} -- "{rel}" --> {d_safe}')
        else:
            lines.append(f"    {s_safe} --> {d_safe}")

    if style:
        lines.append("    classDef agent fill:#cfe,stroke:#063,color:#000")
        lines.append("    classDef entity fill:#fec,stroke:#630,color:#000")

    return "\n".join(lines) + "\n"
