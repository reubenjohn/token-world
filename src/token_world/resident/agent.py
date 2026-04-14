"""ResidentAgent — raw Anthropic SDK action-generation loop (D-01, D-02, D-04, D-21).

The resident agent:
  1. Assembles a hash-stable system prompt from world rules + personality bundle.
  2. Builds an alternating user/assistant messages context from rolling memory.
  3. Calls Haiku (or configured override) to get the next action text.
  4. Returns the stripped action string — caller feeds it to SimulationEngine.run_tick.

The agent does NOT call SimulationEngine directly (clean separation per D-21).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from token_world.engine.llm_backend import (
    AnthropicSDKBackend,
    LLMBackend,
    get_backend,
)
from token_world.resident.memory import AgentMemory
from token_world.resident.personality import PersonalityBundle

if TYPE_CHECKING:
    from token_world.graph import KnowledgeGraph

# ---------------------------------------------------------------------------
# System-prompt template
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_TEMPLATE = """\
{world_rules}

## Your Character

Name: {name}
Archetype: {archetype}
Traits: {traits}
Backstory: {backstory}
Speech style: {speech_style}

## Instructions

You are {name}. Issue actions as short imperative sentences. Be curious and exploratory.
Stay in character at all times. Do not break character. Do not describe your thoughts —
only issue the action you will take next.

If nothing in the world responds to your last attempt, stay in character and try a
different small action. Never narrate the simulation framework itself — words like
"framework", "mechanic", "yield", "system", "operator" break immersion and are
forbidden. Your character does not know the simulation exists."""


# ---------------------------------------------------------------------------
# ResidentAgent
# ---------------------------------------------------------------------------


class ResidentAgent:
    """Generates one action text per turn using the raw Anthropic SDK (D-01).

    Args:
        agent_id:   Graph node ID of the agent.
        session_id: Current session ID (used for memory context).
        personality: The agent's PersonalityBundle (D-03).
        memory:     AgentMemory adapter to fetch rolling context.
        client:     An anthropic.Anthropic instance (or test double).
        model:      LLM model string (default "claude-haiku-4-5" per D-02).
        world_rules: Text content of the universe's CLAUDE.md (world rules section).
    """

    def __init__(
        self,
        agent_id: str,
        session_id: str,
        personality: PersonalityBundle,
        memory: AgentMemory,
        client: Any = None,
        *,
        model: str = "claude-haiku-4-5",
        world_rules: str = "",
        backend: LLMBackend | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._session_id = session_id
        self._personality = personality
        self._memory = memory
        self._client = client
        self._model = model
        self._world_rules = world_rules
        self._system_prompt = self._build_system_prompt()
        # Backend wrap-or-default (D-02, D-10): backend > SDK-wrap(client) > get_backend()
        if backend is not None:
            self._backend: LLMBackend = backend
        elif client is not None:
            self._backend = AnthropicSDKBackend(client)
        else:
            self._backend = get_backend()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def system_prompt_text(self) -> str:
        """Return the assembled system prompt string (used for SHA-256 hashing by D-14)."""
        return self._system_prompt

    def run_turn(self) -> str:
        """Generate the agent's next action via an LLM call.

        Builds context from rolling memory window, calls the configured model
        through the :class:`LLMBackend` abstraction, returns the stripped action
        text. Does NOT call SimulationEngine (D-21).

        The multi-turn conversation history produced by :meth:`_build_messages`
        is flattened into a single prompt string (role-prefixed blocks joined
        by ``\\n\\n``) because ``LLMBackend.call`` takes a single prompt per
        Phase 07.1 D-01. For the SDK auto-wrap path this is a semantic change
        from the prior direct ``messages.create(messages=[...])`` call — the
        backend still issues a real SDK call, but the messages array now
        contains a single user-role message with the flattened history as
        content.
        """
        messages = self._build_messages()
        prompt = self._flatten_messages_to_prompt(messages)
        text = self._backend.call(
            model=self._model,
            system=self._system_prompt,
            prompt=prompt,
            max_tokens=256,
        )
        if not text or not text.strip():
            raise ValueError("LLM returned empty response in run_turn()")
        return text.strip()

    @staticmethod
    def _flatten_messages_to_prompt(messages: list[dict[str, str]]) -> str:
        """Render a ``[{role, content}, ...]`` list as a ``\\n\\n``-joined prompt string."""
        if not messages:
            return ""
        return "\n\n".join(f"{m['role']}: {m['content']}" for m in messages)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        """Assemble the hash-stable system prompt per D-04.

        Components (in order):
          1. Universe world rules (from CLAUDE.md world-rules section)
          2. Personality block (name, archetype, traits, backstory, speech_style)
          3. Static instruction block (imperative sentences, stay in character)

        History is NOT included — it goes in the messages array (D-04).
        """
        return _SYSTEM_PROMPT_TEMPLATE.format(
            world_rules=self._world_rules,
            name=self._personality.name,
            archetype=self._personality.archetype,
            traits=", ".join(self._personality.traits),
            backstory=self._personality.backstory,
            speech_style=self._personality.speech_style,
        )

    def _build_messages(self) -> list[dict[str, str]]:
        """Build alternating user/assistant messages from rolling memory window (D-07).

        Structure:
          [user: action_1, assistant: obs_1, user: action_2, assistant: obs_2, ...]
          [user: "Memory: {summary}\\n\\n{action_1}" if summary present, ...]
          [user: "What do you do next?"]

        The memory summary (if any) is prepended to the FIRST user message.
        """
        turns, summary = self._memory.get_context(self._session_id, window=10)

        messages: list[dict[str, str]] = []

        if turns:
            # Build alternating pairs
            for i, (action, observation) in enumerate(turns):
                user_content = action
                if i == 0 and summary:
                    user_content = f"Memory (older events): {summary}\n\n{action}"
                messages.append({"role": "user", "content": user_content})
                messages.append({"role": "assistant", "content": observation})

        # Final user prompt requesting next action
        if not turns and summary:
            # No history yet but there's a summary — include it in the prompt
            messages.append(
                {
                    "role": "user",
                    "content": f"Memory (older events): {summary}\n\nWhat do you do next?",
                }
            )
        else:
            messages.append({"role": "user", "content": "What do you do next?"})

        return messages


# ---------------------------------------------------------------------------
# Module-level helper (D-03 graph property storage)
# ---------------------------------------------------------------------------


def create_agent_node(
    graph: KnowledgeGraph,
    agent_id: str,
    personality: PersonalityBundle,
) -> None:
    """Create an agent node in the graph with personality stored as a dict property.

    Satisfies D-03: PersonalityBundle stored as JSON-serializable dict on the
    graph node (CLAUDE.md: ALLOWED_PROPERTY_TYPES includes dict).

    Args:
        graph:      The KnowledgeGraph to mutate.
        agent_id:   The node ID for the new agent.
        personality: The personality bundle to store as ``graph.set(agent_id, "personality", ...)``.
    """
    graph.add_node(agent_id, node_type="agent")
    graph.set(agent_id, "personality", personality.model_dump())
