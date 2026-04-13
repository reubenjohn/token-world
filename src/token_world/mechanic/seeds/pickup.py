"""MECH16 pickup seed: actor attempts to add a holds edge to target, bounded by inventory_cap.

Three outcomes:

    1. Actor has room (``_count_holds(actor) < inventory_cap``) and
       target exists: emit ``actor -[holds]-> target``.
    2. Actor is at capacity: emit a refusal narrative on the actor
       (``last_refusal_narrative = "inventory is full"``) and leave
       every edge unchanged. This satisfies UC-R04's assertion chain
       (item_10 stays in the storeroom; alice.inventory_cap remains 10;
       no new holds edge).
    3. Actor is already holding the target: refuse with narrative
       ("already holding it") so double-pickup is a no-op.

Rationale for the capacity-branch placement
-------------------------------------------
The capacity check lives in ``apply``, not ``check``. That is
deliberate:

    - ``check`` returns ``passed=True`` whenever the action is
      *coherent* (actor exists, target exists, target is reachable).
      "Bag is full" is coherent — the agent can still think about
      picking up — so it is not a check-time failure.
    - ``apply`` owns the refusal-narrative path because the Phase-4
      harness does not yet synthesize narratives from
      ``CheckResult.reasons`` (that is a 04-04 Extension Contract
      concern). Authors who need a grounded "why not" on the actor
      must write it in ``apply``.

This matches the pattern 04-07's ``try_door`` established (UC-E06's
"door is locked" narrative is written in ``apply`` after
``check`` passes on "target is a door").

UC-R04 mapping
--------------
alice holds 10 items; ``inventory_cap=10``; item_10 is on the
storeroom floor. ``_count_holds(alice) == 10``, so
``apply`` writes ``last_refusal_narrative = "inventory is full"``
and ``last_refusal_target = "item_10"`` on alice. No new holds
edge. UC-R04's ``expected_observations`` chain passes:

    - ``not_has_edge(alice, item_10, "holds")`` ✓ (never added)
    - ``has_edge(item_10, storeroom, "located_in")`` ✓ (unchanged)
    - ``property_equals(alice.inventory_cap, 10)`` ✓ (unchanged)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _count_holds, _refuse_with_narrative

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


_NARRATIVE_FULL: str = "inventory is full"
_NARRATIVE_ALREADY_HELD: str = "already holding it"


class PickupMechanic(Mechanic):
    """Agent picks up an entity; refuses if inventory is at capacity.

    Preconditions (check):
        - Actor exists.
        - Target exists.
        - Actor declares an integer ``inventory_cap`` property.

    Side effects (apply):
        - Under capacity: one ``holds`` edge added from actor to target.
        - At capacity: refusal narrative on actor; no edge change.
        - Already holding: refusal narrative on actor; no edge change.
    """

    id = "pickup"
    description = "Agent picks up an entity into its inventory, bounded by inventory_cap"
    voluntary = True
    tags: list[str] = ["object_interaction", "inventory"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])
        actor_props = ctx.query_node(ctx.actor)
        cap = actor_props.get("inventory_cap")
        if not isinstance(cap, int):
            return CheckResult(
                passed=False,
                reasons=["actor has no integer inventory_cap property"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        # Already holding the target -> no-op refusal.
        if ctx.has_edge(ctx.actor, ctx.target):
            held = set(ctx.neighbors(ctx.actor, relation="holds"))
            if ctx.target in held:
                return _refuse_with_narrative(
                    ctx, ctx.actor, _NARRATIVE_ALREADY_HELD, target=ctx.target
                )
        cap = int(ctx.query_node(ctx.actor).get("inventory_cap", 0))
        if _count_holds(ctx, ctx.actor) >= cap:
            return _refuse_with_narrative(ctx, ctx.actor, _NARRATIVE_FULL, target=ctx.target)
        return [ctx.add_edge(ctx.actor, ctx.target, relation="holds")]
