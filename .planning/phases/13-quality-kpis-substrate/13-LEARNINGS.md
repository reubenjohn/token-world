---
phase: 13-quality-kpis-substrate
phase_name: Quality KPIs Substrate
project: token_world
generated: 2026-04-14
counts:
  decisions: 4
  lessons: 4
  patterns: 2
  surprises: 1
missing_artifacts:
  - 13-CONTEXT.md (not present in phase directory — was consumed during planning, not checked in as a standalone artifact)
---

# Phase 13 Learnings — Quality KPIs Substrate

## Decisions

### D-1: 8th Dimension (novel_subtype_rate) Added Beyond 7 in Rubric — WARN-Only

The rubric (`docs/quality/sim-quality-rubric.md`) specifies 7 rubric dimensions. Research (13-RESEARCH.md) surfaced a discrepancy: the CONTEXT planned 8 dimensions, adding `novel_subtype_rate` as an informational signal. The dimension was implemented as the 8th scorer with a WARN-only gate (no FAIL path) — it fires WARN when zero new subtypes appear across >= 30 ticks, indicating the universe may have stopped growing, but it never triggers a hard FAIL because the rubric itself does not define red-range thresholds for this signal.

**Rationale:** The WARN-only posture lets CI catch stagnant universes without blocking healthy ones that simply aren't introducing new entity subtypes in a window.

**Files:** `src/token_world/quality/thresholds.py` (`SUBTYPE_RATE_WARN = 0.0`), `src/token_world/quality/scorer.py` (`_score_novel_subtype_rate`)

---

### D-2: Groundedness Uses Mutation-Backed Proxy (Option A), Not Cross-Check

Research identified two candidate implementations for groundedness scoring: (A) a proxy rate counting ticks where mutations occurred or an honest refusal was issued, and (B) a cross-check comparing the observation text against the mutation list using an LLM or heuristic. Option A was chosen because it requires no LLM calls, is deterministic, and is already grounded in concrete tick data.

**Rationale:** Operator-facing CLI and CI tooling must be cost-free and fast. Option B's observer cross-check is higher fidelity but adds latency and cost — deferred to a future rubric revision.

**Files:** `src/token_world/quality/scorer.py` (`_score_groundedness`)

---

### D-3: CLI Exits 0 Always; CI Gate Handles Non-Zero

The `token-world quality <slug>` CLI command always exits with code 0, even when the verdict is FAILED. Non-zero exit behavior lives exclusively in `scripts/check_quality_thresholds.py`. This separates the reporting surface from the gating surface.

**Rationale:** Keeping CLI exit at 0 makes `--format json` pipeable without special-casing (`| jq .verdict` works cleanly). CI pipelines that want gating call the dedicated gate script, not the CLI.

**Files:** `src/token_world/cli.py` (quality command), `scripts/check_quality_thresholds.py`

---

### D-4: Test Isolation Uses XDG_DATA_HOME, Not TOKEN_WORLD_UNIVERSES_DIR

Plan 02 template proposed `TOKEN_WORLD_UNIVERSES_DIR` as the env var for pointing test fixtures at a `tmp_path`-scoped universes directory. After reading `src/token_world/universe/paths.py`, the actual path resolution was confirmed to use `XDG_DATA_HOME`. Test fixtures in `tests/test_meta/test_quality_thresholds.py` set `XDG_DATA_HOME=tmp_path/xdg_home` so `UniverseManager` resolves to `tmp_path/xdg_home/token_world/universes/<slug>/`.

**Rationale:** The implementation was authoritative over the plan template. Using the wrong env var would have caused test fixtures to silently write into the real user's universes directory.

**Files:** `tests/test_meta/test_quality_thresholds.py`, `src/token_world/universe/paths.py`

---

## Lessons

### L-1: Rubric Says 7 Dimensions; CONTEXT Said 8 — Research Surfaced the Discrepancy

The quality rubric document (`docs/quality/sim-quality-rubric.md`) enumerates 7 dimensions. The 13-CONTEXT.md specced 8. Research (13-RESEARCH.md) caught this discrepancy before execution, allowing the executor to implement 8 dimensions as intended rather than 7 as the rubric document literally stated. Without a dedicated research phase, the executor would have followed the rubric literally and shipped an incomplete scorer.

**Takeaway:** Research phases that explicitly compare planning artifacts against primary sources (requirements doc vs. context spec vs. rubric doc) are worth the time investment on dimension-count-sensitive work.

---

### L-2: willowbrook Not in Repo — SC-4 Must Be Manual Pre-Merge

