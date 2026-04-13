"""Operator diagnostics namespace (Phase 4.1 D-15, D-16).

Extends Phase 4's ``DiagnosticsSink`` with an ``operator/`` subfolder per tick:

::

    <universe>/diagnostics/tick_<tick_id>/operator/
    ├── yield_signal.json           # YieldSignal.to_json() output
    ├── authoring_attempts.jsonl    # one line per subagent message
    ├── validation/
    │   └── attempt_NN.json         # zero-padded
    ├── mechanic_diff.patch         # unified diff (may be empty)
    └── resume_outcome.json         # final outcome with schema_version

This module exposes the **only** sanctioned reader/writer for that namespace
(D-16: no regex file-name parsing elsewhere in the codebase).

Security posture:

- :func:`_atomic_write_text` / :func:`_atomic_write_json` use the same
  tempfile + ``os.replace`` pattern as Phase 4's ``_atomic_write_json``
  (T-04.1-09). On crash, leftover ``*.tmp`` files are caught by Phase 4's
  ``DiagnosticsSink._sweep_tmp_files`` next boot.
- :class:`OperatorDiagnosticsContext.__exit__` is a safety net: if the caller
  forgot to call :meth:`close`, an outcome with ``success=False`` is written
  so consumers (replay-tick) always see a final artefact.
- :class:`OperatorDiagnosticsReader.schema_version` raises on unknown versions
  (T-04.1-05), preventing silent consumption of incompatible payloads.
- :meth:`OperatorDiagnosticsReader.attempts` tolerates a partial JSONL last
  line (T-04.1-06) — common after a harness crash mid-append.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Any

from loguru import logger

from token_world.operator.yield_signal import YieldSignal

__all__ = [
    "OPERATOR_SCHEMA_VERSION",
    "OperatorDiagnosticsContext",
    "OperatorDiagnosticsReader",
]


OPERATOR_SCHEMA_VERSION: int = 1
"""Version of the operator diagnostics layout (resume_outcome.json shape).

Bumped on any breaking change to the on-disk format. Readers reject unknown
versions with :class:`ValueError` (threat T-04.1-05)."""


_YIELD_FILE = "yield_signal.json"
_ATTEMPTS_FILE = "authoring_attempts.jsonl"
_VALIDATION_DIR = "validation"
_DIFF_FILE = "mechanic_diff.patch"
_OUTCOME_FILE = "resume_outcome.json"


# ---------------------------------------------------------------------------
# Atomic write helpers
# ---------------------------------------------------------------------------


def _atomic_write_text(path: Path, text: str) -> None:
    """Write *text* to *path* atomically via tempfile + ``os.replace``.

    Mirrors Phase 4's :func:`token_world.mechanic.diagnostics._atomic_write_json`.
    On exception, the tempfile is unlinked. If the process crashes before
    cleanup, the leftover ``*.tmp`` is caught by
    :meth:`DiagnosticsSink._sweep_tmp_files` on the next boot.
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
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            with contextlib.suppress(OSError):
                tmp_path.unlink()
        raise


