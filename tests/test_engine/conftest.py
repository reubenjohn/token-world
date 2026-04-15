"""Shared test fixtures for engine tests.

Provides:
- MockAnthropicClient / _MessagesProxy: test doubles for the Anthropic SDK
- mock_anthropic_haiku: canned classifier-ok response
- mock_anthropic_sonnet: canned observer response
- tmp_universe: temporary scaffolded universe path with minimum config
- kg: blank KnowledgeGraph for engine tests
- seeded_ctx: MechanicContext with deterministic RNG seed
"""

from __future__ import annotations

from pathlib import Path

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext

# ---------------------------------------------------------------------------
# Anthropic SDK test double
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

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError("MockAnthropicClient ran out of responses")
        return _Response(self._responses.pop(0))


class MockAnthropicClient:
    """Test double for anthropic.Anthropic — returns pre-programmed responses in order."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.messages = _MessagesProxy(self._responses)
        self.calls: list[dict] = []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_anthropic_haiku() -> MockAnthropicClient:
    """Mock Anthropic client with canned classifier-ok response."""
    return MockAnthropicClient(
        [
            '{"kind":"ok","actions":[{"verb":"pickup","actor":"alice",'
            '"target":"rock_1","params":{}}],"confidence":0.95}'
        ]
    )


@pytest.fixture
def mock_anthropic_sonnet() -> MockAnthropicClient:
    """Mock Anthropic client with canned observer response."""
    return MockAnthropicClient(
        ["You bend down and pick up the rock. It is cold and rough in your hand."]
    )


@pytest.fixture
def tmp_universe(tmp_path: Path) -> Path:
    """Temp universe folder with minimum scaffolding for engine tests.

    Creates the required directory structure and universe.yaml so
    load_engine_config() returns a valid EngineConfig.
    """
    (tmp_path / "mechanics").mkdir()
    (tmp_path / "diagnostics").mkdir()
    (tmp_path / "tick_summaries").mkdir()
    (tmp_path / "universe.yaml").write_text(
        "universe_seed: 424242\nengine:\n  max_chain_depth: 10\n  classifier_min_confidence: 0.6\n",
        encoding="utf-8",
    )
    (tmp_path / "conservation.yaml").write_text("conserved_properties: []\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def kg() -> KnowledgeGraph:
    """Blank in-memory KnowledgeGraph for engine tests."""
    return KnowledgeGraph(db_path=None)


@pytest.fixture
def seeded_ctx(kg: KnowledgeGraph) -> MechanicContext:
    """MechanicContext with deterministic RNG seed (universe_seed=424242, tick_id=tick_1)."""
    kg.add_node("alice", node_type="agent")
    kg.add_node("rock_1", node_type="entity")
    return MechanicContext(
        kg,
        actor="alice",
        target="rock_1",
        tick_id="tick_1",
        universe_seed=424242,
    )
