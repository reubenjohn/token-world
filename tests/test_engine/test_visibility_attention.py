"""Stage 5 attention_state modulation tests — VisibilityProjector (D-12).

Tests verify the backward-compatible extension of project_for with the
attention_state kwarg. Covers: suppress, boost, combined, edge cases.

Fixture: alice agent in bedroom with properties including visual_detail, smell,
noise_level. bedroom also has noise_level and illumination.
"""

from __future__ import annotations

import copy

from token_world.engine.visibility import VisibilityProjector
from token_world.engine.visibility import project_for as module_project_for
from token_world.graph import KnowledgeGraph

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def make_attention_graph() -> KnowledgeGraph:
    """Return a KnowledgeGraph with alice in bedroom, populated with test props."""
    kg = KnowledgeGraph(db_path=None)
    kg.add_node(
        "alice",
        node_type="agent",
        name="Alice",
        visual_detail="blurred",
        smell="smoke",
        noise_level=0.8,
    )
    kg.add_node(
        "bedroom",
        node_type="entity",
        name="Bedroom",
        illumination=1.0,
        noise_level=0.3,
    )
    kg.add_edge("alice", "bedroom", type="location")
    return kg


# ---------------------------------------------------------------------------
# Default / backward-compat tests
# ---------------------------------------------------------------------------


class TestAttentionStateDefault:
    """attention_state=None (default) must produce identical output to pre-Phase-7."""

    def test_project_for_default_none_matches_pre_phase_7(self) -> None:
        """No attention_state → same dict as calling without the param."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result_no_param = proj.project_for("alice")
        result_none = proj.project_for("alice", attention_state=None)
        result_empty = proj.project_for("alice", attention_state={})
        assert result_no_param == result_none
        assert result_no_param == result_empty

    def test_attention_state_none_no_attention_boosted_key(self) -> None:
        """Default projection must NOT have 'attention_boosted' on any node."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice")
        for node_id, entry in result.items():
            assert "attention_boosted" not in entry, (
                f"Node '{node_id}' unexpectedly has 'attention_boosted'"
            )


# ---------------------------------------------------------------------------
# Suppress tests
# ---------------------------------------------------------------------------


class TestSuppress:
    """attention_state suppress removes properties from all nodes."""

    def test_suppress_removes_properties(self) -> None:
        """Suppress visual_detail and smell removes both from alice's properties."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice", attention_state={"suppress": ["visual_detail", "smell"]})
        alice_props = result["alice"]["properties"]
        assert "visual_detail" not in alice_props
        assert "smell" not in alice_props

    def test_suppress_leaves_other_properties_intact(self) -> None:
        """Suppressing specific props does not affect other properties."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice", attention_state={"suppress": ["visual_detail"]})
        alice_props = result["alice"]["properties"]
        assert "smell" in alice_props
        assert "noise_level" in alice_props

    def test_suppress_property_not_present_is_noop(self) -> None:
        """Suppressing a property that doesn't exist on any node is a no-op."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result_baseline = proj.project_for("alice")
        result_suppress = proj.project_for(
            "alice", attention_state={"suppress": ["does_not_exist"]}
        )
        assert result_baseline == result_suppress

    def test_suppress_applies_to_all_nodes(self) -> None:
        """Suppress removes noise_level from ALL nodes that have it (alice + bedroom)."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice", attention_state={"suppress": ["noise_level"]})
        # Both alice and bedroom have noise_level — both should have it removed
        assert "noise_level" not in result["alice"]["properties"]
        assert "noise_level" not in result["bedroom"]["properties"]


# ---------------------------------------------------------------------------
# Boost tests
# ---------------------------------------------------------------------------


class TestBoost:
    """attention_state boost adds attention_boosted without removing from properties."""

    def test_boost_adds_attention_boosted(self) -> None:
        """Boost noise_level adds attention_boosted to bedroom entry."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice", attention_state={"boost": ["noise_level"]})
        # bedroom has noise_level=0.3
        assert "attention_boosted" in result["bedroom"]
        assert result["bedroom"]["attention_boosted"] == {"noise_level": 0.3}

    def test_boost_does_not_remove_property_from_properties(self) -> None:
        """Boost copies to attention_boosted but does NOT remove from properties."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice", attention_state={"boost": ["noise_level"]})
        # noise_level must still be in properties
        assert "noise_level" in result["bedroom"]["properties"]
        assert result["bedroom"]["properties"]["noise_level"] == 0.3

    def test_boost_property_not_present_adds_no_attention_boosted(self) -> None:
        """Boosting a property not on any node adds no attention_boosted key."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice", attention_state={"boost": ["does_not_exist"]})
        for node_id, entry in result.items():
            assert "attention_boosted" not in entry, (
                f"Node '{node_id}' unexpectedly has 'attention_boosted'"
            )

    def test_boost_only_includes_present_properties(self) -> None:
        """Boost list with mixed present/absent props: only present ones in attention_boosted."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result = proj.project_for(
            "alice", attention_state={"boost": ["noise_level", "does_not_exist"]}
        )
        # bedroom has noise_level — should appear; does_not_exist absent — omitted
        assert result["bedroom"]["attention_boosted"] == {"noise_level": 0.3}


