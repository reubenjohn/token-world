"""Operator subpackage — Agent SDK driver for the yield→author→resume loop.

Public API:
    - :class:`YieldSignal`: locked contract between Phase 5's engine and the
      Phase 4.1 operator (D-07, D-10).
    - :data:`SCHEMA_VERSION`: current YieldSignal schema version.

The testing-only ``EngineStub`` lives in :mod:`token_world.operator.testing`
and is deliberately NOT re-exported here to keep the production API free of
test helpers (D-09/D-10/D-21).
"""

from __future__ import annotations

from token_world.operator.yield_signal import SCHEMA_VERSION, YieldSignal

__all__ = ["SCHEMA_VERSION", "YieldSignal"]
