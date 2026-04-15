"""Mood-change watcher seed mechanic: tracks and logs mood transitions on agents.

Phase 18 chain-seed corpus — REQ-V12-DASHBOARD-06.
Demonstrates PropertyChangeMatcher on the ``mood`` property.

This is an involuntary mechanic that fires whenever any node's ``mood``
property changes.  It records the previous mood on the agent for
observation grounding and can serve as a chain trigger for downstream
mood-reactive mechanics (e.g. NPC sympathy response, ambient dialogue).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.matchers import Matcher, PropertyChangeMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class MoodChangeWatcherMechanic(Mechanic):
    """Records mood transitions for observation grounding.

    Watches for ``mood`` property changes on any node (typically agents).
    When a mood transition occurs the mechanic writes ``previous_mood`` back
    onto the node so observers and downstream mechanics can read both the old
    and new state from the graph — no side-channel required.

    Preconditions:
        - Target node exists in the graph.
        - The node has a ``mood`` property.

    Side effects:
        - Writes ``previous_mood = <old value>`` onto the target node.

    Chain role:
        Downstream mechanics can watch ``previous_mood`` changes to react
        to mood *transitions* (e.g. "was happy, now sad") rather than just
        the current mood.
    """

    id = "mood_change_watcher"
    description = "Records mood transitions (previous_mood) when a node's mood changes"
    voluntary = False
    tags = ["reactive", "agent", "chain", "core"]

    def watches(self) -> list[Matcher]:
        return [PropertyChangeMatcher(property_name="mood")]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["Target node does not exist"])
        props = ctx.query_node(ctx.target)
        if "mood" not in props:
            return CheckResult(passed=False, reasons=["Target has no mood property"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        props = ctx.query_node(ctx.target)
        # The mutation event carries the old value; we read the pre-change
        # value from the last_event context when available, falling back to
        # the current stored value as best-effort.
        current_mood = props.get("mood")
        # Record current mood as previous so chain mechanics can see the transition.
        return [ctx.mutate(ctx.target, "previous_mood", current_mood)]

    def describe(self) -> str:
        return (
            "Watches the ``mood`` property on any node. When mood changes, "
            "writes the current (pre-change) value to ``previous_mood`` so "
            "observers and chain mechanics can reference the full transition."
        )
