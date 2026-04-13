"""Shared pytest fixtures for the operator test tree.

Plan 04.1-01 ships:
    - ``universe``: a scaffolded temporary universe folder
    - ``yield_signal_json_fixture``: a dict matching the 7 ``YieldSignal`` fields,
      used by Plan-02's ``test_yield_signal.py`` round-trip tests.
    - ``stub_yield``: factory callable returning a validated :class:`YieldSignal`
      wired to the per-test :func:`universe` fixture (Task 3).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from token_world.operator import YieldSignal
from token_world.operator.testing import EngineStub
from token_world.universe.manager import UniverseManager


@pytest.fixture
def universe(tmp_path: Path) -> Path:
    """Return a scaffolded temporary universe folder.

    Uses :class:`UniverseManager` with ``data_dir=tmp_path`` so each test gets
    a clean, isolated universe under pytest's ``tmp_path``. The returned
    :class:`Path` is the universe folder (contains ``universe.db``,
    ``mechanics/``, ``agents/``, etc.).
    """
    manager = UniverseManager(data_dir=tmp_path)
    return manager.create("test-operator")


@pytest.fixture
def yield_signal_json_fixture() -> Callable[..., dict[str, Any]]:
    """Factory returning a dict with all 7 ``YieldSignal`` fields populated.

    Plan-02 ``test_yield_signal.py`` uses this to build ``from_json`` payloads.
    Callers can pass keyword overrides; unknown keys are added verbatim (used
    by tests that probe the "extra fields" rejection path).
    """

    def _make(**overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "tick_id": "tick_42",
            "universe_path": "/tmp/test-universe",
            "schema_version": 1,
            "reason": "no_mechanic_for_action",
            "action_text": "pick up the rock",
            "classified_action": {
                "verb": "pickup",
                "actor": "alice",
                "target": "rock_1",
                "params": {},
            },
            "actor_state": {"location": "room_a", "inventory": []},
            "candidate_mechanic_ids": ["grasp", "pickup_v0"],
        }
        base.update(overrides)
        return base

    return _make


@pytest.fixture
def stub_yield(universe: Path) -> Callable[..., YieldSignal]:
    """Factory: call with ``verb=...``, ``actor=...``, plus any optional overrides.

    Returns :meth:`EngineStub.fabricate_yield` bound to the per-test ``universe``
    fixture so every fabricated :class:`YieldSignal` carries ``universe_path``
    pointing at the scaffolded temp universe (D-09/D-10 contract guarantee).
    """
    stub = EngineStub(universe_path=universe)
    return stub.fabricate_yield
