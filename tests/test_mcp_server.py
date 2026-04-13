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

    def test_tools_list_returns_three_tools(self) -> None:
        """tools/list returns exactly 3 tools (register_mechanic dropped per D-10)."""
        response = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = response["result"]["tools"]
        assert len(tools) == 3

    def test_tools_list_contains_expected_names(self) -> None:
        """tools/list returns the three expected tool names."""
        response = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tool_names = {t["name"] for t in response["result"]["tools"]}
        assert tool_names == {"resume_tick", "rollback", "list_mechanics"}

    def test_register_mechanic_is_not_exposed(self) -> None:
        """register_mechanic was removed as an MCP tool (D-10); authoring is
        an operator-side SDLC activity, not a simulation tool."""
        response = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tool_names = {t["name"] for t in response["result"]["tools"]}
        assert "register_mechanic" not in tool_names

    def test_tools_have_input_schemas(self) -> None:
        """Each tool has an inputSchema."""
        response = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        for tool in response["result"]["tools"]:
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"


class TestHandleToolsCall:
    """Tests for the tools/call method."""

    def test_tools_call_missing_universe_path_returns_error(self) -> None:
        """tools/call without universe_path returns a JSON-RPC error (not a stub message)."""
        response = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "resume_tick", "arguments": {}},
            }
        )
        # Real implementation returns -32602 on missing universe_path (not stub text)
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_tools_call_unknown_tool_returns_error(self) -> None:
        """tools/call with unknown tool name returns -32602 error."""
        response = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "rollback", "arguments": {}},
            }
        )
        # rollback without required params returns -32602
        assert "error" in response
        assert response["error"]["code"] == -32602


class TestHandleUnknownMethod:
    """Tests for unknown/invalid methods."""

    def test_unknown_method_returns_error(self) -> None:
        """Unknown method returns JSON-RPC error with code -32601."""
        response = handle_request({"jsonrpc": "2.0", "id": 4, "method": "unknown/method"})
        assert "error" in response
        assert response["error"]["code"] == -32601

    def test_notifications_initialized_returns_none(self) -> None:
        """notifications/initialized returns None (no response for notifications)."""
        response = handle_request(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
        )
        assert response is None


class TestToolsConstant:
    """Tests for the TOOLS constant."""

    def test_tools_constant_has_three_entries(self) -> None:
        """TOOLS constant has exactly 3 tool definitions (D-10 drops
        register_mechanic)."""
        assert len(TOOLS) == 3

    def test_rollback_requires_snapshot_id(self) -> None:
        """rollback tool requires snapshot_id parameter."""
        rollback = next(t for t in TOOLS if t["name"] == "rollback")
        assert "snapshot_id" in rollback["inputSchema"]["properties"]
        assert "snapshot_id" in rollback["inputSchema"]["required"]

    def test_register_mechanic_absent_from_tools_constant(self) -> None:
        """register_mechanic must not be in TOOLS (D-10)."""
        names = {t["name"] for t in TOOLS}
        assert "register_mechanic" not in names
