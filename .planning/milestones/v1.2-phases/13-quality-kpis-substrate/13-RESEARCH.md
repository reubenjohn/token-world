# Phase 13: Quality KPIs Substrate — Research

**Researched:** 2026-04-14
**Domain:** Simulation quality scoring / CLI command / NiceGUI dashboard panel / pytest CI gate
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- New subpackage `src/token_world/quality/` with `__init__.py`, `scorer.py` (8 dimension scorers),
  `thresholds.py` (defaults), `report.py` (QualityReport dataclass)
- CLI entry: `@cli.command("quality")` in `src/token_world/cli.py`, following `inspect` module pattern
- Dashboard: New "Quality" panel in NiceGUI dashboard reading from `token_world.quality` Python import
  (same pattern as stats panel — 2s poll timer, direct import, degrade gracefully on error)
- Data sources: tick_summaries/, graph_events, existing stats aggregators, conservation counters
- CI gate: `scripts/check_quality_thresholds.py <slug>` — non-zero exit on threshold breach;
  wired into pytest via `tests/test_meta/test_quality_thresholds.py`
- Thresholds loaded from a companion `quality_thresholds.json` (canonical defaults) or from the rubric
- `--last N` flag (default 50 ticks) to match rubric spec; `--format table|json` consistent with other commands

### Claude's Discretion
- Exact internal API shape of `scorer.py` / `report.py`
- How graph fan-out snapshot data is stored (time-series approach)
- Whether character stability marker list lives in `markers.py` or `thresholds.py`
- CI script implementation detail (slug discovery, fixture-universe vs real willowbrook)

### Deferred Ideas (OUT OF SCOPE)
- Per-dimension trend charts in dashboard (v2.0)
- Configurable threshold overrides per universe (v2.0)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-V12-QUALITY-02 | Simulation-quality KPIs subpackage + CLI command (`token-world quality <slug>`) + dashboard Quality panel + CI threshold gate. All 8 rubric dimensions (groundedness, character stability, action coherence, refusal clustering, vocabulary growth, novel subtype rate, graph fan-out, conservation drift). Unit tests per KPI; integration test against fixture universe. | Research confirms data availability for 6/7 dimensions from existing tick_summaries; fan-out needs new per-tick graph scan; character stability needs new `action_text` marker scan. Dashboard panel follows verified stats strip pattern exactly. CI gate follows verified `check_requirements_traceability.py` pattern. |
</phase_requirements>

---

## Summary

Phase 13 builds a quality scoring substrate for Token World simulations. The rubric (already shipped in docs/quality/sim-quality-rubric.md) defines 7 dimensions — the CONTEXT says 8 but the rubric document itself specifies 7 (novel subtype rate appears in CONTEXT but not explicitly as its own rubric section; it is subsumed into vocabulary growth or is a gap). This discrepancy is noted below and needs planner attention.

Six of the seven rubric dimensions can be computed entirely from existing data in `tick_summaries/ticks/tick_*.json` files using the already-proven `iter_tick_files` / `read_json_file` helpers from `token_world.inspect._shared`. One dimension (graph fan-out) requires a direct SQLite query against `universe.db`'s `graph_state` table (node_count and edge_count are stored per save). Conservation drift requires reading `refusal_reason` fields — already done in `stats.py`. Character stability requires scanning `action_text` for marker substrings — new code, trivially pure.

