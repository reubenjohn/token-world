"""Mechanic framework for Token World simulation."""

from __future__ import annotations

from token_world.mechanic.context import MechanicContext
from token_world.mechanic.diagnostics import (
    SCHEMA_VERSION,
    DiagnosticsSink,
    TickDiagnostics,
)
from token_world.mechanic.engine import ChainExecutionEngine
from token_world.mechanic.loader import discover_mechanic_modules, load_mechanic_classes
from token_world.mechanic.matchers import (
    DecayMatcher,
    EdgeMatcher,
    Matcher,
    NodeMatcher,
    PropertyChangeMatcher,
    TickMatcher,
    VerbMatcher,
    WorldPropertyMatcher,
)
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.registry import MechanicInfo, MechanicRegistry, MechanicVersion
from token_world.mechanic.trace import (
    ExecutionTrace,
    TraceNode,
    collect_mutations,
    walk_trace,
)

__all__ = [
    "SCHEMA_VERSION",
    "ChainExecutionEngine",
    "CheckResult",
    "DecayMatcher",
    "DiagnosticsSink",
    "EdgeMatcher",
    "ExecutionTrace",
    "Matcher",
    "Mechanic",
    "MechanicContext",
    "MechanicInfo",
    "MechanicRegistry",
    "MechanicVersion",
    "NodeMatcher",
    "PropertyChangeMatcher",
    "TickDiagnostics",
    "TickMatcher",
    "TraceNode",
    "VerbMatcher",
    "WorldPropertyMatcher",
    "collect_mutations",
    "discover_mechanic_modules",
    "load_mechanic_classes",
    "walk_trace",
]
