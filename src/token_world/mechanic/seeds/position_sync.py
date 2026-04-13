"""MECH06 position_sync seed: involuntary post-move hook.

Watches for newly-added ``located_in`` edges and copies the destination's
spatial anchor (``centroid``, ``bbox`` midpoint, or point ``position``) into
the actor's ``position`` property. This keeps continuous and discrete
coordinates synchronized after any mechanic that moves an agent, so later
spatial queries (``nearest``, ``within``, LOS) see the actor where they
actually are.

Chain contract:
    ``ChainExecutionEngine`` emits ``add_edge`` mutations with
    ``mutation.target = "alice->room_b"`` and splits that on ``"->"`` to
    produce the chain-ctx target. So when position_sync fires reactively,
    ``ctx.target == ctx.actor`` (both are the moved agent). The mechanic
    resolves the new location via ``located_in`` neighbors rather than
    trusting ``ctx.target`` to be the destination.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from token_world.graph import Mutation
from token_world.mechanic.matchers import EdgeMatcher, Matcher
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _current_location

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


def _spatial_anchor(props: dict) -> list[Any] | None:
    """Return a two-coordinate list representing the node's position, or None.

    Preference order (deterministic so chained writes are idempotent):
    1. Explicit ``centroid`` property (e.g. room metadata).
    2. ``bbox`` midpoint when bbox is a 4-element ``[x0, y0, x1, y1]`` list.
    3. ``position`` when the node is itself a point.
    """
    centroid = props.get("centroid")
    if isinstance(centroid, list) and len(centroid) == 2:
        return [centroid[0], centroid[1]]
    bbox = props.get("bbox")
    if isinstance(bbox, list) and len(bbox) == 4:
        x0, y0, x1, y1 = bbox
        try:
            return [(x0 + x1) / 2, (y0 + y1) / 2]
        except TypeError:
            return None
    position = props.get("position")
    if isinstance(position, list) and len(position) == 2:
        return [position[0], position[1]]
    return None


class PositionSyncMechanic(Mechanic):
    """Copy destination centroid/bbox-midpoint into actor.position on move.

    This is an involuntary mechanic — it watches for ``add_edge`` mutations
    whose ``relation == "located_in"`` and fires as a post-hook. The
    chain-engine's target after ``->`` splitting is the moving agent, so
    the mechanic walks the agent's ``located_in`` edges to find the
    destination rather than trusting the raw mutation payload.
    """

    id = "position_sync"
    description = "Post-move hook: copy destination centroid into actor.position"
    voluntary = False
    tags: list[str] = ["spatial", "post-move"]

    def watches(self) -> list[Matcher]:
        return [EdgeMatcher(event_type="add_edge", edge_label="located_in")]

    def check(self, ctx: MechanicContext) -> CheckResult:
        # The chain engine targets the src of the edge (the moved agent).
        actor_id = ctx.target
        if not ctx.has_node(actor_id):
            return CheckResult(passed=False, reasons=["moved node does not exist"])
        dst = _current_location(ctx, actor_id)
        if dst is None:
            return CheckResult(
                passed=False,
                reasons=["no located_in neighbor for sync target"],
            )
        dst_props = ctx.query_node(dst)
        anchor = _spatial_anchor(dst_props)
        if anchor is None:
            return CheckResult(
                passed=False,
                reasons=["destination has no centroid/bbox/position to sync"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        actor_id = ctx.target
        dst = _current_location(ctx, actor_id)
        if dst is None:
            return []
        dst_props = ctx.query_node(dst)
        anchor = _spatial_anchor(dst_props)
        if anchor is None:
            return []
        return [ctx.set(actor_id, "position", anchor)]
