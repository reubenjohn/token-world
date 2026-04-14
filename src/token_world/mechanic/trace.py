"""Execution trace: tree structure recording mechanic invocation chains.

This module also provides pure walker helpers (:func:`walk_trace`,
:func:`collect_mutations`) extracted on 2026-04-14 from four near-identical
call sites — ``engine/summary_writer.py``, ``engine/engine.py``,
``engine/observer.py``, and ``playtest/scorer.py`` — per IN-02 tech-debt
closure guidance. All four were walking ``trace.root`` recursively or via a
stack to aggregate mutation lists. They now delegate to these helpers so the
walk logic lives in exactly one place.
"""

from __future__ import annotations

from collections.abc import Iterator
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


# ---------------------------------------------------------------------------
# Walker helpers (IN-02 tech-debt closure, 2026-04-14)
#
# Extracted from four near-identical call sites that previously each reimplemented
# a trace-tree walk:
#   - engine/summary_writer.py::_flatten_trace_mutations (stack-based)
#   - engine/engine.py::_flatten_mutations             (stack-based)
#   - engine/observer.py::_flatten_mutations           (recursive)
#   - playtest/scorer.py (inline stack-based in _groundedness)
#
# Pre-order depth-first traversal (parent before children, children left-to-right).
# Order is chosen for readability — all four original callers used aggregations
# (``len``, list concatenation) that are order-independent, so callers are
# semantically unchanged.
#
# These helpers are pure: no side effects, no I/O, no mutation of the trace.
# ---------------------------------------------------------------------------


def walk_trace(trace: ExecutionTrace | None) -> Iterator[TraceNode]:
    """Yield every TraceNode in ``trace``, depth-first, pre-order.

    A ``None`` trace yields nothing — callers on the yield/refuse path (where
    no mechanic executed) can uniformly delegate to this helper without a
    guard. The traversal visits the root first, then each child subtree in
    declaration order.

    Args:
        trace: The execution trace, or ``None`` for yield/refuse paths where
            no mechanic fired.

    Yields:
        Every :class:`TraceNode` in the tree, root first, children in order.
    """
    if trace is None:
        return
    # Use an explicit stack rather than recursion: trace depth is bounded by
    # the chain-execution engine's ``max_depth`` but still deeper than the
    # default CPython recursion limit would be comfortable with under pathological
    # involuntary-mechanic chains.
    stack: list[TraceNode] = [trace.root]
    while stack:
        node = stack.pop()
        yield node
        # Reverse so pre-order visits children left-to-right after LIFO pop.
        stack.extend(reversed(node.children))


def collect_mutations(trace: ExecutionTrace | None) -> list[Mutation]:
    """Return a flat list of every Mutation recorded across the trace tree.

    Preserves per-node declaration order — the list of mutations on node N
    appears before the list on node N+1 in traversal order (pre-order
    depth-first). Callers that previously used stack-based LIFO traversal
    (summary_writer, engine) observed a slightly different order, but since
    every known caller aggregates mutations without order-sensitivity
    (count, conservation verify, JSON serialise), this change is semantically
    invisible.

    Args:
        trace: The execution trace, or ``None`` (yield/refuse path with
            no mechanic).

    Returns:
        Flat list of :class:`Mutation` instances. Empty when ``trace`` is
        ``None`` or every node has zero mutations.
    """
    result: list[Mutation] = []
    for node in walk_trace(trace):
        result.extend(node.mutations)
    return result
