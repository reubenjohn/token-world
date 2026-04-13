"""Shared fixtures for resident agent tests."""

from __future__ import annotations

from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Anthropic SDK test doubles (mirrors test_engine/conftest.py pattern)
# ---------------------------------------------------------------------------


class _Usage:
    input_tokens = 100
    output_tokens = 20


class _Block:
    def __init__(self, text: str) -> None:
        self.text = text


class _Response:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]
        self.usage = _Usage()


class _MessagesProxy:
    """Records all .create() calls and returns pre-programmed responses in order."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs: Any) -> _Response:
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError("MockAnthropicClient ran out of responses")
        return _Response(self._responses.pop(0))


class MockAnthropicClient:
    """Test double for anthropic.Anthropic — returns pre-programmed responses in order."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.messages = _MessagesProxy(self._responses)


_VALID_PERSONALITY_JSON = (
    '{"name":"Elara","archetype":"curious wanderer",'
    '"traits":["inquisitive","brave","kind"],'
    '"backstory":"She grew up exploring the misty caves. She seeks truth.",'
    '"speech_style":"speaks in clipped sentences"}'
)

_VALID_HAIKU_SUMMARY = "Alice explored the forest and found a golden key."


@pytest.fixture
def mock_sonnet_personality() -> MockAnthropicClient:
    """Mock Anthropic client that returns a valid personality JSON on first call."""
    return MockAnthropicClient([_VALID_PERSONALITY_JSON])


@pytest.fixture
def mock_haiku_summary() -> MockAnthropicClient:
    """Mock Anthropic client that returns a canned memory summary."""
    return MockAnthropicClient([_VALID_HAIKU_SUMMARY])


@pytest.fixture
def valid_personality_json() -> str:
    return _VALID_PERSONALITY_JSON


@pytest.fixture
def valid_haiku_summary() -> str:
    return _VALID_HAIKU_SUMMARY
