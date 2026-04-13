"""Tests for TickCompressor and BatchSummary/EpochSummary schema v2 (SIM-12).

Plan 06-02: D-17 (online trigger), D-18 (schema v2), D-19 (stateless compressor).

Tests are organised in task order:
    Task 1 (tests 1-4):  BatchSummary + EpochSummary Pydantic models
    Task 2 (tests 5-8):  EngineConfig compression fields + universe.yaml template
    Task 3 (tests 9-17): TickCompressor + engine hook
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Task 1 — BatchSummary + EpochSummary schema v2
# ---------------------------------------------------------------------------


def test_batch_summary_requires_schema_v2_and_kind_batch():
    """BatchSummary has schema_version==2 and kind=='batch' as discriminator."""
    from token_world.engine.models import BatchSummary

    bs = BatchSummary(
        batch_id=0,
        first_tick="1",
        last_tick="100",
        tick_count=100,
        key_events=[],
        mechanic_ids_used=[],
        total_mutations=0,
        agent_id="alice",
        haiku_prompt_hash="abc",
    )
    assert bs.schema_version == 2
    assert bs.kind == "batch"
    # Round-trip
    dumped = json.loads(bs.model_dump_json())
    bs2 = BatchSummary.model_validate(dumped)
    assert bs2.batch_id == 0
    assert bs2.agent_id == "alice"


def test_epoch_summary_requires_schema_v2_and_kind_epoch():
    """EpochSummary has schema_version==2 and kind=='epoch' as discriminator."""
    from token_world.engine.models import EpochSummary

    es = EpochSummary(
        epoch_id=0,
        first_batch=0,
        last_batch=99,
        batch_count=100,
        synopsis="A long simulation arc.",
    )
    assert es.schema_version == 2
    assert es.kind == "epoch"
    # Round-trip
    dumped = json.loads(es.model_dump_json())
    es2 = EpochSummary.model_validate(dumped)
    assert es2.epoch_id == 0
    assert es2.synopsis == "A long simulation arc."


def test_discriminated_union_summary_v2_accepts_either_kind():
    """SummaryV2 union parses kind='batch' -> BatchSummary, kind='epoch' -> EpochSummary."""
    from pydantic import TypeAdapter

    from token_world.engine.models import BatchSummary, EpochSummary, SummaryV2

    ta = TypeAdapter(SummaryV2)

    batch_data = {
        "schema_version": 2,
        "kind": "batch",
        "batch_id": 5,
        "first_tick": "1",
        "last_tick": "100",
        "tick_count": 100,
        "key_events": ["e1"],
        "mechanic_ids_used": ["mech_a"],
        "total_mutations": 42,
        "agent_id": "unknown",
        "haiku_prompt_hash": "deadbeef",
    }
    parsed_batch = ta.validate_python(batch_data)
    assert isinstance(parsed_batch, BatchSummary)
    assert parsed_batch.batch_id == 5

    epoch_data = {
        "schema_version": 2,
        "kind": "epoch",
        "epoch_id": 0,
        "first_batch": 0,
        "last_batch": 4,
        "batch_count": 5,
        "synopsis": "Much happened.",
    }
    parsed_epoch = ta.validate_python(epoch_data)
    assert isinstance(parsed_epoch, EpochSummary)
    assert parsed_epoch.epoch_id == 0


def test_models_exported_from_engine_package():
    """BatchSummary, EpochSummary, SummaryV2 are importable from token_world.engine."""
    from token_world.engine import BatchSummary, EpochSummary, SummaryV2  # noqa: F401

    assert BatchSummary is not None
    assert EpochSummary is not None
    assert SummaryV2 is not None


# ---------------------------------------------------------------------------
# Task 2 — EngineConfig compression fields + universe.yaml template
# ---------------------------------------------------------------------------


def test_engine_config_defaults_include_compression_settings():
    """Default EngineConfig has compression_batch_size==100 and compression_epoch_size==100."""
    from token_world.engine.config import EngineConfig

    cfg = EngineConfig()
    assert cfg.compression_batch_size == 100
    assert cfg.compression_epoch_size == 100


def test_load_engine_config_reads_compression_section(tmp_path: Path):
    """load_engine_config parses compression.batch_size and compression.epoch_size."""
    from token_world.engine.config import load_engine_config

    (tmp_path / "universe.yaml").write_text(
        "universe_seed: 1\ncompression:\n  batch_size: 50\n  epoch_size: 10\n",
        encoding="utf-8",
    )
    cfg = load_engine_config(tmp_path)
    assert cfg.compression_batch_size == 50
    assert cfg.compression_epoch_size == 10


def test_load_engine_config_malformed_compression_uses_defaults(tmp_path: Path):
    """Malformed compression.batch_size falls back to 100 with a warning."""
    import logging

    from token_world.engine.config import load_engine_config

    (tmp_path / "universe.yaml").write_text(
        "universe_seed: 1\ncompression:\n  batch_size: not-an-int\n",
        encoding="utf-8",
    )
    with pytest.warns(None):  # just suppress; warning goes to logger not warnings
        pass
    with pytest.MonkeyPatch().context() as mp:
        # capture logger.warning calls
        warnings_issued: list[str] = []
        real_warning = logging.Logger.warning

        def _capture(self, msg, *args, **kw):  # type: ignore[override]
            warnings_issued.append(msg % args if args else msg)
            real_warning(self, msg, *args, **kw)

        mp.setattr(logging.Logger, "warning", _capture)
        cfg = load_engine_config(tmp_path)

    assert cfg.compression_batch_size == 100  # default
    # At least one warning was issued about malformed compression config
    assert any("compression" in w.lower() or "batch_size" in w.lower() for w in warnings_issued)


def test_universe_yaml_template_contains_compression_block():
    """render_universe_yaml() produces YAML text with a commented compression: block."""
    from token_world.universe.templates.universe_yaml import render_universe_yaml

    rendered = render_universe_yaml(universe_seed=1234)
    assert "# compression:" in rendered
    assert "batch_size" in rendered
    assert "epoch_size" in rendered


# ---------------------------------------------------------------------------
# Task 3 — TickCompressor + engine hook
# ---------------------------------------------------------------------------


def _write_tick_files(tick_dir: Path, count: int) -> None:
    """Write `count` minimal TickSummary-v1 JSON files to tick_dir."""
    tick_dir.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        data = {
            "schema_version": 1,
            "tick_id": str(i + 1),
            "timestamp_iso": "2026-01-01T00:00:00Z",
            "action_text": f"action {i}",
            "classified_action": None,
            "matched_mechanic_id": "mech_a" if i % 3 == 0 else None,
            "yielded": False,
            "refused": False,
            "refusal_reason": None,
            "mutations": {"count": i % 5, "list": []},
            "observation_text": f"You did action {i}." if i % 2 == 0 else None,
            "duration_ms": 100,
            "llm_tokens_by_stage": {},
            "llm_cost_usd_by_stage": {},
        }
        (tick_dir / f"tick_{i + 1}.json").write_text(json.dumps(data), encoding="utf-8")


def _write_batch_files(batch_dir: Path, count: int, start_id: int = 0) -> None:
    """Write `count` minimal BatchSummary-v2 JSON files to batch_dir."""
    batch_dir.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        bid = start_id + i
        data = {
            "schema_version": 2,
            "kind": "batch",
            "batch_id": bid,
            "first_tick": str(bid * 100 + 1),
            "last_tick": str((bid + 1) * 100),
            "tick_count": 100,
            "key_events": ["e1"],
            "mechanic_ids_used": ["mech_a"],
            "total_mutations": 50,
            "agent_id": "unknown",
            "haiku_prompt_hash": "abc",
        }
        (batch_dir / f"batch_{bid}.json").write_text(json.dumps(data), encoding="utf-8")


def _make_mock_haiku_batch():
    """Mock Anthropic client returning a valid Haiku batch-compression response."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps(
                {
                    "key_events": ["e1", "e2"],
                    "mechanic_ids_used": ["mech_a"],
                    "total_mutations": 50,
                }
            )
        )
    ]
    mock_client.messages.create.return_value = mock_response
    return mock_client


