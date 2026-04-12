"""Chain execution engine for mechanic invocation with reactive chaining."""

from __future__ import annotations

from token_world.graph import KnowledgeGraph, Mutation
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.matchers import matches
from token_world.mechanic.protocol import Mechanic
from token_world.mechanic.trace import ExecutionTrace, TraceNode


class ChainExecutionEngine:
    """Executes mechanics and chains involuntary mechanics reactively.

    After a mechanic's ``apply()`` produces mutations, the engine evaluates
    all involuntary mechanics' matchers against those mutations. Matching
    mechanics are executed, which may produce further mutations and trigger
    more chains.

    Args:
        involuntary_mechanics: List of involuntary mechanics to evaluate
            after each apply().
        max_depth: Maximum chain depth before truncation. Default 10.
    """

    def __init__(
        self,
        involuntary_mechanics: list[Mechanic],
        max_depth: int = 10,
    ) -> None:
        self._involuntary = involuntary_mechanics
        self._max_depth = max_depth

    def execute(self, mechanic: Mechanic, ctx: MechanicContext) -> ExecutionTrace:
        """Execute a mechanic and chain any triggered involuntary mechanics.

        Args:
            mechanic: The mechanic to execute.
            ctx: The execution context (actor, target, graph access).

        Returns:
            ExecutionTrace containing the full invocation tree.
        """
        check_result = mechanic.check(ctx)

        if not check_result.passed:
            root = TraceNode(
                mechanic_id=mechanic.id,
                actor=ctx.actor,
                target=ctx.target,
                check_result=check_result,
                mutations=[],
            )
            return ExecutionTrace(
                root=root,
                total_mechanics_executed=0,
                max_depth_reached=0,
                truncated=False,
            )

        mutations = mechanic.apply(ctx)

        seen: set[tuple[str, str]] = {(mechanic.id, ctx.target)}
        children, truncated, child_count, child_depth = self._evaluate_chain(
            mutations, ctx.actor, ctx._graph, depth=1, seen=seen
        )

        root = TraceNode(
            mechanic_id=mechanic.id,
            actor=ctx.actor,
            target=ctx.target,
            check_result=check_result,
            mutations=mutations,
            children=children,
        )

        return ExecutionTrace(
            root=root,
            total_mechanics_executed=1 + child_count,
            max_depth_reached=child_depth,
            truncated=truncated,
        )

    def _evaluate_chain(
        self,
        mutations: list[Mutation],
        actor: str,
        graph: KnowledgeGraph,
        depth: int,
        seen: set[tuple[str, str]],
    ) -> tuple[list[TraceNode], bool, int, int]:
        """Recursively evaluate involuntary mechanics against mutations.

        Args:
            mutations: Mutations to match against.
            actor: The actor for context creation.
            graph: The knowledge graph.
            depth: Current chain depth.
            seen: Set of (mechanic_id, target) pairs for cycle detection.

        Returns:
            Tuple of (child_nodes, any_truncated, total_executed, max_depth).
        """
        if depth > self._max_depth:
            return [], True, 0, depth - 1

        nodes: list[TraceNode] = []
        any_truncated = False
        total_executed = 0
        max_depth = 0

        for mech in self._involuntary:
            # Check if any matcher matches any mutation
            for mutation in mutations:
                matched = False
                for matcher in mech.watches():
                    if matches(matcher, mutation, graph):
                        matched = True
                        break

                if not matched:
                    continue

                # Determine target from mutation
                target = mutation.target
                if "->" in target:
                    # Edge mutation: use source node
                    target = target.split("->")[0]

                # Cycle detection
                if (mech.id, target) in seen:
                    continue

                # Create context and execute
                chain_ctx = MechanicContext(graph, actor=actor, target=target)
                check_result = mech.check(chain_ctx)

                if not check_result.passed:
                    nodes.append(
                        TraceNode(
                            mechanic_id=mech.id,
                            actor=actor,
                            target=target,
                            check_result=check_result,
                            mutations=[],
                        )
                    )
                    continue

                new_mutations = mech.apply(chain_ctx)
                seen.add((mech.id, target))
                total_executed += 1

                # Recurse
                children, child_trunc, child_exec, child_d = self._evaluate_chain(
                    new_mutations, actor, graph, depth + 1, seen
                )

                any_truncated = any_truncated or child_trunc
                total_executed += child_exec
                max_depth = max(max_depth, depth, child_d)

                nodes.append(
                    TraceNode(
                        mechanic_id=mech.id,
                        actor=actor,
                        target=target,
                        check_result=check_result,
                        mutations=new_mutations,
                        children=children,
                    )
                )

                # Only trigger once per mechanic per mutation batch
                break

        return nodes, any_truncated, total_executed, max_depth
