"""Operator subpackage — Agent SDK driver for the yield→author→resume loop.

Public API:
    - :class:`YieldSignal`: locked contract between Phase 5's engine and the
      Phase 4.1 operator (D-07, D-10).
    - :data:`SCHEMA_VERSION`: current YieldSignal schema version.
    - :class:`OperatorHarness`: programmatic Agent SDK driver (D-01); call
      ``await harness.handle_yield(signal)`` to drive one tick end-to-end.
    - :class:`OperatorResult`: dataclass returned by ``handle_yield``.
    - :func:`build_mechanic_author_agent`, :func:`mechanic_author_prompt`:
      mechanic-author subagent definition + standalone prompt function
      (the latter reused by Plan 04.1-05 to scaffold
      ``.claude/agents/mechanic-author.md``).

The testing-only ``EngineStub`` lives in :mod:`token_world.operator.testing`
and is deliberately NOT re-exported here to keep the production API free of
test helpers (D-09/D-10/D-21).
"""

from __future__ import annotations

from token_world.operator.harness import OperatorHarness, OperatorResult
from token_world.operator.subagent import (
    build_mechanic_author_agent,
    mechanic_author_prompt,
)
from token_world.operator.yield_signal import SCHEMA_VERSION, YieldSignal

__all__ = [
    "SCHEMA_VERSION",
    "OperatorHarness",
    "OperatorResult",
    "YieldSignal",
    "build_mechanic_author_agent",
    "mechanic_author_prompt",
]
