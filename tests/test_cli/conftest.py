"""Shared fixtures for ``token-world`` CLI tests.

Provides ``fake_universe`` — a minimal valid universe directory built
without invoking ``UniverseManager.create()`` (which scaffolds git, copies
seed mechanics, runs Jinja, etc.). Tests that need realistic seed
mechanics can still use ``UniverseManager`` directly.

The fake universe has:

- ``universe.db`` containing a working ``KnowledgeGraph``-format SQLite
  schema (created by saving an empty graph through the public API).
- ``mechanics/`` (empty by default; tests opt in to fake mechanic files).
- ``tick_summaries/ticks/``, ``tick_summaries/batches/``,
  ``tick_summaries/epochs/`` directories.
- ``.mcp.json`` so :func:`resolve_universe` recognises it when used via
  cwd discovery.

Tests pass the *root* directory; commands that take a slug instead use
``UniverseManager``-managed universes via ``tmp_data_dir`` (see the root
``conftest.py``).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest


def _write_tick_summary(
    ticks_dir: Path,
    tick_id: str | int,
    *,
    timestamp_iso: str = "2026-04-14T00:00:00Z",
    action_text: str = "do something",
    classified_action: dict[str, Any] | None = None,
    matched_mechanic_id: str | None = None,
    yielded: bool = False,
    refused: bool = False,
    refusal_reason: str | None = None,
    mutations: list[list[Any]] | None = None,
    observation_text: str | None = "you do something",
    long_running_action: dict[str, Any] | None = None,
    duration_ms: int = 100,
    classifier_in: int = 0,
    classifier_out: int = 0,
    classifier_cost: float = 0.0,
    observer_in: int = 0,
    observer_out: int = 0,
    observer_cost: float = 0.0,
) -> Path:
    """Write a TickSummary-shaped JSON file. Returns the path."""
    ticks_dir.mkdir(parents=True, exist_ok=True)
    mutations_list = mutations if mutations is not None else []
    payload = {
        "schema_version": 1,
        "tick_id": str(tick_id),
        "timestamp_iso": timestamp_iso,
        "action_text": action_text,
        "classified_action": classified_action,
        "matched_mechanic_id": matched_mechanic_id,
        "yielded": yielded,
        "refused": refused,
        "refusal_reason": refusal_reason,
        "mutations": {"count": len(mutations_list), "list": mutations_list},
        "observation_text": observation_text,
        "long_running_action": long_running_action,
        "duration_ms": duration_ms,
        "llm_tokens_by_stage": {
            "classifier": {"in": classifier_in, "out": classifier_out},
            "observer": {"in": observer_in, "out": observer_out},
        },
        "llm_cost_usd_by_stage": {
            "classifier": classifier_cost,
            "observer": observer_cost,
        },
    }
    path = ticks_dir / f"tick_{tick_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def write_tick() -> Callable[..., Path]:
    """Return a helper that writes a tick summary into a directory.

    Usage::

        def test_x(fake_universe, write_tick):
            tdir = fake_universe / "tick_summaries" / "ticks"
            write_tick(tdir, "1", action_text="open chest")
    """
    return _write_tick_summary


@pytest.fixture
def fake_universe(tmp_path: Path) -> Path:
    """Build a minimal valid universe directory and return its root path.

    The directory is *not* registered with :class:`UniverseManager`; tests
    that go through the CLI's slug resolution must use ``tmp_data_dir +
    UniverseManager().create(...)`` instead. This fixture is for module-
    level aggregator tests that take a directory directly.
    """
    universe_dir = tmp_path / "fake-universe"
    universe_dir.mkdir()
    (universe_dir / "mechanics").mkdir()
    (universe_dir / "tick_summaries" / "ticks").mkdir(parents=True)
    (universe_dir / "tick_summaries" / "batches").mkdir(parents=True)
    (universe_dir / "tick_summaries" / "epochs").mkdir(parents=True)
    (universe_dir / "agents").mkdir()
    # Marker for resolve_universe(cwd=...) discovery.
    (universe_dir / ".mcp.json").write_text("{}", encoding="utf-8")
    return universe_dir


@pytest.fixture
def fake_universe_with_graph(fake_universe: Path) -> Path:
    """Like ``fake_universe`` but also persists a tiny KnowledgeGraph."""
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
