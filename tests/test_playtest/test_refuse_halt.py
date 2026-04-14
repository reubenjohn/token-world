"""Regression tests for ``scripts/run_unattended.py`` consecutive-refuse auto-halt.

MORNING-HANDOFF.md §C documents session 4 round 2 ticks 44-47, where the
resident agent (Mira) decompensated out of character after several refuses
piled up ("I notice the universe framework has been activated..."). The
mitigation is a K-consecutive-refuse guard in the unattended runner — see
:func:`run_unattended.wrap_run_tick_with_refuse_halt`.

These tests load the script by file path (it lives outside the ``src/``
package layout) and exercise the wrapper directly with a fake
``engine.run_tick`` that returns refuse/ok results in a controlled sequence.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass
class _FakeResult:
    """Minimal stand-in for ``engine.TickResult`` — only ``kind`` is inspected."""

    kind: str
    tick_id: str = "tick_x"


def _load_run_unattended():
    """Import scripts/run_unattended.py by path (it's not importable as a module)."""
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "run_unattended.py"
    spec = importlib.util.spec_from_file_location("run_unattended_module", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_unattended_module"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def run_unattended():
    return _load_run_unattended()


def test_wrap_halts_on_k_consecutive_refuses(run_unattended) -> None:
    """K=6 consecutive refuses must raise SystemExit with a descriptive reason."""
    refuses = [_FakeResult(kind="refused", tick_id=f"t{i}") for i in range(10)]
    call_index = {"n": 0}

    def fake_run_tick(*_args, **_kwargs):
        r = refuses[call_index["n"]]
        call_index["n"] += 1
        return r

    state: dict = {"consecutive_refuses": 0, "halt_reason": None}
    wrapped = run_unattended.wrap_run_tick_with_refuse_halt(
        fake_run_tick, state, refuse_threshold=6
    )

    # First 5 calls must return cleanly
    for _ in range(5):
        result = wrapped()
        assert result.kind == "refused"

    # The 6th call must raise SystemExit
    with pytest.raises(SystemExit) as excinfo:
        wrapped()

    # Halt reason must be logged in shared state AND in the exception message
    assert state["consecutive_refuses"] == 6
    assert state["halt_reason"] is not None
    assert "6 consecutive refuses" in str(state["halt_reason"])
    assert "6 consecutive refuses" in str(excinfo.value)
    assert "character-break" in str(state["halt_reason"])


def test_wrap_resets_counter_on_ok_result(run_unattended) -> None:
    """An ``ok`` result between refuses must reset the consecutive counter."""
    # 3 refuses, 1 ok, then 3 more refuses — should NOT halt at K=6
    script = [
        _FakeResult(kind="refused"),
        _FakeResult(kind="refused"),
        _FakeResult(kind="refused"),
        _FakeResult(kind="ok"),
        _FakeResult(kind="refused"),
        _FakeResult(kind="refused"),
        _FakeResult(kind="refused"),
    ]
    call_index = {"n": 0}

    def fake_run_tick(*_args, **_kwargs):
        r = script[call_index["n"]]
        call_index["n"] += 1
        return r

    state: dict = {"consecutive_refuses": 0, "halt_reason": None}
    wrapped = run_unattended.wrap_run_tick_with_refuse_halt(
        fake_run_tick, state, refuse_threshold=6
    )

    # All seven calls complete without SystemExit
    for _ in range(7):
        wrapped()

    # The final streak is only 3 refuses — no halt
    assert state["consecutive_refuses"] == 3
    assert state["halt_reason"] is None


def test_wrap_disabled_when_threshold_zero(run_unattended) -> None:
    """``refuse_threshold=0`` disables the guard — 100 refuses must pass through."""

    def fake_run_tick(*_args, **_kwargs):
        return _FakeResult(kind="refused")

    state: dict = {"consecutive_refuses": 0, "halt_reason": None}
    wrapped = run_unattended.wrap_run_tick_with_refuse_halt(
        fake_run_tick, state, refuse_threshold=0
    )

    # 100 refuses without any halt
    for _ in range(100):
        wrapped()

    assert state["consecutive_refuses"] == 100
    assert state["halt_reason"] is None


def test_wrap_ignores_yielded_like_refused_for_reset(run_unattended) -> None:
    """A ``yielded`` tick resets the consecutive-refuse counter (it's not a refuse)."""
    script = [
        _FakeResult(kind="refused"),
        _FakeResult(kind="refused"),
        _FakeResult(kind="yielded"),
        _FakeResult(kind="refused"),
    ]
    call_index = {"n": 0}

    def fake_run_tick(*_args, **_kwargs):
        r = script[call_index["n"]]
        call_index["n"] += 1
        return r

    state: dict = {"consecutive_refuses": 0, "halt_reason": None}
    wrapped = run_unattended.wrap_run_tick_with_refuse_halt(
        fake_run_tick, state, refuse_threshold=6
    )

    for _ in range(4):
        wrapped()

    # After yielded + 1 refused -> counter = 1
    assert state["consecutive_refuses"] == 1
    assert state["halt_reason"] is None


def test_wrap_passes_args_through(run_unattended) -> None:
    """Wrapper must pass positional and keyword arguments to the underlying fn."""
    captured: dict = {}

    def fake_run_tick(action, *, actor):
        captured["action"] = action
        captured["actor"] = actor
        return _FakeResult(kind="ok")

    state: dict = {"consecutive_refuses": 0, "halt_reason": None}
    wrapped = run_unattended.wrap_run_tick_with_refuse_halt(
        fake_run_tick, state, refuse_threshold=6
    )

    wrapped("look north", actor="alice")

    assert captured == {"action": "look north", "actor": "alice"}
