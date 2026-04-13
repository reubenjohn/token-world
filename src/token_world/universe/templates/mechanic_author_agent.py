"""Renderer for .claude/agents/mechanic-author.md scaffold file (Plan 04.1-05).

Per D-05 / RESEARCH Pattern 5: the filesystem agent is sourced from the
same :func:`mechanic_author_prompt` function the programmatic
:class:`~claude_agent_sdk.AgentDefinition` uses. Prompt drift between the
interactive (Claude Code in universe folder) and programmatic
(:class:`~token_world.operator.OperatorHarness`) operator paths is
eliminated by this shared source — T-04.1-22.

The resulting markdown file is placed at ``<universe>/.claude/agents/mechanic-author.md``
during :func:`~token_world.universe.scaffold.scaffold_universe` and is picked
up automatically by Claude Code when a user opens the universe folder. [CITED:
code.claude.com/docs/en/agent-sdk/subagents §Filesystem-based definition]
"""

from __future__ import annotations

from pathlib import Path

from token_world.operator.subagent import mechanic_author_prompt

__all__ = ["render_mechanic_author_md"]


# Frontmatter locked by T-04.1-23: `Agent` is deliberately absent from tools
# (Pitfall 5 — no sub-subagents). The tool whitelist mirrors the programmatic
# AgentDefinition in token_world.operator.subagent.build_mechanic_author_agent
# for parity.
#
# YAML frontmatter lines must stay on a single line each — a wrapped
# description or tools list is not valid YAML scalar syntax without explicit
# folded-block syntax, which Claude Code's filesystem-agent loader doesn't
# accept. Disable E501 line-length for the literal block only.
_FRONTMATTER = """\
---
description: Authors a new mechanic in response to a simulation yield. Invoke when the simulation has halted waiting for a mechanic matching the resident agent's classified action.
tools: Read, Write, Edit, Glob, Grep, Bash, mcp__validation__validate_mechanic, mcp__token-world__list_mechanics
model: opus
---

"""  # noqa: E501


_TEMPLATE_NOTE = """\
> **Note:** In this filesystem-agent form, `<YIELD_SIGNAL_JSON>` below is a
> template placeholder. At invocation time, paste the live yield signal
> (run `token-world inspect-yield --format json`) into the subagent prompt
> in place of the placeholder.

"""


def render_mechanic_author_md(universe: Path) -> str:
    """Render the body of ``.claude/agents/mechanic-author.md`` for a universe.

    The returned string is YAML frontmatter + a short operator note + the
    canonical mechanic-author prompt (sourced from
    :func:`token_world.operator.subagent.mechanic_author_prompt`).

    Args:
        universe: Path to the universe folder. Embedded into the prompt so the
            subagent knows where to write on invocation.

    Returns:
        Full markdown body suitable for writing to
        ``<universe>/.claude/agents/mechanic-author.md``.
    """
    body = mechanic_author_prompt(
        universe=universe,
        yield_json="<YIELD_SIGNAL_JSON>",
    )
    return _FRONTMATTER + _TEMPLATE_NOTE + body
