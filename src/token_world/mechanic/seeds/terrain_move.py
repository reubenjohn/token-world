"""MECH05 terrain_move seed: agent moves across terrain, consuming stamina.

The mechanic reads a per-terrain movement-cost multiplier (UC-V05 style,
``movement_cost_multiplier`` on the destination node) or falls back to a
built-in category table keyed by ``terrain_type``. The cost is the
multiplier (rounded) and is subtracted from the actor's ``stamina``
property.

Accepted edge kinds between source and destination: ``connects`` OR
``adjacent_to`` (UC-V05 uses the latter; UC-S06 uses the former). This
covers both the "same room, different tile" and "adjacent areas" idioms
without forcing authors to normalize relation names.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _current_location

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


# Default movement cost per terrain_type. Authors can override by setting an
# explicit ``movement_cost_multiplier`` on the destination entity — that wins.
_DEFAULT_TERRAIN_COSTS: dict[str, float] = {
    "floor": 1.0,
    "grass": 1.0,
    "path": 1.0,
    "bridge": 1.0,
    "stair": 2.0,
    "mud": 3.0,
    "sand": 3.0,
    "swamp": 2.0,
    "water": 5.0,
    "wall": 99.0,  # effectively impassable
}

# Multipliers at or above this threshold are treated as impassable terrain
# regardless of actor stamina. Keeps "a wall" from being bypassable by a
# high-stamina character.
_IMPASSABLE_THRESHOLD: float = 50.0


def _terrain_cost(props: dict) -> float | None:
    """Compute the movement cost for stepping onto a terrain-typed node.

    Preference order:
    1. Explicit ``movement_cost_multiplier`` prop on the node.
    2. ``_DEFAULT_TERRAIN_COSTS`` lookup by ``terrain_type``.
    3. ``None`` when no terrain signal is present — caller fails ``check``.
    """
    if "movement_cost_multiplier" in props:
        try:
            return float(props["movement_cost_multiplier"])
        except (TypeError, ValueError):
            return None
    terrain = props.get("terrain_type")
    if isinstance(terrain, str) and terrain in _DEFAULT_TERRAIN_COSTS:
        return _DEFAULT_TERRAIN_COSTS[terrain]
    return None


class TerrainMoveMechanic(Mechanic):
    """Agent moves across terrain; destination's multiplier drains stamina.

    Preconditions:
        - Actor exists and carries a numeric ``stamina`` property.
        - Target exists. Either the source OR the target exposes a terrain
          signal (``movement_cost_multiplier`` directly, or ``terrain_type``
          in the default table). When both are present, the higher cost wins
          (you pay for the heaviest terrain you touch on the step).
        - Actor is located in some source, and an edge
          ``source → target`` exists with relation ``connects`` or
          ``adjacent_to``.
        - Computed cost is below the impassable threshold and
          ``actor.stamina >= cost``.

    Side effects:
        - Decrement ``actor.stamina`` by the computed cost (integer math —
          costs round via ``int(round(cost))`` so the UC-V05 assertion
          ``stamina == 18`` lands exactly: swamp multiplier 2.0 → cost 2 →
          20 - 2 = 18).
        - Remove old ``located_in`` edge.
        - Add new ``located_in`` edge to target.
        - Mirror ``location`` property on actor.
    """

    id = "terrain_move"
    description = "Agent moves across terrain with stamina cost from multiplier"
    voluntary = True
    tags: list[str] = ["spatial", "terrain"]

    # Edge relations accepted as "adjacency" for a terrain step.
    _ADJACENT_RELATIONS: tuple[str, ...] = ("connects", "adjacent_to")

    def check(self, ctx: "MechanicContext") -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])
        actor_props = ctx.query_node(ctx.actor)
        stamina = actor_props.get("stamina")
        if not isinstance(stamina, (int, float)):
            return CheckResult(
                passed=False,
                reasons=["actor missing stamina property"],
            )
        src = _current_location(ctx, ctx.actor)
        if src is None:
            return CheckResult(
                passed=False,
                reasons=["actor has no located_in location"],
            )
        if not self._adjacent(ctx, src, ctx.target):
            return CheckResult(
                passed=False,
                reasons=[f"no adjacency from {src} to {ctx.target}"],
            )
        cost = self._effective_cost(ctx, src, ctx.target)
        if cost is None:
            return CheckResult(
                passed=False,
                reasons=["neither source nor target has terrain info (terrain_type or movement_cost_multiplier)"],
            )
        if cost >= _IMPASSABLE_THRESHOLD:
            return CheckResult(
                passed=False,
                reasons=[f"terrain is impassable (cost={cost})"],
            )
        rounded = int(round(cost))
        if stamina < rounded:
            return CheckResult(
                passed=False,
                reasons=[
                    f"insufficient stamina (need {rounded}, have {stamina})"
                ],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: "MechanicContext") -> list[Mutation]:
        src = _current_location(ctx, ctx.actor)
        cost = self._effective_cost(ctx, src, ctx.target) or 0.0
        rounded = int(round(cost))
        stamina_before = ctx.query_node(ctx.actor).get("stamina", 0)
        muts: list[Mutation] = []
        muts.append(ctx.set(ctx.actor, "stamina", stamina_before - rounded))
        if src is not None:
            muts.append(ctx.remove_edge(ctx.actor, src))
        muts.append(ctx.add_edge(ctx.actor, ctx.target, relation="located_in"))
        muts.append(ctx.set(ctx.actor, "location", ctx.target))
        return muts

    def _adjacent(self, ctx: "MechanicContext", src: str, dst: str) -> bool:
        """True iff an edge ``src → dst`` exists with an accepted relation."""
        for rel in self._ADJACENT_RELATIONS:
            if dst in set(ctx.neighbors(src, relation=rel)):
                return True
        return False

    def _effective_cost(
        self,
        ctx: "MechanicContext",
        src: str | None,
        dst: str,
    ) -> float | None:
        """Compute the cost paid to step from *src* to *dst*.

        Takes the max of the two nodes' terrain costs (the heaviest terrain
        the actor touches on this step). Returns ``None`` iff neither node
        carries a terrain signal.
        """
        costs: list[float] = []
        if src is not None and ctx.has_node(src):
            sc = _terrain_cost(ctx.query_node(src))
            if sc is not None:
                costs.append(sc)
        if ctx.has_node(dst):
            dc = _terrain_cost(ctx.query_node(dst))
            if dc is not None:
                costs.append(dc)
        if not costs:
            return None
        return max(costs)
