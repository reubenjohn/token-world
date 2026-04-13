"""Contract-regression guard for the harness verb->mechanic matcher.

The matcher under test lives at
``tests/test_integration/test_use_cases.py::match_mechanic_for_verb``
and is the sole router between a use-case action's classified verb
and a voluntary :class:`~token_world.mechanic.MechanicInfo`. Its v1
contract is documented in that helper's docstring; this test file
pins the behavior so any future extension is reviewable in one place.

Extension Policy (mandated by
``.planning/phases/04-llm-mechanic-generation/04-REVIEWS.md`` HIGH #1):

Any future extension (alias lookup, tag fallback, ``blocked_by``
routing, refusal-narrative synthesis, classifier-driven routing) MUST
ship with a new test case in THIS FILE -- plan-local matcher changes
in seed plans (04-06..04-11) are explicitly disallowed. When the v1
stub is replaced by Phase 5's classifier-driven router, retire the
helper in favor of that router; keep this file as the
contract-regression guard.

See
``.planning/phases/04-llm-mechanic-generation/04-04-SUMMARY.md``
"Harness Matcher -- Extension Contract" for the owner-plan table.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tests.test_integration.test_use_cases import match_mechanic_for_verb
from token_world.mechanic import MechanicInfo, MechanicRegistry

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _write_mechanic_module(
    path: Path,
    *,
    cls_name: str,
    id_: str,
    voluntary: bool,
    tags: list[str] | None = None,
) -> None:
    """Write a minimal flat-seed mechanic module to *path*.

    Matches the fixture pattern used in ``test_registry.py``.
    """
    tags = tags or []
    path.write_text(
        textwrap.dedent(
            f"""\
            from __future__ import annotations

            from token_world.graph import Mutation
            from token_world.mechanic.protocol import CheckResult, Mechanic


            class {cls_name}(Mechanic):
                id = {id_!r}
                description = "Test mechanic {id_}"
                voluntary = {voluntary!r}
                tags = {tags!r}

                def check(self, ctx) -> CheckResult:
                    return CheckResult(passed=True)

                def apply(self, ctx) -> list[Mutation]:
                    return []
            """
        )
    )


@pytest.fixture
def empty_registry(tmp_path: Path) -> MechanicRegistry:
    """Registry over an empty ``mechanics/`` directory."""
    mechanics = tmp_path / "mechanics"
    mechanics.mkdir()
    return MechanicRegistry(mechanics, universe_dir=tmp_path)


@pytest.fixture
def move_only_registry(tmp_path: Path) -> MechanicRegistry:
    """Registry with a single voluntary ``move`` mechanic."""
    mechanics = tmp_path / "mechanics"
    mechanics.mkdir()
    _write_mechanic_module(
        mechanics / "move.py",
        cls_name="MoveMechanic",
        id_="move",
        voluntary=True,
    )
    return MechanicRegistry(mechanics, universe_dir=tmp_path)


@pytest.fixture
def mixed_registry(tmp_path: Path) -> MechanicRegistry:
    """Registry with one involuntary ``decay`` and one voluntary ``move``."""
    mechanics = tmp_path / "mechanics"
    mechanics.mkdir()
    _write_mechanic_module(
        mechanics / "decay.py",
        cls_name="DecayMechanic",
        id_="decay",
        voluntary=False,
    )
    _write_mechanic_module(
        mechanics / "move.py",
        cls_name="MoveMechanic",
        id_="move",
        voluntary=True,
    )
    return MechanicRegistry(mechanics, universe_dir=tmp_path)


# ---------------------------------------------------------------------------
# The contract-regression suite
# ---------------------------------------------------------------------------


class TestMatchMechanicForVerb:
    """v1 contract for :func:`match_mechanic_for_verb`.

    Every behavior described in the helper's docstring is pinned here.
    Future extensions (alias, tag fallback, blocked_by routing,
    refusal narratives, classifier-driven routing) add a new test
    BEFORE the matcher changes.
    """

    def test_returns_none_for_empty_verb(self, move_only_registry: MechanicRegistry) -> None:
        """Empty-string verb short-circuits to ``None`` before scan."""
        assert match_mechanic_for_verb(move_only_registry, "") is None

    def test_returns_none_for_no_match(self, move_only_registry: MechanicRegistry) -> None:
        """Verb that matches no voluntary id returns ``None``."""
        assert match_mechanic_for_verb(move_only_registry, "unknown") is None

    def test_returns_none_for_empty_registry(self, empty_registry: MechanicRegistry) -> None:
        """An empty registry always returns ``None``, regardless of verb."""
        assert match_mechanic_for_verb(empty_registry, "anything") is None

    def test_returns_first_voluntary_match_on_id_equals_verb(
        self, move_only_registry: MechanicRegistry
    ) -> None:
        """``verb == info.id`` on a voluntary mechanic returns that info."""
        info = match_mechanic_for_verb(move_only_registry, "move")
        assert info is not None
        assert info.id == "move"

    def test_ignores_involuntary_mechanics(self, mixed_registry: MechanicRegistry) -> None:
        """An involuntary mechanic whose id equals *verb* is not returned.

        Involuntary mechanics are driven by the ChainExecutionEngine, not
        classified-action routing. ``verb="decay"`` with a registry that
        holds an involuntary ``decay`` mechanic must resolve to ``None``.
        """
        assert match_mechanic_for_verb(mixed_registry, "decay") is None

    def test_mixed_registry_still_matches_voluntary(
        self,
        mixed_registry: MechanicRegistry,
    ) -> None:
        """A voluntary mechanic in a mixed registry still matches."""
        info = match_mechanic_for_verb(mixed_registry, "move")
        assert info is not None
        assert info.id == "move"
        assert info.voluntary is True

    def test_returns_mechanicinfo_instance(self, move_only_registry: MechanicRegistry) -> None:
        """The return type is a :class:`MechanicInfo` with matching fields."""
        info = match_mechanic_for_verb(move_only_registry, "move")
        assert isinstance(info, MechanicInfo)
        assert info.id == "move"
        assert info.voluntary is True

    @pytest.mark.skip(
        reason=(
            "MechanicRegistry enforces unique ids (T-04-REGISTRY-SHADOWING): "
            "loading two modules with the same id raises ValueError at scan "
            "time, so the 'multiple voluntary matches' case cannot occur in "
            "practice. Documented here so the invariant is visible in the "
            "contract guard; if dedup is ever relaxed, replace this skip "
            "with a real first-match-wins test."
        )
    )
    def test_multiple_voluntary_matches_returns_first(self) -> None:
        """Placeholder for first-match-wins semantics (currently unreachable).

        Documented as ``pytest.skip`` because the registry's duplicate-id
        invariant makes multiple matches unreachable in the v1 stub. Kept
        as a named case so a future relaxation of dedup is forced to
        revisit this contract before shipping.
        """
