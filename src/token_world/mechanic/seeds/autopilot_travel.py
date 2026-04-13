"""Phase 7 autopilot_travel seed mechanic (D-01, D-13, D-18).

Demonstrates long-running action for spatial multi-tick traversal. The
mechanic computes a path via BFS, starts a bounded LRA with route stored
in payload + hazard thresholds on each room in the route, and sets
is_traveling=True. The companion AutopilotAdvanceMechanic (seeds/
autopilot_advance.py) fires each passive-sweep tick to advance the
actor's location one hop along the stored route. The LongRunningHook
(Plan 04) handles time advancement + hazard threshold evaluation.

Authoring pattern note: ctx.begin_long_action does not expose an
extra_payload parameter, so this mechanic uses a 2-step 'begin then
augment' — begin_long_action first, then ctx.set to merge route +
next_index into the stored dict. This keeps Plan 03's helper API minimal.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.matchers import VerbMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext
    from token_world.mechanic.matchers import Matcher

_MAX_BFS_DEPTH = 32


def _find_path(
    ctx: MechanicContext,
    start: str,
    end: str,
    max_depth: int = _MAX_BFS_DEPTH,
) -> list[str] | None:
    """BFS over ctx.neighbors (uses graph's existing adjacency).

    Returns a list including both start and end when reachable within max_depth;
    otherwise None. Uses queue-based BFS to ensure shortest path in edge-count.

    Args:
        ctx: The mechanic context providing graph access via ctx.neighbors/ctx.has_node.
        start: Starting node ID.
        end: Target node ID.
        max_depth: Maximum path length (number of nodes, not edges). Paths requiring
            more than max_depth nodes return None to avoid traversal of very large graphs.

    Returns:
        List of node IDs from start to end inclusive, or None if unreachable.
    """
    if not ctx.has_node(start) or not ctx.has_node(end):
        return None
    if start == end:
        return [start]
    visited: set[str] = {start}
    queue: deque[tuple[str, list[str]]] = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        if len(path) >= max_depth:
            continue
        for nbr in ctx.neighbors(node):
            if nbr in visited:
                continue
            new_path = path + [nbr]
            if nbr == end:
                return new_path
            visited.add(nbr)
            queue.append((nbr, new_path))
    return None


class AutopilotTravelMechanic(Mechanic):
    """Agent autopilot-travels to a target node along the shortest path.

    Preconditions (check):
        - Actor exists.
        - Target exists.
        - Target is not the actor's current location (no travel needed).
        - Actor has no current_long_action already set (D-04 single active per agent).
        - A path exists from actor's current location to target (BFS, depth cap=32).

    Side effects (apply):
        - Set actor.is_traveling = True.
        - Start a bounded LRA with turns_total=len(path)-1 and:
          * hazard_level threshold on each room in the route
          * attention_state suppressing fine_detail, boosting hazard_level (D-18)
        - Augment stored LRA dict with route list and next_index=1 via 2-step pattern
          (begin_long_action then ctx.set; see module docstring).
    """

    id = "autopilot_travel"
    description = "Agent travels to a distant node via autopilot; interrupted by hazards"
    voluntary = True
    tags: list[str] = ["spatial", "long_running"]

    def watches(self) -> list[Matcher]:
        return [VerbMatcher(verb="travel")]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])

        actor_props = ctx.query_node(ctx.actor)
        current_location = actor_props.get("location")

        # Target is current location — no travel needed
        if current_location == ctx.target:
            return CheckResult(
                passed=False, reasons=["target is current location; no travel needed"]
            )

        # Already in an LRA (D-04: single active per agent)
        if isinstance(actor_props.get("current_long_action"), dict):
            return ctx.refuse(
                "mechanic_check_failed",
                {"reason": "actor is already in a long-running action"},
            )

        # Actor has no resolvable location
        if not isinstance(current_location, str) or not ctx.has_node(current_location):
            return CheckResult(passed=False, reasons=["actor has no resolvable current location"])

        # Check path exists
        path = _find_path(ctx, current_location, ctx.target)
        if path is None or len(path) < 2:
            return CheckResult(
                passed=False,
                reasons=[f"no path from {current_location} to {ctx.target}"],
            )

        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        """Return mutations to start the autopilot-travel LRA.

        Uses the 2-step 'begin then augment' pattern:
        1. ctx.begin_long_action writes the initial LRA dict (action_text, turns_total,
           turns_elapsed, thresholds, payload with attention_state).
        2. ctx.set augments the stored dict with route and next_index keys in payload,
           keeping Plan 03's begin_long_action helper API minimal.

        The 3 returned mutations are:
          [0] set(actor, 'is_traveling', True)
          [1] begin_long_action(...) — writes current_long_action
          [2] set(actor, 'current_long_action', <augmented dict>) — adds route/next_index
        """
        actor_props = ctx.query_node(ctx.actor)
        current_location = actor_props["location"]
        path = _find_path(ctx, current_location, ctx.target)
        # check() guarantees path is valid and len >= 2
        assert path is not None and len(path) >= 2

        # One hazard threshold per room in the route (D-18; see module docstring)
        thresholds = [
            {"property": f"{room}.hazard_level", "op": ">", "value": 0.5} for room in path
        ]

        mutations: list[Mutation] = [
            ctx.set(ctx.actor, "is_traveling", True),
            ctx.begin_long_action(
                action_text=f"traveling to {ctx.target}",
                turns_total=len(path) - 1,
                thresholds=thresholds,
                attention_state={
                    "suppress": ["fine_detail"],
                    "boost": ["hazard_level"],
                },
            ),
        ]

        # 2-step augment: merge route + next_index into the stored LRA payload.
        # begin_long_action already wrote the dict; we read it back, enrich,
        # and write again. This stays within ALLOWED_PROPERTY_TYPES (list, dict, int).
        stored = ctx.query_node(ctx.actor, "current_long_action")
        augmented = dict(stored)
        augmented_payload = dict(augmented.get("payload", {}))
        augmented_payload["route"] = list(path)
        augmented_payload["next_index"] = 1
        augmented["payload"] = augmented_payload
        mutations.append(ctx.set(ctx.actor, "current_long_action", augmented))

        return mutations
