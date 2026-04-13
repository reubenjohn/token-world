"""MECH22 decay_tick seed mechanic — voluntary Phase-4 decay wrapper.

Scope
-----
A voluntary mechanic that advances a single decay step on a target. When
the target's ``decay_progress`` reaches ``decay_period``, the target is
marked ``rotten=True`` and ``freshness="rotten"``. Defaults
``decay_progress`` to 0 when the property is absent so a freshly-placed
food item can be tick-driven without manifest scaffolding.

Phase-5 integration notes (GAP-ENG07)
-------------------------------------
This is a Phase-4 *wrapper*: the intended semantics ("decay once per
simulation tick, for every eligible node, with no agent action") require
a passive-tick sweep which is GAP-ENG07 (Phase 5). Until that ships, the
use-case harness stages explicit ``decay_tick`` invocations in its
actions list so UC-V03 can exercise the apply semantics today. When
GAP-ENG07 lands, the mechanic is unchanged -- the engine invokes it
automatically on each tick for every node with ``decay_period``, and
the manifest's explicit invocation retires.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class DecayTickMechanic(Mechanic):
    """Advance target's decay_progress by one; flip rotten=True at threshold.

    Preconditions (check):
        - Target exists.
        - Target has an integer ``decay_period`` property.
        - Target is not already ``rotten=True``.

    Side effects (apply):
        - Increment ``decay_progress`` by 1 (treating absent as 0).
        - If the new progress >= ``decay_period``: set ``rotten=True``
          and ``freshness="rotten"``.
    """

    id = "decay_tick"
    description = "Advance one decay step; flip rotten=True when progress >= period"
    voluntary = True
    tags: list[str] = ["environmental", "decay"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])

        props = ctx.query_node(ctx.target)
        period = props.get("decay_period")
        # Strict int (reject bool per the 04-10 pattern in degrade/fungible_pay).
        if not isinstance(period, int) or isinstance(period, bool) or period <= 0:
            return CheckResult(
                passed=False,
                reasons=["target has no positive integer decay_period"],
            )
        if props.get("rotten"):
            return CheckResult(passed=False, reasons=["target is already rotten"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        props = ctx.query_node(ctx.target)
        period = int(props["decay_period"])
        progress_raw = props.get("decay_progress", 0)
        # Defensive: non-int progress defaults to 0.
        if not isinstance(progress_raw, int) or isinstance(progress_raw, bool):
            progress_raw = 0
        new_progress = int(progress_raw) + 1

        mutations: list[Mutation] = [
            ctx.mutate(ctx.target, "decay_progress", new_progress)
        ]
        if new_progress >= period:
            mutations.append(ctx.mutate(ctx.target, "rotten", True))
            mutations.append(ctx.mutate(ctx.target, "freshness", "rotten"))
        return mutations
