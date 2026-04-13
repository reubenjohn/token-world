"""Frozen-surface test for MechanicContext.

This test pins the authoring-facing DSL surface that seed mechanics (plans
04-06 through 04-11) depend on. Any drift — renamed method, removed
attribute, changed signature — fails here loudly instead of silently
breaking a seed mechanic at import time.

Closes 04-REVIEWS.md HIGH #3: the DSL contract must be enumerated and
tested, not assumed. Known gaps (methods a plan MUST stub because the
framework does not yet supply them) are listed at the bottom as commented-
out entries with the gap ID — never as silent omissions.
"""

from __future__ import annotations

import inspect

import pytest

from token_world.mechanic import MechanicContext

# Expected public surface. Values are the expected `inspect.signature(...)`
# rendered as a string. Parameter names and kinds are asserted; annotations
# on the stringified signature are allowed to change freely (Python may
# render `str | None` vs `Optional[str]`, etc.), so we compare parameter
# lists rather than raw string equality.
#
# Format: { "method_or_attr_name": "signature_string_or_None_for_attrs" }
#
# When adding a new method to MechanicContext, add it here so the surface
# stays frozen. When removing a method, delete it here AND audit every
# caller — seed mechanics depend on this.
EXPECTED_CALLABLES: dict[str, list[tuple[str, str]]] = {
    # name: [(param_name, param_kind), ...] — 'self' excluded
    #
    # --- Query API ---
    "has_node": [("node_id", "POSITIONAL_OR_KEYWORD")],
    "has_edge": [
        ("src", "POSITIONAL_OR_KEYWORD"),
        ("dst", "POSITIONAL_OR_KEYWORD"),
    ],
    "query_node": [
        ("node_id", "POSITIONAL_OR_KEYWORD"),
        ("property", "POSITIONAL_OR_KEYWORD"),
    ],
    "query_neighbors": [("node_id", "POSITIONAL_OR_KEYWORD")],
    "neighbors": [
        ("node_id", "POSITIONAL_OR_KEYWORD"),
        ("relation", "KEYWORD_ONLY"),
    ],
    "find_nodes": [("filters", "VAR_KEYWORD")],
    # --- Mutation API ---
    "mutate": [
        ("node_id", "POSITIONAL_OR_KEYWORD"),
        ("property", "POSITIONAL_OR_KEYWORD"),
        ("value", "POSITIONAL_OR_KEYWORD"),
    ],
    "set": [
        ("node_id", "POSITIONAL_OR_KEYWORD"),
        ("property", "POSITIONAL_OR_KEYWORD"),
        ("value", "POSITIONAL_OR_KEYWORD"),
    ],
    "add_node": [
        ("node_id", "POSITIONAL_OR_KEYWORD"),
        ("node_type", "KEYWORD_ONLY"),
        ("props", "VAR_KEYWORD"),
    ],
    "remove_node": [("node_id", "POSITIONAL_OR_KEYWORD")],
    "add_edge": [
        ("src", "POSITIONAL_OR_KEYWORD"),
        ("dst", "POSITIONAL_OR_KEYWORD"),
        ("props", "VAR_KEYWORD"),
    ],
    "remove_edge": [
        ("src", "POSITIONAL_OR_KEYWORD"),
        ("dst", "POSITIONAL_OR_KEYWORD"),
    ],
    # --- Identity ---
    "claim_id": [("name", "POSITIONAL_OR_KEYWORD")],
    # --- Refusal helper (D-13, Plan 05-03) ---
    "refuse": [
        ("reason_code", "POSITIONAL_OR_KEYWORD"),
        ("details", "POSITIONAL_OR_KEYWORD"),
    ],
    # --- Long-running action helper (D-05, D-15, Plan 07-03) ---
    "begin_long_action": [
        ("action_text", "POSITIONAL_OR_KEYWORD"),
        ("turns_total", "POSITIONAL_OR_KEYWORD"),
        ("thresholds", "POSITIONAL_OR_KEYWORD"),
        ("attention_state", "POSITIONAL_OR_KEYWORD"),
        ("clear_on_end", "POSITIONAL_OR_KEYWORD"),  # WR-01: companion flag cleanup
    ],
}

