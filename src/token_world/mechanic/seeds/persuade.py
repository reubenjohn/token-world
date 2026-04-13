"""MECH09 persuade seed — FRAMEWORK-GAP STUB.

Blocked on GAP-ENG03 (the ``llm_adjudicated`` mechanic category) which
lands in Phase 5. Per D-38 the stub ships now so that:

    - the registry can enumerate ``persuade`` (operator inspection,
      ``token-world list-mechanics`` UX),
    - the integration harness can route UC-O02 to ``pytest.skip`` with
      the gap id surfaced in the reason — making the framework gap
      visible at every test run instead of hiding behind a stale
      ``expected_outcome`` field, and
    - when the gap closes, the stub is rewritten in place: drop
      ``blocked_by``, fill in ``check`` / ``apply``, and the harness
      flips ``UC-O02`` from ``skip`` to ``pass`` automatically.

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


class PersuadeMechanic(Mechanic):
    """Agent attempts to persuade another agent (BLOCKED on GAP-ENG03).

    BLOCKED: requires Phase 5's ``llm_adjudicated`` mechanic category
    (GAP-ENG03). The stub refuses on every check and is a no-op on apply.
    """

    id = "persuade"
    description = "Agent attempts to persuade another (framework-gap stub until GAP-ENG03)"
    voluntary = True
    tags: list[str] = ["social", "llm_adjudicated"]
    blocked_by: str = "GAP-ENG03"

    def check(self, ctx: MechanicContext) -> CheckResult:
        return CheckResult(
            passed=False,
            reasons=[f"blocked by framework gap {self.blocked_by} until Phase 5"],
        )

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return []
