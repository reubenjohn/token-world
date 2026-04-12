"""Minimal MCP stdio server stub for Token World.

Declares four simulation tools (resume_tick, rollback, list_mechanics,
register_mechanic) and returns "not implemented" for each.
This validates Claude Code tool discovery while tools are built in later phases.

Threat mitigation (T-00-05): JSON parse errors return proper JSON-RPC error
response (-32700). Invalid methods return -32601. No eval/exec of input.
"""

from __future__ import annotations

import json
import sys

TOOLS = [
    {
        "name": "resume_tick",
        "description": "Resume or start a new simulation tick",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "rollback",
        "description": "Roll back the universe to a previous snapshot",
        "inputSchema": {
            "type": "object",
            "properties": {
                "snapshot_id": {"type": "string", "description": "Snapshot to restore"},
            },
            "required": ["snapshot_id"],
        },
    },
    {
        "name": "list_mechanics",
        "description": "List all registered mechanics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter": {"type": "string", "description": "Optional filter pattern"},
            },
        },
    },
    {
        "name": "register_mechanic",
        "description": "Register a new mechanic from a mechanics/ subfolder",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to mechanic folder"},
            },
            "required": ["path"],
        },
    },
]


def handle_request(request: dict) -> dict | None:
    """Handle a JSON-RPC request.

    Args:
        request: Parsed JSON-RPC request dict.

    Returns:
        JSON-RPC response dict, or None for notifications.
    """
    method = request.get("method", "")
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "token-world", "version": "0.1.0"},
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS},
        }

    if method == "tools/call":
        tool_name = request.get("params", {}).get("name", "unknown")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Tool '{tool_name}' is not yet implemented. This is a Phase 0 stub."
                        ),
                    }
                ],
            },
        }

    if method == "notifications/initialized":
        return None  # notification, no response

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    """Run the MCP stdio server."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            error_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            sys.stdout.write(json.dumps(error_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