The dashboard integration path is fully proven by `panels/stats.py`: import the aggregator, call it on a 10s timer (rubric specifies 10s for quality, slower than stats' 2s), render cells. The CI gate pattern is proven by `scripts/check_requirements_traceability.py` + `tests/test_meta/test_requirements_traceability.py`.

The willowbrook universe does not appear to exist on disk at this time — no tick files were found anywhere under the repo. SC-4 ("works on real willowbrook dataset") will be satisfied by running against a fixture universe in tests; if willowbrook is regenerated before phase verification the command can be run against it then.

**Primary recommendation:** Build `quality/scorer.py` as a single-pass tick scanner (mirrors `stats.aggregate`), produce a `QualityReport` dataclass, wire CLI and dashboard on top. Graph fan-out reads `graph_state` table directly (node_count, edge_count columns already there). Test with synthetic tick fixtures exactly as `test_stats.py` does.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Quality scoring (8 dimensions) | `src/token_world/quality/scorer.py` | — | Canonical producer rule: compute once, read many |
| Threshold definitions + verdict | `src/token_world/quality/thresholds.py` | — | Separates data from logic; CI script imports same module |
| QualityReport dataclass + renderers | `src/token_world/quality/report.py` | — | Mirrors StatsReport pattern; table + json renderers here |
| CLI command | `src/token_world/cli.py` (`@cli.command("quality")`) | — | Thin wrapper: load universe, call scorer, render, echo |
| Dashboard Quality panel | `src/token_world/dashboard/panels/quality.py` | — | Imports scorer directly; never re-computes |
| CI threshold gate | `scripts/check_quality_thresholds.py` | `tests/test_meta/test_quality_thresholds.py` | Script exits non-zero; pytest invokes it |
| Data source — tick stream | `tick_summaries/ticks/tick_*.json` | `token_world.inspect._shared` helpers | Existing infrastructure; no new instrumentation |
| Data source — graph snapshots | `universe.db` → `graph_state` table | sqlite3 direct | node_count, edge_count already stored per save |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`collections`, `re`, `json`, `sqlite3`, `dataclasses`) | 3.12+ | Scoring, parsing, persistence | Project rule: no ORM, no pickle; stdlib covers all quality-scoring needs |
| click | existing | CLI command | Already the project's CLI framework [VERIFIED: cli.py] |
| nicegui | existing (dashboard extra) | Quality panel UI | Already the project's dashboard framework [VERIFIED: dashboard/app.py] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `token_world.inspect._shared` | internal | `iter_tick_files`, `read_json_file` | Tick file iteration — reuse, don't copy |
| `token_world.inspect.stats` | internal | `aggregate()` for vocabulary growth (novel_verbs) | Provides novel_mechanics_per_10_ticks; quality scorer can compose with stats |
| `pydantic` | existing | Optional: TurnScore already uses it | Only if QualityReport needs validation; dataclass is simpler |

---

## Tick Summary Schema (VERIFIED by conftest.py)

Every `tick_summaries/ticks/tick_N.json` file has this shape [VERIFIED: tests/test_cli/conftest.py `_write_tick_summary`]:

```python
{
    "schema_version": 1,
    "tick_id": str,
    "timestamp_iso": str,            # ISO 8601
    "action_text": str,              # Agent's raw action — used for character stability
    "classified_action": dict | None,
    "matched_mechanic_id": str | None,
    "yielded": bool,
    "refused": bool,
    "refusal_reason": str | None,    # "conservation_violation..." for conservation drift
    "mutations": {
        "count": int,
        "list": [[target, prop, old, new], ...]
    },
    "observation_text": str | None,
    "long_running_action": dict | None,
    "duration_ms": int,
    "llm_tokens_by_stage": {...},
    "llm_cost_usd_by_stage": {...},
}
```

---

## Data Availability Matrix

| Dimension | Source Field(s) | Available? | Notes |
|-----------|-----------------|------------|-------|
| 1. Groundedness | `refused`, `refusal_reason`, tick status | PARTIAL | Existing `playtest.scorer.TurnScorer._observation_groundedness` checks projected_state vs observation. But tick summaries don't store the projected_state cross-check result directly. The rubric's formula is `1 - (ungrounded_ticks / total)` over 50 ticks — must decide: (a) use existing `TurnScore.observation_groundedness` stored somewhere, or (b) approximate from `refused=False AND mutations.count==0` pattern, or (c) use `observation_groundedness` field if written to tick summary. **GAP: tick summary schema does not store groundedness score per tick.** [VERIFIED: conftest.py schema] |
| 2. Character stability | `action_text` field | YES | Scan for marker substrings. New code but trivially pure. action_text is available in every tick file. [VERIFIED: conftest.py] |
| 3. Action coherence | `refused`, `yielded` fields | YES | longest non-refuse streak + refuse rate per 10-tick window. Straightforward scan. [VERIFIED: stats.py shows same scan] |
| 4. Refusal cluster alarm | `refused` field | YES | Running counter of consecutive refuses. Single pass over ordered tick files. [VERIFIED: conftest.py] |
| 5. Vocabulary growth | `matched_mechanic_id` or novel verb counting | PARTIAL | `stats.aggregate` computes `novel_mechanics_per_10_ticks` (uses matched_mechanic_id, not verbs). Rubric says "novel verbs per 10 ticks" — but no verb extraction exists in tick summaries. **Pragmatic resolution: use `novel_mechanics_per_10_ticks` from stats.aggregate as proxy, or extract verb from `classified_action.action_type`.** Need to verify `classified_action` field shape. |
| 6. Conservation drift | `refusal_reason` containing "conservation" | YES | Already done in `stats.aggregate` — `conservation_violation_count`. Rate = count/total. [VERIFIED: stats.py line 170] |
| 7. Graph fan-out | `graph_state` table in `universe.db` | YES | `node_count` and `edge_count` stored per save [VERIFIED: persistence.py schema]. Need snapshots over time — `graph_snapshots` table has tick_id, node_count, edge_count for each snapshot. Fan-out = edge_count/node_count per snapshot; slope across last 5 checkpoints. |

