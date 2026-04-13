"""MECH08 give seed: one-sided transfer of an item OR a scalar property.

Handles both shapes surfaced by the Phase-3 use-case library:

    - Item form (UC-O03): alice holds a sword and hands it to bob.
      Emits ``remove_edge(alice, sword, holds)`` + ``add_edge(bob, sword, holds)``.
    - Scalar form (UC-R03): alice has 10 coin and gives bob 5.
      Emits ``set(alice, "coin", 5)`` + ``set(bob, "coin", 5)``.

Phase-4 workaround for GAP-ENG02 (no indirect_object slot in
MechanicContext)
---------------------------------------------------------------
The DSL does not yet carry a third argument for the recipient or the
amount. The harness only routes ``actor`` and ``target``. Until
GAP-ENG02 is closed, the canonical form is:

    actor.pending_give = {"item": <node_id>, "recipient": <node_id>}
        OR
    actor.pending_give = {"property": <str>, "amount": <num>,
                          "recipient": <node_id>}

The use-case graph_builder populates ``pending_give`` directly; the
mechanic reads it, performs the transfer, then clears it.
``ctx.target`` is ignored by the mechanic (the harness fills it with
either the item or the recipient depending on how the manifest
author classified the verb; both point into ``pending_give``).

When GAP-ENG02 lands, swap the three ``pending_give`` reads for
``ctx.indirect_object`` / ``ctx.amount`` without changing the
public shape of the mechanic.

Design decisions
----------------
- **Scalars default to 0 on the recipient.** UC-R03 pre-initialises
  ``bob.coin = 0``; we still default to 0 if absent so that first-
  time receivers work.
- **Scalar amount must be ≤ actor's current value.** Going negative
  would violate conservation (UC-R03's implicit invariant); we
  refuse with a narrative instead.
- **Item form requires an outgoing ``holds`` edge.** Refuses
  otherwise with a narrative on the actor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _refuse_with_narrative

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


_NARRATIVE_NO_PENDING: str = "no pending give"
_NARRATIVE_NOT_HELD: str = "actor does not hold the item"
_NARRATIVE_INSUFFICIENT: str = "insufficient amount to give"
_NARRATIVE_RECIPIENT_MISSING: str = "recipient does not exist"


class GiveMechanic(Mechanic):
    """One-sided transfer of an item or a scalar property.

    Preconditions (check):
        - Actor exists.
        - Actor has ``pending_give`` dict with either
          (``item``, ``recipient``) or
          (``property``, ``amount``, ``recipient``).

    Side effects (apply):
        - Item form: holds edge moves actor→recipient.
        - Scalar form: property decrements on actor, increments on
          recipient.
        - ``pending_give`` is cleared on the actor after transfer.
    """

    id = "give"
    description = "Actor hands an item or transfers a scalar property to a recipient"
    voluntary = True
    tags: list[str] = ["social", "transfer"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        pending = ctx.query_node(ctx.actor).get("pending_give")
        if not isinstance(pending, dict):
            return CheckResult(
                passed=False, reasons=["actor has no pending_give dict"]
            )
        recipient = pending.get("recipient")
        if not isinstance(recipient, str) or not recipient:
            return CheckResult(
                passed=False, reasons=["pending_give missing recipient"]
            )
        has_item = isinstance(pending.get("item"), str) and pending["item"]
        has_scalar = (
            isinstance(pending.get("property"), str)
            and pending["property"]
            and isinstance(pending.get("amount"), (int, float))
        )
        if not (has_item or has_scalar):
            return CheckResult(
                passed=False,
                reasons=["pending_give missing item or (property, amount)"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        pending = ctx.query_node(ctx.actor).get("pending_give") or {}
        recipient = pending.get("recipient")
        if not isinstance(recipient, str) or not ctx.has_node(recipient):
            return _refuse_with_narrative(ctx, ctx.actor, _NARRATIVE_RECIPIENT_MISSING)

        if isinstance(pending.get("item"), str) and pending["item"]:
            return self._apply_item(ctx, pending["item"], recipient)
        # Scalar form
        prop = pending["property"]
        amount = pending["amount"]
        return self._apply_scalar(ctx, prop, amount, recipient)

    def _apply_item(
        self, ctx: MechanicContext, item: str, recipient: str
    ) -> list[Mutation]:
        held = set(ctx.neighbors(ctx.actor, relation="holds"))
        if item not in held:
            return _refuse_with_narrative(ctx, ctx.actor, _NARRATIVE_NOT_HELD)
        return [
            ctx.remove_edge(ctx.actor, item),
            ctx.add_edge(recipient, item, relation="holds"),
            ctx.set(ctx.actor, "pending_give", None),
        ]

    def _apply_scalar(
        self,
        ctx: MechanicContext,
        prop: str,
        amount: float,
        recipient: str,
    ) -> list[Mutation]:
        actor_props = ctx.query_node(ctx.actor)
        recipient_props = ctx.query_node(recipient)
        current = actor_props.get(prop, 0)
        if not isinstance(current, (int, float)) or current < amount:
            return _refuse_with_narrative(ctx, ctx.actor, _NARRATIVE_INSUFFICIENT)
        recipient_current = recipient_props.get(prop, 0)
        if not isinstance(recipient_current, (int, float)):
            recipient_current = 0
        new_actor = current - amount
        new_recipient = recipient_current + amount
        # Preserve int-ness end-to-end when the inputs are all integral.
        if (
            isinstance(current, int)
            and isinstance(recipient_current, int)
            and isinstance(amount, int)
        ):
            new_actor = int(new_actor)
            new_recipient = int(new_recipient)
        return [
            ctx.set(ctx.actor, prop, new_actor),
            ctx.set(recipient, prop, new_recipient),
            ctx.set(ctx.actor, "pending_give", None),
        ]
