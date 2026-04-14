"""Tests for the graph canvas panel (Plan 11-03)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from token_world.dashboard.panels.graph_canvas import (
    MAX_NODES,
    build_mermaid,
    compute_graph_signature,
    load_graph_snapshot,
    synthesise_property_edges,
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


# ---------------------------------------------------------------------------
# §A3: label escape no longer leaks HTML-entity brackets.
# ---------------------------------------------------------------------------


def test_build_mermaid_labels_have_no_entity_bracket_leakage(
    fake_universe_with_graph: Path,
) -> None:
    """§A3: labels must not render as ``alice &#91;agent&#93;``.

    Regression for the bug where ``escape_label`` entity-escaped ``[``/``]``
    that we ourselves wrapped around the type annotation, leaving the
    entities visible in the rendered chart. The fix is to switch to a
    colon-delimited label form (``alice : agent``) so brackets never enter
    the label in the first place.
    """
    snap = load_graph_snapshot(fake_universe_with_graph)
    src = build_mermaid(snap)
    assert "&#91;" not in src, f"HTML-entity [ leaked into labels: {src!r}"
    assert "&#93;" not in src, f"HTML-entity ] leaked into labels: {src!r}"
    # Chest has a subtype -> ``chest : container`` form.
    assert "chest : container" in src


def test_build_mermaid_colon_label_form_for_agent_type() -> None:
    """A node whose only classification is ``type=agent`` still gets ``: agent``."""
    snap = {
        "nodes": [
            {
                "id": "mira",
                "type": "agent",
                "subtype": None,
                "label_group": "agent",
                "properties": {"type": "agent"},
            }
        ],
        "edges": [],
        "node_count": 1,
        "edge_count": 0,
        "truncated": False,
        "loaded": True,
        "error": None,
        "db_mtime": 0.0,
    }
    src = build_mermaid(snap)
    assert "mira : agent" in src
    assert "&#91;" not in src
    assert "&#93;" not in src


# ---------------------------------------------------------------------------
# §A4: property-valued references become dashed pseudo-edges.
# ---------------------------------------------------------------------------


def _snapshot_for_synthesis(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return {
        "nodes": nodes,
        "edges": edges or [],
        "node_count": len(nodes),
        "edge_count": len(edges or []),
        "truncated": False,
        "loaded": True,
        "error": None,
        "db_mtime": 0.0,
    }


def test_synthesise_property_edges_resolves_located_in_to_known_node() -> None:
    """§A4: ``mira.located_in = "cottage"`` -> dashed pseudo-edge."""
    snap = _snapshot_for_synthesis(
        [
            {
                "id": "mira",
                "type": "agent",
                "subtype": None,
                "label_group": "agent",
                "properties": {
                    "type": "agent",
                    "located_in": "cottage",
                },
            },
            {
                "id": "cottage",
                "type": "entity",
                "subtype": "location",
                "label_group": "location",
                "properties": {"type": "entity", "subtype": "location"},
            },
        ]
    )
    pseudo = synthesise_property_edges(snap)
    assert len(pseudo) == 1
    assert pseudo[0]["src"] == "mira"
    assert pseudo[0]["dst"] == "cottage"
    assert pseudo[0]["relation"] == "located_in"
    assert pseudo[0]["pseudo"] is True


def test_synthesise_property_edges_skips_unknown_target() -> None:
    """§A4: a value that isn't an existing node id must NOT produce an edge."""
    snap = _snapshot_for_synthesis(
        [
            {
                "id": "mira",
                "type": "agent",
                "subtype": None,
                "label_group": "agent",
                "properties": {"type": "agent", "located_in": "nowhere"},
            }
        ]
    )
    pseudo = synthesise_property_edges(snap)
    assert pseudo == [], f"expected no pseudo-edges, got {pseudo!r}"


def test_synthesise_property_edges_does_not_duplicate_real_edge() -> None:
    """If a real edge already goes mira -> cottage, no pseudo-edge is emitted."""
    snap = _snapshot_for_synthesis(
        nodes=[
            {
                "id": "mira",
                "type": "agent",
                "subtype": None,
                "label_group": "agent",
                "properties": {"type": "agent", "located_in": "cottage"},
            },
            {
                "id": "cottage",
                "type": "entity",
                "subtype": "location",
                "label_group": "location",
                "properties": {"type": "entity", "subtype": "location"},
            },
        ],
        edges=[{"src": "mira", "dst": "cottage", "relation": "located_in"}],
    )
    pseudo = synthesise_property_edges(snap)
    assert pseudo == []


