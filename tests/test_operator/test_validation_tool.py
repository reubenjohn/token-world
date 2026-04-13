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

from token_world.operator.validation_tool import (
    build_validate_mechanic_tool,
    build_validation_server,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    tool = build_validate_mechanic_tool(universe)
    assert getattr(tool, "name", None) == "validate_mechanic"


def test_validation_server_returns_well_formed_sdk_server_config(universe: Path) -> None:
    """build_validation_server returns the SDK's McpSdkServerConfig dict shape.

    The dict deliberately does NOT include the tools list — adding it breaks
    the SDK's CLI subprocess transport which JSON-serialises mcp_servers
    (SdkMcpTool is not JSON-serialisable). Use build_validate_mechanic_tool
    for in-process tool introspection.
    """
    server = build_validation_server(universe)
    assert isinstance(server, dict)
    assert server.get("type") == "sdk"
    assert server.get("name") == "validation"
    assert "instance" in server
    # Critical invariant — tools must NOT be in the dict (would break the SDK).
    assert "tools" not in server, (
        "tools key in SDK server config breaks JSON serialisation of mcp_servers"
    )


@pytest.mark.asyncio
async def test_validate_mechanic_returns_is_error_false_on_pass(
    universe: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = build_validate_mechanic_tool(universe)

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
    tool = build_validate_mechanic_tool(universe)

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
    tool = build_validate_mechanic_tool(universe)

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
    tool = build_validate_mechanic_tool(universe)

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
    tool = build_validate_mechanic_tool(universe)

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
