"""Tests for the Sonnet-backed Observer (D-15 hard-grounding, Plan 05-05).

Must-haves per plan:
  truths:
    1. synthesize() returns a non-empty grounded text string
    2. System prompt contains the literal phrase "use only facts that appear in
       the provided state"
    3. Empty projection → darkness fallback without LLM call
    4. Actor-only projection (no edges, ≤2 properties) → darkness fallback
    5. refusal_narrative != None → returned verbatim
    6. refusal_narrative != None → LLM not called
    7. DiagnosticsSink tick context → write_observation called exactly once per
       synthesize()
    8. No tick context → no AttributeError
    9. Token usage captured after call (last_input_tokens / last_output_tokens)
   10. Substring grounding: output only references node IDs present in projection
       (Phase-5 weak check per D-15 + pitfall #6 — full rubric deferred to Phase
       6 TEST-04)
   11. chain_truncated=True → "Time blurs" or "cascade" appears in the user
       prompt sent to the LLM (D-17b closure)

  falsehoods:
    A. anthropic.Anthropic() is NOT called at module import time
    B. Observer never reads KnowledgeGraph directly
    C. synthesize() never returns empty string
    D. client.messages.create is called at most once per synthesize() call
"""

from __future__ import annotations

import re

import pytest

from token_world.engine.observer import _SYSTEM_PROMPT, Observer
from token_world.engine.visibility import VisibilityProjector
from token_world.graph import KnowledgeGraph
from token_world.mechanic.protocol import CheckResult
from token_world.mechanic.trace import ExecutionTrace, TraceNode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simple_trace(truncated: bool = False) -> ExecutionTrace:
    """Build a minimal valid ExecutionTrace for tests that don't care about trace content."""
    root = TraceNode(
        mechanic_id="test_mechanic",
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
        truncated=truncated,
    )


class _FakeTickDiagnostics:
    """Minimal fake DiagnosticsSink that records write_observation calls."""

    def __init__(self) -> None:
        self.observation_calls: list[dict] = []

    def write_observation(self, *, prompt: str, response: str, parsed: dict) -> None:
        self.observation_calls.append({"prompt": prompt, "response": response, "parsed": parsed})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_kg() -> KnowledgeGraph:
    """KnowledgeGraph with alice in a room with rock_1."""
    kg = KnowledgeGraph(db_path=None)
    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity", illumination=1.0)
    kg.add_node("rock_1", node_type="entity", weight=5)
    kg.add_edge("alice", "room_1", type="location")
    kg.add_edge("room_1", "rock_1", type="contains")
    return kg


# ---------------------------------------------------------------------------
# Truth 1: synthesize() returns non-empty text for a normal projection
# ---------------------------------------------------------------------------


def test_synthesize_returns_nonempty_text_for_normal_projection(mock_anthropic_sonnet, simple_kg):
    """Observer returns non-empty, non-whitespace text from a normal projection."""
    projector = VisibilityProjector(simple_kg)
    observer = Observer(client=mock_anthropic_sonnet)
    result = observer.synthesize(
        projection=projector.project_for("alice"),
        trace=_simple_trace(),
        actor_id="alice",
        action_text="look around",
    )
    assert result and result.strip(), "synthesize() must return non-empty text"
    assert mock_anthropic_sonnet.messages.calls, "LLM must be called for a normal projection"


# ---------------------------------------------------------------------------
# Truth 2: System prompt hard-grounding constraint phrase
# ---------------------------------------------------------------------------


def test_system_prompt_contains_grounding_phrase():
    """System prompt must contain the D-15 hard-grounding literal phrase."""
    assert "use only facts that appear in the provided state" in _SYSTEM_PROMPT, (
        "D-15 requires the exact phrase 'use only facts that appear in the provided state' "
        "in the observer system prompt."
    )


# ---------------------------------------------------------------------------
# Truth 3: Empty projection → darkness fallback, no LLM call
# ---------------------------------------------------------------------------


