"""TickSummaryWriter — persist per-tick structured summaries (D-20, SIM-11).

Writes universe/tick_summaries/ticks/tick_<id>.json after every run_tick.
The TickSummary Pydantic schema lives in :mod:`token_world.engine.models`
(defined by Plan 05-01); this module adds the writer and the orchestrator-facing
``build_tick_summary`` factory that turns raw stage outputs into a TickSummary.

Forward-compatibility (D-21): schema_version=1 declared in every file. Phase 6
SIM-12 batch compressor consumes these files; the schema is locked.

Cost accounting (D-24): per-stage USD costs computed from token usage and
hardcoded model-rate constants. Operator audits via the JSON files; Phase 5
ships no circuit breakers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from token_world.engine.models import (
    ExecuteDecision,
    RefuseDecision,
    TickSummary,
    YieldDecision,
)
from token_world.graph import Mutation
from token_world.mechanic.diagnostics import _atomic_write_json
from token_world.mechanic.trace import ExecutionTrace, TraceNode

# Per-million-token USD rates — D-24 visibility, no circuit breaker.
# Adjust in source if Anthropic pricing changes; verify in tests then bump.
_HAIKU_INPUT_PER_MTOK = 1.00
_HAIKU_OUTPUT_PER_MTOK = 5.00
_SONNET_INPUT_PER_MTOK = 3.00
_SONNET_OUTPUT_PER_MTOK = 15.00


def _stage_cost_usd(stage: str, input_tokens: int, output_tokens: int) -> float:
    """Compute USD cost for a stage's token usage.

    Args:
        stage: Pipeline stage name ("classifier" uses Haiku rates,
            "observer" uses Sonnet rates, unknown stages return 0.0).
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.

    Returns:
        Estimated USD cost as a float.
    """
    if stage == "classifier":
        in_rate, out_rate = _HAIKU_INPUT_PER_MTOK, _HAIKU_OUTPUT_PER_MTOK
    elif stage == "observer":
        in_rate, out_rate = _SONNET_INPUT_PER_MTOK, _SONNET_OUTPUT_PER_MTOK
    else:
        # Unknown stage: zero cost (forward-compat for future stages)
        return 0.0
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000


def _flatten_trace_mutations(trace: ExecutionTrace | None) -> list[Mutation]:
    """Walk trace tree and collect every Mutation recorded by every TraceNode.

    Args:
        trace: The execution trace, or None (yield/refuse path with no mechanic).

    Returns:
        Flat list of all Mutations from all nodes in the trace tree.
    """
    if trace is None:
        return []
    result: list[Mutation] = []
    stack: list[TraceNode] = [trace.root]
    while stack:
        node = stack.pop()
        result.extend(node.mutations)
        stack.extend(node.children)
    return result


def _mutations_to_json_list(mutations: list[Mutation]) -> list[list[Any]]:
    """Convert Mutations to D-20 4-tuple form: [target, property, old, new].

    Args:
        mutations: List of Mutation dataclass instances.

    Returns:
        List of 4-element lists suitable for JSON serialisation.
    """
    return [[m.target, m.property, m.old_value, m.new_value] for m in mutations]


def build_tick_summary(
    *,
    tick_id: str,
    action_text: str,
    decision: ExecuteDecision | YieldDecision | RefuseDecision,
    classified_action: dict[str, Any] | None,
    trace: ExecutionTrace | None,
    observation_text: str | None,
    duration_ms: int,
    classifier_input_tokens: int = 0,
    classifier_output_tokens: int = 0,
    observer_input_tokens: int = 0,
    observer_output_tokens: int = 0,
) -> TickSummary:
    """Construct a TickSummary from orchestrator-raw stage outputs.

    Switches on Decision.kind:
        - ExecuteDecision: matched_mechanic_id, observation_text, mutations populated
        - YieldDecision:   yielded=True, matched/observation/refusal_reason all None
        - RefuseDecision:  refused=True, refusal_reason=decision.reason_code

    Args:
        tick_id: Unique tick identifier (engine-internal, not agent-supplied).
        action_text: Raw free-form action text from the resident agent.
        decision: The orchestrator decision (execute / yield / refuse).
        classified_action: Structured action dict from the classifier, or None.
        trace: Execution trace from ChainExecutionEngine, or None.
        observation_text: Synthesised observation from Observer, or None.
        duration_ms: Total tick duration in milliseconds.
        classifier_input_tokens: Input tokens consumed by the classifier stage.
        classifier_output_tokens: Output tokens from the classifier stage.
        observer_input_tokens: Input tokens consumed by the observer stage.
        observer_output_tokens: Output tokens from the observer stage.

    Returns:
        A fully-populated TickSummary instance ready for serialisation.
    """
    yielded = isinstance(decision, YieldDecision)
    refused = isinstance(decision, RefuseDecision)
    matched_id = decision.mechanic_id if isinstance(decision, ExecuteDecision) else None
    refusal_reason = decision.reason_code if isinstance(decision, RefuseDecision) else None

    raw_mutations = _flatten_trace_mutations(trace)
    mutations_field: dict[str, Any] = {
        "count": len(raw_mutations),
        "list": _mutations_to_json_list(raw_mutations),
    }

    tokens_by_stage: dict[str, dict[str, int]] = {
        "classifier": {"in": classifier_input_tokens, "out": classifier_output_tokens},
        "observer": {"in": observer_input_tokens, "out": observer_output_tokens},
    }
    cost_by_stage: dict[str, float] = {
        "classifier": _stage_cost_usd(
            "classifier", classifier_input_tokens, classifier_output_tokens
        ),
        "observer": _stage_cost_usd("observer", observer_input_tokens, observer_output_tokens),
    }

    return TickSummary(
        tick_id=tick_id,
        timestamp_iso=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        action_text=action_text,
        classified_action=classified_action,
        matched_mechanic_id=matched_id,
        yielded=yielded,
        refused=refused,
        refusal_reason=refusal_reason,
        mutations=mutations_field,
        observation_text=observation_text,
        duration_ms=duration_ms,
        llm_tokens_by_stage=tokens_by_stage,
        llm_cost_usd_by_stage=cost_by_stage,
    )


@dataclass(slots=True)
class TickSummaryWriter:
    """Persist a TickSummary to universe/tick_summaries/ticks/tick_<id>.json.

    Stateless: instantiate once, call :meth:`write` any number of times.
    Uses the Phase 4 :func:`~token_world.mechanic.diagnostics._atomic_write_json`
    helper for crash-safe atomic writes (T-05-SUMMARY-PARTIAL-WRITE mitigation).
    """

    def write(self, summary: TickSummary, universe_dir: Path) -> Path:
        """Write the summary; return the resolved file path.

        Idempotent: same tick_id → same path → atomic overwrite. Creates
        tick_summaries/ticks/ if missing (mkdir parents). Uses the Phase 4
        atomic-write helper so partial writes are never observed by readers.

        Args:
            summary: The TickSummary to persist.
            universe_dir: Root of the universe directory (contains mechanics/,
                diagnostics/, tick_summaries/, etc.).

        Returns:
            The path of the written file.

        Raises:
            OSError: If the file cannot be written (propagated from
                :func:`_atomic_write_json`). Caller sees the error; no silent
                swallowing.
        """
        out_dir = universe_dir / "tick_summaries" / "ticks"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"tick_{summary.tick_id}.json"
        # Pydantic → JSON-safe dict via model_dump_json roundtrip.
        # model_dump_json handles Literal[1] schema_version correctly; plain
        # model_dump() may return Python-specific types if fields are extended.
        _atomic_write_json(out_path, json.loads(summary.model_dump_json()))
        return out_path
