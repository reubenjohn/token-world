"""Tests for UniverseManager CRUD operations and CLI commands."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from token_world.cli import cli
from token_world.universe.manager import UniverseManager


class TestManagerCreate:
    """Tests for UniverseManager.create()."""

    def test_create_makes_folder_with_slug(self, tmp_data_dir: Path) -> None:
        """Creating a universe produces a folder named with the slugified name."""
        manager = UniverseManager(data_dir=tmp_data_dir)
        path = manager.create("My Test World")
        assert path.name == "my-test-world"
        assert path.exists()
        assert path.is_dir()

    def test_create_duplicate_raises_file_exists(self, tmp_data_dir: Path) -> None:
        """Creating a universe with a name that already exists raises FileExistsError."""
        manager = UniverseManager(data_dir=tmp_data_dir)
        manager.create("My Test World")
        with pytest.raises(FileExistsError):
            manager.create("My Test World")

    def test_create_empty_name_raises_value_error(self, tmp_data_dir: Path) -> None:
        """Creating a universe with an empty name raises ValueError."""
        manager = UniverseManager(data_dir=tmp_data_dir)
        with pytest.raises(ValueError):
            manager.create("")

    def test_create_initializes_db_with_metadata(self, tmp_data_dir: Path) -> None:
        """Created universe folder contains universe.db with metadata table."""
        manager = UniverseManager(data_dir=tmp_data_dir)
        path = manager.create("DB Test World")
        db_path = path / "universe.db"
        assert db_path.exists()
        with sqlite3.connect(str(db_path)) as conn:
            rows = dict(conn.execute("SELECT key, value FROM metadata").fetchall())
            assert rows["display_name"] == "DB Test World"
            assert rows["slug"] == "db-test-world"
            assert rows["schema_version"] == "1"
            assert "created_at" in rows


class TestManagerList:
    """Tests for UniverseManager.list()."""

    def test_list_empty_returns_empty(self, tmp_data_dir: Path) -> None:
        """Listing with no universes returns an empty list."""
        manager = UniverseManager(data_dir=tmp_data_dir)
        assert manager.list() == []

    def test_list_returns_metadata_for_each(self, tmp_data_dir: Path) -> None:
        """Listing returns metadata for each created universe."""
        manager = UniverseManager(data_dir=tmp_data_dir)
        manager.create("Alpha World")
        manager.create("Beta World")
        universes = manager.list()
        slugs = [u.slug for u in universes]
        assert "alpha-world" in slugs
        assert "beta-world" in slugs
        assert len(universes) == 2


class TestManagerLoad:
    """Tests for UniverseManager.load()."""

    def test_load_existing_returns_path(self, tmp_data_dir: Path) -> None:
        """Loading an existing universe returns its path."""
        manager = UniverseManager(data_dir=tmp_data_dir)
        created_path = manager.create("Load Test")
        loaded_path = manager.load("load-test")
        assert loaded_path == created_path

    def test_load_nonexistent_raises(self, tmp_data_dir: Path) -> None:
        """Loading a nonexistent universe raises FileNotFoundError."""
        manager = UniverseManager(data_dir=tmp_data_dir)
        with pytest.raises(FileNotFoundError):
            manager.load("nonexistent")


class TestManagerDelete:
    """Tests for UniverseManager.delete()."""

    def test_delete_removes_folder(self, tmp_data_dir: Path) -> None:
        """Deleting a universe removes its folder."""
        manager = UniverseManager(data_dir=tmp_data_dir)
        path = manager.create("Delete Me")
        assert path.exists()
        manager.delete("delete-me")
        assert not path.exists()

    def test_delete_nonexistent_raises(self, tmp_data_dir: Path) -> None:
        """Deleting a nonexistent universe raises FileNotFoundError."""
        manager = UniverseManager(data_dir=tmp_data_dir)
        with pytest.raises(FileNotFoundError):
            manager.delete("nonexistent")


class TestCLI:
    """Tests for the Click CLI commands."""

    def test_cli_create_outputs_path(
        self, tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI create command outputs the created path."""
        runner = CliRunner()
        result = runner.invoke(cli, ["create", "CLI Test World"])
        assert result.exit_code == 0
        assert "CLI Test World" in result.output or "cli-test-world" in result.output

    def test_cli_list_outputs_slugs(
        self, tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI list command outputs universe slugs."""
        runner = CliRunner()
        runner.invoke(cli, ["create", "List Test"])
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "list-test" in result.output
