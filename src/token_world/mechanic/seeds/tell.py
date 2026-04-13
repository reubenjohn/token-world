"""MECH10 tell seed: actor writes a belief into the recipient's belief store.

Phase-4 scope and non-scope
---------------------------
``tell`` is a pure write into ``recipient.beliefs``. It does NOT compare
the asserted value against ground truth (that's the partner GAP-GRAPH04
"belief vs. truth lattice" landing in Phase 5). A lie and a true
statement therefore look identical at the mechanic layer; the
distinguishing semantics live in the observation/credibility pipeline,
which is out of Phase-4 scope.

DSL workaround for GAP-ENG02
----------------------------
There is no third positional slot on :class:`MechanicContext` for the
asserted claim. Per the 04-08 ``pending_*`` convention, the actor
carries the claim on its own ``utterance`` property:

    actor.utterance = {
        "about":    <node_id_or_string>,    # subject of the claim
        "property": <str>,                  # property being asserted
        "value":    <json>,                 # asserted value
    }

The mechanic reads the dict, performs the read-modify-write on
``recipient.beliefs[about][property]``, and leaves ``utterance`` in
place (callers may clear it after the tick). When GAP-ENG02 lands,
the three reads swap for a structured ``ctx.claim`` slot without
changing the public mechanic shape.

UC-O04 mapping
--------------
alice's pre-staged ``utterance`` asserts ``chest.contents = []``. The
mechanic writes ``bob.beliefs["chest"]["contents"] = []``. The chest's
real ``contents`` (``["coin:100"]``) is never read or written --
ground truth survives the lie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


_REQUIRED_UTTERANCE_KEYS: frozenset[str] = frozenset({"about", "property", "value"})


class TellMechanic(Mechanic):
    """Agent tells another agent a claim about a third entity.

    Preconditions (check):
        - Actor and recipient (``ctx.target``) both exist.
        - Actor carries an ``utterance`` dict with the keys ``about``,
          ``property``, and ``value`` (GAP-ENG02 workaround).

    Side effects (apply):
        - Read-modify-write on ``recipient.beliefs[about][property] =
          value``. Existing keys for other ``about`` subjects are
          preserved.
    """

    id = "tell"
    description = "Agent writes a belief about a third entity into the recipient's beliefs dict"
    voluntary = True
    tags: list[str] = ["social", "belief", "speech"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["recipient does not exist"])
        utterance = ctx.query_node(ctx.actor).get("utterance")
        if not isinstance(utterance, dict):
            return CheckResult(
                passed=False,
                reasons=["actor has no utterance dict (GAP-ENG02 workaround)"],
            )
        if not _REQUIRED_UTTERANCE_KEYS <= set(utterance.keys()):
            missing = sorted(_REQUIRED_UTTERANCE_KEYS - set(utterance.keys()))
            return CheckResult(
                passed=False,
                reasons=[f"utterance missing required keys: {missing}"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        utterance = ctx.query_node(ctx.actor)["utterance"]
        about = utterance["about"]
        prop = utterance["property"]
        value = utterance["value"]

        beliefs_raw = ctx.query_node(ctx.target).get("beliefs")
        beliefs = dict(beliefs_raw) if isinstance(beliefs_raw, dict) else {}
        claim_raw = beliefs.get(about)
        claim = dict(claim_raw) if isinstance(claim_raw, dict) else {}
        claim[prop] = value
        beliefs[about] = claim
        return [ctx.mutate(ctx.target, "beliefs", beliefs)]
