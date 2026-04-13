"""In-process MCP server wrapping Phase 4's validate-mechanic CLI (Plan 04.1-03 Task 1).

Exposes one tool, ``validate_mechanic(module_path)``, to the mechanic-author
subagent. The wrapper invokes ``token-world validate-mechanic <path> --format json``
in a subprocess and translates the JSON report into an MCP tool result with
``is_error=True`` when validation fails so the subagent's tool-use loop sees
the failure structurally rather than parsing stdout text.

Security posture (T-04.1-11):
    - ``subprocess.run`` is invoked with a list argv and ``shell=False``; the
      ``module_path`` argument is passed verbatim as a separate argv element,
      never interpolated into a shell string. Test
      ``test_validate_mechanic_subprocess_is_shell_false`` enforces this.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

__all__ = ["build_validation_server"]


def build_validation_server(universe: Path) -> Any:
    """Return an in-process SDK MCP server exposing ``validate_mechanic``.

    Args:
        universe: Path to the universe folder. The validator subprocess runs
            with ``cwd=str(universe)`` so relative module paths the subagent
            passes (e.g., ``"mechanics/pickup.py"``) resolve naturally.

    Returns:
        ``McpSdkServerConfig`` (opaque to callers — pass it into
        ``ClaudeAgentOptions(mcp_servers={"validation": ...})``).
    """

    @tool(
        "validate_mechanic",
        (
            "Validate a mechanic module against the Phase 4 pipeline "
            "(syntax, AST rules, import, contract, tests, dry-execute). "
            "Returns a structured report. Call after every edit to the file."
        ),
        {"module_path": str},
    )
    async def validate_mechanic(args: dict[str, Any]) -> dict[str, Any]:
        module_path = args["module_path"]
        result = subprocess.run(
            [
                "uv",
                "run",
                "token-world",
                "validate-mechanic",
                module_path,
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            cwd=str(universe),
            shell=False,  # T-04.1-11: never shell-interpolate
            check=False,
        )
        try:
            report = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Validator crashed (returncode={result.returncode}).\n"
                            f"stdout: {result.stdout[:500]}\n"
                            f"stderr: {result.stderr[:500]}"
                        ),
                    }
                ],
                "is_error": True,
            }
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(report, indent=2, sort_keys=True),
                }
            ],
            "is_error": not bool(report.get("passed", False)),
        }

    server = create_sdk_mcp_server(
        name="validation",
        version="1.0.0",
        tools=[validate_mechanic],
    )
    # The SDK's McpSdkServerConfig dict does NOT echo the tools list back; we
    # attach it under a ``tools`` key for in-process introspection (testing,
    # diagnostics). The Agent SDK ignores extra keys when wiring mcp_servers.
    # ``McpSdkServerConfig`` is a TypedDict; cast through ``dict`` for the
    # extra-key write while preserving the documented runtime shape.
    out: dict[str, Any] = dict(server)
    out["tools"] = [validate_mechanic]
    return out
