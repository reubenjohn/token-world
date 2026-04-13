"""Pydantic models for the simulation-engine pipeline.

Source of truth for every structured object crossing an engine-stage boundary.
Each tagged union uses a :attr:`kind` literal discriminator so downstream
switch-style code is type-safe under mypy and Pydantic v2 validation.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ClassifiedAction(BaseModel):
    """D-05: structured form of a resident-agent action."""

    model_config = ConfigDict(extra="ignore")

    verb: str
    actor: str
    target: str | None = None
    indirect_object: str | None = None  # GAP-ENG02 closure
    params: dict[str, Any] = Field(default_factory=dict)


class VerdictOk(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["ok"] = "ok"
    classified: ClassifiedAction
    confidence: float = Field(ge=0.0, le=1.0)


class VerdictNoViableAction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["no_viable_action"] = "no_viable_action"
    reason: str


class VerdictNoSuchTarget(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["no_such_target"] = "no_such_target"
    target_text: str


class VerdictLowConfidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["low_confidence"] = "low_confidence"
    reason: str
    best_guess: ClassifiedAction | None = None
    confidence: float = Field(ge=0.0, le=1.0)


ClassifierVerdict = Annotated[
    VerdictOk | VerdictNoViableAction | VerdictNoSuchTarget | VerdictLowConfidence,
    Field(discriminator="kind"),
]


class MatchedResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["matched"] = "matched"
    mechanic_id: str
    score: int
    reasoning: str


class NoMatchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["no_match"] = "no_match"
    classified: ClassifiedAction
    candidates: list[str] = Field(default_factory=list)


MatchResult = Annotated[
    MatchedResult | NoMatchResult,
    Field(discriminator="kind"),
]


class ExecuteDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["execute"] = "execute"
    mechanic_id: str


class YieldDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["yield"] = "yield"
    classified: ClassifiedAction
    candidates: list[str] = Field(default_factory=list)


class RefuseDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["refuse"] = "refuse"
    # e.g. "no_viable_action", "no_such_target", "low_confidence",
    # "conservation_violation", "mechanic_check_failed"
    reason_code: str
    details: dict[str, Any] = Field(default_factory=dict)


Decision = Annotated[
    ExecuteDecision | YieldDecision | RefuseDecision,
    Field(discriminator="kind"),
]


class TickSummary(BaseModel):
    """D-20: schema v1 of universe/tick_summaries/tick_<id>.json."""

    model_config = ConfigDict(extra="ignore")

    schema_version: Literal[1] = 1
    tick_id: str
    timestamp_iso: str
    action_text: str
    classified_action: dict[str, Any] | None
    matched_mechanic_id: str | None
    yielded: bool
    refused: bool
    refusal_reason: str | None
    mutations: dict[str, Any]
    observation_text: str | None
    # D-17 (Phase 7): additive optional field; schema_version stays 1 (backward-compat).
    # Populated only for LRA continuation ticks; None for all normal ticks.
    long_running_action: dict[str, Any] | None = None
    duration_ms: int
    llm_tokens_by_stage: dict[str, dict[str, int]]
    llm_cost_usd_by_stage: dict[str, float]


class BatchSummary(BaseModel):
    """D-18: schema v2 batch summary — compresses N tick files into one.

    Written to universe/tick_summaries/batch_<N>.json after every batch
    compression pass.  The ``kind`` literal and ``schema_version: 2`` serve as
    discriminator and forward-compat version stamp respectively.
    ``haiku_prompt_hash`` stores the SHA-256 of the compression prompt so that
    prompt changes can be detected by downstream tooling.
    """

    model_config = ConfigDict(extra="ignore")

    schema_version: Literal[2] = 2
    kind: Literal["batch"] = "batch"
    batch_id: int
    first_tick: str
    last_tick: str
    tick_count: int
    key_events: list[str]
    mechanic_ids_used: list[str]
    total_mutations: int
    agent_id: str
    haiku_prompt_hash: str


class EpochSummary(BaseModel):
    """D-18: schema v2 epoch summary — compresses N batch files into one.

    Written to universe/tick_summaries/epoch_<N>.json after every epoch
    compression pass.
    """

    model_config = ConfigDict(extra="ignore")

    schema_version: Literal[2] = 2
    kind: Literal["epoch"] = "epoch"
    epoch_id: int
    first_batch: int
    last_batch: int
    batch_count: int
    synopsis: str


SummaryV2 = Annotated[
    BatchSummary | EpochSummary,
    Field(discriminator="kind"),
]