def test_empty_projection_returns_darkness_fallback_no_llm_call(mock_anthropic_sonnet):
    """An empty projection dict must return the darkness fallback without calling the LLM."""
    observer = Observer(client=mock_anthropic_sonnet)
    result = observer.synthesize(
        projection={},
        trace=_simple_trace(),
        actor_id="alice",
        action_text="look around",
    )
    assert result, "Fallback must be non-empty"
    assert "nothing" in result.lower() or "dark" in result.lower() or "silence" in result.lower(), (
        f"Darkness fallback expected but got: {result!r}"
    )
    assert not mock_anthropic_sonnet.messages.calls, "LLM must NOT be called for empty projection"


# ---------------------------------------------------------------------------
# Truth 4: Actor-only projection → darkness fallback
# ---------------------------------------------------------------------------


def test_actor_only_projection_returns_darkness_fallback(mock_anthropic_sonnet):
    """Single-actor projection with no edges and ≤2 properties is effectively empty."""
    observer = Observer(client=mock_anthropic_sonnet)
    # Minimal actor-only projection: no edges, just type property
    projection = {
        "alice": {
            "type": "agent",
            "properties": {"type": "agent"},
            "edges": [],
        }
    }
    result = observer.synthesize(
        projection=projection,
        trace=_simple_trace(),
        actor_id="alice",
        action_text="look around",
    )
    assert result, "Fallback must be non-empty"
    assert not mock_anthropic_sonnet.messages.calls, (
        "LLM must NOT be called for actor-only projection"
    )


# ---------------------------------------------------------------------------
# Truth 5: refusal_narrative returned verbatim
# ---------------------------------------------------------------------------


def test_refusal_narrative_returned_verbatim(mock_anthropic_sonnet, simple_kg):
    """refusal_narrative != None must be returned exactly as provided (no rewriting)."""
    observer = Observer(client=mock_anthropic_sonnet)
    custom_narrative = "You try to open the door but it is locked from the inside."
    result = observer.synthesize(
        projection=VisibilityProjector(simple_kg).project_for("alice"),
        trace=_simple_trace(),
        refusal_narrative=custom_narrative,
        actor_id="alice",
        action_text="open door",
    )
    assert result == custom_narrative, (
        f"Refusal narrative must be returned verbatim. Got: {result!r}"
    )


# ---------------------------------------------------------------------------
# Truth 6: refusal_narrative → LLM not called
# ---------------------------------------------------------------------------


def test_refusal_narrative_skips_llm_call(mock_anthropic_sonnet, simple_kg):
    """When refusal_narrative is provided the LLM must not be invoked."""
    observer = Observer(client=mock_anthropic_sonnet)
    observer.synthesize(
        projection=VisibilityProjector(simple_kg).project_for("alice"),
        trace=_simple_trace(),
        refusal_narrative="You are refused.",
        actor_id="alice",
        action_text="do something",
    )
    assert not mock_anthropic_sonnet.messages.calls, (
        "LLM must NOT be called when refusal_narrative is set"
    )


# ---------------------------------------------------------------------------
# Truth 7: Diagnostics written when tick_ctx provided
# ---------------------------------------------------------------------------


def test_diagnostics_written_when_tick_ctx_provided(mock_anthropic_sonnet, simple_kg):
    """Exactly one write_observation call per synthesize() when tick_diag_ctx is set."""
    observer = Observer(client=mock_anthropic_sonnet)
    ctx = _FakeTickDiagnostics()
    observer.synthesize(
        projection=VisibilityProjector(simple_kg).project_for("alice"),
        trace=_simple_trace(),
        actor_id="alice",
        action_text="look around",
        tick_diag_ctx=ctx,
    )
    assert len(ctx.observation_calls) == 1, (
        f"Expected exactly 1 write_observation call; got {len(ctx.observation_calls)}"
    )


