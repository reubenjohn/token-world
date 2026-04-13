"""PlaytestReport: Pydantic model for structured playtest run results (D-23).

Schema (schema_version=1):
    run_id: str
    scenario_file: str | None
    turns: list[TurnRecord]
    aggregate_scores: AggregateScores
    prompts_sha256: dict[str, str]  -- populated by 06-05 hash hook
    duration_ms: int
    schema_version: Literal[1] = 1

Written atomically at end of run via _atomic_write_json from Phase 4 diagnostics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from token_world.mechanic.diagnostics import _atomic_write_json
from token_world.playtest.scorer import TurnScore


class TurnRecord(BaseModel):
    """Per-turn record in a playtest run.

    Attributes:
        turn_number: Zero-based turn index.
        action_text: The action text sent to the engine.
        observation_text: Engine observation (None on yield path).
        tick_id: Engine tick id for this turn.
        kind: "ok" | "yielded" | "refused"
        score: TurnScore.model_dump() dict for this turn.
    """

    turn_number: int
    action_text: str
    observation_text: str | None
    tick_id: str
    kind: str
    score: dict[str, Any]


class AggregateScores(BaseModel):
    """Per-run averaged scores across all turns.

    All metrics are averages over all TurnScore instances in the run.
    If the turn list is empty, all metrics default to 0.0.
    """

    mechanic_match_rate: float
    observation_groundedness: float
    mutation_count: float
    refusal_rate: float
    action_novelty: float
    composite: float

    @classmethod
    def from_turns(cls, turn_scores: list[TurnScore]) -> AggregateScores:
        """Compute average of each metric across all turn scores.

        Args:
            turn_scores: List of TurnScore instances from the run.

        Returns:
            AggregateScores with averaged metrics. All zeros if list is empty.
        """
        if not turn_scores:
            return cls(
                mechanic_match_rate=0.0,
                observation_groundedness=0.0,
                mutation_count=0.0,
                refusal_rate=0.0,
                action_novelty=0.0,
                composite=0.0,
            )
        n = len(turn_scores)
        return cls(
            mechanic_match_rate=sum(s.mechanic_match_rate for s in turn_scores) / n,
            observation_groundedness=sum(s.observation_groundedness for s in turn_scores) / n,
            mutation_count=sum(s.mutation_count for s in turn_scores) / n,
            refusal_rate=sum(s.refusal_rate for s in turn_scores) / n,
            action_novelty=sum(s.action_novelty for s in turn_scores) / n,
            composite=sum(s.composite for s in turn_scores) / n,
        )


class PlaytestReport(BaseModel):
    """Complete report for one playtest run (D-23 schema).

    Attributes:
        run_id: Unique run identifier (uuid hex or timestamp).
        scenario_file: Path to scenario YAML if one was used, else None.
        turns: List of per-turn records.
        aggregate_scores: Averages of all metrics across turns.
        prompts_sha256: SHA-256 hashes of prompts at run start (populated by 06-05 hook).
        duration_ms: Total run duration in milliseconds.
        schema_version: Always 1 for this version of the schema.
    """

    run_id: str
    scenario_file: str | None
    turns: list[TurnRecord]
    aggregate_scores: AggregateScores
    prompts_sha256: dict[str, str] = Field(default_factory=dict)
    duration_ms: int
    schema_version: Literal[1] = 1

    def write(self, universe_dir: Path) -> Path:
        """Write the report atomically to universe_dir/playtest-reports/<run_id>.json.

        Uses _atomic_write_json from Phase 4 diagnostics for crash-safe writes.
        Creates the playtest-reports directory if it does not exist.

        Args:
            universe_dir: Root of the universe directory.

        Returns:
            Path to the written JSON file.
        """
        out_dir = Path(universe_dir) / "playtest-reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{self.run_id}.json"
        _atomic_write_json(out_path, self.model_dump())
        return out_path
