"""Unit tests for the mechanic-author subagent definition (Task 1).

Verifies the ``AgentDefinition`` shape (Opus model, tool whitelist excludes
``Agent`` per Pitfall 5, includes the validation tool + list_mechanics) and
the standalone ``mechanic_author_prompt`` function reused by Plan 04.1-05.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from claude_agent_sdk import AgentDefinition

from token_world.operator import YieldSignal
from token_world.operator.subagent import (
    build_mechanic_author_agent,
    mechanic_author_prompt,
)


def test_mechanic_author_agent_is_agent_definition(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    signal = stub_yield(verb="pickup", actor="alice")
    agent = build_mechanic_author_agent(universe=universe, yield_signal=signal)
    assert isinstance(agent, AgentDefinition)


def test_mechanic_author_model_is_opus(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    signal = stub_yield(verb="pickup", actor="alice")
    agent = build_mechanic_author_agent(universe=universe, yield_signal=signal)
    assert agent.model == "opus", f"D-02 violation: model={agent.model!r}"


def test_mechanic_author_tools_exclude_Agent(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    """Pitfall 5 — subagents must not spawn sub-subagents."""
    signal = stub_yield(verb="pickup", actor="alice")
    agent = build_mechanic_author_agent(universe=universe, yield_signal=signal)
    assert agent.tools is not None
    assert "Agent" not in agent.tools, f"Pitfall 5 violation: tools={agent.tools}"


def test_mechanic_author_tools_include_validate_mechanic(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    signal = stub_yield(verb="pickup", actor="alice")
    agent = build_mechanic_author_agent(universe=universe, yield_signal=signal)
    assert agent.tools is not None
    assert "mcp__validation__validate_mechanic" in agent.tools


def test_mechanic_author_tools_include_list_mechanics(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    signal = stub_yield(verb="pickup", actor="alice")
    agent = build_mechanic_author_agent(universe=universe, yield_signal=signal)
    assert agent.tools is not None
    assert "mcp__token-world__list_mechanics" in agent.tools


def test_mechanic_author_tools_include_basic_io_tools(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    signal = stub_yield(verb="pickup", actor="alice")
    agent = build_mechanic_author_agent(universe=universe, yield_signal=signal)
    assert agent.tools is not None
    for required in ("Read", "Write", "Edit", "Bash", "Glob", "Grep"):
        assert required in agent.tools, f"Missing {required} in {agent.tools}"


def test_mechanic_author_prompt_embeds_yield_json(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    signal = stub_yield(
        verb="meditate",
        actor="alice",
        params={"duration_minutes": 5},
        action_text="alice sits and meditates",
    )
    agent = build_mechanic_author_agent(universe=universe, yield_signal=signal)
    # The full to_json output must be present so the subagent has the signal.
    assert signal.to_json() in agent.prompt


def test_mechanic_author_prompt_embeds_universe_path(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    signal = stub_yield(verb="pickup", actor="alice")
    agent = build_mechanic_author_agent(universe=universe, yield_signal=signal)
    assert str(universe) in agent.prompt


def test_mechanic_author_prompt_mentions_ast_rules(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    signal = stub_yield(verb="pickup", actor="alice")
    agent = build_mechanic_author_agent(universe=universe, yield_signal=signal)
    # Prompt hygiene: the validator is the gate, but the subagent should know
    # the forbidden constructs up front.
    for forbidden in ("eval", "exec", "__import__", "networkx"):
        assert forbidden in agent.prompt, f"Prompt should warn about {forbidden}"


def test_mechanic_author_prompt_function_is_standalone(universe: Path) -> None:
    """04.1-05 will call this directly to scaffold .claude/agents/mechanic-author.md."""
    fake_yield_json = '{"tick_id": "tick_1", "classified_action": {"verb": "x"}}'
    out = mechanic_author_prompt(universe=universe, yield_json=fake_yield_json)
    assert isinstance(out, str)
    assert fake_yield_json in out
    assert str(universe) in out


def test_mechanic_author_description_is_set(
    universe: Path, stub_yield: Callable[..., YieldSignal]
) -> None:
    signal = stub_yield(verb="pickup", actor="alice")
    agent = build_mechanic_author_agent(universe=universe, yield_signal=signal)
    assert agent.description
    assert len(agent.description) > 20, "Description should be substantive"
