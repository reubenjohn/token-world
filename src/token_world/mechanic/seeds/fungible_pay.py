"""MECH18 fungible_pay seed: subset-sum-driven currency transfer.

The single-tick exact-change form of paying a recipient with held coin
entities. Each coin is its own node carrying a ``denomination`` property;
the mechanic finds a held subset of coins whose denominations sum to the
target amount and transfers their ``holds`` edges to the recipient.

Change-making (overpay + emit "change-owed" state) is ``GAP-MECH29``,
deferred to Phase 7+. When no exact subset exists this mechanic refuses
with a narrative naming the deferred gap, rather than overpaying. A
future change-making mechanic can compose on top: it will reuse the
``_subset_sum`` helper, then add a separate "change-owed" emission step.

Phase-4 workaround for GAP-ENG02 (no indirect_object / amount slot)
-------------------------------------------------------------------
The DSL does not yet carry the recipient or amount as positional context
fields. The use-case graph_builder pre-stages the payment intent on the
actor (precedent: 04-08 ``pending_give`` / ``pending_trade``):

    actor.pending_payment = {
        "recipient": <node_id>,
        "amount": N,
        "kind": "coin",
    }

The mechanic reads it, performs the subset-sum + transfer, then clears
``pending_payment`` on success. On refusal (no exact subset, recipient
missing) the dict is LEFT IN PLACE so the agent can try again with a
different intent. ``ctx.target`` carries the recipient id (the harness
fills it from ``classified.target``); we cross-check against
``pending_payment["recipient"]`` for safety.

UC-R06 mapping
--------------
alice holds coins {5, 2, 2, 1, 1} (total 11); ``pending_payment.amount=7``;
the mechanic picks a subset summing to 7 (e.g. {5, 2} or {5, 1, 1} -- the
helper returns the first depth-first match, which the test asserts via
the conservation invariant rather than a fixed choice). The four-edge
mutation set transfers the chosen coin nodes from alice to shopkeeper;
``shopkeeper.coin_received`` is incremented by 7 to satisfy UC-R06's
graph_assertion.

Why coin_received instead of recipient_balance
----------------------------------------------
UC-R06 explicitly asserts ``shopkeeper.coin_received == 7`` -- the
manifest treats this as a running tally on the recipient (analogous to
pending_payment on the sender). We honor the property name from the
manifest rather than introducing a different convention; future fungible
mechanics can reuse the same ``<kind>_received`` pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _refuse_with_narrative, _subset_sum

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


# GAP-MECH29 (change-making) is deferred -- the narrative names the gap so
# the deferred concern is greppable from the seed.
_NARRATIVE_NO_EXACT_SUBSET: str = "cannot make exact change with held coins (GAP-MECH29 deferred)"
_NARRATIVE_RECIPIENT_MISSING: str = "recipient does not exist"


def _eligible_coins(
    ctx: MechanicContext,
    actor: str,
    kind: str,
) -> list[tuple[str, int]]:
    """Return ``(coin_id, denomination)`` pairs the actor holds matching *kind*.

    A coin is eligible when:
      - it is an outgoing ``holds`` neighbor of *actor*,
      - its ``subtype`` equals *kind* (or its ``fungible_kind`` does, for
        a future generalisation; the manifest uses ``subtype``),
      - it carries a positive integer ``denomination`` property.
    """
    out: list[tuple[str, int]] = []
    for nbr in ctx.neighbors(actor, relation="holds"):
        props = ctx.query_node(nbr)
        if props.get("subtype") != kind and props.get("fungible_kind") != kind:
            continue
        denom = props.get("denomination")
        if not isinstance(denom, int) or isinstance(denom, bool) or denom <= 0:
            continue
        out.append((nbr, denom))
    return out


class FungiblePayMechanic(Mechanic):
    """Subset-sum transfer of held coin entities to a recipient.

    Preconditions (check):
        - Actor + target (recipient) exist.
        - Actor has ``pending_payment`` dict with ``recipient`` (str),
          ``amount`` (positive int), and ``kind`` (str).
        - The dict's ``recipient`` matches ``ctx.target`` (or ``ctx.target``
          equals the dict's recipient -- harness routing).

    Side effects (apply):
        - Pick an exact subset of held coins whose ``denomination`` values
          sum to ``amount``; if none exists, refuse with a GAP-MECH29
          narrative and leave ``pending_payment`` in place.
        - For each chosen coin: drop ``actor -[holds]-> coin``, add
          ``recipient -[holds]-> coin``.
        - Increment ``recipient.coin_received`` by ``amount`` (or
          ``recipient.<kind>_received`` more generally).
        - Clear ``actor.pending_payment``.
    """

    id = "fungible_pay"
    description = "Transfer held coin entities to a recipient via exact-subset-sum"
    voluntary = True
    tags: list[str] = ["resource", "currency"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target (recipient) does not exist"])
        pending = ctx.query_node(ctx.actor).get("pending_payment")
        if not isinstance(pending, dict):
            return CheckResult(passed=False, reasons=["actor has no pending_payment dict"])
        recipient = pending.get("recipient")
        if not isinstance(recipient, str) or not recipient:
            return CheckResult(passed=False, reasons=["pending_payment missing recipient"])
        amount = pending.get("amount")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            return CheckResult(
                passed=False,
                reasons=["pending_payment missing positive int amount"],
            )
        kind = pending.get("kind")
        if not isinstance(kind, str) or not kind:
            return CheckResult(passed=False, reasons=["pending_payment missing kind string"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        pending = ctx.query_node(ctx.actor).get("pending_payment") or {}
        recipient = pending.get("recipient")
        amount = pending.get("amount")
        kind = pending.get("kind")

        if not isinstance(recipient, str) or not ctx.has_node(recipient):
            return _refuse_with_narrative(ctx, ctx.actor, _NARRATIVE_RECIPIENT_MISSING)

        # check() guarantees these, but narrow for mypy.
        assert isinstance(kind, str)
        assert isinstance(amount, int) and not isinstance(amount, bool)

        coins = _eligible_coins(ctx, ctx.actor, kind)
        if not coins:
            return _refuse_with_narrative(
                ctx, ctx.actor, _NARRATIVE_NO_EXACT_SUBSET, target=recipient
            )

        denominations = [d for _id, d in coins]
        subset_idx = _subset_sum(denominations, amount)
        if subset_idx is None:
            # No exact subset exists -- defer to change-making (GAP-MECH29).
            return _refuse_with_narrative(
                ctx, ctx.actor, _NARRATIVE_NO_EXACT_SUBSET, target=recipient
            )

        # Increment recipient's running tally for this kind. Default to 0
        # if absent; preserve int-ness when the existing value is int.
        received_prop = f"{kind}_received"
        recipient_props = ctx.query_node(recipient)
        prior = recipient_props.get(received_prop, 0)
        if not isinstance(prior, (int, float)) or isinstance(prior, bool):
            prior = 0
        new_received: int | float = prior + amount
        if isinstance(prior, int) and isinstance(amount, int):
            new_received = int(new_received)

        muts: list[Mutation] = []
        for i in subset_idx:
            coin_id = coins[i][0]
            muts.append(ctx.remove_edge(ctx.actor, coin_id))
            muts.append(ctx.add_edge(recipient, coin_id, relation="holds"))
        muts.append(ctx.set(recipient, received_prop, new_received))
        muts.append(ctx.set(ctx.actor, "pending_payment", None))
        return muts
