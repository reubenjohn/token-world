"""Phase 7 drunk seed mechanic (D-01, D-13, D-16, D-18).

Demonstrates INDEFINITE-duration long-running action via turns_total=None.
The LRA ends only when the companion SoberUpMechanic (sober_up.py) raises
the actor's sobriety_level back above 0.8, at which point the LongRunningHook
(Plan 04) fires the threshold and ends the drunk state.

Single-action-per-agent invariant (D-04): attempting to drink more while
already drunk refuses; v2 multi-LRA support would allow stacking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.matchers import VerbMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext
    from token_world.mechanic.matchers import Matcher


class DrunkMechanic(Mechanic):
    """Actor drinks an alcoholic entity; enters indefinite drunk LRA until sober.

    Preconditions (check):
        - Actor and target exist.
        - Actor holds the target (holds edge).
        - Target has numeric alcohol_content > 0.
        - Actor has no existing current_long_action (D-04 single active).

    Side effects (apply):
        - Decrease actor.sobriety_level by alcohol_content (clamped at 0, default 1.0).
        - Set actor.is_drunk = True.
        - Remove target node (the drink is consumed).
        - Begin indefinite LRA with sobriety_level > 0.8 wake threshold and
          drunk-state attention modulation (D-18 exact).
    """

    id = "drunk"
    description = "Actor drinks alcohol; enters indefinite drunk state until sober"
    voluntary = True
    tags: list[str] = ["social", "consciousness", "long_running"]

    def watches(self) -> list[Matcher]:
        return [VerbMatcher(verb="drink")]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])
        held = set(ctx.neighbors(ctx.actor, relation="holds"))
        if ctx.target not in held:
            return CheckResult(passed=False, reasons=[f"actor does not hold {ctx.target!r}"])
        target_props = ctx.query_node(ctx.target)
        alcohol = target_props.get("alcohol_content")
        if not isinstance(alcohol, int | float) or isinstance(alcohol, bool) or alcohol <= 0:
            return CheckResult(
                passed=False,
                reasons=[f"target {ctx.target!r} has no positive numeric alcohol_content"],
            )
        actor_props = ctx.query_node(ctx.actor)
        if isinstance(actor_props.get("current_long_action"), dict):
            return ctx.refuse(
                "mechanic_check_failed",
                {"reason": "actor is already in a long-running action"},
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        actor_props = ctx.query_node(ctx.actor)
        target_props = ctx.query_node(ctx.target)
        current_sobriety = actor_props.get("sobriety_level", 1.0)
        alcohol = target_props["alcohol_content"]
        new_sobriety_raw = current_sobriety - alcohol
        if new_sobriety_raw < 0.0:
            new_sobriety_raw = 0.0
        # Preserve int-ness when both inputs are int
        if isinstance(current_sobriety, int) and isinstance(alcohol, int):
            new_sobriety: float | int = int(new_sobriety_raw)
        else:
            new_sobriety = float(new_sobriety_raw)

        return [
            ctx.set(ctx.actor, "sobriety_level", new_sobriety),
            ctx.set(ctx.actor, "is_drunk", True),
            ctx.remove_node(ctx.target),
            ctx.begin_long_action(
                action_text="drunk",
                turns_total=None,  # D-16: indefinite
                thresholds=[
                    {"property": f"{ctx.actor}.sobriety_level", "op": ">", "value": 0.8},
                ],
                attention_state={
                    "suppress": ["fine_detail", "social_nuance"],
                    "boost": ["aggression_level"],
                },
            ),
        ]
