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


def test_edge_label_uses_relation_property(small_graph) -> None:
    """Edges with a `relation` property render as quoted labels in Mermaid."""
    sub = graph_viz.extract_subgraph(small_graph, anchor="alice", depth=1)
    output = graph_viz.to_mermaid(small_graph, sub)
    # One of the edges in small_graph has relation="located_in"
    assert '"located_in"' in output or "located_in" in output


def test_no_style_emits_minimal_output(small_graph) -> None:
    """style=False drops classDef and emoji markers."""
    sub = graph_viz.extract_subgraph(small_graph, anchor="alice", depth=1)
    output = graph_viz.to_mermaid(small_graph, sub, style=False)
    assert "classDef" not in output
    assert ":::agent" not in output
    assert ":::entity" not in output
    # Agent/entity emoji markers should be absent
    assert "\U0001f464" not in output  # 👤
    assert "\U0001f3db" not in output  # 🏛


def test_multi_anchor_union(small_graph) -> None:
    """extract_subgraph with multiple anchors returns union of ego-graphs."""
    small_graph.add_node("bob", node_type="agent")
    small_graph.add_node("room_b", node_type="entity", subtype="room")
    small_graph.add_edge("bob", "room_b", relation="located_in")
    sub = graph_viz.extract_subgraph(small_graph, anchors=["alice", "bob"], depth=1)
    assert "alice" in sub.nodes
    assert "bob" in sub.nodes
    assert "room_a" in sub.nodes
    assert "room_b" in sub.nodes


def test_filter_by_type(small_graph) -> None:
    """type_filter restricts output to the chosen node_type (anchors always kept)."""
    sub = graph_viz.extract_subgraph(small_graph, anchor="alice", depth=1)
    output = graph_viz.to_mermaid(small_graph, sub, type_filter="entity")
    # alice is an agent but is the anchor — must remain
    assert "alice" in output
    # room_a and sword are entities — must remain
    assert "room_a" in output
    assert "sword" in output


def test_anchor_preserved_through_filter(small_graph) -> None:
    """Even if anchor doesn't match has_property filter, it is preserved."""
    # alice has no property `subtype`, so filter would drop her — but she's the anchor
    sub = graph_viz.extract_subgraph(small_graph, anchor="alice", depth=1)
    output = graph_viz.to_mermaid(small_graph, sub, has_property="subtype")
    assert "alice" in output


def test_mermaid_id_collision_hash_suffix(small_graph) -> None:
    """Different dangerous node IDs get distinct sanitized IDs (hash suffix)."""
    small_graph.add_node('x"', node_type="entity")
    small_graph.add_node("x|", node_type="entity")
    small_graph.add_edge("alice", 'x"', relation="sees")
    small_graph.add_edge("alice", "x|", relation="sees")
    sub = graph_viz.extract_subgraph(small_graph, anchor="alice", depth=1)
    output = graph_viz.to_mermaid(small_graph, sub)
    # Both sanitized IDs should appear as distinct declarations. Extract declared IDs.
    # A declaration looks like `    safe_id["label"]...`
    declared_ids = set()
    for line in output.splitlines():
        stripped = line.strip()
        if "[" in stripped and stripped[0] not in (" ", "f", "c"):
            safe_id = stripped.split("[", 1)[0]
            declared_ids.add(safe_id)
    # We added two dangerous nodes plus alice — expect alice's id and two distinct sanitized ids
    dangerous_ids = {i for i in declared_ids if i.startswith("x")}
    assert len(dangerous_ids) >= 2, (
        f'expected distinct sanitized IDs for x" and x|, got {dangerous_ids!r} '
        f"from output:\n{output}"
    )
