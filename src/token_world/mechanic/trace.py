"""Execution trace: tree structure recording mechanic invocation chains."""

from __future__ import annotations

from dataclasses import dataclass, field

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult


@dataclass
class TraceNode:
    """A single node in the execution trace tree.

    Attributes:
        mechanic_id: The mechanic that was invoked.
        actor: The actor (agent/entity) that triggered the invocation.
        target: The target of the invocation.
        check_result: The result of the mechanic's precondition check.
        mutations: Mutations produced by the mechanic's apply().
        children: Child trace nodes (from chain-triggered involuntary mechanics).
    """

    mechanic_id: str
    actor: str
    target: str
    check_result: CheckResult
    mutations: list[Mutation]
    children: list[TraceNode] = field(default_factory=list)


@dataclass
class ExecutionTrace:
    """Complete execution trace for a mechanic invocation.

    Attributes:
        root: The root trace node (the initially invoked mechanic).
        total_mechanics_executed: Total number of mechanics that fired
            (including chain-triggered involuntary mechanics).
        max_depth_reached: The maximum chain depth actually reached.
        truncated: Whether execution was stopped due to max_depth limit.
    """

    root: TraceNode
    total_mechanics_executed: int
    max_depth_reached: int
    truncated: bool = False
