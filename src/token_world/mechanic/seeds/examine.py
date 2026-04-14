"""MECH-SEED examine: agent examines a nearby entity, recording its visible properties.

Writes ``actor.last_examined`` with a snapshot of the target entity's properties
(or the current room's properties if no specific target is identified).

Rationale: provides grounded "what do I see when I look closely" semantics.
Unlike ``look``, which records *which* entities are present, ``examine`` records
*what* a single entity is like — its current properties as ground truth.

``ctx.target`` carries the target entity id when the action parser resolves a
specific object (e.g. "examine the chest"). When ``ctx.target`` is an empty
string or absent, the mechanic falls back to examining the room itself so the
verb always produces a mutation and the engine has something to ground an
observation from.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _current_location

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class ExamineMechanic(Mechanic):
    """Agent examines a nearby entity; records its visible properties.

    Preconditions:
        - Actor exists.
        - Actor has a ``located_in`` room.

    Side effects:
        - If ``ctx.target`` resolves to a node in the actor's room: writes
          ``actor.last_examined = {"target": target_id, "props": <property snapshot>}``.
        - Otherwise (no target or target not in room): examines the room itself
          and writes ``actor.last_examined = {"target": room_id, "props": <room snapshot>}``.
    """

    id = "examine"
    description = "Agent examines a nearby entity; records its visible properties."
    voluntary = True
    tags: list[str] = ["observation"]

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

        # Determine the examination target. ctx.target may be "" when the
        # action text doesn't name a specific entity — fall back to the room.
        target_id: str | None = None
        if ctx.target and ctx.has_node(ctx.target):
            # Verify the target is co-located in the actor's room.
            if room in ctx.neighbors(ctx.target, relation="located_in"):
                target_id = ctx.target
            # Also accept if the target IS the room (actor examines the room by name).
            elif ctx.target == room:
                target_id = room

        if target_id is None:
            # No resolvable nearby target — examine the room.
            target_id = room

        props_snapshot = ctx.query_node(target_id)
        last_examined = {"target": target_id, "props": props_snapshot}
        return [ctx.mutate(ctx.actor, "last_examined", last_examined)]
