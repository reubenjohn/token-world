"""Tests for PlaytestReport Pydantic model + atomic write (Task 3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _make_turn_score_dict(composite: float = 0.8) -> dict:
    """Build a minimal TurnScore dict."""
    return {
        "mechanic_match_rate": 1.0,
        "observation_groundedness": 1.0,
        "mutation_count": 1.0,
        "refusal_rate": 1.0,
        "action_novelty": 0.5,
        "composite": composite,
    }


def _make_turn_record_dict(turn_number: int = 0) -> dict:
    """Build a minimal TurnRecord dict."""
    return {
        "turn_number": turn_number,
        "action_text": "look around",
        "observation_text": "You see a room.",
        "tick_id": f"tick_{turn_number + 1}",
        "kind": "ok",
        "score": _make_turn_score_dict(),
    }


# ---------------------------------------------------------------------------
# TurnRecord tests
# ---------------------------------------------------------------------------


def test_turn_record_model_requires_fields() -> None:
    """Test 27: missing required fields raise ValidationError."""
    from pydantic import ValidationError

    from token_world.playtest import TurnRecord

    with pytest.raises(ValidationError):
        TurnRecord()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# AggregateScores tests
# ---------------------------------------------------------------------------


def test_aggregate_scores_average_computed() -> None:
    """Test 28: AggregateScores.from_turns returns average of each metric."""
    from token_world.playtest import AggregateScores, TurnScore

    scores = [
        TurnScore(
            mechanic_match_rate=1.0,
            observation_groundedness=1.0,
            mutation_count=1.0,
            refusal_rate=1.0,
            action_novelty=0.0,
            composite=0.8,
        ),
        TurnScore(
            mechanic_match_rate=0.0,
            observation_groundedness=0.0,
            mutation_count=0.0,
            refusal_rate=0.0,
            action_novelty=1.0,
            composite=0.2,
        ),
    ]
    agg = AggregateScores.from_turns(scores)
    assert agg.mechanic_match_rate == pytest.approx(0.5, abs=0.001)
    assert agg.observation_groundedness == pytest.approx(0.5, abs=0.001)
    assert agg.mutation_count == pytest.approx(0.5, abs=0.001)
    assert agg.refusal_rate == pytest.approx(0.5, abs=0.001)
    assert agg.action_novelty == pytest.approx(0.5, abs=0.001)
    assert agg.composite == pytest.approx(0.5, abs=0.001)


def test_aggregate_scores_empty_list_returns_zeros() -> None:
    """Test 29: empty turn list -> AggregateScores with all metrics 0.0."""
    from token_world.playtest import AggregateScores

    agg = AggregateScores.from_turns([])
    assert agg.mechanic_match_rate == 0.0
    assert agg.composite == 0.0


# ---------------------------------------------------------------------------
# PlaytestReport write tests
# ---------------------------------------------------------------------------


def test_playtest_report_writes_atomically_to_universe_dir(tmp_path: Path) -> None:
    """Test 30: report.write(universe_dir) creates the file with all required fields."""
    from token_world.playtest import AggregateScores, PlaytestReport, TurnRecord, TurnScore

    turn_scores = [
        TurnScore(
            mechanic_match_rate=1.0,
            observation_groundedness=1.0,
            mutation_count=1.0,
            refusal_rate=1.0,
            action_novelty=1.0,
            composite=1.0,
        )
    ]
    records = [TurnRecord(**_make_turn_record_dict(0))]
    agg = AggregateScores.from_turns(turn_scores)

    report = PlaytestReport(
        run_id="test_run_001",
        scenario_file=None,
        turns=records,
        aggregate_scores=agg,
        prompts_sha256={},
        duration_ms=500,
    )
    path = report.write(tmp_path)

    # File must exist
    assert path.exists()
    # Must be under universe_dir/playtest-reports/
    assert path.parent == tmp_path / "playtest-reports"

    # Parse and verify structure
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["run_id"] == "test_run_001"
    assert data["schema_version"] == 1
    assert len(data["turns"]) == 1
    assert "aggregate_scores" in data
    assert data["duration_ms"] == 500


def test_playtest_report_write_returns_path(tmp_path: Path) -> None:
    """Test 31: write() returns the Path to the written file."""
    from token_world.playtest import AggregateScores, PlaytestReport, TurnRecord, TurnScore

    turn_scores = [
        TurnScore(
            mechanic_match_rate=1.0,
            observation_groundedness=1.0,
            mutation_count=1.0,
            refusal_rate=1.0,
            action_novelty=1.0,
            composite=1.0,
        )
    ]
    records = [TurnRecord(**_make_turn_record_dict(0))]
    agg = AggregateScores.from_turns(turn_scores)

    report = PlaytestReport(
        run_id="run_return_path",
        scenario_file="test.yaml",
        turns=records,
        aggregate_scores=agg,
        prompts_sha256={},
        duration_ms=100,
    )
    path = report.write(tmp_path)

    assert isinstance(path, Path)
    assert path.name == "run_return_path.json"
