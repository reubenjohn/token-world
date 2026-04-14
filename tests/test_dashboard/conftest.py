"""Fixtures for dashboard tests.

Reuses the tick-writer helper from ``tests/test_cli/conftest.py`` and
defines a local ``fake_universe`` fixture (the CLI conftest scopes it to
``tests/test_cli/``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_cli.conftest import _write_tick_summary


@pytest.fixture
def fake_universe(tmp_path: Path) -> Path:
    """Minimal universe directory: mechanics/, tick_summaries/*, agents/."""
    universe_dir = tmp_path / "fake-universe"
    universe_dir.mkdir()
    (universe_dir / "mechanics").mkdir()
    (universe_dir / "tick_summaries" / "ticks").mkdir(parents=True)
    (universe_dir / "tick_summaries" / "batches").mkdir(parents=True)
    (universe_dir / "tick_summaries" / "epochs").mkdir(parents=True)
    (universe_dir / "agents").mkdir()
    (universe_dir / ".mcp.json").write_text("{}", encoding="utf-8")
    return universe_dir


@pytest.fixture
def fake_universe_with_graph(fake_universe: Path) -> Path:
    """A ``fake_universe`` with a tiny persisted KnowledgeGraph."""
    from token_world.graph import KnowledgeGraph

    kg = KnowledgeGraph(db_path=fake_universe / "universe.db")
    kg.add_node("alice", node_type="agent")
    kg.add_node("bob", node_type="agent")
    kg.add_node("chest", node_type="entity", subtype="container")
    kg.add_node("room", node_type="entity")
    kg.add_edge("alice", "room", relation="located_in")
    kg.add_edge("bob", "room", relation="located_in")
    kg.add_edge("chest", "room", relation="located_in")
    kg.save()
    return fake_universe


@pytest.fixture
def write_tick_dashboard():  # noqa: ANN201 — callable fixture.
    """Return the tick-writer helper (re-exported for local tests)."""
    return _write_tick_summary