def test_diagnostics_written_for_refusal_when_tick_ctx_provided(simple_kg):
    """Refusal short-circuit still calls write_observation once when ctx is set."""
    # Use a fresh mock with no pre-programmed responses (crash if called)
    from tests.test_engine.conftest import MockAnthropicClient

    observer = Observer(client=MockAnthropicClient([]))
    ctx = _FakeTickDiagnostics()
    observer.synthesize(
        projection=VisibilityProjector(simple_kg).project_for("alice"),
        trace=_simple_trace(),
        refusal_narrative="Refused.",
        actor_id="alice",
        action_text="do x",
        tick_diag_ctx=ctx,
    )
    assert len(ctx.observation_calls) == 1, "Refusal path must also call write_observation"


# ---------------------------------------------------------------------------
# Truth 8: No tick context → no AttributeError
# ---------------------------------------------------------------------------


def test_diagnostics_skipped_when_tick_ctx_none(mock_anthropic_sonnet, simple_kg):
    """synthesize() with tick_diag_ctx=None must not raise any AttributeError."""
    observer = Observer(client=mock_anthropic_sonnet)
    # Should not raise
    result = observer.synthesize(
        projection=VisibilityProjector(simple_kg).project_for("alice"),
        trace=_simple_trace(),
        actor_id="alice",
        action_text="look around",
        tick_diag_ctx=None,
    )
    assert result  # sanity


# ---------------------------------------------------------------------------
# Truth 9: Token usage captured after call
# ---------------------------------------------------------------------------


def test_token_usage_captured_after_call(mock_anthropic_sonnet, simple_kg):
    """last_input_tokens / last_output_tokens must be set from response.usage."""
    observer = Observer(client=mock_anthropic_sonnet)
    # The conftest _Usage class has input_tokens=100, output_tokens=20
    observer.synthesize(
        projection=VisibilityProjector(simple_kg).project_for("alice"),
        trace=_simple_trace(),
        actor_id="alice",
        action_text="look around",
    )
    assert observer.last_input_tokens == 100, (
        f"Expected last_input_tokens=100; got {observer.last_input_tokens}"
    )
    assert observer.last_output_tokens == 20, (
        f"Expected last_output_tokens=20; got {observer.last_output_tokens}"
    )


# ---------------------------------------------------------------------------
# Truth 10: Substring grounding — only known node IDs appear in output
# ---------------------------------------------------------------------------


def test_substring_grounding_observer_only_mentions_known_node_ids():
    """Phase-5 weak grounding check: output node-id-like tokens must be in projection.

    NOTE: This is a deliberately weak check per D-15 + pitfall #6. The full
    LLM-verifier grounding rubric is deferred to Phase 6 TEST-04. This test
    merely asserts that the canned mock response "You see alice and rock_1."
    passes — it doesn't catch hallucinated nodes from a real LLM response.
    """
    from tests.test_engine.conftest import MockAnthropicClient

    # Canned response only mentions known node IDs
    canned_response = "You see alice and rock_1."
    client = MockAnthropicClient([canned_response])
    observer = Observer(client=client)

    kg = KnowledgeGraph(db_path=None)
    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity", illumination=1.0)
    kg.add_node("rock_1", node_type="entity")
    kg.add_edge("alice", "room_1", type="location")
    kg.add_edge("room_1", "rock_1", type="contains")

    projection = VisibilityProjector(kg).project_for("alice")
    result = observer.synthesize(
        projection=projection,
        trace=_simple_trace(),
        actor_id="alice",
        action_text="look",
    )

    # Extract tokens that look like node IDs (underscore or digit, not pure stopword)
    node_id_pattern = re.compile(r"\b([a-z_][a-z_0-9]*)\b")
    common_stopwords = {
        "you",
        "see",
        "and",
        "the",
        "a",
        "an",
        "in",
        "is",
        "to",
        "of",
        "it",
        "its",
        "with",
        "has",
        "have",
        "are",
        "was",
        "were",
        "be",
        "on",
        "at",
        "for",
        "from",
        "that",
        "this",
        "or",
        "but",
        "not",
        "no",
        "your",
        "can",
        "could",
        "would",
        "will",
        "do",
        "did",
        "up",
        "down",
        "by",
        "as",
        "so",
        "if",
        "now",
        "out",
        "about",
    }
    projection_keys = set(projection.keys())
    for match in node_id_pattern.finditer(result.lower()):
        token = match.group(1)
        if "_" in token or any(ch.isdigit() for ch in token):
            # Looks like a node ID — must be in projection
            assert token in projection_keys, (
                f"Token {token!r} looks like a node ID but is NOT in the projection. "
                "Possible grounding violation. (Phase-5 weak check — Phase 6 TEST-04 is definitive)"
            )
        elif token not in common_stopwords:
            # Non-stopword without underscore/digit: permitted (could be property value / adjective)
            pass


