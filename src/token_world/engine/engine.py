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
from token_world.engine.config import EngineConfig, load_engine_config
from token_world.engine.conservation import ConservationChecker
from token_world.engine.decider import decide
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
from token_world.mechanic.trace import ExecutionTrace, TraceNode
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
    """

    kind: str  # "ok" | "yielded" | "refused"
    tick_id: str
    observation: str | None = None
    yield_signal: YieldSignal | None = None
    trace: ExecutionTrace | None = None
    refusal_reason: str | None = None

    @classmethod
    def ok(cls, *, tick_id: str, observation: str, trace: ExecutionTrace) -> TickResult:
        """Successful execute path result."""
        return cls(kind="ok", tick_id=tick_id, observation=observation, trace=trace)

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

    def run_tick(self, action_text: str, actor: str) -> TickResult:
        """Execute one tick through the complete D-01 staged pipeline.

        D-02: registry is re-scanned at the top of every call so that mechanics
        written by the operator after a YieldSignal are picked up automatically
        without restarting the engine.

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
            tick_ctx.write_action(action_text)

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
        for mutation in _flatten_mutations(primary_trace):
            tick_ctx.append_mutation(_mutation_to_dict(mutation))

        # Conservation check on primary trace mutations (D-16)
        primary_mutations = _flatten_mutations(primary_trace)
        cons_verdict = self._conservation.verify(primary_mutations)
        if cons_verdict.is_violation:
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

        return TickResult.ok(tick_id=tick_id_str, observation=observation, trace=combined_trace)

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
        )
        self._summary_writer.write(summary, self._universe_path)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _flatten_mutations(trace: ExecutionTrace | None) -> list:
    """Walk a trace tree and return all Mutations across primary + chain children."""
    if trace is None:
        return []
    out = []
    stack = [trace.root]
    while stack:
        node = stack.pop()
        out.extend(node.mutations)
        stack.extend(node.children)
    return out


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
