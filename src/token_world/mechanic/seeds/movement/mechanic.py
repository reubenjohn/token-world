"""Movement seed mechanic: agent moves between connected locations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class MovementMechanic(Mechanic):
    """Agent moves between connected locations.

    Preconditions:
        - Actor exists and has a ``location`` property.
        - Target location exists.
        - An edge exists from current location to target location.

    Side effects:
        - Sets actor's ``location`` property to the target.
    """

    id = "movement"
    description = "Agent moves between connected locations"
    voluntary = True

    def check(self, ctx: MechanicContext) -> CheckResult:
        # 1. Actor must exist
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["Actor does not exist"])
        # 2. Actor must have a location property
        actor_props = ctx.query_node(ctx.actor)
        location = actor_props.get("location")
        if not location:
            return CheckResult(passed=False, reasons=["Actor has no location"])
        # 3. Target must exist
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["Target location does not exist"])
        # 4. Edge must exist from current location to target
        if not ctx.has_edge(location, ctx.target):
            return CheckResult(passed=False, reasons=[f"No path from {location} to {ctx.target}"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return [ctx.mutate(ctx.actor, "location", ctx.target)]