# ---------------------------------------------------------------------------
# Truth 11: Chain truncation mentioned in user prompt when trace.truncated=True
# ---------------------------------------------------------------------------


def test_chain_truncation_mentioned_in_user_prompt_when_trace_truncated():
    """When trace.truncated=True, user prompt must mention 'Time blurs' or 'cascade' (D-17b)."""
    from tests.test_engine.conftest import MockAnthropicClient

    client = MockAnthropicClient(["You sense the passage of time."])
    observer = Observer(client=client)

    kg = KnowledgeGraph(db_path=None)
    kg.add_node("alice", node_type="agent")
    kg.add_node("room_1", node_type="entity", illumination=1.0)
    kg.add_edge("alice", "room_1", type="location")

    projection = VisibilityProjector(kg).project_for("alice")
    observer.synthesize(
        projection=projection,
        trace=_simple_trace(truncated=True),
        actor_id="alice",
        action_text="do something",
    )

    assert client.messages.calls, "LLM must be called"
    # The user prompt (or full message content) must mention truncation
    last_call = client.messages.calls[-1]
    # messages is a list of dicts with role+content
    user_content = "".join(
        m.get("content", "") for m in last_call.get("messages", []) if m.get("role") == "user"
    )
    assert "Time blurs" in user_content or "cascade" in user_content.lower(), (
        f"Expected 'Time blurs' or 'cascade' in user prompt for truncated trace, "
        f"got: {user_content!r}"
    )


# ---------------------------------------------------------------------------
# Falsehood D: client.messages.create called at most once per synthesize()
# ---------------------------------------------------------------------------


def test_llm_called_at_most_once_per_synthesize(mock_anthropic_sonnet, simple_kg):
    """Observer calls client.messages.create exactly once per synthesize() — no internal retry."""
    observer = Observer(client=mock_anthropic_sonnet)
    observer.synthesize(
        projection=VisibilityProjector(simple_kg).project_for("alice"),
        trace=_simple_trace(),
        actor_id="alice",
        action_text="look around",
    )
    assert len(mock_anthropic_sonnet.messages.calls) == 1, (
        f"Expected exactly 1 LLM call; got {len(mock_anthropic_sonnet.messages.calls)}"
    )


# ---------------------------------------------------------------------------
# E4 regression: mutation content + outcome-consistency in observer prompt
#
# Willowbrook tick 35 drift (2026-04-14): the force mechanic emitted
# ``old_chest.locked: True -> False`` yet the observation narrated
# "The old iron-bound chest remains locked and silent". Symmetrically, tick
# 32 emitted NO locked-mutation (failed attempt) yet the observer narrated
# "The chest is no longer locked." Both failures share one root cause: the
# observer user prompt included only a mutation *count*, never the mutation
# content, so the LLM narrated outcomes from intent (action_text) rather
# than ground truth. These tests lock in the fix.
# ---------------------------------------------------------------------------


def _trace_with_mutations(mutations: list) -> ExecutionTrace:
    """Build a one-node trace carrying the given Mutation list."""
    root = TraceNode(
        mechanic_id="force",
        actor="mira",
        target="old_chest",
        check_result=CheckResult(passed=True, reasons=["ok"]),
        mutations=list(mutations),
        children=[],
    )
    return ExecutionTrace(
        root=root,
        total_mechanics_executed=1,
        max_depth_reached=1,
        truncated=False,
    )


def _user_prompt_of(client) -> str:
    """Extract the user-role content from the most recent MockAnthropicClient call."""
    last_call = client.messages.calls[-1]
    return "".join(
        m.get("content", "") for m in last_call.get("messages", []) if m.get("role") == "user"
    )


