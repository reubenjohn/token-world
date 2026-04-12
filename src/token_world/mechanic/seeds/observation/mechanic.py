"""Observation seed mechanic: agent observes entities at current location."""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class ObservationMechanic(Mechanic):
    """Agent observes entities and properties at current location.

    Preconditions:
        - Actor exists and has a ``location`` property.

    Side effects:
        - None (read-only mechanic per D-04). The observation content is
          synthesized by the simulation engine from graph state.
    """

    id = "observation"
    description = "Agent observes entities and properties at current location"
    voluntary = True

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["Actor does not exist"])
        actor_props = ctx.query_node(ctx.actor)
        if "location" not in actor_props:
            return CheckResult(passed=False, reasons=["Actor has no location"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        # Read-only mechanic (D-04): returns empty list
        return []