def _atomic_write_json(path: Path, obj: Any) -> None:
    """Write *obj* as deterministic JSON (sorted keys, indent=2) atomically."""
    _atomic_write_text(path, json.dumps(obj, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# Write side
# ---------------------------------------------------------------------------


class OperatorDiagnosticsContext(AbstractContextManager["OperatorDiagnosticsContext"]):
    """Context manager that writes the per-tick operator diagnostics namespace.

    Constructed by :meth:`DiagnosticsSink.open_operator_session` (Task 2) or
    directly for tests.

    Lifecycle:

    1. ``__enter__`` (or construction) creates ``operator/`` and ``validation/``.
    2. Caller invokes :meth:`write_yield_signal`, :meth:`append_attempt`,
       :meth:`write_validation_report`, :meth:`write_mechanic_diff` as the
       authoring loop progresses.
    3. Caller invokes :meth:`close` with the final outcome dict; ``close()``
       atomically writes ``resume_outcome.json`` with ``schema_version``
       injected.
    4. If the caller forgets to call :meth:`close`, ``__exit__`` writes a
       fallback outcome with ``success=False`` so consumers always see a
       final artefact (D-15 invariant).
    """

    universe_path: Path
    tick_id: str
    operator_dir: Path

    def __init__(self, universe_path: Path, tick_id: str | int) -> None:
        self.universe_path = universe_path
        self.tick_id = str(tick_id)
        self.operator_dir = universe_path / "diagnostics" / f"tick_{self.tick_id}" / "operator"
        self.operator_dir.mkdir(parents=True, exist_ok=True)
        (self.operator_dir / _VALIDATION_DIR).mkdir(exist_ok=True)
        self._closed = False

    # ------------------------------------------------------------------
    # Writers
    # ------------------------------------------------------------------

    def write_yield_signal(self, signal: YieldSignal) -> None:
        """Persist *signal* as the source-of-truth yield artefact.

        Uses :meth:`YieldSignal.to_json` (deterministic — sorted keys + indent).
        """
        _atomic_write_text(self.operator_dir / _YIELD_FILE, signal.to_json())

    def append_attempt(self, attempt: dict[str, Any]) -> None:
        """Append one line of subagent transcript to ``authoring_attempts.jsonl``.

        Non-atomic by JSONL convention — a crash mid-append may produce a
        partial final line. The reader (:meth:`OperatorDiagnosticsReader.attempts`)
        tolerates this by skipping unparseable lines (T-04.1-06).
        """
        path = self.operator_dir / _ATTEMPTS_FILE
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(attempt, sort_keys=True) + "\n")

    def write_validation_report(self, attempt_n: int, report: dict[str, Any]) -> None:
        """Write per-attempt validation report at ``validation/attempt_NN.json``.

        ``attempt_n`` is zero-padded to two digits so directory listings sort
        correctly through attempts 1..99. (Beyond 99 the natural ordering
        diverges; the harness's ``max_turns=20`` makes that unreachable in
        practice.)
        """
        path = self.operator_dir / _VALIDATION_DIR / f"attempt_{attempt_n:02d}.json"
        _atomic_write_json(path, report)

    def write_mechanic_diff(self, diff: str) -> None:
        """Persist the unified diff produced by the authoring subagent.

        Empty string is allowed and produces an empty file (signals
        "subagent wrote nothing" without a missing-file ambiguity).
        """
        _atomic_write_text(self.operator_dir / _DIFF_FILE, diff)

    def close(self, outcome: dict[str, Any]) -> None:
        """Write ``resume_outcome.json`` and mark the session closed.

        :data:`OPERATOR_SCHEMA_VERSION` is merged in so caller can omit it.
        Idempotent: a second :meth:`close` overwrites the first (last-call wins).
        """
        merged = {"schema_version": OPERATOR_SCHEMA_VERSION, **outcome}
        _atomic_write_json(self.operator_dir / _OUTCOME_FILE, merged)
        self._closed = True

    # ------------------------------------------------------------------
    # Context manager protocol
    # ------------------------------------------------------------------

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._closed:
            return None
        # Safety net: if the caller forgot to close (or an exception bubbled
        # through before close was called), still land a resume_outcome.json
        # so consumers like replay-tick always have a final artefact.
        if exc is not None:
            error = f"{exc_type.__name__ if exc_type else 'Error'}: {exc}"
        else:
            error = "session_not_closed"
        outcome: dict[str, Any] = {
            "success": False,
            "mechanic_id": None,
            "cost_usd": None,
            "turns": 0,
            "tick_continued": False,
            "error": error,
        }
        try:
            self.close(outcome)
        except Exception:  # pragma: no cover — best-effort safety net
            logger.exception(
                "Failed to write fallback resume_outcome.json for tick {}",
                self.tick_id,
            )
        # Do NOT suppress the original exception.
        return None


# ---------------------------------------------------------------------------
# Read side
# ---------------------------------------------------------------------------


class OperatorDiagnosticsReader:
    """Read an already-written operator session from disk (D-16).

    The single sanctioned entry-point for parsing operator namespace artefacts.
    Used by ``replay-tick`` (Plan 04.1-04) and any future consumer. Constructing
    a reader does NOT require the session to exist; individual accessors raise
    on missing critical artefacts (yield_signal) but return safe defaults for
    optional ones (attempts, validation_reports, mechanic_diff, resume_outcome).

    Threats:
        - T-04.1-05: :attr:`schema_version` raises :class:`ValueError` on
          unknown versions in ``resume_outcome.json``.
        - T-04.1-06: :meth:`attempts` skips unparseable JSONL lines (logged
          warning) instead of crashing on a partial final line.
    """

    universe_path: Path
    tick_id: str
    operator_dir: Path

    def __init__(self, universe_path: Path, tick_id: str | int) -> None:
        self.universe_path = universe_path
        self.tick_id = str(tick_id)
        self.operator_dir = universe_path / "diagnostics" / f"tick_{self.tick_id}" / "operator"

    def yield_signal(self) -> YieldSignal:
        """Return the persisted :class:`YieldSignal` for this tick.

        Raises:
            FileNotFoundError: if the session never started for this tick.
                Message names the expected path so the operator can debug
                directly.
            json.JSONDecodeError, TypeError, ValueError: propagated from
                :meth:`YieldSignal.from_json` (corrupt payload, schema drift).
        """
        path = self.operator_dir / _YIELD_FILE
        if not path.exists():
            raise FileNotFoundError(
                f"No yield signal at {path}. "
                f"Operator session may not have started for tick {self.tick_id!r}."
            )
        return YieldSignal.from_json(path.read_text(encoding="utf-8"))

    def attempts(self) -> list[dict[str, Any]]:
        """Return the list of authoring-attempt records (one dict per JSONL line).

        Empty list if no attempts were appended. Malformed lines (e.g. a
        truncated final line from a crashed harness) are skipped with a
        :func:`logger.warning` (T-04.1-06 — graceful degradation rather than
        hard failure for forensic readability).
        """
        path = self.operator_dir / _ATTEMPTS_FILE
        if not path.exists():
            return []
        out: list[dict[str, Any]] = []
        for line_num, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSONL line {} in {}", line_num, path)
                continue
            if not isinstance(parsed, dict):
                logger.warning(
                    "Skipping non-object JSONL line {} in {} (got {})",
                    line_num,
                    path,
                    type(parsed).__name__,
                )
                continue
            out.append(parsed)
        return out

    def validation_reports(self) -> list[dict[str, Any]]:
        """Return validation reports sorted by attempt number (zero-padded glob)."""
        vdir = self.operator_dir / _VALIDATION_DIR
        if not vdir.is_dir():
            return []
        return [
            json.loads(p.read_text(encoding="utf-8")) for p in sorted(vdir.glob("attempt_*.json"))
        ]

    def mechanic_diff(self) -> str | None:
        """Return the unified diff produced by the authoring subagent.

        Returns ``None`` if no diff was written. An empty string is a valid
        result and means "subagent wrote nothing" (distinguished from a
        missing file).
        """
        path = self.operator_dir / _DIFF_FILE
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def resume_outcome(self) -> dict[str, Any] | None:
        """Return the final outcome dict, or ``None`` if the session never closed.

        :meth:`OperatorDiagnosticsContext.close` and the safety-net
        ``__exit__`` both produce this artefact; ``None`` means the harness
        crashed hard enough to bypass even ``__exit__`` (rare).
        """
        path = self.operator_dir / _OUTCOME_FILE
        if not path.exists():
            return None
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Expected JSON object in {path}, got {type(loaded).__name__}")
        return loaded

    @property
    def schema_version(self) -> int:
        """Return the on-disk schema_version, or raise on mismatch.

        Returns :data:`OPERATOR_SCHEMA_VERSION` if the session never closed
        (no outcome on disk → assume current). Raises :class:`ValueError` if
        the persisted version differs from the build's supported version
        (T-04.1-05 — prevents silent consumption of incompatible payloads).
        """
        outcome = self.resume_outcome()
        if outcome is None:
            return OPERATOR_SCHEMA_VERSION
        version = outcome.get("schema_version", 1)
        if version != OPERATOR_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported operator diagnostics schema_version={version} at "
                f"{self.operator_dir / _OUTCOME_FILE}; "
                f"this build understands v{OPERATOR_SCHEMA_VERSION}."
            )
        return int(version)
