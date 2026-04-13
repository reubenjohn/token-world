"""Unit tests for the operator validation tool wrapper (Task 1).

Wraps Phase 4's ``token-world validate-mechanic ... --format json`` CLI as an
in-process MCP tool the mechanic-author subagent can call. Mocks subprocess so
no real validator is invoked.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from token_world.operator.validation_tool import build_validation_server

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_validate_tool(server: Any) -> Any:
    """Pull the ``validate_mechanic`` SdkMcpTool object out of a server config."""
    # ``create_sdk_mcp_server`` returns a McpSdkServerConfig dict shape with an
    # ``instance`` attribute carrying the MCP Server, but the tools are also
    # registered on the original list passed in. We probe whichever is present.
    if hasattr(server, "tools"):
        tools = server.tools
    elif isinstance(server, dict) and "tools" in server:
        tools = server["tools"]
    else:
        # Fall back: the SDK keeps a private reference; introspect via dataclass
        instance = getattr(server, "instance", None)
        tools = getattr(instance, "tools", None) if instance else None
    assert tools, f"No tools registered on server: {server!r}"
    by_name = {getattr(t, "name", None): t for t in tools}
    assert "validate_mechanic" in by_name, f"validate_mechanic not in {sorted(by_name)}"
    return by_name["validate_mechanic"]


async def _invoke(tool: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Invoke the tool's underlying handler in-process."""
    handler = getattr(tool, "handler", None)
    if handler is None:
        # Some SDK builds expose the callable directly on the tool object.
        handler = tool
    result = await handler(args)
    assert isinstance(result, dict)
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_validation_server_has_validate_mechanic_tool(universe: Path) -> None:
    server = build_validation_server(universe)
    tool = _extract_validate_tool(server)
    assert getattr(tool, "name", None) == "validate_mechanic"


@pytest.mark.asyncio
async def test_validate_mechanic_returns_is_error_false_on_pass(
    universe: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = build_validation_server(universe)
    tool = _extract_validate_tool(server)

    fake_completed = MagicMock(spec=subprocess.CompletedProcess)
    fake_completed.returncode = 0
    fake_completed.stdout = json.dumps(
        {"passed": True, "findings": [], "module_path": "mechanics/pickup.py"}
    )
    fake_completed.stderr = ""
    monkeypatch.setattr(
        "token_world.operator.validation_tool.subprocess.run",
        lambda *a, **k: fake_completed,
    )

    out = await _invoke(tool, {"module_path": "mechanics/pickup.py"})
    assert out.get("is_error") is False
    text = out["content"][0]["text"]
    assert "passed" in text


@pytest.mark.asyncio
async def test_validate_mechanic_returns_is_error_true_on_fail(
    universe: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = build_validation_server(universe)
    tool = _extract_validate_tool(server)

    fake_completed = MagicMock(spec=subprocess.CompletedProcess)
    fake_completed.returncode = 1
    fake_completed.stdout = json.dumps(
        {
            "passed": False,
            "findings": [
                {
                    "stage": "ast",
                    "rule": "no-raw-graph-access",
                    "severity": "error",
                    "message": "raw NetworkX import detected",
                    "path": "mechanics/x.py",
                    "line": 3,
                }
            ],
            "module_path": "mechanics/x.py",
        }
    )
    fake_completed.stderr = ""
    monkeypatch.setattr(
        "token_world.operator.validation_tool.subprocess.run",
        lambda *a, **k: fake_completed,
    )

    out = await _invoke(tool, {"module_path": "mechanics/x.py"})
    assert out.get("is_error") is True


@pytest.mark.asyncio
async def test_validate_mechanic_crash_returns_is_error_true_text_stderr(
    universe: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = build_validation_server(universe)
    tool = _extract_validate_tool(server)

    fake_completed = MagicMock(spec=subprocess.CompletedProcess)
    fake_completed.returncode = 2
    fake_completed.stdout = "Traceback (most recent call last):\n  File ..."
    fake_completed.stderr = "ImportError: cannot import name X"
    monkeypatch.setattr(
        "token_world.operator.validation_tool.subprocess.run",
        lambda *a, **k: fake_completed,
    )

    out = await _invoke(tool, {"module_path": "mechanics/broken.py"})
    assert out.get("is_error") is True
    text = out["content"][0]["text"]
    assert "ImportError" in text or "stderr" in text


@pytest.mark.asyncio
async def test_validate_mechanic_subprocess_is_shell_false(
    universe: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-04.1-11: never shell-interpolate."""
    server = build_validation_server(universe)
    tool = _extract_validate_tool(server)

    captured: dict[str, Any] = {}

    def fake_run(*args: Any, **kwargs: Any) -> Any:
        captured["args"] = args
        captured["kwargs"] = kwargs
        m = MagicMock(spec=subprocess.CompletedProcess)
        m.returncode = 0
        m.stdout = json.dumps({"passed": True, "findings": []})
        m.stderr = ""
        return m

    monkeypatch.setattr("token_world.operator.validation_tool.subprocess.run", fake_run)
    await _invoke(tool, {"module_path": "mechanics/pickup.py"})
    assert captured["kwargs"].get("shell", True) is False, (
        f"shell must be False to mitigate T-04.1-11; got kwargs={captured['kwargs']}"
    )


@pytest.mark.asyncio
async def test_validate_mechanic_module_path_arg_is_passed_literal(
    universe: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The module_path string must appear verbatim as a separate argv element."""
    server = build_validation_server(universe)
    tool = _extract_validate_tool(server)

    captured: dict[str, Any] = {}

    def fake_run(*args: Any, **kwargs: Any) -> Any:
        captured["argv"] = args[0]
        m = MagicMock(spec=subprocess.CompletedProcess)
        m.returncode = 0
        m.stdout = json.dumps({"passed": True, "findings": []})
        m.stderr = ""
        return m

    monkeypatch.setattr("token_world.operator.validation_tool.subprocess.run", fake_run)
    await _invoke(tool, {"module_path": "mechanics/pickup.py"})
    argv = captured["argv"]
    assert "mechanics/pickup.py" in argv, f"module_path missing from argv: {argv}"
    assert "validate-mechanic" in argv, f"validate-mechanic command missing: {argv}"
    assert "--format" in argv and "json" in argv, f"--format json missing: {argv}"
