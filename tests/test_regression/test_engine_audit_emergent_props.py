"""Regression test: REQ-V12-ENGINE-03 — engine must not privilege property names.

SC-3: A mechanic using `warded` or `trapped` property names must receive identical
engine treatment as a mechanic using `locked`.  The engine must not hard-code any
semantic check on graph property names.

Tests verify:
- ctx.refuse("warded", ...) works identically to ctx.refuse("locked", ...)
- ctx.refuse("trapped", ...) works identically to ctx.refuse("locked", ...)
- Arbitrary property-name reason codes produce a CheckResult(passed=False)
- The refusal narrative for novel codes falls back cleanly (no crash)
"""

from __future__ import annotations

from token_world.graph import KnowledgeGraph
from token_world.mechanic import MechanicContext
from token_world.mechanic.protocol import CheckResult


def _make_ctx(target: str = "gate") -> MechanicContext:
    kg = KnowledgeGraph()
    kg.add_node("player", node_type="agent")
    kg.add_node(target, node_type="entity")
    return MechanicContext(kg, actor="player", target=target)


class TestEmergentPropertyRefusal:
    """The engine treats all reason codes identically regardless of name."""

    def test_locked_refusal_returns_failed_check(self) -> None:
        ctx = _make_ctx("iron_door")
        result = ctx.refuse("locked", {"target": "iron_door"})
        assert isinstance(result, CheckResult)
        assert result.passed is False

    def test_warded_refusal_returns_failed_check(self) -> None:
        """A mechanic using 'warded' must get identical treatment as 'locked'."""
        ctx = _make_ctx("magic_portal")
        result = ctx.refuse("warded", {"target": "magic_portal"})
        assert isinstance(result, CheckResult)
        assert result.passed is False

    def test_trapped_refusal_returns_failed_check(self) -> None:
        """A mechanic using 'trapped' must get identical treatment as 'locked'."""
        ctx = _make_ctx("treasure_chest")
        result = ctx.refuse("trapped", {"target": "treasure_chest"})
        assert isinstance(result, CheckResult)
        assert result.passed is False

    def test_warded_narrative_is_grounded(self) -> None:
        """Fallback narrative includes the reason_code so it is always informative."""
        ctx = _make_ctx("magic_portal")
        result = ctx.refuse("warded")
        assert result.passed is False
        assert len(result.reasons) >= 1
        # Fallback template uses reason_code in the text
        assert "warded" in result.reasons[0]

    def test_trapped_narrative_is_grounded(self) -> None:
        ctx = _make_ctx("treasure_chest")
        result = ctx.refuse("trapped")
        assert result.passed is False
        assert len(result.reasons) >= 1
        assert "trapped" in result.reasons[0]

    def test_arbitrary_property_name_never_crashes(self) -> None:
        """Any emergent property name is a valid reason code."""
        ctx = _make_ctx("mystic_gate")
        for code in ["enchanted", "cursed", "rusted_shut", "phase_shifted", "quantum_locked"]:
            result = ctx.refuse(code)
            assert result.passed is False, f"refuse('{code}') must return passed=False"
            assert len(result.reasons) >= 1, f"refuse('{code}') must return a reason"

    def test_warded_and_locked_both_yield_check_result_passed_false(self) -> None:
        """Structural equality: both produce CheckResult(passed=False)."""
        ctx = _make_ctx("the_door")
        locked_result = ctx.refuse("locked", {"target": "the_door"})
        warded_result = ctx.refuse("warded", {"target": "the_door"})
        # Both must be CheckResult with passed=False — identical structural treatment
        assert type(locked_result) is type(warded_result)
        assert locked_result.passed == warded_result.passed


class TestRefusalTemplateDoesNotGateOnPropertyName:
    """Confirm the RefusalTemplate _TEMPLATES dict does not gate engine behavior.

    These tests document the design contract: having an entry in _TEMPLATES is
    a narrative convenience only — it never implies the engine checks for that
    property in the graph.
    """

    def test_template_keys_are_narrative_shortcuts_not_semantic_gates(self) -> None:
        """Known template keys should not give the engine special knowledge."""
        from token_world.engine.refusal import _TEMPLATES  # noqa: PLC2701

        # These keys exist as narrative helpers only
        convenience_keys = {"inventory_full", "locked", "blocked"}
        for key in convenience_keys:
            assert key in _TEMPLATES, f"Convenience key '{key}' should exist in _TEMPLATES"

        # But any unknown key must also work (fallback), proving no privileging
        from token_world.engine.refusal import RefusalTemplate

        for arbitrary in ["warded", "trapped", "rusted", "enchanted"]:
            result = RefusalTemplate.render(arbitrary, {})
            assert arbitrary in result, (
                f"Fallback for '{arbitrary}' must include the reason code in output"
            )