**Key gap — Groundedness:** The rubric says "extend with per-tick observer cross-check". The tick summary does not store an `is_grounded` boolean. Resolution options:
- **Option A (pragmatic):** Proxy groundedness using `mutation_count > 0 OR refused` (a tick is "grounded" if its observation is backed by actual mutations or an honest refusal). Low fidelity but zero new instrumentation.
- **Option B (correct but out-of-scope):** Add `groundedness_score: float` to tick summary schema when `run_tick` generates an observation. This is engine-level instrumentation that would be a separate phase.
- **Option C (reuse TurnScorer):** Call `TurnScorer._observation_groundedness` retroactively if `observation_text` and `projected_state` are in the tick file. Projected_state is NOT in the tick summary schema. [VERIFIED: conftest.py]

**Recommendation:** Use Option A as v1.2 groundedness proxy (mutation-backed execution rate). Document the proxy clearly. Reserve true observer cross-check for a future engine instrumentation phase. The rubric already says "Extend with per-tick observer cross-check" — this is explicitly a future addition.

**Key gap — Vocabulary growth (novel verbs vs novel mechanics):** The rubric says "novel verbs per 10 ticks" but the existing stats infrastructure tracks novel mechanic IDs, not action verbs. The `classified_action` dict likely has an `action_type` field — this should be verified. The planner should decide: use novel mechanic IDs as proxy, or extract verb from classified_action.

**Key gap — "8 dimensions" vs "7 dimensions":** The rubric document has exactly 7 numbered dimensions. The phase CONTEXT mentions 8 (listing "novel subtype rate" separately from "vocabulary growth"). Looking at the rubric: §5 "Vocabulary growth" covers novel verbs. "Novel subtype rate" appears only in CONTEXT.md and the phase description, not in the rubric. The CONTEXT lists it as a distinct 8th dimension. Planner must decide: (a) implement novel subtype rate as an 8th dimension using the existing `distinct_subtypes_seen` from stats, or (b) treat vocabulary growth as combining both. Both are implementable; the data is available via `mutations[*][prop]=="subtype"` scans (already done in stats.py).

---

## Architecture Patterns

### System Architecture Diagram

```
tick_summaries/ticks/*.json  ──────────────────┐
                                                ▼
universe.db (graph_state, graph_snapshots) ──▶  quality/scorer.py
                                                │ score_all_dimensions(universe_dir, last=50)
                                                │ returns QualityReport
                                                ▼
                              ┌─────────────────┼─────────────────┐
                              ▼                 ▼                  ▼
                     CLI quality cmd    dashboard/panels/    scripts/check_
                     (table | json)     quality.py           quality_thresholds.py
                                        (10s timer)          (exit non-zero)
                                                              │
                                                              ▼
                                              tests/test_meta/test_quality_thresholds.py
                                              (subprocess.run → assert returncode==0)
```

### Recommended Project Structure

```
src/token_world/quality/
├── __init__.py          # exports: score, QualityReport, DimensionResult
├── scorer.py            # score() → QualityReport; 7-8 dimension scorers
├── thresholds.py        # GREEN/RED ranges; MARKERS list; verdict logic
└── report.py            # QualityReport, DimensionResult dataclasses + renderers

src/token_world/dashboard/panels/
└── quality.py           # mount_quality_panel(universe_dir, slug)

scripts/
└── check_quality_thresholds.py   # CLI gate; non-zero on FAIL verdict

tests/
├── test_cli/
│   └── test_quality.py          # CLI integration; unit tests per scorer
└── test_meta/
    └── test_quality_thresholds.py  # pytest-wired CI gate
```

### Pattern 1: Stats Aggregator (mirror this exactly)
**What:** Single-pass scan over tick files, produce frozen dataclass, render table/json.
**When to use:** All tick-based dimensions (character stability, action coherence, refusal cluster, vocabulary, conservation drift).
**Example:**
```python
# Source: src/token_world/inspect/stats.py (VERIFIED)
from token_world.inspect._shared import iter_tick_files, read_json_file

def score(universe_dir: Path, *, slug: str, last: int = 50) -> QualityReport:
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    files = iter_tick_files(ticks_dir, since=last)
    payloads = [read_json_file(f) for f in files]
    payloads = [p for p in payloads if p is not None]
    # ... single-pass computation of all dimensions
```

