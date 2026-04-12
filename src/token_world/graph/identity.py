"""Node identity deconfliction for the knowledge graph."""

from __future__ import annotations

import hashlib

import networkx as nx


def claim_id(graph: nx.DiGraph, name: str) -> str:
    """Propose a human-readable node ID, deconflicting if already taken.

    If ``name`` is not in the graph, returns it as-is. Otherwise, appends
    progressively longer hash suffixes until a unique ID is found.

    Args:
        graph: The NetworkX DiGraph to check for collisions.
        name: The proposed human-readable ID.

    Returns:
        A unique node ID string.

    Raises:
        ValueError: If deconfliction fails after 4 attempts.
    """
    if name not in graph:
        return name
    for length in (2, 4, 6, 8):
        h = hashlib.sha256(f"{name}_{graph.number_of_nodes()}".encode()).hexdigest()[:length]
        candidate = f"{name}_{h}"
        if candidate not in graph:
            return candidate
    raise ValueError(f"Cannot deconflict ID after 4 attempts: {name}")
