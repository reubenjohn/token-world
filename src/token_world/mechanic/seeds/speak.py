"""MECH13 speak seed: utterance propagates to agents in earshot.

The mechanic writes the utterance to ``last_heard`` on every agent the
speaker can reach acoustically. Reach is modelled conservatively:

    - Listeners must share the speaker's ``located_in`` room (fast room
      filter — walls between rooms act as natural occluders).
    - Listeners must additionally be within ``earshot_radius`` Euclidean
      of the speaker's ``position`` when both carry a 2D point.

This composition handles UC-O08 exactly: alice shouts in room_a; bob
(same room, 5 units away) hears; charlie (room_b, 30 units, wall between)
does not. Walls with ``blocks_sound=True`` are modelled by cross-room
separation — the room-membership filter already excludes them by
construction. A future LOS-aware ``speak`` can read ``blocks_sound``
directly once GAP-GRAPH02 is closed.

Utterance source: ``ctx.target`` is expected to carry an ``utterance``
property (the speaker leaves the words on the target placeholder), or
the speaker themselves carries ``last_utterance``. This is a soft
convention — the mechanic falls through to ``"<no utterance>"`` if
neither is set, so the broadcast side effect still runs for UC
assertions that only check receiver-side state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _current_location

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


# Default earshot for a normal speaking voice. Authors can override by
# setting ``earshot_radius`` on the speaker (agent.earshot_radius).
_DEFAULT_EARSHOT_RADIUS: float = 15.0


def _point_from_props(props: dict) -> tuple[float, float] | None:
    position = props.get("position")
    if isinstance(position, list) and len(position) == 2:
        try:
            return float(position[0]), float(position[1])
        except (TypeError, ValueError):
            return None
    return None


def _extract_utterance(ctx: MechanicContext) -> str:
    """Pull the utterance from target or actor, with a graceful fallback."""
    # Prefer the target slot (speak "X" at Y — Y.utterance carries the words).
    if ctx.has_node(ctx.target):
        target_utter = ctx.query_node(ctx.target).get("utterance")
        if isinstance(target_utter, str) and target_utter:
            return target_utter
    actor_utter = ctx.query_node(ctx.actor).get("last_utterance")
    if isinstance(actor_utter, str) and actor_utter:
        return actor_utter
    return "<no utterance>"


class SpeakMechanic(Mechanic):
    """Agent utters speech; nearby agents record it as ``last_heard``.

    Preconditions:
        - Actor exists.
        - Actor has a ``located_in`` room (scope for the broadcast).

    Side effects:
        - For every other agent sharing the actor's room and within
          ``earshot_radius`` (Euclidean over ``position`` when both
          points are present — when either side is unpositioned, the
          room-membership filter alone qualifies them), emit one
          ``set_property`` mutation setting ``last_heard`` to a list
          with the utterance appended. This is a read-modify-write
          pattern since properties are immutable JSON values.
    """

    id = "speak"
    description = "Agent speaks; nearby agents in earshot record the utterance"
    voluntary = True
    tags: list[str] = ["social", "speech", "spatial"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if _current_location(ctx, ctx.actor) is None:
            return CheckResult(
                passed=False,
                reasons=["actor has no located_in room for broadcast scope"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        room = _current_location(ctx, ctx.actor)
        if room is None:
            return []
        utterance = _extract_utterance(ctx)
        actor_props = ctx.query_node(ctx.actor)
        speaker_point = _point_from_props(actor_props)
        earshot = actor_props.get("earshot_radius", _DEFAULT_EARSHOT_RADIUS)
        try:
            earshot = float(earshot)
        except (TypeError, ValueError):
            earshot = _DEFAULT_EARSHOT_RADIUS

        muts: list[Mutation] = []
        # Find candidate listeners by walking the room's located_in
        # in-neighbors (everyone in the same room).
        for node_id in ctx.find_nodes(type="agent"):
            if node_id == ctx.actor:
                continue
            # Must share the room.
            if room not in ctx.neighbors(node_id, relation="located_in"):
                continue
            # If both speaker and listener carry a position, enforce the
            # Euclidean earshot filter. When either side is unpositioned,
            # shared room is sufficient.
            if speaker_point is not None:
                listener_point = _point_from_props(ctx.query_node(node_id))
                if listener_point is not None:
                    dx = listener_point[0] - speaker_point[0]
                    dy = listener_point[1] - speaker_point[1]
                    if dx * dx + dy * dy > earshot * earshot:
                        continue
            # Append the utterance to the listener's last_heard list
            # (JSON-safe read-modify-write).
            existing = ctx.query_node(node_id).get("last_heard", [])
            if not isinstance(existing, list):
                existing = []
            new_heard = [*existing, utterance]
            muts.append(ctx.mutate(node_id, "last_heard", new_heard))
        return muts
