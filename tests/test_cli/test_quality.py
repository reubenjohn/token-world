"""Tests for ``token_world.quality`` scorer and the ``token-world quality`` CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from token_world.cli import cli

# ---------------------------------------------------------------------------
# Tick fixture builder
# ---------------------------------------------------------------------------


def _tick(
    *,
    refused: bool = False,
    yielded: bool = False,
    mutations_count: int = 0,
    mutations_list: list[Any] | None = None,
    action_text: str = "pick up the apple",
    matched_mechanic_id: str | None = None,
    refusal_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "tick_id": "tick_1",
        "timestamp_iso": "2026-04-14T00:00:00Z",
        "action_text": action_text,
        "classified_action": None,
        "matched_mechanic_id": matched_mechanic_id,
        "yielded": yielded,
        "refused": refused,
        "refusal_reason": refusal_reason,
        "mutations": {"count": mutations_count, "list": mutations_list or []},
        "observation_text": None,
        "duration_ms": 100,
    }


def _write_ticks(ticks_dir: Path, payloads: list[dict[str, Any]]) -> None:
    """Write tick payloads to numbered tick_*.json files."""
    ticks_dir.mkdir(parents=True, exist_ok=True)
    for i, payload in enumerate(payloads, start=1):
        p = dict(payload)
        p["tick_id"] = str(i)
        (ticks_dir / f"tick_{i}.json").write_text(json.dumps(p), encoding="utf-8")


# ---------------------------------------------------------------------------
# score() unit tests
# ---------------------------------------------------------------------------


def test_score_empty_universe(tmp_path: Path) -> None:
    """Missing ticks dir should return INSUFFICIENT_DATA verdict, never crash."""
    from token_world.quality import score

    universe_dir = tmp_path / "empty-universe"
    universe_dir.mkdir()

    report = score(universe_dir, slug="empty", last=50)

    assert report.verdict == "INSUFFICIENT_DATA"
    assert report.tick_count == 0


def test_groundedness_all_grounded(tmp_path: Path) -> None:
    """10 ticks with mutations.count=1, not refused -> groundedness=1.0, OK."""
    from token_world.quality import score

    universe_dir = tmp_path / "universe"
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    payloads = [_tick(mutations_count=1) for _ in range(10)]
    _write_ticks(ticks_dir, payloads)

    report = score(universe_dir, slug="test", last=50)

    groundedness = next(d for d in report.dimensions if d.name == "Groundedness")
    assert abs(groundedness.score - 1.0) < 1e-9
    assert groundedness.status == "OK"


def test_groundedness_ungrounded(tmp_path: Path) -> None:
    """10 executed ticks with mutations.count=0 -> groundedness=0.0, FAIL."""
    from token_world.quality import score

    universe_dir = tmp_path / "universe"
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    # Not refused, not yielded, no mutations = ungrounded
    payloads = [_tick(mutations_count=0) for _ in range(10)]
    _write_ticks(ticks_dir, payloads)

    report = score(universe_dir, slug="test", last=50)

    groundedness = next(d for d in report.dimensions if d.name == "Groundedness")
    assert abs(groundedness.score - 0.0) < 1e-9
    assert groundedness.status == "FAIL"


def test_character_stability_marker(tmp_path: Path) -> None:
    """1 tick with 'framework' in action_text out of 10 -> breaks=1."""
    from token_world.quality import score

    universe_dir = tmp_path / "universe"
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    payloads = [_tick(mutations_count=1) for _ in range(9)]
    payloads.append(_tick(action_text="I see the framework here", mutations_count=1))
    _write_ticks(ticks_dir, payloads)

    report = score(universe_dir, slug="test", last=50)

    stability = next(d for d in report.dimensions if d.name == "Character stability")
    assert "1 break" in stability.detail


def test_action_coherence_all_refused(tmp_path: Path) -> None:
    """All 10 ticks refused -> action coherence FAIL."""
    from token_world.quality import score

    universe_dir = tmp_path / "universe"
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    payloads = [_tick(refused=True) for _ in range(10)]
    _write_ticks(ticks_dir, payloads)

    report = score(universe_dir, slug="test", last=50)

    coherence = next(d for d in report.dimensions if d.name == "Action coherence")
    assert coherence.status == "FAIL"


def test_refusal_cluster_five_consecutive(tmp_path: Path) -> None:
    """5 consecutive refused ticks -> refusal cluster FAIL."""
    from token_world.quality import score

    universe_dir = tmp_path / "universe"
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    # 5 good ticks then 5 consecutive refuses
    payloads = [_tick(mutations_count=1) for _ in range(5)]
    payloads += [_tick(refused=True) for _ in range(5)]
    _write_ticks(ticks_dir, payloads)

    report = score(universe_dir, slug="test", last=50)

    cluster = next(d for d in report.dimensions if d.name == "Refusal cluster")
    assert cluster.status == "FAIL"
    assert cluster.score >= 5.0


def test_vocabulary_growth_novel_mechanics(tmp_path: Path) -> None:
    """10 ticks each with unique matched_mechanic_id -> novel=10."""
    from token_world.quality import score

    universe_dir = tmp_path / "universe"
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    payloads = [_tick(matched_mechanic_id=f"mechanic_{i}", mutations_count=1) for i in range(10)]
    _write_ticks(ticks_dir, payloads)

    report = score(universe_dir, slug="test", last=50)

    vocab = next(d for d in report.dimensions if d.name == "Vocabulary growth")
    assert "10 novel" in vocab.detail


def test_conservation_drift(tmp_path: Path) -> None:
    """2 refused ticks with conservation reason out of 10 -> rollback_rate=0.2, FAIL."""
    from token_world.quality import score

    universe_dir = tmp_path / "universe"
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    payloads = [_tick(mutations_count=1) for _ in range(8)]
    payloads += [
        _tick(refused=True, refusal_reason="conservation_violation: item count mismatch")
        for _ in range(2)
    ]
    _write_ticks(ticks_dir, payloads)

    report = score(universe_dir, slug="test", last=50)

    conservation = next(d for d in report.dimensions if d.name == "Conservation drift")
    assert conservation.status == "FAIL"
    assert "2/10" in conservation.detail


def test_novel_subtype_rate(tmp_path: Path) -> None:
    """3 ticks with mutations containing prop='subtype' and unique new values -> new_subtypes=3."""
    from token_world.quality import score

    universe_dir = tmp_path / "universe"
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    payloads = [_tick(mutations_count=1) for _ in range(7)]
    payloads += [
        _tick(
            mutations_count=1,
            mutations_list=[["chest_1", "subtype", None, "container"]],
        ),
        _tick(
            mutations_count=1,
            mutations_list=[["sword_1", "subtype", None, "weapon"]],
        ),
        _tick(
            mutations_count=1,
            mutations_list=[["scroll_1", "subtype", None, "scroll"]],
        ),
    ]
    _write_ticks(ticks_dir, payloads)

    report = score(universe_dir, slug="test", last=50)

    subtype = next(d for d in report.dimensions if d.name == "Novel subtype rate")
    assert "3 new subtype" in subtype.detail


def test_graph_fanout_no_db(tmp_path: Path) -> None:
    """Missing universe.db -> graph fan-out status OK with 'insufficient history'."""
    from token_world.quality import score

    universe_dir = tmp_path / "universe"
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    payloads = [_tick(mutations_count=1) for _ in range(10)]
    _write_ticks(ticks_dir, payloads)
    # No universe.db created

    report = score(universe_dir, slug="test", last=50)

    fanout = next(d for d in report.dimensions if d.name == "Graph fan-out")
    assert fanout.status == "OK"
    assert "insufficient history" in fanout.detail


# ---------------------------------------------------------------------------
# render tests
# ---------------------------------------------------------------------------


def test_render_table_contains_verdict(tmp_path: Path) -> None:
    """render_table() output contains 'Verdict:'."""
    from token_world.quality import score
    from token_world.quality.report import render_table

    universe_dir = tmp_path / "universe"
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    payloads = [_tick(mutations_count=1) for _ in range(10)]
    _write_ticks(ticks_dir, payloads)

    report = score(universe_dir, slug="test", last=50)
    output = render_table(report)

    assert "Verdict:" in output
    assert any(marker in output for marker in ["[OK]", "[WARN]", "[FAIL]", "INSUFFICIENT_DATA"])


def test_render_json_valid(tmp_path: Path) -> None:
    """render_json() output is valid JSON with required top-level keys."""
    from token_world.quality import score
    from token_world.quality.report import render_json

    universe_dir = tmp_path / "universe"
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    payloads = [_tick(mutations_count=1) for _ in range(10)]
    _write_ticks(ticks_dir, payloads)

    report = score(universe_dir, slug="test", last=50)
    output = render_json(report)

    data = json.loads(output)
    assert "slug" in data
    assert "window" in data
    assert "tick_count" in data
    assert "verdict" in data
    assert "dimensions" in data
    assert isinstance(data["dimensions"], list)


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_quality_help() -> None:
    """token-world quality --help shows slug, --last, --format options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["quality", "--help"])
    assert result.exit_code == 0
    assert "slug" in result.output.lower() or "SLUG" in result.output
    assert "--last" in result.output
    assert "--format" in result.output
