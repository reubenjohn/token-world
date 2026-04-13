"""Tests for ChainExecutionEngine."""

from __future__ import annotations

from tests.test_mechanic.conftest import DummyMechanic, FailingMechanic
from token_world.graph import KnowledgeGraph, Mutation
from token_world.mechanic import (
    ChainExecutionEngine,
    CheckResult,
    Mechanic,
    MechanicContext,
    PropertyChangeMatcher,
)


class WatchTestedMechanic(Mechanic):
    """Involuntary mechanic that watches the 'tested' property."""

    id = "watch_tested"
    description = "reacts to tested property"
    voluntary = False

    def check(self, ctx: MechanicContext) -> CheckResult:
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return [ctx.mutate(ctx.target, "reacted", True)]

    def watches(self) -> list[PropertyChangeMatcher]:
        return [PropertyChangeMatcher(property_name="tested")]


class ChainAMechanic(Mechanic):
    """Sets prop_a, watched by ChainBMechanic."""

    id = "chain_a"
    description = "sets prop_a"
    voluntary = False

    def check(self, ctx: MechanicContext) -> CheckResult:
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return [ctx.mutate(ctx.target, "prop_a", True)]

    def watches(self) -> list[PropertyChangeMatcher]:
        return [PropertyChangeMatcher(property_name="trigger_a")]


class ChainBMechanic(Mechanic):
    """Sets prop_b, watched by ChainAMechanic (creates cycle potential)."""

    id = "chain_b"
    description = "sets prop_b"
    voluntary = False

    def check(self, ctx: MechanicContext) -> CheckResult:
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return [ctx.mutate(ctx.target, "trigger_a", True)]

    def watches(self) -> list[PropertyChangeMatcher]:
        return [PropertyChangeMatcher(property_name="prop_a")]


class SelfWatchMechanic(Mechanic):
    """Involuntary mechanic that watches its own output property."""

    id = "self_watch"
    description = "watches its own output"
    voluntary = False

    def check(self, ctx: MechanicContext) -> CheckResult:
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return [ctx.mutate(ctx.target, "self_prop", True)]

    def watches(self) -> list[PropertyChangeMatcher]:
        return [PropertyChangeMatcher(property_name="self_prop")]


