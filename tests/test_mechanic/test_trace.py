"""Tests for ExecutionTrace, TraceNode, and the shared walker helpers.

The walker helpers (``walk_trace``, ``collect_mutations``) were extracted on
2026-04-14 from four near-identical call sites (summary_writer, engine,
observer, scorer) as IN-02 tech-debt closure. Tests here pin their pure
behaviour — no I/O, no side effects, deterministic pre-order depth-first
traversal.
"""

from __future__ import annotations

from token_world.graph import Mutation
from token_world.mechanic import (
    CheckResult,
    ExecutionTrace,
    TraceNode,
    collect_mutations,
    walk_trace,
)


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


# ---------------------------------------------------------------------------
# Walker helpers (IN-02 tech-debt closure, 2026-04-14)
# ---------------------------------------------------------------------------


def _make_mutation(target: str, prop: str, old: int, new: int) -> Mutation:
    """Build a simple Mutation for walker tests."""
    return Mutation(
        type="set_property",
        target=target,
        property=prop,
        old_value=old,
        new_value=new,
    )


def _make_node(
    mechanic_id: str,
    mutations: list[Mutation] | None = None,
    children: list[TraceNode] | None = None,
) -> TraceNode:
    """Build a TraceNode with minimal required fields."""
    return TraceNode(
        mechanic_id=mechanic_id,
        actor="alice",
        target="target",
        check_result=CheckResult(passed=True),
        mutations=mutations or [],
        children=children or [],
    )


class TestWalkTrace:
    """Tests for walk_trace: pre-order depth-first node traversal."""

    def test_none_yields_nothing(self) -> None:
        """walk_trace(None) is a valid empty iterator — no crash, no nodes."""
        assert list(walk_trace(None)) == []

    def test_single_root_yields_one_node(self) -> None:
        """Trace with only a root node yields exactly that node."""
        root = _make_node("root")
        trace = ExecutionTrace(root=root, total_mechanics_executed=1, max_depth_reached=0)
        visited = list(walk_trace(trace))
        assert len(visited) == 1
        assert visited[0].mechanic_id == "root"

    def test_preorder_depth_first_left_to_right(self) -> None:
        """Pre-order DFS: parent first, then each child subtree in order.

        Tree shape:
            root
            ├── a
            │   └── a1
            └── b

        Expected order: root, a, a1, b.
        """
        a1 = _make_node("a1")
        a = _make_node("a", children=[a1])
        b = _make_node("b")
        root = _make_node("root", children=[a, b])
        trace = ExecutionTrace(root=root, total_mechanics_executed=4, max_depth_reached=2)

        ids = [n.mechanic_id for n in walk_trace(trace)]
        assert ids == ["root", "a", "a1", "b"]

    def test_deep_chain_visits_all_levels(self) -> None:
        """Deep chain (root → c1 → c2 → c3) visits every level in order."""
        c3 = _make_node("c3")
        c2 = _make_node("c2", children=[c3])
        c1 = _make_node("c1", children=[c2])
        root = _make_node("root", children=[c1])
        trace = ExecutionTrace(root=root, total_mechanics_executed=4, max_depth_reached=3)

        ids = [n.mechanic_id for n in walk_trace(trace)]
        assert ids == ["root", "c1", "c2", "c3"]


class TestCollectMutations:
    """Tests for collect_mutations: flat Mutation list across trace tree."""

    def test_none_returns_empty_list(self) -> None:
        """collect_mutations(None) returns [] — mirrors yield/refuse path."""
        assert collect_mutations(None) == []

    def test_single_node_no_mutations(self) -> None:
        """Single node with empty mutations list returns []."""
        root = _make_node("root")
        trace = ExecutionTrace(root=root, total_mechanics_executed=1, max_depth_reached=0)
        assert collect_mutations(trace) == []

    def test_single_node_with_mutations(self) -> None:
        """Single node's mutations are returned verbatim."""
        m1 = _make_mutation("room_a", "temp", 20, 25)
        m2 = _make_mutation("room_a", "humidity", 40, 50)
        root = _make_node("root", mutations=[m1, m2])
        trace = ExecutionTrace(root=root, total_mechanics_executed=1, max_depth_reached=0)

        result = collect_mutations(trace)
        assert result == [m1, m2]

    def test_mutations_collected_across_children(self) -> None:
        """Mutations from every subtree are flattened into one list."""
        m_root = _make_mutation("root_target", "p", 0, 1)
        m_a = _make_mutation("a_target", "p", 0, 1)
        m_b = _make_mutation("b_target", "p", 0, 1)
        a = _make_node("a", mutations=[m_a])
        b = _make_node("b", mutations=[m_b])
        root = _make_node("root", mutations=[m_root], children=[a, b])
        trace = ExecutionTrace(root=root, total_mechanics_executed=3, max_depth_reached=1)

        result = collect_mutations(trace)
        assert len(result) == 3
        # Pre-order: root first, then a, then b.
        assert result[0] is m_root
        assert result[1] is m_a
        assert result[2] is m_b

    def test_mutations_collected_from_deep_chain(self) -> None:
        """Chain depth >= 2 walks all levels and collects all mutations."""
        m_c2 = _make_mutation("x", "p", 0, 1)
        m_c1 = _make_mutation("y", "p", 0, 1)
        m_root = _make_mutation("z", "p", 0, 1)
        c2 = _make_node("c2", mutations=[m_c2])
        c1 = _make_node("c1", mutations=[m_c1], children=[c2])
        root = _make_node("root", mutations=[m_root], children=[c1])
        trace = ExecutionTrace(root=root, total_mechanics_executed=3, max_depth_reached=2)

        result = collect_mutations(trace)
        # Pre-order: root, c1, c2.
        assert [m.target for m in result] == ["z", "y", "x"]

    def test_empty_middle_node_does_not_break_collection(self) -> None:
        """A node with no mutations but with children still has children walked."""
        m_leaf = _make_mutation("leaf", "p", 0, 1)
        leaf = _make_node("leaf", mutations=[m_leaf])
        middle = _make_node("middle", children=[leaf])  # no mutations on middle
        root = _make_node("root", children=[middle])
        trace = ExecutionTrace(root=root, total_mechanics_executed=3, max_depth_reached=2)

        result = collect_mutations(trace)
        assert result == [m_leaf]

    def test_parity_with_recursive_reference_implementation(self) -> None:
        """Cross-check against a trivial recursive implementation on a mixed tree.

        This guards against a silent regression if the iterative implementation
        ever drifts from the simple recursive spec.
        """

        def ref_collect(node: TraceNode) -> list[Mutation]:
            out = list(node.mutations)
            for child in node.children:
                out.extend(ref_collect(child))
            return out

        # Build a moderately complex tree.
        m_a1 = _make_mutation("a1", "p", 0, 1)
        m_a2 = _make_mutation("a2", "p", 0, 1)
        m_b = _make_mutation("b", "p", 0, 1)
        a1 = _make_node("a1", mutations=[m_a1])
        a2 = _make_node("a2", mutations=[m_a2])
        a = _make_node("a", children=[a1, a2])
        b = _make_node("b", mutations=[m_b])
        root = _make_node("root", children=[a, b])
        trace = ExecutionTrace(root=root, total_mechanics_executed=5, max_depth_reached=2)

        assert collect_mutations(trace) == ref_collect(root)
