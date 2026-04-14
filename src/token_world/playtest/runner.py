"""PlaytestRunner: N-turn simulation loop with scoring and report generation (D-09, D-10).

Loop structure (D-24 synchronous tight loop):
    for each turn:
        determine action (scenario/inject/agent)
        run engine tick
        if yielded and not no_operator: asyncio.run(harness.handle_yield)
        store turn in memory
        score turn
        append to records
    write report once at end (D-23, Pitfall 6)

Hook points for downstream plans (Wave 4+):
    hash_check_fn: optional callable(engine, agent) -> dict[str, str]
        Plugged by 06-05 (prompt hash registry + regression trigger).
    harness_factory: callable(universe_dir) -> OperatorHarness
        Replaceable in tests or future plans.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from token_world.playtest.report import AggregateScores, PlaytestReport, TurnRecord
from token_world.playtest.scenarios import InjectionSampler, Scenario
from token_world.playtest.scorer import TurnScore, TurnScorer

if TYPE_CHECKING:
    from token_world.operator.harness import OperatorHarness


def _default_harness_factory(universe_dir: Path) -> OperatorHarness:
    """Default factory: create OperatorHarness for the given universe directory."""
    from token_world.operator.harness import OperatorHarness

    return OperatorHarness(universe_dir)


@dataclass
class PlaytestRunner:
    """Orchestrates N-turn playtest runs (D-09, D-10).

    Attributes:
        engine: SimulationEngine instance for run_tick().
        agent: ResidentAgent instance for run_turn().
        memory: AgentMemory for persisting turns.
        agent_id: ID of the resident agent in the graph.
        session_id: Current session ID for memory storage.
        harness_factory: Callable(universe_dir) -> OperatorHarness.
            Replaceable for testing. Default uses OperatorHarness from harness.py.
        scorer: TurnScorer instance (default: new TurnScorer()).
        hash_check_fn: Optional callable(engine, agent) -> dict[str, str].
            Called at run start to capture prompt hashes (plugged by 06-05).
        progress_fn: Callable for per-turn progress output (D-28 plain stdout).
    """

    engine: object
    agent: object
    memory: object
    agent_id: str
    session_id: str
    harness_factory: Callable = field(default=_default_harness_factory)
    scorer: TurnScorer = field(default_factory=TurnScorer)
    hash_check_fn: Callable | None = None
    progress_fn: Callable[[str], None] = field(default=print)

    def run(
        self,
        universe_dir: Path,
        *,
        turns: int = 20,
        scenario: Scenario | None = None,
        seed: int | None = None,
        no_operator: bool = False,
        judge: bool = False,
        output_path: Path | None = None,
    ) -> Path:
        """Run N simulation turns and write a structured quality report.

        Args:
            universe_dir: Root directory of the universe.
            turns: Number of turns to run (default 20).
            scenario: Optional Scenario with scripted/inject turns.
            seed: RNG seed for injection sampler (overrides scenario.seed).
            no_operator: If True, skip OperatorHarness on yield.
            judge: If True, run optional Sonnet judge (stub in this plan; D-13).
            output_path: Override report output path.

        Returns:
            Path to the written report JSON file.
        """
        start_ns = time.perf_counter_ns()
        run_id = uuid.uuid4().hex

        # Determine sampler seed
        sampler_seed = seed if seed is not None else (scenario.seed if scenario else 0)
        sampler = InjectionSampler(sampler_seed)

        # Initialize tracking state
        action_history: list[str] = []
        non_refusal_count = 0
        turn_records: list[TurnRecord] = []
        turn_scores: list[TurnScore] = []

        # Hook: prompt hash check (plugged by 06-05)
        prompts_sha256: dict[str, str] = {}
        if self.hash_check_fn is not None:
            result = self.hash_check_fn(self.engine, self.agent)
            if result is not None:
                prompts_sha256 = result

        # Main simulation loop (D-24 synchronous)
        for turn_num in range(turns):
            # Phase 7 (D-07): when an LRA is active, skip agent.run_turn() to save
            # LLM tokens and let the engine emit a synthetic continuation tick.
            # Marker text keeps memory's alternating user/assistant rolling window
            # consistent (Pitfall 2 mitigation).
            _lra_check = getattr(self.engine, "has_active_long_action", None)
            if _lra_check is not None and _lra_check(self.agent_id) is True:  # type: ignore[misc]
                action: str | None = None
                action_for_memory = "[long_running_continuation]"
            else:
                action = self._determine_action(
                    turn_num=turn_num,
                    scenario=scenario,
                    sampler=sampler,
                    action_history=action_history,
                )
                action_for_memory = action

            # Run the engine tick (action may be None for LRA continuation)
            result = self.engine.run_tick(action, actor=self.agent_id)  # type: ignore[attr-defined]

            # Handle yield: invoke OperatorHarness then re-run (only on non-None action path)
            if result.kind == "yielded" and not no_operator:
                harness = self.harness_factory(universe_dir)
                asyncio.run(harness.handle_yield(result.yield_signal))
                result = self.engine.run_tick(action, actor=self.agent_id)  # type: ignore[attr-defined]

            # Persist turn to memory using action_for_memory (marker on LRA turns)
            self.memory.store_turn(  # type: ignore[attr-defined]
                self.agent_id,
                self.session_id,
                turn_num,
                action_for_memory,
                result.observation or "",
                result.tick_id,
            )
            # Regenerate rolling summary at 10-turn boundaries (D-07, D-27)
            self.memory.maybe_compact_summary(  # type: ignore[attr-defined]
                self.session_id,
                self.agent._client,  # type: ignore[attr-defined]
            )

            # Score the turn
            score = self.scorer.score(
                result=result,
                action_text=action_for_memory,
                action_history=action_history[-3:],
                previous_non_refusal_count=non_refusal_count,
                total_turns_so_far=turn_num,
            )

            # Track state for next turn
            if result.kind != "refused":
                non_refusal_count += 1
            action_history.append(action_for_memory)

            # Build turn record (uses action_for_memory for auditability)
            record = TurnRecord(
                turn_number=turn_num,
                action_text=action_for_memory,
                observation_text=result.observation,
                tick_id=result.tick_id,
                kind=result.kind,
                score=score.model_dump(),
            )
            turn_records.append(record)
            turn_scores.append(score)

            # Progress output (D-28 plain stdout)
            self.progress_fn(
                f"Turn {turn_num}: action={action_for_memory[:50]!r} score={score.composite:.2f}"
            )

        # Build report
        duration_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)
        aggregate = AggregateScores.from_turns(turn_scores)
        report = PlaytestReport(
            run_id=run_id,
            scenario_file=str(scenario) if scenario is not None else None,
            turns=turn_records,
            aggregate_scores=aggregate,
            prompts_sha256=prompts_sha256,
            duration_ms=duration_ms,
        )

        # Atomic write at end only (Pitfall 6)
        if output_path is None:
            return report.write(universe_dir)
        else:
            # Honour the exact path the caller specified
            output_path.parent.mkdir(parents=True, exist_ok=True)
            from token_world.mechanic.diagnostics import _atomic_write_json

            _atomic_write_json(output_path, report.model_dump())
            return output_path

    def _determine_action(
        self,
        *,
        turn_num: int,
        scenario: Scenario | None,
        sampler: InjectionSampler,
        action_history: list[str],
    ) -> str:
        """Determine the action text for a given turn.

        Priority:
            1. Scripted action from scenario
            2. Inject: sampler generates text
            3. Agent: call agent.run_turn()
        """
        if scenario is not None:
            kind, payload = scenario.next_turn(turn_num)
            if kind == "action" and payload is not None:
                return payload
            elif kind == "inject" and payload is not None:
                return sampler.sample(
                    payload,
                    previous_action=action_history[-1] if action_history else "",
                    turn_number=turn_num,
                )
            # kind == "agent" or action with None payload -> fall through to agent

        # Agent decides
        result: str = self.agent.run_turn()  # type: ignore[attr-defined]
        return result