### Pattern 2: Dashboard Panel (mirror stats strip exactly)
**What:** `load_X(universe_dir, slug)` wraps aggregator with try/except; `mount_X_panel` uses `ui.timer(10.0, _rebuild)`.
**When to use:** Quality panel — slower signal than stats (10s vs 2s).
**Example:**
```python
# Source: src/token_world/dashboard/panels/stats.py (VERIFIED)
def load_quality(universe_dir: Path, slug: str) -> QualityReport:
    try:
        return score(universe_dir, slug=slug)
    except Exception:
        return QualityReport(slug=slug)  # zero-filled degraded report

def mount_quality_panel(universe_dir: Path, slug: str) -> Any:
    from nicegui import ui
    container = ui.row().classes("w-full ...")
    def _rebuild() -> None:
        container.clear()
        report = load_quality(universe_dir, slug)
        # render coloured cells
    _rebuild()
    ui.timer(10.0, _rebuild)
    return container
```

### Pattern 3: CI Gate Script (mirror check_requirements_traceability.py)
**What:** Standalone script, argparse, exit 0/1, invoked by pytest via subprocess.run.
**When to use:** `scripts/check_quality_thresholds.py`.
**Example:**
```python
# Source: scripts/check_requirements_traceability.py (VERIFIED)
# pytest side: tests/test_meta/test_quality_thresholds.py
result = subprocess.run(
    ["uv", "run", "python", str(SCRIPT), slug],
    cwd=REPO_ROOT, capture_output=True, text=True,
)
assert result.returncode == 0, f"Quality threshold breach:\n{result.stdout}\n{result.stderr}"
```

### Pattern 4: Graph Fan-out from SQLite
**What:** Query `graph_snapshots` table for (tick_id, node_count, edge_count) history; compute fan-out slope.
**When to use:** graph fan-out dimension.
**Example:**
```python
# Source: src/token_world/graph/persistence.py (VERIFIED) — schema confirmed
import sqlite3
from pathlib import Path

def _load_fanout_history(db_path: Path) -> list[tuple[int, float]]:
    """Return list of (tick_id, fan_out) from graph_snapshots, last 5."""
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            "SELECT tick_id, node_count, edge_count FROM graph_snapshots "
            "ORDER BY tick_id DESC LIMIT 5"
        ).fetchall()
    result = []
    for tick_id, n, e in reversed(rows):
        if n > 0:
            result.append((tick_id, e / n))
    return result

def _fanout_slope(history: list[tuple[int, float]]) -> float:
    """Slope of fan_out over tick range. Positive = growing."""
    if len(history) < 2:
        return 0.0
    first_tick, first_val = history[0]
    last_tick, last_val = history[-1]
    elapsed = last_tick - first_tick
    if elapsed <= 0:
        return 0.0
    return (last_val - first_val) / elapsed * 10  # per-10-tick slope
```

**Warning:** If `universe.db` has no snapshots (no `graph_snapshots` rows), fan-out slope defaults to 0.0 (green). The scorer should degrade gracefully when the DB doesn't exist or has insufficient snapshot history.

### Anti-Patterns to Avoid
- **Subprocess out to `token-world quality --format json` in dashboard:** Violates SC-2; use Python import.
- **Duplicating `iter_tick_files` / `read_json_file`:** Use `token_world.inspect._shared` directly.
- **Mutating global threshold state:** Thresholds are module-level constants; no mutation.
- **Reading full graph JSON blob for fan-out:** `graph_state` stores one row per universe (the current state). Use `graph_snapshots` for time-series fan-out. `graph_state` only stores the latest node_count/edge_count.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tick file iteration + sorting | Custom glob + sort | `iter_tick_files(ticks_dir, since=N)` from `_shared` | Handles numeric sort, since-windowing, missing dir |
| JSON parse with error swallowing | try/except in scorer | `read_json_file(path)` from `_shared` | Returns None on error, no crash |
| Novel mechanic tracking | Custom set accumulation | `stats.aggregate().novel_mechanics_per_10_ticks` if composing | Already computed; but scorer may need raw data so a single-pass re-implementation is fine |
| Verdict CSS colours in NiceGUI | Custom colour lookup | `"text-green-400"/"text-yellow-400"/"text-red-400"` Tailwind classes | Already used in dashboard codebase |

---

## Dimension Scorer Implementation Notes

