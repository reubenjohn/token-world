"""MECH01 passage_move seed: agent moves through a passage entity or a direct connects edge.

Covers three use-case shapes:

    - ``src --connects--> passage --connects--> dst`` where ``passage`` is a
      doorway / passage / bridge entity with ``open=True`` (doorways) or
      ``traversable=True`` (bridges). This is the UC-S01 / UC-S06 pattern.
    - ``src --connects--> dst`` directly (no intermediate entity). This is the
      UC-S07 pattern.
    - Fails with a concrete reason when no viable path exists.

``apply()`` mutates both the ``located_in`` edge (remove old, add new) AND the
actor's ``location`` property. The property mirror keeps UC-S07's
``property_equals alice.location == 'room_b'`` assertion satisfiable without
a separate mechanic, and also preserves backwards-compatibility with the
original ``movement`` seed that only wrote the property.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _current_location, _find_open_passage

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class PassageMoveMechanic(Mechanic):
    """Agent moves from its current location to a connected location.

    Preconditions:
        - Actor node exists.
        - Target node exists.
        - Actor has a ``located_in`` edge to some source location.
        - Either ``src --connects--> target`` exists directly, OR an open
          passage entity ``P`` mediates the hop (see
          :func:`token_world.mechanic.seeds._helpers._find_open_passage`).

    Side effects:
        - Removes actor's ``located_in`` edge to the old source.
        - Adds actor's ``located_in`` edge to the target.
        - Sets actor's ``location`` property to the target id (mirror of the
          edge for convenience / backwards compatibility with the first
          ``movement`` seed).
    """

    id = "passage_move"
    description = "Agent moves through an open passage or directly-connected location"
    voluntary = True
    tags: list[str] = ["spatial", "passage"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])
        src = _current_location(ctx, ctx.actor)
        if src is None:
            return CheckResult(
                passed=False,
                reasons=["actor has no located_in location"],
            )
        if src == ctx.target:
            return CheckResult(passed=False, reasons=["already at target"])
        # Accept either a direct connects edge or an open passage.
        direct = ctx.target in set(ctx.neighbors(src, relation="connects"))
        passage = _find_open_passage(ctx, src, ctx.target)
        if not direct and passage is None:
            return CheckResult(
                passed=False,
                reasons=[f"no open passage from {src} to {ctx.target}"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        src = _current_location(ctx, ctx.actor)
        muts: list[Mutation] = []
        if src is not None:
            muts.append(ctx.remove_edge(ctx.actor, src))
        muts.append(ctx.add_edge(ctx.actor, ctx.target, relation="located_in"))
        # Mirror the edge into a scalar property so UCs that assert on
        # ``property_equals alice.location == 'room_b'`` stay green.
        muts.append(ctx.set(ctx.actor, "location", ctx.target))
        return muts
