"""Tests for MechanicContext.rng deterministic seeded RNG (D-19).

Covers: raises on missing seed/tick_id, determinism, differs across ticks/seeds,
lazy caching.
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext


def _make_ctx(
    *,
    tick_id: str | None = "tick_1",
    universe_seed: int | None = 42,
) -> MechanicContext:
    """Build a minimal MechanicContext for RNG tests."""
    kg = KnowledgeGraph()
    kg.add_node("actor", node_type="agent")
    kg.add_node("target", node_type="entity")
    return MechanicContext(
        kg,
        actor="actor",
        target="target",
        tick_id=tick_id,
        universe_seed=universe_seed,
    )


class TestRngRaisesWhenUninitialized:
    """ctx.rng raises RuntimeError when tick_id or universe_seed is missing."""

    def test_rng_raises_when_seed_missing(self) -> None:
        """No universe_seed -> RuntimeError on ctx.rng access."""
        ctx = _make_ctx(universe_seed=None, tick_id="tick_1")
        with pytest.raises(RuntimeError, match="universe_seed"):
            _ = ctx.rng

    def test_rng_raises_when_tick_id_missing(self) -> None:
        """universe_seed set but tick_id=None -> RuntimeError."""
        ctx = _make_ctx(universe_seed=42, tick_id=None)
        with pytest.raises(RuntimeError, match="tick_id"):
            _ = ctx.rng


class TestRngDeterminism:
    """ctx.rng is deterministic given the same (seed, tick_id) pair."""

    def test_rng_determinism_same_seed_and_tick(self) -> None:
        """Two contexts with same seed+tick produce identical sequences."""
        ctx_a = _make_ctx(universe_seed=12345, tick_id="tick_99")
        ctx_b = _make_ctx(universe_seed=12345, tick_id="tick_99")
        seq_a = [ctx_a.rng.random() for _ in range(10)]
        seq_b = [ctx_b.rng.random() for _ in range(10)]
        assert seq_a == seq_b

    def test_rng_differs_across_tick_ids(self) -> None:
        """Same seed, different tick_ids -> different sequences."""
        ctx_a = _make_ctx(universe_seed=999, tick_id="tick_1")
        ctx_b = _make_ctx(universe_seed=999, tick_id="tick_2")
        seq_a = [ctx_a.rng.random() for _ in range(5)]
        seq_b = [ctx_b.rng.random() for _ in range(5)]
        assert seq_a != seq_b

    def test_rng_differs_across_seeds(self) -> None:
        """Same tick, different universe_seeds -> different sequences."""
        ctx_a = _make_ctx(universe_seed=1, tick_id="tick_1")
        ctx_b = _make_ctx(universe_seed=2, tick_id="tick_1")
        seq_a = [ctx_a.rng.random() for _ in range(5)]
        seq_b = [ctx_b.rng.random() for _ in range(5)]
        assert seq_a != seq_b


class TestRngCaching:
    """ctx.rng is lazily built and cached for the lifetime of the context."""

    def test_rng_is_cached(self) -> None:
        """Second access to ctx.rng returns the same object."""
        ctx = _make_ctx()
        rng_first = ctx.rng
        rng_second = ctx.rng
        assert rng_first is rng_second

    def test_rng_state_carries_across_calls(self) -> None:
        """Calling ctx.rng repeatedly returns the same stateful RNG (not reset)."""
        ctx = _make_ctx()
        first_val = ctx.rng.random()
        # rng should have advanced; next call from same instance gives different value
        second_val = ctx.rng.random()
        assert first_val != second_val  # sequence advances, not reset


class TestBackwardsCompat:
    """Existing callers that don't pass tick_id/universe_seed still work."""

    def test_legacy_construction_still_works(self) -> None:
        """MechanicContext(kg, actor=..., target=...) without new kwargs doesn't crash."""
        kg = KnowledgeGraph()
        kg.add_node("a", node_type="agent")
        kg.add_node("b", node_type="entity")
        ctx = MechanicContext(kg, actor="a", target="b")
        assert ctx.actor == "a"
        assert ctx.target == "b"
