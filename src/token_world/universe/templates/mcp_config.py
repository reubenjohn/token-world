"""MCP configuration (.mcp.json) generation for universe folders.

Generates the .mcp.json that points Claude Code (or any MCP-compatible
harness) to the token-world MCP server entry point.
"""

from __future__ import annotations

import json


def render_mcp_json() -> str:
    """Generate .mcp.json content for a universe folder.

    The token-world-mcp command must be available in PATH or installed
    via uv. Users may need to adjust the command path based on their
    installation.

    Returns:
        JSON string for the .mcp.json file.
    """
    config = {
        "mcpServers": {
            "token-world": {
                "command": "uvx",
                "args": ["--from", "token-world", "token-world-mcp"],
            }
        }
    }
    return json.dumps(config, indent=2) + "\n"
