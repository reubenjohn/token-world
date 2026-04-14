"""Regression tests for ENGINE-05: doubled 'You try, but' wrapper bug.

RefusalTemplate.render() must be idempotent — if the reason string already
contains the wrapper prefix, it must not be doubled.

Tests 2 and 3 MUST FAIL before the fix in refusal.py (RED phase).
"""

from __future__ import annotations

import pytest

from token_world.engine.refusal import RefusalTemplate


class TestSingleWrapperInvariant:
    """A refused tick's observation contains 'You try, but' exactly once."""

    def test_clean_reason_wraps_once(self) -> None:
        """Test 1: Normal path — reason has no pre-existing prefix."""
        result = RefusalTemplate.render(
            "mechanic_check_failed", {"reason": "the knife is too dull"}
        )
        assert result == "You try, but the knife is too dull."
        assert result.count("You try, but") == 1

    def test_prewrapped_reason_not_doubled(self) -> None:
        """Test 2 (RED before fix): reason already starts with 'You try, but '."""
        result = RefusalTemplate.render(
            "mechanic_check_failed",
            {"reason": "You try, but the knife is too dull"},
        )
        # Must NOT produce "You try, but You try, but the knife is too dull."
        assert result.count("You try, but") == 1
        assert result == "You try, but the knife is too dull."

    def test_doubly_nested_reason_collapses(self) -> None:
        """Test 3 (RED before fix): reason contains doubled prefix — collapse all nesting."""
        result = RefusalTemplate.render(
            "mechanic_check_failed",
            {"reason": "You try, but You try, but nested"},
        )
        assert result.count("You try, but") == 1
        assert result == "You try, but nested."

    def test_non_mechanic_check_failed_unchanged(self) -> None:
        """Test 4: Non-mechanic_check_failed template is not affected."""
        result = RefusalTemplate.render("no_viable_action", {"action_text": "fly"})
        assert "fly" in result
        assert isinstance(result, str)
        assert len(result) > 0
        # This template does not start with "You try, but" — that's fine
        assert result.count("You try, but") <= 1

    @pytest.mark.parametrize(
        "reason",
        [
            "the knife is too dull",
            "You try, but the knife is too dull",
            "You try, but You try, but nested",
            "the door is locked",
            "You try, but your arms are too short",
        ],
    )
    def test_mechanic_check_failed_always_single_wrapper(self, reason: str) -> None:
        """Test 5: str.count('You try, but') == 1 for all mechanic_check_failed renders."""
        result = RefusalTemplate.render("mechanic_check_failed", {"reason": reason})
        assert result.count("You try, but") == 1, f"Expected single wrapper, got: {result!r}"