# ---------------------------------------------------------------------------
# Combined suppress + boost
# ---------------------------------------------------------------------------


class TestSuppressAndBoost:
    """Suppress + boost can be combined; suppress runs first (deterministic order)."""

    def test_suppress_and_boost_combined(self) -> None:
        """Suppress visual_detail AND boost noise_level in one call."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result = proj.project_for(
            "alice",
            attention_state={"suppress": ["visual_detail"], "boost": ["noise_level"]},
        )
        # Suppress: visual_detail gone from alice
        assert "visual_detail" not in result["alice"]["properties"]
        # Boost: noise_level boosted on bedroom
        assert "attention_boosted" in result["bedroom"]
        assert result["bedroom"]["attention_boosted"]["noise_level"] == 0.3
        # Boost doesn't remove noise_level from properties
        assert "noise_level" in result["bedroom"]["properties"]

    def test_suppress_wins_over_boost_when_same_key(self) -> None:
        """Suppress then boost on same key: key gone from properties, not in attention_boosted.

        Deterministic order: suppress FIRST, then boost reads post-suppression state.
        So suppressed key is absent when boost runs → no attention_boosted entry for it.
        """
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result = proj.project_for(
            "alice",
            attention_state={"suppress": ["noise_level"], "boost": ["noise_level"]},
        )
        # noise_level gone from all node properties
        for node_id, entry in result.items():
            assert "noise_level" not in entry["properties"], (
                f"noise_level still in {node_id}.properties after suppress"
            )
            # attention_boosted must NOT contain noise_level (boost reads post-suppress)
            boosted = entry.get("attention_boosted", {})
            assert "noise_level" not in boosted, (
                f"noise_level found in {node_id}.attention_boosted despite being suppressed first"
            )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestAttentionEdgeCases:
    """Empty dicts, unknown keys, mutation safety."""

    def test_empty_attention_state_is_noop(self) -> None:
        """Empty dict behaves identically to attention_state=None."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result_none = proj.project_for("alice", attention_state=None)
        result_empty = proj.project_for("alice", attention_state={})
        assert result_none == result_empty

    def test_unknown_attention_keys_silently_ignored(self) -> None:
        """Unknown top-level keys like 'tilt' do not raise an error."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice", attention_state={"tilt": ["x"]})
        assert "alice" in result  # projection still returned normally
        # No attention_boosted added for unknown key
        for entry in result.values():
            assert "attention_boosted" not in entry

    def test_suppress_empty_list_is_noop(self) -> None:
        """suppress=[] is equivalent to no suppression."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result_none = proj.project_for("alice")
        result_empty_suppress = proj.project_for("alice", attention_state={"suppress": []})
        assert result_none == result_empty_suppress

    def test_boost_empty_list_is_noop(self) -> None:
        """boost=[] adds no attention_boosted keys."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result_none = proj.project_for("alice")
        result_empty_boost = proj.project_for("alice", attention_state={"boost": []})
        assert result_none == result_empty_boost

    def test_attention_state_dict_not_mutated(self) -> None:
        """The attention_state dict passed to project_for is not mutated."""
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        attention = {"suppress": ["visual_detail"], "boost": ["noise_level"]}
        original = copy.deepcopy(attention)
        proj.project_for("alice", attention_state=attention)
        assert attention == original

    def test_input_projection_not_mutated_by_stage5(self) -> None:
        """Stage 5 uses defensive copies — original intermediate projection not mutated.

        Verify by calling project_for twice with attention_state and confirming
        identical results (no internal state bleeding between calls).
        """
        kg = make_attention_graph()
        proj = VisibilityProjector(kg)
        result1 = proj.project_for("alice", attention_state={"suppress": ["visual_detail"]})
        result2 = proj.project_for("alice", attention_state={"suppress": ["visual_detail"]})
        assert result1 == result2

    def test_attention_applied_to_all_nodes(self) -> None:
        """Properties on multiple nodes are all affected by suppress."""
        kg = make_attention_graph()
        # Add a second entity in the room with noise_level
        kg.add_node("radio", node_type="entity", name="Radio", noise_level=0.9)
        kg.add_edge("bedroom", "radio", type="contains")
        proj = VisibilityProjector(kg)
        result = proj.project_for("alice", attention_state={"suppress": ["noise_level"]})
        # All three nodes (alice, bedroom, radio) should have noise_level removed
        assert "noise_level" not in result["alice"]["properties"]
        assert "noise_level" not in result["bedroom"]["properties"]
        assert "noise_level" not in result["radio"]["properties"]


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


class TestModuleLevelProjectForFunction:
    """Module-level project_for convenience function must accept attention_state."""

    def test_module_level_project_for_function_accepts_attention_state(self) -> None:
        """Module-level project_for passes attention_state to VisibilityProjector."""
        kg = make_attention_graph()
        result = module_project_for(kg, "alice", attention_state={"suppress": ["visual_detail"]})
        assert "visual_detail" not in result["alice"]["properties"]

    def test_module_level_project_for_default_none_backward_compat(self) -> None:
        """Module-level project_for with no attention_state is backward-compatible."""
        kg = make_attention_graph()
        result_no_param = module_project_for(kg, "alice")
        result_none = module_project_for(kg, "alice", attention_state=None)
        assert result_no_param == result_none
