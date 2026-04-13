"""Tests for the locked YieldSignal contract (Phase 4.1 D-07, D-10).

Covers:
    - 7-field dataclass shape + defaults + frozen semantics
    - JSON round-trip (sorted keys, indent=2, deterministic)
    - Rejection paths in ``from_json``:
        * malformed JSON (json.JSONDecodeError)
        * non-dict root (TypeError)
        * missing required fields (TypeError from cls(**data))
        * extra/unknown fields (TypeError — strict policy)
        * unknown schema_version (ValueError — threat T-04.1-01)
    - ``validate()`` enforces classified_action required keys (Pitfall 4)

These tests lock the contract that Phase 5's engine will emit and the operator
will consume. Any drift must be detected here first.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from typing import Any

import pytest

from token_world.operator import SCHEMA_VERSION, YieldSignal


class TestYieldSignalShape:
    """Shape: 7 fields, frozen+slots, defaults."""

    def test_yieldsignal_fields(self) -> None:
        """Construct with all 7 fields; each attribute equals the input."""
        sig = YieldSignal(
            tick_id="tick_1",
            universe_path="/tmp/u",
            schema_version=1,
            reason="no_mechanic_for_action",
            action_text="pick up the rock",
            classified_action={
                "verb": "pickup",
                "actor": "alice",
                "target": "rock_1",
                "params": {},
            },
            actor_state={"location": "room_a"},
            candidate_mechanic_ids=["grasp"],
        )
        assert sig.tick_id == "tick_1"
        assert sig.universe_path == "/tmp/u"
        assert sig.schema_version == 1
        assert sig.reason == "no_mechanic_for_action"
        assert sig.action_text == "pick up the rock"
        assert sig.classified_action == {
            "verb": "pickup",
            "actor": "alice",
            "target": "rock_1",
            "params": {},
        }
        assert sig.actor_state == {"location": "room_a"}
        assert sig.candidate_mechanic_ids == ["grasp"]

    def test_yieldsignal_defaults(self) -> None:
        """Construct with only required fields; defaults fill the rest."""
        sig = YieldSignal(tick_id="tick_1", universe_path="/tmp/u")
        assert sig.schema_version == SCHEMA_VERSION == 1
        assert sig.reason == "no_mechanic_for_action"
        assert sig.action_text == ""
        assert sig.classified_action == {}
        assert sig.actor_state == {}
        assert sig.candidate_mechanic_ids == []

    def test_yieldsignal_frozen(self) -> None:
        """Frozen: assignment raises FrozenInstanceError (subclass of AttributeError)."""
        sig = YieldSignal(tick_id="tick_1", universe_path="/tmp/u")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            sig.tick_id = "mutated"  # type: ignore[misc]


class TestJsonRoundtrip:
    """JSON round-trip + deterministic formatting (threat T-04.1-04)."""

    def test_to_json_roundtrip(
        self,
        yield_signal_json_fixture: Callable[..., dict[str, Any]],
    ) -> None:
        """A fully-populated signal round-trips losslessly."""
        payload = yield_signal_json_fixture(
            classified_action={
                "verb": "craft",
                "actor": "bob",
                "target": None,
                "params": {"recipe": {"iron": 2, "wood": 1}, "tools": ["hammer"]},
            },
            actor_state={
                "location": "forge",
                "inventory": [{"id": "iron_ore", "qty": 3}],
                "mood": None,
            },
            candidate_mechanic_ids=["smelt", "forge", "assemble"],
        )
        original = YieldSignal(**payload)
        reloaded = YieldSignal.from_json(original.to_json())
        assert reloaded == original

    def test_to_json_is_pretty_printed_stable(self) -> None:
        """Output is sorted-keys + indent=2 for diff-friendly diagnostics."""
        sig = YieldSignal(
            tick_id="tick_1",
            universe_path="/tmp/u",
            action_text="x",
            classified_action={"verb": "v", "actor": "a", "target": None, "params": {}},
        )
        text = sig.to_json()
        assert "\n  " in text  # indent=2 present
        # sort_keys: confirm key-alphabetical ordering on top-level keys by
        # scanning the key prefix of any line that begins with a quoted key.
        top_keys: list[str] = []
        for raw in text.splitlines():
            stripped = raw.lstrip()
            # Only capture top-level keys (exactly 2 leading spaces per indent=2)
            if raw.startswith("  ") and not raw.startswith("   ") and stripped.startswith('"'):
                key = stripped.split(":", 1)[0].strip().strip('"')
                top_keys.append(key)
        assert top_keys == sorted(top_keys), f"Expected sorted top-level keys; got {top_keys}"


class TestFromJsonRejections:
    """Rejection paths — threat T-04.1-01 (disk-read tampering / schema drift)."""

    def test_from_json_rejects_malformed(self) -> None:
        """Non-JSON input raises json.JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            YieldSignal.from_json("not json")

    def test_from_json_rejects_non_dict_root(self) -> None:
        """Array/string/int root raises TypeError with a clear message."""
        with pytest.raises(TypeError, match="must be an object"):
            YieldSignal.from_json("[1, 2, 3]")
        with pytest.raises(TypeError, match="must be an object"):
            YieldSignal.from_json('"a string"')

    def test_from_json_rejects_missing_required(self) -> None:
        """Missing ``universe_path`` raises TypeError from cls(**data)."""
        with pytest.raises(TypeError):
            YieldSignal.from_json('{"tick_id": "x"}')

    def test_from_json_rejects_extra_fields(
        self,
        yield_signal_json_fixture: Callable[..., dict[str, Any]],
    ) -> None:
        """Unknown keys raise TypeError (strict dataclass(**kwargs) behaviour)."""
        payload = yield_signal_json_fixture(unknown_field="ignored")
        with pytest.raises(TypeError):
            YieldSignal.from_json(json.dumps(payload))

    def test_from_json_rejects_unknown_schema_version(
        self,
        yield_signal_json_fixture: Callable[..., dict[str, Any]],
    ) -> None:
        """schema_version != SCHEMA_VERSION raises ValueError naming the version."""
        payload = yield_signal_json_fixture(schema_version=99)
        with pytest.raises(ValueError, match="99"):
            YieldSignal.from_json(json.dumps(payload))


