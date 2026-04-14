"""Quality scorer: compute QualityReport for a universe.

Single-pass scanner over tick_summaries/ticks/*.json plus a SQLite query
against graph_snapshots for graph fan-out. Degrades gracefully on missing
or malformed data — never raises.

All 8 dimensions from docs/quality/sim-quality-rubric.md are implemented.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from token_world.inspect._shared import iter_tick_files, read_json_file
from token_world.quality.report import DimensionResult, QualityReport
from token_world.quality.thresholds import (
    CLUSTER_RED,
    CLUSTER_WARN,
    COHERENCE_RATE_GREEN,
    COHERENCE_RATE_RED,
    COHERENCE_STREAK_GREEN,
    COHERENCE_STREAK_RED,
    CONSERVATION_GREEN,
    CONSERVATION_RED,
    FANOUT_GREEN,
    FANOUT_RED,
    GROUNDEDNESS_GREEN,
    GROUNDEDNESS_RED,
    MARKERS,
    STABILITY_GREEN,
    STABILITY_RED,
    SUBTYPE_RATE_WARN,
    VOCAB_RATE_MAX_GREEN,
    VOCAB_RATE_MIN_GREEN,
    VOCAB_RATE_RED_HIGH,
    VOCAB_STAGNANT_TICKS,
    compute_verdict,
)


def score(universe_dir: Path, *, slug: str, last: int = 50) -> QualityReport:
    """Compute QualityReport for the last ``last`` ticks of the universe.

    Degrades gracefully:
    - Missing tick dir -> INSUFFICIENT_DATA, tick_count=0.
    - 0 parseable payloads -> INSUFFICIENT_DATA, tick_count=0.
    - Missing universe.db -> graph fan-out returns OK with slope=0.0.
    """
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    files = iter_tick_files(ticks_dir, since=last)

    if not files:
        return QualityReport(slug=slug, window=last, tick_count=0, verdict="INSUFFICIENT_DATA")

    raw = [read_json_file(f) for f in files]
    payloads: list[dict[str, Any]] = [p for p in raw if p is not None]

    if not payloads:
        return QualityReport(slug=slug, window=last, tick_count=0, verdict="INSUFFICIENT_DATA")

    dimensions = [
        _score_groundedness(payloads),
        _score_character_stability(payloads),
        _score_action_coherence(payloads),
        _score_refusal_cluster(payloads),
        _score_vocabulary_growth(payloads),
        _score_conservation_drift(payloads),
        _score_graph_fanout(universe_dir, payloads),
        _score_novel_subtype_rate(payloads),
    ]

    verdict = compute_verdict(dimensions)

    return QualityReport(
        slug=slug,
        window=last,
        tick_count=len(payloads),
        dimensions=dimensions,
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# Private dimension scorers
# ---------------------------------------------------------------------------


def _score_groundedness(payloads: list[dict[str, Any]]) -> DimensionResult:
    """Proxy groundedness: tick is grounded if backed by mutations, refused, or yielded.

    Ungrounded = executed (not refused, not yielded) AND mutations.count == 0.
    """
    total = len(payloads)
    grounded = 0
    for p in payloads:
        refused = p.get("refused", False)
        yielded = p.get("yielded", False)
        mutations_count = p.get("mutations", {}).get("count", 0)
        if refused or yielded or mutations_count > 0:
            grounded += 1

    rate = grounded / total
    detail = f"{grounded}/{total} grounded"

    if rate >= GROUNDEDNESS_GREEN:
        status = "OK"
    elif rate < GROUNDEDNESS_RED:
        status = "FAIL"
    else:
        status = "WARN"

    return DimensionResult(name="Groundedness", status=status, score=rate, detail=detail)


def _score_character_stability(payloads: list[dict[str, Any]]) -> DimensionResult:
    """Scan action_text for meta-narration markers indicating immersion break."""
    total = len(payloads)
    breaks = 0
    for p in payloads:
        action_text = p.get("action_text", "").lower()
        if any(m in action_text for m in MARKERS):
            breaks += 1

    rate = 1.0 - (breaks / total)
    detail = f"{breaks} break{'s' if breaks != 1 else ''}"

    if rate >= STABILITY_GREEN:
        status = "OK"
    elif rate < STABILITY_RED:
        status = "FAIL"
    else:
        status = "WARN"

    return DimensionResult(name="Character stability", status=status, score=rate, detail=detail)


def _score_action_coherence(payloads: list[dict[str, Any]]) -> DimensionResult:
    """Compute longest non-refuse streak + refuse rate per 10 ticks.

    Both must be in green for OK; either in red triggers FAIL; else WARN.
    """
    total = len(payloads)
    total_refuses = 0
    current_streak = 0
    longest_streak = 0

    for p in payloads:
        refused = p.get("refused", False)
        if refused:
            total_refuses += 1
            current_streak = 0
        else:
            current_streak += 1
            if current_streak > longest_streak:
                longest_streak = current_streak

    refuse_rate = (total_refuses / total) * 10.0
    detail = f"streak={longest_streak}  refuse_rate={refuse_rate:.1f}"

    # Determine status: streak and rate must both be green; either red = FAIL
    streak_green = longest_streak >= COHERENCE_STREAK_GREEN
    streak_red = longest_streak < COHERENCE_STREAK_RED
    rate_green = refuse_rate <= COHERENCE_RATE_GREEN
    rate_red = refuse_rate >= COHERENCE_RATE_RED

    if streak_red or rate_red:
        status = "FAIL"
    elif streak_green and rate_green:
        status = "OK"
    else:
        status = "WARN"

    return DimensionResult(
        name="Action coherence", status=status, score=float(longest_streak), detail=detail
    )


def _score_refusal_cluster(payloads: list[dict[str, Any]]) -> DimensionResult:
    """Track maximum consecutive refusal run in the window."""
    max_consecutive = 0
    current = 0

    for p in payloads:
        if p.get("refused", False):
            current += 1
            if current > max_consecutive:
                max_consecutive = current
        else:
            current = 0

    detail = f"max={max_consecutive}  (< {CLUSTER_RED})"

    if max_consecutive <= CLUSTER_WARN:
        status = "OK"
    elif max_consecutive >= CLUSTER_RED:
        status = "FAIL"
    else:
        status = "WARN"

    return DimensionResult(
        name="Refusal cluster", status=status, score=float(max_consecutive), detail=detail
    )


def _score_vocabulary_growth(payloads: list[dict[str, Any]]) -> DimensionResult:
    """Track novel mechanic IDs introduced; compute rate per 10 ticks.

    Stagnation: longest run without a new mechanic ID.
    """
    seen_ids: set[str] = set()
    novel_count = 0
    stagnant_run = 0
    longest_stagnant = 0

    for p in payloads:
        mechanic_id = p.get("matched_mechanic_id")
        if mechanic_id is not None and mechanic_id not in seen_ids:
            seen_ids.add(mechanic_id)
            novel_count += 1
            stagnant_run = 0
        else:
            stagnant_run += 1
            if stagnant_run > longest_stagnant:
                longest_stagnant = stagnant_run

    total = len(payloads)
    rate = novel_count / (total / 10.0) if total > 0 else 0.0
    stagnant = longest_stagnant >= VOCAB_STAGNANT_TICKS

    detail = f"{novel_count} novel mechanics  rate={rate:.1f}/10t"

    if stagnant or rate > VOCAB_RATE_RED_HIGH:
        status = "FAIL"
    elif VOCAB_RATE_MIN_GREEN <= rate <= VOCAB_RATE_MAX_GREEN:
        status = "OK"
    else:
        status = "WARN"

    return DimensionResult(name="Vocabulary growth", status=status, score=rate, detail=detail)


def _score_conservation_drift(payloads: list[dict[str, Any]]) -> DimensionResult:
    """Count ticks where refusal_reason contains 'conservation'."""
    total = len(payloads)
    conservation_count = 0

    for p in payloads:
        if p.get("refused", False):
            reason = p.get("refusal_reason") or ""
            if "conservation" in reason.lower():
                conservation_count += 1

    rollback_rate = conservation_count / total
    detail = f"{conservation_count}/{total} rollbacks"

    if rollback_rate <= CONSERVATION_GREEN:
        status = "OK"
    elif rollback_rate >= CONSERVATION_RED:
        status = "FAIL"
    else:
        status = "WARN"

    return DimensionResult(
        name="Conservation drift",
        status=status,
        score=rollback_rate,
        detail=detail,
    )


def _score_graph_fanout(universe_dir: Path, payloads: list[dict[str, Any]]) -> DimensionResult:
    """Compute graph fan-out slope from graph_snapshots table.

    Degrades gracefully: missing DB or < 2 snapshots returns OK with slope=0.0.
    """
    db_path = universe_dir / "universe.db"

    if not db_path.exists():
        return DimensionResult(
            name="Graph fan-out",
            status="OK",
            score=0.0,
            detail="insufficient history",
        )

    try:
        with sqlite3.connect(str(db_path)) as conn:
            rows = conn.execute(
                "SELECT tick_id, node_count, edge_count "
                "FROM graph_snapshots ORDER BY tick_id DESC LIMIT 5"
            ).fetchall()
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        return DimensionResult(
            name="Graph fan-out",
            status="OK",
            score=0.0,
            detail="insufficient history",
        )

    if len(rows) < 2:
        return DimensionResult(
            name="Graph fan-out",
            status="OK",
            score=0.0,
            detail="insufficient history",
        )

    # Compute fan-out (edges/nodes) per snapshot; slope across history
    # rows are DESC so reverse for chronological order
    history = list(reversed(rows))

    def _fanout(row: tuple[Any, ...]) -> float:
        tick_id, node_count, edge_count = row
        return edge_count / node_count if node_count > 0 else 0.0

    first_tick = history[0][0]
    last_tick = history[-1][0]
    elapsed_ticks = (last_tick - first_tick) if (last_tick - first_tick) != 0 else 1

    first_fanout = _fanout(history[0])
    last_fanout = _fanout(history[-1])
    slope = (last_fanout - first_fanout) / elapsed_ticks * 10.0  # per 10 ticks

    detail = f"slope={slope:.4f}/10t  (last {len(history)} snapshots)"

    if slope >= FANOUT_GREEN:
        status = "OK"
    elif slope <= FANOUT_RED:
        status = "FAIL"
    else:
        status = "WARN"

    return DimensionResult(name="Graph fan-out", status=status, score=slope, detail=detail)


def _score_novel_subtype_rate(payloads: list[dict[str, Any]]) -> DimensionResult:
    """Track distinct new subtype values introduced via mutations.

    WARN if rate==0 and window >= 30 ticks. No FAIL (informational dimension).
    """
    seen_subtypes: set[str] = set()
    new_subtypes = 0
    total = len(payloads)

    for p in payloads:
        mutation_list = p.get("mutations", {}).get("list", [])
        for mutation in mutation_list:
            if len(mutation) >= 4 and mutation[1] == "subtype":
                new_value = mutation[3]
                if new_value is not None and new_value not in seen_subtypes:
                    seen_subtypes.add(new_value)
                    new_subtypes += 1

    rate = new_subtypes / (total / 10.0) if total > 0 else 0.0
    detail = f"{new_subtypes} new subtype{'s' if new_subtypes != 1 else ''}  rate={rate:.1f}/10t"

    status = "WARN" if rate == SUBTYPE_RATE_WARN and total >= 30 else "OK"

    return DimensionResult(name="Novel subtype rate", status=status, score=rate, detail=detail)
