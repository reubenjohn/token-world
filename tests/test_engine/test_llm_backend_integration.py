"""Integration tests for Phase 07.1 — LLMBackend wired into Classifier / Observer / ResidentAgent.

Three layers verified:
  1. Backward compat: existing ``client=FakeClient(...)`` patterns auto-wrap via
     ``__post_init__`` / ``__init__``.
  2. Direct injection: ``backend=FakeBackend(...)`` routes calls through the explicit
     backend.
  3. Env-var dispatch: ``TOKEN_WORLD_BACKEND=claude-cli`` + mocked subprocess.run
     produces identical results to the SDK path — proves the env var threads through
     to the actual LLM-calling classes.
  4. End-to-end CLI fence stripping: a Classifier default-constructed under the
     env var parses fenced JSON via ClaudeCLIBackend -> _strip_markdown_fences.

No real ``claude`` CLI invocation. No real ``anthropic.Anthropic`` instantiation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from token_world.engine.classifier import Classifier
from token_world.engine.llm_backend import (
    AnthropicSDKBackend,
    ClaudeCLIBackend,
)
from token_world.engine.models import VerdictOk
from token_world.engine.observer import Observer, _UsageCapturingSDKBackend
from token_world.mechanic.protocol import CheckResult
from token_world.mechanic.trace import ExecutionTrace, TraceNode
from token_world.resident.agent import ResidentAgent
from token_world.resident.memory import AgentMemory
from token_world.resident.personality import PersonalityBundle

# ---------------------------------------------------------------------------
# Test fakes — purpose-built here to keep the integration file self-contained.
# ---------------------------------------------------------------------------


class _Block:
    def __init__(self, text: str) -> None:
        self.text = text


class _Response:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]


class _MessagesProxy:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _Response:
        self.calls.append(kwargs)
        return _Response(self._response_text)


class FakeClient:
    """Minimal Anthropic-shaped client returning a canned text per call."""

    def __init__(self, response_text: str) -> None:
        self.messages = _MessagesProxy(response_text)


class FakeBackend:
    """LLMBackend test double — records calls + returns a canned text."""

    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.calls: list[dict[str, Any]] = []

    def call(self, *, model: str, system: str, prompt: str, max_tokens: int) -> str:
        self.calls.append(
            {
                "model": model,
                "system": system,
                "prompt": prompt,
                "max_tokens": max_tokens,
            }
        )
        return self.response_text


# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

_OK_RESPONSE = json.dumps(
    {
        "kind": "ok",
        "classified": {
            "verb": "pickup",
            "actor": "alice",
            "target": "rock_1",
            "params": {},
        },
        "confidence": 0.95,
    }
)

_BUNDLE = PersonalityBundle(
    name="Elara",
    archetype="curious wanderer",
    traits=["inquisitive", "brave", "kind"],
    backstory="She seeks truth.",
    speech_style="speaks in clipped sentences",
)


def _simple_projection() -> dict[str, dict[str, Any]]:
    return {
        "alice": {"type": "agent", "properties": {"in": "room_1"}, "edges": []},
        "rock_1": {"type": "entity", "properties": {"type": "rock"}, "edges": []},
    }


def _simple_trace() -> ExecutionTrace:
    root = TraceNode(
        mechanic_id="test",
        actor="alice",
        target="rock_1",
        check_result=CheckResult(passed=True, reasons=["ok"]),
        mutations=[],
        children=[],
    )
    return ExecutionTrace(
        root=root,
        total_mechanics_executed=1,
        max_depth_reached=1,
        truncated=False,
    )


# ---------------------------------------------------------------------------
# Layer 1: Backward compatibility — existing client=FakeClient pattern
# ---------------------------------------------------------------------------


class TestBackwardCompatClientPath:
    """Existing ``client=FakeClient(...)`` auto-wraps into an SDK-backend path."""

    def test_classifier_with_client_only_auto_wraps(self) -> None:
        client = FakeClient(_OK_RESPONSE)
        clf = Classifier(client=client)
        assert clf.backend is not None
        assert isinstance(clf.backend, AnthropicSDKBackend)

        verdict = clf.classify(
            "pick up the rock",
            "alice",
            available_verbs=["pickup"],
            known_node_ids=["alice", "rock_1"],
        )
        assert isinstance(verdict, VerdictOk)
        assert verdict.classified.verb == "pickup"
        # SDK client received exactly one .messages.create() call via the wrapper.
        assert len(client.messages.calls) == 1

    def test_observer_with_client_only_auto_wraps_with_usage_capture(self) -> None:
        client = FakeClient("You see a rock on the floor.")
        obs = Observer(client=client)
        # Observer uses the _UsageCapturingSDKBackend subclass specifically so it
        # can read back token usage from the SDK response (D-24).
        assert isinstance(obs.backend, _UsageCapturingSDKBackend)

        text = obs.synthesize(
            projection=_simple_projection(),
            trace=_simple_trace(),
            actor_id="alice",
            action_text="look",
        )
        assert "rock" in text.lower()
        assert len(client.messages.calls) == 1

    def test_resident_agent_with_client_only_auto_wraps(self, tmp_path: Path) -> None:
        client = FakeClient("look around")
        memory = AgentMemory(tmp_path / "u.db")
        agent = ResidentAgent(
            agent_id="alice",
            session_id="s1",
            personality=_BUNDLE,
            memory=memory,
            client=client,
        )
        # pylint: disable=protected-access — intentional: verifying wrap-or-default.
        assert agent._backend is not None  # type: ignore[union-attr]
        assert isinstance(agent._backend, AnthropicSDKBackend)  # type: ignore[union-attr]

        text = agent.run_turn()
        assert text == "look around"
        assert len(client.messages.calls) == 1
        # Flattening produces a single user-role message containing the prompt.
        messages = client.messages.calls[0]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "What do you do next?" in messages[0]["content"]


# ---------------------------------------------------------------------------
# Layer 2: Direct backend injection — backend=FakeBackend
# ---------------------------------------------------------------------------


class TestDirectBackendInjection:
    """New ``backend=...`` kwarg routes calls through the injected backend directly."""

    def test_classifier_with_backend_routes_through_backend(self) -> None:
        backend = FakeBackend(_OK_RESPONSE)
        clf = Classifier(backend=backend)
        # client stays None; the injected backend is used verbatim (no wrapping).
        assert clf.client is None
        assert clf.backend is backend

        verdict = clf.classify(
            "pick up the rock",
            "alice",
            available_verbs=["pickup"],
            known_node_ids=["alice", "rock_1"],
        )
        assert isinstance(verdict, VerdictOk)
        assert len(backend.calls) == 1
        call = backend.calls[0]
        assert call["model"]  # populated with classifier's _MODEL
        assert "Action text" in call["prompt"]  # user prompt content
        assert call["max_tokens"] == 1024

    def test_observer_with_backend_routes_through_backend(self) -> None:
        backend = FakeBackend("You perceive a rock.")
        obs = Observer(backend=backend)
        assert obs.client is None
        assert obs.backend is backend

        text = obs.synthesize(
            projection=_simple_projection(),
            trace=_simple_trace(),
            actor_id="alice",
            action_text="look",
        )
        assert text == "You perceive a rock."
        assert len(backend.calls) == 1
        # Direct-injection path: token counters remain 0 per CONTEXT D-07
        # (FakeBackend does not expose _last_usage; Observer leaves counters untouched).
        assert obs.last_input_tokens == 0
        assert obs.last_output_tokens == 0

    def test_resident_agent_with_backend_routes_through_backend(self, tmp_path: Path) -> None:
        backend = FakeBackend("walk north")
        memory = AgentMemory(tmp_path / "u.db")
        agent = ResidentAgent(
            agent_id="alice",
            session_id="s1",
            personality=_BUNDLE,
            memory=memory,
            backend=backend,
        )
        assert agent._client is None
        assert agent._backend is backend

        text = agent.run_turn()
        assert text == "walk north"
        assert len(backend.calls) == 1
        # Flattened prompt includes the final "What do you do next?" prompt.
        assert "What do you do next?" in backend.calls[0]["prompt"]
        # And the system prompt contains the character identity.
        assert "Elara" in backend.calls[0]["system"]


# ---------------------------------------------------------------------------
# Layer 3: Env-var dispatch — TOKEN_WORLD_BACKEND=claude-cli + mocked subprocess
# ---------------------------------------------------------------------------


class TestEnvVarDispatchToClaudeCli:
    """``TOKEN_WORLD_BACKEND=claude-cli`` threads through to LLM-calling classes.

    All tests patch ``subprocess.run`` to avoid real ``claude`` invocations.
    """

    def test_classifier_defaults_to_cli_backend_under_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TOKEN_WORLD_BACKEND", "claude-cli")
        mock_result = MagicMock()
        mock_result.stdout = _OK_RESPONSE  # CLI returns unfenced JSON in this test
        with patch(
            "token_world.engine.llm_backend.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            clf = Classifier()  # no client, no backend -> get_backend() -> CLI
            assert isinstance(clf.backend, ClaudeCLIBackend)

            verdict = clf.classify(
                "pick up the rock",
                "alice",
                available_verbs=["pickup"],
                known_node_ids=["alice", "rock_1"],
            )
            assert isinstance(verdict, VerdictOk)

        mock_run.assert_called_once()
        argv = mock_run.call_args[0][0]
        assert argv[0] == "claude"
        assert "--model" in argv
        assert "-p" in argv

    def test_observer_defaults_to_cli_backend_under_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TOKEN_WORLD_BACKEND", "claude-cli")
        mock_result = MagicMock()
        mock_result.stdout = "You perceive the room."
        with patch(
            "token_world.engine.llm_backend.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            obs = Observer()
            assert isinstance(obs.backend, ClaudeCLIBackend)

            text = obs.synthesize(
                projection=_simple_projection(),
                trace=_simple_trace(),
                actor_id="alice",
                action_text="look",
            )
            assert text == "You perceive the room."

        mock_run.assert_called_once()

    def test_resident_agent_defaults_to_cli_backend_under_env_var(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setenv("TOKEN_WORLD_BACKEND", "claude-cli")
        mock_result = MagicMock()
        mock_result.stdout = "look around"
        with patch(
            "token_world.engine.llm_backend.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            memory = AgentMemory(tmp_path / "u.db")
            agent = ResidentAgent(
                agent_id="alice",
                session_id="s1",
                personality=_BUNDLE,
                memory=memory,
            )
            assert isinstance(agent._backend, ClaudeCLIBackend)

            text = agent.run_turn()
            assert text == "look around"

        mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# Layer 4: CLI fence stripping end-to-end via Classifier
# ---------------------------------------------------------------------------


class TestCliFenceStrippingEndToEnd:
    """Simulate real CLI behaviour: ``claude -p`` wraps JSON in ``\u0060\u0060\u0060json`` fences.

    ``ClaudeCLIBackend._strip_markdown_fences`` must remove them before the
    classifier's JSON parser sees the payload.
    """

    def test_classifier_strips_cli_fences_before_parsing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TOKEN_WORLD_BACKEND", "claude-cli")
        fenced_response = f"```json\n{_OK_RESPONSE}\n```"
        mock_result = MagicMock()
        mock_result.stdout = fenced_response
        with patch(
            "token_world.engine.llm_backend.subprocess.run",
            return_value=mock_result,
        ):
            clf = Classifier()
            verdict = clf.classify(
                "pick up the rock",
                "alice",
                available_verbs=["pickup"],
                known_node_ids=["alice", "rock_1"],
            )
            # Parsed cleanly despite the fences: backend stripped them.
            assert isinstance(verdict, VerdictOk)
            assert verdict.classified.verb == "pickup"

    def test_classifier_with_plain_fences_also_strips(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Also cover the ``\u0060\u0060\u0060`` (no language tag) fence shape."""
        monkeypatch.setenv("TOKEN_WORLD_BACKEND", "claude-cli")
        fenced_response = f"```\n{_OK_RESPONSE}\n```"
        mock_result = MagicMock()
        mock_result.stdout = fenced_response
        with patch(
            "token_world.engine.llm_backend.subprocess.run",
            return_value=mock_result,
        ):
            clf = Classifier()
            verdict = clf.classify(
                "pick up the rock",
                "alice",
                available_verbs=["pickup"],
                known_node_ids=["alice", "rock_1"],
            )
            assert isinstance(verdict, VerdictOk)


