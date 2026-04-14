"""Read-only NiceGUI dashboard for Token World.

The dashboard is an *observer-mode* window into a running or completed
universe. It never mutates graph state — all writes still go through the
simulation engine + MCP. See
``.planning/phases/11-nicegui-dashboard/11-CONTEXT.md`` for design rationale.

Entry point: ``token-world dashboard <slug> [--port PORT]`` (see
:mod:`token_world.cli`).
"""

from token_world.dashboard.app import create_app, run_app

__all__ = ["create_app", "run_app"]
