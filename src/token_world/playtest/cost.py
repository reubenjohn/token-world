"""Per-universe cost dashboard.

Aggregates USD spend and token usage from a universe's ``tick_summaries/``
directory. Read-only: never mutates on-disk artefacts. Pure stdlib (no new
dependencies per CLI-cost phase constraints).

Data sources (read-only):
- ``<universe>/tick_summaries/ticks/tick_*.json`` — per-tick TickSummary files.
  Each file exposes ``llm_cost_usd_by_stage`` (``{stage: usd}``) and
  ``llm_tokens_by_stage`` (``{stage: {"in": int, "out": int}}``).
- ``<universe>/tick_summaries/batches/*.json`` — BatchSummary schema v2 does
  NOT currently carry usage/cost; we scan for optional fields
  (``llm_cost_usd_by_stage`` / ``llm_tokens_by_stage`` / ``total_cost_usd`` /
  ``total_input_tokens`` / ``total_output_tokens``) so forward-compatible
  writers that add them are picked up automatically.
- ``<universe>/tick_summaries/epochs/*.json`` — same forward-compat shape.

The "CLI subscription" signal (Phase 07.1 D-07): when the simulation runs
via the ``claude-cli`` backend, tokens are not exposed and costs stay 0.0.
Per-tick we classify a stage as "CLI-subscription" when all three of
``cost``, ``in_tokens``, ``out_tokens`` are zero. Such ticks are reported
as a distinct count so that a $0.00 total is not mistaken for "nothing ran".

Stage -> model-label mapping (D-02, engine constants): the classifier stage
is always the Haiku model in effect at the time of the run; the observer
stage is always the Sonnet model. Tick summaries do NOT persist the model
ID, so we use pinned labels (matching ``engine/classifier.py::_MODEL`` and
``engine/observer.py::_MODEL`` at the time this module was written) and the
labels are cosmetic — they do not feed any computation.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Pinned stage -> model-label pairs (cosmetic; used only for table/JSON output).
# Kept in sync with engine/classifier.py::_MODEL and engine/observer.py::_MODEL.
STAGE_MODEL_LABELS: dict[str, str] = {
    "classifier": "claude-haiku-4-5-20251001",
    "observer": "claude-sonnet-4-5-20250929",
}


@dataclass(slots=True)
class StageTotals:
    """Running totals for a single pipeline stage (e.g. classifier / observer)."""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cli_subscription_calls: int = 0


@dataclass(slots=True)
class CostReport:
    """Aggregate cost/usage for a universe, ready for rendering."""

    slug: str
    tick_count: int = 0
    tick_id_min: str | None = None
    tick_id_max: str | None = None
    duration_ms_total: int = 0
    stage_totals: dict[str, StageTotals] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    batch_count: int = 0
    epoch_count: int = 0
    # Raw counters across all per-tick stage calls, convenient for JSON export.
    all_zero_stage_calls: int = 0

    @property
    def total_cost_usd(self) -> float:
        return sum(s.cost_usd for s in self.stage_totals.values())

    @property
    def total_input_tokens(self) -> int:
        return sum(s.input_tokens for s in self.stage_totals.values())

    @property
    def total_output_tokens(self) -> int:
        return sum(s.output_tokens for s in self.stage_totals.values())

    @property
    def total_calls(self) -> int:
        return sum(s.calls for s in self.stage_totals.values())

    @property
    def backend_label(self) -> str:
        """Heuristic backend label derived from token visibility.

        ``anthropic-sdk`` when every stage call recorded non-zero usage,
        ``claude-cli`` when every stage call was all-zeros, ``mixed``
        otherwise. ``no-data`` if no stage calls were observed at all.
        """
        total = self.total_calls
        if total == 0:
            return "no-data"
        if self.all_zero_stage_calls == total:
            return "claude-cli"
        if self.all_zero_stage_calls == 0:
            return "anthropic-sdk"
        return "mixed"


def _read_json_file(path: Path, warnings: list[str]) -> dict[str, Any] | None:
    """Return parsed JSON object, or None on malformed/non-object payloads."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"skipped {path.name}: {exc.__class__.__name__}: {exc}")
        return None
    if not isinstance(data, dict):
        warnings.append(f"skipped {path.name}: top-level JSON is not an object")
        return None
    return data


def _tick_id_sort_key(tick_id: str) -> tuple[int, str]:
    """Sort tick IDs numerically when possible, lexicographically otherwise."""
    try:
        return (int(tick_id), "")
    except (TypeError, ValueError):
        return (sys.maxsize, tick_id)