def _make_graph() -> KnowledgeGraph:
    """Create a test graph with alice and room_a."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", location="room_a")
    kg.add_node("room_a", node_type="entity", location=True)
    kg.add_node("room_b", node_type="entity", location=True)
    return kg


class TestChainExecutionEngine:
    """Tests for ChainExecutionEngine."""

    def test_basic_execution(self) -> None:
        """Execute returns ExecutionTrace with root TraceNode."""
        graph = _make_graph()
        ctx = MechanicContext(graph, actor="alice", target="room_a")
        engine = ChainExecutionEngine(involuntary_mechanics=[])
        trace = engine.execute(DummyMechanic(), ctx)

        assert trace.root.mechanic_id == "dummy"
        assert trace.root.actor == "alice"
        assert trace.root.target == "room_a"
        assert trace.root.check_result.passed is True
        assert len(trace.root.mutations) == 1
        assert trace.root.mutations[0].type == "set_property"
        assert trace.root.children == []
        assert trace.total_mechanics_executed == 1
        assert trace.truncated is False

    def test_failing_check(self) -> None:
        """Failing check returns trace with empty mutations."""
        graph = _make_graph()
        ctx = MechanicContext(graph, actor="alice", target="room_a")
        engine = ChainExecutionEngine(involuntary_mechanics=[])
        trace = engine.execute(FailingMechanic(), ctx)

        assert trace.root.mechanic_id == "failing"
        assert trace.root.check_result.passed is False
        assert trace.root.mutations == []
        assert trace.root.children == []
        assert trace.total_mechanics_executed == 0

    def test_chain_trigger(self) -> None:
        """Involuntary mechanics triggered by matching mutations."""
        graph = _make_graph()
        ctx = MechanicContext(graph, actor="alice", target="alice")
        watcher = WatchTestedMechanic()
        engine = ChainExecutionEngine(involuntary_mechanics=[watcher])
        trace = engine.execute(DummyMechanic(), ctx)

        assert trace.total_mechanics_executed == 2
        assert len(trace.root.children) == 1
        child = trace.root.children[0]
        assert child.mechanic_id == "watch_tested"
        assert child.check_result.passed is True
        assert len(child.mutations) == 1

    def test_max_depth_truncation(self) -> None:
        """Max depth stops chain and sets truncated=True."""
        graph = _make_graph()
        ctx = MechanicContext(graph, actor="alice", target="room_a")
        # ChainA and ChainB ping-pong: A sets prop_a, B watches prop_a and
        # sets trigger_a, A watches trigger_a... With same target, cycle
        # detection would stop them. But the chain hits max_depth first
        # when max_depth is low enough.
        engine = ChainExecutionEngine(
            involuntary_mechanics=[ChainAMechanic(), ChainBMechanic()],
            max_depth=2,
        )

        class TriggerMechanic(Mechanic):
            id = "trigger"
            description = "sets trigger_a"

            def check(self, ctx: MechanicContext) -> CheckResult:
                return CheckResult(passed=True)

            def apply(self, ctx: MechanicContext) -> list[Mutation]:
                return [ctx.mutate(ctx.target, "trigger_a", True)]

        trace = engine.execute(TriggerMechanic(), ctx)

        # Chain: trigger(d0) -> chain_a at d1 -> chain_b at d2 -> would try d3
        # but max_depth=2 truncates
        assert trace.truncated is True
        assert trace.total_mechanics_executed >= 2

    def test_cycle_detection_same_target(self) -> None:
        """Cycle detection skips (mechanic_id, target) duplicates."""
        graph = _make_graph()
        ctx = MechanicContext(graph, actor="alice", target="room_a")
        engine = ChainExecutionEngine(involuntary_mechanics=[SelfWatchMechanic()])

        # Mechanic that triggers self_prop
        class TriggerSelfProp(Mechanic):
            id = "trigger_self"
            description = "sets self_prop to trigger self_watch"

            def check(self, ctx: MechanicContext) -> CheckResult:
                return CheckResult(passed=True)

            def apply(self, ctx: MechanicContext) -> list[Mutation]:
                return [ctx.mutate(ctx.target, "self_prop", True)]

        trace = engine.execute(TriggerSelfProp(), ctx)

        # self_watch fires once on room_a, then its own output would trigger it
        # again on room_a, but cycle detection prevents it
        assert trace.total_mechanics_executed == 2  # trigger + self_watch once
        assert len(trace.root.children) == 1

    def test_different_targets_not_cycles(self) -> None:
        """Different targets for same mechanic are NOT cycles."""
        graph = _make_graph()
        # Add self_prop to both rooms so the mechanic can fire on both
        ctx = MechanicContext(graph, actor="alice", target="room_a")

        class MultiTargetWatcher(Mechanic):
            """Watches temperature, sets temperature on neighbors."""

            id = "multi_target"
            description = "spreads to neighbors"
            voluntary = False

            def check(self, ctx: MechanicContext) -> CheckResult:
                return CheckResult(passed=True)

            def apply(self, ctx: MechanicContext) -> list[Mutation]:
                return [ctx.mutate(ctx.target, "heated", True)]

            def watches(self) -> list[PropertyChangeMatcher]:
                return [PropertyChangeMatcher(property_name="temperature")]

        engine = ChainExecutionEngine(involuntary_mechanics=[MultiTargetWatcher()])

        # Set temperature on room_a - this triggers the watcher on room_a
        class HeatMechanic(Mechanic):
            id = "heat"
            description = "heats room_a"

            def check(self, ctx: MechanicContext) -> CheckResult:
                return CheckResult(passed=True)

            def apply(self, ctx: MechanicContext) -> list[Mutation]:
                # Set temperature on room_a AND room_b
                return [
                    ctx.mutate("room_a", "temperature", 100),
                    ctx.mutate("room_b", "temperature", 80),
                ]

        trace = engine.execute(HeatMechanic(), ctx)

        # multi_target should fire on both room_a and room_b (different targets)
        assert trace.total_mechanics_executed >= 3  # heat + 2 multi_target firings

    def test_total_mechanics_count(self) -> None:
        """total_mechanics_executed count is correct."""
        graph = _make_graph()
        ctx = MechanicContext(graph, actor="alice", target="alice")
        engine = ChainExecutionEngine(involuntary_mechanics=[WatchTestedMechanic()])
        trace = engine.execute(DummyMechanic(), ctx)

        # DummyMechanic + WatchTestedMechanic
        assert trace.total_mechanics_executed == 2

    def test_max_depth_reached(self) -> None:
        """max_depth_reached reflects actual depth."""
        graph = _make_graph()
        ctx = MechanicContext(graph, actor="alice", target="alice")
        engine = ChainExecutionEngine(involuntary_mechanics=[WatchTestedMechanic()])
        trace = engine.execute(DummyMechanic(), ctx)

        # Root is depth 0, WatchTested fires at depth 1
        assert trace.max_depth_reached == 1
