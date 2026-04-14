"""MECH-SEED pet: actor pets a nearby animal, improving its mood.

Models a simple social interaction between an agent and an animal entity.
Mood advances through a fixed escalation ladder so repeated petting has
diminishing returns (the animal caps at "purring") — a natural consequence
of the clamp, not a separate cooldown mechanic.

Mood ladder: hostile → wary → neutral → content → purring (clamped at top).

Preconditions (check):
    - Actor exists.
    - At least one entity with ``subtype="animal"`` is in the actor's room.

Side effects (apply):
    - Advances the first matching animal's ``mood`` by one step on the ladder.
    - If the animal has no ``mood`` property, the default is treated as
      ``"neutral"`` and advances to ``"content"``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _current_location

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


# Fixed mood escalation ladder. Clamped at the top ("purring").
_MOOD_LADDER: list[str] = ["hostile", "wary", "neutral", "content", "purring"]
_MOOD_DEFAULT: str = "neutral"


def _next_mood(current: str) -> str:
    """Advance mood one step up the ladder, clamping at the top."""
    try:
        idx = _MOOD_LADDER.index(current)
    except ValueError:
        # Unknown mood — treat as neutral and advance to content.
        idx = _MOOD_LADDER.index(_MOOD_DEFAULT)
    next_idx = min(idx + 1, len(_MOOD_LADDER) - 1)
    return _MOOD_LADDER[next_idx]


def _find_animal_in_room(ctx: MechanicContext, room: str) -> str | None:
    """Return the first animal entity co-located in *room*, or None."""
    for node_id in ctx.find_nodes():
        if node_id == ctx.actor:
            continue
        if room not in ctx.neighbors(node_id, relation="located_in"):
            continue
        props = ctx.query_node(node_id)
        if props.get("subtype") == "animal":
            return node_id
    return None


class PetMechanic(Mechanic):
    """Agent pets a nearby animal; improves its mood.

    Preconditions:
        - Actor exists.
        - At least one entity with ``subtype="animal"`` is in the actor's room.

    Side effects:
        - Writes ``target.mood`` advanced one step up the mood ladder
          (hostile→wary→neutral→content→purring, clamped at purring).
    """

    id = "pet"
    description = "Agent pets a nearby animal; improves its mood."
    voluntary = True
    tags: list[str] = ["social", "animal"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        room = _current_location(ctx, ctx.actor)
        if room is None:
            return CheckResult(passed=False, reasons=["actor has no located_in location"])
        if _find_animal_in_room(ctx, room) is None:
            return CheckResult(passed=False, reasons=["no animal nearby"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        room = _current_location(ctx, ctx.actor)
        if room is None:
            return []
        # Prefer ctx.target if it resolves to an animal in the room.
        target_id: str | None = None
        if ctx.target and ctx.has_node(ctx.target):
            props = ctx.query_node(ctx.target)
            if props.get("subtype") == "animal" and room in ctx.neighbors(
                ctx.target, relation="located_in"
            ):
                target_id = ctx.target
        if target_id is None:
            target_id = _find_animal_in_room(ctx, room)
        if target_id is None:
            return []
        current_mood = ctx.query_node(target_id).get("mood", _MOOD_DEFAULT)
        if not isinstance(current_mood, str):
            current_mood = _MOOD_DEFAULT
        new_mood = _next_mood(current_mood)
        return [ctx.mutate(target_id, "mood", new_mood)]
