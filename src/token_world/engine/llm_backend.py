"""Pluggable LLM backend abstraction for Phase 07.1 (D-01, D-03, D-04, D-05, D-06, D-08, D-09).

Two implementations sharing one Protocol:
- :class:`AnthropicSDKBackend`: wraps ``anthropic.Anthropic`` raw SDK (default path).
- :class:`ClaudeCLIBackend`: ``subprocess.run`` wrapper around
  ``claude --model <id> -p <prompt>``.

Dispatch via the ``TOKEN_WORLD_BACKEND`` env var (D-08):
- ``"claude-cli"`` (case-insensitive, whitespace-stripped) -> :class:`ClaudeCLIBackend`
- anything else (empty, unset, or any other string) -> ``AnthropicSDKBackend(Anthropic())``

Markdown fence stripping (D-03) is CLI-path only: ``claude -p`` wraps JSON in
``\u0060\u0060\u0060json`` fences even when told not to (validated 2026-04-14 live probe).
The SDK path returns unfenced text directly and must not strip.

Other locked decisions from the CONTEXT:
- D-04 — no model-alias translation; full IDs pass through verbatim.
- D-05 — ``subprocess.run(..., timeout=120, check=True, capture_output=True, text=True)``;
  ``CalledProcessError`` propagates to callers.
- D-06 — ``["claude", ...]`` relies on PATH; no ``shutil.which`` lookup.
- D-09 — synchronous ``subprocess.run`` only; no ``Popen``, no ``asyncio.subprocess``.

The ``anthropic.Anthropic`` import is done lazily inside :func:`get_backend` so that
(a) environments without the SDK installed can still import this module, and
(b) tests can patch ``anthropic.Anthropic`` before the factory call resolves it
(preserves the Phase 5 D-01 "no module-load instantiation" pattern).
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Protocol


class LLMBackend(Protocol):
    """Protocol every LLM backend must implement.

    Exactly one method: :meth:`call` — keyword-only, ``str`` return. Callers pass
    ``model``, ``system``, ``prompt``, and ``max_tokens`` and receive a
    unified plain-text response (no fences, no wrapper objects).
    """

    def call(self, *, model: str, system: str, prompt: str, max_tokens: int) -> str: ...


def _strip_markdown_fences(text: str) -> str:
    """Strip a single leading/trailing Markdown fence block from ``text``.

    Handles both ``\u0060\u0060\u0060json\\n...\\n\u0060\u0060\u0060`` and plain
    ``\u0060\u0060\u0060\\n...\\n\u0060\u0060\u0060`` wrappings. If ``text`` does
    not start with ``\u0060\u0060\u0060`` after ``.strip()`` it is returned as-is.
    If the opening fence has no newline after it, the text is returned verbatim
    (defensive against the ``\u0060\u0060\u0060json no newline`` edge case).
    Any missing closing fence is tolerated — leading content only is returned.

    Idempotent on already-stripped text (D-03).
    """
    text = text.strip()
    if not text.startswith("```"):
        return text
    first_newline = text.find("\n")
    if first_newline == -1:
        return text
    text = text[first_newline + 1 :]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


class AnthropicSDKBackend:
    """Raw Anthropic SDK backend — the default path.

    Wraps an injected ``anthropic.Anthropic`` client (or a test fake exposing
    ``.messages.create``). The SDK already returns unfenced text, so this
    backend does NOT invoke :func:`_strip_markdown_fences` (D-03).
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def call(self, *, model: str, system: str, prompt: str, max_tokens: int) -> str:
        resp = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        # Matches existing classifier/observer behaviour: empty content -> "" (no raise).
        if not resp.content:
            return ""
        text: str = resp.content[0].text
        return text


class ClaudeCLIBackend:
    """``claude`` CLI subprocess backend — zero-API-cost path for UAT.

    Invokes ``claude --model <model> -p <system + "\\n\\n" + prompt>`` via
    :func:`subprocess.run` (D-09; synchronous). ``max_tokens`` is advisory
    only — the ``claude`` CLI does not accept a ``--max-tokens`` argument, so
    the parameter is NOT forwarded to argv.

    Failure posture (D-05 loud failure):
    - Non-zero exit codes raise :class:`subprocess.CalledProcessError` (propagated).
    - Timeouts raise :class:`subprocess.TimeoutExpired` (propagated).
    - Missing ``claude`` on PATH raises :class:`FileNotFoundError` (propagated; D-06).

    Output post-processing:
    - :func:`_strip_markdown_fences` is applied to ``stdout`` before return (D-03).
    """

    def __init__(self, timeout: int = 120) -> None:
        self._timeout = timeout

    def call(self, *, model: str, system: str, prompt: str, max_tokens: int) -> str:
        # max_tokens is advisory only — CLI does not accept a max-tokens argument.
        full = f"{system}\n\n{prompt}"
        result = subprocess.run(
            ["claude", "--model", model, "-p", full],
            capture_output=True,
            text=True,
            timeout=self._timeout,
            check=True,
        )
        return _strip_markdown_fences(result.stdout)


def get_backend() -> LLMBackend:
    """Return the LLM backend selected by ``TOKEN_WORLD_BACKEND`` (D-08).

    - ``TOKEN_WORLD_BACKEND=claude-cli`` (case-insensitive, whitespace-stripped)
      -> :class:`ClaudeCLIBackend` with default 120s timeout.
    - anything else (empty, unset, or any other string)
      -> ``AnthropicSDKBackend(Anthropic())``.

    The ``anthropic.Anthropic`` import is lazy so the module remains importable
    in environments without the SDK installed and so tests can patch
    ``anthropic.Anthropic`` before factory resolution.
    """
    backend_env = os.environ.get("TOKEN_WORLD_BACKEND", "").strip().lower()
    if backend_env == "claude-cli":
        return ClaudeCLIBackend()
    from anthropic import Anthropic

    return AnthropicSDKBackend(Anthropic())
