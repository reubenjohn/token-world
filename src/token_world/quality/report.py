"""QualityReport and DimensionResult dataclasses + renderers.

Mirrors the StatsReport pattern: thin dataclasses here, all computation
in scorer.py. Two renderers: render_table() and render_json().
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal

Status = Literal["OK", "WARN", "FAIL", "UNKNOWN"]
Verdict = Literal["HEALTHY", "DEGRADED", "FAILED", "INSUFFICIENT_DATA"]


@dataclass(slots=True)
class DimensionResult:
    """Result for a single rubric dimension."""

    name: str
    status: Status
    score: float
    detail: str


@dataclass(slots=True)
class QualityReport:
    """Quality scorecard across all 8 rubric dimensions."""

    slug: str
    window: int = 50
    tick_count: int = 0
    dimensions: list[DimensionResult] = field(default_factory=list)
    verdict: Verdict = "INSUFFICIENT_DATA"


def render_table(report: QualityReport) -> str:
    """Return a multi-line string scorecard matching the rubric format."""
    lines: list[str] = []
    lines.append(f"{report.slug} · last {report.tick_count} ticks")

    if report.verdict == "INSUFFICIENT_DATA":
        lines.append("")
        lines.append("  Verdict: INSUFFICIENT_DATA")
        lines.append("")
        return "\n".join(lines)

    lines.append("")
    for dim in report.dimensions:
        status_tag = f"[{dim.status}]"
        lines.append(f"  {status_tag:<7} {dim.name:<22} {dim.score:6.2f}   ({dim.detail})")

    lines.append("")
    lines.append(f"  Verdict: {report.verdict}")
    lines.append("")
    return "\n".join(lines)


def render_json(report: QualityReport) -> str:
    """Return JSON string consumable by CI and dashboard."""
    data = {
        "slug": report.slug,
        "window": report.window,
        "tick_count": report.tick_count,
        "verdict": report.verdict,
        "dimensions": [
            {
                "name": dim.name,
                "status": dim.status,
                "score": dim.score,
                "detail": dim.detail,
            }
            for dim in report.dimensions
        ],
    }
    return json.dumps(data, indent=2)
