"""Tests for the graph canvas panel (Plan 11-03)."""

from __future__ import annotations

from pathlib import Path

from token_world.dashboard.panels.graph_canvas import (
    MAX_NODES,
    build_mermaid,
    load_graph_snapshot,
)


def test_load_graph_snapshot_no_db(fake_universe: Path) -> None:
    """Missing universe.db degrades cleanly."""
    snap = load_graph_snapshot(fake_universe)
    assert snap["loaded"] is False
    assert snap["nodes"] == []
    assert snap["edges"] == []
    assert "universe.db" in (snap["error"] or "")


def test_load_graph_snapshot_populated(fake_universe_with_graph: Path) -> None:
    """A populated universe returns nodes + edges with type/subtype."""
    snap = load_graph_snapshot(fake_universe_with_graph)
    assert snap["loaded"] is True
    assert snap["node_count"] == 4
    assert snap["edge_count"] == 3
    ids = {n["id"] for n in snap["nodes"]}
    assert ids == {"alice", "bob", "chest", "room"}
    chest_node = next(n for n in snap["nodes"] if n["id"] == "chest")
    assert chest_node["subtype"] == "container"
    assert chest_node["label_group"] == "container"
    alice_node = next(n for n in snap["nodes"] if n["id"] == "alice")
    assert alice_node["label_group"] == "agent"


def test_build_mermaid_contains_nodes_and_edges(fake_universe_with_graph: Path) -> None:
    """Generated Mermaid source is a valid flowchart with node declarations."""
    snap = load_graph_snapshot(fake_universe_with_graph)
    src = build_mermaid(snap)
    assert src.startswith("flowchart LR")
    assert "alice" in src
    assert "chest" in src
    # Edge line syntax: either `src --> dst` or `src -- label --> dst`.
    assert "-->" in src
    # Class definitions included.
    assert "classDef agent" in src


def test_build_mermaid_empty_graph(fake_universe: Path) -> None:
    """Empty graph renders a placeholder flowchart instead of crashing."""
    snap = load_graph_snapshot(fake_universe)
    src = build_mermaid(snap)
    assert "flowchart LR" in src
    assert "empty" in src


def test_max_nodes_constant_sane() -> None:
    """MAX_NODES is a reasonable rendering cap."""
    assert 20 <= MAX_NODES <= 500
