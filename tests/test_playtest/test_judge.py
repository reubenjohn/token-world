"""Tests for the optional Sonnet judge pass (D-13, TEST-04)."""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest

from token_world.playtest import build_transcript, prompt_hash
from token_world.playtest import evaluate as judge_evaluate
from token_world.playtest.report import PlaytestReport, TurnRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_turn(n: int, action: str = "look around", obs: str = "You see nothing.") -> TurnRecord:
    return TurnRecord(
        turn_number=n,
        action_text=action,
        observation_text=obs,
        tick_id=f"tick_{n}",
        kind="ok",
        score={
            "mechanic_match_rate": 1.0,
            "observation_groundedness": 1.0,
            "mutation_count": 1.0,
            "refusal_rate": 1.0,
            "action_novelty": 1.0,
            "composite": 1.0,
        },
    )


def _make_report(turns: int = 3) -> PlaytestReport:
    from token_world.playtest.report import AggregateScores

    turn_records = [_make_turn(i, f"action {i}", f"observation {i}") for i in range(turns)]
    aggregate = AggregateScores(
        mechanic_match_rate=1.0,
        observation_groundedness=1.0,
        mutation_count=1.0,
        refusal_rate=1.0,
        action_novelty=1.0,
        composite=1.0,
    )
    return PlaytestReport(
        run_id="test_run_id",
        scenario_file=None,
        turns=turn_records,
        aggregate_scores=aggregate,
        prompts_sha256={},
        duration_ms=100,
    )


def _make_mock_client(response_text: str) -> MagicMock:
    """Return a mock Anthropic client that returns response_text on messages.create()."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=response_text)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client


# ---------------------------------------------------------------------------
# Test 16: build_transcript
# ---------------------------------------------------------------------------


def test_judge_builds_transcript_from_report_turns() -> None:
    """build_transcript returns a string containing each turn's action + observation in order."""
    report = _make_report(turns=3)
    transcript = build_transcript(report)

    assert isinstance(transcript, str)
    for i in range(3):
        assert f"action {i}" in transcript
        assert f"observation {i}" in transcript

    # Turns appear in order (action 0 before action 1 before action 2)
    pos_0 = transcript.index("action 0")
    pos_1 = transcript.index("action 1")
    pos_2 = transcript.index("action 2")
    assert pos_0 < pos_1 < pos_2


# ---------------------------------------------------------------------------
# Test 17: evaluate calls Sonnet with rubric prompt
# ---------------------------------------------------------------------------


def test_judge_calls_sonnet_with_rubric_prompt() -> None:
    """evaluate() calls client.messages.create with model=claude-sonnet-4-5, max_tokens=1024."""
    valid_json = (
        '{"scores": {"coherence": 0.9, "personality_consistency": 0.8, '
        '"world_rule_adherence": 0.7}, "rationale": "Good run."}'
    )
    mock_client = _make_mock_client(valid_json)
    report = _make_report()

    judge_evaluate(report, mock_client)

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args

    # Model and token budget
    assert call_kwargs.kwargs.get("model") == "claude-sonnet-4-5" or (
        len(call_kwargs.args) > 0 and call_kwargs.args[0] == "claude-sonnet-4-5"
    )
    # Easier: check via the keyword args dict
    kwargs = call_kwargs[1] if call_kwargs[1] else {}
    if not kwargs:
        keys = ["model", "max_tokens", "messages"]
        kwargs = {k: v for k, v in zip(keys, call_kwargs[0], strict=False)}

    # The user message content should mention all three rubric dimensions
    messages = mock_client.messages.create.call_args.kwargs.get("messages", [])
    if not messages:
        # Positional — unlikely but defensive
        all_args = str(mock_client.messages.create.call_args)
        assert "coherence" in all_args
        assert "personality_consistency" in all_args
        assert "world_rule_adherence" in all_args
    else:
        user_content = messages[0]["content"]
        assert "coherence" in user_content
        assert "personality_consistency" in user_content
        assert "world_rule_adherence" in user_content

    # max_tokens=1024
    assert mock_client.messages.create.call_args.kwargs.get("max_tokens") == 1024


# ---------------------------------------------------------------------------
# Test 18: evaluate parses valid JSON response
# ---------------------------------------------------------------------------


def test_judge_parses_valid_json_response() -> None:
    """evaluate() parses scores + rationale from a valid JSON Sonnet response."""
    valid_json = (
        '{"scores": {"coherence": 0.9, "personality_consistency": 0.85, '
        '"world_rule_adherence": 0.75}, "rationale": "Agent was consistent."}'
    )
    mock_client = _make_mock_client(valid_json)
    report = _make_report()

    result = judge_evaluate(report, mock_client)

    assert "scores" in result
    assert result["scores"]["coherence"] == pytest.approx(0.9)
    assert result["scores"]["personality_consistency"] == pytest.approx(0.85)
    assert result["scores"]["world_rule_adherence"] == pytest.approx(0.75)
    assert result["rationale"] == "Agent was consistent."
    assert result["model"] == "claude-sonnet-4-5"
    assert "prompt_hash" in result
    assert re.fullmatch(r"[0-9a-f]{64}", result["prompt_hash"])


# ---------------------------------------------------------------------------
# Test 19: evaluate handles malformed response gracefully
# ---------------------------------------------------------------------------


def test_judge_handles_malformed_response_gracefully() -> None:
    """evaluate() returns an error struct on garbled text; does NOT raise."""
    mock_client = _make_mock_client("this is not valid json at all !!!")
    report = _make_report()

    result = judge_evaluate(report, mock_client)

    # Does not raise
    assert isinstance(result, dict)
    assert "error" in result
    assert result["model"] == "claude-sonnet-4-5"
    # Scores field absent or empty on error — not required to be present
    assert result.get("scores") is None or result.get("scores") == {}


# ---------------------------------------------------------------------------
# Test 20: prompt_hash is stable
# ---------------------------------------------------------------------------


def test_judge_prompt_hash_is_stable() -> None:
    """prompt_hash() returns a consistent 64-char SHA-256 hex for the judge prompt template."""
    h1 = prompt_hash()
    h2 = prompt_hash()

    assert h1 == h2
    assert re.fullmatch(r"[0-9a-f]{64}", h1)
