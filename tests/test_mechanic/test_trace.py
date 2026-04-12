"""Tests for ExecutionTrace and TraceNode dataclasses."""

from __future__ import annotations

from token_world.graph import Mutation
from token_world.mechanic import CheckResult, ExecutionTrace, TraceNode


class TestTraceNode:
    """Tests for TraceNode dataclass."""

    def test_construction(self) -> None:
        """TraceNode has all expected fields."""
        node = TraceNode(
            mechanic_id="test_mech",
            actor="alice",
            target="room_a",
            check_result=CheckResult(passed=True),
            mutations=[
                Mutation(
                    type="set_property",
                    target="room_a",
                    property="temperature",
                    old_value=20,
                    new_value=100,
                )
            ],
        )
        assert node.mechanic_id == "test_mech"
        assert node.actor == "alice"
        assert node.target == "room_a"
        assert node.check_result.passed is True
        assert len(node.mutations) == 1
        assert node.children == []

    def test_children_default_empty(self) -> None:
        """Children default to empty list."""
        node = TraceNode(
            mechanic_id="m",
            actor="a",
            target="t",
            check_result=CheckResult(passed=True),
            mutations=[],
        )
        assert node.children == []

    def test_children_populated(self) -> None:
        """TraceNode can have children."""
        child = TraceNode(
            mechanic_id="child",
            actor="a",
            target="t",
            check_result=CheckResult(passed=True),
            mutations=[],
        )
        parent = TraceNode(
            mechanic_id="parent",
            actor="a",
            target="t",
            check_result=CheckResult(passed=True),
            mutations=[],
            children=[child],
        )
        assert len(parent.children) == 1
        assert parent.children[0].mechanic_id == "child"


class TestExecutionTrace:
    """Tests for ExecutionTrace dataclass."""

    def test_construction(self) -> None:
        """ExecutionTrace has root, total, max_depth, truncated."""
        root = TraceNode(
            mechanic_id="m",
            actor="a",
            target="t",
            check_result=CheckResult(passed=True),
            mutations=[],
        )
        trace = ExecutionTrace(
            root=root,
            total_mechanics_executed=1,
            max_depth_reached=0,
        )
        assert trace.root is root
        assert trace.total_mechanics_executed == 1
        assert trace.max_depth_reached == 0
        assert trace.truncated is False

    def test_truncated_flag(self) -> None:
        """ExecutionTrace truncated flag can be set."""
        root = TraceNode(
            mechanic_id="m",
            actor="a",
            target="t",
            check_result=CheckResult(passed=True),
            mutations=[],
        )
        trace = ExecutionTrace(
            root=root,
            total_mechanics_executed=5,
            max_depth_reached=10,
            truncated=True,
        )
        assert trace.truncated is True
        assert trace.max_depth_reached == 10
