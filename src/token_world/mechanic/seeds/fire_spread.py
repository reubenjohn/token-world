"""MECH20 fire_spread seed mechanic — involuntary single-hop fire propagation.

Scope
-----
Fire spreads one hop per tick: when a burning node's ``on_fire`` or
``temperature`` property changes and it has flammable neighbours that
are NOT already on fire, each eligible neighbour catches. The
:class:`ChainExecutionEngine` drives the multi-hop cascade because each
mutation to a neighbour's ``on_fire`` property re-triggers the same
matcher on the next tier. The mechanic's check refuses when every
flammable neighbour is already on fire -- that is the reactive-cycle
guard required by T-04-CYCLE in the PLAN's threat_model (single-hop
apply + the check guard together bound the engine's cascade).

UC-V01 mapping
--------------
The torch's ``on_fire=True`` state in UC-V01's graph_builder is the
priming event. When the harness invokes the voluntary ignite step (or
any property change triggers the matcher), fire_spread fires as an
involuntary, writes ``on_fire=True`` + ``temperature=150`` on the
wooden_table, and the chain engine stops after the single hop because
the table has no further flammable neighbours.

Phase-5 integration notes
-------------------------
- GAP-MECH26 (reactive-cycle visibility): addressed in Phase 4 by the
  check()'s "all neighbours already on fire" refusal.
- GAP-ENG08 (engine-level cycle detector): defers to Phase 5 as a
  backstop. Today's ``max_chain_depth=10`` is the coarse backstop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.matchers import Matcher, PropertyChangeMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class FireSpreadMechanic(Mechanic):
    """Spread fire from an on-fire node to flammable neighbours (single hop).

    Preconditions (check):
        - Target exists.
        - Target has ``on_fire=True``.
        - At least one out-neighbour of target is flammable AND not
          already on fire (reactive-cycle guard, T-04-CYCLE).

    Side effects (apply):
        - For each flammable neighbour that is NOT already on_fire=True,
          set ``on_fire=True`` and ``temperature=150``. Emits zero
          mutations for neighbours that are already burning (idempotent
          reactive-cycle guard).
    """

    id = "fire_spread"
    description = "Fire propagates one hop per tick to flammable neighbours"
    voluntary = False
    tags: list[str] = ["environmental", "fire", "involuntary"]

    def watches(self) -> list[Matcher]:
        return [
            PropertyChangeMatcher(property_name="temperature"),
            PropertyChangeMatcher(property_name="on_fire"),
        ]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])

        target_props = ctx.query_node(ctx.target)
        if not target_props.get("on_fire"):
            return CheckResult(passed=False, reasons=["target is not on fire"])

        # At least one flammable neighbour that is NOT already on fire.
        eligible = False
        for neighbor in ctx.query_neighbors(ctx.target):
            props = ctx.query_node(neighbor)
            if props.get("flammable") and not props.get("on_fire"):
                eligible = True
                break
        if not eligible:
            return CheckResult(
                passed=False,
                reasons=["no flammable neighbours that are not already on fire"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        mutations: list[Mutation] = []
        for neighbor in ctx.query_neighbors(ctx.target):
            props = ctx.query_node(neighbor)
            if not props.get("flammable"):
                continue
            if props.get("on_fire"):
                # Reactive-cycle guard: never re-ignite already-burning nodes.
                continue
            mutations.append(ctx.mutate(neighbor, "on_fire", True))
            mutations.append(ctx.mutate(neighbor, "temperature", 150))
        return mutations
