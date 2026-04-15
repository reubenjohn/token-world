---
phase: 06-resident-agent-end-to-end-loop
plan: "02"
title: "TickCompressor: online batch + epoch hierarchical tick-summary compression"
subsystem: engine
tags: [compression, tick-summaries, haiku, pydantic, schema-v2, sim-12]
requirements: [SIM-12]
decisions: [D-17, D-18, D-19]
dependency_graph:
  requires:
    - "05-07: TickSummaryWriter.write() (hook point)"
    - "05-08: SimulationEngine._write_summary() (integration site)"
    - "04.1: _atomic_write_json() crash-safe helper"
    - "05-01: TickSummary schema_version=1 (consumed by compressor)"
  provides:
    - "BatchSummary / EpochSummary schema_version=2 Pydantic models"
    - "TickCompressor.maybe_compress(universe_dir, client)"
    - "engine package exports: BatchSummary, EpochSummary, SummaryV2, TickCompressor"
    - "EngineConfig.compression_batch_size / compression_epoch_size fields"
  affects:
    - "06-04: PlaytestRunner (long runs will naturally exercise compression at batch_size=100)"
tech_stack:
  added: []
  patterns:
    - "dataclass(slots=True) for stateless compressor"
    - "WRITE-THEN-DELETE atomicity for crash-safe compression"
    - "Pydantic Literal discriminator on 'kind' field for SummaryV2 tagged union"
    - "Module-level SHA-256 of prompt template stored in BatchSummary for change detection"
key_files:
  created:
    - "src/token_world/engine/compressor.py"
    - "tests/test_engine/test_compressor.py"
  modified:
    - "src/token_world/engine/models.py"
    - "src/token_world/engine/__init__.py"
    - "src/token_world/engine/config.py"
    - "src/token_world/engine/engine.py"
    - "src/token_world/universe/templates/universe_yaml.py"
decisions:
  - "agent_id stubbed to 'unknown' in BatchSummary v1 — TickSummary schema v1 has no actor field; add actor to TickSummary in Phase 7 (D-18 acknowledges sentinel)"
  - "TickCompressor._BATCH_PROMPT_TEMPLATE set post-class-definition (slots=True prevents class-body assignment)"
  - "Epoch check proceeds even when tick_dir absent — allows epoch-only runs when tick compression was already done"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-13"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 7
---

# Phase 6 Plan 02: TickCompressor Summary

**One-liner:** Hierarchical online tick-summary compression (batch + epoch) using Haiku via `TickCompressor.maybe_compress()` hooked into `SimulationEngine._write_summary()` with WRITE-THEN-DELETE crash-safety.

## What Was Built

### BatchSummary + EpochSummary schema v2 (D-18)

Two new Pydantic v2 models in `src/token_world/engine/models.py`:

**BatchSummary** — compresses N tick files into one batch:
```
schema_version: Literal[2] = 2
kind: Literal["batch"] = "batch"
batch_id: int
first_tick: str, last_tick: str
tick_count: int
key_events: list[str]        # 3-5 strings from Haiku
mechanic_ids_used: list[str]  # union of matched_mechanic_ids
total_mutations: int
agent_id: str                # "unknown" in v1 (D-18 note)
haiku_prompt_hash: str       # SHA-256 of _BATCH_PROMPT_TEMPLATE
```

**EpochSummary** — compresses N batch files into one epoch:
```
schema_version: Literal[2] = 2
kind: Literal["epoch"] = "epoch"
epoch_id: int
first_batch: int, last_batch: int
batch_count: int
synopsis: str                # one-paragraph Haiku narrative
```

**SummaryV2** tagged union with `kind` discriminator — `BatchSummary | EpochSummary` — parses both kinds from raw JSON.

All three exported from `token_world.engine`.

### EngineConfig compression fields (D-17)

`src/token_world/engine/config.py` gains:
- `compression_batch_size: int = 100`
- `compression_epoch_size: int = 100`

`load_engine_config()` reads `compression.batch_size` and `compression.epoch_size` from `universe.yaml` with int-coercion and warn-to-logger fallback on invalid values.

Universe YAML template (`universe_yaml.py`) includes a commented-out `compression:` block documenting the defaults.

### TickCompressor module interface (D-19)

`src/token_world/engine/compressor.py` — `TickCompressor` dataclass:

```python
@dataclass(slots=True)
class TickCompressor:
    batch_size: int = 100
    epoch_size: int = 100
    model: str = "claude-haiku-4-5"

    def maybe_compress(self, universe_dir: Path, client: Any) -> None: ...
```

**Algorithm:**
1. If `batch_size <= 0 or epoch_size <= 0` → return (disabled).
2. Scan `tick_summaries/ticks/tick_*.json` sorted by numeric ID.
3. If `len >= batch_size`: compress oldest `batch_size` ticks → `tick_summaries/batch_<id>.json`.
4. Scan `tick_summaries/batch_*.json` sorted by numeric ID.
5. If `len >= epoch_size`: compress oldest `epoch_size` batches → `tick_summaries/epoch_<id>.json`.

**Atomicity pattern (WRITE-THEN-DELETE, 06-RESEARCH Pitfall 5):**
- `_atomic_write_json(batch_path, ...)` — crash-safe write via temp file + rename.
- Only AFTER the output file is written do the input files get `unlink()`'d.
- On crash between write and delete: next run finds the output, allocates a new ID, compresses again. At-least-once is acceptable; no data loss.

**ID allocation:** `_next_batch_id()` / `_next_epoch_id()` return `max(existing_ids) + 1`, or `0` if none. Monotonically increasing; no collision with pre-existing files.

