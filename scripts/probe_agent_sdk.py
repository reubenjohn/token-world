#!/usr/bin/env python3
"""Probe the claude-agent-sdk surface used by the operator harness.

Prints the field set of the dataclasses + types we depend on so we can
write the harness against the actual installed SDK version's API rather
than guessing or relying on docs that may be out of date.

Usage:
    uv run python scripts/probe_agent_sdk.py

This is a one-shot diagnostic — keep it small. The output is consumed by
the human/agent reading it; nothing depends on it programmatically.
"""

from __future__ import annotations

import dataclasses
import inspect

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SdkMcpTool,
    SystemMessage,
    create_sdk_mcp_server,
    query,
    tool,
)


def _fields(cls: type) -> list[str]:
    if not dataclasses.is_dataclass(cls):
        return [f"<not dataclass>: {[a for a in dir(cls) if not a.startswith('_')]}"]
    return sorted(f.name for f in dataclasses.fields(cls))


def main() -> None:
    print("=== Dataclass fields ===")
    for cls in (
        ClaudeAgentOptions,
        AgentDefinition,
        ResultMessage,
        AssistantMessage,
        SystemMessage,
        SdkMcpTool,
    ):
        print(f"{cls.__name__}: {_fields(cls)}")

    print("\n=== Function signatures ===")
    print(f"query: {inspect.signature(query)}")
    print(f"tool: {inspect.signature(tool)}")
    print(f"create_sdk_mcp_server: {inspect.signature(create_sdk_mcp_server)}")

    # Build a sample server and inspect the result shape
    @tool("dummy", "dummy", {"x": str})
    async def _dummy(args: dict) -> dict:  # type: ignore[type-arg]
        return {"content": [{"type": "text", "text": "ok"}]}

    server = create_sdk_mcp_server(name="probe", tools=[_dummy])
    print(f"\n=== create_sdk_mcp_server() return shape ===")
    print(f"type: {type(server).__name__}")
    print(f"value: {server!r}")

    print(f"\n=== SdkMcpTool dummy attributes ===")
    print(f"type: {type(_dummy).__name__}")
    public = [a for a in dir(_dummy) if not a.startswith("_")]
    for a in public:
        v = getattr(_dummy, a)
        if not callable(v):
            print(f"  {a} = {v!r}")
        else:
            print(f"  {a}() callable")


if __name__ == "__main__":
    main()
