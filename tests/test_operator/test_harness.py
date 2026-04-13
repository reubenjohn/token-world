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
# _parse_final — robustness regressions (WR-01)
# ---------------------------------------------------------------------------


def test_parse_final_handles_nested_json_object() -> None:
    """WR-01: final-message JSON with a nested ``{...}`` value must parse.

    The old ``\\{[^{}]*\\}`` regex excluded braces inside the candidate, so a
    payload like ``{"success": true, "params": {"x": 1}, "attempts": 3}`` only
    matched the *inner* object and reported failure. The fix uses
    ``json.JSONDecoder.raw_decode`` which respects brace nesting.
    """
    text = '{"success": true, "mechanic_id": "meditate", "params": {"x": 1}, "attempts": 3}'
    success, mechanic_id, attempts = OperatorHarness._parse_final(text)
    assert success is True
    assert mechanic_id == "meditate"
    assert attempts == 3


def test_parse_final_handles_nested_json_wrapped_in_prose() -> None:
    """Nested JSON embedded in prose (the pessimistic real-model case)."""
    text = (
        "I called validate with params {duration: 5} and got "
        '{"success": true, "mechanic_id": "meditate", '
        '"params": {"x": 1, "y": {"z": 2}}, "attempts": 2} '
        "so we're done."
    )
    success, mechanic_id, attempts = OperatorHarness._parse_final(text)
    assert success is True
    assert mechanic_id == "meditate"
    assert attempts == 2


def test_parse_final_prefers_last_json_candidate_in_prose() -> None:
    """If multiple JSON objects appear, the LAST one (summary) wins."""
    text = (
        'First attempt: {"success": false, "mechanic_id": null, "attempts": 1}. '
        'Retried: {"success": true, "mechanic_id": "final", "attempts": 2}.'
    )
    success, mechanic_id, attempts = OperatorHarness._parse_final(text)
    assert success is True
    assert mechanic_id == "final"
    assert attempts == 2


def test_parse_final_prose_only_returns_failure_tuple() -> None:
    """Prose with no JSON object still returns ``(False, None, 0)``."""
    success, mechanic_id, attempts = OperatorHarness._parse_final(
        "I tried but it didn't work because reasons."
    )
    assert success is False
    assert mechanic_id is None
    assert attempts == 0


def test_parse_final_flat_json_still_parses() -> None:
    """Backwards compatibility: flat JSON (the common case) keeps working."""
    text = '{"success": true, "mechanic_id": "meditate", "attempts": 1}'
    success, mechanic_id, attempts = OperatorHarness._parse_final(text)
    assert success is True
    assert mechanic_id == "meditate"
    assert attempts == 1


@pytest.mark.asyncio
async def test_handle_yield_handles_nested_json_in_final(
    universe: Path,
    stub_yield: Callable[..., YieldSignal],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: a final message with nested JSON produces ``success=True``."""
    fake_msgs = [
        _make_result_msg(
            result=(
                '{"success": true, "mechanic_id": "meditate", '
                '"params": {"duration": 5}, "attempts": 1}'
            )
        ),
    ]
    monkeypatch.setattr("token_world.operator.harness.query", _fake_query_factory(fake_msgs))

    h = OperatorHarness(universe)
    signal = stub_yield(verb="meditate", actor="alice")
    result = await h.handle_yield(signal)
    assert result.success is True
    assert result.mechanic_id == "meditate"
    assert result.attempts == 1


# ---------------------------------------------------------------------------
# _track_validation — observability (WR-03)
# ---------------------------------------------------------------------------


class _FakeCtx:
    """Minimal stand-in for OperatorDiagnosticsContext used by _track_validation."""

    def __init__(self) -> None:
        self.writes: list[tuple[int, dict[str, Any]]] = []

    def write_validation_report(self, attempt_n: int, report: dict[str, Any]) -> None:
        self.writes.append((attempt_n, report))


def _make_tool_result_block(tool_use_id: str, content: Any = "irrelevant") -> Any:
    """Duck-typed ToolResultBlock with class name ``ToolResultBlock``."""

    class ToolResultBlock:  # class-name detection is what harness uses
        def __init__(self) -> None:
            self.tool_use_id = tool_use_id
            self.content = content

    return ToolResultBlock()


def _make_msg_with_blocks(blocks: list[Any]) -> Any:
    """Minimal SDK-like message with a ``content`` list of blocks."""
    m = MagicMock()
    m.content = blocks
    return m


def test_track_validation_logs_uncorrelated_tool_result_blocks(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """WR-03: an uncorrelated ToolResultBlock must be logged at DEBUG level.

    Silent drops leave replay-tick consumers with incomplete diagnostic records
    and no signal; a debug log lets forensic operators spot correlation misses
    without changing runtime behaviour.

    Uses the loguru->stdlib-logging propagation pattern from
    test_graph/test_spatial_index.py so pytest's caplog sees loguru records.
    """
    import logging

    from loguru import logger as loguru_logger

    class PropagateHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - glue
            logging.getLogger(record.name).handle(record)

    handler_id = loguru_logger.add(PropagateHandler(), format="{message}", level="DEBUG")
    try:
        ctx = _FakeCtx()
        pending: dict[str, int] = {}
        orphan_block = _make_tool_result_block("nonexistent-id-42", content="some content")
        msg = _make_msg_with_blocks([orphan_block])
        with caplog.at_level("DEBUG"):
            counter = OperatorHarness._track_validation(
                msg=msg, ctx=ctx, pending=pending, counter=0
            )
        assert counter == 0, "counter should not advance for uncorrelated results"
        assert not ctx.writes, "uncorrelated block must NOT produce a validation report write"
        # Debug log must mention the orphan id so operators can grep for it.
        assert any("nonexistent-id-42" in rec.message for rec in caplog.records), (
            f"No debug log mentioning orphan tool_use_id in records: "
            f"{[r.message for r in caplog.records]}"
        )
    finally:
        loguru_logger.remove(handler_id)


def test_track_validation_correlated_blocks_still_write_reports(tmp_path: Path) -> None:
    """Regression guard: the WR-03 fix must NOT break the happy path.

    A matching ToolUseBlock + ToolResultBlock pair should still record a
    validation report on disk — the debug log is additive, not a behaviour
    change.
    """

    class ToolUseBlock:
        def __init__(self, name: str, tool_use_id: str) -> None:
            self.name = name
            self.id = tool_use_id

    use_block = ToolUseBlock("mcp__validation__validate_mechanic", "id-1")
    result_block = _make_tool_result_block("id-1", content='{"passed": true, "attempt": 1}')

    ctx = _FakeCtx()
    pending: dict[str, int] = {}

    # First message: ToolUseBlock -> counter advances, pending populated.
    counter = OperatorHarness._track_validation(
        msg=_make_msg_with_blocks([use_block]),
        ctx=ctx,
        pending=pending,
        counter=0,
    )
    assert counter == 1
    assert pending == {"id-1": 1}

    # Second message: matching ToolResultBlock -> report written, pending emptied.
    counter = OperatorHarness._track_validation(
        msg=_make_msg_with_blocks([result_block]),
        ctx=ctx,
        pending=pending,
        counter=counter,
    )
    assert pending == {}
    assert len(ctx.writes) == 1
    attempt_n, report = ctx.writes[0]
    assert attempt_n == 1
    assert report.get("passed") is True


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
