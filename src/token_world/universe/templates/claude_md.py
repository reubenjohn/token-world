"""CLAUDE.md template generation for universe folders.

Generates the per-universe CLAUDE.md with sections for world rules,
available MCP tools, operator flow guidance (Phase 4.1), current state,
and grounding constraints (per D-04, D-05, D-19).
"""

from __future__ import annotations

from string import Template

_CLAUDE_MD_TEMPLATE = Template("""\
# Universe: $name

> When a tick yields because no mechanic matches the resident agent's action,
> see [Operator Flow: When a Tick Yields](#operator-flow-when-a-tick-yields)
> below for the canonical author-and-resume process.

## World Rules

> No rules yet. The world is a blank slate.
> Rules emerge as mechanics are created during simulation.

**Maintenance:** When a mechanic is registered, append its rule summary to this
section. When a mechanic is removed or superseded, update or remove the
corresponding entry. This section must always reflect the current rule set.

## Available Tools

Three MCP tools (Phase 4 surface, UNIV-03 stable) are exposed to any
MCP-aware harness opening this universe. The `mechanic-author` subagent
(defined in `.claude/agents/mechanic-author.md`) is the canonical way to
respond to a yield.

### resume_tick
Resume or start a simulation tick. The engine interprets the resident agent's
action, matches it to a mechanic, executes the mechanic, and returns an
observation grounded in the knowledge graph. May yield a `YieldSignal` when
no mechanic matches — see [Operator Flow](#operator-flow-when-a-tick-yields).

### rollback
Roll back the universe to a previous snapshot. Takes a tick id or snapshot id
and restores graph + mechanic state to that point.

### list_mechanics
List all registered mechanics with their ids, descriptions, tags, and voluntary
flag. Useful to check existing coverage before authoring a new mechanic in
response to a yield.

## Operator Flow: When a Tick Yields

If `token-world run-tick` (or `resume_tick` returns a yield result), the
simulation has halted because no mechanic matches the resident agent's action.
Your job is to author the needed mechanic and resume the tick.

Canonical flow:

1. Run `token-world inspect-yield` to see the yield signal (classified action,
   actor state, candidate existing mechanics).
2. Use the `mechanic-author` subagent (defined in `.claude/agents/mechanic-author.md`)
   to write the mechanic. The subagent reads the authoring guide, writes
   `mechanics/<id>.py` + a test, and validates with `validate-mechanic` until
   passing.
3. Run `token-world resume-tick --tick <tick_id>` to continue. The registry
   re-scans, picks up the new mechanic, and the tick completes.

When to author vs extend: if the yield's `candidate_mechanic_ids` list is
populated, Read those files first — prefer extending over rewriting when the
verb semantics match.

Debugging past ticks: `token-world replay-tick <tick_id>` renders the full
per-tick diagnostics.

## Mechanic Authoring

This universe is a Python codebase. Mechanics live as flat modules at
`mechanics/<id>.py` with a `Mechanic` subclass declaring class-level
`id`, `description`, `voluntary`, `tags`. Shared helpers go in
`mechanics/_helpers.py` (underscore-prefixed files are skipped by the
registry).

Author a new mechanic:

```bash
token-world scaffold-mechanic $slug --id <mechanic-id>
token-world validate-mechanic $slug <mechanic-id>
```

See `docs/authoring-mechanics.md` in this universe for the full guide —
class contract, MechanicContext DSL reference, forbidden imports/calls,
voluntary/involuntary matcher patterns, the `blocked_by` framework-gap
stub convention, and common anti-patterns.

## Current State

Empty universe. No nodes, no edges, no mechanics.

**Maintenance:** Update this section after each tick to reflect the current
graph summary (node/edge counts, active mechanics, notable entities).

## Constraints

- All observations MUST be grounded in knowledge graph state
- Never hallucinate state that doesn't exist in the graph
- Mechanics are the only way to modify the knowledge graph
- Every mutation is logged and reversible
""")


def render_claude_md(*, name: str, slug: str) -> str:
    """Render the CLAUDE.md template for a universe.

    Args:
        name: Display name of the universe.
        slug: Slugified universe name (used in the authoring-tool examples
            rendered in the ``Mechanic Authoring`` section).

    Returns:
        The rendered CLAUDE.md content as a string.
    """
    return _CLAUDE_MD_TEMPLATE.substitute(name=name, slug=slug)
