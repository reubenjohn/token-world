"""Mechanic-author subagent definition (Plan 04.1-03 Task 1).

Provides:
    - :func:`mechanic_author_prompt` — standalone function returning the
      authoring prompt; reused by Plan 04.1-05 to populate
      ``.claude/agents/mechanic-author.md``.
    - :func:`build_mechanic_author_agent` — assembles an
      :class:`~claude_agent_sdk.AgentDefinition` pinned to Opus (D-02) with a
      tool whitelist that excludes ``Agent`` (Pitfall 5 — no sub-subagents)
      and includes the in-process validation tool plus list_mechanics.

Design (RESEARCH §Pattern 3):
    The subagent gets a fresh context window in the SDK; embedding the full
    yield signal JSON in its prompt avoids extra tool-call round-trips for
    the subagent to re-fetch context it could already have up front.
"""

from __future__ import annotations

import os
from pathlib import Path

from claude_agent_sdk import AgentDefinition

from token_world.operator.yield_signal import YieldSignal

__all__ = ["build_mechanic_author_agent", "mechanic_author_prompt"]


_MECHANIC_AUTHOR_PROMPT = """\
You are the Token World Mechanic Author. The simulation has halted on a tick
because no existing mechanic matches the resident agent's classified action.
Your job is to write a correct mechanic as a Python file and verify it with
the validation tool.

# The yield signal

```json
{yield_json}
```

# Universe path

{universe}

# Your process

1. **Understand the action.** Read `classified_action.verb`, `actor`, `target`,
   and `params`. These tell you what the agent tried to do.

2. **Check existing mechanics first.** Call `mcp__token-world__list_mechanics`.
   If `candidate_mechanic_ids` in the yield are populated, Read those files.
   Prefer extending an existing mechanic over writing a new one when the verb
   and semantics match.

3. **Read the authoring guide.** `docs/authoring-mechanics.md` (in the universe
   or the framework docs) is the canonical reference. Skim it if you haven't
   recently.

4. **Write the mechanic.** If a new one, create `mechanics/<id>.py` where
   `<id>` is a short, descriptive snake_case name. One `Mechanic` subclass.
   Required class attributes: `id`, `description`. Default `voluntary=True`,
   `tags=[]`. Implement `check(ctx) -> CheckResult` and
   `apply(ctx) -> list[Mutation]`. See the seed mechanics for reference.

5. **Validate.** Call `mcp__validation__validate_mechanic` with the module
   path. If it returns findings, fix them and re-validate. Continue until the
   report returns `passed=True`.

6. **Summarise.** Your final message must include:
   - The mechanic id you authored (or extended)
   - The file path(s) you wrote
   - A one-line description of the mechanic's semantics

# Constraints

- Use only `MechanicContext` DSL; never import `networkx` or
  `token_world.graph.knowledge_graph` directly. The validator will reject
  such imports.
- `eval`, `exec`, `__import__`, bare `open` are forbidden in mechanic modules.
- Keep mechanics small and composable. If the action is a primitive, write a
  primitive; helpers go in `mechanics/_helpers.py`.
- Don't call `resume_tick` — the outer orchestrator will.
"""


def mechanic_author_prompt(*, universe: Path, yield_json: str) -> str:
    """Return the canonical mechanic-author subagent prompt.

    Exposed as a public function so Plan 04.1-05 can write the same text into
    ``.claude/agents/mechanic-author.md`` for the interactive Claude Code
    flow without duplicating the prompt source.

    Args:
        universe: Path to the universe folder; embedded in the prompt so the
            subagent knows where to write.
        yield_json: The :meth:`YieldSignal.to_json` output for the halting
            yield. Embedded verbatim so the subagent has the full structured
            signal up front.

    Returns:
        The fully-rendered prompt string.
    """
    return _MECHANIC_AUTHOR_PROMPT.format(universe=universe, yield_json=yield_json)


def build_mechanic_author_agent(
    *,
    universe: Path,
    yield_signal: YieldSignal,
    model: str = os.environ.get("OPERATOR_MODEL", "opus"),
) -> AgentDefinition:
    """Build the mechanic-author :class:`AgentDefinition` (D-17).

    - ``model="opus"`` per D-02.
    - ``tools`` excludes ``"Agent"`` (Pitfall 5: subagents must not spawn
      sub-subagents).
    - Includes ``mcp__validation__validate_mechanic`` (the @tool wrapper from
      :mod:`token_world.operator.validation_tool`) and
      ``mcp__token-world__list_mechanics`` from the universe MCP surface.

    Args:
        universe: Universe folder; embedded in the prompt.
        yield_signal: The halting yield; serialised into the prompt via
            :meth:`YieldSignal.to_json`.

    Returns:
        :class:`AgentDefinition` ready to be passed via
        ``ClaudeAgentOptions(agents={"mechanic-author": ...})``.
    """
    return AgentDefinition(
        description=(
            "Authors a new mechanic in response to a simulation yield. "
            "Invoke when the simulation has halted waiting for a mechanic "
            "that matches the classified agent action."
        ),
        prompt=mechanic_author_prompt(universe=universe, yield_json=yield_signal.to_json()),
        tools=[
            "Read",
            "Write",
            "Edit",
            "Glob",
            "Grep",
            "Bash",
            "mcp__validation__validate_mechanic",
            "mcp__token-world__list_mechanics",
        ],
        model=model,
    )
