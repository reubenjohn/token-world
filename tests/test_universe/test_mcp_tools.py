"""Tests for the real MCP tool implementations (Plan 05-09).

Tests cover all three tools (resume_tick, rollback, list_mechanics) against the
real handle_request dispatcher. MockAnthropicClient is injected via monkeypatching
token_world.mcp_server._anthropic_factory so tests never call the real Anthropic API.

Test organisation:
  TestToolsList          -- tools/list method tests (tighten inputSchema assertions)
  TestListMechanics      -- list_mechanics: directory scan, filter, error paths
  TestResumeTick         -- resume_tick: ok/yield paths, param validation
  TestRollback           -- rollback: snapshot restore, param validation
  TestErrorHandling      -- -32603 internal error, no-stack-trace-leak
  TestAntiPatterns       -- stub string absent, JSON-serializable payloads
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import token_world.mcp_server as mcp_module
from token_world.mcp_server import handle_request

# ---------------------------------------------------------------------------
# Anthropic SDK test double (same pattern as tests/test_engine/conftest.py)
# ---------------------------------------------------------------------------


class _Usage:
    input_tokens = 100
    output_tokens = 20


class _Block:
    def __init__(self, text: str) -> None:
        self.text = text


class _Response:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]
        self.usage = _Usage()


class _MessagesProxy:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs: Any) -> _Response:
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError("MockAnthropicClient ran out of responses")
        return _Response(self._responses.pop(0))


class MockAnthropicClient:
    """Test double for anthropic.Anthropic."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.messages = _MessagesProxy(self._responses)


# ---------------------------------------------------------------------------
# Canned classifier / observer responses
# ---------------------------------------------------------------------------

_OK_PICKUP = json.dumps(
    {
        "kind": "ok",
        "classified": {"verb": "pickup", "actor": "alice", "target": "rock_1", "params": {}},
        "confidence": 0.95,
    }
)
_OK_NOMATCH = json.dumps(
    {
        "kind": "ok",
        "classified": {
            "verb": "frobnicate",
            "actor": "alice",
            "target": None,
            "params": {},
        },
        "confidence": 0.90,
    }
)
_OBSERVATION = "You bend down and pick up the rock."

# ---------------------------------------------------------------------------
# Minimal mechanic source snippets
# ---------------------------------------------------------------------------

_PICKUP_MECHANIC_SOURCE = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import VerbMatcher

class Pickup(Mechanic):
    id = "pickup"
    description = "Pick up a target entity"
    voluntary = True
    tags = []
    def watches(self):
        return [VerbMatcher(verb="pickup")]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        return [ctx.set(ctx.target, "held_by", ctx.actor)]
"""

_AARDVARK_MECHANIC_SOURCE = """
from token_world.mechanic.protocol import Mechanic, CheckResult
from token_world.mechanic.matchers import VerbMatcher

class AardvarkMechanic(Mechanic):
    id = "aardvark"
    description = "Aardvark mechanic"
    voluntary = True
    tags = ["animal"]
    def watches(self):
        return [VerbMatcher(verb="aardvark")]
    def check(self, ctx):
        return CheckResult(passed=True)
    def apply(self, ctx):
        return []
