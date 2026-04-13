"""MECH02 look seed: agent observes visible entities in the current room.

Writes ``actor.last_observed`` with a deduplicated list of visible neighbor
entity ids. Critically, this mechanic intentionally does NOT grant
perceptual knowledge across occluders (UC-S02): it never writes a ``saw``
property, and does not return entities whose room is separated from the
actor's current room by a node with ``occludes=True``.

Degraded-query fallback — ``ctx.spatial.segment_intersections`` is GAP-GRAPH02
(see ``docs/guides/authoring-mechanics.md`` § Known gaps). Rather than ship
a stub, this mechanic falls back to a room-local scan: visible = entities
sharing the actor's current ``located_in`` room, minus any entity that is
itself an ``occludes=True`` wall. Bob-in-another-room is NOT visible because
he is not a located_in-neighbor of alice's room, so the UC-S02 "cannot see
across the wall" invariant holds by construction. When GAP-GRAPH02 is
closed, this mechanic should switch to a segment-ray check that can see
across rooms if no occluder intersects the line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _current_location

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class LookMechanic(Mechanic):
    """Agent looks around; records room-local visible entities.

    Preconditions:
        - Actor exists.
        - Actor has a ``located_in`` edge to some room.

    Side effects:
        - Writes ``actor.last_observed`` = sorted list of visible entity ids
          (all entities whose ``located_in`` points at the actor's room and
          that do not themselves occlude vision — i.e., walls are filtered).
        - Does NOT write ``actor.saw`` — that property would imply
          perceptual knowledge, and we are not asserting that across
          occluders. The "cannot see X" narrative is synthesized by the
          engine from the absence of X in ``last_observed``.
    """

    id = "look"
    description = "Agent observes entities in the current room (occluder-aware)"
    voluntary = True
    tags: list[str] = ["spatial", "observation"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if _current_location(ctx, ctx.actor) is None:
            return CheckResult(
                passed=False,
                reasons=["actor has no located_in location"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        room = _current_location(ctx, ctx.actor)
        if room is None:
            return []
        # Find everything located_in the same room. Since located_in edges
        # point agent/entity -> room, we walk in-neighbors of the room by
        # scanning nodes that have a located_in edge to it.
        visible: list[str] = []
        for node_id in ctx.find_nodes():
            if node_id == ctx.actor:
                continue
            if room not in ctx.neighbors(node_id, relation="located_in"):
                continue
            props = ctx.query_node(node_id)
            # Occluders (walls) are in the room metadata but should not be
            # "seen" as objects of interest.
            if props.get("occludes") is True:
                continue
            visible.append(node_id)
        visible.sort()
        return [ctx.mutate(ctx.actor, "last_observed", visible)]
