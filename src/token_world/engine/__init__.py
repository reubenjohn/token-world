"""Simulation engine — the in-tool LLM-driven tick pipeline.

Per Phase 5 CONTEXT D-01: five explicit stages (classify -> match -> decide ->
execute -> observe), orchestrated by :class:`SimulationEngine.run_tick`.

Components available in this package:
- Models (ClassifiedAction, ClassifierVerdict, Decision, …) — Pydantic pipeline types.
- Observer — Sonnet-backed observation synthesiser (D-15 hard-grounding, Plan 05-05).
  Wired into the tick pipeline by Plan 05-08; standalone and testable here.
- ConservationChecker / ConservationVerdict — post-execute conservation enforcement
  (D-16, GAP-ENG06, Plan 05-06). Orchestrator wired in Plan 05-08.
- TickSummaryWriter / build_tick_summary — per-tick JSON summary writer (D-20, SIM-11,
  Plan 05-07). Orchestrator wired in Plan 05-08.
"""

from __future__ import annotations

from token_world.engine.conservation import ConservationChecker, ConservationVerdict
from token_world.engine.models import (
    ClassifiedAction,
    ClassifierVerdict,
    Decision,
    ExecuteDecision,
    MatchedResult,
    MatchResult,
    NoMatchResult,
    RefuseDecision,
    TickSummary,
    VerdictLowConfidence,
    VerdictNoSuchTarget,
    VerdictNoViableAction,
    VerdictOk,
    YieldDecision,
)
from token_world.engine.observer import Observer
from token_world.engine.summary_writer import TickSummaryWriter, build_tick_summary

__all__ = [
    "ClassifiedAction",
    "ClassifierVerdict",
    "ConservationChecker",
    "ConservationVerdict",
    "Decision",
    "ExecuteDecision",
    "MatchedResult",
    "MatchResult",
    "NoMatchResult",
    "Observer",
    "RefuseDecision",
    "TickSummary",
    "TickSummaryWriter",
    "VerdictLowConfidence",
    "VerdictNoSuchTarget",
    "VerdictNoViableAction",
    "VerdictOk",
    "YieldDecision",
    "build_tick_summary",
]
