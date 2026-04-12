"""Tests for XDG path resolution and UniverseMetadata model."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from token_world.models import UniverseMetadata
from token_world.universe.paths import get_config_dir, get_data_dir, get_universes_dir


class TestGetDataDir:
    """Tests for get_data_dir()."""

    def test_returns_path_ending_in_token_world(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Default data dir ends with 'token_world'."""
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        result = get_data_dir()
        assert result.name == "token_world"
        assert result.parent == Path.home() / ".local" / "share"

    def test_respects_xdg_data_home_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """XDG_DATA_HOME env var overrides the default path."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        result = get_data_dir()
        assert result == tmp_path / "token_world"


class TestGetUniversesDir:
    """Tests for get_universes_dir()."""

    def test_returns_universes_under_data_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Universes dir is a 'universes' subdirectory of data dir."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        result = get_universes_dir()
        assert result == tmp_path / "token_world" / "universes"


class TestGetConfigDir:
    """Tests for get_config_dir()."""

    def test_returns_path_ending_in_token_world(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Default config dir ends with 'token_world'."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        result = get_config_dir()
        assert result.name == "token_world"
        assert result.parent == Path.home() / ".config"

    def test_respects_xdg_config_home_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """XDG_CONFIG_HOME env var overrides the default path."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        result = get_config_dir()
        assert result == tmp_path / "token_world"


class TestUniverseMetadata:
    """Tests for the UniverseMetadata Pydantic model."""

    def test_validates_name_slug_created_at(self) -> None:
        """Model accepts valid name, slug, and created_at fields."""
        meta = UniverseMetadata(name="My World", slug="my-world")
        assert meta.name == "My World"
        assert meta.slug == "my-world"
        assert meta.created_at is not None
        assert meta.schema_version == 1

    def test_rejects_empty_name(self) -> None:
        """Model rejects an empty string for name."""
        with pytest.raises(ValidationError):
            UniverseMetadata(name="", slug="something")

    def test_rejects_blank_name(self) -> None:
        """Model rejects a name that is only whitespace."""
        with pytest.raises(ValidationError):
            UniverseMetadata(name="   ", slug="something")

    def test_strips_name_whitespace(self) -> None:
        """Model strips leading/trailing whitespace from name."""
        meta = UniverseMetadata(name="  My World  ", slug="my-world")
        assert meta.name == "My World"