class TestValidate:
    """classified_action shape enforcement (Pitfall 4 — stub↔Phase-5 drift)."""

    def test_validate_passes_on_full_signal(self) -> None:
        """Well-formed signal passes .validate() silently."""
        sig = YieldSignal(
            tick_id="tick_1",
            universe_path="/tmp/u",
            classified_action={
                "verb": "move",
                "actor": "alice",
                "target": "room_b",
                "params": {"speed": 1.0},
            },
        )
        assert sig.validate() is None  # explicit None return; no raise

    def test_validate_accepts_target_none(self) -> None:
        """``target`` key must be present but ``None`` is a legal value."""
        sig = YieldSignal(
            tick_id="tick_1",
            universe_path="/tmp/u",
            classified_action={
                "verb": "shout",
                "actor": "alice",
                "target": None,
                "params": {},
            },
        )
        sig.validate()

    def test_validate_classified_action_missing_verb(self) -> None:
        """Missing ``verb`` raises ValueError naming the missing key."""
        sig = YieldSignal(
            tick_id="tick_1",
            universe_path="/tmp/u",
            classified_action={"actor": "alice", "target": None, "params": {}},
        )
        with pytest.raises(ValueError, match="verb"):
            sig.validate()

    def test_validate_classified_action_missing_actor(self) -> None:
        """Missing ``actor`` raises ValueError naming the missing key."""
        sig = YieldSignal(
            tick_id="tick_1",
            universe_path="/tmp/u",
            classified_action={"verb": "move", "target": "x", "params": {}},
        )
        with pytest.raises(ValueError, match="actor"):
            sig.validate()

    def test_validate_classified_action_missing_target(self) -> None:
        """Missing ``target`` key (vs None value) raises ValueError."""
        sig = YieldSignal(
            tick_id="tick_1",
            universe_path="/tmp/u",
            classified_action={"verb": "move", "actor": "alice", "params": {}},
        )
        with pytest.raises(ValueError, match="target"):
            sig.validate()

    def test_validate_classified_action_missing_params(self) -> None:
        """Missing ``params`` key raises ValueError."""
        sig = YieldSignal(
            tick_id="tick_1",
            universe_path="/tmp/u",
            classified_action={"verb": "move", "actor": "alice", "target": "x"},
        )
        with pytest.raises(ValueError, match="params"):
            sig.validate()

    def test_validate_classified_action_params_must_be_dict(self) -> None:
        """``params`` present but not a dict raises ValueError."""
        sig = YieldSignal(
            tick_id="tick_1",
            universe_path="/tmp/u",
            classified_action={
                "verb": "move",
                "actor": "alice",
                "target": "x",
                "params": "oops-not-a-dict",
            },
        )
        with pytest.raises(ValueError, match="params"):
            sig.validate()

    def test_validate_classified_action_verb_must_be_str(self) -> None:
        """Non-string ``verb`` raises ValueError."""
        sig = YieldSignal(
            tick_id="tick_1",
            universe_path="/tmp/u",
            classified_action={
                "verb": 123,
                "actor": "alice",
                "target": None,
                "params": {},
            },
        )
        with pytest.raises(ValueError, match="verb"):
            sig.validate()