def _coerce_int(value: object) -> int:
    """Best-effort int coercion; returns 0 on any failure."""
    if isinstance(value, bool):  # bool is an int subclass — exclude
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _coerce_float(value: object) -> float:
    """Best-effort float coercion; returns 0.0 on any failure."""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _iter_tick_files(ticks_dir: Path, since: int | None) -> list[Path]:
    """Return tick_*.json files, sorted by numeric tick id, optionally trimmed.

    ``since=N`` keeps the last N files (highest tick IDs). Non-numeric tick
    IDs sort after numeric ones to preserve determinism without crashing.
    """
    if not ticks_dir.is_dir():
        return []
    files = sorted(
        ticks_dir.glob("tick_*.json"),
        key=lambda p: _tick_id_sort_key(p.stem.removeprefix("tick_")),
    )
    if since is not None and since > 0:
        files = files[-since:]
    return files


def _apply_tick(
    tick: dict[str, Any],
    report: CostReport,
) -> None:
    """Fold a single TickSummary dict into the running report."""
    tokens_by_stage = tick.get("llm_tokens_by_stage") or {}
    cost_by_stage = tick.get("llm_cost_usd_by_stage") or {}
    stages = set(tokens_by_stage) | set(cost_by_stage)

    for stage in stages:
        tok = tokens_by_stage.get(stage) or {}
        in_tok = _coerce_int(tok.get("in", 0))
        out_tok = _coerce_int(tok.get("out", 0))
        cost = _coerce_float(cost_by_stage.get(stage, 0.0))

        totals = report.stage_totals.setdefault(stage, StageTotals())
        totals.calls += 1
        totals.input_tokens += in_tok
        totals.output_tokens += out_tok
        totals.cost_usd += cost

        if in_tok == 0 and out_tok == 0 and cost == 0.0:
            totals.cli_subscription_calls += 1
            report.all_zero_stage_calls += 1

    report.duration_ms_total += _coerce_int(tick.get("duration_ms", 0))


def _apply_aggregate_optional(
    data: dict[str, Any],
    report: CostReport,
    source_label: str,
) -> None:
    """Fold optional aggregate fields from a batch/epoch file into the report.

    BatchSummary/EpochSummary schema v2 do not currently expose usage totals,
    but we scan for forward-compatible fields: ``llm_cost_usd_by_stage`` and
    ``llm_tokens_by_stage`` (per-stage), or flat ``total_cost_usd`` /
    ``total_input_tokens`` / ``total_output_tokens``. Flat fields are folded
    into a pseudo-stage named after ``source_label`` to keep per-stage
    rendering honest. A batch/epoch without any of these fields is a no-op.
    """
    per_stage_tokens = data.get("llm_tokens_by_stage") or {}
    per_stage_cost = data.get("llm_cost_usd_by_stage") or {}
    if per_stage_tokens or per_stage_cost:
        stages = set(per_stage_tokens) | set(per_stage_cost)
        for stage in stages:
            tok = per_stage_tokens.get(stage) or {}
            in_tok = _coerce_int(tok.get("in", 0))
            out_tok = _coerce_int(tok.get("out", 0))
            cost = _coerce_float(per_stage_cost.get(stage, 0.0))
            totals = report.stage_totals.setdefault(stage, StageTotals())
            totals.calls += 1
            totals.input_tokens += in_tok
            totals.output_tokens += out_tok
            totals.cost_usd += cost
            if in_tok == 0 and out_tok == 0 and cost == 0.0:
                totals.cli_subscription_calls += 1
                report.all_zero_stage_calls += 1
        return

    flat_cost = data.get("total_cost_usd")
    flat_in = data.get("total_input_tokens")
    flat_out = data.get("total_output_tokens")
    if flat_cost is None and flat_in is None and flat_out is None:
        return
    totals = report.stage_totals.setdefault(source_label, StageTotals())
    totals.calls += 1
    totals.input_tokens += _coerce_int(flat_in)
    totals.output_tokens += _coerce_int(flat_out)
    totals.cost_usd += _coerce_float(flat_cost)
    if totals.input_tokens == 0 and totals.output_tokens == 0 and totals.cost_usd == 0.0:
        totals.cli_subscription_calls += 1
        report.all_zero_stage_calls += 1