def test_synthesise_property_edges_skips_blocked_scalars() -> None:
    """Built-in property names (``type``, ``name``, ``state``...) never edge-ify."""
    snap = _snapshot_for_synthesis(
        [
            {
                "id": "agent",
                "type": "entity",
                "subtype": None,
                "label_group": "entity",
                "properties": {"type": "entity"},
            },
            {
                "id": "mira",
                "type": "agent",
                "subtype": None,
                "label_group": "agent",
                # `type == "agent"` must NOT produce mira -.type.-> agent.
                "properties": {"type": "agent", "name": "mira"},
            },
        ]
    )
    pseudo = synthesise_property_edges(snap)
    assert pseudo == [], f"blocklist failed, got {pseudo!r}"


def test_synthesise_property_edges_ignores_non_string_values() -> None:
    """Only string-valued properties that name a node can pseudo-edge."""
    snap = _snapshot_for_synthesis(
        [
            {
                "id": "mira",
                "type": "agent",
                "subtype": None,
                "label_group": "agent",
                "properties": {"type": "agent", "hp": 100, "tags": ["cottage"]},
            },
            {
                "id": "cottage",
                "type": "entity",
                "subtype": "location",
                "label_group": "location",
                "properties": {"type": "entity"},
            },
        ]
    )
    pseudo = synthesise_property_edges(snap)
    assert pseudo == []


def test_build_mermaid_emits_dashed_pseudo_edge_for_located_in() -> None:
    """End-to-end: the dashed arrow syntax appears in the Mermaid output."""
    snap = _snapshot_for_synthesis(
        [
            {
                "id": "mira",
                "type": "agent",
                "subtype": None,
                "label_group": "agent",
                "properties": {"type": "agent", "located_in": "cottage"},
            },
            {
                "id": "cottage",
                "type": "entity",
                "subtype": "location",
                "label_group": "location",
                "properties": {"type": "entity", "subtype": "location"},
            },
        ]
    )
    src = build_mermaid(snap)
    # Mermaid dashed-edge-with-label syntax:  ``A -.label.-> B``
    assert "mira -.located_in.-> cottage" in src, src
    # Real edges still use the solid arrow form.
    assert "mira --> cottage" not in src


def test_build_mermaid_skips_pseudo_for_unknown_target() -> None:
    """§A4 negative: ``mira.located_in="nowhere"`` produces NO dashed arrow."""
    snap = _snapshot_for_synthesis(
        [
            {
                "id": "mira",
                "type": "agent",
                "subtype": None,
                "label_group": "agent",
                "properties": {"type": "agent", "located_in": "nowhere"},
            }
        ]
    )
    src = build_mermaid(snap)
    assert "-.->" not in src, src
    assert "-.located_in.->" not in src, src


def test_synthesise_does_not_mutate_snapshot() -> None:
    """Guarantee: the graph / snapshot must never be mutated by synthesis."""
    snap = _snapshot_for_synthesis(
        [
            {
                "id": "mira",
                "type": "agent",
                "subtype": None,
                "label_group": "agent",
                "properties": {"type": "agent", "located_in": "cottage"},
            },
            {
                "id": "cottage",
                "type": "entity",
                "subtype": "location",
                "label_group": "location",
                "properties": {"type": "entity"},
            },
        ]
    )
    edges_before = list(snap["edges"])
    node_props_before = {n["id"]: dict(n["properties"]) for n in snap["nodes"]}
    synthesise_property_edges(snap)
    assert snap["edges"] == edges_before
    for node in snap["nodes"]:
        assert node["properties"] == node_props_before[node["id"]]


# ---------------------------------------------------------------------------
# §A7: chart rebuild is signature-gated + drawer never rebuilds on poll.
# ---------------------------------------------------------------------------


def test_compute_graph_signature_stable_for_unchanged_snapshot() -> None:
    """Two equal snapshots compute the same signature tuple."""
    snap_a = {
        "node_count": 5,
        "edge_count": 3,
        "db_mtime": 123.456,
    }
    snap_b = dict(snap_a)
    assert compute_graph_signature(snap_a) == compute_graph_signature(snap_b)


def test_compute_graph_signature_changes_on_node_count_bump() -> None:
    snap_a = {"node_count": 5, "edge_count": 3, "db_mtime": 123.0}
    snap_b = {"node_count": 6, "edge_count": 3, "db_mtime": 123.0}
    assert compute_graph_signature(snap_a) != compute_graph_signature(snap_b)