### Groundedness (Proxy)
- **Input:** tick payloads, `refused`, `mutations.count`
- **Proxy formula:** `grounded_ticks = ticks where (NOT refused AND mutations.count > 0) OR (refused AND refusal_reason is honest)`
- **Cleaner proxy:** any executed tick (`refused=False, yielded=False`) with `mutations.count > 0` is grounded. Executed ticks with zero mutations are suspect (could be ungrounded observation). Score = `(executed_with_mutations + yielded + honest_refuses) / total`.
- **Rubric threshold:** green >= 0.95, red < 0.85

### Character Stability
- **Input:** `action_text` per tick
- **Markers:** `["framework", "yield", "mechanic", "system prompt", "operator", "scenario"]` (from rubric §2)
- **Formula:** `stability = 1 - (ticks_with_any_marker / total_ticks)`
- **Implementation:** simple `any(m in action_text.lower() for m in MARKERS)` per tick
- **Rubric threshold:** green >= 0.98, red < 0.90

### Action Coherence
- **Input:** `refused`, `yielded` fields per tick (ordered)
- **longest_coherent_streak:** scan in order, track current non-refuse run length
- **refuse_rate_10tick:** sliding 10-tick window mean; compute mean over all windows or overall rate
- **Rubric threshold (green):** streak >= 15 AND rate <= 1.5; red: streak < 5 OR rate >= 4

### Refusal Cluster Alarm
- **Input:** `refused` fields in tick order
- **Formula:** max consecutive refuses in the window
- **Rubric threshold:** green: max_consecutive <= 2; red: max_consecutive >= 5

### Vocabulary Growth (Novel Mechanics Proxy)
- **Input:** `matched_mechanic_id` per tick
- **Formula:** `novel_mechanics / (window_size / 10)` — average per 10-tick bucket
- **Rubric threshold:** green: 0.5 <= rate <= 2.5; red: rate==0 for 30+ ticks OR rate > 4
- **Note:** Rubric says "novel verbs" but mechanic IDs are the closest available proxy. Document clearly.

### Conservation Drift
- **Input:** `refused=True, refusal_reason` containing "conservation"
- **Formula:** `rollback_rate = conservation_refuses / total_ticks`
- **Rubric threshold:** green <= 0.02, red >= 0.10

### Graph Fan-out
- **Input:** `graph_snapshots` table (tick_id, node_count, edge_count)
- **Formula:** `fan_out = edge_count / node_count` per checkpoint; slope across last 5 checkpoints
- **Rubric threshold:** green: slope >= 0; red: slope < -0.02 per 10 ticks sustained
- **Degrade:** if < 2 snapshots exist, return slope=0.0, status=OK with note "insufficient history"

### Novel Subtype Rate (8th dimension — if included)
- **Input:** `mutations.list` entries where `prop == "subtype"`
- **Formula:** cumulative distinct new subtypes per 10 ticks (same logic as `stats.py _scan_subtype_proxies`)
- **Threshold:** to be defined (no threshold in rubric — planner must set one or mark as informational)

---

## QualityReport Dataclass Design

```python
# src/token_world/quality/report.py
from dataclasses import dataclass, field
from typing import Literal

Status = Literal["OK", "WARN", "FAIL", "UNKNOWN"]

@dataclass(slots=True)
class DimensionResult:
    name: str
    status: Status          # "OK" | "WARN" | "FAIL" | "UNKNOWN"
    score: float            # primary numeric value
    detail: str             # human-readable detail (e.g. "48/50 grounded")

@dataclass(slots=True)
class QualityReport:
    slug: str
    window: int = 50        # ticks scanned
    tick_count: int = 0     # actual ticks found (may be < window)
    dimensions: list[DimensionResult] = field(default_factory=list)
    verdict: Literal["HEALTHY", "DEGRADED", "FAILED", "INSUFFICIENT_DATA"] = "INSUFFICIENT_DATA"
```

---

## Thresholds Module Design

