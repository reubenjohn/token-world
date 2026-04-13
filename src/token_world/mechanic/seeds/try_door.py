"""MECH27 try_door seed: inspect a door; unlock it if the actor holds a key.

Three outcomes:

    1. Door is unlocked (``locked != True``). No mutation — the door is
       already openable; a subsequent ``passage_move`` would succeed.
    2. Door is locked AND the actor holds an entity whose ``key_id``
       matches the door's ``required_key_id``. Mutation:
       ``door.locked = False``. A future ``passage_move`` can now cross.
    3. Door is locked AND no matching key. No unlock mutation — instead
       the mechanic writes ``actor.last_refusal_narrative`` = "the door
       is locked" and ``actor.last_refusal_target`` = target id. This
       establishes the "refusal narrative" pattern that 04-08 MECH16
       ``use_object`` and similar refused-interaction mechanics will
       reuse (authoring-guide §9 pattern).

UC-E06 maps to (3): alice meets a locked door with no key, stays in
room_a, door stays locked, stamina unchanged. The assertion chain is
satisfied because try_door emits only the refusal-narrative mutation on
the actor — not the door or location edges.

Shares ``_find_matching_key`` with ``_helpers.py`` so follow-on mechanics
(pick_lock, try_chest) can reuse the holds-walk. Shares
``_find_open_passage`` (also in ``_helpers.py``) conceptually — try_door
is the "what if the passage is closed?" dual of passage_move's "is it
open?" — but doesn't call it directly because the target here IS the
door itself, not the adjacency shape passage_move scans.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _find_matching_key

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


# Door subtypes this mechanic understands. Extend freely as authors add
# related subtypes (gate, portcullis, hatch) — the behaviour is identical.
_DOOR_SUBTYPES: frozenset[str] = frozenset({"door", "doorway", "gate"})

_REFUSAL_NARRATIVE_LOCKED: str = "the door is locked"


class TryDoorMechanic(Mechanic):
    """Agent interacts with a door; may unlock if a matching key is held.

    Preconditions:
        - Actor exists.
        - Target exists and is a door-like entity (``subtype`` in
          ``_DOOR_SUBTYPES``).

    Side effects:
        - Unlocked door: no mutation.
        - Locked door + matching key: ``target.locked = False``.
        - Locked door + no matching key: write refusal narrative on
          actor (``last_refusal_narrative`` + ``last_refusal_target``).
    """

    id = "try_door"
    description = "Agent inspects a door; unlocks it if holding a matching key"
    voluntary = True
    tags: list[str] = ["spatial", "interaction", "passage"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])
        target_props = ctx.query_node(ctx.target)
        subtype = target_props.get("subtype")
        if subtype not in _DOOR_SUBTYPES:
            return CheckResult(
                passed=False,
                reasons=[
                    f"target subtype {subtype!r} is not door-like "
                    f"(expected one of {sorted(_DOOR_SUBTYPES)})"
                ],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        target_props = ctx.query_node(ctx.target)
        locked = bool(target_props.get("locked", False))
        if not locked:
            # Door is already openable — nothing to do.
            return []
        required_key_id = target_props.get("required_key_id")
        if isinstance(required_key_id, str) and required_key_id:
            matched_key = _find_matching_key(ctx, ctx.actor, required_key_id)
            if matched_key is not None:
                # Unlock the door.
                return [ctx.mutate(ctx.target, "locked", False)]
        # Locked, no matching key — refuse with narrative. No mutation on
        # door or location edges. This keeps UC-E06's assertion chain
        # green (door stays locked, alice stays in room_a, stamina
        # unchanged).
        return [
            ctx.mutate(ctx.actor, "last_refusal_narrative", _REFUSAL_NARRATIVE_LOCKED),
            ctx.mutate(ctx.actor, "last_refusal_target", ctx.target),
        ]