"""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def call_tool(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    req_id: int = 1,
) -> dict:
    """Dispatch a tools/call JSON-RPC request and return the full response dict."""
    return handle_request(
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
    )


def parse_tool_result(response: dict) -> dict:
    """Extract and JSON-parse the text payload from a tools/call success response."""
    content = response["result"]["content"]
    assert len(content) == 1
    assert content[0]["type"] == "text"
    return json.loads(content[0]["text"])


@pytest.fixture
def tmp_universe(tmp_path: Path) -> Path:
    """Temp universe folder with minimum scaffolding."""
    (tmp_path / "mechanics").mkdir()
    (tmp_path / "diagnostics").mkdir()
    (tmp_path / "tick_summaries").mkdir()
    (tmp_path / "universe.yaml").write_text(
        "universe_seed: 424242\nengine:\n  max_chain_depth: 10\n  classifier_min_confidence: 0.6\n",
        encoding="utf-8",
    )
    (tmp_path / "conservation.yaml").write_text("conserved_properties: []\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def mock_client_factory(monkeypatch: pytest.MonkeyPatch):
    """Return a helper that patches _anthropic_factory with a fresh MockAnthropicClient."""

    def _patch(responses: list[str]) -> MockAnthropicClient:
        client = MockAnthropicClient(responses)
        monkeypatch.setattr(mcp_module, "_anthropic_factory", lambda: client)
        return client

    return _patch


# ---------------------------------------------------------------------------
# TestToolsList
# ---------------------------------------------------------------------------


class TestToolsList:
    def test_tools_list_returns_three_tools_with_required_fields(self) -> None:
        """tools/list returns 3 tools, each with name, description, inputSchema.required."""
        response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        tools = response["result"]["tools"]
        assert len(tools) == 3
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert "required" in tool["inputSchema"]

    def test_tools_list_resume_tick_requires_universe_action_actor(self) -> None:
        """resume_tick inputSchema.required == ['universe_path', 'action_text', 'actor']."""
        response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        tools = response["result"]["tools"]
        rt = next(t for t in tools if t["name"] == "resume_tick")
        assert set(rt["inputSchema"]["required"]) == {"universe_path", "action_text", "actor"}

    def test_tools_list_rollback_requires_universe_and_snapshot(self) -> None:
        """rollback inputSchema.required includes universe_path and snapshot_id."""
        response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        tools = response["result"]["tools"]
        rb = next(t for t in tools if t["name"] == "rollback")
        assert set(rb["inputSchema"]["required"]) == {"universe_path", "snapshot_id"}

    def test_tools_list_list_mechanics_requires_only_universe_path(self) -> None:
        """list_mechanics only requires universe_path (filter is optional)."""
        response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        tools = response["result"]["tools"]
        lm = next(t for t in tools if t["name"] == "list_mechanics")
        assert lm["inputSchema"]["required"] == ["universe_path"]


# ---------------------------------------------------------------------------
# TestListMechanics
# ---------------------------------------------------------------------------


class TestListMechanics:
    def test_list_mechanics_returns_empty_for_empty_mechanics_dir(self, tmp_universe: Path) -> None:
        """list_mechanics with empty mechanics/ returns count=0, mechanics=[]."""
        response = call_tool("list_mechanics", {"universe_path": str(tmp_universe)})
        assert "result" in response
        payload = parse_tool_result(response)
        assert payload["count"] == 0
        assert payload["mechanics"] == []

    def test_list_mechanics_returns_registered_mechanics(self, tmp_universe: Path) -> None:
        """list_mechanics returns both mechanics with expected fields."""
        (tmp_universe / "mechanics" / "pickup.py").write_text(
            _PICKUP_MECHANIC_SOURCE, encoding="utf-8"
        )
        (tmp_universe / "mechanics" / "aardvark.py").write_text(
            _AARDVARK_MECHANIC_SOURCE, encoding="utf-8"
        )
        response = call_tool("list_mechanics", {"universe_path": str(tmp_universe)})
        payload = parse_tool_result(response)
        assert payload["count"] == 2
        ids = [m["id"] for m in payload["mechanics"]]
        assert "pickup" in ids
        assert "aardvark" in ids
        # Each entry has expected fields
        for m in payload["mechanics"]:
            assert "id" in m
            assert "description" in m
            assert "voluntary" in m
            assert "tags" in m

    def test_list_mechanics_filter_substring(self, tmp_universe: Path) -> None:
        """list_mechanics with filter='ark' returns only aardvark."""
        (tmp_universe / "mechanics" / "pickup.py").write_text(
            _PICKUP_MECHANIC_SOURCE, encoding="utf-8"
        )
        (tmp_universe / "mechanics" / "aardvark.py").write_text(
            _AARDVARK_MECHANIC_SOURCE, encoding="utf-8"
        )
        response = call_tool(
            "list_mechanics", {"universe_path": str(tmp_universe), "filter": "ark"}
        )
        payload = parse_tool_result(response)
        assert payload["count"] == 1
        assert payload["mechanics"][0]["id"] == "aardvark"

    def test_list_mechanics_missing_universe_path_returns_invalid_params(self) -> None:
        """list_mechanics with no universe_path returns -32602."""
        response = call_tool("list_mechanics", {})
        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "universe_path" in response["error"]["message"]

    def test_list_mechanics_path_traversal_rejected(self, tmp_path: Path) -> None:
        """list_mechanics with '../etc' universe_path returns -32602 mentioning '..'."""
        response = call_tool("list_mechanics", {"universe_path": "../etc"})
        assert "error" in response
        assert response["error"]["code"] == -32602
        msg = response["error"]["message"]
        assert ".." in msg or "disallowed" in msg

    def test_list_mechanics_nonexistent_path_returns_invalid_params(self, tmp_path: Path) -> None:
        """list_mechanics with non-existent path returns -32602."""
        response = call_tool("list_mechanics", {"universe_path": str(tmp_path / "does_not_exist")})
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_list_mechanics_payload_is_json_serializable(self, tmp_universe: Path) -> None:
        """list_mechanics result payload round-trips through json.dumps without error."""
        (tmp_universe / "mechanics" / "pickup.py").write_text(
            _PICKUP_MECHANIC_SOURCE, encoding="utf-8"
        )
        response = call_tool("list_mechanics", {"universe_path": str(tmp_universe)})
        # Must not raise
        json.dumps(response)


# ---------------------------------------------------------------------------
# TestResumeTick
# ---------------------------------------------------------------------------


class TestResumeTick:
    def test_resume_tick_execute_path_returns_observation(
        self, tmp_universe: Path, mock_client_factory: Any
    ) -> None:
        """resume_tick execute path returns kind=ok with observation text."""
        from token_world.graph import KnowledgeGraph

        # Seed graph with required nodes + persist to universe.db
        kg = KnowledgeGraph(db_path=tmp_universe / "universe.db")
        kg.add_node("alice", node_type="agent")
        kg.add_node("room_1", node_type="entity")
        kg.add_node("rock_1", node_type="entity")
        kg.add_edge("alice", "room_1", type="location")
        kg.add_edge("room_1", "rock_1", type="contains")
        kg.save()

        (tmp_universe / "mechanics" / "pickup.py").write_text(
            _PICKUP_MECHANIC_SOURCE, encoding="utf-8"
        )

        mock_client_factory([_OK_PICKUP, _OBSERVATION])

        response = call_tool(
            "resume_tick",
            {
                "universe_path": str(tmp_universe),
                "action_text": "pick up the rock",
                "actor": "alice",
            },
        )
        assert "result" in response, response
        payload = parse_tool_result(response)
        assert payload["kind"] == "ok"
        assert "observation" in payload
        assert isinstance(payload["observation"], str)
        assert len(payload["observation"]) > 0

    def test_resume_tick_yield_path_returns_yield_signal_json(
        self, tmp_universe: Path, mock_client_factory: Any
    ) -> None:
        """resume_tick with no matching mechanic returns kind=yielded with yield_signal."""
        from token_world.graph import KnowledgeGraph

        kg = KnowledgeGraph(db_path=tmp_universe / "universe.db")
        kg.add_node("alice", node_type="agent")
        kg.save()

        # No mechanics registered — classifier returns ok but no match → yield
        mock_client_factory([_OK_NOMATCH])

        response = call_tool(
            "resume_tick",
            {
                "universe_path": str(tmp_universe),
                "action_text": "frobnicate the air",
                "actor": "alice",
            },
        )
        assert "result" in response, response
        payload = parse_tool_result(response)
        assert payload["kind"] == "yielded"
        assert "yield_signal" in payload
        assert "tick_id" in payload["yield_signal"]

    def test_resume_tick_missing_action_text_returns_invalid_params(
        self, tmp_universe: Path
    ) -> None:
        """resume_tick without action_text returns -32602 mentioning action_text."""
        response = call_tool(
            "resume_tick",
            {"universe_path": str(tmp_universe), "actor": "alice"},
        )
        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "action_text" in response["error"]["message"]

    def test_resume_tick_missing_actor_returns_invalid_params(self, tmp_universe: Path) -> None:
        """resume_tick without actor returns -32602 mentioning actor."""
        response = call_tool(
            "resume_tick",
            {"universe_path": str(tmp_universe), "action_text": "do something"},
        )
        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "actor" in response["error"]["message"]

    def test_resume_tick_empty_action_text_rejected(self, tmp_universe: Path) -> None:
        """resume_tick with action_text='' returns -32602."""
        response = call_tool(
            "resume_tick",
            {
                "universe_path": str(tmp_universe),
                "action_text": "",
                "actor": "alice",
            },
        )
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_resume_tick_missing_universe_path_returns_invalid_params(self) -> None:
        """resume_tick with no universe_path returns -32602."""
        response = call_tool(
            "resume_tick",
            {"action_text": "do something", "actor": "alice"},
        )
        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "universe_path" in response["error"]["message"]

    def test_resume_tick_path_traversal_rejected(self) -> None:
        """resume_tick with '../secret' universe_path returns -32602."""
        response = call_tool(
            "resume_tick",
            {
                "universe_path": "../secret",
                "action_text": "do something",
                "actor": "alice",
            },
        )
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_resume_tick_payload_is_json_serializable(
        self, tmp_universe: Path, mock_client_factory: Any
    ) -> None:
        """resume_tick response round-trips through json.dumps without error."""
        from token_world.graph import KnowledgeGraph

        kg = KnowledgeGraph(db_path=tmp_universe / "universe.db")
        kg.add_node("alice", node_type="agent")
        kg.save()

        mock_client_factory([_OK_NOMATCH])

        response = call_tool(
            "resume_tick",
            {
                "universe_path": str(tmp_universe),
                "action_text": "frobnicate",
                "actor": "alice",
            },
        )
        # Must not raise
        json.dumps(response)


# ---------------------------------------------------------------------------
# TestRollback
# ---------------------------------------------------------------------------


class TestRollback:
    def test_rollback_missing_snapshot_id_returns_invalid_params(self, tmp_universe: Path) -> None:
        """rollback without snapshot_id returns -32602."""
        response = call_tool("rollback", {"universe_path": str(tmp_universe)})
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_rollback_non_integer_snapshot_id_returns_invalid_params(
        self, tmp_universe: Path
    ) -> None:
        """rollback with snapshot_id='not an int' returns -32602."""
        response = call_tool(
            "rollback",
            {"universe_path": str(tmp_universe), "snapshot_id": "not an int"},
        )
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_rollback_nonexistent_db_returns_invalid_params(self, tmp_universe: Path) -> None:
        """rollback when universe.db doesn't exist returns -32602."""
        response = call_tool("rollback", {"universe_path": str(tmp_universe), "snapshot_id": 1})
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_rollback_restores_graph_state(self, tmp_universe: Path) -> None:
        """rollback(snapshot_id) restores graph to the state at that snapshot."""
        from token_world.graph import KnowledgeGraph

        kg = KnowledgeGraph(db_path=tmp_universe / "universe.db")
        kg.add_node("alice", node_type="agent")
        kg.set("alice", "coin", 10)
        snapshot_id = kg.snapshot(tick_id=3, summary="before mutation")

        # Mutate after snapshot
        kg.set("alice", "coin", 0)
        kg.save()

        # Rollback via MCP tool
        response = call_tool(
            "rollback",
            {"universe_path": str(tmp_universe), "snapshot_id": snapshot_id},
        )
        assert "result" in response, response
        payload = parse_tool_result(response)
        assert payload["ok"] is True
        assert payload["snapshot_id"] == snapshot_id

        # Reload graph and verify coin restored to 10
        kg2 = KnowledgeGraph(db_path=tmp_universe / "universe.db")
        kg2.load()
        assert kg2.query("alice", "coin") == 10

    def test_rollback_returns_restored_tick_id(self, tmp_universe: Path) -> None:
        """rollback response includes restored_to_tick matching the snapshot's tick_id."""
        from token_world.graph import KnowledgeGraph

        kg = KnowledgeGraph(db_path=tmp_universe / "universe.db")
        kg.add_node("alice", node_type="agent")
        snapshot_id = kg.snapshot(tick_id=5, summary="tick 5 snap")
        kg.save()

        response = call_tool(
            "rollback",
            {"universe_path": str(tmp_universe), "snapshot_id": snapshot_id},
        )
        assert "result" in response, response
        payload = parse_tool_result(response)
        assert payload["ok"] is True
        assert payload["restored_to_tick"] == 5

    def test_rollback_missing_universe_path_returns_invalid_params(self) -> None:
        """rollback without universe_path returns -32602."""
        response = call_tool("rollback", {"snapshot_id": 1})
        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "universe_path" in response["error"]["message"]


