"""Tests for MechanicContext.refuse helper (D-13, Plan 05-03 Task 3).

ctx.refuse(reason_code, details) returns CheckResult(passed=False, reasons=[narrative])
where the narrative comes from RefusalTemplate. Mechanics use this inside check()
to produce a consistent refusal surface.
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic import MechanicContext
from token_world.mechanic.protocol import CheckResult


def _make_ctx() -> MechanicContext:
    kg = KnowledgeGraph()
    kg.add_node("player", node_type="agent")
    kg.add_node("gate", node_type="entity")
    return MechanicContext(kg, actor="player", target="gate")


class TestContextRefuseHelper:
    """ctx.refuse returns the expected CheckResult shape."""

    def test_refuse_returns_check_result(self) -> None:
        ctx = _make_ctx()
        result = ctx.refuse("no_such_target", {"target_text": "ghost"})
        assert isinstance(result, CheckResult)

    def test_refuse_passed_is_false(self) -> None:
        ctx = _make_ctx()
        result = ctx.refuse("locked", {"target": "iron gate"})
        assert result.passed is False

    def test_refuse_reasons_contains_narrative(self) -> None:
        ctx = _make_ctx()
        result = ctx.refuse("no_such_target", {"target_text": "ghost"})
        # reasons is a list; the rendered narrative should be the first element
        assert len(result.reasons) >= 1
        assert "ghost" in result.reasons[0]

    def test_refuse_unknown_code_uses_fallback(self) -> None:
        ctx = _make_ctx()
        result = ctx.refuse("some_unknown_code")
        assert result.passed is False
        assert len(result.reasons) >= 1
        assert "some_unknown_code" in result.reasons[0]

    def test_refuse_with_no_details_does_not_raise(self) -> None:
        ctx = _make_ctx()
        # details=None must not crash
        result = ctx.refuse("locked")
        assert isinstance(result, CheckResult)
        assert result.passed is False

    def test_refuse_deterministic_same_inputs(self) -> None:
        ctx = _make_ctx()
        r1 = ctx.refuse("no_viable_action", {"action_text": "flap wildly"})
        r2 = ctx.refuse("no_viable_action", {"action_text": "flap wildly"})
        assert r1.reasons == r2.reasons

    def test_refuse_different_codes_produce_different_narratives(self) -> None:
        ctx = _make_ctx()
        r_locked = ctx.refuse("locked", {"target": "door"})
        r_blocked = ctx.refuse("blocked", {"reason": "wall"})
        # Different templates → different narratives
        assert r_locked.reasons[0] != r_blocked.reasons[0]


class TestContextRefuseLazyImport:
    """RefusalTemplate is NOT imported at context.py module-load time."""

    def test_engine_refusal_not_imported_at_module_load(self) -> None:
        """Import MechanicContext without triggering engine.refusal import.

        This verifies the lazy-import discipline: context.py must not have a
        top-level 'from token_world.engine.refusal import ...' statement.
        Mechanics that never call ctx.refuse pay zero engine-import cost.
        """
        # If context.py had a top-level import of engine.refusal, the module
        # would already be in sys.modules from the earlier import above.
        # We verify by checking the module's source for a lazy pattern.
        import inspect

        import token_world.mechanic.context as ctx_mod

        src = inspect.getsource(ctx_mod)
        # Top-level (non-indented) import of engine.refusal must NOT appear
        top_level_import = "from token_world.engine.refusal"
        lines = src.splitlines()
        for line in lines:
            stripped = line.lstrip()
            # A top-level import would have no leading indent
            if line == stripped and top_level_import in line:
                pytest.fail(
                    f"context.py has a top-level import of engine.refusal: {line!r}. "
                    "Must be a lazy import inside the refuse() method."
                )
