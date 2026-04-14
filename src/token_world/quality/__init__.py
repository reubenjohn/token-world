"""Quality scoring subpackage for Token World simulations.

Computes all 8 rubric dimensions from docs/quality/sim-quality-rubric.md.
Canonical producer rule: compute once in this package, read many (CLI, dashboard, CI).
"""

from token_world.quality.report import DimensionResult, QualityReport
from token_world.quality.scorer import score

__all__ = ["DimensionResult", "QualityReport", "score"]
