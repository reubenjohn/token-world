"""Tests for EngineStub — fabricates YieldSignal instances matching the Phase-5 shape.

The stub is the throwaway fixture that unblocks Plan 04.1-03's harness
integration test before Phase 5's engine lands (D-09/D-10). These tests lock
the contract guarantee: every fabricated signal passes ``YieldSignal.validate()``
by construction, so downstream authoring subagents can trust the shape.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from token_world.operator import YieldSignal
from token_world.operator.testing import EngineStub


class TestFabricateShape:
    """Default / override construction paths."""

    def test_engine_stub_fabricate_yield_default_shape(self, universe: Path) -> None:
        """Default fabrication produces the expected 7-field shape."""
        stub = EngineStub(universe_path=universe)
        sig = stub.fabricate_yield(verb="pickup", actor="alice")
        assert isinstance(sig, YieldSignal)
        assert sig.tick_id == "tick_1"
        assert sig.universe_path == str(universe)
        assert sig.schema_version == 1
        assert sig.reason == "no_mechanic_for_action"
        assert sig.action_text == ""
        assert sig.classified_action == {
            "verb": "pickup",
            "actor": "alice",
            "target": None,
            "params": {},
        }
        assert sig.actor_state == {}
        assert sig.candidate_mechanic_ids == []

    def test_engine_stub_with_candidates(self, universe: Path) -> None:
        """Optional ``candidate_mechanic_ids`` flows through unchanged."""
        stub = EngineStub(universe_path=universe)
        sig = stub.fabricate_yield(
            verb="pickup",
            actor="alice",
            candidate_mechanic_ids=["pickup_v1", "grasp"],
        )
        assert sig.candidate_mechanic_ids == ["pickup_v1", "grasp"]

    def test_engine_stub_with_actor_state(self, universe: Path) -> None:
        """Optional ``actor_state`` flows through unchanged."""
        stub = EngineStub(universe_path=universe)
        sig = stub.fabricate_yield(
            verb="move",
            actor="alice",
            target="room_b",
            actor_state={"location": "room_a", "inventory": []},
        )
        assert sig.actor_state == {"location": "room_a", "inventory": []}
        assert sig.classified_action["target"] == "room_b"

    def test_engine_stub_with_params_and_action_text(self, universe: Path) -> None:
        """Optional ``params`` + ``action_text`` flow through."""
        stub = EngineStub(universe_path=universe)
        sig = stub.fabricate_yield(
            verb="craft",
            actor="bob",
            params={"recipe": "sword"},
            action_text="bob crafts a sword",
        )
        assert sig.classified_action["params"] == {"recipe": "sword"}
        assert sig.action_text == "bob crafts a sword"


class TestFabricateContract:
    """Contract: every fabricated signal passes validate() by construction."""

    def test_engine_stub_validate_passes(self, universe: Path) -> None:
        """The fabricated signal passes ``.validate()`` without raising.

        This is the critical contract test (D-10 — stub matches Phase-5 shape).
        If EngineStub ever drifts, this test fails before integration tests
        downstream get confused.
        """
        stub = EngineStub(universe_path=universe)
        sig = stub.fabricate_yield(verb="pickup", actor="alice")
        sig.validate()  # must not raise

    def test_engine_stub_roundtrip(self, universe: Path) -> None:
        """to_json → from_json → validate completes without error."""
        stub = EngineStub(universe_path=universe)
        sig = stub.fabricate_yield(
            verb="move",
            actor="alice",
            target="room_b",
            params={"speed": 1.5},
            candidate_mechanic_ids=["movement"],
            actor_state={"location": "room_a"},
        )
        reloaded = YieldSignal.from_json(sig.to_json())
        reloaded.validate()
        assert reloaded == sig


class TestIndependence:
    """Stub should emit distinct, uncoupled instances — no hidden shared state."""

    def test_engine_stub_distinct_tick_ids(self, universe: Path) -> None:
        """Two calls with distinct tick_ids yield two distinct YieldSignal objects."""
        stub = EngineStub(universe_path=universe)
        sig5 = stub.fabricate_yield(tick_id="tick_5", verb="move", actor="alice")
        sig6 = stub.fabricate_yield(tick_id="tick_6", verb="move", actor="alice")
        assert sig5.tick_id == "tick_5"
        assert sig6.tick_id == "tick_6"
        assert sig5 is not sig6
        assert sig5 != sig6

    def test_engine_stub_does_not_alias_mutable_defaults(self, universe: Path) -> None:
        """Mutating one signal's candidate list doesn't leak into another.

        Guards against accidental default-argument sharing — a common Python
        footgun. Because YieldSignal is frozen+slots we can't assign to the
        attribute, but we can exercise the deeper concern: passing an empty
        list twice must not produce aliased lists.
        """
        stub = EngineStub(universe_path=universe)
        sig_a = stub.fabricate_yield(verb="a", actor="x", candidate_mechanic_ids=[])
        sig_b = stub.fabricate_yield(verb="b", actor="y", candidate_mechanic_ids=[])
        # Lists must compare equal-but-be-separate instances (defensive copy).
        assert sig_a.candidate_mechanic_ids == sig_b.candidate_mechanic_ids == []
        assert sig_a.candidate_mechanic_ids is not sig_b.candidate_mechanic_ids


class TestStubYieldFixture:
    """The stub_yield fixture exposes the stub factory callable directly."""

    def test_stub_yield_fixture_is_callable(
        self,
        stub_yield: Callable[..., YieldSignal],
    ) -> None:
        """Fixture returns a factory that produces validated signals."""
        sig = stub_yield(verb="pickup", actor="alice")
        assert isinstance(sig, YieldSignal)
        sig.validate()

    def test_stub_yield_fixture_uses_universe_path(
        self,
        universe: Path,
        stub_yield: Callable[..., YieldSignal],
    ) -> None:
        """Fixture wires the ``universe`` fixture into the stub's universe_path."""
        sig = stub_yield(verb="pickup", actor="alice")
        assert sig.universe_path == str(universe)
