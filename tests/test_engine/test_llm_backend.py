"""Unit tests for llm_backend module (Phase 07.1 Plan 01).

Covers the pluggable LLM backend abstraction:
- LLMBackend Protocol (one method: call(*, model, system, prompt, max_tokens) -> str)
- AnthropicSDKBackend: wraps raw anthropic.Anthropic client; DOES NOT strip fences (D-03)
- _strip_markdown_fences(): idempotent helper covering ```json and plain ``` wrappings
- get_backend(): env-dispatched factory reading TOKEN_WORLD_BACKEND (D-08)

ClaudeCLIBackend tests live alongside here (added in Task 2). All ClaudeCLIBackend
tests mock subprocess.run — zero real CLI invocations.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from token_world.engine.llm_backend import (
    AnthropicSDKBackend,
    ClaudeCLIBackend,
    LLMBackend,
    _strip_markdown_fences,
    get_backend,
)

# ---- Test fakes for the Anthropic SDK path ----


class _Block:
    def __init__(self, text: str) -> None:
        self.text = text


class _Response:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]


class _EmptyResponse:
    content: list[_Block] = []


class _MessagesProxy:
    def __init__(self, response: Any) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self._response


class FakeClient:
    def __init__(self, response: Any) -> None:
        self.messages = _MessagesProxy(response)


# ---- _strip_markdown_fences edge cases ----


class TestStripMarkdownFences:
    def test_strips_json_fences(self) -> None:
        assert _strip_markdown_fences('```json\n{"a":1}\n```') == '{"a":1}'

    def test_strips_plain_fences(self) -> None:
        assert _strip_markdown_fences("```\nplain text\n```") == "plain text"

    def test_unfenced_passthrough(self) -> None:
        assert _strip_markdown_fences("plain text") == "plain text"

    def test_strips_outer_whitespace_before_detect(self) -> None:
        assert _strip_markdown_fences("   plain text   ") == "plain text"

    def test_only_opening_fence_no_newline_returns_input(self) -> None:
        # Locked shape: if no newline after ```, return text verbatim after strip
        assert _strip_markdown_fences("```json no newline") == "```json no newline"

    def test_opening_fence_no_closing_fence(self) -> None:
        # Strip leading ```\n; no trailing ``` to remove; .strip() trims final whitespace
        assert _strip_markdown_fences("```\nopen but no close") == "open but no close"

    def test_empty_string_passthrough(self) -> None:
        assert _strip_markdown_fences("") == ""

    def test_idempotent_on_already_stripped(self) -> None:
        # Second pass on clean text yields same clean text
        clean = _strip_markdown_fences('```json\n{"a":1}\n```')
        assert _strip_markdown_fences(clean) == '{"a":1}'


# ---- AnthropicSDKBackend behavior ----


class TestAnthropicSDKBackend:
    def test_routes_call_args_through_client(self) -> None:
        client = FakeClient(_Response("hello"))
        backend = AnthropicSDKBackend(client)
        result = backend.call(
            model="claude-haiku-4-5-20251001",
            system="SYSTEM",
            prompt="user prompt",
            max_tokens=512,
        )
        assert result == "hello"
        assert len(client.messages.calls) == 1
        kw = client.messages.calls[0]
        assert kw["model"] == "claude-haiku-4-5-20251001"
        assert kw["max_tokens"] == 512
        assert kw["system"] == "SYSTEM"
        assert kw["messages"] == [{"role": "user", "content": "user prompt"}]

    def test_returns_empty_string_when_response_content_empty(self) -> None:
        client = FakeClient(_EmptyResponse())
        backend = AnthropicSDKBackend(client)
        result = backend.call(model="m", system="s", prompt="p", max_tokens=1)
        assert result == ""

    def test_does_not_strip_markdown_fences(self) -> None:
        # D-03: SDK backend MUST NOT strip fences — CLI-path-only behavior
        client = FakeClient(_Response('```json\n{"a":1}\n```'))
        backend = AnthropicSDKBackend(client)
        result = backend.call(model="m", system="s", prompt="p", max_tokens=1)
        assert result == '```json\n{"a":1}\n```'  # fences preserved


# ---- get_backend() env-var dispatch ----


class TestGetBackendEnvDispatch:
    def test_claude_cli_env_returns_cli_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TOKEN_WORLD_BACKEND", "claude-cli")
        backend = get_backend()
        assert isinstance(backend, ClaudeCLIBackend)

    def test_anthropic_sdk_env_returns_sdk_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TOKEN_WORLD_BACKEND", "anthropic-sdk")
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value = MagicMock()
            backend = get_backend()
        assert isinstance(backend, AnthropicSDKBackend)

    def test_unset_env_returns_sdk_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TOKEN_WORLD_BACKEND", raising=False)
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value = MagicMock()
            backend = get_backend()
        assert isinstance(backend, AnthropicSDKBackend)

    def test_empty_string_env_returns_sdk_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TOKEN_WORLD_BACKEND", "")
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value = MagicMock()
            backend = get_backend()
        assert isinstance(backend, AnthropicSDKBackend)

    def test_uppercase_normalized_to_cli(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TOKEN_WORLD_BACKEND", "CLAUDE-CLI")
        backend = get_backend()
        assert isinstance(backend, ClaudeCLIBackend)

    def test_padded_whitespace_normalized_to_cli(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TOKEN_WORLD_BACKEND", "  claude-cli  ")
        backend = get_backend()
        assert isinstance(backend, ClaudeCLIBackend)

    def test_unknown_value_falls_back_to_sdk(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # D-08: any value except "claude-cli" (after strip+lower) falls through to SDK
        monkeypatch.setenv("TOKEN_WORLD_BACKEND", "some-other-backend")
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value = MagicMock()
            backend = get_backend()
        assert isinstance(backend, AnthropicSDKBackend)


# ---- Protocol conformance ----


class TestProtocolConformance:
    def test_anthropic_sdk_backend_is_llm_backend(self) -> None:
        # Structural typing: AnthropicSDKBackend must satisfy LLMBackend Protocol
        client = FakeClient(_Response("x"))
        backend: LLMBackend = AnthropicSDKBackend(client)
        assert hasattr(backend, "call")

    def test_claude_cli_backend_is_llm_backend(self) -> None:
        backend: LLMBackend = ClaudeCLIBackend()
        assert hasattr(backend, "call")
