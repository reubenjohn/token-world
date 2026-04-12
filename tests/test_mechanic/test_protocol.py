"""Tests for Mechanic ABC and CheckResult."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from token_world.graph import Mutation
from token_world.mechanic import CheckResult, Mechanic, MechanicContext


class TestMechanicABC:
    """Tests for the Mechanic abstract base class."""

    def test_abc_enforcement_no_methods(self) -> None:
        """Subclass without check() or apply() raises TypeError on instantiation."""

        class Incomplete(Mechanic):
            id = "incomplete"
            description = "missing both"

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_abc_enforcement_missing_apply(self) -> None:
        """Subclass with only check() raises TypeError (missing apply)."""

        class MissingApply(Mechanic):
            id = "missing_apply"
            description = "has check but no apply"

            def check(self, ctx: MechanicContext) -> CheckResult:
                return CheckResult(passed=True)

        with pytest.raises(TypeError):
            MissingApply()  # type: ignore[abstract]

    def test_abc_enforcement_missing_check(self) -> None:
        """Subclass with only apply() raises TypeError (missing check)."""

        class MissingCheck(Mechanic):
            id = "missing_check"
            description = "has apply but no check"

            def apply(self, ctx: MechanicContext) -> list[Mutation]:
                return []

        with pytest.raises(TypeError):
            MissingCheck()  # type: ignore[abstract]

    def test_valid_subclass(self) -> None:
        """Valid concrete subclass instantiates with expected attributes."""
        from tests.test_mechanic.conftest import DummyMechanic

        m = DummyMechanic()
        assert m.id == "dummy"
        assert m.description == "test mechanic"
        assert m.voluntary is True

    def test_voluntary_default_true(self) -> None:
        """Voluntary defaults to True."""
        from tests.test_mechanic.conftest import DummyMechanic

        assert DummyMechanic.voluntary is True

    def test_watches_default_empty(self) -> None:
        """watches() returns empty list by default for voluntary mechanics."""
        from tests.test_mechanic.conftest import DummyMechanic

        m = DummyMechanic()
        assert m.watches() == []


class TestCheckResult:
    """Tests for the CheckResult dataclass."""

    def test_passed_true_empty_reasons(self) -> None:
        """CheckResult(passed=True) has empty reasons list."""
        result = CheckResult(passed=True)
        assert result.passed is True
        assert result.reasons == []

    def test_passed_false_with_reasons(self) -> None:
        """CheckResult with reasons preserves them."""
        result = CheckResult(passed=False, reasons=["not enough mana", "too far"])
        assert result.passed is False
        assert result.reasons == ["not enough mana", "too far"]

    def test_frozen(self) -> None:
        """CheckResult is frozen (immutable)."""
        result = CheckResult(passed=True)
        with pytest.raises(FrozenInstanceError):
            result.passed = False  # type: ignore[misc]
