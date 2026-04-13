"""Diagnostics filesystem substrate (AUTO-02).

Per D-21/D-22/D-23/D-24/D-25 from 04-CONTEXT.md.

Per-tick: universe/diagnostics/tick_<id>/
Per-validation: universe/diagnostics/validation/<ts>_<id>/
Schema version 1 declared in summary.json.

Security posture (see 04-03-PLAN threat_model):

- :data:`SCHEMA_VERSION` is the version tag emitted into every summary.json.
- :func:`_atomic_write_json` guarantees readers never see a partial summary
  (tempfile + ``os.replace``). Crashes leave ``<name>.tmp.*`` files behind;
  :meth:`DiagnosticsSink._sweep_tmp_files` cleans them on next boot
  (T-04-TMP-LEAK).
- :meth:`DiagnosticsSink.open_validation` sanitises the caller-supplied
  ``mechanic_id`` and verifies the resulting folder is under the diagnostics
  root (T-04-DIAG-PATH-TRAVERSAL).
- :meth:`DiagnosticsSink.prune` is dry-run by default, skips symlinks, and
  re-checks every candidate path against the root before deletion
  (T-04-PRUNE-DESTRUCTION).
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from token_world.operator.diagnostics import OperatorDiagnosticsContext

SCHEMA_VERSION = 1

_TMP_SUFFIX_PATTERN = re.compile(r".*\.tmp$")
_SAFE_ID_PATTERN = re.compile(r"[^A-Za-z0-9_.-]")


def _atomic_write_json(path: Path, obj: Any) -> None:
    """Write *obj* as pretty JSON to *path* atomically.

    Uses ``tempfile.mkstemp`` in the parent directory plus ``os.replace`` so
    that partial writes can never be observed by readers. On crash, a
    ``<name>.tmp`` leftover may remain; :meth:`DiagnosticsSink._sweep_tmp_files`
    clears those on the next :class:`DiagnosticsSink` construction.

    Args:
        path: Destination file path. Parent directories are created.
        obj: Any ``json.dumps``-compatible object.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path_str = tempfile.mkstemp(
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            with contextlib.suppress(OSError):
                tmp_path.unlink()
        raise


class DiagnosticsSink:
    """Filesystem substrate for per-tick + per-validation diagnostics.

    The sink owns ``<universe_dir>/diagnostics/``. All write operations go
    through either :meth:`open_tick` (context manager yielding a
    :class:`TickDiagnostics`) or :meth:`open_validation` (returns a directory
    for validation-report payloads). :meth:`prune` implements the
    operator-controlled retention policy (D-25).

    Args:
        universe_dir: The universe directory that owns the diagnostics tree.
            ``universe_dir / "diagnostics"`` is created on init.
    """

    def __init__(self, universe_dir: Path) -> None:
        self._universe_dir = universe_dir.resolve()
        self._root = (self._universe_dir / "diagnostics").resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._sweep_tmp_files()

    @property
    def root(self) -> Path:
        """Return the diagnostics root directory."""
        return self._root

    # ------------------------------------------------------------------
    # Boot-time hygiene (T-04-TMP-LEAK)
    # ------------------------------------------------------------------

    def _sweep_tmp_files(self) -> None:
        """Remove leftover ``*.tmp`` files from crashed atomic writes.

        Walks the diagnostics tree and unlinks regular files whose name ends
        with ``.tmp`` (the suffix used by :func:`_atomic_write_json` via
        ``tempfile.mkstemp``). Symlinks and entries that resolve outside the
        root are never followed.
        """
        for entry in self._root.rglob("*.tmp"):
            if entry.is_symlink():
                continue
            if not entry.is_file():
                continue
            try:
                resolved = entry.resolve()
                resolved.relative_to(self._root)
            except (ValueError, OSError):
                continue
            with contextlib.suppress(OSError):
                entry.unlink()

    # ------------------------------------------------------------------
    # Per-tick diagnostics
    # ------------------------------------------------------------------

    @contextmanager
    def open_tick(self, tick_id: int) -> Iterator[TickDiagnostics]:
        """Context manager yielding a :class:`TickDiagnostics` writer.

        On ``__exit__``, :meth:`TickDiagnostics.finalize` is called, flushing
        ``summary.json`` atomically. If the ``with`` body raises, the summary
        still lands but its ``status`` field reflects whatever was set by the
        caller (default ``"ok"``) — callers that want to record failures
        should set the status before the exception propagates.

        Args:
            tick_id: The tick identifier. Used as the folder name suffix:
                ``tick_<tick_id>``.

        Yields:
            A :class:`TickDiagnostics` bound to the per-tick folder.
        """
        tick_dir = self._root / f"tick_{tick_id}"
        tick_dir.mkdir(exist_ok=True)
        ctx = TickDiagnostics(tick_dir=tick_dir, tick_id=tick_id)
        try:
            yield ctx
        finally:
            ctx.finalize()

    # ------------------------------------------------------------------
    # Operator namespace (Phase 4.1 D-15)
    # ------------------------------------------------------------------

    def open_operator_session(self, tick_id: str | int) -> OperatorDiagnosticsContext:
        """Open the operator diagnostics namespace for ``tick_id``.

        Returns an :class:`OperatorDiagnosticsContext` that writes into
        ``<universe>/diagnostics/tick_<id>/operator/``. Use as a context
        manager so the safety-net ``__exit__`` lands a final
        ``resume_outcome.json`` even on exception::

            with sink.open_operator_session(tick_id) as op_ctx:
                op_ctx.write_yield_signal(signal)
                ...
                op_ctx.close({"success": True, "mechanic_id": mid, ...})

        Decoupling note: we resolve the universe root via ``self._root.parent``
        rather than referencing the private ``_universe_dir`` attribute. The
        Phase 4 invariant is that ``_root`` points at ``<universe>/diagnostics``
        (asserted by ``test_sink_creates_diagnostics_root_on_init``); reading
        ``.parent`` gives us the universe folder portably across any future
        rename of the private attribute.

        Args:
            tick_id: Tick identifier. Accepts str or int; stringified internally
                so ``open_operator_session(42)`` and ``open_operator_session("42")``
                produce the same directory.

        Returns:
            A new :class:`OperatorDiagnosticsContext` with the operator/
            and operator/validation/ subfolders already created.
        """
        # Local import keeps the operator subpackage from being eagerly loaded
        # whenever Phase 4 diagnostics is imported (matters for the mechanic
        # framework's startup time and avoids a hard dep cycle if the operator
        # subpackage ever needs to import from mechanic.*).
        from token_world.operator.diagnostics import OperatorDiagnosticsContext

        return OperatorDiagnosticsContext(
            universe_path=self._root.parent,
            tick_id=tick_id,
        )

    # ------------------------------------------------------------------
    # Per-validation diagnostics
    # ------------------------------------------------------------------

    def open_validation(self, mechanic_id: str) -> Path:
        """Allocate a timestamped validation folder for *mechanic_id*.

        T-04-DIAG-PATH-TRAVERSAL mitigation: *mechanic_id* is sanitised via
        :data:`_SAFE_ID_PATTERN` (non-``[A-Za-z0-9_.-]`` chars replaced with
        ``_``), and the resulting directory is verified to resolve under the
        diagnostics root before being returned.

        Args:
            mechanic_id: Operator-controlled mechanic identifier.

        Returns:
            The created folder path
            ``<root>/validation/<YYYYMMDDThhmmssZ>_<safe_id>/``.

        Raises:
            ValueError: If the resolved folder would escape the diagnostics
                root (should not happen given the sanitisation, but checked
                defensively).
        """
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        safe_id = _SAFE_ID_PATTERN.sub("_", mechanic_id) or "unknown"
        d = self._root / "validation" / f"{ts}_{safe_id}"
        d.mkdir(parents=True, exist_ok=True)
        resolved = d.resolve()
        resolved.relative_to(self._root)  # raises ValueError if escape
        return d

    # ------------------------------------------------------------------
    # Retention (D-25)
    # ------------------------------------------------------------------

    def prune(
        self,
        *,
        before_tick: int | None = None,
        before_date: date | None = None,
        confirm: bool = False,
    ) -> list[Path]:
        """Remove ``tick_<id>/`` and ``validation/<...>/`` folders older than cutoff.

        Dry-run by default: returns the list of candidate paths without
        touching the filesystem. Pass ``confirm=True`` to actually delete.

        T-04-PRUNE-DESTRUCTION mitigations:

        - Every candidate is re-verified via ``Path.resolve().relative_to``
          against the diagnostics root before deletion.
        - Symlinks are never followed (``entry.is_symlink()`` filter).
        - Raises :class:`ValueError` when neither cutoff is provided so a
          naked ``prune()`` call cannot wipe the tree.

        Args:
            before_tick: Tick-folder cutoff. Folders with
                ``int(name.removeprefix("tick_")) < before_tick`` are
                candidates.
            before_date: Date cutoff. Folders whose name-timestamp (for
                validation folders) or mtime (for tick folders) is older
                than this date are candidates.
            confirm: When ``True`` actually ``shutil.rmtree`` each candidate.

        Returns:
            The candidate list (same regardless of ``confirm``). When
            ``confirm=True`` the entries no longer exist on disk but the
            paths themselves are still returned so the CLI can print them.

        Raises:
            ValueError: If both ``before_tick`` and ``before_date`` are
                ``None``.
        """
        if before_tick is None and before_date is None:
            raise ValueError("prune requires before_tick or before_date")

        candidates: list[Path] = []

        # Tick folders (direct children of root).
        if self._root.is_dir():
            for entry in sorted(self._root.iterdir()):
                if entry.is_symlink():
                    continue
                if not entry.is_dir():
                    continue
                name = entry.name
                if not name.startswith("tick_"):
                    continue
                try:
                    tid = int(name.removeprefix("tick_"))
                except ValueError:
                    continue
                if before_tick is not None and tid < before_tick:
                    candidates.append(entry)
                elif before_date is not None:
                    mt = datetime.fromtimestamp(entry.stat().st_mtime, UTC).date()
                    if mt < before_date:
                        candidates.append(entry)

        # Validation folders (children of root/validation).
        vroot = self._root / "validation"
        if vroot.is_dir():
            for entry in sorted(vroot.iterdir()):
                if entry.is_symlink():
                    continue
                if not entry.is_dir():
                    continue
                name = entry.name
                try:
                    ts_part = name.split("_", 1)[0]
                    folder_dt = datetime.strptime(ts_part, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
                except (ValueError, IndexError):
                    continue
                if before_date is not None and folder_dt.date() < before_date:
                    candidates.append(entry)
                elif before_tick is not None:
                    # Validation folders aren't keyed by tick; skip them when
                    # only --before-tick was given.
                    continue

        # Re-verify every candidate is under root (defence in depth).
        safe_candidates: list[Path] = []
        for c in candidates:
            try:
                c.resolve().relative_to(self._root)
            except (ValueError, OSError):
                continue
            safe_candidates.append(c)

        if confirm:
            for c in safe_candidates:
                if c.exists() and not c.is_symlink():
                    shutil.rmtree(c, ignore_errors=False)

        return safe_candidates


class TickDiagnostics:
    """Per-tick diagnostics writer. Allocated by :meth:`DiagnosticsSink.open_tick`.

    All writes are idempotent with respect to their destination filename, so
    callers may overwrite (e.g. update ``matching.json`` after a re-match).
    ``mutations.jsonl`` is append-only.

    :meth:`finalize` writes the summary JSON. Called automatically by the
    context-manager ``__exit__``; idempotent on repeat invocation.
    """

    def __init__(self, tick_dir: Path, tick_id: int) -> None:
        self._dir = tick_dir
        self.tick_id = tick_id
        self._summary: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "tick_id": tick_id,
            "status": "pending",
        }
        self._finalized = False

    @property
    def dir(self) -> Path:
        """Return the per-tick directory."""
        return self._dir

    # ---- Writers used by Phase 4 + Phase 5 ----------------------------

    def write_action(self, text: str) -> None:
        """Write the raw resident-agent action text."""
        (self._dir / "action.txt").write_text(text, encoding="utf-8")

    def write_classification(self, *, prompt: str, response: str, parsed: dict) -> None:
        """Record the classifier (Haiku) call: prompt, raw response, parsed struct."""
        d = self._dir / "classification"
        d.mkdir(exist_ok=True)
        (d / "prompt.txt").write_text(prompt, encoding="utf-8")
        (d / "response.txt").write_text(response, encoding="utf-8")
        _atomic_write_json(d / "parsed.json", parsed)

    def write_matching(self, matched: list[dict]) -> None:
        """Record which mechanic(s) matched and why."""
        _atomic_write_json(self._dir / "matching.json", matched)

    def append_mutation(self, mutation_dict: dict) -> None:
        """Append a single Mutation dict to ``execution/mutations.jsonl``."""
        d = self._dir / "execution"
        d.mkdir(exist_ok=True)
        with (d / "mutations.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(mutation_dict, sort_keys=True) + "\n")

    def write_execution_trace(self, trace_dict: dict) -> None:
        """Write the chain execution tree (from Phase 2's ExecutionTrace)."""
        d = self._dir / "execution"
        d.mkdir(exist_ok=True)
        _atomic_write_json(d / "trace.json", trace_dict)

    def write_observation(self, *, prompt: str, response: str, parsed: dict) -> None:
        """Record the observer (Sonnet) call: prompt, raw response, parsed struct."""
        d = self._dir / "observation"
        d.mkdir(exist_ok=True)
        (d / "prompt.txt").write_text(prompt, encoding="utf-8")
        (d / "response.txt").write_text(response, encoding="utf-8")
        _atomic_write_json(d / "parsed.json", parsed)

    def set_summary(self, **fields: Any) -> None:
        """Update fields merged into ``summary.json`` on finalize."""
        self._summary.update(fields)

    def finalize(self) -> None:
        """Write ``summary.json`` atomically. Idempotent.

        If the caller never explicitly called :meth:`set_summary` with a
        ``status`` field, the default ``"pending"`` placeholder is upgraded
        to ``"ok"`` so readers don't see a stuck "pending" tick.
        """
        if self._finalized:
            return
        if self._summary.get("status") == "pending":
            self._summary["status"] = "ok"
        _atomic_write_json(self._dir / "summary.json", self._summary)
        self._finalized = True