**Haiku prompt hash:** `_BATCH_PROMPT_HASH = hashlib.sha256(_BATCH_PROMPT_TEMPLATE.encode()).hexdigest()` is a module-level constant computed once and stored in every `BatchSummary.haiku_prompt_hash`. Downstream tooling can detect prompt changes by comparing stored hashes.

### Batch prompt template SHA-256s

| Template | SHA-256 |
|----------|---------|
| `_BATCH_PROMPT_TEMPLATE` | `ae0a3d257a453bafdaa856283a1019f7f63c91f663e94922152521923f15a20f` |
| `_EPOCH_PROMPT_TEMPLATE` | `9e7607f77c7456e572daff6b1a3204b8aedb5a0596508b24b4e295a055869f40` |

### Engine hook location (D-19)

`src/token_world/engine/engine.py`, `_write_summary()` method, **line 784**:

```python
self._summary_writer.write(summary, self._universe_path)
# D-19: opportunistic compression after every tick write.
# Failures MUST NOT cause the tick itself to fail — compression is best-effort.
try:
    self._compressor.maybe_compress(self._universe_path, self._anthropic_client)
except Exception as exc:
    logger.warning("TickCompressor failed (tick still succeeded): %s", exc)
```

The `_compressor` is instantiated in `SimulationEngine.__init__()` from `EngineConfig.compression_batch_size` / `compression_epoch_size`. The Anthropic client reference is stored as `self._anthropic_client` (added in this plan).

The compressor fires on ALL three tick paths (execute, yield, refuse) because all three call `_write_summary()`.

### Interaction with Plan 06-04 (PlaytestRunner)

The PlaytestRunner (06-04) runs `SimulationEngine.run_tick()` in a loop. At default `batch_size=100`, compression won't fire during a 20-turn playtest run (the default). For longer runs or benchmarks with `--turns 200+`, the compressor will naturally fire once and produce a `batch_0.json`. The compressor is transparent to the PlaytestRunner — no API changes needed.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 1: BatchSummary + EpochSummary models | `b72ee92` | engine/models.py, engine/__init__.py, test_compressor.py |
| Task 2: EngineConfig compression fields | `10b02c0` | engine/config.py, universe_yaml.py, test_compressor.py |
| Task 3: TickCompressor + engine hook | `7056206` | engine/compressor.py, engine/engine.py, engine/__init__.py |

## Test Coverage

17 tests in `tests/test_engine/test_compressor.py` covering:
- Schema v2 round-trips and discriminated union parsing (tests 1-4)
- EngineConfig defaults, YAML loading, malformed-config fallback, template content (tests 5-8)
- No-op below threshold (test 9)
- Exact-threshold batch creation (test 10)
- WRITE-THEN-DELETE atomicity verification (test 11)
- Partial remainder preserved (test 12)
- Epoch creation at batch threshold (test 13)
- Monotonic batch ID allocation (test 14)
- Disabled when batch_size=0 (test 15)
- Engine hook calls compressor 3× for 3 ticks (test 16)
- Haiku prompt hash stored correctly (test 17)

## Deviations from Plan

**1. [Rule 1 - Bug] Epoch check restructured to not require tick_dir**
- **Found during:** Task 3, test 13
- **Issue:** Original control flow returned early when `tick_dir` was missing, preventing the epoch check from running in scenarios where only batch files exist (no tick files present).
- **Fix:** Restructured `maybe_compress` to check tick dir conditionally; epoch check always runs if `tick_summaries/` exists.
- **Files modified:** `src/token_world/engine/compressor.py`
- **Commit:** `7056206`

**2. [Rule 1 - Bug] slots=True prevents class-body attribute assignment**
- **Found during:** Task 3, test 17
- **Issue:** `_BATCH_PROMPT_TEMPLATE: str = _BATCH_PROMPT_TEMPLATE` inside `@dataclass(slots=True)` creates a slot descriptor, not a string attribute. `TickCompressor._BATCH_PROMPT_TEMPLATE.encode()` raised `AttributeError`.
- **Fix:** Set `TickCompressor._BATCH_PROMPT_TEMPLATE = _BATCH_PROMPT_TEMPLATE` after the class definition (Python allows post-definition class attribute assignment on slotted dataclasses).
- **Files modified:** `src/token_world/engine/compressor.py`
- **Commit:** `7056206`

## Known Stubs

- `agent_id = "unknown"` in `BatchSummary` — TickSummary schema v1 has no actor field. The D-18 schema requires the field; it carries a sentinel value. Planned resolution: add `actor` to `TickSummary` in Phase 7 alongside attention work, then populate `BatchSummary.agent_id` from the tick data.

## Threat Flags

None. `TickCompressor` reads/writes only the universe's own `tick_summaries/` directory. No new network endpoints, auth paths, or trust-boundary crossings introduced.

## Self-Check: PASSED

- `src/token_world/engine/compressor.py` — FOUND
- `src/token_world/engine/models.py` (BatchSummary, EpochSummary) — FOUND
- `src/token_world/engine/config.py` (compression_batch_size) — FOUND
- `src/token_world/engine/engine.py` (compressor hook line 784) — FOUND
- `src/token_world/engine/__init__.py` (TickCompressor exported) — FOUND
- `tests/test_engine/test_compressor.py` (17 tests) — FOUND
- Commit `b72ee92` — FOUND
- Commit `10b02c0` — FOUND
- Commit `7056206` — FOUND
- `uv run pytest tests/ -x -q` → 1275 passed (1258 baseline + 17 new)
