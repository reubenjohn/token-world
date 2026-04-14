"""SimulationEngine — orchestrator wiring all Phase 5 stages (D-01).

Pipeline (per D-01):
    classify (Haiku) → match (deterministic) → decide (precedence ladder)
        → execute (ChainExecutionEngine) → conservation → passive_sweep
        → observe (Sonnet) → tick_summary write

Three terminal paths:
    EXECUTE: full pipeline; returns TickResult.ok(observation_text)
    YIELD:   skip execute/conservation/sweep/observe; emit YieldSignal;
             return TickResult.yielded(signal)
    REFUSE:  classifier-refusal OR conservation-violation; render via RefusalTemplate;
             on conservation violation also rollback via graph.restore(pre_tick_snapshot)

Per D-02 the registry is re-scanned at the top of every run_tick so resume_tick after the
operator authors a missing mechanic Just Works without extra plumbing.

Per D-22 every LLM call writes diagnostics through `DiagnosticsSink.open_tick(tick_id)`.

Per D-17 (single-agent invariant): at most one resident-agent action per tick in v1.
Multi-agent conflict detection is deferred to v2 (D-18).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from token_world.engine.classifier import Classifier
from token_world.engine.compressor import TickCompressor
from token_world.engine.config import EngineConfig, load_engine_config
from token_world.engine.conservation import ConservationChecker
from token_world.engine.decider import decide
from token_world.engine.long_running_hook import LongRunningHook
from token_world.engine.matcher import DeterministicMatcher
from token_world.engine.models import (
    ClassifiedAction,
    Decision,
    ExecuteDecision,
    RefuseDecision,
    VerdictOk,
    YieldDecision,
)
from token_world.engine.observer import Observer
from token_world.engine.refusal import RefusalTemplate
from token_world.engine.summary_writer import TickSummaryWriter, build_tick_summary
from token_world.engine.visibility import VisibilityProjector
from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.diagnostics import DiagnosticsSink
from token_world.mechanic.engine import ChainExecutionEngine
from token_world.mechanic.matchers import (
    DecayMatcher,
    TickMatcher,
    VerbMatcher,
    WorldPropertyMatcher,
)
from token_world.mechanic.registry import MechanicRegistry
from token_world.mechanic.trace import ExecutionTrace, TraceNode, collect_mutations
from token_world.operator.yield_signal import YieldSignal

logger = logging.getLogger(__name__)

_SENTINEL_NODE_ID = "_engine_tick_sentinel"


class _ClassifierDiagnosticsAdapter:
    """Thin adapter bridging the Classifier's write_prompt/write_response/write_parsed
    API to the TickDiagnostics.write_classification(prompt, response, parsed) API.

    The Classifier (Wave 1) was authored against a slightly different diagnostics
    contract from TickDiagnostics (Phase 4). Rather than modifying either file
    (classifier.py is outside plan scope; TickDiagnostics is Phase 4), this adapter
    buffers the three separate calls and forwards them to write_classification on flush.
    """

    def __init__(self, tick_ctx: Any) -> None:
        self._ctx = tick_ctx
        self._prompts: dict[str, str] = {}
        self._responses: dict[str, str] = {}
        self._parsed: dict[str, dict] = {}

    def write_prompt(self, stage: str, prompt: str) -> None:
        self._prompts[stage] = prompt

    def write_response(self, stage: str, response: str, suffix: str = "") -> None:
        key = stage + suffix
        self._responses[key] = response
        # Flush to TickDiagnostics if we have all three for this stage
        self._maybe_flush(stage)

    def write_parsed(self, stage: str, parsed: dict) -> None:
        self._parsed[stage] = parsed
        self._maybe_flush(stage)

    def _maybe_flush(self, stage: str) -> None:
        prompt = self._prompts.get(stage, "")
        response = self._responses.get(stage, "")
        parsed = self._parsed.get(stage, {})
        if (
            (response or parsed)
            and hasattr(self._ctx, "write_classification")
            and stage == "classification"
        ):
            self._ctx.write_classification(
                prompt=prompt,
                response=response,
                parsed=parsed,
            )

    # Pass-through all other TickDiagnostics methods so the adapter can be used
    # anywhere tick_ctx is expected.
    def __getattr__(self, name: str) -> Any:
        return getattr(self._ctx, name)


@dataclass(frozen=True, slots=True)
class TickResult:
    """Result of one run_tick call. Discriminated via `kind`.

    Attributes:
        kind: One of "ok", "yielded", or "refused".
        tick_id: String tick identifier (monotonic from current_tick+1).
        observation: Grounded prose observation from the observer (ok/refused paths).
        yield_signal: Phase 4.1 locked YieldSignal contract (yielded path only).
        trace: Combined execution trace (ok path only).
        refusal_reason: Machine-readable reason code for refused path.
        projected_state: VisibilityProjector.project_for(actor) dict used during Observer
            synthesis (ok path only). None on yield/refuse paths (no observer call made).
            Exposed for Phase 6 Plan 05 TurnScorer groundedness metric (D-12 metric #2)
            without requiring private-attribute access to engine._projector.
    """

    kind: str  # "ok" | "yielded" | "refused"
    tick_id: str
    observation: str | None = None
    yield_signal: YieldSignal | None = None
    trace: ExecutionTrace | None = None
    refusal_reason: str | None = None
    projected_state: dict | None = None  # Phase 6 D-12: groundedness scoring surface

    @classmethod
    def ok(
        cls,
        *,
        tick_id: str,
        observation: str,
        trace: ExecutionTrace | None,
        projected_state: dict | None = None,
    ) -> TickResult:
        """Successful execute path result."""
        return cls(
            kind="ok",
            tick_id=tick_id,
            observation=observation,
            trace=trace,
            projected_state=projected_state,
        )

    @classmethod
    def yielded(cls, *, tick_id: str, signal: YieldSignal) -> TickResult:
        """No-match yield path result — Phase 4.1 operator takes over."""
        return cls(kind="yielded", tick_id=tick_id, yield_signal=signal)

    @classmethod
    def refused(
        cls, *, tick_id: str, observation: str, refusal_reason: str | None = None
    ) -> TickResult:
        """Classifier or conservation refusal path result."""
        return cls(
            kind="refused",
            tick_id=tick_id,
            observation=observation,
            refusal_reason=refusal_reason,
        )


class SimulationEngine:
    """Orchestrates one tick end-to-end (D-01).

    Single-agent v1 invariant (D-18): at most one resident-agent action per
    tick. Multi-agent turn ordering and conflict detection are deferred to v2.

    Args:
        universe_path: Root directory of the universe (contains mechanics/,
            diagnostics/, tick_summaries/, universe.yaml, conservation.yaml).
        graph: The KnowledgeGraph instance that is the simulation's ground truth.
        anthropic_client: An ``anthropic.Anthropic`` instance or test fake.
            Injected so both the Classifier (Haiku) and Observer (Sonnet) share
            the same client object.
        config: Optional pre-loaded EngineConfig. If None, loaded from
            universe_path/universe.yaml with soft-fail defaults (D-03).
    """

    def __init__(
        self,
        universe_path: Path,
        *,
        graph: KnowledgeGraph,
        anthropic_client: Any,
        config: EngineConfig | None = None,
    ) -> None:
        self._universe_path = Path(universe_path).resolve()
        self._graph = graph
        self._anthropic_client = anthropic_client
        self._config = config or load_engine_config(self._universe_path)
        self._registry = MechanicRegistry(self._universe_path / "mechanics")
        self._diagnostics = DiagnosticsSink(self._universe_path)
        self._classifier = Classifier(client=anthropic_client)
        self._observer = Observer(client=anthropic_client)
        self._matcher = DeterministicMatcher()
        self._projector = VisibilityProjector(self._graph)
        self._conservation = ConservationChecker.from_yaml(
            self._universe_path / "conservation.yaml"
        )
        self._summary_writer = TickSummaryWriter()
        self._compressor = TickCompressor(
            batch_size=self._config.compression_batch_size,
            epoch_size=self._config.compression_epoch_size,
        )
        self._long_running_hook = LongRunningHook()

    def has_active_long_action(self, actor: str) -> bool:
        """Return True iff the actor node has an active current_long_action dict (D-07, D-11).

        Used by PlaytestRunner to decide whether to skip agent.run_turn() for this tick.

        Args:
            actor: Node ID of the actor to check.

        Returns:
            True if actor exists and has a dict-typed current_long_action property.
        """
        if not self._graph.has_node(actor):
            return False
        try:
            lra = self._graph.query(actor, "current_long_action")
        except (KeyError, Exception):
            return False
        return isinstance(lra, dict)

    def run_tick(self, action_text: str | None, actor: str) -> TickResult:
        """Execute one tick through the complete D-01 staged pipeline.

        D-02: registry is re-scanned at the top of every call so that mechanics
        written by the operator after a YieldSignal are picked up automatically
        without restarting the engine.

        Phase 7 (D-07, D-11): action_text may be None to signal a long-running
        action continuation tick. When the actor has an active current_long_action:
        - action_text is None or empty → synthetic continuation (_handle_long_running_tick)
        - action_text is a real string → implicit LRA cancellation (D-11), then normal pipeline

        Returns a TickResult with kind "ok" | "yielded" | "refused".
        """
        # D-02: idempotent registry re-scan
        self._registry.scan()

        # Allocate tick_id (monotonic from graph.current_tick + 1)
        next_tick = self._graph.current_tick + 1
        self._graph.set_tick(next_tick)
        tick_id_str = str(next_tick)

        start_time = time.perf_counter()

        with self._diagnostics.open_tick(next_tick) as tick_ctx:
            # Pre-tick snapshot for conservation rollback (D-16)
            pre_tick_snapshot_id = self._graph.snapshot(next_tick, summary=f"pre-tick {next_tick}")

            # Persist raw action for diagnostics
            tick_ctx.write_action(action_text or "")

            # ------------------------------------------------------------------
            # Phase 7: Long-running action detection (D-07, D-11)
            # Runs BEFORE Stage 1 Classify to short-circuit when LRA is active.
            # ------------------------------------------------------------------
            if self.has_active_long_action(actor):
                if action_text is None or (
                    isinstance(action_text, str) and not action_text.strip()
                ):
                    # D-07: continuation — skip classify/match/decide entirely
                    return self._handle_long_running_tick(
                        actor=actor,
                        tick_id_str=tick_id_str,
                        tick_ctx=tick_ctx,
                        start_time=start_time,
                    )
                # D-11: implicit cancellation — clear LRA and proceed normally
                logger.debug(
                    "Implicit LRA cancellation for actor=%s by action_text=%r",
                    actor,
                    action_text,
                )
                self._graph.set(actor, "current_long_action", None)

            # action_text is guaranteed non-None here (continuation returned early)
            if action_text is None:
                # This branch is only reachable if actor has NO active LRA and
                # action_text is None — raise clearly rather than passing None
                # to the classifier.
                raise ValueError(
                    f"run_tick called with action_text=None but actor {actor!r} has no "
                    "active long-running action. Pass a string action or ensure the actor "
                    "has an active LRA."
                )

            # Classifier uses write_prompt/write_response/write_parsed API;
            # TickDiagnostics exposes write_classification. Adapt via a thin wrapper
            # (Rule 2 deviation — interface mismatch between Wave 1 classifier.py and
            # Phase 4 TickDiagnostics; neither file is in plan scope to modify).
            classifier_diag_ctx = _ClassifierDiagnosticsAdapter(tick_ctx)

            # ------------------------------------------------------------------
            # Stage 1: Classify
            # ------------------------------------------------------------------
            available_verbs = self._collect_available_verbs()
            known_node_ids = self._graph.nodes()

            verdict = self._classifier.classify(
                action_text,
                actor,
                available_verbs=available_verbs,
                known_node_ids=known_node_ids,
                min_confidence=self._config.classifier_min_confidence,
                tick_diag_ctx=classifier_diag_ctx,
            )

            classifier_in = getattr(self._classifier, "last_input_tokens", 0)
            classifier_out = getattr(self._classifier, "last_output_tokens", 0)

            # ------------------------------------------------------------------
            # Stage 2: Match (only when verdict is VerdictOk)
            # ------------------------------------------------------------------
            match_result = None
            if isinstance(verdict, VerdictOk):
                match_result = self._matcher.match(verdict.classified, self._registry, self._graph)
                tick_ctx.write_matching([match_result.model_dump()])

            # ------------------------------------------------------------------
            # Stage 3: Decide
            # ------------------------------------------------------------------
            decision = decide(verdict, match_result, action_text=action_text)

            # ------------------------------------------------------------------
            # Stage 4+: branch on Decision kind
            # ------------------------------------------------------------------
            if isinstance(decision, ExecuteDecision):
                return self._handle_execute(
                    decision=decision,
                    verdict=cast(VerdictOk, verdict),  # decide() only yields Execute for VerdictOk
                    actor=actor,
                    tick_id_str=tick_id_str,
                    next_tick=next_tick,
                    pre_tick_snapshot_id=pre_tick_snapshot_id,
                    tick_ctx=tick_ctx,
                    start_time=start_time,
                    classifier_in=classifier_in,
                    classifier_out=classifier_out,
                    action_text=action_text,
                )
            elif isinstance(decision, YieldDecision):
                return self._handle_yield(
                    decision=decision,
                    verdict=cast(VerdictOk, verdict),  # decide() only yields Yield for VerdictOk
                    actor=actor,
                    tick_id_str=tick_id_str,
                    tick_ctx=tick_ctx,
                    start_time=start_time,
                    classifier_in=classifier_in,
                    classifier_out=classifier_out,
                    action_text=action_text,
                )
            elif isinstance(decision, RefuseDecision):
                return self._handle_refuse(
                    decision=decision,
                    verdict=verdict,
                    tick_id_str=tick_id_str,
                    tick_ctx=tick_ctx,
                    start_time=start_time,
                    classifier_in=classifier_in,
                    classifier_out=classifier_out,
                    action_text=action_text,
                )
            else:
                tick_ctx.set_summary(
                    status="error",
                    error=f"Unhandled decision type: {type(decision).__name__}",
                )
                raise TypeError(f"Unhandled Decision type: {type(decision).__name__}")

    # =========================================================================
    # Path handlers
    # =========================================================================

    def _handle_execute(
        self,
        *,
        decision: ExecuteDecision,
        verdict: VerdictOk,
        actor: str,
        tick_id_str: str,
        next_tick: int,
        pre_tick_snapshot_id: int,
        tick_ctx: Any,
        start_time: float,
        classifier_in: int,
        classifier_out: int,
        action_text: str,
    ) -> TickResult:
        """Full execute path: ChainExecutionEngine → conservation → sweep → observe."""
        # Construct MechanicContext with seeded RNG (D-19)
        target_id = verdict.classified.target or actor
        ctx = MechanicContext(
            self._graph,
            actor=actor,
            target=target_id,
            tick_id=tick_id_str,
            universe_seed=self._config.universe_seed,
        )
        mechanic = self._registry.get_mechanic(decision.mechanic_id)

        # Execute primary chain (D-03: max_chain_depth from config)
        chain_engine = ChainExecutionEngine(
            involuntary_mechanics=self._registry.involuntary_mechanics(),
            max_depth=self._config.max_chain_depth,
        )
        try:
            primary_trace = chain_engine.execute(mechanic, ctx)
        except Exception as exc:
            logger.exception("ChainExecutionEngine raised during run_tick")
            tick_ctx.set_summary(status="error", error=str(exc))
            self._graph.restore(pre_tick_snapshot_id)
            error_narrative = RefusalTemplate.render(
                "mechanic_check_failed",
                {"reason": f"engine error: {exc.__class__.__name__}"},
            )
            self._write_summary(
                tick_id_str=tick_id_str,
                action_text=action_text,
                decision=RefuseDecision(
                    reason_code="engine_error",
                    details={"reason": str(exc)},
                ),
                classified=verdict.classified,
                trace=None,
                observation_text=error_narrative,
                start_time=start_time,
                classifier_in=classifier_in,
                classifier_out=classifier_out,
            )
            return TickResult.refused(
                tick_id=tick_id_str,
                observation=error_narrative,
                refusal_reason="engine_error",
            )

        # Write diagnostics: trace + mutations
        tick_ctx.write_execution_trace(_trace_to_dict(primary_trace))
        for mutation in collect_mutations(primary_trace):
            tick_ctx.append_mutation(_mutation_to_dict(mutation))

        # Conservation check on primary trace mutations (D-16)
        primary_mutations = collect_mutations(primary_trace)
        cons_verdict = self._conservation.verify(primary_mutations)
        if cons_verdict.is_violation:
            # restore() sets _current_tick = snapshot's tick_id = next_tick, so the
            # next run_tick call allocates next_tick + 1 — no tick-ID collision.
            # See: test_run_tick_consecutive_conservation_rollbacks_produce_distinct_tick_ids
            self._graph.restore(pre_tick_snapshot_id)
            violated = next(iter(cons_verdict.violations))
            narrative = RefusalTemplate.render(
                "conservation_violation",
                {"violated_property": violated},
            )
            tick_ctx.set_summary(
                status="conservation_violated",
                violated_property=violated,
                violations=cons_verdict.violations,
            )
            refuse_decision = RefuseDecision(
                reason_code="conservation_violation",
                details={"violated_property": violated},
            )
            self._write_summary(
                tick_id_str=tick_id_str,
                action_text=action_text,
                decision=refuse_decision,
                classified=verdict.classified,
                trace=primary_trace,
                observation_text=narrative,
                start_time=start_time,
                classifier_in=classifier_in,
                classifier_out=classifier_out,
            )
            return TickResult.refused(
                tick_id=tick_id_str,
                observation=narrative,
                refusal_reason="conservation_violation",
            )

        # Passive sweep (D-17) — runs AFTER primary chain, NOT on yield/refuse (pitfall #8)
        sweep_trace_nodes = self._run_passive_sweep(
            actor=actor,
            tick_id_str=tick_id_str,
            primary_mutations=primary_mutations,
        )

        # Combine all mutations (primary + sweep) for conservation + summary
        sweep_mutations = [m for node in sweep_trace_nodes for m in node.mutations]
        all_mutations = primary_mutations + sweep_mutations

        # Re-verify conservation across combined mutations (D-16 + D-17 chain)
        cons_verdict_with_sweep = self._conservation.verify(all_mutations)
        if cons_verdict_with_sweep.is_violation:
            # Same tick-ID invariant as above: restore() leaves _current_tick = next_tick,
            # so the subsequent run_tick call gets next_tick + 1 — no collision.
            self._graph.restore(pre_tick_snapshot_id)
            violated = next(iter(cons_verdict_with_sweep.violations))
            narrative = RefusalTemplate.render(
                "conservation_violation",
                {"violated_property": violated},
            )
            tick_ctx.set_summary(status="conservation_violated_in_sweep")
            refuse_decision = RefuseDecision(
                reason_code="conservation_violation",
                details={"violated_property": violated},
            )
            self._write_summary(
                tick_id_str=tick_id_str,
                action_text=action_text,
                decision=refuse_decision,
                classified=verdict.classified,
                trace=primary_trace,
                observation_text=narrative,
                start_time=start_time,
                classifier_in=classifier_in,
                classifier_out=classifier_out,
            )
            return TickResult.refused(
                tick_id=tick_id_str,
                observation=narrative,
                refusal_reason="conservation_violation",
            )

        # Combine traces: sweep nodes attached as additional children of root
        combined_trace = _trace_with_sweep(primary_trace, sweep_trace_nodes)

        # Stage 5: Observe (D-15 hard grounding via Plan 05-05 system prompt)
        projection = self._projector.project_for(actor)
        observation = self._observer.synthesize(
            projection=projection,
            trace=combined_trace,
            refusal_narrative=None,
            actor_id=actor,
            action_text=action_text,
            tick_diag_ctx=tick_ctx,
        )
        observer_in = getattr(self._observer, "last_input_tokens", 0)
        observer_out = getattr(self._observer, "last_output_tokens", 0)

        # Write tick summary (D-20) — after observer so observation_text is included
        self._write_summary(
            tick_id_str=tick_id_str,
            action_text=action_text,
            decision=decision,
            classified=verdict.classified,
            trace=combined_trace,
            observation_text=observation,
            start_time=start_time,
            classifier_in=classifier_in,
            classifier_out=classifier_out,
            observer_in=observer_in,
            observer_out=observer_out,
        )

        tick_ctx.set_summary(
            status="ok",
            action_text=action_text,
            decision_kind="execute",
            mechanic_id=decision.mechanic_id,
            mutation_count=len(all_mutations),
            observation_text=observation,
            yielded=False,
            refused=False,
        )

        return TickResult.ok(
            tick_id=tick_id_str,
            observation=observation,
            trace=combined_trace,
            projected_state=projection,
        )

    def _handle_yield(
        self,
        *,
        decision: YieldDecision,
        verdict: VerdictOk,
        actor: str,
        tick_id_str: str,
        tick_ctx: Any,
        start_time: float,
        classifier_in: int,
        classifier_out: int,
        action_text: str,
    ) -> TickResult:
        """Yield path: build YieldSignal per Phase 4.1 locked contract (D-07)."""
        # Construct classified_action dict with all required keys (target MUST be present)
        ca_dict = verdict.classified.model_dump()
        ca_dict.setdefault("target", None)
        ca_dict.setdefault("params", {})

        # Actor state snapshot from visibility projection
        actor_state = self._projector.project_for(actor).get(actor, {}).get("properties", {})

        signal = YieldSignal(
            tick_id=tick_id_str,
            universe_path=str(self._universe_path),
            action_text=action_text,
            classified_action=ca_dict,
            actor_state=dict(actor_state),
            candidate_mechanic_ids=list(decision.candidates),
        )
        # Validate before returning — surfaces Phase 4.1 D-07 contract drift here
        signal.validate()

        tick_ctx.set_summary(
            status="yielded",
            action_text=action_text,
            decision_kind="yield",
            yielded=True,
            refused=False,
            candidate_mechanic_ids=list(decision.candidates),
        )

        # Tick summary (D-20) — written even on yield path
        self._write_summary(
            tick_id_str=tick_id_str,
            action_text=action_text,
            decision=decision,
            classified=verdict.classified,
            trace=None,
            observation_text=None,
            start_time=start_time,
            classifier_in=classifier_in,
            classifier_out=classifier_out,
        )

        return TickResult.yielded(tick_id=tick_id_str, signal=signal)

    def _handle_refuse(
        self,
        *,
        decision: RefuseDecision,
        verdict: Any,
        tick_id_str: str,
        tick_ctx: Any,
        start_time: float,
        classifier_in: int,
        classifier_out: int,
        action_text: str,
    ) -> TickResult:
        """Refusal path: render narrative, write summary, return refused result."""
        narrative = RefusalTemplate.render(decision.reason_code, decision.details)
        tick_ctx.set_summary(
            status="refused",
            action_text=action_text,
            decision_kind="refuse",
            refused=True,
            yielded=False,
            refusal_reason=decision.reason_code,
        )
        # Classifier verdict may have no classified_action (no_viable_action, etc.)
        classified = verdict.classified if isinstance(verdict, VerdictOk) else None
        self._write_summary(
            tick_id_str=tick_id_str,
            action_text=action_text,
            decision=decision,
            classified=classified,
            trace=None,
            observation_text=narrative,
            start_time=start_time,
            classifier_in=classifier_in,
            classifier_out=classifier_out,
        )
        return TickResult.refused(
            tick_id=tick_id_str,
            observation=narrative,
            refusal_reason=decision.reason_code,
        )

    def _handle_long_running_tick(
        self,
        *,
        actor: str,
        tick_id_str: str,
        tick_ctx: Any,
        start_time: float,
    ) -> TickResult:
        """D-07: synthetic continuation tick for an active long-running action.

        Skips classifier/matcher/decider entirely. Calls LongRunningHook to advance
        turns_elapsed and evaluate thresholds, runs passive sweep so the world keeps
        changing (D-06), builds tick summary with the long_running_action D-17 field,
        and returns TickResult.ok.

        Pitfall 1: this method is ONLY called when the actor already has an active LRA
        on the graph. The tick that STARTED the LRA (via begin_long_action) goes through
        _handle_execute, not here — so the hook never fires on LRA-start tick.

        Pitfall 6: passive sweep runs AFTER the hook, so passive mechanics (decay,
        weather) still fire while the agent is sleeping/drunk/traveling.
        """
        # 1. Read attention_state from current LRA payload before projection
        lra = self._graph.query(actor, "current_long_action") or {}
        if not lra:
            # WR-03: LRA disappeared between has_active_long_action check and here.
            # This can happen if a passive mechanic cleared it in the same tick.
            # Log the event and fall through — hook will return HookResult.inactive().
            logger.warning(
                "LRA disappeared between has_active_long_action check and "
                "_handle_long_running_tick for actor=%s",
                actor,
            )
        raw_payload = lra.get("payload") if isinstance(lra, dict) else None
        payload: dict = raw_payload if isinstance(raw_payload, dict) else {}
        raw_attention = payload.get("attention_state")
        attention_state_pre: dict | None = (
            raw_attention if isinstance(raw_attention, dict) else None
        )

        # 2. Single projection call — reused for hook threshold evaluation (D-09)
        projection = self._projector.project_for(actor, attention_state=attention_state_pre)

        # 3. Run hook (advances turns_elapsed, evaluates thresholds, synthesises narrative)
        hook_result = self._long_running_hook.process(
            actor=actor,
            projection=projection,
            graph=self._graph,
            tick_id_str=tick_id_str,
            observer=self._observer,
            tick_diag_ctx=tick_ctx,
        )

        # 4. Run passive sweep — world still changes while agent is in LRA (D-06, Pitfall 6)
        sweep_nodes = self._run_passive_sweep(
            actor=actor,
            tick_id_str=tick_id_str,
            primary_mutations=[],
        )
        sweep_mutations = [m for node in sweep_nodes for m in node.mutations]
        if sweep_mutations:
            cons_verdict = self._conservation.verify(sweep_mutations)
            if cons_verdict.is_violation:
                # Conservation violations in sweep during LRA ticks: log warning and
                # continue — restoring the snapshot here would also undo the LRA's
                # turns_elapsed increment, causing incorrect bookkeeping.
                violated = next(iter(cons_verdict.violations))
                logger.warning(
                    "Conservation violation in passive sweep during LRA tick %s "
                    "(violated_property=%s); not restoring (LRA tick semantics)",
                    tick_id_str,
                    violated,
                )

        # 5. Build long_running_action summary field (D-17)
        # Use post-hook state from graph if hook is still continuing; otherwise
        # compute from pre-hook lra dict (hook cleared it on interrupt/complete).
        post_lra = (
            self._graph.query(actor, "current_long_action") if self._graph.has_node(actor) else None
        )
        if hook_result.interrupted or hook_result.completed:
            # LRA was cleared: report the state at the moment it ended
            turns_elapsed_for_summary = int(lra.get("turns_elapsed", 0) or 0) + 1
            turns_total_for_summary = lra.get("turns_total")
        elif isinstance(post_lra, dict):
            turns_elapsed_for_summary = int(post_lra.get("turns_elapsed", 0) or 0)
            turns_total_for_summary = post_lra.get("turns_total")
        else:
            turns_elapsed_for_summary = 0
            turns_total_for_summary = None

        long_running_action_field: dict = {
            "active": True,
            "turns_elapsed": turns_elapsed_for_summary,
            "turns_total": turns_total_for_summary,
            "threshold_fired": (
                {
                    "property": hook_result.fired_threshold.property,
                    "op": hook_result.fired_threshold.op,
                    "value": hook_result.fired_threshold.value,
                }
                if hook_result.fired_threshold is not None
                else None
            ),
            "interrupted": hook_result.interrupted,
        }

        # Synthetic ExecuteDecision for build_tick_summary's decision dispatch
        synthetic_decision = ExecuteDecision(mechanic_id="continue_long_action")

        observer_in = getattr(self._observer, "last_input_tokens", 0) or 0
        observer_out = getattr(self._observer, "last_output_tokens", 0) or 0

        self._write_summary(
            tick_id_str=tick_id_str,
            action_text="[long_running_continuation]",
            decision=synthetic_decision,
            classified=None,
            trace=None,
            observation_text=hook_result.observation,
            start_time=start_time,
            classifier_in=0,
            classifier_out=0,
            observer_in=observer_in,
            observer_out=observer_out,
            long_running_action=long_running_action_field,
        )

        tick_ctx.set_summary(
            status="ok",
            action_text="[long_running_continuation]",
            decision_kind="execute",
            mechanic_id="continue_long_action",
            mutation_count=0,
            observation_text=hook_result.observation,
            yielded=False,
            refused=False,
            long_running_action=long_running_action_field,
        )

        return TickResult.ok(
            tick_id=tick_id_str,
            observation=hook_result.observation or "",
            trace=None,
            projected_state=projection,
        )

    # =========================================================================
    # Helpers
    # =========================================================================

    def _collect_available_verbs(self) -> list[str]:
        """Collect verb strings from VerbMatcher in voluntary mechanics' watches()."""
        verbs: set[str] = set()
        for mech in self._registry.voluntary_mechanics():
            for matcher in mech.watches():
                if isinstance(matcher, VerbMatcher):
                    verbs.add(matcher.verb)
        return sorted(verbs)

    def _ensure_sentinel(self) -> str:
        """Idempotently create the engine tick sentinel agent node (D-17)."""
        if not self._graph.has_node(_SENTINEL_NODE_ID):
            self._graph.add_node(_SENTINEL_NODE_ID, node_type="agent", _system=True)
        return _SENTINEL_NODE_ID

    def _run_passive_sweep(
        self,
        *,
        actor: str,
        tick_id_str: str,
        primary_mutations: list,
    ) -> list[TraceNode]:
        """Iterate involuntary mechanics and fire TickMatcher / DecayMatcher /
        WorldPropertyMatcher mechanics (D-17).

        Each mechanic is invoked AT MOST ONCE per sweep call (T-05-ORCH-PASSIVE-LOOP
        mitigation). Sweep mutations do NOT trigger a re-sweep.

        Mechanic contract for DecayMatcher: the mechanic receives the sentinel as
        actor/target and its own check()/apply() iterates graph nodes with
        decay_period via ctx.find_nodes().
        """
        sentinel = self._ensure_sentinel()
        sweep_nodes: list[TraceNode] = []

        for mech in self._registry.involuntary_mechanics():
            mech_matchers = mech.watches()
            should_fire = False

            for matcher in mech_matchers:
                if isinstance(matcher, TickMatcher):
                    # Always fires once per tick
                    should_fire = True
                    break
                if isinstance(matcher, DecayMatcher):
                    # Fires once per tick; the mechanic iterates decay nodes internally
                    should_fire = True
                    break
                if isinstance(matcher, WorldPropertyMatcher):
                    # Fires only if this tick produced a set_property on _world for this property.
                    # NOTE: the Phase 2 matches() helper does NOT dispatch WorldPropertyMatcher
                    # (it only handles PropertyChangeMatcher/EdgeMatcher/NodeMatcher). Use the
                    # Phase 5 matcher's own .match(mutation) method directly.
                    for mutation in primary_mutations:
                        if matcher.match(mutation):
                            should_fire = True
                            break
                    if should_fire:
                        break

            if not should_fire:
                continue

            sweep_ctx = MechanicContext(
                self._graph,
                actor=sentinel,
                target=sentinel,
                tick_id=tick_id_str,
                universe_seed=self._config.universe_seed,
            )
            check = mech.check(sweep_ctx)
            if not check.passed:
                # Record refused sweep mechanic in trace for diagnostics
                sweep_nodes.append(
                    TraceNode(
                        mechanic_id=mech.id,
                        actor=sentinel,
                        target=sentinel,
                        check_result=check,
                        mutations=[],
                    )
                )
                continue

            try:
                mutations = mech.apply(sweep_ctx)
            except Exception as exc:
                logger.warning("Passive sweep mechanic %s raised: %s", mech.id, exc)
                sweep_nodes.append(
                    TraceNode(
                        mechanic_id=mech.id,
                        actor=sentinel,
                        target=sentinel,
                        check_result=check,
                        mutations=[],
                    )
                )
                continue

            sweep_nodes.append(
                TraceNode(
                    mechanic_id=mech.id,
                    actor=sentinel,
                    target=sentinel,
                    check_result=check,
                    mutations=mutations,
                )
            )

        return sweep_nodes

    def _write_summary(
        self,
        *,
        tick_id_str: str,
        action_text: str,
        decision: Decision,
        classified: ClassifiedAction | None,
        trace: ExecutionTrace | None,
        observation_text: str | None,
        start_time: float,
        classifier_in: int,
        classifier_out: int,
        observer_in: int = 0,
        observer_out: int = 0,
        long_running_action: dict | None = None,
    ) -> None:
        """Build and persist the per-tick tick_summary JSON (D-20)."""
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        summary = build_tick_summary(
            tick_id=tick_id_str,
            action_text=action_text,
            decision=decision,
            classified_action=classified.model_dump() if classified is not None else None,
            trace=trace,
            observation_text=observation_text,
            duration_ms=duration_ms,
            classifier_input_tokens=classifier_in,
            classifier_output_tokens=classifier_out,
            observer_input_tokens=observer_in,
            observer_output_tokens=observer_out,
            long_running_action=long_running_action,
        )
        self._summary_writer.write(summary, self._universe_path)
        # D-19: opportunistic compression after every tick write.
        # Failures MUST NOT cause the tick itself to fail — compression is best-effort.
        try:
            self._compressor.maybe_compress(self._universe_path, self._anthropic_client)
        except Exception as exc:
            logger.warning("TickCompressor failed (tick still succeeded): %s", exc)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _trace_with_sweep(primary: ExecutionTrace, sweep_nodes: list[TraceNode]) -> ExecutionTrace:
    """Return a new ExecutionTrace with sweep_nodes appended as children of root.

    Constructs a new root TraceNode (does not mutate the original) so consumers
    that hold a reference to the original trace are unaffected.
    """
    new_root = TraceNode(
        mechanic_id=primary.root.mechanic_id,
        actor=primary.root.actor,
        target=primary.root.target,
        check_result=primary.root.check_result,
        mutations=primary.root.mutations,
        children=primary.root.children + sweep_nodes,
    )
    return ExecutionTrace(
        root=new_root,
        total_mechanics_executed=primary.total_mechanics_executed + len(sweep_nodes),
        max_depth_reached=primary.max_depth_reached,
        truncated=primary.truncated,
    )


def _trace_to_dict(trace: ExecutionTrace) -> dict:
    """Serialise an ExecutionTrace to a JSON-friendly dict for diagnostics."""

    def node_to_dict(n: TraceNode) -> dict:
        return {
            "mechanic_id": n.mechanic_id,
            "actor": n.actor,
            "target": n.target,
            "check_passed": n.check_result.passed,
            "check_reasons": list(n.check_result.reasons),
            "mutations": [_mutation_to_dict(m) for m in n.mutations],
            "children": [node_to_dict(c) for c in n.children],
        }

    return {
        "root": node_to_dict(trace.root),
        "total_mechanics_executed": trace.total_mechanics_executed,
        "max_depth_reached": trace.max_depth_reached,
        "truncated": trace.truncated,
    }


def _mutation_to_dict(m: Any) -> dict:
    """Convert a Mutation to a JSON-friendly dict."""
    return {
        "type": m.type,
        "target": m.target,
        "property": m.property,
        "old_value": m.old_value,
        "new_value": m.new_value,
    }
