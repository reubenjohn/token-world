"""Tests for the side-effect chain panel (§A5).

Renders an ``ExecutionTrace`` as an indented tree inside a tick-card
expansion. We unit-test both branches of the renderer:

- disk-backed: when the trace lives at
  ``<universe>/diagnostics/tick_<id>/execution/trace.json``
- trace-direct: when the caller passes the trace dict in-hand

The real NiceGUI render surface is stubbed out by the same
``_FakeUI`` / ``_FakeElement`` pair used in ``test_tick_stream.py``;
we assert on the produced element tree, not on any visual output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.test_dashboard.test_tick_stream import (
    _collect_label_texts,
    _FakeUI,
    _patch_ui,
    _reset_fake_ui,
)


def _write_trace(universe_dir: Path, tick_id: str, trace: dict[str, Any]) -> Path:
    d = universe_dir / "diagnostics" / f"tick_{tick_id}" / "execution"
    d.mkdir(parents=True, exist_ok=True)
    path = d / "trace.json"
    path.write_text(json.dumps(trace), encoding="utf-8")
    return path


def test_render_refused_tick_shows_placeholder(monkeypatch, fake_universe: Path) -> None:
    """A refused tick has no execution trace; renderer emits a placeholder."""
    _reset_fake_ui()
    _patch_ui(monkeypatch)

    from nicegui import ui as real_ui

    from token_world.dashboard.panels.side_effect_chain import render_side_effect_tree

    parent = real_ui.column()
    with parent:
        render_side_effect_tree(
            {"tick_id": "1", "refused": True, "matched_mechanic_id": None},
            parent,
            universe_dir=fake_universe,
        )

    texts = _collect_label_texts(parent)
    joined = "\n".join(texts)
    assert "no execution trace (refused/yielded tick)" in joined


def test_render_nested_trace_produces_indented_rows(monkeypatch, fake_universe: Path) -> None:
    """An ExecutionTrace with 2 levels of nesting produces 2 indented rows."""
    _reset_fake_ui()
    _patch_ui(monkeypatch)

    # Depth-2 trace: root -> child -> grandchild
    trace = {
        "root": {
            "mechanic_id": "force_lock",
            "actor": "mira",
            "target": "old_chest",
            "check_passed": True,
            "check_reasons": [],
            "mutations": [
                {
                    "type": "set_property",
                    "target": "old_chest",
                    "property": "locked",
                    "old_value": True,
                    "new_value": False,
                }
            ],
            "children": [
                {
                    "mechanic_id": "unlock_chest",
                    "actor": "engine",
                    "target": "old_chest",
                    "check_passed": True,
                    "check_reasons": [],
                    "mutations": [],
                    "children": [
                        {
                            "mechanic_id": "observe_chest",
                            "actor": "engine",
                            "target": "old_chest",
                            "check_passed": True,
                            "check_reasons": [],
                            "mutations": [],
                            "children": [],
                        }
                    ],
                }
            ],
        },
        "total_mechanics_executed": 3,
        "max_depth_reached": 2,
        "truncated": False,
    }
    _write_trace(fake_universe, "7", trace)

    from nicegui import ui as real_ui

    from token_world.dashboard.panels.side_effect_chain import render_side_effect_tree

    parent = real_ui.column()
    with parent:
        render_side_effect_tree(
            {"tick_id": "7", "refused": False, "yielded": False},
            parent,
            universe_dir=fake_universe,
        )

    # Collect every header line — one per TraceNode.
    texts = _collect_label_texts(parent)
    joined = "\n".join(texts)

    # All three mechanics appear.
    assert "force_lock(check_pass)" in joined
    assert "unlock_chest(check_pass)" in joined
    assert "observe_chest(check_pass)" in joined
    # max_depth_reached chip rendered (>0).
    assert "max_depth_reached: 2" in joined
    # Mutation summary line.
    assert "old_chest.locked" in joined

    # Check that rendered rows have increasing left margins (depth indent).
    # Each TraceNode gets its own ui.column() with a margin-left style.
    indent_rows: list[int] = []
    for elem in _FakeUI._created:
        if elem.factory == "column" and "margin-left" in elem._style:
            margin = elem._style.split("margin-left:")[1]
            px = int(margin.split("px")[0].strip())
            indent_rows.append(px)

    # At least 3 rows (one per TraceNode) with strictly-increasing margins.
    assert len(indent_rows) >= 3, f"expected 3+ indented rows; got {indent_rows}"
    assert indent_rows[:3] == sorted(indent_rows[:3]), (
        f"indent must be monotonic non-decreasing by tree depth; got {indent_rows[:3]}"
    )


def test_render_truncated_trace_shows_warning_chip(monkeypatch, fake_universe: Path) -> None:
    """When the chain hit max_depth, the renderer surfaces a warning chip."""
    _reset_fake_ui()
    _patch_ui(monkeypatch)

    trace = {
        "root": {
            "mechanic_id": "cascade_start",
            "actor": "sim",
            "target": "tile",
            "check_passed": True,
            "check_reasons": [],
            "mutations": [],
            "children": [],
        },
        "total_mechanics_executed": 5,
        "max_depth_reached": 3,
        "truncated": True,
    }
    _write_trace(fake_universe, "11", trace)

    from nicegui import ui as real_ui

    from token_world.dashboard.panels.side_effect_chain import render_side_effect_tree

    parent = real_ui.column()
    with parent:
        render_side_effect_tree(
            {"tick_id": "11", "refused": False, "yielded": False},
            parent,
            universe_dir=fake_universe,
        )

    joined = "\n".join(_collect_label_texts(parent))
    assert "truncated" in joined
    assert "cascade_start" in joined
