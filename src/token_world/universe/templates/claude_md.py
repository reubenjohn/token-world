"""CLAUDE.md template generation for universe folders.

Generates the per-universe CLAUDE.md with sections for world rules,
available MCP tools, current state, and grounding constraints (per D-04).
"""

from __future__ import annotations

from string import Template

_CLAUDE_MD_TEMPLATE = Template("""\
# Universe: $name

## World Rules

> No rules yet. The world is a blank slate.
> Rules emerge as mechanics are created during simulation.

**Maintenance:** When a mechanic is registered, append its rule summary to this
section. When a mechanic is removed or superseded, update or remove the
corresponding entry. This section must always reflect the current rule set.

## Available Tools

### resume_tick
Resume or start a new simulation tick. The engine interprets the resident
agent's action, matches it to a mechanic, executes the mechanic, and
returns an observation grounded in the knowledge graph.

**Status:** Not yet implemented (Phase 5)

### rollback
Roll back the universe to a previous snapshot.

**Status:** Not yet implemented (Phase 1)

### list_mechanics
List all registered mechanics with their descriptions and preconditions.

**Status:** Not yet implemented (Phase 2)

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

See `docs/authoring-mechanics.md` in this universe for the full guide
(populated during Phase 4 plan 04-05).

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