# ---------------------------------------------------------------------------
# TestErrorHandling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_unknown_tool_returns_invalid_params(self, tmp_universe: Path) -> None:
        """Calling unknown tool 'frobnicate' returns -32602 mentioning 'Unknown tool'."""
        response = call_tool("frobnicate", {"universe_path": str(tmp_universe)})
        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "Unknown tool" in response["error"]["message"]

    def test_internal_error_returns_32603_with_generic_message(
        self, tmp_universe: Path, mock_client_factory: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WR-04: SimulationEngine.run_tick crash → -32603 with generic 'Internal error'
        message only; exc details and stack trace must NOT appear in the client response."""
        from token_world.graph import KnowledgeGraph

        kg = KnowledgeGraph(db_path=tmp_universe / "universe.db")
        kg.add_node("alice", node_type="agent")
        kg.save()

        mock_client_factory([_OK_NOMATCH])

        from token_world.engine import SimulationEngine

        monkeypatch.setattr(
            SimulationEngine,
            "run_tick",
            lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        response = call_tool(
            "resume_tick",
            {
                "universe_path": str(tmp_universe),
                "action_text": "something",
                "actor": "alice",
            },
        )
        assert "error" in response
        assert response["error"]["code"] == -32603
        # Generic message only — exc repr must NOT be in client-facing message
        assert "boom" not in response["error"]["message"], (
            "Internal error message must not leak exception details to the client"
        )
        # Stack trace must NOT appear in the error message
        assert "Traceback" not in response["error"]["message"]
        # The message must be the fixed generic string
        assert response["error"]["message"] == "Internal error"


# ---------------------------------------------------------------------------
# TestAntiPatterns
# ---------------------------------------------------------------------------


class TestAntiPatterns:
    def test_stub_string_no_longer_in_responses(
        self, tmp_universe: Path, mock_client_factory: Any
    ) -> None:
        """'This is a Phase 0 stub.' does not appear in any tool response."""
        from token_world.graph import KnowledgeGraph

        kg = KnowledgeGraph(db_path=tmp_universe / "universe.db")
        kg.add_node("alice", node_type="agent")
        kg.save()

        mock_client_factory([_OK_NOMATCH])

        response = call_tool(
            "resume_tick",
            {
                "universe_path": str(tmp_universe),
                "action_text": "something",
                "actor": "alice",
            },
        )
        resp_str = json.dumps(response)
        assert "This is a Phase 0 stub." not in resp_str

    def test_phase0_stub_string_not_in_mcp_server_module(self) -> None:
        """Verify the stub string is not in the mcp_server source file."""
        import importlib.util

        spec = importlib.util.find_spec("token_world.mcp_server")
        assert spec is not None
        source_path = Path(spec.origin)
        source = source_path.read_text(encoding="utf-8")
        assert "This is a Phase 0 stub." not in source
