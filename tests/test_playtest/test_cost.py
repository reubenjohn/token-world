"""Tests for ``token_world.playtest.cost`` and the ``token-world cost`` CLI.

Covers:
- Empty universe (no ticks directory, or empty directory)
- Aggregation correctness across multiple ticks
- Batches / epochs walked when present (schema-compatible)
- Malformed JSON tolerance (skipped with stderr warning)
- CLI-subscription annotation (all-zero usage)
- Table output smoke assertions
- JSON output smoke assertions
- CLI exit codes (universe not found => 1; empty ticks => 0)
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from token_world.cli import cli
from token_world.playtest.cost import (
    CostReport,
    StageTotals,
    aggregate,
    render_json,
    render_table,
)
from token_world.universe.manager import UniverseManager


def _write_tick(
    ticks_dir: Path,
    tick_id: str,
    *,
    classifier_in: int = 0,
    classifier_out: int = 0,
    classifier_cost: float = 0.0,
    observer_in: int = 0,
    observer_out: int = 0,
    observer_cost: float = 0.0,
    duration_ms: int = 100,
) -> Path:
    """Write a minimal tick_<id>.json file compatible with the reader."""
    ticks_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "tick_id": tick_id,
        "timestamp_iso": "2026-04-13T00:00:00Z",
        "action_text": "test",
        "classified_action": None,
        "matched_mechanic_id": None,
        "yielded": False,
        "refused": False,
        "refusal_reason": None,
        "mutations": {"count": 0, "list": []},
        "observation_text": None,
        "long_running_action": None,
        "duration_ms": duration_ms,
        "llm_tokens_by_stage": {
            "classifier": {"in": classifier_in, "out": classifier_out},
            "observer": {"in": observer_in, "out": observer_out},
        },
        "llm_cost_usd_by_stage": {
            "classifier": classifier_cost,
            "observer": observer_cost,
        },
    }
    path = ticks_dir / f"tick_{tick_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# aggregate() unit tests
# ---------------------------------------------------------------------------


def test_aggregate_empty_directory(tmp_path: Path) -> None:
    """A universe with no tick_summaries/ yields an empty report."""
    report = aggregate(tmp_path, slug="empty")
    assert report.tick_count == 0
    assert report.total_cost_usd == 0.0
    assert report.total_input_tokens == 0
    assert report.total_output_tokens == 0
    assert report.stage_totals == {}
    assert report.backend_label == "no-data"


def test_aggregate_empty_ticks_dir(tmp_path: Path) -> None:
    """An empty tick_summaries/ticks/ dir yields an empty report."""
    (tmp_path / "tick_summaries" / "ticks").mkdir(parents=True)
    report = aggregate(tmp_path, slug="empty")
    assert report.tick_count == 0
    assert report.warnings == []


def test_aggregate_sums_tokens_and_cost(tmp_path: Path) -> None:
    """Tokens/cost sum correctly across ticks and stages."""
    ticks = tmp_path / "tick_summaries" / "ticks"
    _write_tick(
        ticks,
        "1",
        classifier_in=100,
        classifier_out=20,
        classifier_cost=0.001,
        observer_in=500,
        observer_out=150,
        observer_cost=0.015,
    )
    _write_tick(
        ticks,
        "2",
        classifier_in=50,
        classifier_out=10,
        classifier_cost=0.0005,
        observer_in=300,
        observer_out=100,
        observer_cost=0.010,
    )
    report = aggregate(tmp_path, slug="u")
    assert report.tick_count == 2
    assert report.tick_id_min == "1"
    assert report.tick_id_max == "2"
    assert report.stage_totals["classifier"].calls == 2
    assert report.stage_totals["classifier"].input_tokens == 150
    assert report.stage_totals["classifier"].output_tokens == 30
    assert abs(report.stage_totals["classifier"].cost_usd - 0.0015) < 1e-9
    assert report.stage_totals["observer"].input_tokens == 800
    assert report.stage_totals["observer"].output_tokens == 250
    assert abs(report.stage_totals["observer"].cost_usd - 0.025) < 1e-9
    assert abs(report.total_cost_usd - 0.0265) < 1e-9
    assert report.backend_label == "anthropic-sdk"


def test_aggregate_since_trims_to_last_n(tmp_path: Path) -> None:
    """``since=N`` keeps the last N ticks (numerically)."""
    ticks = tmp_path / "tick_summaries" / "ticks"
    for i in range(1, 6):
        _write_tick(ticks, str(i), classifier_in=10 * i)
    report = aggregate(tmp_path, slug="u", since=2)
    assert report.tick_count == 2
    # last two by numeric order: ticks 4 and 5 => 40 + 50 = 90
    assert report.stage_totals["classifier"].input_tokens == 90
    assert report.tick_id_min == "4"
    assert report.tick_id_max == "5"


def test_aggregate_all_zero_ticks_flagged_cli_subscription(tmp_path: Path) -> None:
    """Ticks with zero tokens + zero cost are flagged as CLI-subscription."""
    ticks = tmp_path / "tick_summaries" / "ticks"
    _write_tick(ticks, "1")  # all zeros by default
    _write_tick(ticks, "2")
    report = aggregate(tmp_path, slug="u")
    assert report.tick_count == 2
    cli_calls = sum(s.cli_subscription_calls for s in report.stage_totals.values())
    assert cli_calls == 4  # 2 ticks x 2 stages
    assert report.backend_label == "claude-cli"
    assert report.total_cost_usd == 0.0


def test_aggregate_mixed_cli_and_sdk_backend_label(tmp_path: Path) -> None:
    """Mix of zero and non-zero stage calls yields ``mixed`` backend label."""
    ticks = tmp_path / "tick_summaries" / "ticks"
    _write_tick(ticks, "1", classifier_in=100, classifier_out=20, classifier_cost=0.001)
    _write_tick(ticks, "2")  # all zeros
    report = aggregate(tmp_path, slug="u")
    assert report.backend_label == "mixed"


def test_aggregate_skips_malformed_json_with_warning(tmp_path: Path) -> None:
    """Malformed JSON files are skipped; a warning is added to the report."""
    ticks = tmp_path / "tick_summaries" / "ticks"
    ticks.mkdir(parents=True)
    (ticks / "tick_1.json").write_text("{not valid json", encoding="utf-8")
    _write_tick(ticks, "2", classifier_in=10)
    report = aggregate(tmp_path, slug="u")
    assert report.tick_count == 1  # only the valid one
    assert any("tick_1.json" in w for w in report.warnings)


def test_aggregate_skips_non_object_json(tmp_path: Path) -> None:
    """A JSON file whose top-level is a list (not a dict) is skipped."""
    ticks = tmp_path / "tick_summaries" / "ticks"
    ticks.mkdir(parents=True)
    (ticks / "tick_1.json").write_text("[1, 2, 3]", encoding="utf-8")
    report = aggregate(tmp_path, slug="u")
    assert report.tick_count == 0
    assert any("tick_1.json" in w for w in report.warnings)


def test_aggregate_handles_missing_usage_fields(tmp_path: Path) -> None:
    """Tick files without cost/token fields count with zero usage."""
    ticks = tmp_path / "tick_summaries" / "ticks"
    ticks.mkdir(parents=True)
    minimal = {
        "schema_version": 1,
        "tick_id": "1",
        "duration_ms": 42,
        # No llm_tokens_by_stage / llm_cost_usd_by_stage.
    }
    (ticks / "tick_1.json").write_text(json.dumps(minimal), encoding="utf-8")
    report = aggregate(tmp_path, slug="u")
    assert report.tick_count == 1
    assert report.duration_ms_total == 42
    assert report.stage_totals == {}  # no stages seen => no rows


def test_aggregate_counts_batches_and_epochs_no_usage(tmp_path: Path) -> None:
    """Current batch/epoch schemas have no usage; count them, don't crash."""
    ts = tmp_path / "tick_summaries"
    _write_tick(ts / "ticks", "1", classifier_in=10)
    (ts / "batches").mkdir(parents=True)
    (ts / "batches" / "batch_1.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "kind": "batch",
                "batch_id": 1,
                "first_tick": "1",
                "last_tick": "10",
                "tick_count": 10,
                "key_events": [],
                "mechanic_ids_used": [],
                "total_mutations": 0,
                "agent_id": "a",
                "haiku_prompt_hash": "abc",
            }
        ),
        encoding="utf-8",
    )
    (ts / "epochs").mkdir(parents=True)
    (ts / "epochs" / "epoch_1.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "kind": "epoch",
                "epoch_id": 1,
                "first_batch": 1,
                "last_batch": 10,
                "batch_count": 10,
                "synopsis": "stuff",
            }
        ),
        encoding="utf-8",
    )
    report = aggregate(tmp_path, slug="u")
    assert report.batch_count == 1
    assert report.epoch_count == 1
    # batch/epoch files had no usage fields — stage_totals stays as per-tick only
    assert set(report.stage_totals.keys()) == {"classifier", "observer"}