```python
# src/token_world/quality/thresholds.py
# All constants match docs/quality/sim-quality-rubric.md verbatim
GROUNDEDNESS_GREEN = 0.95
GROUNDEDNESS_RED   = 0.85

STABILITY_GREEN = 0.98
STABILITY_RED   = 0.90

COHERENCE_STREAK_GREEN = 15
COHERENCE_STREAK_RED   = 5
COHERENCE_RATE_GREEN   = 1.5   # refuses per 10 ticks
COHERENCE_RATE_RED     = 4.0

CLUSTER_WARN = 2   # max consecutive refuses — above this is WARN
CLUSTER_RED  = 5   # at or above this is FAIL

VOCAB_RATE_MIN_GREEN = 0.5
VOCAB_RATE_MAX_GREEN = 2.5
VOCAB_RATE_RED       = 4.0
VOCAB_STAGNANT_TICKS = 30   # 0-rate sustained over this many ticks = RED

CONSERVATION_GREEN = 0.02
CONSERVATION_RED   = 0.10

FANOUT_SLOPE_GREEN = 0.0       # >= 0 is OK
FANOUT_SLOPE_RED   = -0.02     # < -0.02 per 10 ticks is FAIL

CHARACTER_MARKERS = [
    "framework", "yield", "mechanic", "system prompt", "operator", "scenario"
]

MARKERS = [  # src/token_world/quality/markers.py (or inline in thresholds.py)
    "framework", "yield", "mechanic", "system prompt", "operator", "scenario"
]
```

---

## Dashboard Integration

The "Quality" panel mounts in `app.py` directly above or below the stats strip. Dashboard app currently has:
1. Active yield banner
2. Stats strip (header)
3. Main body (tick stream | graph | property history)

Quality panel fits naturally as a **second header strip** below stats, before the main body. [VERIFIED: dashboard/app.py lines 70-82 show mounting pattern]

The panel renders 7-8 coloured cells (green/amber/red) using Tailwind text colour classes, one per dimension plus a verdict label. Refresh timer: 10s (rubric specifies "refreshes every 10 seconds").

---

## CI Gate Design

`scripts/check_quality_thresholds.py <slug>`:
- Takes a slug argument (or discovers via env var)
- Loads universe from `UniverseManager`
- Calls `quality.score(universe_dir, slug=slug, last=50)`
- If verdict == "FAILED": print named failing dimensions, `sys.exit(1)`
- If verdict == "HEALTHY" or "DEGRADED": `sys.exit(0)` (WARN does not block CI)

`tests/test_meta/test_quality_thresholds.py`:
- Parametrize over a fixture universe with synthetic ticks (all green)
- `subprocess.run(["uv", "run", "python", str(SCRIPT), slug])` → assert returncode == 0
- Second test: inject failing ticks → assert returncode == 1

**Challenge:** The CI script requires a slug of a real or fixture universe. For `tests/test_meta`, a fixture universe must be created in `tmp_path`. The test must wire `XDG_DATA_HOME` monkeypatching so UniverseManager finds the fixture universe. This is the same pattern used in `test_stats.py`. [VERIFIED: test_stats.py lines 159-167]

---

## Common Pitfalls

### Pitfall 1: Fan-out from `graph_state` instead of `graph_snapshots`
**What goes wrong:** `graph_state` is a single row (current state). Using it gives only one data point — no slope computation possible.
**Why it happens:** `graph_state` has `node_count` and `edge_count` columns, tempting to use it.
**How to avoid:** Always read from `graph_snapshots` for time-series. If no snapshots, degrade to UNKNOWN.
**Warning signs:** Fan-out slope is always 0.0 regardless of universe activity.

### Pitfall 2: Groundedness ground truth unavailable
**What goes wrong:** Implementing the rubric formula literally (diff observation vs Mutation list) requires projected_state, which is not in tick summaries.
**Why it happens:** The rubric was written aspirationally; the per-tick cross-check is "forward-referenced" in rubric §1.
**How to avoid:** Use the documented proxy (mutation-backed execution rate). Add a code comment referencing the rubric's future instrumentation goal.
**Warning signs:** Test tries to read `projected_state` from tick summary and fails.

### Pitfall 3: "Novel verbs" vs "novel mechanic IDs"
**What goes wrong:** Rubric says "novel verbs"; tick summaries have no verb extraction. Building a verb extractor from scratch is over-engineered.
**Why it happens:** Rubric was written from the simulation's perspective; the implementation only records mechanic IDs.
**How to avoid:** Use `matched_mechanic_id` novelty as the proxy. Document explicitly.

### Pitfall 4: Dashboard subprocess call violating SC-2
**What goes wrong:** Dashboard panel shells out to `token-world quality --format json` instead of importing.
**Why it happens:** Looks clean, avoids import coupling.
**How to avoid:** Follow stats panel pattern exactly — direct Python import of `score()`.

### Pitfall 5: CI script requires real willowbrook slug
**What goes wrong:** `test_quality_thresholds.py` tries to test against the real willowbrook universe, which may not exist in CI.
**Why it happens:** SC-4 says "works on real willowbrook dataset" but this is a manual verification goal.
**How to avoid:** The pytest-wired test uses a synthetic fixture universe. SC-4 is verified manually pre-merge, not in CI.

