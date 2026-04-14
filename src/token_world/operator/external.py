"""External operator — file-based protocol for out-of-process authoring (v1.1).

Instead of invoking the Agent SDK in-process (:class:`OperatorHarness`), the
external operator writes each yield signal to an inbox file and blocks until
a sibling resolution file appears. The *external orchestrator* (in practice a
Claude Code session spawning subagents) is responsible for detecting the yield
file, authoring the mechanic, and writing the resolution marker.

Protocol (v1):

    <universe>/operator_inbox/
        <tick_id>.yield.json      # runner writes; orchestrator reads
        <tick_id>.resolved        # orchestrator writes (after authoring)
        <tick_id>.rejected        # orchestrator writes (refuses the tick)

    <universe>/.stop              # kill switch — any file exists halts loop
    <universe>/operator-log.jsonl # append-only audit trail of resolutions

This mode is zero-marginal-cost: the external orchestrator runs through the
caller's Claude Code subscription (subagents + MCP tools) rather than paid
Agent SDK + Opus, so a 200-tick unattended run costs $0 beyond the engine
LLM calls (which themselves can route via ``TOKEN_WORLD_BACKEND=claude-cli``).

The shape of :class:`OperatorResult` matches :mod:`operator.harness` so
:class:`PlaytestRunner` can swap factories without other changes.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from token_world.operator.yield_signal import YieldSignal

__all__ = [
    "ExternalOperator",
    "ExternalOperatorResult",
    "external_operator_factory",
]


@dataclass(frozen=True, slots=True)
class ExternalOperatorResult:
    """Result of one :meth:`ExternalOperator.handle_yield` call.

    Shape-compatible with :class:`operator.harness.OperatorResult` so callers
    that type-check against either implementation continue to work.
    """

    success: bool
    tick_id: str
    mechanic_id: str | None
    attempts: int
    final_message: str
    cost_usd: float | None
    turns: int
    error: str | None = None


class ExternalOperator:
    """Yields tick authoring to an out-of-process orchestrator via files.

    Args:
        universe: Root of the universe directory.
        timeout_s: Maximum wait for a resolution file before returning
            failure. Default 1800 (30 min).
        poll_s: How often to check the inbox. Default 2.0 s.

    Typical wiring from :class:`PlaytestRunner`::

        runner = PlaytestRunner(
            engine=engine,
            agent=agent,
            ...,
            harness_factory=external_operator_factory,
        )

    The orchestrator is expected to:

    1. Watch ``<universe>/operator_inbox/*.yield.json`` for new files.
    2. For each yield, author a mechanic (reuse existing or write new),
       commit it to ``<universe>/mechanics/``, and write
       ``<tick_id>.resolved`` containing a brief JSON payload with
       ``{"mechanic_id": ..., "attempts": N}``.
    3. On genuine incoherence, write ``<tick_id>.rejected`` with
       ``{"reason": "..."}`` instead.
    4. Append an entry to ``<universe>/operator-log.jsonl``.

    The engine re-scans the mechanic registry at the top of every
    ``run_tick`` (D-02), so re-running after ``.resolved`` lands picks up
    the new file automatically — no explicit reload.
    """

    def __init__(
        self,
        universe: Path,
        *,
        timeout_s: float = 1800.0,
        poll_s: float = 2.0,
    ) -> None:
        self.universe = Path(universe).resolve()
        self.timeout_s = timeout_s
        self.poll_s = poll_s
        self._inbox = self.universe / "operator_inbox"
        self._inbox.mkdir(parents=True, exist_ok=True)
        self._log_path = self.universe / "operator-log.jsonl"
        self._stop_path = self.universe / ".stop"

    # --- paths ---------------------------------------------------------

    def yield_path(self, tick_id: str) -> Path:
        return self._inbox / f"{tick_id}.yield.json"

    def resolved_path(self, tick_id: str) -> Path:
        return self._inbox / f"{tick_id}.resolved"

    def rejected_path(self, tick_id: str) -> Path:
        return self._inbox / f"{tick_id}.rejected"

    # --- public API ----------------------------------------------------

    async def handle_yield(self, signal: YieldSignal) -> ExternalOperatorResult:
        """Write the yield, block on resolution, return a result.

        Uses :func:`asyncio.sleep` so concurrent engines can multiplex if
        needed. The kill switch (``<universe>/.stop``) short-circuits
        immediately with failure.

        Args:
            signal: The locked Phase 4.1 yield contract from the engine.

        Returns:
            :class:`ExternalOperatorResult` — ``success=True`` if a
            ``.resolved`` file landed before timeout; ``False`` otherwise.
        """
        tick_id = signal.tick_id
        y_path = self.yield_path(tick_id)
        r_path = self.resolved_path(tick_id)
        x_path = self.rejected_path(tick_id)

        y_path.write_text(signal.to_json())
        self._append_log(
            {
                "event": "yield_emitted",
                "tick_id": tick_id,
                "verb": signal.classified_action.get("verb"),
                "action_text_head": signal.action_text[:120],
            }
        )
        logger.info("ExternalOperator wrote yield for tick {}; awaiting resolution", tick_id)

        deadline = time.monotonic() + self.timeout_s
        while True:
            if self._stop_path.exists():
                return self._finalize_failure(
                    tick_id, y_path, error="kill_switch", log_event="kill_switch_hit"
                )
            if r_path.exists():
                return self._consume_resolution(tick_id, y_path, r_path, success=True)
            if x_path.exists():
                return self._consume_resolution(tick_id, y_path, x_path, success=False)
            if time.monotonic() >= deadline:
                return self._finalize_failure(
                    tick_id, y_path, error="timeout", log_event="resolution_timeout"
                )
            await asyncio.sleep(self.poll_s)

    # --- internals -----------------------------------------------------

    def _consume_resolution(
        self,
        tick_id: str,
        y_path: Path,
        marker: Path,
        *,
        success: bool,
    ) -> ExternalOperatorResult:
        payload: dict[str, object] = {}
        try:
            payload = json.loads(marker.read_text() or "{}")
        except json.JSONDecodeError as e:
            logger.warning("Malformed resolution marker for {}: {}", tick_id, e)

        mechanic_id = payload.get("mechanic_id") if isinstance(payload, dict) else None
        attempts_raw = payload.get("attempts") if isinstance(payload, dict) else 0
        attempts = int(attempts_raw) if isinstance(attempts_raw, int | str) else 0
        error = payload.get("reason") if isinstance(payload, dict) and not success else None

        for p in (y_path, marker):
            with contextlib.suppress(FileNotFoundError):
                p.unlink()

        self._append_log(
            {
                "event": "resolution_consumed",
                "tick_id": tick_id,
                "success": success,
                "mechanic_id": mechanic_id,
                "attempts": attempts,
                "reason": error,
            }
        )
        logger.info(
            "ExternalOperator consumed {} for tick {} (mechanic={})",
            "resolved" if success else "rejected",
            tick_id,
            mechanic_id,
        )
        return ExternalOperatorResult(
            success=success,
            tick_id=tick_id,
            mechanic_id=mechanic_id if isinstance(mechanic_id, str) else None,
            attempts=attempts,
            final_message=str(payload),
            cost_usd=0.0,
            turns=0,
            error=str(error) if error else None,
        )

    def _finalize_failure(
        self,
        tick_id: str,
        y_path: Path,
        *,
        error: str,
        log_event: str,
    ) -> ExternalOperatorResult:
        with contextlib.suppress(FileNotFoundError):
            y_path.unlink()
        self._append_log({"event": log_event, "tick_id": tick_id})
        logger.warning("ExternalOperator {} for tick {}", log_event, tick_id)
        return ExternalOperatorResult(
            success=False,
            tick_id=tick_id,
            mechanic_id=None,
            attempts=0,
            final_message="",
            cost_usd=0.0,
            turns=0,
            error=error,
        )

    def _append_log(self, entry: dict[str, object]) -> None:
        entry = {"ts": datetime.now(UTC).isoformat(), **entry}
        line = json.dumps(entry, sort_keys=True)
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + os.linesep)


def external_operator_factory(universe_dir: Path) -> ExternalOperator:
    """PlaytestRunner-compatible factory returning a fresh :class:`ExternalOperator`.

    Configuration knobs can be overridden through environment variables:

    - ``TOKEN_WORLD_OPERATOR_TIMEOUT_S`` (float) — per-yield wait ceiling.
    - ``TOKEN_WORLD_OPERATOR_POLL_S`` (float) — filesystem poll interval.
    """
    timeout = float(os.environ.get("TOKEN_WORLD_OPERATOR_TIMEOUT_S", "1800"))
    poll = float(os.environ.get("TOKEN_WORLD_OPERATOR_POLL_S", "2.0"))
    return ExternalOperator(universe_dir, timeout_s=timeout, poll_s=poll)
