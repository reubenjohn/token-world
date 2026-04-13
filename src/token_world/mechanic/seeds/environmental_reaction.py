"""Environmental reaction seed mechanic: fire spreads to adjacent flammable entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.matchers import Matcher, PropertyChangeMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class EnvironmentalReactionMechanic(Mechanic):
    """Fire spreads to adjacent flammable entities when temperature changes.

    This is an involuntary mechanic that watches for temperature property changes.
    When a node's temperature reaches >= 100, fire spreads to adjacent flammable
    entities that are not already hot.

    Preconditions:
        - Target node exists and has a ``temperature`` >= 100.
        - At least one neighbor is flammable.

    Side effects:
        - Sets ``temperature=150`` and ``on_fire=True`` on flammable neighbors
          whose current temperature is < 100.
    """

    id = "environmental_reaction"
    description = "Fire spreads to adjacent flammable entities when temperature changes"
    voluntary = False
    tags = ["environmental", "reactive", "core"]

    def watches(self) -> list[Matcher]:
        return [PropertyChangeMatcher(property_name="temperature")]

    def check(self, ctx: MechanicContext) -> CheckResult:
        # Target is the node whose temperature changed
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["Target does not exist"])
        try:
            temp = ctx.query_node(ctx.target, "temperature")
        except KeyError:
            return CheckResult(passed=False, reasons=["No temperature property"])
        if not isinstance(temp, (int, float)) or temp < 100:
            return CheckResult(
                passed=False, reasons=[f"Temperature {temp} too low for fire spread"]
            )
        # Check for flammable neighbors
        neighbors = ctx.query_neighbors(ctx.target)
        flammable = [n for n in neighbors if ctx.query_node(n).get("flammable", False)]
        if not flammable:
            return CheckResult(passed=False, reasons=["No flammable neighbors"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        neighbors = ctx.query_neighbors(ctx.target)
        mutations: list[Mutation] = []
        for n in neighbors:
            props = ctx.query_node(n)
            if props.get("flammable", False) and props.get("temperature", 0) < 100:
                mutations.append(ctx.mutate(n, "temperature", 150))
                mutations.append(ctx.mutate(n, "on_fire", True))
        return mutations