def test_mutation_target_property_and_values_appear_in_user_prompt():
    """E4: observer user prompt must include mutation target.property: old -> new.

    Without this the LLM only sees a bare count ("3 graph changes") and can
    narrate outcomes contradicting the graph. Tick 35 force-unlock regression.
    """
    from tests.test_engine.conftest import MockAnthropicClient
    from token_world.graph import Mutation

    client = MockAnthropicClient(["The lock gives way."])
    observer = Observer(client=client)

    kg = KnowledgeGraph(db_path=None)
    kg.add_node("mira", node_type="agent")
    kg.add_node("room_1", node_type="entity", illumination=1.0)
    kg.add_node("old_chest", node_type="entity", locked=False)
    kg.add_edge("mira", "room_1", type="location")
    kg.add_edge("room_1", "old_chest", type="contains")

    mutation = Mutation(
        type="set_property",
        target="old_chest",
        property="locked",
        old_value=True,
        new_value=False,
    )

    projection = VisibilityProjector(kg).project_for("mira")
    observer.synthesize(
        projection=projection,
        trace=_trace_with_mutations([mutation]),
        actor_id="mira",
        action_text="force the chest",
    )

    prompt = _user_prompt_of(client)
    assert "old_chest.locked" in prompt, (
        f"Mutation target.property missing from observer prompt. Prompt was:\n{prompt}"
    )
    assert "True" in prompt and "False" in prompt, (
        f"Mutation old/new values missing from observer prompt. Prompt was:\n{prompt}"
    )


def test_empty_mutations_dont_claim_state_change_in_prompt():
    """E4: when no mutations happened the prompt must not list any mutation bullets.

    Tick 32 regression: a failed force attempt produced no ``locked`` mutation,
    yet the observer narrated "The chest is no longer locked" — because the
    prompt never told it which property changed. A zero-mutation trace must
    not contain a ``.locked:`` bullet that could be misread as a state change.
    """
    from tests.test_engine.conftest import MockAnthropicClient

    client = MockAnthropicClient(["The lock resists. Nothing gives."])
    observer = Observer(client=client)

    kg = KnowledgeGraph(db_path=None)
    kg.add_node("mira", node_type="agent")
    kg.add_node("room_1", node_type="entity", illumination=1.0)
    kg.add_node("old_chest", node_type="entity", locked=True)
    kg.add_edge("mira", "room_1", type="location")
    kg.add_edge("room_1", "old_chest", type="contains")

    projection = VisibilityProjector(kg).project_for("mira")
    observer.synthesize(
        projection=projection,
        trace=_trace_with_mutations([]),  # failed attempt: zero mutations
        actor_id="mira",
        action_text="force the chest",
    )

    prompt = _user_prompt_of(client)
    # Zero mutations = zero per-mutation bullets. Look specifically for the
    # ``target.property:`` bullet shape that would signal a state change.
    assert "  - old_chest.locked:" not in prompt, (
        "Zero-mutation trace must not emit a ``old_chest.locked:`` bullet — "
        f"that would mislead the observer. Prompt was:\n{prompt}"
    )
    assert "0 graph changes" in prompt, (
        f"Mutation count should reflect zero changes. Prompt was:\n{prompt}"
    )


def test_system_prompt_contains_outcome_consistency_clause():
    """E4: system prompt must direct the LLM to treat mutations as ground truth.

    Locks in the OUTCOME CONSISTENCY clause added alongside the user-prompt
    mutation-detail fix. The action_text is only intent; the mutation list is
    what actually happened. Both sides of the fix are needed: data (user
    prompt) + instruction (system prompt).
    """
    assert "OUTCOME CONSISTENCY" in _SYSTEM_PROMPT, (
        "Observer system prompt must carry an OUTCOME CONSISTENCY clause "
        "instructing the LLM to treat mutations as ground truth."
    )
    # Specifically the action_text-is-intent / mutations-are-truth distinction.
    assert "ground truth" in _SYSTEM_PROMPT.lower(), (
        "Outcome-consistency clause should name mutations as ground truth."
    )
