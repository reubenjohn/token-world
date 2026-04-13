"""Phase 7 autopilot_advance passive mechanic (D-01, D-18, Q4 option a).

Companion to autopilot_travel.py. Fires once per passive sweep tick
(TickMatcher; involuntary) and advances any traveling agent's location
one hop along its stored route. Location mutation triggers the projector
to show the NEW current room on the next hook tick, which drives hazard
threshold evaluation against the right room.

Separation of concerns (D-01 composability):
- LongRunningHook (Plan 04): advances turns_elapsed, evaluates thresholds,
  emits observations.
- AutopilotAdvanceMechanic (this file): advances actor.location one hop.
- AutopilotTravelMechanic (autopilot_travel.py): starts the LRA, sets up
  the route + thresholds.

Each piece knows nothing about the others. The graph is the shared state.

Passive sweep and hook ordering (Pitfall 6 from Phase 7 research):
The engine runs LongRunningHook BEFORE the passive sweep. So on each
continuation tick:
  1. Hook evaluates thresholds at actor's CURRENT location (the room the
     actor was already in).
  2. Passive sweep fires this mechanic → actor advances ONE hop.

This means alice "perceives" each room BEFORE moving on — hazard_level in
room_b is evaluated on the tick alice ARRIVES there (which is the tick
after she moved from room_a), not on the prior tick.
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.matchers import TickMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext
    from token_world.mechanic.matchers import Matcher


def _find_traveling_actors(ctx: MechanicContext) -> list[tuple[str, dict]]:
    """Return [(actor_id, lra_dict)] for every agent currently autopilot-traveling
    with an unfinished route.

    An actor qualifies when:
    - node type is "agent"
    - current_long_action is a dict
    - action_text starts with "traveling"
    - payload contains a list 'route' and int 'next_index'
    - next_index < len(route)  (route not yet exhausted)
    """
    out: list[tuple[str, dict]] = []
    for node_id in ctx.find_nodes():
        try:
            props = ctx.query_node(node_id)
        except KeyError:
            continue
        if props.get("type") != "agent":
            continue
        lra = props.get("current_long_action")
        if not isinstance(lra, dict):
            continue
        if not lra.get("action_text", "").startswith("traveling"):
            continue
        payload = lra.get("payload")
        if not isinstance(payload, dict):
            continue
        route = payload.get("route")
        next_index = payload.get("next_index", 0)
        if not isinstance(route, list) or not isinstance(next_index, int):
            continue
        if next_index >= len(route):
            continue
        out.append((node_id, lra))
    return out


class AutopilotAdvanceMechanic(Mechanic):
    """Passive per-tick mechanic that advances autopilot-traveling agents by one hop.

    Preconditions (check):
        At least one agent in the graph has a 'traveling' LRA with an unfinished route.
        The check iterates graph.nodes() because the passive sweep invokes this mechanic
        against a sentinel actor — the mechanic must find its real targets internally
        (same pattern as DecayMatcher / weather_reaction).

    Side effects (apply):
        For each qualifying agent: set actor.location = route[next_index]; increment
        next_index in the stored LRA dict. Does NOT clear the LRA or evaluate thresholds
        — both are the LongRunningHook's responsibility.
    """

    id = "autopilot_advance"
    description = "Passive: advance each autopilot-traveling agent's location one hop per tick"
    voluntary = False
    tags: list[str] = ["spatial", "long_running", "passive"]

    def watches(self) -> list[Matcher]:
        return [TickMatcher()]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if _find_traveling_actors(ctx):
            return CheckResult(passed=True)
        return CheckResult(passed=False, reasons=["no actors currently autopilot-traveling"])

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        """Advance each traveling agent one hop.

        For each agent with an unfinished traveling LRA:
        1. Set actor.location = route[next_index] (location property)
        2. Move the actor's type=location edge to the new room so the
           VisibilityProjector includes the new room in its projection.
           This is required for threshold evaluation: thresholds reference
           "room_id.hazard_level", which is only evaluable when the room
           is in the projection (D-09; projector follows type=location edge).
           The previous room is route[next_index - 1] (known from the route;
           no need to scan neighbors). Edge removal is best-effort — if the
           edge was never added or was already removed, we continue silently.
        3. Write back the LRA with next_index incremented by 1

        When next_index >= len(route) the agent is silently skipped (the hook's
        turns_total completion fires on the same or next tick).
        """
        mutations: list[Mutation] = []
        for actor_id, lra in _find_traveling_actors(ctx):
            payload = dict(lra.get("payload", {}))
            route = list(payload.get("route", []))
            next_index = int(payload.get("next_index", 0))
            if next_index <= 0:
                # IN-03: next_index=0 indicates a corrupt or manually-crafted LRA payload.
                # autopilot_travel always initialises next_index=1, so 0 is invalid.
                logger.warning(
                    "autopilot_advance: next_index=0 for actor %s; skipping "
                    "(likely corrupt LRA payload)",
                    actor_id,
                )
                continue
            if next_index >= len(route):
                continue
            new_room = route[next_index]
            prev_room = route[next_index - 1] if next_index > 0 else None

            # 1. Update location property
            mutations.append(ctx.set(actor_id, "location", new_room))

            # 2. Move type=location edge: remove old, add new.
            # prev_room is known from the route — no need to scan all neighbors.
            if prev_room is not None and ctx.has_edge(actor_id, prev_room):
                with contextlib.suppress(Exception):
                    mutations.append(ctx.remove_edge(actor_id, prev_room))
            mutations.append(ctx.add_edge(actor_id, new_room, type="location"))

            # 3. Increment next_index in payload
            payload["next_index"] = next_index + 1
            updated_lra = dict(lra)
            updated_lra["payload"] = payload
            mutations.append(ctx.set(actor_id, "current_long_action", updated_lra))
        return mutations
