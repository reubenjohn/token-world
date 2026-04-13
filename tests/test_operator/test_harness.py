"""Unit tests for ``OperatorHarness`` (Task 2).

Mocks the Agent SDK ``query`` async-generator so no real LLM is invoked. The
real-Opus end-to-end test lives in ``test_integration.py`` (Task 3) and is
gated behind ``@pytest.mark.integration``.
"""

from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage

from token_world.operator import (
    OperatorHarness,
    OperatorResult,
    YieldSignal,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result_msg(
    *,
    result: str = '{"success": true, "mechanic_id": "meditate", "attempts": 2}',
    cost: float | None = 0.15,
    turns: int = 7,
) -> Any:
    """Build a MagicMock with ResultMessage's interface."""
    m = MagicMock(spec=ResultMessage)
    m.result = result
    m.total_cost_usd = cost
    m.num_turns = turns
    m.subtype = "success"
    m.is_error = False
    return m


def _make_assistant_msg(text: str = "ok") -> Any:
    """Lightweight fake AssistantMessage with the attributes harness reads."""
    m = MagicMock()
    m.__class__ = MagicMock  # not used for isinstance checks
    m.content = [{"type": "text", "text": text}]
    m.parent_tool_use_id = None
    m.message_id = "msg_xxx"
    return m


def _fake_query_factory(
    messages: list[Any],
) -> Callable[..., AsyncIterator[Any]]:
    """Return a function with the same kwargs signature as ``query``."""

    async def _fake_query(
        *, prompt: str, options: ClaudeAgentOptions, transport: Any = None
    ) -> AsyncIterator[Any]:
        for m in messages:
            yield m

    return _fake_query


# ---------------------------------------------------------------------------
# Construction & defaults
# ---------------------------------------------------------------------------


def test_harness_init_sets_defaults(universe: Path) -> None:
    h = OperatorHarness(universe)
    assert h.universe == universe
    assert h.model == "opus"
    assert h.max_turns == 20
    assert h.max_budget_usd == pytest.approx(5.0)


def test_harness_init_overrides(universe: Path) -> None:
    h = OperatorHarness(universe, model="sonnet", max_turns=30, max_budget_usd=2.0)
    assert h.model == "sonnet"
    assert h.max_turns == 30
    assert h.max_budget_usd == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# _build_options content
# ---------------------------------------------------------------------------


def test_options_include_Agent_in_allowed_tools(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    """Pitfall 1 — without ``Agent`` in allowed_tools the subagent never runs."""
    h = OperatorHarness(universe)
    signal = stub_yield(verb="meditate", actor="alice")
    options = h._build_options(signal)
    assert options.allowed_tools is not None
    assert "Agent" in options.allowed_tools


def test_options_include_three_token_world_mcp_tools(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    """UNIV-03: harness must expose all 3 locked MCP tools (resume_tick / list / rollback)."""
    h = OperatorHarness(universe)
    signal = stub_yield(verb="meditate", actor="alice")
    options = h._build_options(signal)
    assert options.allowed_tools is not None
    for required in (
        "mcp__token-world__resume_tick",
        "mcp__token-world__list_mechanics",
        "mcp__token-world__rollback",
    ):
        assert required in options.allowed_tools, f"Missing {required}"


def test_options_include_validate_mechanic_tool(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    h = OperatorHarness(universe)
    options = h._build_options(stub_yield(verb="meditate", actor="alice"))
    assert options.allowed_tools is not None
    assert "mcp__validation__validate_mechanic" in options.allowed_tools


def test_options_model_is_opus(universe: Path, stub_yield: Callable[..., YieldSignal]) -> None:
    h = OperatorHarness(universe)
    options = h._build_options(stub_yield(verb="meditate", actor="alice"))
    assert options.model == "opus"


def test_options_cwd_is_universe(universe: Path, stub_yield: Callable[..., YieldSignal]) -> None:
    h = OperatorHarness(universe)
    options = h._build_options(stub_yield(verb="meditate", actor="alice"))
    assert options.cwd == str(universe)


def test_options_max_turns_is_20_by_default(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    h = OperatorHarness(universe)
    options = h._build_options(stub_yield(verb="meditate", actor="alice"))
    assert options.max_turns == 20


def test_options_permission_mode_is_bypass_for_programmatic(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    """D-05 programmatic path uses bypassPermissions; subagent's tight
    tools whitelist + cwd scope contain blast radius (Pitfall 2)."""
    h = OperatorHarness(universe)
    options = h._build_options(stub_yield(verb="meditate", actor="alice"))
    assert options.permission_mode == "bypassPermissions"


def test_options_have_mechanic_author_agent(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    h = OperatorHarness(universe)
    options = h._build_options(stub_yield(verb="meditate", actor="alice"))
    assert options.agents is not None
    assert "mechanic-author" in options.agents


def test_options_mcp_servers_include_validation_and_token_world(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    h = OperatorHarness(universe)
    options = h._build_options(stub_yield(verb="meditate", actor="alice"))
    assert options.mcp_servers is not None
    assert "validation" in options.mcp_servers
    assert "token-world" in options.mcp_servers


def test_options_max_budget_usd_wired(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    """BLOCKER-4 resolution: ``max_budget_usd`` IS a ClaudeAgentOptions field
    (probed on claude-agent-sdk 0.1.58); the harness wires it as a hard cap."""
    has_field = "max_budget_usd" in {f.name for f in dataclasses.fields(ClaudeAgentOptions)}
    assert has_field, (
        "BLOCKER-4 expected max_budget_usd to be a ClaudeAgentOptions field; "
        "if this fails the SDK version may have changed — reprobe with "
        "scripts/probe_agent_sdk.py and adapt _build_options."
    )
    h = OperatorHarness(universe, max_budget_usd=4.2)
    options = h._build_options(stub_yield(verb="meditate", actor="alice"))
    assert options.max_budget_usd == pytest.approx(4.2)


# ---------------------------------------------------------------------------
# handle_yield happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_yield_returns_operator_result(
    universe: Path,
    stub_yield: Callable[..., YieldSignal],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_msgs = [
        _make_assistant_msg("Calling subagent..."),
        _make_result_msg(
            result='{"success": true, "mechanic_id": "meditate", "attempts": 1}',
            cost=0.12,
            turns=5,
        ),
    ]
    monkeypatch.setattr("token_world.operator.harness.query", _fake_query_factory(fake_msgs))

    h = OperatorHarness(universe)
    signal = stub_yield(verb="meditate", actor="alice")
    result = await h.handle_yield(signal)

    assert isinstance(result, OperatorResult)
    assert result.success is True
    assert result.mechanic_id == "meditate"
    assert result.attempts == 1
    assert result.cost_usd == pytest.approx(0.12)
    assert result.turns == 5
    assert result.tick_id == signal.tick_id
    assert result.error is None


@pytest.mark.asyncio
async def test_handle_yield_writes_diagnostics(
    universe: Path,
    stub_yield: Callable[..., YieldSignal],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_msgs = [
        _make_assistant_msg("Step 1"),
        _make_assistant_msg("Step 2"),
        _make_result_msg(result='{"success": true, "mechanic_id": "meditate", "attempts": 2}'),
    ]
    monkeypatch.setattr("token_world.operator.harness.query", _fake_query_factory(fake_msgs))

    h = OperatorHarness(universe)
    signal = stub_yield(verb="meditate", actor="alice")
    await h.handle_yield(signal)

    op_dir = universe / "diagnostics" / f"tick_{signal.tick_id}" / "operator"
    assert (op_dir / "yield_signal.json").exists()
    attempts = op_dir / "authoring_attempts.jsonl"
    assert attempts.exists()
    assert attempts.stat().st_size > 0
    outcome = op_dir / "resume_outcome.json"
    assert outcome.exists()
    text = outcome.read_text()
    assert '"success": true' in text or '"success":true' in text.replace(" ", "")


@pytest.mark.asyncio
async def test_handle_yield_failure_path_captures_error(
    universe: Path,
    stub_yield: Callable[..., YieldSignal],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If query() raises, the diagnostics safety-net __exit__ records failure
    AND the exception bubbles to the caller (asyncio errors should not be swallowed)."""

    async def _raising_query(
        *, prompt: str, options: ClaudeAgentOptions, transport: Any = None
    ) -> AsyncIterator[Any]:
        yield _make_assistant_msg("starting")
        raise RuntimeError("simulated SDK failure")

    monkeypatch.setattr("token_world.operator.harness.query", _raising_query)

    h = OperatorHarness(universe)
    signal = stub_yield(verb="meditate", actor="alice")
    with pytest.raises(RuntimeError, match="simulated SDK failure"):
        await h.handle_yield(signal)

    # Safety net wrote the outcome
    outcome_path = (
        universe / "diagnostics" / f"tick_{signal.tick_id}" / "operator" / "resume_outcome.json"
    )
    assert outcome_path.exists()
    text = outcome_path.read_text()
    assert "false" in text.lower()  # success=false
    assert "RuntimeError" in text or "simulated SDK failure" in text


@pytest.mark.asyncio
async def test_handle_yield_unparseable_result_returns_failure(
    universe: Path,
    stub_yield: Callable[..., YieldSignal],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the outer model returns prose instead of JSON, fall back to (False, None, 0)."""
    fake_msgs = [
        _make_result_msg(result="I tried but it didn't work because reasons.", cost=0.05),
    ]
    monkeypatch.setattr("token_world.operator.harness.query", _fake_query_factory(fake_msgs))

    h = OperatorHarness(universe)
    signal = stub_yield(verb="meditate", actor="alice")
    result = await h.handle_yield(signal)

    assert result.success is False
    assert result.mechanic_id is None
    assert result.error is not None


@pytest.mark.asyncio
async def test_handle_yield_message_serialisation_does_not_crash_on_unexpected_shape(
    universe: Path,
    stub_yield: Callable[..., YieldSignal],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSONL append must not crash on weird message objects."""

    class WeirdMessage:
        pass

    fake_msgs = [
        WeirdMessage(),
        _make_result_msg(result='{"success": true, "mechanic_id": "x", "attempts": 1}'),
    ]
    monkeypatch.setattr("token_world.operator.harness.query", _fake_query_factory(fake_msgs))

    h = OperatorHarness(universe)
    signal = stub_yield(verb="meditate", actor="alice")
    result = await h.handle_yield(signal)
    assert result.success is True


# ---------------------------------------------------------------------------
# OperatorResult shape
# ---------------------------------------------------------------------------


def test_operator_result_is_frozen_slots() -> None:
    assert OperatorResult.__dataclass_params__.frozen is True
    # slots presence
    assert "__slots__" in OperatorResult.__dict__ or OperatorResult.__slots__ is not None


def test_operator_result_has_expected_fields() -> None:
    fields = {f.name for f in dataclasses.fields(OperatorResult)}
    expected = {
        "success",
        "tick_id",
        "mechanic_id",
        "attempts",
        "final_message",
        "cost_usd",
        "turns",
        "error",
    }
    assert expected <= fields, f"Missing fields: {expected - fields}"