def aggregate(
    universe_dir: Path,
    *,
    slug: str,
    since: int | None = None,
) -> CostReport:
    """Walk tick_summaries/ and produce a CostReport.

    Args:
        universe_dir: Root of the universe directory.
        slug: Universe slug (used only for display).
        since: If provided and positive, only aggregate the last N per-tick
            files. Batches/epochs are always scanned in full (they pre-date
            the ``since`` window; trimming them would double-count).

    Returns:
        A fully-populated :class:`CostReport`. Missing/empty directories
        yield a report with ``tick_count == 0``.
    """
    report = CostReport(slug=slug)

    ts_dir = universe_dir / "tick_summaries"
    ticks_dir = ts_dir / "ticks"
    batches_dir = ts_dir / "batches"
    epochs_dir = ts_dir / "epochs"

    tick_files = _iter_tick_files(ticks_dir, since)
    tick_ids: list[str] = []
    for path in tick_files:
        data = _read_json_file(path, report.warnings)
        if data is None:
            continue
        tick_id = str(data.get("tick_id") or path.stem.removeprefix("tick_"))
        tick_ids.append(tick_id)
        _apply_tick(data, report)

    report.tick_count = len(tick_ids)
    if tick_ids:
        ordered = sorted(tick_ids, key=_tick_id_sort_key)
        report.tick_id_min = ordered[0]
        report.tick_id_max = ordered[-1]

    # Batches/epochs — best-effort: only fold in optional usage fields when
    # present. If the schema hasn't grown them yet, these loops only bump
    # the count so the dashboard shows how many compression units exist.
    if batches_dir.is_dir():
        for batch_path in sorted(batches_dir.glob("*.json")):
            data = _read_json_file(batch_path, report.warnings)
            if data is None:
                continue
            report.batch_count += 1
            _apply_aggregate_optional(data, report, source_label="batch")

    if epochs_dir.is_dir():
        for epoch_path in sorted(epochs_dir.glob("*.json")):
            data = _read_json_file(epoch_path, report.warnings)
            if data is None:
                continue
            report.epoch_count += 1
            _apply_aggregate_optional(data, report, source_label="epoch")

    return report


def _stage_display_label(stage: str) -> str:
    """Return the cosmetic ``<stage> (<model-id>)`` label."""
    model = STAGE_MODEL_LABELS.get(stage)
    if model is None:
        return stage
    return f"{stage} ({model})"


def render_table(report: CostReport) -> str:
    """Render the report as a human-readable table.

    Format is stable enough to smoke-test via substring assertions but is
    NOT a machine-parseable contract — JSON output is the stable shape.
    """
    out: list[str] = []
    out.append(f"=== Cost Dashboard: {report.slug} ===")
    if report.tick_count == 0:
        out.append("No tick summaries found — has the universe run any ticks?")
        return "\n".join(out) + "\n"

    tick_range = "n/a"
    if report.tick_id_min is not None and report.tick_id_max is not None:
        if report.tick_id_min == report.tick_id_max:
            tick_range = report.tick_id_min
        else:
            tick_range = f"{report.tick_id_min}..{report.tick_id_max}"
    out.append(f"Ticks analyzed:    {report.tick_count} (tick range: {tick_range})")

    if report.duration_ms_total > 0:
        seconds = report.duration_ms_total / 1000.0
        out.append(f"Duration:          {seconds:.1f} seconds ({report.tick_count} ticks)")
    else:
        out.append(f"Duration:          {report.tick_count} ticks (no timing data)")
    out.append("")

    header = f"{'Model':<42} {'Calls':>7} {'Input tok':>12} {'Output tok':>12} {'Cost USD':>12}"
    out.append(header)
    for stage in sorted(report.stage_totals):
        totals = report.stage_totals[stage]
        out.append(
            f"{_stage_display_label(stage):<42} "
            f"{totals.calls:>7} "
            f"{totals.input_tokens:>12,} "
            f"{totals.output_tokens:>12,} "
            f"${totals.cost_usd:>11.4f}"
        )
    out.append("-" * len(header))
    out.append(
        f"{'Total':<42} "
        f"{report.total_calls:>7} "
        f"{report.total_input_tokens:>12,} "
        f"{report.total_output_tokens:>12,} "
        f"${report.total_cost_usd:>11.4f}"
    )
    out.append("")
    out.append(f"Backend used:      {report.backend_label}")

    cli_calls = sum(s.cli_subscription_calls for s in report.stage_totals.values())
    if cli_calls > 0:
        out.append(f"CLI-subscription calls (zero marginal cost): {cli_calls}")

    if report.batch_count or report.epoch_count:
        out.append(f"Compression units: {report.batch_count} batches, {report.epoch_count} epochs")

    return "\n".join(out) + "\n"


def render_json(report: CostReport) -> str:
    """Render the report as a JSON blob suitable for scripting."""
    payload: dict[str, Any] = {
        "slug": report.slug,
        "tick_count": report.tick_count,
        "tick_id_min": report.tick_id_min,
        "tick_id_max": report.tick_id_max,
        "duration_ms_total": report.duration_ms_total,
        "batch_count": report.batch_count,
        "epoch_count": report.epoch_count,
        "backend": report.backend_label,
        "total_calls": report.total_calls,
        "total_input_tokens": report.total_input_tokens,
        "total_output_tokens": report.total_output_tokens,
        "total_cost_usd": report.total_cost_usd,
        "cli_subscription_calls": sum(
            s.cli_subscription_calls for s in report.stage_totals.values()
        ),
        "stages": {
            stage: {
                "model_label": STAGE_MODEL_LABELS.get(stage),
                "calls": totals.calls,
                "input_tokens": totals.input_tokens,
                "output_tokens": totals.output_tokens,
                "cost_usd": totals.cost_usd,
                "cli_subscription_calls": totals.cli_subscription_calls,
            }
            for stage, totals in sorted(report.stage_totals.items())
        },
        "warnings": report.warnings,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
