"""Universe lifecycle management: create, load, list, delete."""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from slugify import slugify

from token_world.models import UniverseMetadata
from token_world.universe.paths import get_universes_dir


class UniverseManager:
    """Manages universe lifecycle: create, load, list, delete."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or get_universes_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def create(self, name: str) -> Path:
        """Create a new universe. Returns path to universe folder.

        Raises:
            ValueError: If name is empty or produces an empty slug.
            FileExistsError: If a universe with the same slug already exists.
        """
        name = name.strip()
        if not name:
            raise ValueError("Universe name cannot be empty")
        slug = slugify(name)
        if not slug:
            raise ValueError(f"Universe name '{name}' produces an empty slug")
        universe_dir = self.data_dir / slug
        universe_dir.mkdir()  # raises FileExistsError if exists (atomic, no TOCTOU)
        self._init_db(universe_dir, name=name, slug=slug)
        return universe_dir

    def list(self) -> list[UniverseMetadata]:
        """List all universes with metadata."""
        universes = []
        for path in sorted(self.data_dir.iterdir()):
            if path.is_dir() and (path / "universe.db").exists():
                meta = self._load_metadata(path)
                if meta:
                    universes.append(meta)
        return universes

    def load(self, slug: str) -> Path:
        """Load an existing universe by slug.

        Raises:
            FileNotFoundError: If no universe with the given slug exists.
        """
        path = self.data_dir / slug
        if not path.exists() or not (path / "universe.db").exists():
            raise FileNotFoundError(f"Universe '{slug}' not found")
        return path

    def delete(self, slug: str) -> None:
        """Delete a universe and all its data.

        Raises:
            FileNotFoundError: If no universe with the given slug exists.
            ValueError: If path traversal is detected.
        """
        path = self.load(slug)  # validates existence
        # Security: verify path is under data_dir before rmtree (T-00-02)
        path.resolve().relative_to(self.data_dir.resolve())
        shutil.rmtree(path)

    def _init_db(self, universe_dir: Path, *, name: str, slug: str) -> None:
        """Initialize universe.db with metadata table."""
        db_path = universe_dir / "universe.db"
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.executemany(
                "INSERT INTO metadata (key, value) VALUES (?, ?)",
                [
                    ("display_name", name),
                    ("slug", slug),
                    ("created_at", now),
                    ("schema_version", "1"),
                ],
            )

    def _load_metadata(self, universe_dir: Path) -> UniverseMetadata | None:
        """Load metadata from universe.db."""
        db_path = universe_dir / "universe.db"
        try:
            with sqlite3.connect(str(db_path)) as conn:
                rows = conn.execute("SELECT key, value FROM metadata").fetchall()
                data = dict(rows)
                return UniverseMetadata(
                    name=data["display_name"],
                    slug=data["slug"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    schema_version=int(data.get("schema_version", "1")),
                )
        except (sqlite3.Error, KeyError):
            return None
