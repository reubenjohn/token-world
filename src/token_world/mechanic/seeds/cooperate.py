"""MECH12 cooperate seed — FRAMEWORK-GAP STUB.

Blocked on GAP-ENG05 (intent-fusion pre-pass for multi-actor mechanics)
which lands in Phase 5 alongside the ``actors: list[NodeId]`` mechanic
API extension (also tracked as GAP-MECH12). Per D-38 the stub ships so
the registry, harness, and operator UX can all see the gap explicitly.

Per the §8 authoring guide spec (and 04-RESEARCH "Pitfall 6"), the
stub MUST NOT import any symbol that doesn't yet exist; it must pass
all six validation stages. This module imports only ``Mutation`` and
``CheckResult`` / ``Mechanic`` from already-shipped surfaces.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class CooperateMechanic(Mechanic):
    """Multi-actor cooperative action stub (BLOCKED on GAP-ENG05).

    BLOCKED: requires Phase 5's intent-fusion pre-pass (GAP-ENG05) plus
    the multi-actor mechanic API extension. The stub refuses on every
    check and is a no-op on apply.
    """

    id = "cooperate"
    description = (
        "Multi-actor cooperative action (framework-gap stub until GAP-ENG05)"
    )
    voluntary = True
    tags: list[str] = ["social", "multi_actor"]
    blocked_by: str = "GAP-ENG05"

    def check(self, ctx: MechanicContext) -> CheckResult:
        return CheckResult(
            passed=False,
            reasons=[f"blocked by framework gap {self.blocked_by} until Phase 5"],
        )

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return []