def test_aggregate_folds_forward_compatible_batch_usage(tmp_path: Path) -> None:
    """A batch file WITH usage fields (forward-compat) is folded in."""
    ts = tmp_path / "tick_summaries"
    (ts / "ticks").mkdir(parents=True)  # empty ticks
    (ts / "batches").mkdir(parents=True)
    (ts / "batches" / "batch_1.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "kind": "batch",
                "batch_id": 1,
                "first_tick": "1",
                "last_tick": "10",
                "tick_count": 10,
                "key_events": [],
                "mechanic_ids_used": [],
                "total_mutations": 0,
                "agent_id": "a",
                "haiku_prompt_hash": "abc",
                "llm_tokens_by_stage": {
                    "compressor": {"in": 1000, "out": 200},
                },
                "llm_cost_usd_by_stage": {"compressor": 0.002},
            }
        ),
        encoding="utf-8",
    )
    report = aggregate(tmp_path, slug="u")
    assert report.stage_totals["compressor"].input_tokens == 1000
    assert report.stage_totals["compressor"].output_tokens == 200
    assert abs(report.stage_totals["compressor"].cost_usd - 0.002) < 1e-9


def test_aggregate_folds_flat_aggregate_fields(tmp_path: Path) -> None:
    """Flat ``total_*`` fields on batches fall into a ``batch`` pseudo-stage."""
    ts = tmp_path / "tick_summaries"
    (ts / "batches").mkdir(parents=True)
    (ts / "batches" / "batch_1.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "kind": "batch",
                "total_input_tokens": 100,
                "total_output_tokens": 20,
                "total_cost_usd": 0.005,
            }
        ),
        encoding="utf-8",
    )
    report = aggregate(tmp_path, slug="u")
    assert "batch" in report.stage_totals
    assert report.stage_totals["batch"].input_tokens == 100
    assert report.stage_totals["batch"].cost_usd == 0.005


