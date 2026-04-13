"""Universe ``.mcp.json`` loader (Plan 04.1-03 Task 1).

Translates a universe's ``.mcp.json`` (the Claude Code convention with an
outer ``mcpServers`` wrapper) into the flat dict shape the Agent SDK expects
for ``ClaudeAgentOptions(mcp_servers=...)``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = ["load_universe_mcp_config"]


def load_universe_mcp_config(universe_path: Path) -> dict[str, Any]:
    """Parse ``<universe>/.mcp.json`` into Agent SDK's ``mcp_servers`` dict.

    Input shape (Claude Code convention)::

        {"mcpServers": {"token-world": {"command": "uvx", ...}}}

    Output shape (Agent SDK convention per RESEARCH Example 4)::

        {"token-world": {"command": "uvx", ...}}

    Args:
        universe_path: Path to the universe folder.

    Returns:
        Flat dict mapping server name -> server config.

    Raises:
        FileNotFoundError: ``.mcp.json`` does not exist in *universe_path*.
        json.JSONDecodeError: file contents are not valid JSON.
        ValueError: the ``mcpServers`` value is present but not an object.
    """
    mcp_path = universe_path / ".mcp.json"
    if not mcp_path.exists():
        raise FileNotFoundError(f"No .mcp.json in {universe_path}. Is this a scaffolded universe?")
    data = json.loads(mcp_path.read_text(encoding="utf-8"))
    servers = data.get("mcpServers", {}) if isinstance(data, dict) else {}
    if not isinstance(servers, dict):
        raise ValueError(
            f"Malformed .mcp.json at {mcp_path}: 'mcpServers' must be an object, "
            f"got {type(servers).__name__}"
        )
    return dict(servers)
