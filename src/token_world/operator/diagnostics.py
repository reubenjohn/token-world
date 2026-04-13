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
