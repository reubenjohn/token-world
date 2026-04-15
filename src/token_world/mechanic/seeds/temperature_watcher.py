"""Temperature watcher seed mechanic: tracks temperature thresholds on entities.

Phase 18 chain-seed corpus — REQ-V12-DASHBOARD-06.
Demonstrates PropertyChangeMatcher on the ``temperature`` property with
threshold classification — distinct from environmental_reaction which
handles fire spread side-effects.

This mechanic classifies the current temperature into a human-readable
``temp_state`` (freezing / cold / warm / hot / scorching) so observation
synthesis and downstream mechanics can read a stable label instead of raw
numeric thresholds.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.matchers import Matcher, PropertyChangeMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext

# Temperature thresholds (degrees, arbitrary units consistent with universe defaults)
_THRESHOLDS: list[tuple[float, str]] = [
    (0, "freezing"),
    (10, "cold"),
    (25, "warm"),
    (60, "hot"),
    (100, "scorching"),
]


def _classify_temp(temp: float) -> str:
    """Return a human-readable label for *temp*."""
    label = "freezing"
    for threshold, name in _THRESHOLDS:
        if temp >= threshold:
            label = name
        else:
            break
    return label


class TemperatureWatcherMechanic(Mechanic):
    """Classifies temperature changes into stable state labels.

    Watches for ``temperature`` property changes on any node.  When triggered,
    maps the numeric value to a ``temp_state`` label (freezing / cold / warm /
    hot / scorching) and writes it back to the node.

    This keeps observation synthesis simple — the observer reads
    ``temp_state`` rather than inferring meaning from raw numbers.

    Preconditions:
        - Target node exists.
        - The node has a ``temperature`` property whose value is numeric.

    Side effects:
        - Writes ``temp_state = <label>`` onto the target node.

    Chain role:
        Downstream mechanics (e.g. environmental_reaction, contagion) can
        watch ``temp_state`` changes instead of raw ``temperature`` values,
        decoupling threshold logic from reaction logic.
    """

    id = "temperature_watcher"
    description = "Classifies temperature changes into temp_state labels (cold/warm/hot/…)"
    voluntary = False
    tags = ["reactive", "environmental", "chain", "core"]

    def watches(self) -> list[Matcher]:
        return [PropertyChangeMatcher(property_name="temperature")]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["Target node does not exist"])
        props = ctx.query_node(ctx.target)
        temp = props.get("temperature")
        if temp is None:
            return CheckResult(passed=False, reasons=["Target has no temperature property"])
        if not isinstance(temp, int | float):
            return CheckResult(
                passed=False,
                reasons=[f"temperature must be numeric, got {type(temp).__name__}"],
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        temp = ctx.query_node(ctx.target).get("temperature", 0)
        label = _classify_temp(float(temp))
        return [ctx.mutate(ctx.target, "temp_state", label)]

    def describe(self) -> str:
        return (
            "Watches the ``temperature`` property. Writes a ``temp_state`` "
            "label (freezing / cold / warm / hot / scorching) whenever "
            "temperature changes — decouples threshold logic from reaction "
            "mechanics."
        )
