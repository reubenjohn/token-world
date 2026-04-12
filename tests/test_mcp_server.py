"""Tests for the MCP stdio server stub."""

from __future__ import annotations

from token_world.mcp_server import TOOLS, handle_request


class TestHandleInitialize:
    """Tests for the initialize method."""

    def test_initialize_returns_protocol_version(self) -> None:
        """Initialize returns protocolVersion in result."""
        response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert response["result"]["protocolVersion"] == "2024-11-05"

    def test_initialize_returns_server_info(self) -> None:
        """Initialize returns serverInfo with name and version."""
        response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        info = response["result"]["serverInfo"]
        assert info["name"] == "token-world"
        assert info["version"] == "0.1.0"

    def test_initialize_returns_tools_capability(self) -> None:
        """Initialize returns tools in capabilities."""
        response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert "tools" in response["result"]["capabilities"]


class TestHandleToolsList:
    """Tests for the tools/list method."""

    def test_tools_list_returns_four_tools(self) -> None:
        """tools/list returns exactly 4 tools."""
        response = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = response["result"]["tools"]
        assert len(tools) == 4

    def test_tools_list_contains_expected_names(self) -> None:
        """tools/list returns the four expected tool names."""
        response = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tool_names = {t["name"] for t in response["result"]["tools"]}
        assert tool_names == {"resume_tick", "rollback", "list_mechanics", "register_mechanic"}

    def test_tools_have_input_schemas(self) -> None:
        """Each tool has an inputSchema."""
        response = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        for tool in response["result"]["tools"]:
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"


class TestHandleToolsCall:
    """Tests for the tools/call method."""

    def test_tools_call_returns_not_implemented(self) -> None:
        """tools/call returns a not-implemented message for any tool."""
        response = handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "resume_tick", "arguments": {}},
        })
        content = response["result"]["content"]
        assert len(content) == 1
        assert "not yet implemented" in content[0]["text"].lower()
        assert content[0]["type"] == "text"

    def test_tools_call_includes_tool_name_in_response(self) -> None:
        """tools/call response includes the requested tool name."""
        response = handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "rollback", "arguments": {}},
        })
        assert "rollback" in response["result"]["content"][0]["text"]


class TestHandleUnknownMethod:
    """Tests for unknown/invalid methods."""

    def test_unknown_method_returns_error(self) -> None:
        """Unknown method returns JSON-RPC error with code -32601."""
        response = handle_request({"jsonrpc": "2.0", "id": 4, "method": "unknown/method"})
        assert "error" in response
        assert response["error"]["code"] == -32601

    def test_notifications_initialized_returns_none(self) -> None:
        """notifications/initialized returns None (no response for notifications)."""
        response = handle_request({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })
        assert response is None


class TestToolsConstant:
    """Tests for the TOOLS constant."""

    def test_tools_constant_has_four_entries(self) -> None:
        """TOOLS constant has exactly 4 tool definitions."""
        assert len(TOOLS) == 4

    def test_rollback_requires_snapshot_id(self) -> None:
        """rollback tool requires snapshot_id parameter."""
        rollback = next(t for t in TOOLS if t["name"] == "rollback")
        assert "snapshot_id" in rollback["inputSchema"]["properties"]
        assert "snapshot_id" in rollback["inputSchema"]["required"]

    def test_register_mechanic_requires_path(self) -> None:
        """register_mechanic tool requires path parameter."""
        reg = next(t for t in TOOLS if t["name"] == "register_mechanic")
        assert "path" in reg["inputSchema"]["properties"]
        assert "path" in reg["inputSchema"]["required"]
