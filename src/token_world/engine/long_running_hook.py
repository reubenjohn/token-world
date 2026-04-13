"""LongRunningHook (D-06, D-15, D-20) — per-tick orchestration of long-running actions.

Reads current_long_action from the actor's graph node, advances turns_elapsed,
evaluates thresholds, and emits an interruption / completion / time-passes
observation. Returns a HookResult that the engine uses to build the tick
summary and the TickResult.

Pitfall 1 mitigation: this hook is invoked ONLY on the synthetic continuation
path (engine._handle_long_running_tick). It is NOT invoked on _handle_execute
(where a mechanic just called begin_long_action). This means the FIRST hook
call for any LRA happens on the tick AFTER LRA-start, with turns_elapsed=0
on the graph; the hook advances to 1 and evaluates. An LRA that started in
a noisy room therefore does not insta-cancel.

D-22: "time passes" observation for continuing case is a static template
(no LLM call — cost-efficient for hobby budget; BatchCompressor already
compresses these).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from token_world.engine.long_running import ThresholdEvaluator, ThresholdSpec

logger = logging.getLogger(__name__)

_LRA_PROPERTY = "current_long_action"
_TIME_PASSES_TEMPLATE = "Time passes. You continue {action_text}."


@dataclass(frozen=True, slots=True)
class HookResult:
    """Result of one LongRunningHook.process() call (D-06).

    Attributes:
        active: Whether a long-running action was running on this tick.
        interrupted: Whether a threshold fired and interrupted the action.
        completed: Whether turns_elapsed reached turns_total.
        continuing: Whether the action is still in progress (no fire, not done).
        fired_threshold: The ThresholdSpec that fired, if any.
        observation: The narrative for this tick (interruption / completion / time passes).
        attention_state: Echoed from lra.payload for the engine to pass to the projector.
        action_text: Echoed from the LRA for tick summary and observation use.
    """

    active: bool
    interrupted: bool
    completed: bool
    continuing: bool
    fired_threshold: ThresholdSpec | None
    observation: str | None
    attention_state: dict | None
    action_text: str

    @classmethod
    def inactive(cls) -> HookResult:
        """No-op result: actor has no active LRA."""
        return cls(
            active=False,
            interrupted=False,
            completed=False,
            continuing=False,
            fired_threshold=None,
            observation=None,
            attention_state=None,
            action_text="",
        )


class LongRunningHook:
    """Per-tick orchestration of an actor's long-running action (D-06).

    Stateless: instantiate once and call process() each tick. All state is
    read from / written to the KnowledgeGraph.
    """

    def process(
        self,
        *,
        actor: str,
        projection: dict,
        graph: Any,  # KnowledgeGraph — avoided circular import via Any
        tick_id_str: str,
        observer: Any,  # Observer — avoided circular import via Any
        tick_diag_ctx: Any,  # Phase 4 TickDiagnostics ctx
    ) -> HookResult:
        """Process one continuation tick for an active long-running action.

        Steps:
        1. Graceful no-op if actor missing or has no current_long_action (Pitfall 3).
        2. Advance turns_elapsed by 1 (Pitfall 1: evaluate AFTER increment).
        3. Evaluate thresholds; if one fires → interruption path (D-10).
        4. If turns_elapsed >= turns_total → completion path.
        5. Otherwise → continuing path, static "time passes" template (D-22).

        Args:
            actor: Node ID of the actor whose LRA to process.
            projection: VisibilityProjector output (may include attention modulation).
            graph: The KnowledgeGraph instance.
            tick_id_str: Current tick identifier (for diagnostics).
            observer: Observer instance for interruption/completion narrative synthesis.
            tick_diag_ctx: TickDiagnostics context for observer diagnostics.

        Returns:
            HookResult describing the outcome of this tick.
        """
        # Step 1: graceful no-op (Pitfall 3 — actor missing or no LRA)
        if not graph.has_node(actor):
            return HookResult.inactive()

        try:
            lra = graph.query(actor, _LRA_PROPERTY)
        except (KeyError, Exception):
            return HookResult.inactive()

        if lra is None or not isinstance(lra, dict):
            return HookResult.inactive()

        # Extract LRA fields
        action_text = lra.get("action_text", "")
        payload = lra.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        attention_state = payload.get("attention_state")
        if not isinstance(attention_state, dict):
            attention_state = None

        # Step 2: advance turns_elapsed FIRST (Pitfall 1 — increment before eval)
        new_elapsed = int(lra.get("turns_elapsed", 0)) + 1
        updated = dict(lra)
        updated["turns_elapsed"] = new_elapsed
        graph.set(actor, _LRA_PROPERTY, updated)

        # Step 3: evaluate thresholds against current projection (D-09)
        thresholds = lra.get("thresholds")
        if not isinstance(thresholds, list):
            thresholds = []
        fired = ThresholdEvaluator.evaluate(thresholds, projection)
        if fired is not None:
            # Interruption path (D-10): clear LRA, synthesise grounded narrative
            graph.set(actor, _LRA_PROPERTY, None)
            observation = self._synthesise_interruption(
                observer=observer,
                projection=projection,
                actor=actor,
                action_text=action_text,
                fired=fired,
                tick_diag_ctx=tick_diag_ctx,
            )
            return HookResult(
                active=True,
                interrupted=True,
                completed=False,
                continuing=False,
                fired_threshold=fired,
                observation=observation,
                attention_state=attention_state,
                action_text=action_text,
            )

        # Step 4: completion check (D-13, D-16: turns_total=None = indefinite)
        turns_total = lra.get("turns_total")
        if turns_total is not None and new_elapsed >= int(turns_total):
            graph.set(actor, _LRA_PROPERTY, None)
            observation = self._synthesise_completion(
                observer=observer,
                projection=projection,
                actor=actor,
                action_text=action_text,
                tick_diag_ctx=tick_diag_ctx,
            )
            return HookResult(
                active=True,
                interrupted=False,
                completed=True,
                continuing=False,
                fired_threshold=None,
                observation=observation,
                attention_state=attention_state,
                action_text=action_text,
            )

        # Step 5: continuing — static template (D-22)
        return HookResult(
            active=True,
            interrupted=False,
            completed=False,
            continuing=True,
            fired_threshold=None,
            observation=_TIME_PASSES_TEMPLATE.format(action_text=action_text),
            attention_state=attention_state,
            action_text=action_text,
        )

    def _synthesise_interruption(
        self,
        *,
        observer: Any,
        projection: dict,
        actor: str,
        action_text: str,
        fired: ThresholdSpec,
        tick_diag_ctx: Any,
    ) -> str:
        """Build an interruption observation via observer.synthesize (D-10, D-21)."""
        from token_world.mechanic.protocol import CheckResult
        from token_world.mechanic.trace import ExecutionTrace, TraceNode

        # Minimal trace for the synthetic continuation tick — no real mechanic ran
        stub_node = TraceNode(
            mechanic_id="continue_long_action",
            actor=actor,
            target=actor,
            check_result=CheckResult(passed=True),
            mutations=[],
        )
        trace = ExecutionTrace(
            root=stub_node,
            total_mechanics_executed=0,
            max_depth_reached=0,
        )
        interruption_context = {
            "interrupted_by": {
                "property": fired.property,
                "op": fired.op,
                "value": fired.value,
            },
            "long_action": action_text,
        }
        return observer.synthesize(
            projection=projection,
            trace=trace,
            refusal_narrative=None,
            actor_id=actor,
            action_text=f"[interrupted: {action_text}]",
            tick_diag_ctx=tick_diag_ctx,
            interruption_context=interruption_context,
        )

    def _synthesise_completion(
        self,
        *,
        observer: Any,
        projection: dict,
        actor: str,
        action_text: str,
        tick_diag_ctx: Any,
    ) -> str:
        """Build a completion observation via observer.synthesize (D-10, D-21)."""
        from token_world.mechanic.protocol import CheckResult
        from token_world.mechanic.trace import ExecutionTrace, TraceNode

        stub_node = TraceNode(
            mechanic_id="continue_long_action",
            actor=actor,
            target=actor,
            check_result=CheckResult(passed=True),
            mutations=[],
        )
        trace = ExecutionTrace(
            root=stub_node,
            total_mechanics_executed=0,
            max_depth_reached=0,
        )
        interruption_context = {"completed": True, "long_action": action_text}
        return observer.synthesize(
            projection=projection,
            trace=trace,
            refusal_narrative=None,
            actor_id=actor,
            action_text=f"[completed: {action_text}]",
            tick_diag_ctx=tick_diag_ctx,
            interruption_context=interruption_context,
        )
