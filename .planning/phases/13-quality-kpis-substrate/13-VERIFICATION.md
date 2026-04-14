---
phase: 13-quality-kpis-substrate
verified: 2026-04-14T00:00:00Z
status: passed
score: 4/4
overrides_applied: 0
human_verification:
  - test: "Run `token-world quality willowbrook` on the live willowbrook dataset"
    expected: "Scorecard with all 8 dimensions showing interpretable scores (no crash, no INSUFFICIENT_DATA)"
    why_human: "Willowbrook universe not available in CI; requires local environment with real run data (SC-4)"
    result: "VERIFIED 2026-04-14 — scorecard ran cleanly on willowbrook (50 ticks): 8 dimensions scored, verdict=FAILED (expected given pre-ENGINE-01 history). No crash, no INSUFFICIENT_DATA. Calibration notes: vocabulary_growth FAIL is stagnation not rate (accurate); character_stability breaks from early seeding phase action_text; refusal_cluster max=9 reflects pre-fix era."
---

# Phase 13: Quality KPIs Substrate — Verification Report

**Phase Goal:** Every overnight run ends with an automatable, mechanically-scored quality report consumed by both CLI users and the dashboard — with CI able to gate a release on thresholds from the sim-quality rubric.
**Verified:** 2026-04-14
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `token-world quality <slug>` prints a scorecard with all 8 rubric dimensions | VERIFIED | CLI command exists (`uv run token-world quality --help` confirmed); scorer.py implements all 8 dimension scorers: Groundedness, Character stability, Action coherence, Refusal cluster, Vocabulary growth, Conservation drift, Graph fan-out, Novel subtype rate |
| 2 | Dashboard Quality panel uses Python import, never recomputes | VERIFIED | `quality.py` panel imports `from token_world.quality import QualityReport, score` (line 13); no subprocess or shell calls present; `app.py` mounts panel at lines 76+78 |
| 3 | CI gate fails with named-dimension error when threshold breached | VERIFIED | `test_failing_fixture_exits_nonzero` passes: all-refused fixture exits 1 with "Action coherence" in stderr; `test_healthy_fixture_exits_zero` passes |
| 4 | Works on real data (willowbrook) | VERIFIED | `uv run token-world quality willowbrook --last 50` ran cleanly: 8 dimensions scored, verdict=FAILED (expected — pre-ENGINE-01 history). No crash, no INSUFFICIENT_DATA |