def test_compute_graph_signature_changes_on_mtime_bump() -> None:
    snap_a = {"node_count": 5, "edge_count": 3, "db_mtime": 123.0}
    snap_b = {"node_count": 5, "edge_count": 3, "db_mtime": 124.0}
    assert compute_graph_signature(snap_a) != compute_graph_signature(snap_b)


def test_mount_graph_panel_poll_skips_rebuild_when_signature_unchanged(
    fake_universe_with_graph: Path,
) -> None:
    """§A7: calling the poll handler twice with the same snapshot must NOT
    re-emit ``ui.mermaid`` the second time.
    """
    from unittest.mock import MagicMock, patch

    from nicegui import ui

    # Collect the timer callback so we can call it a second time manually.
    captured: dict[str, Any] = {"timer_cb": None}

    def fake_timer(interval: float, cb: Any, *a: Any, **kw: Any) -> Any:  # noqa: ARG001
        captured["timer_cb"] = cb
        return MagicMock()

    mermaid_mock = MagicMock()
    mermaid_mock.return_value.classes = MagicMock(return_value=MagicMock())

    with patch.object(ui, "mermaid", mermaid_mock), patch.object(ui, "timer", fake_timer):
        from token_world.dashboard.panels.graph_canvas import mount_graph_panel

        mount_graph_panel(fake_universe_with_graph, "int-universe")

    # Initial render during mount must emit exactly once.
    first_calls = mermaid_mock.call_count
    assert first_calls == 1, f"expected 1 initial ui.mermaid, got {first_calls}"

    # Drive the timer callback (simulates the 5s poll) — no graph change
    # between polls, so signature is unchanged and we should NOT re-emit.
    timer_cb = captured["timer_cb"]
    assert timer_cb is not None, "mount_graph_panel failed to register ui.timer"
    timer_cb()
    assert mermaid_mock.call_count == first_calls, (
        f"poll re-emitted ui.mermaid even though signature was unchanged "
        f"(before={first_calls}, after={mermaid_mock.call_count})"
    )


def test_mount_graph_panel_poll_does_not_rebuild_drawer(
    fake_universe_with_graph: Path,
) -> None:
    """§A7: the property drawer is USER-state. Once the initial placeholder
    is rendered, the drawer must NEVER be rebuilt by the poll handler —
    scroll position + open state must survive.
    """
    from unittest.mock import MagicMock, patch

    from nicegui import ui

    captured: dict[str, Any] = {"timer_cb": None}

    def fake_timer(interval: float, cb: Any, *a: Any, **kw: Any) -> Any:  # noqa: ARG001
        captured["timer_cb"] = cb
        return MagicMock()

    columns_created: list[MagicMock] = []
    real_column = ui.column

    def fake_column(*a: Any, **kw: Any) -> Any:
        real_col = real_column(*a, **kw)
        spy = MagicMock(wraps=real_col)
        spy.__enter__ = MagicMock(side_effect=lambda: real_col.__enter__())
        spy.__exit__ = MagicMock(side_effect=lambda *args: real_col.__exit__(*args))
        spy.classes = MagicMock(side_effect=real_col.classes)
        spy.clear = MagicMock(side_effect=real_col.clear)
        columns_created.append(spy)
        return spy

    mermaid_mock = MagicMock()
    mermaid_mock.return_value.classes = MagicMock(return_value=MagicMock())

    with (
        patch.object(ui, "mermaid", mermaid_mock),
        patch.object(ui, "timer", fake_timer),
        patch.object(ui, "column", fake_column),
    ):
        from token_world.dashboard.panels.graph_canvas import mount_graph_panel

        mount_graph_panel(fake_universe_with_graph, "int-universe")

    drawer_clear_calls_after_mount = sum(c.clear.call_count for c in columns_created)

    timer_cb = captured["timer_cb"]
    assert timer_cb is not None

    # Two poll cycles with no change — no column should be cleared again,
    # because the chart is signature-gated and the drawer is user-state.
    timer_cb()
    timer_cb()
    drawer_clear_calls_after_polls = sum(c.clear.call_count for c in columns_created)
    assert drawer_clear_calls_after_polls == drawer_clear_calls_after_mount, (
        "poll handler rebuilt a column (likely the drawer) even though "
        "nothing changed: "
        f"before={drawer_clear_calls_after_mount} after={drawer_clear_calls_after_polls}"
    )
