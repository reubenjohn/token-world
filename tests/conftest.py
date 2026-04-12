"""Shared test fixtures for Token World tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set XDG_DATA_HOME to a temp dir and return the universes path."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    universes = tmp_path / "token_world" / "universes"
    universes.mkdir(parents=True)
    return universes