def _make_mock_haiku_epoch():
    """Mock Anthropic client returning a valid Haiku epoch-compression response."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({"synopsis": "A long simulation arc."}))]
    mock_client.messages.create.return_value = mock_response
    return mock_client


def test_maybe_compress_noop_when_below_threshold(tmp_path: Path):
    """99 tick files with batch_size=100 → no compression, mock never called."""
    from token_world.engine.compressor import TickCompressor

    tick_dir = tmp_path / "tick_summaries" / "ticks"
    _write_tick_files(tick_dir, 99)

    mock_client = MagicMock()
    compressor = TickCompressor(batch_size=100, epoch_size=100)
    compressor.maybe_compress(tmp_path, mock_client)

    assert mock_client.messages.create.call_count == 0
    assert len(list(tick_dir.glob("tick_*.json"))) == 99
    assert len(list((tmp_path / "tick_summaries").glob("batch_*.json"))) == 0


def test_maybe_compress_creates_batch_at_exact_threshold(tmp_path: Path):
    """100 tick files → 1 batch_0.json created, 0 ticks remain, Haiku called once."""
    from token_world.engine.compressor import TickCompressor
    from token_world.engine.models import BatchSummary

    tick_dir = tmp_path / "tick_summaries" / "ticks"
    _write_tick_files(tick_dir, 100)
    mock_client = _make_mock_haiku_batch()

    compressor = TickCompressor(batch_size=100, epoch_size=100)
    compressor.maybe_compress(tmp_path, mock_client)

    # One batch file created
    batch_files = list((tmp_path / "tick_summaries").glob("batch_*.json"))
    assert len(batch_files) == 1
    assert batch_files[0].name == "batch_0.json"

    # Batch has schema v2 content
    batch = BatchSummary.model_validate_json(batch_files[0].read_text())
    assert batch.schema_version == 2
    assert batch.kind == "batch"
    assert batch.tick_count == 100
    assert "e1" in batch.key_events

    # All tick files deleted
    assert len(list(tick_dir.glob("tick_*.json"))) == 0

    # Haiku called exactly once
    assert mock_client.messages.create.call_count == 1


def test_maybe_compress_batch_file_written_before_ticks_deleted(tmp_path: Path):
    """Crash-safety: batch file must exist before any tick file is unlinked."""
    from token_world.engine.compressor import TickCompressor

    tick_dir = tmp_path / "tick_summaries" / "ticks"
    _write_tick_files(tick_dir, 100)
    mock_client = _make_mock_haiku_batch()

    batch_existed_before_unlink: list[bool] = []

    original_unlink = Path.unlink

    def _patched_unlink(self: Path, missing_ok: bool = False) -> None:  # type: ignore[override]
        # Only intercept tick file deletions
        if "tick_" in self.name and self.parent.name == "ticks":
            batch_dir = self.parent.parent
            batches = list(batch_dir.glob("batch_*.json"))
            batch_existed_before_unlink.append(len(batches) > 0)
        original_unlink(self, missing_ok=missing_ok)

    compressor = TickCompressor(batch_size=100, epoch_size=100)
    with patch.object(Path, "unlink", _patched_unlink):
        compressor.maybe_compress(tmp_path, mock_client)

    # Every tick unlink must have seen the batch file already present
    assert len(batch_existed_before_unlink) == 100
    assert all(batch_existed_before_unlink), "Batch written BEFORE tick deletion violated"


def test_maybe_compress_partial_remainder_preserved(tmp_path: Path):
    """150 tick files with batch_size=100 → 1 batch + 50 ticks remain."""
    from token_world.engine.compressor import TickCompressor

    tick_dir = tmp_path / "tick_summaries" / "ticks"
    _write_tick_files(tick_dir, 150)
    mock_client = _make_mock_haiku_batch()

    compressor = TickCompressor(batch_size=100, epoch_size=100)
    compressor.maybe_compress(tmp_path, mock_client)

    batch_files = list((tmp_path / "tick_summaries").glob("batch_*.json"))
    assert len(batch_files) == 1
    remaining_ticks = list(tick_dir.glob("tick_*.json"))
    assert len(remaining_ticks) == 50


def test_maybe_compress_creates_epoch_at_batch_threshold(tmp_path: Path):
    """100 batch files → 1 epoch_0.json created, all batches deleted, Haiku called once."""
    from token_world.engine.compressor import TickCompressor
    from token_world.engine.models import EpochSummary

    summary_dir = tmp_path / "tick_summaries"
    _write_batch_files(summary_dir, 100)
    mock_client = _make_mock_haiku_epoch()

    compressor = TickCompressor(batch_size=100, epoch_size=100)
    compressor.maybe_compress(tmp_path, mock_client)

    # One epoch file created
    epoch_files = list(summary_dir.glob("epoch_*.json"))
    assert len(epoch_files) == 1
    assert epoch_files[0].name == "epoch_0.json"

    # Epoch has schema v2 content
    epoch = EpochSummary.model_validate_json(epoch_files[0].read_text())
    assert epoch.schema_version == 2
    assert epoch.kind == "epoch"
    assert epoch.batch_count == 100
    assert "long simulation" in epoch.synopsis

    # All batch files deleted
    assert len(list(summary_dir.glob("batch_*.json"))) == 0

    # Haiku called exactly once (epoch compression)
    assert mock_client.messages.create.call_count == 1


def test_batch_id_allocation_monotonic_no_collision(tmp_path: Path):
    """Pre-existing batch_0.json + batch_1.json → new batch is batch_2.json."""
    from token_world.engine.compressor import TickCompressor

    summary_dir = tmp_path / "tick_summaries"
    # Create existing batches
    _write_batch_files(summary_dir, 2, start_id=0)
    # Create 100 new tick files
    tick_dir = summary_dir / "ticks"
    _write_tick_files(tick_dir, 100)
    mock_client = _make_mock_haiku_batch()

    compressor = TickCompressor(batch_size=100, epoch_size=1000)  # epoch_size high to avoid epoch
    compressor.maybe_compress(tmp_path, mock_client)

    batch_files = sorted(summary_dir.glob("batch_*.json"))
    batch_names = [f.name for f in batch_files]
    assert "batch_2.json" in batch_names
    assert "batch_0.json" in batch_names  # unchanged
    assert "batch_1.json" in batch_names  # unchanged


def test_disabled_compression_when_batch_size_zero_or_negative(tmp_path: Path):
    """batch_size=0 → compressor is a no-op even with 200 tick files."""
    from token_world.engine.compressor import TickCompressor

    tick_dir = tmp_path / "tick_summaries" / "ticks"
    _write_tick_files(tick_dir, 200)
    mock_client = MagicMock()

    compressor = TickCompressor(batch_size=0, epoch_size=100)
    compressor.maybe_compress(tmp_path, mock_client)

    assert mock_client.messages.create.call_count == 0
    assert len(list(tick_dir.glob("tick_*.json"))) == 200


def test_engine_calls_maybe_compress_after_each_summary_write(tmp_path: Path):
    """SimulationEngine calls compressor.maybe_compress once per tick (3 ticks → 3 calls)."""
    from unittest.mock import MagicMock

    from tests.test_engine.conftest import MockAnthropicClient
    from token_world.engine import SimulationEngine
    from token_world.graph import KnowledgeGraph

    # Minimal universe setup
    (tmp_path / "mechanics").mkdir()
    (tmp_path / "diagnostics").mkdir()
    (tmp_path / "tick_summaries").mkdir()
    (tmp_path / "universe.yaml").write_text(
        "universe_seed: 42\nengine:\n  max_chain_depth: 10\n  classifier_min_confidence: 0.6\n",
        encoding="utf-8",
    )
    (tmp_path / "conservation.yaml").write_text("conserved_properties: []\n", encoding="utf-8")

    kg = KnowledgeGraph(db_path=tmp_path / "test.db")
    kg.add_node("alice", node_type="agent")

    # Need 3 ticks — each needs classifier (Haiku) response; refuse path only needs classifier
    refuse_responses = [
        '{"kind":"no_viable_action","reason":"test"}',
        '{"kind":"no_viable_action","reason":"test"}',
        '{"kind":"no_viable_action","reason":"test"}',
    ]
    mock_anthropic = MockAnthropicClient(refuse_responses)

    engine = SimulationEngine(
        tmp_path,
        graph=kg,
        anthropic_client=mock_anthropic,
    )

    # Patch the compressor with a mock
    mock_compressor = MagicMock()
    engine._compressor = mock_compressor

    engine.run_tick("do something", "alice")
    engine.run_tick("do something else", "alice")
    engine.run_tick("do yet another thing", "alice")

    assert mock_compressor.maybe_compress.call_count == 3
    # Each call should be with (universe_path, anthropic_client)
    for call in mock_compressor.maybe_compress.call_args_list:
        args = call.args
        assert args[0] == tmp_path.resolve()


def test_haiku_prompt_hash_is_sha256_of_template(tmp_path: Path):
    """BatchSummary.haiku_prompt_hash equals SHA-256 of TickCompressor._BATCH_PROMPT_TEMPLATE."""
    from token_world.engine.compressor import TickCompressor

    tick_dir = tmp_path / "tick_summaries" / "ticks"
    _write_tick_files(tick_dir, 100)
    mock_client = _make_mock_haiku_batch()

    compressor = TickCompressor(batch_size=100, epoch_size=100)
    compressor.maybe_compress(tmp_path, mock_client)

    batch_file = tmp_path / "tick_summaries" / "batch_0.json"
    batch_data = json.loads(batch_file.read_text())
    stored_hash = batch_data["haiku_prompt_hash"]

    expected_hash = hashlib.sha256(TickCompressor._BATCH_PROMPT_TEMPLATE.encode()).hexdigest()
    assert stored_hash == expected_hash
