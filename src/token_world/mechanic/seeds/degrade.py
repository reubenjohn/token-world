"""MECH17 degrade seed: actor uses a held tool, decrementing its durability.

The use-on-tool form of degradation: the actor swings/strikes/works with
a held tool, the tool's ``durability`` decreases by ``usage_cost`` (default
1), and at-or-below 0 the tool is removed from the world (which drops its
``holds`` edge as a consequence). This is the canonical wear primitive --
"every action has a consequence on the thing it was done with".

Ambient (passive-tick) decay -- rust on metal, rot on food, fade on dye --
is OUT of scope. That's ``GAP-ENG07`` (passive-tick sweep) and lives in
Phase 5+; the engine will fire ``degrade`` reactively from a tick scheduler
without needing an actor verb.

UC-R05 routing
--------------
UC-R05's manifest classifies its actions as ``verb=strike`` with
``target=dummy`` and ``instrument=sword``. The Phase-4 harness routes by
``verb -> mechanic.id`` and uses ``target = classified.target or
classified.indirect_object`` -- there is no ``instrument`` slot
(``GAP-ENG02``). The harness cannot route the manifest's ``strike`` to
``degrade`` without a use-case rewrite. Combined with UC-R05's threshold-
flag assertion semantics (``broken=true`` on intact zero-durability node)
being a different shape than the degrade-with-removal-at-zero contract
this mechanic ships, UC-R05's ``expected_outcome`` stays ``blocked``
(rationale recorded in 04-10-SUMMARY.md). When Phase 5 lands the
classifier and an ``instrument`` slot, the manifest can be revisited.

Contract
--------
Preconditions (check):
    - Actor exists.
    - Target exists.
    - Actor holds the target (``actor -[holds]-> target``).
    - Target carries an integer ``durability`` property.

Side effects (apply):
    - ``new_durability = durability - usage_cost`` (default usage_cost=1).
    - If ``new_durability <= 0``: ``remove_node(target)``. The holds edge
      is dropped as a consequence (KnowledgeGraph removes incident edges).
    - Else: ``set(target, "durability", new_durability)``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class DegradeMechanic(Mechanic):
    """Actor uses a held tool, decrementing its durability.

    Preconditions (check):
        - Actor + target exist.
        - Actor holds the target.
        - Target has an integer ``durability`` property.

    Side effects (apply):
        - Above 0: durability decremented by ``usage_cost`` (default 1).
        - At/below 0: target node removed; holds edge dropped with it.
    """

    id = "degrade"
    description = "Actor uses a held tool, decrementing durability; removes at <= 0"
    voluntary = True
    tags: list[str] = ["resource", "durability"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])
        held = set(ctx.neighbors(ctx.actor, relation="holds"))
        if ctx.target not in held:
            return CheckResult(
                passed=False,
                reasons=[f"actor does not hold target {ctx.target!r}"],
            )
        target_props = ctx.query_node(ctx.target)
        durability = target_props.get("durability")
        # bool is a subclass of int in Python; reject it explicitly so
        # ``durability=True`` doesn't slip through as a numeric value.
        if not isinstance(durability, int) or isinstance(durability, bool):
            return CheckResult(
                passed=False,
                reasons=[f"target {ctx.target!r} has no integer durability property"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        target_props = ctx.query_node(ctx.target)
        durability = int(target_props["durability"])
        usage_cost = target_props.get("usage_cost", 1)
        # Defensive: a bad usage_cost type falls back to 1 rather than
        # raising in apply (check has already passed).
        if not isinstance(usage_cost, int) or isinstance(usage_cost, bool) or usage_cost < 0:
            usage_cost = 1

        new_durability = durability - usage_cost
        if new_durability <= 0:
            return [ctx.remove_node(ctx.target)]
        return [ctx.set(ctx.target, "durability", new_durability)]
