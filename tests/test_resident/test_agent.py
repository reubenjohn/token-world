"""Tests for ResidentAgent (Task 4 TDD)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_resident.conftest import MockAnthropicClient
from token_world.graph import KnowledgeGraph
from token_world.resident.agent import ResidentAgent, create_agent_node
from token_world.resident.memory import AgentMemory
from token_world.resident.personality import PersonalityBundle

# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

_BUNDLE = PersonalityBundle(
    name="Elara",
    archetype="curious wanderer",
    traits=["inquisitive", "brave", "kind"],
    backstory="She grew up exploring the misty caves. She seeks truth.",
    speech_style="speaks in clipped sentences",
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "universe.db"


@pytest.fixture
def memory(db_path: Path) -> AgentMemory:
    return AgentMemory(db_path)


def _make_agent(
    client: MockAnthropicClient,
    memory: AgentMemory,
    *,
    world_rules: str = "RULES",
    model: str = "claude-haiku-4-5",
    session_id: str = "session-1",
    agent_id: str = "alice",
) -> ResidentAgent:
    return ResidentAgent(
        agent_id=agent_id,
        session_id=session_id,
        personality=_BUNDLE,
        memory=memory,
        client=client,
        model=model,
        world_rules=world_rules,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_build_system_prompt_includes_personality_and_rules(memory: AgentMemory) -> None:
    """system_prompt_text() includes world rules, all personality fields, static instruction."""
    client = MockAnthropicClient(["look around"])
    agent = _make_agent(client, memory, world_rules="RULES")
    prompt = agent.system_prompt_text()

    assert "RULES" in prompt
    assert "Elara" in prompt
    assert "curious wanderer" in prompt
    # All traits must appear
    for trait in _BUNDLE.traits:
        assert trait in prompt
    assert _BUNDLE.backstory in prompt
    assert _BUNDLE.speech_style in prompt
    # Static instruction block
    assert "Issue actions as short imperative sentences" in prompt
    # No turn history in system prompt
    assert "look around" not in prompt


def test_run_turn_calls_haiku_and_returns_stripped_text(memory: AgentMemory) -> None:
    """run_turn() calls create with default model and returns stripped action text."""
    client = MockAnthropicClient(["  look around  \n"])
    agent = _make_agent(client, memory)

    action = agent.run_turn()

    assert action == "look around"
    assert len(client.messages.calls) == 1
    call = client.messages.calls[0]
    assert call["model"] == "claude-haiku-4-5"
    assert call["system"]  # non-empty system prompt
    assert isinstance(call["messages"], list)
    assert len(call["messages"]) >= 1


def test_run_turn_uses_rolling_context_from_memory(db_path: Path) -> None:
    """run_turn builds alternating user/assistant turns from memory context."""
    import sqlite3

    # Pre-create session in DB
    with sqlite3.connect(str(db_path)) as conn:
        from token_world.resident.memory import ensure_memory_tables

        ensure_memory_tables(conn)
        conn.execute(
            "INSERT INTO agent_sessions (session_id, agent_id, started_at) VALUES (?,?,?)",
            ("session-1", "alice", "2026-01-01T00:00:00"),
        )

    memory = AgentMemory(db_path)
    for i in range(5):
        memory.store_turn("alice", "session-1", i, f"a{i + 1}", f"o{i + 1}", str(i))

    client = MockAnthropicClient(["explore north"])
    agent = _make_agent(client, memory)
    agent.run_turn()

    call = client.messages.calls[0]
    messages = call["messages"]
    # Should have alternating user/assistant pairs + final user prompt
    assert len(messages) >= 3  # at least 1 pair + final user turn
    # First pair: user=action, assistant=observation
    assert messages[0]["role"] == "user"
    assert "a1" in messages[0]["content"]
    assert messages[1]["role"] == "assistant"
    assert "o1" in messages[1]["content"]
    # Last message is user asking for next action
    assert messages[-1]["role"] == "user"


def test_run_turn_includes_memory_summary_when_present(db_path: Path) -> None:
    """run_turn prepends memory summary to first user message when session has one."""
    import sqlite3

    with sqlite3.connect(str(db_path)) as conn:
        from token_world.resident.memory import ensure_memory_tables

        ensure_memory_tables(conn)
        conn.execute(
            "INSERT INTO agent_sessions (session_id, agent_id, started_at, memory_summary) "
            "VALUES (?,?,?,?)",
            ("session-1", "alice", "2026-01-01T00:00:00", "You found a key earlier."),
        )

    memory = AgentMemory(db_path)
    client = MockAnthropicClient(["open the door"])
    agent = _make_agent(client, memory)
    agent.run_turn()

    messages = client.messages.calls[0]["messages"]
    # Summary should appear in the first message
    first_content = messages[0]["content"]
    assert "You found a key earlier." in first_content


def test_run_turn_respects_configured_model(memory: AgentMemory) -> None:
    """run_turn uses configured model override (D-02)."""
    client = MockAnthropicClient(["pick up the sword"])
    agent = _make_agent(client, memory, model="claude-sonnet-4-5")

    agent.run_turn()

    assert client.messages.calls[0]["model"] == "claude-sonnet-4-5"


# ---------------------------------------------------------------------------
# WR-03 regression: empty LLM response raises clear ValueError, not IndexError
# ---------------------------------------------------------------------------


def test_run_turn_raises_on_empty_content_list(memory: AgentMemory) -> None:
    """WR-03: run_turn raises ValueError with clear message on empty response.content."""
    from unittest.mock import MagicMock

    # Build a fake response with an empty content list
    fake_response = MagicMock()
    fake_response.content = []

    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    agent = _make_agent(fake_client, memory)

    with pytest.raises(ValueError, match="[Ee]mpty"):
        agent.run_turn()


def test_agent_personality_stored_as_dict_property_on_graph_node(tmp_path: Path) -> None:
    """create_agent_node stores personality as a dict property (JSON-serializable per CLAUDE.md)."""
    kg = KnowledgeGraph(db_path=tmp_path / "test.db")

    create_agent_node(kg, "alice", _BUNDLE)

    # Node must exist as "agent" type with personality as a dict (not str)
    props = kg.query("alice")
    assert isinstance(props, dict)
    personality = props.get("personality")
    assert isinstance(personality, dict)
    assert personality["name"] == "Elara"
    assert personality["archetype"] == "curious wanderer"
    assert personality["traits"] == ["inquisitive", "brave", "kind"]
