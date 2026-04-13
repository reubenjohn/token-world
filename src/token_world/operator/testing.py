"""Test-only helpers for the operator.

Ships an :class:`EngineStub` that fabricates :class:`YieldSignal` instances
matching Phase 5's future shape verbatim (D-09/D-10). Phase 5's real engine
will replace this stub; downstream operator code should be unaffected because
both emit the same :class:`YieldSignal`.

Lives in ``src/`` (not ``tests/``) per D-21 / RESEARCH A3 so smoke scripts and
future programmatic drivers can import it without ``sys.path`` gymnastics.
Deliberately NOT re-exported from :mod:`token_world.operator.__init__` — import
explicitly via ``from token_world.operator.testing import EngineStub`` so
test-only code cannot leak into the production API (threat T-04.1-02).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from token_world.operator.yield_signal import YieldSignal

__all__ = ["EngineStub"]


@dataclass(frozen=True, slots=True)
class EngineStub:
    """Emits fabricated :class:`YieldSignal` instances matching the Phase-5 shape.

    DO NOT USE in production code. Swapped out when Phase 5's real engine lands.

    Every :meth:`fabricate_yield` call runs :meth:`YieldSignal.validate` on the
    result before returning, so any accidental drift from the contract fails
    fast inside the Phase 4.1 test suite rather than producing malformed
    signals that downstream authoring subagents silently misinterpret.
    """

    universe_path: Path
    """Temp scaffolded universe root. Stored as :class:`Path`; stringified when
    emitting the signal (:class:`YieldSignal` carries ``universe_path: str``)."""

    def fabricate_yield(
        self,
        *,
        verb: str,
        actor: str,
        tick_id: str = "tick_1",
        target: str | None = None,
        params: dict[str, Any] | None = None,
        action_text: str = "",
        actor_state: dict[str, Any] | None = None,
        candidate_mechanic_ids: list[str] | None = None,
    ) -> YieldSignal:
        """Build a validated :class:`YieldSignal` with sensible defaults.

        Defensive copies of all mutable inputs (``params``, ``actor_state``,
        ``candidate_mechanic_ids``) so repeated calls never accidentally
        alias shared containers — a common Python footgun when passing
        ``[]`` or ``{}`` through default-or-provided flows.

        Raises:
            ValueError: if the fabricated signal fails
                :meth:`YieldSignal.validate` (indicates the stub drifted from
                the contract; bug in this file, not the caller).
        """
        signal = YieldSignal(
            tick_id=tick_id,
            universe_path=str(self.universe_path),
            action_text=action_text,
            classified_action={
                "verb": verb,
                "actor": actor,
                "target": target,
                "params": dict(params or {}),
            },
            actor_state=dict(actor_state or {}),
            candidate_mechanic_ids=list(candidate_mechanic_ids or []),
        )
        signal.validate()  # fail fast if the stub ever drifts from the contract
        return signal
