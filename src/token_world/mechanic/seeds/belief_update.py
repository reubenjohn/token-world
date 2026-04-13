"""MECH25 belief_update seed: write actor's belief about a target's observable state.

Phase-4 scope and Phase-5 successor
-----------------------------------
``belief_update`` is the manual hook for the belief-on-failed-precondition
pattern that Phase 5's GAP-ENG19 passive-tick sweep will eventually
fire automatically. For Phase 4 it is a *voluntary* mechanic — a
manifest can stage it directly, and the harness will invoke it the
same way it invokes any other voluntary mechanic.

Mechanic shape
--------------
Reads the target's currently observable properties (the subset
declared in :data:`_OBSERVABLE_PROPS`) and writes them into
``actor.beliefs[target_id]``. Existing beliefs about other targets are
preserved; the asserted target's prior belief dict (if any) is fully
replaced — Phase 4's "reveal" semantics are coarse-grained.

Why a fixed observable set?
---------------------------
Without GAP-GRAPH04 (per-property visibility metadata), the framework
cannot distinguish "publicly observable" from "private internal" props.
The hard-coded :data:`_OBSERVABLE_PROPS` set captures the canonical
observable surfaces touched by Phase-3 use cases (locked, color,
state, position, subtype, contents). Phase 5 will replace this with
graph-driven visibility once GAP-GRAPH04 lands.

UC-E03 mapping
--------------
chest carries ``locked=True``. After alice's failed open attempt
(modelled as a manifest invocation of ``belief_update`` against
``chest``), the mechanic writes ``alice.beliefs["chest"] =
{"locked": True}``. Ground truth is unchanged; no opened edge is
added; alice's other beliefs are preserved.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


# Properties considered "observable on inspection" for Phase 4. When
# GAP-GRAPH04 lands, this constant retires in favour of per-node
# visibility metadata.
_OBSERVABLE_PROPS: frozenset[str] = frozenset(
    {
        "locked",
        "color",
        "state",
        "position",
        "subtype",
        "contents",
        "open",
        "broken",
        "lit",
    }
)


class BeliefUpdateMechanic(Mechanic):
    """Actor records observable properties of *target* into its belief store.

    Preconditions (check):
        - Actor and target both exist.

    Side effects (apply):
        - Read-modify-write on ``actor.beliefs[target] = {prop: value
          for prop in _OBSERVABLE_PROPS if prop in target_props}``.
          Beliefs about other targets are preserved. Ground truth is
          never read or written — this is purely an actor-side
          memory write.
    """

    id = "belief_update"
    description = "Actor records observable properties of target into actor.beliefs"
    voluntary = True
    tags: list[str] = ["belief", "epistemic", "introspection"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        target_props = ctx.query_node(ctx.target)
        observed = {prop: target_props[prop] for prop in _OBSERVABLE_PROPS if prop in target_props}

        beliefs_raw = ctx.query_node(ctx.actor).get("beliefs")
        beliefs = dict(beliefs_raw) if isinstance(beliefs_raw, dict) else {}
        beliefs[ctx.target] = observed
        return [ctx.mutate(ctx.actor, "beliefs", beliefs)]