**Score:** 3/3 programmatically verified truths + 1 human-needed item

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/token_world/quality/__init__.py` | Public exports: score, QualityReport, DimensionResult | VERIFIED | Exports all 3; 11 lines |
| `src/token_world/quality/report.py` | QualityReport, DimensionResult dataclasses + render_table + render_json | VERIFIED | Full implementation |
| `src/token_world/quality/thresholds.py` | GREEN/RED constants for all 8 dimensions; MARKERS list; verdict logic | VERIFIED | All constants + compute_verdict() present |
| `src/token_world/quality/scorer.py` | score() -> QualityReport; all 8 dimension scorers | VERIFIED | 362 lines; all 8 private scorers implemented with graceful degradation |
| `src/token_world/cli.py` | @cli.command('quality') registered | VERIFIED | `--help` shows SLUG, --last, --format; exits 0 always |
| `tests/test_cli/test_quality.py` | Unit tests per scorer + CLI integration test | VERIFIED | 13 tests; all pass |
| `src/token_world/dashboard/panels/quality.py` | mount_quality_panel; load_quality; render_cells | VERIFIED | All 3 exports present; 10s timer; coloured cells |
| `src/token_world/dashboard/app.py` | Quality panel mounted above stats strip | VERIFIED | Lines 76+78 mount panel before stats |
| `scripts/check_quality_thresholds.py` | CI gate; exits 1 on FAIL verdict; names failing dimensions | VERIFIED | Full implementation; exits 1 on all-refused fixture with "Action coherence" named in stderr |
| `tests/test_meta/test_quality_thresholds.py` | pytest-wired CI gate tests | VERIFIED | 3 tests; all pass |
| `tests/test_dashboard/test_quality_panel.py` | Dashboard panel unit tests | VERIFIED | 7 tests; all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli.py` quality command | `quality/scorer.py` | `from token_world.quality import score` (line 1785) | WIRED | Confirmed by grep |
| `dashboard/panels/quality.py` | `quality/scorer.py` | `from token_world.quality import QualityReport, score` (line 13) | WIRED | No subprocess; Python import only |
| `dashboard/app.py` | `dashboard/panels/quality.py` | `from token_world.dashboard.panels.quality import mount_quality_panel` (lines 76+78) | WIRED | Confirmed by grep |
| `tests/test_meta/test_quality_thresholds.py` | `scripts/check_quality_thresholds.py` | `subprocess.run(["uv", "run", "python", str(SCRIPT), slug])` | WIRED | Test passes; script invoked via subprocess |
| `quality/scorer.py` | `tick_summaries/ticks/*.json` | `iter_tick_files` from `token_world.inspect._shared` | WIRED | Import confirmed in scorer.py line 16 |
| `quality/scorer.py` | `universe.db graph_snapshots` | `sqlite3.connect(str(db_path))` | WIRED | SELECT on graph_snapshots table; graceful degradation if missing |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `scorer.py` | `payloads` | `iter_tick_files` + `read_json_file` from real `tick_summaries/ticks/*.json` | Yes — reads actual tick JSON files | FLOWING |
| `dashboard/panels/quality.py` | `report` | `load_quality()` calls `score()` Python import | Yes — same scorer, no recompute | FLOWING |
| `scripts/check_quality_thresholds.py` | `report` | `score()` via `token_world.quality` import | Yes — same scorer | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CLI command exists with correct options | `token-world quality --help` | Shows SLUG, --last INTEGER, --format options | PASS |
| All 23 quality tests pass | `pytest tests/test_cli/test_quality.py tests/test_meta/test_quality_thresholds.py tests/test_dashboard/test_quality_panel.py -q` | 23 passed in 2.45s | PASS |
| Lint passes on quality files | `ruff check src/token_world/quality/ src/token_world/dashboard/panels/quality.py scripts/check_quality_thresholds.py` | All checks passed | PASS |
| Dashboard panel uses no subprocess | grep subprocess in quality.py | No matches (only in docstring comment) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REQ-V12-QUALITY-02 | 13-01, 13-02 | 8-dimension quality scorer, CLI command, dashboard panel, CI gate | SATISFIED | All 4 success criteria addressed (SC-1 through SC-3 verified; SC-4 human) |

### Anti-Patterns Found

No blockers or stubs found. All dimension scorers produce real computed values from tick data. Dashboard panel uses Python import, not subprocess. CI gate names failing dimensions.

### Human Verification Required

#### 1. SC-4: Real Data Smoke Test

**Test:** Run `uv run token-world quality willowbrook --last 50` against the live willowbrook universe
**Expected:** Scorecard prints with all 8 dimensions showing numeric scores and [OK]/[WARN]/[FAIL] status; no crash; verdict is not INSUFFICIENT_DATA
**Why human:** Willowbrook universe data is not committed to the repo and is not available in CI; requires local environment with the existing run data

### Gaps Summary

No gaps blocking goal achievement. All programmatically verifiable success criteria are met:
- SC-1: `token-world quality <slug>` exists, shows all 8 rubric dimensions, degrades gracefully
- SC-2: Dashboard Quality panel imports `score` from `token_world.quality` (Python import, no subprocess); mounts with 10s timer above stats strip
- SC-3: CI gate exits non-zero with named dimension ("Action coherence") when threshold breached; pytest-wired in `tests/test_meta/`

SC-4 (real data) is the only remaining item and requires human testing with the willowbrook dataset.

---

_Verified: 2026-04-14T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
