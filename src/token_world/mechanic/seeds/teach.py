"""MECH11 teach seed: actor copies a known skill to a co-located agent.

Phase-4 scope and DSL routing
-----------------------------
The Phase-3 manifest UC-O05 classifies the teach action as
``verb=teach, target=lockpicking, indirect_object=bob``. The
integration harness picks ``target or indirect_object``, so
``ctx.target`` arrives as the bare *skill name string*
(``"lockpicking"``). UC-O05 explicitly opts into this with
``validator_exception: target_may_not_exist``.

The recipient is therefore not in ``ctx.target``. Per the same
co-location convention used by ``trade`` and ``give``, ``teach``
locates the recipient by walking the actor's ``located_in`` neighbour
and finding the OTHER co-located agent. UC-O05 has exactly one such
agent (bob) — when there is more than one, the mechanic refuses with a
narrative rather than guess (a classroom scenario is out of Phase-4
scope; deferred to GAP-ENG02 / Phase 5).

UC-O05 mapping
--------------
alice.knows_skill=["lockpicking"], bob.knows_skill=[], both in
workshop. ``check`` passes (skill known, co-located bob exists,
bob doesn't already know it). ``apply`` appends "lockpicking" to
bob.knows_skill. alice.knows_skill is unchanged — teaching is a copy,
not a transfer.

GAP-ENG04 (skill-as-node) is deferred to Phase 5 — Phase 4 leaves
skill names as bare strings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import (
    _current_location,
    _refuse_with_narrative,
)

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


_NARRATIVE_AMBIGUOUS_RECIPIENT: str = (
    "ambiguous recipient: more than one co-located agent (Phase 5 GAP-ENG02)"
)


def _find_sole_recipient(ctx: MechanicContext) -> tuple[str | None, list[str]]:
    """Return (recipient_id, all_candidates) for the actor's co-located agents.

    A *candidate* is any agent (other than the actor) sharing the
    actor's ``located_in`` room. When there is exactly one candidate
    it is returned as the recipient. Otherwise recipient is ``None``
    and the caller decides whether to refuse (>1) or fail check (0).
    """
    room = _current_location(ctx, ctx.actor)
    if room is None:
        return None, []
    candidates: list[str] = []
    for node_id in ctx.find_nodes(type="agent"):
        if node_id == ctx.actor:
            continue
        if room in ctx.neighbors(node_id, relation="located_in"):
            candidates.append(node_id)
    if len(candidates) == 1:
        return candidates[0], candidates
    return None, candidates


class TeachMechanic(Mechanic):
    """Agent teaches a known skill to a co-located recipient.

    Preconditions (check):
        - Actor exists.
        - Actor has a ``located_in`` room (scope for "co-located").
        - Actor's ``knows_skill`` list contains ``ctx.target``.
        - Exactly one other agent shares the actor's room.
        - That recipient does not already know the skill.

    Side effects (apply):
        - Append ``ctx.target`` to ``recipient.knows_skill``. The
          actor's own ``knows_skill`` is unchanged (teaching is a
          copy, not a transfer).
        - When more than one recipient is co-located: emit a
          refusal narrative on the actor.
    """

    id = "teach"
    description = "Agent copies a skill to a co-located recipient (Phase 4 single-recipient)"
    voluntary = True
    tags: list[str] = ["social", "skill", "knowledge"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        room = _current_location(ctx, ctx.actor)
        if room is None:
            return CheckResult(
                passed=False,
                reasons=["actor has no located_in room (no co-location scope)"],
            )

        skill = ctx.target
        if not isinstance(skill, str) or not skill:
            return CheckResult(
                passed=False,
                reasons=["target skill must be a non-empty string"],
            )
        actor_skills = ctx.query_node(ctx.actor).get("knows_skill") or []
        if skill not in actor_skills:
            return CheckResult(
                passed=False,
                reasons=[f"actor does not know skill {skill!r}"],
            )

        recipient, candidates = _find_sole_recipient(ctx)
        if not candidates:
            return CheckResult(
                passed=False,
                reasons=["no co-located recipient agent"],
            )
        if recipient is None:
            # Ambiguous (>1 candidate) — coherent action, refusal lives
            # in apply via _refuse_with_narrative.
            return CheckResult(passed=True)

        recipient_skills = ctx.query_node(recipient).get("knows_skill") or []
        if skill in recipient_skills:
            return CheckResult(
                passed=False,
                reasons=[f"recipient {recipient!r} already knows {skill!r}"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        recipient, candidates = _find_sole_recipient(ctx)
        if recipient is None:
            return _refuse_with_narrative(
                ctx,
                ctx.actor,
                _NARRATIVE_AMBIGUOUS_RECIPIENT,
            )
        skill = ctx.target
        existing = ctx.query_node(recipient).get("knows_skill") or []
        if not isinstance(existing, list):
            existing = []
        if skill in existing:
            # Defensive: check should have prevented this; behave as
            # idempotent no-op rather than duplicate the entry.
            return []
        new_skills = [*existing, skill]
        return [ctx.mutate(recipient, "knows_skill", new_skills)]
