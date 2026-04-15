# Phase 13: Quality KPIs Substrate — Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous smart discuss)

<domain>
## Phase Boundary

Add a `token-world quality <slug>` CLI command that produces a single scorecard with all 8 rubric dimensions from `docs/quality/sim-quality-rubric.md`: groundedness, character stability, action coherence, refusal clustering, vocabulary growth, novel subtype rate, graph fan-out, conservation drift.

Dashboard gains a "Quality" panel that imports from `token_world.quality` directly (no subprocess) and renders the scorecard live.

A CI check (`scripts/check_quality_thresholds.py`) fails with a named-dimension error when any dimension drops below its threshold over the last 50 ticks.

REQ-V12-QUALITY-02. Success criteria from ROADMAP:
- SC-1: `token-world quality <slug>` outputs all 8 dimensions
- SC-2: Dashboard "Quality" panel consumes it via Python import, never recomputes
- SC-3: CI hook fails with named-dimension error on threshold breach
- SC-4: Works on real willowbrook dataset

</domain>

<decisions>
## Implementation Decisions

### Module structure
- New subpackage `src/token_world/quality/` with `__init__.py`, `scorer.py` (8 dimension scorers), `thresholds.py` (defaults), `report.py` (QualityReport dataclass)
- CLI entry: `@cli.command("quality")` in `src/token_world/cli.py`, following `inspect` module pattern
- Dashboard: New "Quality" panel in NiceGUI dashboard reading from `token_world.quality` Python import (same pattern as stats panel)

### Data sources
- tick_summaries/ — groundedness, refusal clustering, character stability, action coherence
- graph_events — graph fan-out (node/edge counts over time)
- existing stats aggregators — vocabulary growth, novel subtype rate
- conservation counters — conservation drift

### CI gate
- `scripts/check_quality_thresholds.py <slug>` — non-zero exit on threshold breach; wired into pytest via `tests/test_meta/test_quality_thresholds.py`
- Thresholds loaded from `docs/quality/sim-quality-rubric.md` or a companion `quality_thresholds.json`

### Scope
- All 8 rubric dimensions scored for v1.2
- `--last N` flag (default 50 ticks) to match rubric spec
- `--format table|json` consistent with other CLI commands

</decisions>

<code_context>
## Existing Code Insights

- `src/token_world/cli.py` — main CLI entry; add `quality` command following `stats`/`cost` pattern
- `src/token_world/inspect/stats.py` — existing stats aggregator; reuse novel-verb/subtype counts
- `src/token_world/playtest/scorer.py` — existing groundedness scorer; extend or reuse
- `docs/quality/sim-quality-rubric.md` — canonical rubric; thresholds live here
- Dashboard panel pattern: `from token_world.inspect.X import aggregate` with 2s poll timer

</code_context>

<specifics>
## Specific Requirements

- Per ROADMAP SC-2: Dashboard panel NEVER recomputes scores itself — it calls into `token_world.quality`
- Per §G tooling-surfaces rule: quality scoring logic lives in `src/token_world/quality/`, not embedded in CLI or dashboard
- CI script must be pytest-wired (like `check_requirements_traceability.py`) so `uv run pytest` catches regressions

</specifics>

<deferred>
## Deferred Ideas

- Per-dimension trend charts in dashboard (v2.0)
- Configurable threshold overrides per universe (v2.0)

</deferred>
