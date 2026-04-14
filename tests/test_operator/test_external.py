"""Tests for :mod:`token_world.operator.external` (v1.1 file-based operator)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from token_world.operator.external import (
    ExternalOperator,
    ExternalOperatorResult,
    external_operator_factory,
)


def _drive(coro):  # small helper — pytest-asyncio is not a declared dep
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def fresh_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


def test_yield_path_layout(universe: Path) -> None:
    op = ExternalOperator(universe)
    assert op.yield_path("42") == universe / "operator_inbox" / "42.yield.json"
    assert op.resolved_path("42") == universe / "operator_inbox" / "42.resolved"
    assert op.rejected_path("42") == universe / "operator_inbox" / "42.rejected"
    assert (universe / "operator_inbox").is_dir()


def test_handle_yield_resolved_path(universe: Path, stub_yield, fresh_loop) -> None:
    op = ExternalOperator(universe, timeout_s=5.0, poll_s=0.05)
    signal = stub_yield(verb="pickup", actor="alice")

    async def _drop_resolution() -> None:
        # Wait one poll cycle then drop a resolved marker.
        await asyncio.sleep(0.1)
        op.resolved_path(signal.tick_id).write_text(
            json.dumps({"mechanic_id": "pickup_v1", "attempts": 2})
        )

    async def _run() -> ExternalOperatorResult:
        drop = asyncio.create_task(_drop_resolution())
        result = await op.handle_yield(signal)
        await drop
        return result

    result = fresh_loop.run_until_complete(_run())
    assert result.success is True
    assert result.mechanic_id == "pickup_v1"
    assert result.attempts == 2
    assert not op.yield_path(signal.tick_id).exists()
    assert not op.resolved_path(signal.tick_id).exists()


def test_handle_yield_rejected_path(universe: Path, stub_yield, fresh_loop) -> None:
    op = ExternalOperator(universe, timeout_s=5.0, poll_s=0.05)
    signal = stub_yield(verb="time_travel", actor="bob")

    async def _drop_rejection() -> None:
        await asyncio.sleep(0.1)
        op.rejected_path(signal.tick_id).write_text(json.dumps({"reason": "incoherent_action"}))

    async def _run() -> ExternalOperatorResult:
        drop = asyncio.create_task(_drop_rejection())
        result = await op.handle_yield(signal)
        await drop
        return result

    result = fresh_loop.run_until_complete(_run())
    assert result.success is False
    assert result.error == "incoherent_action"
    assert not op.yield_path(signal.tick_id).exists()


def test_handle_yield_timeout(universe: Path, stub_yield, fresh_loop) -> None:
    op = ExternalOperator(universe, timeout_s=0.3, poll_s=0.05)
    signal = stub_yield(verb="stare", actor="alice")

    result = fresh_loop.run_until_complete(op.handle_yield(signal))
    assert result.success is False
    assert result.error == "timeout"
    assert not op.yield_path(signal.tick_id).exists()


def test_handle_yield_kill_switch(universe: Path, stub_yield, fresh_loop) -> None:
    op = ExternalOperator(universe, timeout_s=5.0, poll_s=0.05)
    signal = stub_yield(verb="sit", actor="alice")
    (universe / ".stop").write_text("halt")

    result = fresh_loop.run_until_complete(op.handle_yield(signal))
    assert result.success is False
    assert result.error == "kill_switch"


def test_operator_log_is_appended(universe: Path, stub_yield, fresh_loop) -> None:
    op = ExternalOperator(universe, timeout_s=0.2, poll_s=0.05)
    signal = stub_yield(verb="wave", actor="alice")
    fresh_loop.run_until_complete(op.handle_yield(signal))

    log = (universe / "operator-log.jsonl").read_text().strip().splitlines()
    assert len(log) >= 2
    events = [json.loads(line)["event"] for line in log]
    assert "yield_emitted" in events
    assert "resolution_timeout" in events


def test_malformed_resolution_is_recoverable(universe: Path, stub_yield, fresh_loop) -> None:
    """Orchestrator should never crash the runner with malformed JSON."""
    op = ExternalOperator(universe, timeout_s=5.0, poll_s=0.05)
    signal = stub_yield(verb="sing", actor="alice")

    async def _drop() -> None:
        await asyncio.sleep(0.1)
        op.resolved_path(signal.tick_id).write_text("not valid json")

    async def _run() -> ExternalOperatorResult:
        drop = asyncio.create_task(_drop())
        r = await op.handle_yield(signal)
        await drop
        return r

    result = fresh_loop.run_until_complete(_run())
    # Malformed JSON is swallowed; resolution still consumed, success True.
    assert result.success is True
    assert result.mechanic_id is None


def test_factory_respects_env(universe: Path, monkeypatch) -> None:
    monkeypatch.setenv("TOKEN_WORLD_OPERATOR_TIMEOUT_S", "42")
    monkeypatch.setenv("TOKEN_WORLD_OPERATOR_POLL_S", "0.1")
    op = external_operator_factory(universe)
    assert op.timeout_s == 42.0
    assert op.poll_s == 0.1
