"""Mechanic registry: folder scanning, querying, and git versioning."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from token_world.mechanic.loader import load_mechanic_class
from token_world.mechanic.protocol import Mechanic


@dataclass
class MechanicInfo:
    """Metadata about a registered mechanic.

    Attributes:
        id: Unique mechanic identifier.
        description: Human-readable description.
        voluntary: Whether the mechanic is triggered by agent action.
        tags: Classification tags for querying.
        path: Filesystem path to the mechanic folder.
    """

    id: str
    description: str
    voluntary: bool
    tags: list[str] = field(default_factory=list)
    path: Path = field(default_factory=lambda: Path("."))


@dataclass
class MechanicVersion:
    """A single git commit touching a mechanic folder.

    Attributes:
        commit_hash: Full git commit hash.
        date: ISO date string of the commit.
        message: Commit message subject line.
    """

    commit_hash: str
    date: str
    message: str


class MechanicRegistry:
    """Scans a mechanics/ folder and indexes all mechanic folders.

    Provides listing, lookup by id, tag-based querying, and git-based
    version history retrieval for individual mechanics.

    Args:
        mechanics_dir: Path to the mechanics/ folder to scan.
        universe_dir: Parent universe directory (used as cwd for git commands).
            Defaults to ``mechanics_dir.parent``.
    """

    def __init__(self, mechanics_dir: Path, *, universe_dir: Path | None = None) -> None:
        self._mechanics_dir = mechanics_dir
        self._universe_dir = universe_dir or mechanics_dir.parent
        self._index: dict[str, MechanicInfo] = {}
        self._classes: dict[str, type[Mechanic]] = {}
        self.scan()

    def scan(self) -> None:
        """Scan mechanics directory and rebuild the index.

        Clears existing index, iterates subdirectories, loads meta.yaml
        and mechanic classes. Skips directories without ``mechanic.py``.
        """
        self._index.clear()
        self._classes.clear()

        if not self._mechanics_dir.is_dir():
            return

        for entry in sorted(self._mechanics_dir.iterdir()):
            if not entry.is_dir() or not (entry / "mechanic.py").exists():
                continue

            # Load mechanic class
            mechanic_cls = load_mechanic_class(entry)
            mechanic_id: str

            # Load metadata from meta.yaml or fall back to class attributes
            meta_path = entry / "meta.yaml"
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = yaml.safe_load(f) or {}
                mechanic_id = meta.get("id", mechanic_cls.id)
                description = meta.get("description", mechanic_cls.description)
                voluntary = meta.get("voluntary", mechanic_cls.voluntary)
                tags = meta.get("tags", [])
            else:
                mechanic_id = mechanic_cls.id
                description = mechanic_cls.description
                voluntary = mechanic_cls.voluntary
                tags = []

            info = MechanicInfo(
                id=mechanic_id,
                description=description,
                voluntary=voluntary,
                tags=tags,
                path=entry,
            )
            self._index[mechanic_id] = info
            self._classes[mechanic_id] = mechanic_cls

    def list_mechanics(self) -> list[MechanicInfo]:
        """Return a sorted list of all discovered mechanic info."""
        return sorted(self._index.values(), key=lambda m: m.id)

    def get_mechanic(self, mechanic_id: str) -> Mechanic:
        """Instantiate and return a mechanic by id.

        Args:
            mechanic_id: The mechanic identifier.

        Returns:
            An instance of the Mechanic subclass.

        Raises:
            KeyError: If *mechanic_id* is not in the registry.
        """
        if mechanic_id not in self._index:
            raise KeyError(f"Unknown mechanic: {mechanic_id}")
        return self._classes[mechanic_id]()

    def get_info(self, mechanic_id: str) -> MechanicInfo:
        """Return metadata for a mechanic by id.

        Args:
            mechanic_id: The mechanic identifier.

        Returns:
            MechanicInfo for the mechanic.

        Raises:
            KeyError: If *mechanic_id* is not in the registry.
        """
        if mechanic_id not in self._index:
            raise KeyError(f"Unknown mechanic: {mechanic_id}")
        return self._index[mechanic_id]

    def query_by_tag(self, tag: str) -> list[MechanicInfo]:
        """Return mechanics that have the given tag.

        Args:
            tag: Tag to filter by.

        Returns:
            List of matching MechanicInfo, sorted by id.
        """
        return sorted(
            [info for info in self._index.values() if tag in info.tags],
            key=lambda m: m.id,
        )

    def get_history(self, mechanic_id: str, limit: int = 10) -> list[MechanicVersion]:
        """Retrieve git commit history for a mechanic folder.

        Args:
            mechanic_id: The mechanic identifier.
            limit: Maximum number of commits to return.

        Returns:
            List of MechanicVersion entries. Empty list if not in a git repo.

        Raises:
            KeyError: If *mechanic_id* is not in the registry.
        """
        if mechanic_id not in self._index:
            raise KeyError(f"Unknown mechanic: {mechanic_id}")

        info = self._index[mechanic_id]
        try:
            rel_path = info.path.relative_to(self._universe_dir)
        except ValueError:
            return []

        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"--max-count={limit}",
                    "--format=%H|%ai|%s",
                    "--",
                    str(rel_path),
                ],
                cwd=self._universe_dir,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            # git not installed
            return []

        if result.returncode != 0:
            return []

        versions: list[MechanicVersion] = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                versions.append(
                    MechanicVersion(
                        commit_hash=parts[0],
                        date=parts[1],
                        message=parts[2],
                    )
                )
        return versions
