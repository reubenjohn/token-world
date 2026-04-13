"""Phase 7 Long-Running Action primitives (D-01, D-03, D-09, D-13, D-15, D-16, D-19, D-23).

Pure-Python frozen dataclasses + pure-function evaluator. Zero dependency on
KnowledgeGraph, VisibilityProjector, Anthropic SDK, or any engine stage. The engine
hook (Plan 04) and seed mechanics (Plans 05-07) consume these primitives.

Key design decisions:
- D-01: All consciousness states (sleep, drunk, autopilot travel) are long-running actions.
- D-03: Thresholds are declarative dicts; operators: >, >=, <, <=, ==, !=.
- D-09: Threshold evaluation against VisibilityProjector output (dot-notation paths).
- D-13: turns_total=None means indefinite duration (drunkenness, lingering states).
- D-15: This module is the single source of truth for threshold + action primitives.
- D-16: turns_total=None never auto-expires; turns_elapsed still advances each tick.
- D-19: ThresholdSpec field names exactly: property, op, value.
- D-23: Frozen dataclasses (not Pydantic), consistent with YieldSignal, Mutation, SnapshotInfo.

Serialization boundary: in-memory thresholds are tuple[ThresholdSpec, ...] (frozen,
hashable); on-graph they serialize as list[dict] per ALLOWED_PROPERTY_TYPES (tuple is
not in ALLOWED_PROPERTY_TYPES; json.dumps/loads converts to list).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ThresholdSpec:
    """Declarative threshold specification (D-03, D-19).

    A threshold fires when projection[node_id]['properties'][prop_name] satisfies
    the comparison `actual <op> value`. Operators are enforced by ThresholdEvaluator,
    not by this dataclass — ThresholdSpec is a pure data carrier (D-19).

    Attributes:
        property: Dot-notation path "<node_id>.<prop_name>" (D-09).
        op: Comparison operator string; one of >, >=, <, <=, ==, != (D-03).
        value: Threshold value (must be JSON-serializable when used in LongRunningAction).
    """

    property: str
    op: str
    value: Any


@dataclass(frozen=True, slots=True)
class LongRunningAction:
    """Multi-tick interruptible action state stored on actor graph node (D-02, D-13, D-16, D-23).

    Stored as `current_long_action` dict on the actor node via kg.set(). Serialized to
    dict via to_dict() for graph storage (tuple → list, ThresholdSpec → dict). Reconstructed
    via from_dict() when read back from the graph.

    Attributes:
        action_text: Human-readable description of the ongoing action.
        turns_total: Maximum turns for this action; None = indefinite (D-16).
        turns_elapsed: How many ticks have passed since action started.
        thresholds: Interruption conditions (D-03). Stored as tuple for immutability;
            serialized as list[dict] for graph storage (ALLOWED_PROPERTY_TYPES).
        payload: Mechanic-specific extra data. attention_state lives here (D-12).
    """

    action_text: str
    turns_total: int | None
    turns_elapsed: int
    thresholds: tuple[ThresholdSpec, ...]
    payload: dict

    def to_dict(self) -> dict:
        """Serialize to a JSON-serializable plain dict for graph storage (D-02).

        Thresholds tuple becomes list[dict] to satisfy ALLOWED_PROPERTY_TYPES.
        turns_total=None is preserved as None (JSON null).
        """
        return {
            "action_text": self.action_text,
            "turns_total": self.turns_total,
            "turns_elapsed": self.turns_elapsed,
            "thresholds": [
                {"property": t.property, "op": t.op, "value": t.value} for t in self.thresholds
            ],
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, d: dict) -> LongRunningAction:
        """Reconstruct from a graph-stored dict (inverse of to_dict).

        Converts list of threshold dicts back to tuple[ThresholdSpec, ...].
        turns_total=None (JSON null) is preserved as None.
        Missing payload defaults to {}.
        """
        thresholds = tuple(
            ThresholdSpec(
                property=t["property"],
                op=t["op"],
                value=t["value"],
            )
            for t in d.get("thresholds", [])
        )
        return cls(
            action_text=d["action_text"],
            turns_total=d.get("turns_total"),
            turns_elapsed=d.get("turns_elapsed", 0),
            thresholds=thresholds,
            payload=dict(d.get("payload", {})),
        )


class ThresholdEvaluator:
    """Pure-function evaluator for declarative threshold dicts (D-03, D-09).

    Stateless. Takes a list of threshold dicts and a projection dict and
    returns the first firing ThresholdSpec, or None if none fire. All
    error modes (missing node, missing prop, unknown op, type mismatch)
    return None per D-09 safe defaults — never raises.

    Evaluates against VisibilityProjector output shape:
        {
            "<node_id>": {
                "type": "entity" | "agent",
                "properties": {"<prop_name>": <value>, ...},
                "edges": [...],
            },
            ...
        }

    Property path format: "<node_id>.<prop_name>" (D-09). Only single-level paths
    are supported in v1 (str.partition splits on first dot only).
    """

    _OPS: dict[str, Callable[[Any, Any], bool]] = {
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }

    @classmethod
    def evaluate(
        cls,
        thresholds: list[dict],
        projection: dict,
    ) -> ThresholdSpec | None:
        """Return the first firing ThresholdSpec, or None if none fire.

        Args:
            thresholds: List of threshold dicts with keys property, op, value.
            projection: VisibilityProjector output dict keyed by node_id.

        Returns:
            The first ThresholdSpec whose condition is satisfied, or None.
        """
        for spec_dict in thresholds:
            try:
                spec = ThresholdSpec(
                    property=spec_dict["property"],
                    op=spec_dict["op"],
                    value=spec_dict["value"],
                )
            except KeyError:
                continue  # malformed spec: skip, no fire (D-09 safe default)
            if cls._evaluate_one(spec, projection):
                return spec
        return None

    @classmethod
    def _evaluate_one(cls, spec: ThresholdSpec, projection: dict) -> bool:
        """Evaluate a single ThresholdSpec against the projection.

        Returns False (not None) on all error paths — D-09 safe default.
        """
        node_id, sep, prop_name = spec.property.partition(".")
        if not sep:
            return False  # no dot separator: malformed path
        node_entry = projection.get(node_id)
        if not isinstance(node_entry, dict):
            return False  # missing node
        props = node_entry.get("properties")
        if not isinstance(props, dict):
            return False
        if prop_name not in props:
            return False  # missing property
        actual = props[prop_name]
        if actual is None:
            return False  # None property does not fire
        op_fn = cls._OPS.get(spec.op)
        if op_fn is None:
            return False  # unknown operator
        try:
            return bool(op_fn(actual, spec.value))
        except TypeError:
            return False  # type mismatch (D-09 safe default)