SC-4 ("real data smoke test") requires running `uv run token-world quality willowbrook --last 50` against the live willowbrook universe. Willowbrook universe data is not committed to the repo; it lives at `/home/reuben/.local/share/token_world/universes/willowbrook/` on the developer's machine. This means SC-4 cannot be automated in CI and must be manually executed before merging any quality-scorer changes that could affect how real universe data is scored.

**Takeaway:** Any feature that gates on real universe data needs a documented manual verification step. The VERIFICATION.md captures this as a `human_verification` entry so it isn't silently dropped.

---

### L-3: universe.db Required for Manager.load() — Not universe.json

Plan 02 template proposed writing a `universe.json` file to make `UniverseManager.load()` recognize a fixture universe. Reading `src/token_world/universe/manager.py` revealed the actual check is for `universe.db` (SQLite), not a JSON metadata file. The test fixtures were updated to create a minimal SQLite `universe.db` via `sqlite3.connect`.

**Takeaway:** Plan templates that specify fixture structure should be verified against the actual loader implementation before writing tests. The time cost of reading one file is lower than the time cost of debugging a mysteriously-failing test that can't find the universe.

---

### L-4: Pre-Commit Hook Catches Ruff Issues That Tests Don't

Both plan executions hit ruff pre-commit hook failures (SIM108 ternary in Plan 01; import order in Plan 02). These were auto-fixed and folded into the task commit. The hook caught issues that the test suite passes silently — specifically, style violations the linter enforces but pytest doesn't check.

**Takeaway:** Running ruff locally before committing (rather than relying on the pre-commit hook as a backstop) avoids the commit-fail-fix-recommit cycle. The Script Catalog entry `uv run ruff check src/` is the right gate to run proactively.

---

## Patterns

### P-1: Scorer / Dashboard Panel / CI Gate Triple

Phase 13 established a three-layer pattern for quality signals:

```
scorer.py          →  compute QualityReport (pure Python, no side effects)
  ↓ Python import
panel.py           →  mount_quality_panel (NiceGUI, 10s refresh, coloured cells)
  ↓ Python import
check_script.py    →  CI gate script (exits 1 on FAIL, names failing dimensions)
  ↓ subprocess.run
test_meta.py       →  pytest wrapper (exits 1 captured as assertion failure)
```

Each layer consumes the layer above via Python import — no subprocess re-invocation until the pytest gate calls the CI script. This keeps the scorer as the single source of truth; the dashboard and CI gate never recompute.

**Applies to:** Any new quality signal added in future phases should follow this triple. The dashboard panel pattern is in `src/token_world/dashboard/panels/stats.py` (older) and `quality.py` (newer).

---

### P-2: XDG_DATA_HOME Isolation for Subprocess-Based Pytest Fixtures

When a pytest test needs to run a subprocess (e.g., `uv run python scripts/check_quality_thresholds.py`) against a fixture universe, isolating the fixture requires overriding the path-resolution env var. For Token World this is `XDG_DATA_HOME`. The pattern:

```python
env = {**os.environ, "XDG_DATA_HOME": str(tmp_path / "xdg_home")}
subprocess.run([...], env=env, cwd=REPO_ROOT, ...)
```

The fixture universe is then written to `tmp_path / "xdg_home" / "token_world" / "universes" / slug /`.

**Applies to:** Any future test that invokes a CLI script or external subprocess against a synthetic universe. See `tests/test_meta/test_quality_thresholds.py` for the canonical example.

---

## Surprises

### S-1: graph_snapshots Table (Not graph_events) is the Correct Fan-Out Source

Initial intuition (and early draft scorer logic) reached for `graph_events` as the source for graph fan-out slope. Research (13-RESEARCH.md Pattern 4) corrected this: `graph_snapshots` contains pre-aggregated `(tick_id, node_count, edge_count)` rows that are exactly what the fan-out scorer needs. Reading `graph_events` would require re-aggregating every mutation into a current count — far more expensive and fragile.

**Impact:** The `_score_graph_fanout` scorer queries `graph_snapshots` directly with `SELECT tick_id, node_count, edge_count FROM graph_snapshots ORDER BY tick_id DESC LIMIT 5`. This is a one-row-per-snapshot query (max 5 rows) rather than a potentially-huge event log scan.

**Takeaway:** When adding new scorers that read from the persistence layer, read the actual SQLite schema before deciding which table to query. The graph module's `persistence.py` and `events.py` have distinct purposes that aren't obvious from names alone.