# ---------------------------------------------------------------------------
# Layer 5: Explicit backend wins over env var (precedence check)
# ---------------------------------------------------------------------------


class TestExplicitBackendOverridesEnvVar:
    """Injected ``backend=`` or ``client=`` always wins over ``TOKEN_WORLD_BACKEND``."""

    def test_explicit_backend_wins_over_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TOKEN_WORLD_BACKEND", "claude-cli")
        # Even with the env var set, explicit backend injection takes precedence.
        # No subprocess patch needed — the CLI backend must not be instantiated.
        backend = FakeBackend(_OK_RESPONSE)
        clf = Classifier(backend=backend)
        assert clf.backend is backend  # NOT a ClaudeCLIBackend

        verdict = clf.classify(
            "pick up the rock",
            "alice",
            available_verbs=["pickup"],
            known_node_ids=["alice", "rock_1"],
        )
        assert isinstance(verdict, VerdictOk)
        assert len(backend.calls) == 1

    def test_explicit_client_wins_over_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TOKEN_WORLD_BACKEND", "claude-cli")
        # Client-only auto-wrap should NOT fall through to the CLI dispatch.
        client = FakeClient(_OK_RESPONSE)
        clf = Classifier(client=client)
        assert isinstance(clf.backend, AnthropicSDKBackend)
        assert not isinstance(clf.backend, ClaudeCLIBackend)

        verdict = clf.classify(
            "pick up the rock",
            "alice",
            available_verbs=["pickup"],
            known_node_ids=["alice", "rock_1"],
        )
        assert isinstance(verdict, VerdictOk)
        assert len(client.messages.calls) == 1
