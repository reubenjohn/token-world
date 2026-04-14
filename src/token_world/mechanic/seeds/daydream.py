"""Phase 7 daydream seed mechanic (D-01, D-13, D-18).

Demonstrates the composable long-running action pattern for the BOUNDED
COGNITIVE case — a short cognitive drift interrupted by sensory or health
pressure. Authored as a regular Mechanic using ctx.begin_long_action; the
engine's LongRunningHook (Plan 04) advances turns_elapsed, evaluates
thresholds, and synthesises interruption / completion narratives.

This is the FOURTH seed in the composability family:
  - sleep: bounded physiological (turns_total=8)
  - daydream: bounded cognitive (turns_total=4)
  - autopilot_travel: bounded movement (turns_total=path_len)
  - drunk: indefinite chemical (turns_total=None)

Together they prove that one infrastructure handles four distinct state
categories with only data-level variation in each mechanic.

Daydream specification:
  - turns_total: 4 (shorter than sleep's 8; distinguishes from drunk's None)
  - thresholds: {noise_level > 0.4 on current room, health < 0.2 on actor}
  - attention_state: suppress [ambient_sound, peripheral_vision]; boost [noise_level]

Location fallback policy (identical to sleep.py's Q8 graceful-degradation):
  If the actor has no location property, or the location value is not a string,
  or the referenced room node does not exist in the graph, the noise_level
  threshold is omitted. Only the health threshold is written. The mechanic does
  NOT crash — graceful degradation is preferred over strict enforcement, since
  agents without a resolvable room may still drift into a daydream.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.matchers import VerbMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext
    from token_world.mechanic.matchers import Matcher


class DaydreamMechanic(Mechanic):
    """Agent drifts into daydreaming for 4 ticks; snaps out on loud noise or health crisis.

    Preconditions (check):
        - Actor exists.
        - Actor has no current_long_action already set (D-04 single active per agent).

    Side effects (apply):
        - Set actor.is_daydreaming = True.
        - Start a 4-tick long-running action with:
          * noise threshold on current room (if resolvable; see fallback policy)
          * health threshold on actor
          * attention_state suppressing ambient_sound/peripheral_vision, boosting noise_level
    """

    id = "daydream"
    description = (
        "Agent drifts into daydreaming for 4 ticks; snaps out on loud noise or health crisis"
    )
    voluntary = True
    tags: list[str] = ["cognitive", "long_running"]

    def watches(self) -> list[Matcher]:
        return [VerbMatcher(verb="daydream")]

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
        """Return mutations to start the daydream LRA.

        Thresholds:
          1. health < 0.2 on actor (always present)
          2. {room_id}.noise_level > 0.4 (present only if a resolvable room exists)

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
                {"property": f"{location_id}.noise_level", "op": ">", "value": 0.4},
            )

        return [
            ctx.set(ctx.actor, "is_daydreaming", True),
            ctx.begin_long_action(
                action_text="daydreaming",
                turns_total=4,
                thresholds=thresholds,
                attention_state={
                    "suppress": ["ambient_sound", "peripheral_vision"],
                    "boost": ["noise_level"],
                },
                clear_on_end={"is_daydreaming": False},
            ),
        ]
