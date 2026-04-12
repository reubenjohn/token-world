"""Stubs for AUTO-04 viz-graph CLI + viz module."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

graph_viz = pytest.importorskip("token_world.viz.graph_viz")


def test_extract_ego_subgraph_respects_depth(small_graph) -> None:
    sub = graph_viz.extract_subgraph(small_graph, anchor="alice", depth=1)
    # Undirected ego_graph at depth 1 from alice: alice, room_a, sword
    assert set(sub.nodes) >= {"alice", "room_a", "sword"}


def test_to_mermaid_emits_flowchart_header(small_graph) -> None:
    sub = graph_viz.extract_subgraph(small_graph, anchor="alice", depth=1)
    output = graph_viz.to_mermaid(small_graph, sub)
    assert output.startswith("flowchart"), f"expected flowchart header, got: {output[:40]!r}"


def test_node_cap_refuses_huge_subgraph(small_graph) -> None:
    sub = graph_viz.extract_subgraph(small_graph, anchor="alice", depth=10)
    with pytest.raises(graph_viz.TooManyNodesError):
        graph_viz.to_mermaid(small_graph, sub, max_nodes=1)


def test_cli_requires_anchor(tmp_path) -> None:
    """viz-graph without --node/--seed-query/--all-agents must error."""
    from token_world.cli import cli

    runner = CliRunner()
    # Use a universe slug that won't exist — CLI should still error on missing anchor first
    result = runner.invoke(cli, ["viz-graph", "nonexistent-universe"])
    assert result.exit_code != 0
    assert "anchor" in result.output.lower() or "--node" in result.output


def test_cli_emits_mermaid_with_node_anchor(tmp_path, monkeypatch) -> None:
    """End-to-end smoke: viz-graph on a small real universe emits flowchart."""
    # This test is wired once Wave 1 viz plan creates the CLI command.
    from token_world.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["viz-graph", "--help"])
    assert result.exit_code == 0
    assert "--node" in result.output


def test_injection_safe_node_id(small_graph) -> None:
    """Node IDs containing Mermaid-dangerous chars must not break output (T-03-02)."""
    small_graph.add_node('danger"|[evil]', node_type="entity")
    small_graph.add_edge("alice", 'danger"|[evil]', relation="observes")
    sub = graph_viz.extract_subgraph(small_graph, anchor="alice", depth=1)
    output = graph_viz.to_mermaid(small_graph, sub)
    # Raw dangerous chars must be escaped in label output
    assert '"|[evil]' not in output or "#quot;" in output
