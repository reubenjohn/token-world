"""MECH21 weather_reaction seed — FRAMEWORK-GAP STUB.

Blocked on GAP-ENG09 (the ``WorldPropertyMatcher`` mechanic-matcher
primitive) which lands in Phase 5. Per D-38 the stub ships now so:

    - the registry can enumerate ``weather_reaction`` (operator
      inspection, ``token-world list-mechanics`` UX),
    - the integration harness routes UC-V02 / UC-V04 to ``pytest.skip``
      with the gap id surfaced in the reason -- making the framework
      gap visible at every test run instead of hiding behind the
      manifests' stale ``expected_outcome: blocked`` reasons, and
    - when GAP-ENG09 closes, the stub is rewritten in place: drop
      ``blocked_by``, declare ``watches()`` with a WorldPropertyMatcher,
      fill in ``check`` / ``apply``, and the harness flips UC-V02 /
      UC-V04 from ``skip`` to ``pass`` automatically.

Per the §8 authoring-guide spec (and 04-RESEARCH "Pitfall 6"), the stub
MUST NOT import any symbol that doesn't yet exist; it must pass all six
validation stages. This module imports only ``Mutation`` and
``CheckResult`` / ``Mechanic`` from already-shipped surfaces.

Why GAP-ENG09 matters
---------------------
UC-V02 (weather change) and UC-V04 (seasons) flip world-level
properties -- ``world.weather``, ``world.season`` -- and expect every
outdoor/deciduous entity to react without per-agent action. Today's
matcher vocabulary only watches per-entity mutations; there is no
``WorldPropertyMatcher`` that filters on "a named property on the
distinguished 'world' node changed". Implementing weather_reaction
without that primitive would either (a) watch every entity's
``outdoor`` property for no-op reads, or (b) reach into ``ctx._graph``
and scan manually -- both are AST-flagged or noise. The stub is the
Phase-4-correct answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class WeatherReactionMechanic(Mechanic):
    """World-level weather/season reaction stub (BLOCKED on GAP-ENG09).

    BLOCKED: requires Phase 5's ``WorldPropertyMatcher`` (GAP-ENG09) so
    the involuntary triggers on ``world.weather`` / ``world.season``
    changes without scanning every entity on every tick. The stub
    refuses on every check and is a no-op on apply.
    """

    id = "weather_reaction"
    description = (
        "World-level weather/season reaction (framework-gap stub until GAP-ENG09)"
    )
    # NOTE: voluntary=True is a Phase-4 routing requirement for the D-38
    # harness stub-probe. The semantic intent remains *involuntary* (the
    # tag below records that intent); when GAP-ENG09 lands in Phase 5
    # this flips to voluntary=False along with the WorldPropertyMatcher
    # wiring. The stub never actually fires (check always refuses), so
    # voluntary=True is immaterial to runtime behaviour -- the flag
    # only decides whether match_mechanic_for_verb considers it. 04-09's
    # persuade / cooperate stubs follow the same pattern.
    voluntary = True
    tags: list[str] = ["environmental", "weather", "involuntary_intent"]
    blocked_by: str = "GAP-ENG09"

    def check(self, ctx: MechanicContext) -> CheckResult:
        return CheckResult(
            passed=False,
            reasons=[f"blocked by framework gap {self.blocked_by} until Phase 5"],
        )

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return []
