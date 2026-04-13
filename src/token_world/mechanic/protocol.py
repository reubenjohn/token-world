"""Mechanic protocol: ABC and CheckResult."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from token_world.graph import Mutation

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext
    from token_world.mechanic.matchers import Matcher


@dataclass(frozen=True)
class CheckResult:
    """Result of a mechanic precondition check.

    Attributes:
        passed: Whether preconditions are met.
        reasons: Human-readable reasons (e.g. why check failed). Empty by default.
    """

    passed: bool
    reasons: list[str] = field(default_factory=list)


class Mechanic(ABC):
    """Abstract base class for all mechanics.

    Subclasses must define class-level attributes ``id`` and ``description``,
    and implement :meth:`check` and :meth:`apply`.

    Attributes:
        id: Unique mechanic identifier.
        description: Human-readable description.
        voluntary: Whether this mechanic is triggered by agent action (True)
            or reactively by graph mutations (False). Defaults to True.
        tags: Classification tags for querying (e.g. ``["spatial"]``). Defaults
            to an empty list. Per D-04, ``tags`` supersedes ``meta.yaml`` as
            the single source of truth for mechanic classification.
    """

    id: str
    description: str
    voluntary: bool = True
    tags: list[str] = []

    @abstractmethod
    def check(self, ctx: MechanicContext) -> CheckResult:
        """Evaluate preconditions against graph state.

        Args:
            ctx: The mechanic execution context (DSL wrapper around the graph).

        Returns:
            CheckResult indicating whether the mechanic can fire.
        """

    @abstractmethod
    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        """Apply the mechanic's side effects to the graph.

        Args:
            ctx: The mechanic execution context.

        Returns:
            List of mutations that were applied.
        """

    def watches(self) -> list[Matcher]:
        """Declare matchers for involuntary mechanic triggering.

        Voluntary mechanics return an empty list (default). Involuntary mechanics
        override this to declare which graph mutations trigger them.

        Returns:
            List of matcher objects.
        """
        return []
