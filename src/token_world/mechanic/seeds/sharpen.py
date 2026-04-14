"""MECH-SEED sharpen: actor sharpens a carried item on a whetstone in the room.

Models the tool-maintenance craft interaction. A whetstone is identified by
``subtype="tool"`` and ``material="stone"`` (the canonical whetstone signature).
The target item is the actor's first "carrying" neighbor; if the actor carries
nothing, the mechanic falls back to the first non-whetstone tool entity in the
room.

Sharpness is a float in [0.0, 1.0] incremented by 0.1 per application,
clamped at 1.0. Entities that start without a ``sharpness`` property are
treated as sharpness=0.5 (somewhat dull — coherent for a used tool).

T-14-03 (Tampering, sharpen sharpness clamp): accepted — the 1.0 clamp
prevents unbounded growth; no conservation property is at stake.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _current_location

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


_SHARPNESS_INCREMENT: float = 0.1
_SHARPNESS_DEFAULT: float = 0.5
_SHARPNESS_MAX: float = 1.0


def _find_whetstone(ctx: MechanicContext, room: str) -> str | None:
    """Return the first entity in *room* with subtype="tool" and material="stone"."""
    for node_id in ctx.find_nodes():
        if room not in ctx.neighbors(node_id, relation="located_in"):
            continue
        props = ctx.query_node(node_id)
        if props.get("subtype") == "tool" and props.get("material") == "stone":
            return node_id
    return None


class SharpenMechanic(Mechanic):
    """Agent sharpens an item on a whetstone in the current room.

    Preconditions:
        - Actor exists.
        - Actor has a ``located_in`` room.
        - Room contains at least one entity with ``subtype="tool"`` and
          ``material="stone"`` (the whetstone).

    Side effects:
        - Increments the target item's ``sharpness`` by 0.1, clamped at 1.0.
        - Target selection: actor's first "carrying" neighbor, else the first
          non-whetstone tool entity in the room.
    """

    id = "sharpen"
    description = "Agent sharpens an item on a whetstone in the current room."
    voluntary = True
    tags: list[str] = ["tool", "craft"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        room = _current_location(ctx, ctx.actor)
        if room is None:
            return CheckResult(passed=False, reasons=["actor has no located_in location"])
        if _find_whetstone(ctx, room) is None:
            return CheckResult(passed=False, reasons=["no whetstone nearby"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        room = _current_location(ctx, ctx.actor)
        if room is None:
            return []
        whetstone_id = _find_whetstone(ctx, room)
        if whetstone_id is None:
            return []

        # Find the item to sharpen: prefer something the actor is carrying.
        target_id: str | None = None

        # Check ctx.target first (explicit action target).
        if ctx.target and ctx.has_node(ctx.target) and ctx.target != whetstone_id:
            target_id = ctx.target

        # Fall back to actor's first "carrying" neighbor.
        if target_id is None:
            for carried in ctx.neighbors(ctx.actor, relation="carrying"):
                target_id = carried
                break

        # Fall back to first non-whetstone tool entity in the room.
        if target_id is None:
            for node_id in ctx.find_nodes():
                if node_id == whetstone_id:
                    continue
                if room not in ctx.neighbors(node_id, relation="located_in"):
                    continue
                props = ctx.query_node(node_id)
                if props.get("subtype") == "tool":
                    target_id = node_id
                    break

        if target_id is None:
            return []

        current = ctx.query_node(target_id).get("sharpness", _SHARPNESS_DEFAULT)
        try:
            current = float(current)
        except (TypeError, ValueError):
            current = _SHARPNESS_DEFAULT
        new_sharpness = min(round(current + _SHARPNESS_INCREMENT, 10), _SHARPNESS_MAX)
        return [ctx.mutate(target_id, "sharpness", new_sharpness)]
