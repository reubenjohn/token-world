"""MECH-SEED hum: actor hums a tune, setting humming=True on the actor.

The simplest possible expressive mechanic — no preconditions beyond the actor
existing. Used as a baseline for "always succeeds" action resolution so a
resident agent can always do *something* productive even in a sparse world.

``humming=True`` is a toggle property. A future mechanic (e.g. ``stop_humming``)
can clear it; for now, ``hum`` is a one-shot state setter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class HumMechanic(Mechanic):
    """Agent hums a tune; sets ``humming=True`` on the actor.

    Preconditions:
        - Actor exists (no other preconditions — humming is always possible).

    Side effects:
        - Writes ``actor.humming = True``.
    """

    id = "hum"
    description = "Agent hums a tune; sets humming=True on the actor."
    voluntary = True
    tags: list[str] = ["social", "expressive"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return [ctx.mutate(ctx.actor, "humming", True)]
