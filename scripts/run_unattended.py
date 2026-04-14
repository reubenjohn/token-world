"""Drive an unattended simulation run with the external-operator protocol.

The runner loop is the usual :class:`PlaytestRunner`, but ``harness_factory``
is wired to :func:`external_operator_factory` so every yield is written to
``<universe>/operator_inbox/<tick_id>.yield.json`` and blocks waiting for a
sibling ``.resolved`` / ``.rejected`` marker from an external orchestrator
(typically a Claude Code session spawning authoring subagents).

Safety rails (all optional, all off unless flagged):

- ``--tick-budget N`` — hard cap; runner never exceeds N turns (default 200).
- ``--yield-budget K`` — stop if the operator has been consulted K times
  (prevents runaway authoring thrash).
- ``--cost-ceiling $`` — refuse to start if the engine's recent per-tick
  cost × remaining ticks would exceed the ceiling.
- ``--timeout-per-yield S`` — per-yield resolution wait (forwarded to
  ``TOKEN_WORLD_OPERATOR_TIMEOUT_S``).
- ``<universe>/.stop`` — kill switch file; any contents halt at next
  yield boundary.

Usage::

    TOKEN_WORLD_BACKEND=claude-cli uv run python scripts/run_unattended.py \\
        --slug willowbrook --ticks 50 --yield-budget 25 --timeout-per-yield 900
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import anthropic
from loguru import logger

from token_world.cli import _load_or_create_agent  # type: ignore[attr-defined]
from token_world.engine.engine import SimulationEngine
from token_world.graph import KnowledgeGraph
from token_world.operator.external import external_operator_factory
from token_world.playtest.runner import PlaytestRunner
from token_world.resident import AgentMemory, SessionManager
from token_world.universe.manager import UniverseManager


def _cost_hint(universe_dir: Path, lookback: int = 20) -> float:
    """Rough per-tick cost estimate from recent tick_summaries (USD).

    Reads the last ``lookback`` tick summary JSON files and averages
    ``llm_cost_usd_by_stage`` totals. Returns ``0.0`` if no files exist
    (e.g. first run) — callers should treat missing history as unknown,
    not zero.
    """
    tick_dir = universe_dir / "tick_summaries" / "ticks"
    if not tick_dir.exists():
        return 0.0
    files = sorted(tick_dir.glob("tick_*.json"))[-lookback:]
    if not files:
        return 0.0
    total = 0.0
    count = 0
    for f in files:
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        stages = data.get("llm_cost_usd_by_stage") or {}
        total += sum(float(v or 0) for v in stages.values())
        count += 1
    return total / count if count else 0.0


def _check_cost_ceiling(universe_dir: Path, ticks: int, ceiling: float) -> None:
    avg = _cost_hint(universe_dir)
    projected = avg * ticks
    if ceiling > 0 and projected > ceiling:
        raise SystemExit(
            f"Projected cost ${projected:.2f} (avg ${avg:.4f}/tick × {ticks}) "
            f"exceeds ceiling ${ceiling:.2f}. Refusing to start. "
            f"Set TOKEN_WORLD_BACKEND=claude-cli or lower --ticks."
        )
    if avg > 0:
        logger.info("Cost estimate: ~${:.4f}/tick × {} ticks = ~${:.2f}", avg, ticks, projected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--ticks", type=int, default=50)
    parser.add_argument(
        "--tick-budget",
        type=int,
        default=None,
        help="Alias for --ticks when you want a hard cap stated explicitly.",
    )
    parser.add_argument(
        "--yield-budget",
        type=int,
        default=None,
        help="Stop if operator consulted N times. Prevents authoring thrash.",
    )
    parser.add_argument(
        "--cost-ceiling",
        type=float,
        default=0.0,
        help="Refuse to start if projected cost exceeds $X. 0 = unbounded.",
    )
    parser.add_argument(
        "--timeout-per-yield",
        type=float,
        default=1800.0,
        help="Max wait (s) for external resolution per yield. Default 30min.",
    )
    parser.add_argument("--poll-s", type=float, default=2.0)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--agent-id", default=None)
    args = parser.parse_args()

    ticks = args.tick_budget if args.tick_budget is not None else args.ticks

    manager = UniverseManager()
    try:
        universe_dir = manager.load(args.slug)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    _check_cost_ceiling(universe_dir, ticks, args.cost_ceiling)

    # Pass env to the external operator factory.
    os.environ["TOKEN_WORLD_OPERATOR_TIMEOUT_S"] = str(args.timeout_per_yield)
    os.environ["TOKEN_WORLD_OPERATOR_POLL_S"] = str(args.poll_s)

    kg = KnowledgeGraph(db_path=universe_dir / "universe.db")
    kg.load()

    claude_md = universe_dir / "CLAUDE.md"
    world_rules = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""

    client = anthropic.Anthropic()
    db_path = universe_dir / "universe.db"
    memory = AgentMemory(db_path)
    sessions = SessionManager(db_path)

    agent, agent_id, session_id = _load_or_create_agent(
        universe_dir, kg, memory, sessions, client, world_rules, agent_id=args.agent_id
    )

    engine = SimulationEngine(universe_dir, graph=kg, anthropic_client=client)
    runner = PlaytestRunner(
        engine=engine,
        agent=agent,
        memory=memory,
        agent_id=agent_id,
        session_id=session_id,
        harness_factory=external_operator_factory,
    )

    # Monkey-patch runner.run to inject yield-budget tracking. Wrap progress_fn
    # so every printed turn also checks the kill switch and yield count.
    stop_path = universe_dir / ".stop"
    state = {"yields": 0, "halt_reason": None}

    original_progress = runner.progress_fn

    def _tracking_progress(msg: str) -> None:
        original_progress(msg)
        if stop_path.exists():
            state["halt_reason"] = "kill_switch"
            raise SystemExit("halted: kill switch file present")

    runner.progress_fn = _tracking_progress

    # Install a counter in the harness_factory so we can cap yields.
    def _counting_factory(universe_path: Path):
        state["yields"] += 1
        if args.yield_budget and state["yields"] > args.yield_budget:
            state["halt_reason"] = "yield_budget"
            raise SystemExit(
                f"halted: yield_budget {args.yield_budget} exceeded "
                f"(consulted {state['yields']} times)"
            )
        return external_operator_factory(universe_path)

    runner.harness_factory = _counting_factory

    logger.info(
        "Starting unattended run: slug={} ticks={} yield_budget={} timeout={}s",
        args.slug,
        ticks,
        args.yield_budget,
        args.timeout_per_yield,
    )

    start = time.monotonic()
    try:
        report_path = runner.run(
            universe_dir,
            turns=ticks,
            no_operator=False,
            output_path=args.output,
        )
    except SystemExit as e:
        logger.warning("Run halted: {}", e)
        elapsed = time.monotonic() - start
        print(f"halted after {elapsed:.1f}s  reason={state['halt_reason'] or e}")
        return 3

    elapsed = time.monotonic() - start
    logger.info("Run complete in {:.1f}s, {} yields observed", elapsed, state["yields"])
    print(f"report: {report_path}")
    print(f"yields: {state['yields']}")
    print(f"elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
