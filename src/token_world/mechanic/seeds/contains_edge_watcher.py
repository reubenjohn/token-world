"""Contains-edge watcher seed mechanic: reacts to items entering or leaving containers.

Phase 18 chain-seed corpus — REQ-V12-DASHBOARD-06.
Demonstrates EdgeMatcher on the ``contains`` edge relation.

This is an involuntary mechanic that fires whenever a ``contains`` edge is
added or removed (i.e. an item is placed into or taken out of a container).
It updates ``item_count`` on the container node to keep a cached count
consistent with graph ground truth.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.matchers import EdgeMatcher, Matcher
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class ContainsEdgeWatcherMechanic(Mechanic):
    """Keeps ``item_count`` on containers in sync with ``contains`` edges.

    Watches for addition or removal of ``contains`` edges.  When triggered,
    counts all outgoing ``contains`` edges from the edge's *source* node
    (the container) and writes the count to ``item_count``.

    This cached count lets the observation layer and mechanics read container
    fullness in O(1) without walking the graph.

    Preconditions:
        - The source node of the ``contains`` edge exists.

    Side effects:
        - Sets ``item_count = <current contains-edge count>`` on the container.

    Chain role:
        Downstream mechanics can watch ``item_count`` changes to trigger
        events like "container overflowing" or "container now empty".
    """

    id = "contains_edge_watcher"
    description = "Keeps item_count on containers in sync with contains edges"
    voluntary = False
    tags = ["reactive", "container", "chain", "core"]

    def watches(self) -> list[Matcher]:
        # Fire on both add and remove of a contains edge
        return [
            EdgeMatcher(event_type="add_edge", edge_label="contains"),
            EdgeMatcher(event_type="remove_edge", edge_label="contains"),
        ]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["Container node does not exist"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        # ctx.target is the *source* of the edge mutation (the container node).
        # Count its current outgoing contains edges using the relation filter.
        count = len(ctx.neighbors(ctx.target, relation="contains"))
        return [ctx.mutate(ctx.target, "item_count", count)]

    def describe(self) -> str:
        return (
            "Watches ``contains`` edge additions and removals. Updates "
            "``item_count`` on the container node to reflect the current "
            "number of contained items — enabling O(1) fullness checks."
        )