def test_aggregate_reads_real_uatworld_if_present(tmp_path: Path) -> None:
    """Regression: the real uatworld tick files parse without crashing."""
    real = Path.home() / ".local" / "share" / "token_world" / "universes" / "uatworld"
    if not real.is_dir():
        return  # only runs where the dev env has this universe
    report = aggregate(real, slug="uatworld")
    # we don't assert exact counts (universe state drifts) — just no crash
    # and sensible shape.
    assert isinstance(report, CostReport)
    assert report.tick_count >= 0


# ---------------------------------------------------------------------------
# render_table / render_json unit tests
# ---------------------------------------------------------------------------


def test_render_table_empty_report() -> None:
    """Empty report renders the 'no ticks' message."""
    report = CostReport(slug="empty")
    out = render_table(report)
    assert "=== Cost Dashboard: empty ===" in out
    assert "No tick summaries found" in out


def test_render_table_populated_smoke() -> None:
    """Table output contains header, totals, stage rows, backend line."""
    report = CostReport(
        slug="u",
        tick_count=2,
        tick_id_min="1",
        tick_id_max="2",
        duration_ms_total=500,
        stage_totals={
            "classifier": StageTotals(calls=2, input_tokens=150, output_tokens=30, cost_usd=0.0015),
            "observer": StageTotals(calls=2, input_tokens=800, output_tokens=250, cost_usd=0.025),
        },
    )
    out = render_table(report)
    assert "Cost Dashboard: u" in out
    assert "Ticks analyzed:    2" in out
    assert "tick range: 1..2" in out
    assert "classifier" in out
    assert "observer" in out
    assert "Total" in out
    assert "Backend used:" in out
    assert "claude-haiku-4-5-20251001" in out
    assert "claude-sonnet-4-5-20250929" in out


def test_render_table_shows_cli_subscription_line() -> None:
    """When cli-subscription calls exist, a dedicated line appears."""
    report = CostReport(
        slug="u",
        tick_count=1,
        tick_id_min="1",
        tick_id_max="1",
        duration_ms_total=0,
        stage_totals={
            "classifier": StageTotals(calls=1, cli_subscription_calls=1),
            "observer": StageTotals(calls=1, cli_subscription_calls=1),
        },
        all_zero_stage_calls=2,
    )
    out = render_table(report)
    assert "CLI-subscription calls (zero marginal cost): 2" in out
    assert "Backend used:      claude-cli" in out


def test_render_json_valid_and_roundtrips() -> None:
    """JSON output parses and exposes the totals."""
    report = CostReport(
        slug="u",
        tick_count=1,
        tick_id_min="1",
        tick_id_max="1",
        duration_ms_total=100,
        stage_totals={
            "classifier": StageTotals(calls=1, input_tokens=10, output_tokens=5, cost_usd=0.001),
        },
    )
    payload = json.loads(render_json(report))
    assert payload["slug"] == "u"
    assert payload["tick_count"] == 1
    assert payload["total_input_tokens"] == 10
    assert payload["total_output_tokens"] == 5
    assert abs(payload["total_cost_usd"] - 0.001) < 1e-9
    assert payload["stages"]["classifier"]["calls"] == 1
    assert payload["stages"]["classifier"]["model_label"] == "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# CLI integration tests (click.testing)
# ---------------------------------------------------------------------------


