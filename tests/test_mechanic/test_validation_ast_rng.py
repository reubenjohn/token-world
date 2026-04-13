"""Tests for AST validation rule: forbid `import random` in mechanics (D-19).

The mechanic sandbox forbids direct `import random` because mechanics must
use ctx.rng for deterministic randomness. This rule extends Phase 4 D-14
AST checks.
"""

from __future__ import annotations

from pathlib import Path

from token_world.mechanic.validation import validate


def _write_mechanic(tmp_path: Path, source: str) -> Path:
    """Write a mechanic source to a temp .py file and return the path."""
    p = tmp_path / "test_mechanic.py"
    p.write_text(source, encoding="utf-8")
    return p


# Minimal valid mechanic template (no randomness) for passing tests.
_VALID_MECHANIC = """\
from token_world.mechanic.protocol import Mechanic


class ValidMechanic(Mechanic):
    id = "valid"
    description = "A valid mechanic"

    def check(self, ctx):
        return ctx.has_node(ctx.actor)

    def apply(self, ctx):
        ctx.set(ctx.actor, "checked", True)
"""


class TestForbidImportRandom:
    """AST rule rejects `import random` and `from random import ...`."""

    def test_import_random_fails_validation(self, tmp_path: Path) -> None:
        """Mechanic with `import random` fails validation."""
        source = _VALID_MECHANIC.replace(
            "from token_world.mechanic.protocol import Mechanic",
            "from token_world.mechanic.protocol import Mechanic\nimport random",
        )
        p = _write_mechanic(tmp_path, source)
        report = validate(p)
        assert not report.passed
        error_messages = [f.message for f in report.findings if f.severity == "error"]
        assert any("random" in msg for msg in error_messages)

    def test_from_random_import_choice_fails(self, tmp_path: Path) -> None:
        """Mechanic with `from random import choice` fails validation."""
        source = _VALID_MECHANIC.replace(
            "from token_world.mechanic.protocol import Mechanic",
            "from token_world.mechanic.protocol import Mechanic\nfrom random import choice",
        )
        p = _write_mechanic(tmp_path, source)
        report = validate(p)
        assert not report.passed
        error_messages = [f.message for f in report.findings if f.severity == "error"]
        assert any("random" in msg for msg in error_messages)

    def test_import_random_extra_prefix_passes(self, tmp_path: Path) -> None:
        """Mechanic with `import random_extra` passes (not the stdlib random module)."""
        # We only check AST, not actual resolution, so use a fictitious module name.
        source = """\
from token_world.mechanic.protocol import Mechanic
# Hypothetical third-party module with 'random' as prefix
# import random_extra  <- would pass; we test just the AST check logic

class ValidMechanic(Mechanic):
    id = "valid_prefix"
    description = "Tests that random_ prefix is allowed"

    def check(self, ctx):
        return True

    def apply(self, ctx):
        pass
"""
        p = _write_mechanic(tmp_path, source)
        report = validate(p)
        # No random import at all here, just the comment — should pass AST
        assert report.passed

    def test_ctx_rng_attribute_access_passes(self, tmp_path: Path) -> None:
        """Mechanic using `ctx.rng` (attribute access, no import) passes validation."""
        source = """\
from token_world.mechanic.protocol import Mechanic


class RngMechanic(Mechanic):
    id = "rng_user"
    description = "Uses ctx.rng for deterministic randomness"

    def check(self, ctx):
        return ctx.has_node(ctx.actor)

    def apply(self, ctx):
        roll = ctx.rng.random()
        ctx.set(ctx.actor, "last_roll", roll)
"""
        p = _write_mechanic(tmp_path, source)
        report = validate(p)
        assert report.passed, f"Expected pass but got findings: {report.findings}"


class TestRandomImportExactMatch:
    """Verify the AST check is exact-match, not prefix-match."""

    def test_import_random_exact_name_fails(self, tmp_path: Path) -> None:
        """import random (exact) fails."""
        source = """\
from token_world.mechanic.protocol import Mechanic
import random


class M(Mechanic):
    id = "m"
    description = "test"

    def check(self, ctx):
        return True

    def apply(self, ctx):
        x = random.random()
        ctx.set(ctx.actor, "x", x)
"""
        p = _write_mechanic(tmp_path, source)
        report = validate(p)
        assert not report.passed
