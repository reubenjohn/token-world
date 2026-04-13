"""MECH07 trade seed: atomic single-tick two-party swap of held items.

Scope
-----
Phase 4 ships ONLY the single-tick atomic swap. The multi-turn
offer/accept protocol described in UC-O01's vignette (alice proposes
at tick N; bob accepts at tick N+1) is ``GAP-ENG01`` and lives in
Phase 5 -- it requires the classifier to resolve ``accept`` against
the most-recent open offer, which is engine machinery, not a
mechanic.

For Phase 4 the use-case graph_builder pre-stages the agreement on
both parties and the mechanic performs the swap in one tick.

Convention
----------
Two complementary dicts on the actors:

    actor.pending_trade  = {"offer_item": X, "demand_item": Y,
                            "counterparty": <other_actor_id>}
    other.pending_trade  = {"offer_item": Y, "demand_item": X,
                            "counterparty": <actor_id>}

The mechanic verifies that both parties' ``offer_item``/``demand_item``
mirror each other, then swaps the ``holds`` edges atomically. Any
asymmetry (e.g. bob wants a shield but alice offers a sword) is a
refusal with narrative.

Dispatch
--------
``ctx.target`` is the counterparty node id. The harness routes
``verb=trade`` with ``target=<counterparty>`` per the Phase-4
convention. We do NOT reach for ``indirect_object`` (GAP-ENG02).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _refuse_with_narrative

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


_NARRATIVE_NO_OFFER: str = "no pending trade offer"
_NARRATIVE_ASYMMETRIC: str = "trade offers are asymmetric"
_NARRATIVE_NOT_HELD: str = "required item not held"
_NARRATIVE_COUNTERPARTY_MISSING: str = "counterparty does not exist"


class TradeMechanic(Mechanic):
    """Atomic two-party item swap.

    Preconditions (check):
        - Actor exists.
        - Counterparty (``ctx.target``) exists.
        - Both parties have complementary ``pending_trade`` dicts.

    Side effects (apply):
        - Four edge mutations: actor drops offer_item, counterparty
          gains it; counterparty drops demand_item, actor gains it.
        - Both ``pending_trade`` dicts cleared.

    Refusal:
        - Asymmetric offers / missing items: narrative on actor;
          graph unchanged.
    """

    id = "trade"
    description = "Two actors swap held items atomically in a single tick"
    voluntary = True
    tags: list[str] = ["social", "trade"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["counterparty (target) does not exist"])
        if ctx.actor == ctx.target:
            return CheckResult(passed=False, reasons=["actor and counterparty are the same agent"])
        actor_pending = ctx.query_node(ctx.actor).get("pending_trade")
        if not isinstance(actor_pending, dict):
            return CheckResult(passed=False, reasons=["actor has no pending_trade dict"])
        counter_pending = ctx.query_node(ctx.target).get("pending_trade")
        if not isinstance(counter_pending, dict):
            return CheckResult(passed=False, reasons=["counterparty has no pending_trade dict"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        actor_pending = ctx.query_node(ctx.actor).get("pending_trade") or {}
        counter_pending = ctx.query_node(ctx.target).get("pending_trade") or {}

        offer_item = actor_pending.get("offer_item")
        demand_item = actor_pending.get("demand_item")
        counter_offer = counter_pending.get("offer_item")
        counter_demand = counter_pending.get("demand_item")

        # The two offers must mirror: each party's "offer" is the other's "demand".
        if not (
            isinstance(offer_item, str)
            and isinstance(demand_item, str)
            and offer_item == counter_demand
            and demand_item == counter_offer
        ):
            return _refuse_with_narrative(ctx, ctx.actor, _NARRATIVE_ASYMMETRIC, target=ctx.target)

        actor_holds = set(ctx.neighbors(ctx.actor, relation="holds"))
        counter_holds = set(ctx.neighbors(ctx.target, relation="holds"))
        if offer_item not in actor_holds or demand_item not in counter_holds:
            return _refuse_with_narrative(ctx, ctx.actor, _NARRATIVE_NOT_HELD, target=ctx.target)

        # Atomic swap: drop both edges, re-add in mirrored directions.
        return [
            ctx.remove_edge(ctx.actor, offer_item),
            ctx.remove_edge(ctx.target, demand_item),
            ctx.add_edge(ctx.target, offer_item, relation="holds"),
            ctx.add_edge(ctx.actor, demand_item, relation="holds"),
            ctx.set(ctx.actor, "pending_trade", None),
            ctx.set(ctx.target, "pending_trade", None),
        ]
