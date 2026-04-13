"""MECH15 consume seed: actor eats a held food entity, reducing hunger atomically.

The canonical conservation micro-case: remove one node (the food),
decrement one scalar on the actor (the hunger), in a single tick.

UC-R02 mapping
--------------
alice has ``hunger=80`` and holds an ``apple`` with ``nutrition=25``.
apply emits:

    - ``remove_node("apple")`` -- the apple leaves the world
    - ``set(alice, "hunger", 55)`` -- 80 - 25 = 55, floor at 0

UC-R02's ``expected_observations`` chain passes:

    - ``not_has_edge(alice, apple, "holds")`` ✓ (edge removed with node)
    - ``property_equals(alice.hunger, 55)`` ✓

Non-food targets, non-held targets, or targets without ``nutrition``
are refused (check-time): consume is specifically the food-removal
primitive, not a generic "destroy entity" mechanic. A future
``burn`` or ``discard`` mechanic can own those shapes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class ConsumeMechanic(Mechanic):
    """Agent eats a held food entity.

    Preconditions (check):
        - Actor exists.
        - Target exists.
        - Actor holds the target (``actor -[holds]-> target``).
        - Target has a numeric ``nutrition`` property.
        - Actor has a numeric ``hunger`` property.

    Side effects (apply):
        - Target node is removed from the graph (``remove_node``),
          which also drops the holds edge as a consequence.
        - Actor's ``hunger`` is decreased by ``nutrition``, floored
          at 0 so hunger never goes negative (semantics question
          beyond Phase 4; floor is the conservative choice).
    """

    id = "consume"
    description = "Agent eats a held food entity, reducing hunger by its nutrition value"
    voluntary = True
    tags: list[str] = ["object_interaction", "resource"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])
        held = set(ctx.neighbors(ctx.actor, relation="holds"))
        if ctx.target not in held:
            return CheckResult(
                passed=False,
                reasons=[f"actor does not hold target {ctx.target!r}"],
            )
        target_props = ctx.query_node(ctx.target)
        nutrition = target_props.get("nutrition")
        if not isinstance(nutrition, (int, float)):
            return CheckResult(
                passed=False,
                reasons=[f"target {ctx.target!r} has no numeric nutrition property"],
            )
        actor_props = ctx.query_node(ctx.actor)
        hunger = actor_props.get("hunger")
        if not isinstance(hunger, (int, float)):
            return CheckResult(
                passed=False,
                reasons=["actor has no numeric hunger property"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        actor_props = ctx.query_node(ctx.actor)
        target_props = ctx.query_node(ctx.target)
        hunger = actor_props["hunger"]
        nutrition = target_props["nutrition"]
        new_hunger = hunger - nutrition
        if new_hunger < 0:
            new_hunger = 0
        # Preserve int-ness when both inputs are int.
        if isinstance(hunger, int) and isinstance(nutrition, int):
            new_hunger = int(new_hunger)
        return [
            ctx.set(ctx.actor, "hunger", new_hunger),
            ctx.remove_node(ctx.target),
        ]
