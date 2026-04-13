"""Phase 7 sleep seed mechanic (D-01, D-13, D-18).

Demonstrates the composable long-running action pattern by authoring sleep
as a regular Mechanic. The mechanic itself is tiny: start the LRA via
ctx.begin_long_action and let the engine's LongRunningHook (Plan 04) handle
turns_elapsed advancement, threshold evaluation, and interruption narrative
synthesis.

D-18 specification:
  - turns_total: 8
  - thresholds: {noise_level > 0.7 on current room, health < 0.2 on actor}
  - attention_state: suppress [visual_detail, smell]; boost [noise_level]

Location fallback policy (Q8):
  If the actor has no location property, or the location value is not a string,
  or the referenced room node does not exist in the graph, the noise_level
  threshold is omitted. Only the health threshold is written. The mechanic does
  NOT crash — graceful degradation is preferred over strict enforcement, since
  agents without a room may still need rest.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.matchers import VerbMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext
    from token_world.mechanic.matchers import Matcher


class SleepMechanic(Mechanic):
    """Agent sleeps for 8 ticks; wakes on loud noise or health crisis.

    Preconditions (check):
        - Actor exists.
        - Actor has no current_long_action already set (D-04 single active per agent).

    Side effects (apply):
        - Set actor.is_sleeping = True.
        - Start an 8-tick long-running action with:
          * noise threshold on current room (if resolvable; see fallback policy)
          * health threshold on actor
          * attention_state suppressing visual_detail/smell, boosting noise_level
    """

    id = "sleep"
    description = "Agent sleeps for 8 ticks; wakes on loud noise or health crisis"
    voluntary = True
    tags: list[str] = ["rest", "long_running"]

    def watches(self) -> list[Matcher]:
        return [VerbMatcher(verb="sleep")]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        actor_props = ctx.query_node(ctx.actor)
        existing_lra = actor_props.get("current_long_action")
        if isinstance(existing_lra, dict):
            return ctx.refuse(
                "mechanic_check_failed",
                {"reason": "actor is already in a long-running action"},
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        """Return mutations to start the sleep LRA.

        Thresholds:
          1. health < 0.2 on actor (always present)
          2. {room_id}.noise_level > 0.7 (present only if a resolvable room exists)

        If the actor has no location property, location is not a string, or the
        referenced room node is absent from the graph, the noise threshold is
        omitted (graceful degradation — mechanic does not crash; see module docstring).
        """
        actor_props = ctx.query_node(ctx.actor)
        thresholds: list[dict] = [
            {"property": f"{ctx.actor}.health", "op": "<", "value": 0.2},
        ]
        location_id = actor_props.get("location")
        if isinstance(location_id, str) and ctx.has_node(location_id):
            thresholds.insert(
                0,
                {"property": f"{location_id}.noise_level", "op": ">", "value": 0.7},
            )

        return [
            ctx.set(ctx.actor, "is_sleeping", True),
            ctx.begin_long_action(
                action_text="sleeping",
                turns_total=8,
                thresholds=thresholds,
                attention_state={
                    "suppress": ["visual_detail", "smell"],
                    "boost": ["noise_level"],
                },
            ),
        ]