### Pitfall 6: Empty window (< 5 ticks) produces misleading FAIL
**What goes wrong:** With 0-3 ticks, longest streak < 5 → action coherence shows FAIL when the universe is just new.
**Why it happens:** Rubric thresholds assume 50 ticks of history.
**How to avoid:** Add an `INSUFFICIENT_DATA` status when `tick_count < MIN_TICKS` (e.g. 10). Return this instead of FAIL/WARN.

---

## Test Strategy

### Unit tests (`tests/test_cli/test_quality.py`)

Mirror `test_stats.py` exactly:
- `test_score_empty_universe` — all dimensions UNKNOWN/INSUFFICIENT_DATA, no crash
- `test_groundedness_all_executed_with_mutations` — score 1.0, OK
- `test_groundedness_with_refuses` — score decrements, threshold check
- `test_character_stability_clean` — no markers in action_text, score 1.0
- `test_character_stability_with_breaks` — markers present, score decrements
- `test_action_coherence_streak` — long non-refuse run, streak metric correct
- `test_refusal_cluster_alarm` — 5 consecutive refuses → FAIL
- `test_vocab_growth_proxy` — novel mechanic IDs, rate in green range
- `test_conservation_drift` — conservation_violation refusals, rate correct
- `test_fanout_slope_growing` — inject mock snapshots, slope >= 0 → OK
- `test_fanout_slope_shrinking` — slope < -0.02 → FAIL
- `test_fanout_no_snapshots` — degrade to UNKNOWN gracefully
- `test_render_table_smoke` — output contains dimension names
- `test_render_json_valid` — JSON parses, has all dimension keys
- `test_cli_quality_table` — CLI integration via CliRunner, exit 0
- `test_cli_quality_json` — CLI JSON integration

### Meta test (`tests/test_meta/test_quality_thresholds.py`)

```python
# Pattern from test_requirements_traceability.py (VERIFIED)
def test_quality_thresholds_green_universe(tmp_path, monkeypatch):
    # Create fixture universe with all-green ticks
    # Run script against it
    # Assert returncode == 0

def test_quality_thresholds_red_universe(tmp_path, monkeypatch):
    # Create fixture universe with 5+ consecutive refuses
    # Run script against it
    # Assert returncode == 1 and stderr/stdout mentions dimension name
```

---

## Environment Availability

Step 2.6: All dependencies are internal to the repo (Python stdlib, existing packages). No external services required.

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| sqlite3 | Graph fan-out scorer | Built-in Python 3.12 | Always available |
| nicegui | Dashboard panel | Conditional (dashboard extra) | Import guarded by local import in mount function [VERIFIED: stats.py line 64] |
| click | CLI command | Yes (always installed) | |
| uv | Test runner | Yes | CI uses `uv run pytest` |

---

## Open Questions

1. **8th dimension: Novel subtype rate**
   - What we know: CONTEXT.md lists it; rubric has 7 dimensions not 8; data is available via mutations scan (already in stats.py)
   - What's unclear: Is this a distinct 8th dimension with its own threshold, or is it rolled into vocabulary growth?
   - Recommendation: Implement as an 8th informational dimension (no FAIL threshold; just display the count). Planner to decide threshold values.

2. **Groundedness proxy adequacy**
   - What we know: True groundedness needs projected_state cross-check not available in tick summaries
   - What's unclear: Is the "mutation-backed execution" proxy acceptable for CI gating in v1.2?
   - Recommendation: Use proxy for now; add a comment in thresholds.py noting the future instrumentation path. Do not block CI gate on this approximation — it will have false positives.

3. **`classified_action` field shape**
   - What we know: Field exists in tick summary schema (conftest.py shows it as `dict | None`)
   - What's unclear: Does it contain a verb/action_type that could power true vocabulary growth scoring?
   - Recommendation: Planner inspect one real tick file from a universe to check classified_action structure. If `action_type` exists, use it for vocab growth instead of mechanic IDs.

