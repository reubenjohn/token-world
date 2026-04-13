"""MECH03 find_nearest seed: return the nearest positioned entity matching a filter.

The mechanic uses ``ctx.spatial.nearest`` (GRAPH-06 R-tree) filtered by the
target entity's ``subtype``, and writes the winning id to
``actor.nearest_result``. When the spatial index cannot answer (no indexed
nodes), it falls back to a brute-force Euclidean scan over positioned
nodes with a matching subtype so the mechanic still produces a result on
trivial graphs.

UC-S03 shape: alice at origin, three weapons in an armory; the dagger
(distance ≈ 3.16) is nearer than the sword (7) or the bow (≈ 12.6).
``ctx.target`` carries a reference weapon whose ``subtype`` ("weapon") is
used as the search predicate — not the canonical answer. The mechanic
recomputes the winner so the harness exercise is meaningful.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


def _point_from_props(props: dict) -> tuple[float, float] | None:
    """Return ``(x, y)`` from ``position=[x, y]`` or ``None``.

    ``bbox`` is NOT used here — we need a point-anchor to compute nearest.
    Mechanics that care about bbox-anchor semantics (rooms) go through
    ``position_sync`` beforehand.
    """
    position = props.get("position")
    if isinstance(position, list) and len(position) == 2:
        try:
            return float(position[0]), float(position[1])
        except (TypeError, ValueError):
            return None
    return None


class FindNearestMechanic(Mechanic):
    """Agent finds the nearest entity matching the target's subtype.

    Preconditions:
        - Actor exists and carries a 2-element ``position`` list.
        - Target exists and carries a ``subtype`` string (used as the
          filter key for the nearest query).

    Side effects:
        - Writes ``actor.nearest_result`` = node id of the nearest matching
          entity. Returns the actor's own target unchanged when it is the
          only match.
    """

    id = "find_nearest"
    description = "Agent finds the nearest entity matching a subtype filter"
    voluntary = True
    tags: list[str] = ["spatial", "query"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])
        actor_point = _point_from_props(ctx.query_node(ctx.actor))
        if actor_point is None:
            return CheckResult(
                passed=False,
                reasons=["actor has no 2D position"],
            )
        subtype = ctx.query_node(ctx.target).get("subtype")
        if not isinstance(subtype, str) or not subtype:
            return CheckResult(
                passed=False,
                reasons=["target has no subtype to use as a filter"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        actor_point = _point_from_props(ctx.query_node(ctx.actor))
        subtype = ctx.query_node(ctx.target).get("subtype")
        if actor_point is None or not isinstance(subtype, str):
            return []
        nearest_id = self._find_nearest_id(ctx, actor_point, subtype)
        if nearest_id is None:
            return []
        return [ctx.mutate(ctx.actor, "nearest_result", nearest_id)]

    def _find_nearest_id(
        self,
        ctx: MechanicContext,
        point: tuple[float, float],
        subtype: str,
    ) -> str | None:
        """Return the nearest node id with a matching ``subtype``, or ``None``.

        Prefers ``ctx.spatial.nearest`` (R-tree, post-filtered). Falls back to
        a brute-force Euclidean scan over positioned nodes when the spatial
        index is empty (which happens on graphs where no nodes have
        position/bbox yet — unlikely in UC-S03 but cheap to be robust about).
        """
        # Primary: rtree-backed nearest with subtype filter. Over-fetch so
        # post-filtering still yields at least 1 match when available.
        try:
            candidates = ctx.spatial.nearest(point, k=5, subtype=subtype)
        except Exception:  # pragma: no cover -- defensive; rtree should not raise
            candidates = []
        for cand in candidates:
            if cand == ctx.actor:
                continue
            return cand
        # Fallback: brute-force scan.
        best_id: str | None = None
        best_d2 = math.inf
        for node_id in ctx.find_nodes(subtype=subtype):
            if node_id == ctx.actor:
                continue
            other = _point_from_props(ctx.query_node(node_id))
            if other is None:
                continue
            dx = other[0] - point[0]
            dy = other[1] - point[1]
            d2 = dx * dx + dy * dy
            if d2 < best_d2:
                best_d2 = d2
                best_id = node_id
        return best_id