def _make_universe_with_ticks(tmp_data_dir: Path, slug_name: str) -> tuple[str, Path]:
    """Create a universe via the manager so CLI resolution works."""
    manager = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = manager.create(slug_name)
    return universe_dir.name, universe_dir


def test_cli_unknown_universe_exits_1(tmp_data_dir: Path, monkeypatch) -> None:
    """``token-world cost <nonexistent>`` exits 1 with a clear error."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    runner = CliRunner()
    result = runner.invoke(cli, ["cost", "does-not-exist"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_cli_empty_universe_exits_0_with_message(tmp_data_dir: Path, monkeypatch) -> None:
    """Empty-ticks case: exit 0, helpful 'no tick summaries' message."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, _ = _make_universe_with_ticks(tmp_data_dir, "cost test empty")
    runner = CliRunner()
    result = runner.invoke(cli, ["cost", slug])
    assert result.exit_code == 0, result.output
    assert "No tick summaries found" in result.output


def test_cli_table_output_smoke(tmp_data_dir: Path, monkeypatch) -> None:
    """Table format shows totals, backend, and stage model IDs."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, universe_dir = _make_universe_with_ticks(tmp_data_dir, "cost test populated")
    ticks = universe_dir / "tick_summaries" / "ticks"
    _write_tick(
        ticks,
        "1",
        classifier_in=100,
        classifier_out=20,
        classifier_cost=0.001,
        observer_in=500,
        observer_out=150,
        observer_cost=0.015,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["cost", slug])
    assert result.exit_code == 0, result.output
    assert "Cost Dashboard:" in result.output
    assert "Ticks analyzed:    1" in result.output
    assert "Backend used:      anthropic-sdk" in result.output
    assert "claude-haiku" in result.output
    assert "claude-sonnet" in result.output


def test_cli_json_output_is_valid_json(tmp_data_dir: Path, monkeypatch) -> None:
    """``--format json`` emits a parseable JSON blob."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, universe_dir = _make_universe_with_ticks(tmp_data_dir, "cost test json")
    ticks = universe_dir / "tick_summaries" / "ticks"
    _write_tick(ticks, "1", classifier_in=10, classifier_out=5, classifier_cost=0.0001)
    runner = CliRunner()
    result = runner.invoke(cli, ["cost", slug, "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["slug"] == slug
    assert payload["tick_count"] == 1
    assert "stages" in payload


def test_cli_since_flag_restricts_window(tmp_data_dir: Path, monkeypatch) -> None:
    """``--since 2`` only aggregates the last 2 ticks."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, universe_dir = _make_universe_with_ticks(tmp_data_dir, "cost test since")
    ticks = universe_dir / "tick_summaries" / "ticks"
    for i in range(1, 6):
        _write_tick(ticks, str(i), classifier_in=100 * i)
    runner = CliRunner()
    result = runner.invoke(cli, ["cost", slug, "--since", "2", "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["tick_count"] == 2
    # Ticks 4 and 5 => 400 + 500 = 900 classifier input tokens
    assert payload["stages"]["classifier"]["input_tokens"] == 900


def test_cli_malformed_json_warning_goes_to_stderr(tmp_data_dir: Path, monkeypatch) -> None:
    """Malformed JSON produces a stderr warning; stdout stays clean."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, universe_dir = _make_universe_with_ticks(tmp_data_dir, "cost test bad json")
    ticks = universe_dir / "tick_summaries" / "ticks"
    ticks.mkdir(parents=True, exist_ok=True)
    (ticks / "tick_1.json").write_text("{broken", encoding="utf-8")
    _write_tick(ticks, "2", classifier_in=10)
    runner = CliRunner()
    result = runner.invoke(cli, ["cost", slug])
    assert result.exit_code == 0, result.output
    # Click 8.3 separates stdout/stderr by default; in 8.x the stderr buffer
    # carries click.echo(..., err=True) output.
    assert "warning:" in result.stderr
    assert "tick_1.json" in result.stderr
    # stdout still renders the (1-tick) dashboard
    assert "Ticks analyzed:    1" in result.output


def test_cli_cli_subscription_annotation(tmp_data_dir: Path, monkeypatch) -> None:
    """All-zero ticks produce a CLI-subscription line, not a naked $0.00 total."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, universe_dir = _make_universe_with_ticks(tmp_data_dir, "cost test cli sub")
    ticks = universe_dir / "tick_summaries" / "ticks"
    _write_tick(ticks, "1")
    _write_tick(ticks, "2")
    runner = CliRunner()
    result = runner.invoke(cli, ["cost", slug])
    assert result.exit_code == 0, result.output
    assert "CLI-subscription calls (zero marginal cost):" in result.output
    assert "Backend used:      claude-cli" in result.output