EXPECTED_ATTRS: dict[str, type | None] = {
    # Name -> expected type (None = just existence check, accept any type)
    "actor": str,
    "target": str,
    # spatial and temporal are properties — existence + duck-typing asserted
    # separately below.
    # rng is a lazy property — existence asserted; type is random.Random.
    # Added in Phase 5 Plan 01 (D-19, GAP-GRAPH05 closure).
}

# Known gaps — methods/attributes that plans 04-06..04-11 reference but
# that MechanicContext does NOT (yet) supply. Plans that need these MUST
# stub via the framework-gap-stub convention (see authoring-mechanics.md
# §8). Enumerated here so the gap list stays in one place; do NOT silently
# delete entries from this section without updating the guide.
#
# - "actors"               : MECH12 (broadcast). Needs engine-level ctx
#                            extension for multi-actor ticks. GAP-ENG02.
# - "spatial.segment_intersections" : MECH02 (look with occluders).
#                            Needs Shapely/segment-vs-bbox support on
#                            SpatialIndex. GAP-GRAPH02.
# - "seed" / "_seed"       : Determinism primitive for random-sampling
#                            mechanics (fire_spread). GAP-GRAPH05.
#
# DO NOT uncomment any of these without a paired implementation + test.
# EXPECTED_CALLABLES["actors"] = [...]           # GAP-ENG02
# EXPECTED_ATTRS["seed"] = int                   # GAP-GRAPH05


def _param_summary(sig: inspect.Signature) -> list[tuple[str, str]]:
    """Extract (name, kind.name) pairs, skipping `self`."""
    out = []
    for name, p in sig.parameters.items():
        if name == "self":
            continue
        out.append((name, p.kind.name))
    return out


