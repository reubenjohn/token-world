"""Unit tests for the operator's .mcp.json loader (Task 1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from token_world.operator.mcp_client import load_universe_mcp_config


def test_load_mcp_config_reads_universe_file(universe: Path) -> None:
    """Universe fixture already scaffolds .mcp.json with mcpServers wrapper."""
    cfg = load_universe_mcp_config(universe)
    assert isinstance(cfg, dict)
    assert "token-world" in cfg
    inner = cfg["token-world"]
    assert isinstance(inner, dict)
    assert "command" in inner


def test_load_mcp_config_strips_outer_wrapper(tmp_path: Path) -> None:
    """SDK expects flat dict; .mcp.json wraps under 'mcpServers'."""
    (tmp_path / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "token-world": {"command": "uvx", "args": ["token-world-mcp"]},
                    "extra": {"command": "x"},
                }
            }
        )
    )
    cfg = load_universe_mcp_config(tmp_path)
    assert set(cfg.keys()) == {"token-world", "extra"}
    assert "mcpServers" not in cfg


def test_load_mcp_config_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError) as excinfo:
        load_universe_mcp_config(tmp_path)
    assert ".mcp.json" in str(excinfo.value)


def test_load_mcp_config_rejects_malformed(tmp_path: Path) -> None:
    (tmp_path / ".mcp.json").write_text("{not valid json")
    with pytest.raises(json.JSONDecodeError):
        load_universe_mcp_config(tmp_path)


def test_load_mcp_config_rejects_non_object_servers(tmp_path: Path) -> None:
    (tmp_path / ".mcp.json").write_text(json.dumps({"mcpServers": ["not", "a", "dict"]}))
    with pytest.raises(ValueError) as excinfo:
        load_universe_mcp_config(tmp_path)
    assert "mcpServers" in str(excinfo.value)


def test_load_mcp_config_empty_servers_returns_empty_dict(tmp_path: Path) -> None:
    (tmp_path / ".mcp.json").write_text(json.dumps({"mcpServers": {}}))
    cfg = load_universe_mcp_config(tmp_path)
    assert cfg == {}


def test_load_mcp_config_no_mcpservers_key_returns_empty(tmp_path: Path) -> None:
    """Some user .mcp.json files omit the wrapper entirely; treat as empty."""
    (tmp_path / ".mcp.json").write_text(json.dumps({"other": "stuff"}))
    cfg = load_universe_mcp_config(tmp_path)
    assert cfg == {}
