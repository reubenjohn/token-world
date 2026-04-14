"""Threshold constants for all 8 quality rubric dimensions.

Constants match docs/quality/sim-quality-rubric.md verbatim.
Verdict computation logic lives here to keep scorer.py pure computation.
"""

from __future__ import annotations

from token_world.quality.report import DimensionResult, Verdict

# ---------------------------------------------------------------------------
# 1. Groundedness proxy (mutation-backed execution rate)
# ---------------------------------------------------------------------------
GROUNDEDNESS_GREEN = 0.95
GROUNDEDNESS_RED = 0.85

# ---------------------------------------------------------------------------
# 2. Character stability
# ---------------------------------------------------------------------------
STABILITY_GREEN = 0.98
STABILITY_RED = 0.90

# Marker substrings indicating the agent has broken immersion.
MARKERS = ["framework", "yield", "mechanic", "system prompt", "operator", "scenario"]

# ---------------------------------------------------------------------------
# 3. Action coherence
# ---------------------------------------------------------------------------
COHERENCE_STREAK_GREEN = 15
COHERENCE_STREAK_RED = 5
COHERENCE_RATE_GREEN = 1.5  # max refuses per 10 ticks (green)
COHERENCE_RATE_RED = 4.0  # min refuses per 10 ticks (red)

# ---------------------------------------------------------------------------
# 4. Refusal cluster alarm
# ---------------------------------------------------------------------------
CLUSTER_WARN = 2  # max consecutive refuses for OK; above = WARN
CLUSTER_RED = 5  # at or above = FAIL

# ---------------------------------------------------------------------------
# 5. Vocabulary growth (novel mechanic IDs proxy)
# ---------------------------------------------------------------------------
VOCAB_RATE_MIN_GREEN = 0.5
VOCAB_RATE_MAX_GREEN = 2.5
VOCAB_RATE_RED_HIGH = 4.0
VOCAB_STAGNANT_TICKS = 30  # 0 novel mechanics for this many ticks = RED

# ---------------------------------------------------------------------------
# 6. Conservation drift
# ---------------------------------------------------------------------------
CONSERVATION_GREEN = 0.02
CONSERVATION_RED = 0.10

# ---------------------------------------------------------------------------
# 7. Graph fan-out slope (per 10 ticks)
# ---------------------------------------------------------------------------
FANOUT_GREEN = 0.0  # slope >= 0 is green
FANOUT_RED = -0.02  # slope <= -0.02 is fail

# ---------------------------------------------------------------------------
# 8. Novel subtype rate (informational; WARN-only gate at zero)
# ---------------------------------------------------------------------------
SUBTYPE_RATE_WARN = 0.0  # no new subtypes ever = WARN (not FAIL)


# ---------------------------------------------------------------------------
# Verdict computation
# ---------------------------------------------------------------------------


def compute_verdict(dimensions: list[DimensionResult]) -> Verdict:
    """Derive overall verdict from dimension statuses.

    - INSUFFICIENT_DATA if no dimensions provided.
    - FAILED if any dimension is FAIL.
    - DEGRADED if any dimension is WARN (and no FAIL).
    - HEALTHY otherwise (all OK or UNKNOWN).
    """
    if not dimensions:
        return "INSUFFICIENT_DATA"
    statuses = {d.status for d in dimensions}
    if "FAIL" in statuses:
        return "FAILED"
    if "WARN" in statuses:
        return "DEGRADED"
    return "HEALTHY"
