"""Tests for Phase 7 long-running action primitives.

Covers:
- ThresholdSpec frozen dataclass (D-19, D-23)
- LongRunningAction frozen dataclass with to_dict/from_dict (D-02, D-16, D-23)
- ThresholdEvaluator pure-function evaluator (D-03, D-09)
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from token_world.engine.long_running import (
    LongRunningAction,
    ThresholdEvaluator,
    ThresholdSpec,
)
from token_world.graph.models import ALLOWED_PROPERTY_TYPES

# ---------------------------------------------------------------------------
# Task 1: ThresholdSpec + LongRunningAction dataclasses
# ---------------------------------------------------------------------------


class TestThresholdSpec:
    def test_threshold_spec_is_frozen(self):
        """ThresholdSpec is a frozen dataclass — mutation raises FrozenInstanceError."""
        spec = ThresholdSpec(property="room.noise_level", op=">", value=0.7)
        with pytest.raises(FrozenInstanceError):
            spec.property = "other"  # type: ignore[misc]

    def test_threshold_spec_fields(self):
        """ThresholdSpec has exactly property, op, value fields."""
        spec = ThresholdSpec(property="alice.health", op=">=", value=0.5)
        assert spec.property == "alice.health"
        assert spec.op == ">="
        assert spec.value == 0.5

    def test_threshold_spec_allows_any_op_at_construction(self):
        """Construction does not validate op — evaluator is the enforcement point (D-19)."""
        spec = ThresholdSpec(property="x.y", op="~=", value=1)
        assert spec.op == "~="

    def test_threshold_spec_equality(self):
        """Two ThresholdSpec with same fields compare equal (frozen dataclass default)."""
        a = ThresholdSpec(property="room.noise_level", op=">", value=0.7)
        b = ThresholdSpec(property="room.noise_level", op=">", value=0.7)
        assert a == b


class TestLongRunningAction:
    def _make_action(self, **overrides):
        defaults = dict(
            action_text="sleeping",
            turns_total=8,
            turns_elapsed=0,
            thresholds=(ThresholdSpec(property="room.noise_level", op=">", value=0.7),),
            payload={},
        )
        defaults.update(overrides)
        return LongRunningAction(**defaults)

    def test_long_running_action_is_frozen(self):
        """LongRunningAction is a frozen dataclass."""
        action = self._make_action()
        with pytest.raises(FrozenInstanceError):
            action.turns_elapsed = 3  # type: ignore[misc]

    def test_long_running_action_equality(self):
        """Two instances with equal fields compare equal."""
        a = self._make_action()
        b = self._make_action()
        assert a == b

    def test_to_dict_structure(self):
        """to_dict returns a dict with exactly the expected keys."""
        action = self._make_action()
        d = action.to_dict()
        assert set(d.keys()) == {
            "action_text",
            "turns_total",
            "turns_elapsed",
            "thresholds",
            "payload",
        }

    def test_to_dict_thresholds_is_list_of_dicts(self):
        """to_dict produces thresholds as list[dict], not tuple or ThresholdSpec (D-02)."""
        action = self._make_action()
        d = action.to_dict()
        assert isinstance(d["thresholds"], list)
        assert len(d["thresholds"]) == 1
        assert isinstance(d["thresholds"][0], dict)
        assert set(d["thresholds"][0].keys()) == {"property", "op", "value"}

    def test_to_dict_turns_total_none_preserved(self):
        """to_dict preserves turns_total=None (D-16 indefinite)."""
        action = self._make_action(turns_total=None)
        d = action.to_dict()
        assert d["turns_total"] is None

    def test_to_dict_passes_allowed_property_types(self):
        """Every value in to_dict output is an ALLOWED_PROPERTY_TYPES instance."""
        action = self._make_action(
            thresholds=(ThresholdSpec(property="room.noise_level", op=">", value=0.7),),
            payload={"attention_state": {"suppress": ["x"], "boost": ["y"]}},
        )
        d = action.to_dict()
        # Top-level dict
        assert isinstance(d, dict)
        # action_text
        assert isinstance(d["action_text"], ALLOWED_PROPERTY_TYPES)
        # turns_total: int or None
        assert d["turns_total"] is None or isinstance(d["turns_total"], int)
        # turns_elapsed: int
        assert isinstance(d["turns_elapsed"], int)
        # thresholds: list
        assert isinstance(d["thresholds"], list)
        for t in d["thresholds"]:
            assert isinstance(t, dict)
            for v in t.values():
                assert isinstance(v, ALLOWED_PROPERTY_TYPES)
        # payload: dict
        assert isinstance(d["payload"], dict)

    def test_from_dict_reconstructs(self):
        """to_dict -> from_dict returns an equal instance."""
        action = self._make_action()
        reconstructed = LongRunningAction.from_dict(action.to_dict())
        assert reconstructed == action

    def test_from_dict_converts_thresholds_list_to_tuple(self):
        """from_dict converts the list of threshold dicts back to tuple[ThresholdSpec, ...]."""
        action = self._make_action()
        d = action.to_dict()
        reconstructed = LongRunningAction.from_dict(d)
        assert isinstance(reconstructed.thresholds, tuple)
        assert all(isinstance(t, ThresholdSpec) for t in reconstructed.thresholds)

    def test_json_roundtrip_turns_total_none(self):
        """JSON roundtrip preserves turns_total=None (D-16 indefinite duration)."""
        action = self._make_action(turns_total=None)
        d = action.to_dict()
        serialized = json.dumps(d)
        reconstructed = LongRunningAction.from_dict(json.loads(serialized))
        assert reconstructed == action
        assert reconstructed.turns_total is None

    def test_json_roundtrip_turns_total_int(self):
        """JSON roundtrip preserves turns_total=8."""
        action = self._make_action(turns_total=8)
        reconstructed = LongRunningAction.from_dict(json.loads(json.dumps(action.to_dict())))
        assert reconstructed == action
        assert reconstructed.turns_total == 8

    def test_json_roundtrip_empty_thresholds(self):
        """JSON roundtrip works with zero thresholds."""
        action = self._make_action(thresholds=())
        reconstructed = LongRunningAction.from_dict(json.loads(json.dumps(action.to_dict())))
        assert reconstructed == action
        assert reconstructed.thresholds == ()

    def test_json_roundtrip_with_payload_attention_state(self):
        """JSON roundtrip preserves complex attention_state in payload."""
        action = self._make_action(
            payload={
                "attention_state": {
                    "suppress": ["visual_detail", "smell"],
                    "boost": ["noise_level"],
                }
            }
        )
        reconstructed = LongRunningAction.from_dict(json.loads(json.dumps(action.to_dict())))
        assert reconstructed == action
        assert reconstructed.payload["attention_state"]["suppress"] == ["visual_detail", "smell"]

    def test_json_roundtrip_multiple_thresholds(self):
        """JSON roundtrip with two ThresholdSpec objects."""
        action = self._make_action(
            thresholds=(
                ThresholdSpec(property="room.noise_level", op=">", value=0.7),
                ThresholdSpec(property="alice.health", op="<", value=0.2),
            )
        )
        reconstructed = LongRunningAction.from_dict(json.loads(json.dumps(action.to_dict())))
        assert reconstructed == action
        assert len(reconstructed.thresholds) == 2

    def test_from_dict_missing_payload_defaults_to_empty(self):
        """from_dict with no payload key defaults to {}."""
        d = {
            "action_text": "wandering",
            "turns_total": 3,
            "turns_elapsed": 1,
            "thresholds": [],
        }
        action = LongRunningAction.from_dict(d)
        assert action.payload == {}


# ---------------------------------------------------------------------------
# Task 2: ThresholdEvaluator
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_projection() -> dict:
    """Sample VisibilityProjector output for evaluator tests."""
    return {
        "bedroom": {
            "type": "entity",
            "properties": {"noise_level": 0.3, "illumination": 0.8},
            "edges": [],
        },
        "alice": {
            "type": "agent",
            "properties": {"health": 0.9, "energy": 0.4},
            "edges": [],
        },
    }


class TestThresholdEvaluator:
    def test_evaluate_empty_thresholds_returns_none(self, sample_projection):
        """Empty threshold list always returns None."""
        result = ThresholdEvaluator.evaluate([], sample_projection)
        assert result is None

    @pytest.mark.parametrize(
        "op,prop,threshold_value,expected_fire",
        [
            # noise_level is 0.3
            (">", "bedroom.noise_level", 0.2, True),  # 0.3 > 0.2
            (">", "bedroom.noise_level", 0.3, False),  # 0.3 > 0.3 is False
            (">=", "bedroom.noise_level", 0.3, True),  # 0.3 >= 0.3
            (">=", "bedroom.noise_level", 0.4, False),  # 0.3 >= 0.4 is False
            ("<", "bedroom.noise_level", 0.4, True),  # 0.3 < 0.4
            ("<", "bedroom.noise_level", 0.3, False),  # 0.3 < 0.3 is False
            ("<=", "bedroom.noise_level", 0.3, True),  # 0.3 <= 0.3
            ("<=", "bedroom.noise_level", 0.2, False),  # 0.3 <= 0.2 is False
            ("==", "bedroom.noise_level", 0.3, True),  # 0.3 == 0.3
            ("==", "bedroom.noise_level", 0.4, False),  # 0.3 == 0.4 is False
            ("!=", "bedroom.noise_level", 0.4, True),  # 0.3 != 0.4
            ("!=", "bedroom.noise_level", 0.3, False),  # 0.3 != 0.3 is False
        ],
    )
    def test_evaluate_all_six_operators(
        self, op, prop, threshold_value, expected_fire, sample_projection
    ):
        """All six operators produce correct fire/no-fire results."""
        thresholds = [{"property": prop, "op": op, "value": threshold_value}]
        result = ThresholdEvaluator.evaluate(thresholds, sample_projection)
        if expected_fire:
            assert result is not None
            assert isinstance(result, ThresholdSpec)
            assert result.op == op
        else:
            assert result is None

    def test_evaluate_missing_node_returns_none(self, sample_projection):
        """Threshold on missing node_id returns None (D-09 safe default)."""
        thresholds = [{"property": "kitchen.temperature", "op": ">", "value": 25.0}]
        result = ThresholdEvaluator.evaluate(thresholds, sample_projection)
        assert result is None

    def test_evaluate_missing_property_returns_none(self, sample_projection):
        """Threshold on existing node with missing property returns None."""
        thresholds = [{"property": "bedroom.temperature", "op": ">", "value": 25.0}]
        result = ThresholdEvaluator.evaluate(thresholds, sample_projection)
        assert result is None

    def test_evaluate_unknown_operator_returns_none(self, sample_projection):
        """Unknown operator (e.g. '~=') returns None (D-09 safe default)."""
        thresholds = [{"property": "bedroom.noise_level", "op": "~=", "value": 0.3}]
        result = ThresholdEvaluator.evaluate(thresholds, sample_projection)
        assert result is None

    def test_evaluate_type_mismatch_returns_none(self, sample_projection):
        """Incompatible type comparison (str vs float) returns None, does not raise."""
        thresholds = [{"property": "bedroom.noise_level", "op": ">", "value": "loud"}]
        result = ThresholdEvaluator.evaluate(thresholds, sample_projection)
        assert result is None

    def test_evaluate_returns_first_firing(self, sample_projection):
        """When multiple thresholds would fire, returns the first one in list order."""
        spec1 = {"property": "bedroom.noise_level", "op": "<", "value": 0.5}  # fires: 0.3 < 0.5
        spec2 = {"property": "alice.health", "op": ">", "value": 0.5}  # fires: 0.9 > 0.5
        result = ThresholdEvaluator.evaluate([spec1, spec2], sample_projection)
        assert result is not None
        assert result.property == "bedroom.noise_level"

    def test_evaluate_does_not_mutate_inputs(self, sample_projection):
        """evaluate() does not modify thresholds list or projection dict."""
        import copy

        original_proj = copy.deepcopy(sample_projection)
        thresholds = [{"property": "bedroom.noise_level", "op": ">", "value": 0.2}]
        original_thresholds = list(thresholds)
        ThresholdEvaluator.evaluate(thresholds, sample_projection)
        assert thresholds == original_thresholds
        assert sample_projection == original_proj

    def test_evaluate_malformed_spec_dict_skipped(self, sample_projection):
        """A threshold dict missing 'value' key is skipped; does not raise."""
        thresholds = [{"property": "bedroom.noise_level", "op": ">"}]  # missing "value"
        result = ThresholdEvaluator.evaluate(thresholds, sample_projection)
        assert result is None

    def test_evaluate_malformed_property_path_returns_none(self, sample_projection):
        """Property path with no dot ('noDotHere') returns None for that spec."""
        thresholds = [{"property": "noDotHere", "op": ">", "value": 0.1}]
        result = ThresholdEvaluator.evaluate(thresholds, sample_projection)
        assert result is None

    def test_evaluate_returns_threshold_spec_on_fire(self, sample_projection):
        """Fired result is a ThresholdSpec instance with correct field values."""
        thresholds = [{"property": "bedroom.noise_level", "op": "<", "value": 0.5}]
        result = ThresholdEvaluator.evaluate(thresholds, sample_projection)
        assert isinstance(result, ThresholdSpec)
        assert result.property == "bedroom.noise_level"
        assert result.op == "<"
        assert result.value == 0.5

    def test_evaluate_first_firing_when_first_does_not_fire(self, sample_projection):
        """When first threshold does not fire and second does, returns second."""
        spec1 = {"property": "bedroom.noise_level", "op": ">", "value": 0.9}  # no fire: 0.3 > 0.9
        spec2 = {"property": "alice.health", "op": ">", "value": 0.5}  # fires: 0.9 > 0.5
        result = ThresholdEvaluator.evaluate([spec1, spec2], sample_projection)
        assert result is not None
        assert result.property == "alice.health"
