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
- ``--refuse-halt-threshold K`` — halt after K consecutive refused ticks
  (default 6). Catches character-break / classifier-failure decompensation
  early so overnight runs don't burn a budget on a stuck agent.
- ``<universe>/.stop`` — kill switch file; any contents halt at next
  yield boundary.

Usage::

    TOKEN_WORLD_BACKEND=claude-cli uv run python scripts/run_unattended.py \\
        --slug willowbrook --ticks 50 --yield-budget 25 --timeout-per-yield 900
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import signal
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


def wrap_run_tick_with_refuse_halt(
    original_run_tick,
    state: dict,
    refuse_threshold: int,
):
    """Return a wrapper around ``engine.run_tick`` that halts on K consecutive refuses.

    The wrapper is transparent for ``kind="ok"`` and ``kind="yielded"``
    results — it resets the consecutive-refuse counter to zero and passes
    the result through. On ``kind="refused"`` it increments the counter and
    raises :class:`SystemExit` once the counter reaches ``refuse_threshold``
    (which acts as the halt signal for the runner loop).

    This catches the character-break / classifier-failure decompensation
    pattern documented in MORNING-HANDOFF.md §C (session 4 round 2, Mira
    narrating the simulation framework itself after several refuses piled
    up). Setting ``refuse_threshold=0`` disables the guard.

    Args:
        original_run_tick: Bound method ``engine.run_tick`` to wrap.
        state: Shared mutable dict with ``consecutive_refuses`` (int) and
            ``halt_reason`` (str | None) keys. Mutated in place.
        refuse_threshold: Number of consecutive refuses that triggers the
            halt. ``0`` disables the guard.

    Returns:
        A callable with the same signature as ``engine.run_tick``.
    """

    def _wrapped(*args, **kwargs):  # type: ignore[no-untyped-def]
        result = original_run_tick(*args, **kwargs)
        kind = getattr(result, "kind", None)
        if kind == "refused":
            state["consecutive_refuses"] = int(state.get("consecutive_refuses", 0)) + 1
            if refuse_threshold and int(state["consecutive_refuses"]) >= refuse_threshold:
                reason = (
                    f"halt: {refuse_threshold} consecutive refuses — "
                    "probable character-break or classifier failure"
                )
                state["halt_reason"] = reason
                raise SystemExit(reason)
        else:
            state["consecutive_refuses"] = 0
        return result

    return _wrapped


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
    parser.add_argument(
        "--refuse-halt-threshold",
        type=int,
        default=6,
        help=(
            "Halt cleanly after K consecutive refused ticks (probable "
            "character-break or classifier failure). Default 6; 0 disables."
        ),
    )
    parser.add_argument("--poll-s", type=float, default=2.0)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--agent-id", default=None)
    parser.add_argument(
        "--scenario",
        type=Path,
        default=None,
        help="YAML scenario file (scripted/inject turns) — accelerates emergence.",
    )
    args = parser.parse_args()

    ticks = args.tick_budget if args.tick_budget is not None else args.ticks

    manager = UniverseManager()
    try:
        universe_dir = manager.load(args.slug)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    # OPS-01: check for .stop kill-switch at startup (T-17-02-04).
    stop_path = universe_dir / ".stop"
    if stop_path.exists():
        print(
            f"WARNING: .stop file present at {stop_path}; delete it before running.",
            file=sys.stderr,
        )
        return 2

    _check_cost_ceiling(universe_dir, ticks, args.cost_ceiling)

    # PID file management (SC-3).
    pid_path = universe_dir / ".run-pid"

    def _remove_pid_file() -> None:
        with contextlib.suppress(OSError):
            pid_path.unlink(missing_ok=True)

    def _sigint_handler(signum, frame) -> None:  # noqa: ANN001
        _remove_pid_file()
        sys.exit(130)  # conventional SIGINT exit code

    signal.signal(signal.SIGINT, _sigint_handler)

    pid_path.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        ),
        encoding="utf-8",
    )

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
    # Note: stop_path already defined above for the startup check.
    state: dict = {
        "yields": 0,
        "halt_reason": None,
        "consecutive_refuses": 0,
        "refuse_threshold": args.refuse_halt_threshold,
    }

    original_progress = runner.progress_fn

    def _tracking_progress(msg: str) -> None:
        original_progress(msg)
        if stop_path.exists():
            state["halt_reason"] = "kill_switch"
            raise SystemExit("halted: kill switch file present")

    runner.progress_fn = _tracking_progress

    # Install a counter in the harness_factory so we can cap yields.
    def _counting_factory(universe_path: Path):
        state["yields"] = int(state["yields"]) + 1
        if args.yield_budget and int(state["yields"]) > args.yield_budget:
            state["halt_reason"] = "yield_budget"
            raise SystemExit(
                f"halted: yield_budget {args.yield_budget} exceeded "
                f"(consulted {state['yields']} times)"
            )
        return external_operator_factory(universe_path)

    runner.harness_factory = _counting_factory

    # Wrap engine.run_tick so we can detect consecutive refuses and halt
    # cleanly before the resident agent decompensates out of character under
    # piled-up rejection (character-break / classifier-failure guard).
    engine.run_tick = wrap_run_tick_with_refuse_halt(  # type: ignore[method-assign]
        engine.run_tick,
        state,
        args.refuse_halt_threshold,
    )

    logger.info(
        "Starting unattended run: slug={} ticks={} yield_budget={} "
        "refuse_halt_threshold={} timeout={}s",
        args.slug,
        ticks,
        args.yield_budget,
        args.refuse_halt_threshold,
        args.timeout_per_yield,
    )

    scenario_obj = None
    if args.scenario is not None:
        from token_world.playtest import Scenario

        scenario_obj = Scenario.load(args.scenario)
        logger.info(
            "Loaded scenario {} ({} scripted turns)",
            args.scenario.name,
            len(scenario_obj.turns),
        )

    start = time.monotonic()
    try:
        try:
            report_path = runner.run(
                universe_dir,
                turns=ticks,
                no_operator=False,
                scenario=scenario_obj,
                output_path=args.output,
            )
        except SystemExit as e:
            logger.warning("Run halted: {}", e)
            elapsed = time.monotonic() - start
            reason = state["halt_reason"] or str(e)
            # First line: big, prominent, so morning-operator sees it at top of log.
            print(f"STATUS: HALTED — {reason}")
            print(f"halted after {elapsed:.1f}s  reason={reason}")
            print(f"yields: {state['yields']}")
            print(f"consecutive_refuses_at_halt: {state['consecutive_refuses']}")
            # Persist halt metadata alongside universe dir so operators can grep it.
            halt_log = universe_dir / "unattended_halt.json"
            with contextlib.suppress(OSError):
                halt_log.write_text(
                    json.dumps(
                        {
                            "reason": reason,
                            "elapsed_s": elapsed,
                            "yields": state["yields"],
                            "consecutive_refuses_at_halt": state["consecutive_refuses"],
                            "refuse_halt_threshold": args.refuse_halt_threshold,
                        },
                        indent=2,
                    )
                )
            return 3
    finally:
        _remove_pid_file()

    elapsed = time.monotonic() - start
    logger.info("Run complete in {:.1f}s, {} yields observed", elapsed, state["yields"])
    print(f"report: {report_path}")
    print(f"yields: {state['yields']}")
    print(f"elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
