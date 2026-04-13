"""Mechanic framework for Token World simulation."""

from __future__ import annotations

from token_world.mechanic.context import MechanicContext
from token_world.mechanic.engine import ChainExecutionEngine
from token_world.mechanic.loader import discover_mechanic_modules, load_mechanic_classes
from token_world.mechanic.matchers import (
    EdgeMatcher,
    Matcher,
    NodeMatcher,
    PropertyChangeMatcher,
)
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.registry import MechanicInfo, MechanicRegistry, MechanicVersion
from token_world.mechanic.trace import ExecutionTrace, TraceNode

__all__ = [
    "ChainExecutionEngine",
    "CheckResult",
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
    "TraceNode",
    "discover_mechanic_modules",
    "load_mechanic_classes",
]