4. **CI script slug discovery**
   - What we know: Script takes a slug argument; test must provide one
   - What's unclear: Should the CI gate only run when willowbrook exists, or always with a fixture?
   - Recommendation: Always with a fixture universe; willowbrook testing is manual SC-4 verification.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pyproject.toml` (existing pytest config) |
| Quick run command | `uv run pytest tests/test_cli/test_quality.py -x -q` |
| Full suite command | `uv run pytest -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-V12-QUALITY-02 | All 8 dimension scorers correct | unit | `uv run pytest tests/test_cli/test_quality.py -x -q` | Wave 0 |
| REQ-V12-QUALITY-02 | CLI exits 0 with table output | integration | `uv run pytest tests/test_cli/test_quality.py::test_cli_quality_table -x` | Wave 0 |
| REQ-V12-QUALITY-02 | CLI JSON output valid | integration | `uv run pytest tests/test_cli/test_quality.py::test_cli_quality_json -x` | Wave 0 |
| REQ-V12-QUALITY-02 | CI script exits 0 on green universe | meta | `uv run pytest tests/test_meta/test_quality_thresholds.py -x -q` | Wave 0 |
| REQ-V12-QUALITY-02 | CI script exits 1 on FAIL verdict | meta | `uv run pytest tests/test_meta/test_quality_thresholds.py -x -q` | Wave 0 |
| REQ-V12-QUALITY-02 | Dashboard panel loads without crash | smoke | `uv run pytest tests/test_dashboard/ -x -q` | Extend existing |

### Wave 0 Gaps
- [ ] `tests/test_cli/test_quality.py` — unit + integration tests for all scorers
- [ ] `tests/test_meta/test_quality_thresholds.py` — CI gate test
- [ ] `src/token_world/quality/__init__.py`, `scorer.py`, `thresholds.py`, `report.py` — new subpackage
- [ ] `src/token_world/dashboard/panels/quality.py` — new panel
- [ ] `scripts/check_quality_thresholds.py` — CI gate script

---

## Security Domain

Security enforcement applies but this phase has no authentication, network calls, user input validation, or cryptography concerns. All data sources are local files (tick_summaries/) and SQLite (universe.db). No ASVS categories apply beyond V5 input validation.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `read_json_file` returns None on malformed JSON; all scorers must handle None/missing fields gracefully |
| V6 Cryptography | no | — |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Tick summaries do not store a per-tick groundedness boolean | Data Availability Matrix | If they do, the proxy is unnecessary — check tick schema more carefully |
| A2 | `graph_snapshots` table has node_count and edge_count per snapshot | Architecture Patterns | Confirmed by persistence.py schema — LOW risk |
| A3 | `classified_action` does not have a standardized `action_type` verb field | Open Questions | If it does, vocabulary growth can be more accurate |
| A4 | Willowbrook universe does not exist on disk at research time | Summary | If it exists, SC-4 can be tested immediately; no impact on planning |
| A5 | Dashboard Quality panel refresh at 10s (per rubric) is correct | Dashboard Integration | Rubric specifies 10s; no conflicting constraint |

**A2 is [VERIFIED: persistence.py lines 57-68]** — graph_snapshots table has `node_count INTEGER NOT NULL` and `edge_count INTEGER NOT NULL` columns. This is confirmed.

---

## Sources

### Primary (HIGH confidence)
- `docs/quality/sim-quality-rubric.md` — canonical dimension definitions, formulas, thresholds [VERIFIED: read in full]
- `src/token_world/inspect/stats.py` — aggregator pattern to mirror [VERIFIED: read in full]
- `src/token_world/dashboard/panels/stats.py` — dashboard panel pattern to mirror [VERIFIED: read in full]
- `src/token_world/graph/persistence.py` — graph_snapshots schema [VERIFIED: read in full]
- `tests/test_cli/conftest.py` — tick summary JSON schema [VERIFIED: read in full]
- `tests/test_cli/test_stats.py` — test pattern to mirror [VERIFIED: read in full]
- `tests/test_meta/test_requirements_traceability.py` — CI gate pytest pattern [VERIFIED: read in full]
- `src/token_world/inspect/_shared.py` — iter_tick_files, read_json_file [VERIFIED: read in full]
- `src/token_world/dashboard/app.py` — panel mounting pattern [VERIFIED: read in full]
- `src/token_world/playtest/scorer.py` — TurnScorer; observation_groundedness logic [VERIFIED: read in full]

### Secondary (MEDIUM confidence)
- `.planning/phases/13-quality-kpis-substrate/13-CONTEXT.md` — locked decisions [VERIFIED: read in full]
- `.planning/REQUIREMENTS.md` REQ-V12-QUALITY-02 section [VERIFIED: read]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; versions match existing codebase
- Architecture: HIGH — mirroring proven patterns (stats strip, CI gate script)
- Data availability: MEDIUM — 5/7 dimensions are clean; groundedness and vocab growth need proxy decisions
- Pitfalls: HIGH — identified from actual code patterns and schema gaps

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable patterns; no external dependencies)
