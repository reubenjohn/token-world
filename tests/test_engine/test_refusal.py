"""Tests for RefusalTemplate (D-13).

Verifies that all known reason codes produce correct, grounded narratives,
that missing details are safe-substituted, and that unknown codes fall back
gracefully.
"""

from __future__ import annotations

from token_world.engine.refusal import RefusalTemplate


class TestRefusalTemplateKnownCodes:
    """Known reason codes produce well-formed narratives."""

    def test_no_viable_action_includes_action_text(self) -> None:
        narrative = RefusalTemplate.render("no_viable_action", {"action_text": "gragh the stone"})
        assert "gragh the stone" in narrative
        assert len(narrative) <= 200

    def test_no_such_target_includes_target_text(self) -> None:
        narrative = RefusalTemplate.render("no_such_target", {"target_text": "ghost lantern"})
        assert "ghost lantern" in narrative
        assert len(narrative) <= 200

    def test_low_confidence_includes_action_text(self) -> None:
        narrative = RefusalTemplate.render("low_confidence", {"action_text": "flurble the wizard"})
        assert "flurble the wizard" in narrative
        assert len(narrative) <= 200

    def test_mechanic_check_failed_includes_reason(self) -> None:
        narrative = RefusalTemplate.render(
            "mechanic_check_failed", {"reason": "your hands are full"}
        )
        assert "your hands are full" in narrative
        assert len(narrative) <= 200

    def test_conservation_violation_includes_violated_property(self) -> None:
        narrative = RefusalTemplate.render("conservation_violation", {"violated_property": "coin"})
        assert "coin" in narrative
        assert len(narrative) <= 200

    def test_inventory_full_includes_target(self) -> None:
        narrative = RefusalTemplate.render("inventory_full", {"target": "golden idol"})
        assert "golden idol" in narrative
        assert len(narrative) <= 200

    def test_locked_includes_target(self) -> None:
        narrative = RefusalTemplate.render("locked", {"target": "iron gate"})
        assert "iron gate" in narrative
        assert len(narrative) <= 200

    def test_blocked_includes_reason(self) -> None:
        narrative = RefusalTemplate.render("blocked", {"reason": "a boulder"})
        assert "a boulder" in narrative
        assert len(narrative) <= 200


class TestRefusalTemplateSafeSubstitution:
    """Missing keys fall back to [key] placeholder, never KeyError."""

    def test_missing_detail_key_produces_placeholder(self) -> None:
        # no_such_target expects target_text; we omit it
        narrative = RefusalTemplate.render("no_such_target", {})
        assert "[target_text]" in narrative

    def test_missing_action_text_in_no_viable_action(self) -> None:
        narrative = RefusalTemplate.render("no_viable_action", {})
        assert "[action_text]" in narrative

    def test_partial_details_fills_what_is_present(self) -> None:
        narrative = RefusalTemplate.render("no_such_target", {"target_text": "broken mirror"})
        assert "broken mirror" in narrative
        # No [action_text] substitution because no_such_target doesn't use it
        assert "[target_text]" not in narrative


class TestRefusalTemplateUnknownCode:
    """Unknown reason codes degrade gracefully to fallback template."""

    def test_unknown_code_uses_fallback(self) -> None:
        narrative = RefusalTemplate.render("totally_unknown_reason", {})
        assert "totally_unknown_reason" in narrative

    def test_unknown_code_returns_string(self) -> None:
        result = RefusalTemplate.render("some_future_code", {"extra": "data"})
        assert isinstance(result, str)
        assert len(result) > 0


class TestRefusalTemplateReturnType:
    """render() always returns a non-empty string."""

    def test_returns_string(self) -> None:
        result = RefusalTemplate.render("no_viable_action", {"action_text": "test"})
        assert isinstance(result, str)

    def test_returns_nonempty(self) -> None:
        result = RefusalTemplate.render("no_viable_action", {})
        assert len(result) > 0

    def test_none_details_treated_as_empty(self) -> None:
        # details=None should be equivalent to details={}
        result_none = RefusalTemplate.render("locked", None)
        result_empty = RefusalTemplate.render("locked", {})
        assert result_none == result_empty
