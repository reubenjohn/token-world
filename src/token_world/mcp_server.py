"""MCP stdio server for Token World simulation tools (UNIV-03).

Exposes three tools to any MCP-capable LLM harness (Claude Code, Codex) running
inside a universe folder:

- ``resume_tick``:    run one simulation tick via SimulationEngine.run_tick (Plan 05-08)
- ``rollback``:       restore the knowledge graph to a snapshot via KnowledgeGraph.restore (Phase 1)
- ``list_mechanics``: enumerate mechanics via MechanicRegistry (Phase 2, updated by Phase 4)

Stateless: each tool call constructs its dependencies from universe_path, does the work,
persists changes, and exits. No long-lived state in the server process beyond the stdio
loop.

Threat mitigation (see ``threat_model`` in 05-09-PLAN.md):
- T-05-MCP-JSON-INJECTION: structured params; no shell interpolation
- T-05-MCP-PATH-TRAVERSAL: universe_path resolved and '..' rejected
- T-05-MCP-ROLLBACK-WIPE: snapshot_id integer-coerced before restore; missing db rejected

Test injection: monkeypatch ``token_world.mcp_server._anthropic_factory`` to a callable
returning a ``MockAnthropicClient`` to avoid hitting the real Anthropic API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

TOOLS = [
    {
        "name": "resume_tick",
        "description": (
            "Run one simulation tick for the resident agent. Classifies the action text, "
            "matches a mechanic, executes (or yields to the operator if no mechanic matches), "
            "and returns a grounded observation. Tools are stateless — each call creates a "
            "fresh SimulationEngine instance bound to the universe folder."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "universe_path": {
                    "type": "string",
                    "description": "Absolute path to the universe folder",
                },
                "action_text": {
                    "type": "string",
                    "description": "Resident agent's natural-language action",
                },
                "actor": {
                    "type": "string",
                    "description": "Node id of the acting agent",
                },
            },
            "required": ["universe_path", "action_text", "actor"],
        },
    },
    {
        "name": "rollback",
        "description": "Restore the graph to a previous snapshot identified by snapshot_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "universe_path": {
                    "type": "string",
                    "description": "Absolute path to the universe folder",
                },
                "snapshot_id": {
                    "type": "integer",
                    "description": "Snapshot id to restore",
                },
            },
            "required": ["universe_path", "snapshot_id"],
        },
    },
    {
        "name": "list_mechanics",
        "description": (
            "List all mechanics currently registered in the universe's mechanics/ folder."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "universe_path": {
                    "type": "string",
                    "description": "Absolute path to the universe folder",
                },
                "filter": {
                    "type": "string",
                    "description": "Optional substring filter on mechanic id",
                },
            },
            "required": ["universe_path"],
        },
    },
]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


class _InvalidParams(ValueError):
    """Raised by tool functions on missing/invalid JSON-RPC params."""


def _jsonrpc_error(req_id: Any, code: int, message: str) -> dict:
    """Return a JSON-RPC error response dict."""
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _require_universe_path(arguments: dict) -> Path:
    """Extract and validate universe_path from tool arguments.

    Returns the resolved Path. Raises _InvalidParams on missing or invalid input.
    Path-traversal defence: rejects '..' segments in the raw input.
    """
    raw = arguments.get("universe_path")
    if not isinstance(raw, str) or not raw:
        raise _InvalidParams("missing or non-string 'universe_path'")
    if ".." in Path(raw).parts:
        raise _InvalidParams("'universe_path' contains disallowed '..' segment")
    path = Path(raw).resolve()
    if not path.is_dir():
        raise _InvalidParams(f"universe_path does not exist or is not a directory: {path}")
    return path


# Module-level factory; tests monkeypatch to inject a MockAnthropicClient.
# Set to None means "use the real anthropic.Anthropic()".
_anthropic_factory: Any = None


def _build_anthropic_client() -> Any:
    """Return an Anthropic client. Tests monkeypatch _anthropic_factory."""
    if _anthropic_factory is not None:
        return _anthropic_factory()
    # Lazy import so the MCP module doesn't crash if anthropic is missing at import time
    from anthropic import Anthropic

    return Anthropic()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _tool_resume_tick(arguments: dict) -> dict:
    """Run one simulation tick and return a result payload.

    Required arguments: universe_path, action_text, actor.
    """
    universe_path = _require_universe_path(arguments)
    action_text = arguments.get("action_text")
    actor = arguments.get("actor")
    if not isinstance(action_text, str) or not action_text.strip():
        raise _InvalidParams("missing or empty 'action_text'")
    if not isinstance(actor, str) or not actor.strip():
        raise _InvalidParams("missing or empty 'actor'")

    # Lazy imports — keep module import light so tests that don't exercise resume_tick
    # don't pay for the engine + anthropic import chain.
    from token_world.engine import SimulationEngine
    from token_world.graph import KnowledgeGraph

    db_path = universe_path / "universe.db"
    graph = KnowledgeGraph(db_path=db_path)
    if db_path.exists():
        graph.load()

    engine = SimulationEngine(
        universe_path=universe_path,
        graph=graph,
        anthropic_client=_build_anthropic_client(),
    )
    result = engine.run_tick(action_text, actor)

    # Persist graph state after tick
    graph.save()

    payload: dict[str, Any] = {
        "tick_id": result.tick_id,
        "kind": result.kind,
        "observation": result.observation,
        "refusal_reason": result.refusal_reason,
    }
    if result.yield_signal is not None:
        payload["yield_signal"] = json.loads(result.yield_signal.to_json())
    return payload


def _tool_list_mechanics(arguments: dict) -> dict:
    """List all registered mechanics.

    Required arguments: universe_path.
    Optional: filter (substring match against mechanic id, case-insensitive).
    """
    universe_path = _require_universe_path(arguments)
    filter_str = arguments.get("filter")

    from token_world.mechanic.registry import MechanicRegistry

    registry = MechanicRegistry(universe_path / "mechanics", universe_dir=universe_path)
    mechanics = registry.list_mechanics()

    if isinstance(filter_str, str) and filter_str:
        needle = filter_str.lower()
        mechanics = [m for m in mechanics if needle in m.id.lower()]

    return {
        "count": len(mechanics),
        "mechanics": [
            {
                "id": m.id,
                "description": m.description,
                "voluntary": m.voluntary,
                "tags": list(m.tags),
            }
            for m in mechanics
        ],
    }


def _tool_rollback(arguments: dict) -> dict:
    """Restore the graph to a previous snapshot.

    Required arguments: universe_path, snapshot_id (int).
    """
    universe_path = _require_universe_path(arguments)
    raw_snapshot = arguments.get("snapshot_id")
    try:
        snapshot_id = int(raw_snapshot)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise _InvalidParams(f"'snapshot_id' must be an integer: got {raw_snapshot!r}") from exc

    from token_world.graph import KnowledgeGraph

    db_path = universe_path / "universe.db"
    if not db_path.exists():
        raise _InvalidParams(f"no universe.db at {db_path}")

    graph = KnowledgeGraph(db_path=db_path)
    graph.load()
    pre_restore_tick = graph.current_tick
    graph.restore(snapshot_id)
    graph.save()

    return {
        "ok": True,
        "snapshot_id": snapshot_id,
        "restored_to_tick": graph.current_tick,
        "rolled_back_from_tick": pre_restore_tick,
    }


# ---------------------------------------------------------------------------
# Request dispatcher
# ---------------------------------------------------------------------------


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
        params = request.get("params", {}) or {}
        tool_name = params.get("name", "unknown")
        arguments = params.get("arguments", {}) or {}

        try:
            if tool_name == "resume_tick":
                result_payload = _tool_resume_tick(arguments)
            elif tool_name == "list_mechanics":
                result_payload = _tool_list_mechanics(arguments)
            elif tool_name == "rollback":
                result_payload = _tool_rollback(arguments)
            else:
                return _jsonrpc_error(req_id, -32602, f"Unknown tool: {tool_name}")
        except _InvalidParams as exc:
            return _jsonrpc_error(req_id, -32602, f"Invalid params: {exc}")
        except Exception as exc:
            # Log full trace to stderr (not stdout — stdout is reserved for JSON-RPC responses)
            import traceback

            sys.stderr.write(traceback.format_exc())
            return _jsonrpc_error(req_id, -32603, f"Internal error: {exc}")

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result_payload, sort_keys=True)}],
            },
        }

    if method == "notifications/initialized":
        return None  # notification, no response

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


# ---------------------------------------------------------------------------
# stdio loop
# ---------------------------------------------------------------------------


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
