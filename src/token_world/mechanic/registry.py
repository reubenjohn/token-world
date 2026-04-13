"""Mechanic registry: flat module scanning, querying, and git versioning.

Per Phase 4 D-10 mechanics live as flat ``<id>.py`` modules under
``mechanics/``. This module scans the directory via
:func:`token_world.mechanic.loader.discover_mechanic_modules`, loads each
module with :func:`load_mechanic_classes`, and indexes every concrete
:class:`Mechanic` subclass by its class-level ``id``. Metadata is read
entirely from class attributes (``id``, ``description``, ``voluntary``,
``tags``) -- ``meta.yaml`` has been removed (D-04).

Duplicate ``id`` values across modules raise :class:`ValueError`
(T-04-REGISTRY-SHADOWING mitigation). Underscore-prefixed modules and
``__init__.py`` are skipped by the discovery helper.
"""

from __future__ import annotations

import subprocess
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from token_world.mechanic.loader import (
    discover_mechanic_modules,
    load_mechanic_classes,
)
from token_world.mechanic.protocol import Mechanic
from token_world.mechanic.validation import ValidationReport, validate

if TYPE_CHECKING:
    from token_world.mechanic.diagnostics import DiagnosticsSink


@dataclass
class MechanicInfo:
    """Metadata about a registered mechanic.

    Attributes:
        id: Unique mechanic identifier.
        description: Human-readable description.
        voluntary: Whether the mechanic is triggered by agent action.
        tags: Classification tags for querying.
        path: Filesystem path to the mechanic module (.py file).
    """

    id: str
    description: str
    voluntary: bool
    tags: list[str] = field(default_factory=list)
    path: Path = field(default_factory=lambda: Path("."))


@dataclass
class MechanicVersion:
    """A single git commit touching a mechanic module.

    Attributes:
        commit_hash: Full git commit hash.
        date: ISO date string of the commit.
        message: Commit message subject line.
    """

    commit_hash: str
    date: str
    message: str


