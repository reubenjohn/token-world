"""MECH-SEED drop: actor drops a carried item into the current room.

Inverse of ``pickup``. Removes the actor→item "carrying" edge and adds a
room→item "contains" edge so the item is discoverable via ``look``.

T-14-04 (Tampering, drop edge removal): mitigated — ``check()`` enforces that
the actor has at least one "carrying" edge before ``apply()`` runs, so the
remove_edge in ``apply`` is always valid.

Design note on "carrying" vs "holds":
    The plan spec uses "carrying" (not "holds", which ``pickup`` uses). These
    are distinct edge relation names. "carrying" suits an explicit drop/carry
    workflow where the actor consciously moves an item; "holds" suits inventory
    management (pickup/give). Seeds are not required to be consistent across
    each other — they are independent; the engine dispatches each by id.
    If a future mechanic needs unification, that is a refactor, not a fix.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _current_location

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class DropMechanic(Mechanic):
    """Agent drops a carried item into the current room.

    Preconditions:
        - Actor exists.
        - Actor has at least one outgoing "carrying" edge.

    Side effects:
        - Removes the ``actor --[carrying]--> item`` edge.
        - Adds the ``room --[contains]--> item`` edge so the item is in the room.
    """

    id = "drop"
    description = "Agent drops a carried item into the current room."
    voluntary = True
    tags: list[str] = ["inventory"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        carrying = ctx.neighbors(ctx.actor, relation="carrying")
        if not carrying:
            return CheckResult(passed=False, reasons=["not carrying anything"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        room = _current_location(ctx, ctx.actor)

        # Prefer ctx.target if actor is explicitly carrying it.
        item_id: str | None = None
        if ctx.target and ctx.has_node(ctx.target):
            carrying = ctx.neighbors(ctx.actor, relation="carrying")
            if ctx.target in carrying:
                item_id = ctx.target

        # Fall back to first carried item.
        if item_id is None:
            for carried in ctx.neighbors(ctx.actor, relation="carrying"):
                item_id = carried
                break

        if item_id is None:
            return []

        muts: list[Mutation] = [ctx.remove_edge(ctx.actor, item_id)]
        if room is not None:
            muts.append(ctx.add_edge(room, item_id, relation="contains"))
        return muts
