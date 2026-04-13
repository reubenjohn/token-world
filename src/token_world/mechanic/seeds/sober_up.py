"""Phase 7 sober_up passive mechanic (D-01, D-18).

Companion to drunk.py. Fires once per passive-sweep tick via TickMatcher
(involuntary). Raises the sobriety_level of every drunk actor by a fixed
recovery rate. When sobriety crosses the 0.8 threshold declared by
DrunkMechanic's LRA, the LongRunningHook (Plan 04) fires the threshold
and ends the drunk state on the NEXT continuation tick.

Separation of concerns (D-01 composability):
- LongRunningHook: owns LRA lifecycle (advance turns_elapsed, evaluate thresholds, clear LRA).
- SoberUpMechanic: owns sobriety_level recovery each tick.
- DrunkMechanic: owns initial state and LRA start.

Each piece is independent; graph state is the shared channel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.matchers import TickMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext
    from token_world.mechanic.matchers import Matcher


RECOVERY_RATE = 0.1  # sobriety increase per tick for drunk actors


def _find_drunk_actors_with_room_to_recover(ctx: MechanicContext) -> list[tuple[str, float]]:
    """Return [(actor_id, current_sobriety)] for every drunk actor with sobriety < 1.0."""
    out: list[tuple[str, float]] = []
    for node_id in ctx.find_nodes():
        try:
            props = ctx.query_node(node_id)
        except KeyError:
            continue
        if props.get("type") != "agent":
            continue
        if not props.get("is_drunk"):
            continue
        sobriety = props.get("sobriety_level", 0.0)
        if not isinstance(sobriety, int | float) or isinstance(sobriety, bool):
            sobriety = 0.0
        sobriety = float(sobriety)
        if sobriety >= 1.0:
            continue
        out.append((node_id, sobriety))
    return out


class SoberUpMechanic(Mechanic):
    """Passive per-tick mechanic that recovers sobriety for drunk actors."""

    id = "sober_up"
    description = "Passive: increase sobriety_level by RECOVERY_RATE for each drunk actor"
    voluntary = False
    tags: list[str] = ["social", "consciousness", "passive"]

    def watches(self) -> list[Matcher]:
        return [TickMatcher()]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if _find_drunk_actors_with_room_to_recover(ctx):
            return CheckResult(passed=True)
        return CheckResult(passed=False, reasons=["no drunk actors with room to recover"])

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        mutations: list[Mutation] = []
        for actor_id, current_sobriety in _find_drunk_actors_with_room_to_recover(ctx):
            new_sobriety = min(1.0, current_sobriety + RECOVERY_RATE)
            mutations.append(ctx.set(actor_id, "sobriety_level", new_sobriety))
        return mutations
