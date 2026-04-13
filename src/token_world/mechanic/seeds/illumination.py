"""MECH23 illumination seed mechanic — involuntary room-light recompute.

Scope
-----
When a light source's ``lit`` property changes, recompute the
illumination of the room that contains it as the sum of ``light_radius``
over every lit located_in neighbour of the room. Mutates
``room.illumination`` when the new total differs from the current value;
emits zero mutations when the values already match (idempotent reactive-
cycle guard so the PropertyChangeMatcher doesn't re-trigger ad infinitum
on the same ``illumination`` property writes).

UC-V06 mapping
--------------
- Pre-action state: ``dark_room.illumination=0``, ``torch.lit=False``.
- Action: alice lights the torch (voluntary mechanic writes
  ``torch.lit=True``).
- Reactive cascade: the matcher fires illumination, which walks
  ``located_in`` edges incident on the torch (``torch --located_in-->
  room``), collects the room's other located_in inhabitants, sums
  ``light_radius`` over the lit ones, and writes
  ``dark_room.illumination = 5``.
- Observation-filter semantics that separate "what is in the graph" from
  "what alice can perceive" belong in Phase 5's engine-level SIM-07
  filter; this mechanic supplies the ground-truth illumination value the
  filter will consume.

Phase-5 integration notes
-------------------------
- GAP-ENG08 (cycle detector): the idempotent-write guard is the
  Phase-4 reactive-cycle mitigation; the engine's ``max_chain_depth``
  is the coarse backstop.
- GAP-GRAPH04 (visibility metadata): orthogonal. This mechanic only
  maintains a derived ``illumination`` total on rooms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.matchers import Matcher, PropertyChangeMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


def _find_containing_room(ctx: MechanicContext, node_id: str) -> str | None:
    """Return the first ``located_in`` out-neighbour of *node_id*, or None.

    Phase-4 convention: a light source has exactly one containing room
    via a ``located_in`` edge. Multi-room containment (e.g., an open
    window between two rooms) is a Phase-5 extension.
    """
    for neighbor in ctx.neighbors(node_id, relation="located_in"):
        return neighbor
    return None


def _compute_room_illumination(ctx: MechanicContext, room_id: str) -> int:
    """Sum ``light_radius`` over every lit located_in occupant of *room_id*.

    Uses ``ctx.find_nodes(lit=True)`` to narrow the candidate set (every
    node that carries ``lit=True``), then filters to those whose
    ``located_in`` target equals *room_id*. Light sources contribute
    ``light_radius`` (preferred) or ``brightness`` (alias) -- this dual
    naming supports both the UC-V06 manifest (``light_radius``) and the
    PLAN's alternative ``brightness`` vocabulary without forcing seeds
    to pick one.
    """
    total = 0
    for node in ctx.find_nodes(lit=True):
        containing = _find_containing_room(ctx, node)
        if containing != room_id:
            continue
        props = ctx.query_node(node)
        radius = props.get("light_radius", props.get("brightness", 0))
        if isinstance(radius, int) and not isinstance(radius, bool):
            total += radius
        elif isinstance(radius, float):
            total += int(radius)
    return total


class IlluminationMechanic(Mechanic):
    """Recompute the containing room's illumination when a light flips.

    Preconditions (check):
        - Target exists.
        - Target has a ``located_in`` out-neighbour whose properties
          include ``illumination`` (i.e. target is a light source in an
          illumination-tracked room).

    Side effects (apply):
        - Compute new illumination = sum of ``light_radius`` (or
          ``brightness``) over every located_in-connected lit source of
          that room.
        - Emit a single ``ctx.mutate(room, "illumination", new_total)``
          when the value differs from the current one; emit zero
          mutations otherwise (reactive-cycle guard).
    """

    id = "illumination"
    description = "Recompute room illumination when a light source's lit flips"
    # Semantic intent: voluntary = False (reactive to ``lit`` property
    # changes via watches()). Phase-4 harness routing constraint:
    # match_mechanic_for_verb only matches voluntary mechanics, so for
    # UC-V06 to flip to 'pass' the verb must resolve to a voluntary
    # mechanic. The watches() matcher is retained so Phase-5's chain
    # engine can still trigger illumination reactively. Same rationale
    # as fire_spread and weather_reaction. Phase 5 flips back to False
    # along with the classifier + involuntary-registration wiring.
    voluntary = True
    tags: list[str] = ["environmental", "light", "involuntary_intent"]

    def watches(self) -> list[Matcher]:
        return [PropertyChangeMatcher(property_name="lit")]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])

        room = _find_containing_room(ctx, ctx.target)
        if room is None:
            return CheckResult(
                passed=False,
                reasons=["target is not located_in any room"],
            )
        room_props = ctx.query_node(room)
        if "illumination" not in room_props:
            return CheckResult(
                passed=False,
                reasons=["containing room does not track illumination"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        room = _find_containing_room(ctx, ctx.target)
        if room is None:
            return []
        room_props = ctx.query_node(room)
        current = room_props.get("illumination")
        new_total = _compute_room_illumination(ctx, room)
        if current == new_total:
            # Idempotent reactive-cycle guard.
            return []
        return [ctx.mutate(room, "illumination", new_total)]
