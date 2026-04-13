"""ConservationChecker — verify mutations don't violate conservation laws (D-16, GAP-ENG06).

Loads a list of conserved property names from universe/conservation.yaml. After
the orchestrator collects all mutations from a tick's chain execution, calls
``checker.verify(mutations)`` and inspects the verdict. On violation, the
orchestrator (Plan 05-08) rolls the graph back via ``KnowledgeGraph.restore(snapshot_id)``
and returns a refusal narrative via ``RefusalTemplate.render("conservation_violation", ...)``.

Empty default: an absent or empty conservation.yaml yields a disabled checker
that returns ok() in O(1) (D-16 — opt-in per universe).

Trust-boundary notes (T-05-CONS-CONFIG-INJECT, T-05-CONS-NUMERIC-CRASH):
- Malformed YAML / non-mapping root / non-list conserved_properties → log warning,
  return disabled checker (soft-fail).
- Non-numeric property values for conserved properties → warnings.warn + skip mutation
  rather than crashing.
- T-05-CONS-BYPASS: only ``set_property`` mutations are checked. ``add_node``,
  ``add_edge``, ``remove_node``, ``remove_edge`` are graph-structural operations —
  not value-changing. v2 may extend if needed.

Hot-reload: ConservationChecker is instantiated once at engine init (Plan 05-08).
Operators must restart the engine to pick up conservation.yaml changes.
"""

from __future__ import annotations

import logging
import warnings
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from token_world.graph import Mutation

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ConservationVerdict:
    """Result of a conservation check.

    Attributes:
        violations: Map of conserved-property-name -> net delta. Empty when no
            violation. The orchestrator passes ``next(iter(violations))`` to
            the refusal template's ``violated_property`` slot.
    """

    violations: dict[str, float] = field(default_factory=dict)

    @property
    def is_violation(self) -> bool:
        return bool(self.violations)

    @classmethod
    def ok(cls) -> ConservationVerdict:
        return cls(violations={})

    @classmethod
    def violation(cls, deltas: dict[str, float]) -> ConservationVerdict:
        return cls(violations=dict(deltas))


@dataclass(slots=True)
class ConservationChecker:
    """Verifies that mutations preserve declared conserved properties.

    Instantiated once at engine init from ``conservation.yaml``. The checker
    is stateless w.r.t. graph state — it operates purely on the mutation list
    produced by the current tick. Rollback and refusal are the orchestrator's
    responsibility (Plan 05-08).
    """

    conserved_properties: frozenset[str]

    @classmethod
    def from_yaml(cls, config_path: Path) -> ConservationChecker:
        """Load conserved property names from conservation.yaml.

        Soft-fail: missing file, malformed YAML, or root-not-mapping all yield
        a disabled checker (no enforcement). Mirrors ``load_engine_config``.
        """
        if not config_path.exists():
            return cls(conserved_properties=frozenset())
        try:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            logger.warning(
                "Malformed conservation.yaml at %s: %s — disabling enforcement",
                config_path,
                e,
            )
            return cls(conserved_properties=frozenset())
        if not isinstance(raw, dict):
            logger.warning(
                "conservation.yaml root is not a mapping at %s — disabling enforcement",
                config_path,
            )
            return cls(conserved_properties=frozenset())
        names = raw.get("conserved_properties", [])
        if not isinstance(names, list):
            logger.warning(
                "conservation.yaml conserved_properties is not a list — disabling enforcement"
            )
            return cls(conserved_properties=frozenset())
        # Drop non-string entries defensively
        clean = {n for n in names if isinstance(n, str) and n}
        return cls(conserved_properties=frozenset(clean))

    def verify(self, mutations: list[Mutation]) -> ConservationVerdict:
        """Return verdict for the given mutations.

        Disabled checker (empty conserved_properties) returns ok() in O(1)
        without iterating mutations (D-16 zero-cost opt-out).
        """
        if not self.conserved_properties:
            return ConservationVerdict.ok()

        deltas: dict[str, float] = defaultdict(float)
        for m in mutations:
            if m.type != "set_property":
                continue
            if m.property is None or m.property not in self.conserved_properties:
                continue
            try:
                old = float(m.old_value) if m.old_value is not None else 0.0
                new = float(m.new_value) if m.new_value is not None else 0.0
            except (TypeError, ValueError):
                warnings.warn(
                    f"Conservation: skipping non-numeric mutation on conserved property "
                    f"{m.property!r} (old={m.old_value!r}, new={m.new_value!r})",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            deltas[m.property] += new - old

        violations = {p: d for p, d in deltas.items() if d != 0}
        if violations:
            return ConservationVerdict.violation(violations)
        return ConservationVerdict.ok()