class MechanicRegistry:
    """Scans a mechanics/ folder of flat modules and indexes them by id.

    Provides listing, lookup by id, tag-based querying, and git-based
    version history retrieval for individual mechanic modules.

    Args:
        mechanics_dir: Path to the mechanics/ folder to scan.
        universe_dir: Parent universe directory (used as cwd for git commands).
            Defaults to ``mechanics_dir.parent``.

    Raises:
        ValueError: If two modules declare the same ``id`` (T-04 mitigation).
    """

    def __init__(self, mechanics_dir: Path, *, universe_dir: Path | None = None) -> None:
        self._mechanics_dir = mechanics_dir
        self._universe_dir = universe_dir or mechanics_dir.parent
        self._index: dict[str, MechanicInfo] = {}
        self._classes: dict[str, type[Mechanic]] = {}
        self._last_scan_reports: list[ValidationReport] = []
        self.scan()

    @property
    def last_scan_reports(self) -> list[ValidationReport]:
        """Return the ValidationReports from the most recent :meth:`scan`.

        Consumed by 04-03's diagnostics sink to write per-module validation
        reports under ``<universe>/diagnostics/validation/...`` after every
        ``resume_tick`` (D-15).
        """
        return list(self._last_scan_reports)

    def scan(
        self,
        *,
        diagnostics_sink: DiagnosticsSink | None = None,
    ) -> list[ValidationReport]:
        """Scan mechanics directory and rebuild the index.

        Runs :func:`token_world.mechanic.validation.validate` on every
        discovered module. Modules whose report has ``passed=False`` are
        EXCLUDED from the live index (D-15) -- callers can still inspect
        the full report list via the return value or
        :attr:`last_scan_reports`. Valid modules pass through the usual
        class-attribute indexing.

        When ``diagnostics_sink`` is provided, every FAILED report is
        additionally persisted to
        ``universe/diagnostics/validation/<ts>_<mechanic-id>/report.json``
        via :meth:`DiagnosticsSink.open_validation` (D-15 wiring loop).
        Sink-level write failures degrade to a :mod:`warnings` entry --
        the registry's primary contract (indexing valid mechanics) must not
        be broken by a diagnostics write failure.

        Args:
            diagnostics_sink: Optional sink; when ``None`` (default) the
                scan is silent and behaves exactly as the 04-02 contract.

        Returns:
            One :class:`ValidationReport` per module scanned (passing and
            failing alike). Order matches ``discover_mechanic_modules``.

        Raises:
            ValueError: If two *valid* modules declare the same ``id``
                (T-04-REGISTRY-SHADOWING mitigation). Invalid modules are
                skipped before duplicate detection.
        """
        self._index.clear()
        self._classes.clear()
        reports: list[ValidationReport] = []

        if not self._mechanics_dir.is_dir():
            self._last_scan_reports = reports
            return reports

        for module_path in discover_mechanic_modules(self._mechanics_dir):
            report = validate(module_path)
            reports.append(report)
            if not report.passed:
                if diagnostics_sink is not None:
                    self._write_validation_diagnostics(diagnostics_sink, report)
                continue

            classes = load_mechanic_classes(module_path)
            for cls in classes:
                mechanic_id = cls.id
                if mechanic_id in self._index:
                    prior_path = self._index[mechanic_id].path
                    raise ValueError(
                        f"Duplicate mechanic id {mechanic_id!r} in {module_path} "
                        f"(already registered from {prior_path})"
                    )
                info = MechanicInfo(
                    id=mechanic_id,
                    description=cls.description,
                    voluntary=cls.voluntary,
                    tags=list(cls.tags),
                    path=module_path,
                )
                self._index[mechanic_id] = info
                self._classes[mechanic_id] = cls

        self._last_scan_reports = reports
        return reports

    def _write_validation_diagnostics(
        self,
        sink: DiagnosticsSink,
        report: ValidationReport,
    ) -> None:
        """Persist a failing ValidationReport via the diagnostics sink (D-15).

        Never raises. Sink-level failures are reported via
        :func:`warnings.warn` so the scan can continue indexing the remaining
        modules. Pure helper -- the caller has already decided that *report*
        is failing.
        """
        # Local import avoids a module-level cycle between
        # token_world.mechanic.registry and token_world.mechanic.diagnostics
        # (both are re-exported from the mechanic package __init__).
        from token_world.mechanic.diagnostics import _atomic_write_json

        mechanic_id = self._mechanic_id_from_report(report)
        try:
            folder = sink.open_validation(mechanic_id)
            _atomic_write_json(folder / "report.json", report.to_dict())
        except (OSError, ValueError) as e:
            warnings.warn(
                f"Registry failed to write validation diagnostics for {mechanic_id!r}: {e}",
                stacklevel=2,
            )

    @staticmethod
    def _mechanic_id_from_report(report: ValidationReport) -> str:
        """Best-effort mechanic id for a failing report.

        Preference order:

        1. An explicit ``mechanic_id`` attribute on the report (04-02's
           ``ValidationReport`` currently doesn't carry one, but the getattr
           is forward-compatible if it's added later).
        2. The module filename stem, which always exists and is safe to pass
           through :meth:`DiagnosticsSink.open_validation` (that method
           sanitises the id defensively).
        """
        explicit = getattr(report, "mechanic_id", None)
        if isinstance(explicit, str) and explicit:
            return explicit
        return report.module_path.stem

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

    def get_class(self, mechanic_id: str) -> type[Mechanic]:
        """Return the registered Mechanic subclass (not an instance) by id.

        Companion to :meth:`get_mechanic`: where ``get_mechanic`` constructs
        and returns a fresh instance, ``get_class`` returns the class object
        itself so callers can read class-level attributes (e.g. ``id``,
        ``description``, ``tags``, and -- motivating the accessor --
        framework-gap markers like ``blocked_by`` declared on the class)
        without paying the cost of instantiation and without reaching into
        the registry's private ``_classes`` dict.

        Motivating caller: plan 04-09's ``blocked_by`` routing logic in the
        integration harness (04-04) inspects a mechanic's declared
        framework-gap class attribute to decide how to route a stubbed
        scenario. That code needs a stable public API, not the documented
        private-access fallback flagged by 04-REVIEWS.md HIGH #2.

        Args:
            mechanic_id: The mechanic identifier.

        Returns:
            The :class:`Mechanic` subclass registered under *mechanic_id*.

        Raises:
            KeyError: If *mechanic_id* is not in the registry. Matches the
                :meth:`get_mechanic` convention with message
                ``f"Unknown mechanic: {mechanic_id!r}"``.
        """
        if mechanic_id not in self._classes:
            raise KeyError(f"Unknown mechanic: {mechanic_id!r}")
        return self._classes[mechanic_id]

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
        """Retrieve git commit history for a mechanic module.

        ``git log -- <path>`` treats a file identically to a folder, so this
        works unchanged for flat modules.

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
