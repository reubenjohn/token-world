"""Operator subpackage — Agent SDK driver for the yield→author→resume loop.

Public API is populated incrementally by Phase 4.1 plans. Plan 04.1-01 adds
``YieldSignal`` + ``SCHEMA_VERSION``. The testing-only ``EngineStub`` lives in
``token_world.operator.testing`` and is deliberately NOT re-exported here to
keep the production API free of test helpers (Phase 4.1 D-09/D-10/D-21).
"""

from __future__ import annotations

__all__: list[str] = []