class TestMechanicContextFrozenSurface:
    """Assert the public DSL surface matches what plans 06-11 expect."""

    @pytest.mark.parametrize("method_name", sorted(EXPECTED_CALLABLES))
    def test_callable_exists_and_signature(self, method_name: str) -> None:
        """Each expected callable exists with expected parameters."""
        assert hasattr(MechanicContext, method_name), (
            f"MechanicContext is missing public method '{method_name}' "
            f"that plans 04-06..04-11 depend on. See "
            f"docs/guides/authoring-mechanics.md §4."
        )
        member = getattr(MechanicContext, method_name)
        assert callable(member), f"'{method_name}' exists but is not callable"
        sig = inspect.signature(member)
        actual = _param_summary(sig)
        expected = EXPECTED_CALLABLES[method_name]
        assert actual == expected, (
            f"Signature drift on MechanicContext.{method_name}: "
            f"expected {expected}, got {actual}. Seeds depend on this; "
            f"if you changed it intentionally, update EXPECTED_CALLABLES "
            f"AND docs/guides/authoring-mechanics.md."
        )

    @pytest.mark.parametrize("attr_name", sorted(EXPECTED_ATTRS))
    def test_attribute_exists(self, attr_name: str) -> None:
        """Each expected attribute exists on instances."""
        # Build a minimal instance to inspect instance-level attrs.
        from token_world.graph import KnowledgeGraph

        kg = KnowledgeGraph()
        kg.add_node("a", node_type="agent")
        kg.add_node("b", node_type="entity")
        ctx = MechanicContext(kg, actor="a", target="b")
        assert hasattr(ctx, attr_name), f"MechanicContext instance missing attr '{attr_name}'"
        expected_type = EXPECTED_ATTRS[attr_name]
        if expected_type is not None:
            assert isinstance(getattr(ctx, attr_name), expected_type)

    def test_spatial_property_exposes_expected_methods(self) -> None:
        """ctx.spatial (lazy) exposes the SpatialIndex methods seeds use."""
        from token_world.graph import KnowledgeGraph

        kg = KnowledgeGraph()
        ctx = MechanicContext(kg, actor="a", target="b")
        spatial = ctx.spatial
        # These are the SpatialIndex methods cited by plan 04-07.
        for name in ("nearest", "within", "intersects"):
            assert hasattr(spatial, name), f"ctx.spatial missing '{name}' — plan 04-07 requires it"
            assert callable(getattr(spatial, name))
        # segment_intersections is a KNOWN GAP (GAP-GRAPH02). Plans that
        # need it MUST stub via blocked_by. Do not assert presence here.

    def test_temporal_property_exists(self) -> None:
        """ctx.temporal (lazy) exists and returns a queryable facade."""
        from token_world.graph import KnowledgeGraph

        kg = KnowledgeGraph()
        ctx = MechanicContext(kg, actor="a", target="b")
        temporal = ctx.temporal
        assert temporal is not None

    def test_neighbors_relation_filter(self) -> None:
        """ctx.neighbors(id, relation=...) filters by edge `relation` property.

        Plans 04-06, 04-07, 04-08 all use this pattern
        (``ctx.neighbors(actor, relation="holds")``). Validate end-to-end so
        the filter works against real KnowledgeGraph edge data, not just the
        signature shape.
        """
        from token_world.graph import KnowledgeGraph

        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("room_a", node_type="entity")
        kg.add_node("room_b", node_type="entity")
        kg.add_node("sword", node_type="entity")
        kg.add_edge("alice", "room_a", relation="located_in")
        kg.add_edge("alice", "sword", relation="holds")
        kg.add_edge("alice", "room_b", relation="located_in")
        ctx = MechanicContext(kg, actor="alice", target="sword")

        # No filter: all out-neighbors.
        assert set(ctx.neighbors("alice")) == {"room_a", "room_b", "sword"}
        # Relation filter returns only matching edges.
        assert set(ctx.neighbors("alice", relation="holds")) == {"sword"}
        assert set(ctx.neighbors("alice", relation="located_in")) == {
            "room_a",
            "room_b",
        }
        # Unknown relation -> empty.
        assert ctx.neighbors("alice", relation="owns") == []

    def test_set_and_mutate_are_equivalent(self) -> None:
        """ctx.set and ctx.mutate produce the same Mutation record.

        Plan 04-08 uses ctx.set; every other plan uses ctx.mutate. Both must
        work identically so seeds aren't fragile to author preference.
        """
        from token_world.graph import KnowledgeGraph

        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", hunger=5)
        ctx = MechanicContext(kg, actor="alice", target="alice")
        m1 = ctx.mutate("alice", "hunger", 3)
        m2 = ctx.set("alice", "hunger", 1)
        assert m1.type == "set_property"
        assert m2.type == "set_property"
        assert m1.target == m2.target == "alice"
        assert m2.new_value == 1

    def test_claim_id_delegates(self) -> None:
        """ctx.claim_id delegates to KnowledgeGraph.claim_id."""
        from token_world.graph import KnowledgeGraph

        kg = KnowledgeGraph()
        ctx = MechanicContext(kg, actor="a", target="b")
        claimed = ctx.claim_id("sword")
        assert claimed == "sword"
        # Second call with the same base + node present must return a suffix.
        kg.add_node(claimed, node_type="entity")
        claimed2 = ctx.claim_id("sword")
        assert claimed2 != "sword"
        assert claimed2.startswith("sword_")

    def test_no_unexpected_public_methods(self) -> None:
        """Flag any new public method that slipped in without doc+test coverage.

        The surface is frozen: additions must land in EXPECTED_CALLABLES /
        EXPECTED_ATTRS (and be documented in authoring-mechanics.md §4)
        alongside the implementation. This test tightens the feedback loop
        so reviewers notice contract growth.
        """
        public_members = {name for name in dir(MechanicContext) if not name.startswith("_")}
        # Known non-method public attrs / properties.
        known_attrs = set(EXPECTED_ATTRS) | {"spatial", "temporal", "rng"}
        expected = set(EXPECTED_CALLABLES) | known_attrs
        unexpected = public_members - expected
        assert not unexpected, (
            f"Unexpected public members on MechanicContext: "
            f"{sorted(unexpected)}. Either add them to EXPECTED_CALLABLES / "
            f"EXPECTED_ATTRS (with a docs update) or make them private."
        )
