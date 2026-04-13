"""MECH04 aoe seed: area-of-effect damage fan-out via a radius query.

Applies a boolean ``damaged=True`` flag to every node within an axis-aligned
bbox centred on the target's position. The bbox edge length is ``2 *
radius`` where ``radius`` is read from the target (``blast_radius`` prop) or
defaults to ``3.0`` — matches UC-S04's fireball radius. Emits one mutation
per affected node so the chain engine can observe per-victim side effects.

The mechanic is deliberately boolean-flag-based rather than numeric damage.
UC-S04's assertions check ``damaged=True`` / absence of ``damaged``; a
follow-up resource-conservation plan (v2) would read HP and compute
reductions. Booleans are forward-compatible: any future "compute hp
reduction" mechanic can chain off ``damaged=True`` via a
``PropertyChangeMatcher``.

Filter: the actor is never damaged by their own blast. Nodes without a
2D anchor (position or bbox) are skipped silently — the spatial index
never saw them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


_DEFAULT_BLAST_RADIUS: float = 3.0


def _point_from_props(props: dict) -> tuple[float, float] | None:
    position = props.get("position")
    if isinstance(position, list) and len(position) == 2:
        try:
            return float(position[0]), float(position[1])
        except (TypeError, ValueError):
            return None
    return None


class AreaOfEffectMechanic(Mechanic):
    """Agent triggers an AoE blast centred on the target's position.

    Preconditions:
        - Actor exists.
        - Target exists and has a 2-element ``position`` list.

    Side effects:
        - For every positioned node inside the blast bbox (except the
          actor themselves), sets ``damaged=True``. One mutation per
          victim.

    Blast geometry:
        - Centre = ``target.position``.
        - Radius = ``target.blast_radius`` (float) if present, else
          ``_DEFAULT_BLAST_RADIUS`` = 3.0.
        - Bbox = ``[cx - r, cy - r, cx + r, cy + r]`` (axis-aligned square
          tightly enclosing the circle; R-tree ``within`` is bbox-native).
    """

    id = "aoe"
    description = "Agent triggers an AoE blast that damages everything in radius"
    voluntary = True
    tags: list[str] = ["spatial", "aoe"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])
        if _point_from_props(ctx.query_node(ctx.target)) is None:
            return CheckResult(
                passed=False,
                reasons=["target has no 2D position to centre the blast"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        target_props = ctx.query_node(ctx.target)
        centre = _point_from_props(target_props)
        if centre is None:
            return []
        raw_radius = target_props.get("blast_radius", _DEFAULT_BLAST_RADIUS)
        try:
            radius = float(raw_radius)
        except (TypeError, ValueError):
            radius = _DEFAULT_BLAST_RADIUS
        cx, cy = centre
        bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
        try:
            hits = ctx.spatial.within(bbox)
        except Exception:  # pragma: no cover -- defensive
            hits = []
        muts: list[Mutation] = []
        seen: set[str] = set()
        for hit in hits:
            if hit in seen:
                continue
            seen.add(hit)
            if hit == ctx.actor:
                continue
            # Rooms (subtype=room) are containers — they border the blast
            # but shouldn't be "damaged" themselves. Filter them out to
            # keep the fan-out scoped to contents-of-room rather than
            # room-itself. UC-S04 doesn't assert on the room, so either
            # behaviour would pass; excluding rooms is the more defensible
            # default.
            hit_props = ctx.query_node(hit)
            if hit_props.get("subtype") == "room":
                continue
            # Additional circle-refinement: bbox over-approximates the
            # circle at the corners. Re-check true Euclidean distance so
            # UC-S04 partitions exactly the 3 inside vs 2 outside nodes.
            p = _point_from_props(hit_props)
            if p is None:
                # bbox-only node: keep it (it overlapped the blast bbox).
                muts.append(ctx.mutate(hit, "damaged", True))
                continue
            dx = p[0] - cx
            dy = p[1] - cy
            if dx * dx + dy * dy > radius * radius:
                continue
            muts.append(ctx.mutate(hit, "damaged", True))
        return muts
