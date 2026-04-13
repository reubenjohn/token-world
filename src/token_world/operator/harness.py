"""Operator harness — the Agent SDK driver for the yield→author→resume loop (D-01).

:class:`OperatorHarness` owns one tick:

1. Take a :class:`YieldSignal` (engine emitted, or stub fabricated).
2. Open the operator diagnostics namespace (Plan 04.1-02).
3. Spawn the outer Claude session (Opus) with the universe's MCP tools, the
   in-process validation @tool wrapper, and the mechanic-author subagent.
4. Pipe every SDK message into ``authoring_attempts.jsonl``.
5. Parse the outer model's final JSON summary into an :class:`OperatorResult`.
6. Close the diagnostics session with the success/failure outcome.

Threats / design constraints addressed here:

- **Pitfall 1 (subagent invocation):** ``"Agent"`` is in ``allowed_tools`` so the
  outer Claude can spawn the mechanic-author subagent.
- **Pitfall 2 (permission inheritance):** ``permission_mode="bypassPermissions"``
  on the outer; subagent inherits it but its ``tools=[...]`` whitelist + ``cwd``
  scoping contain blast radius.
- **T-04.1-13 (DoS / runaway):** ``max_turns=20`` hard cap + ``max_budget_usd=5.0``
  hard cap (BLOCKER-4 resolution: ``max_budget_usd`` IS a ClaudeAgentOptions
  field on claude-agent-sdk 0.1.58, so the SDK enforces it).
- **D-15 / D-16 (diagnostics):** every message goes through the operator
  diagnostics context manager; the safety-net ``__exit__`` lands a
  ``resume_outcome.json`` even on exception so consumers (replay-tick)
  always see a final artefact.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ResultMessage,
    query,
)
from loguru import logger

from token_world.mechanic.diagnostics import DiagnosticsSink
from token_world.operator.mcp_client import load_universe_mcp_config
from token_world.operator.subagent import build_mechanic_author_agent
from token_world.operator.validation_tool import build_validation_server
from token_world.operator.yield_signal import YieldSignal

__all__ = ["OperatorHarness", "OperatorResult"]


@dataclass(frozen=True, slots=True)
class OperatorResult:
    """Final result of one ``handle_yield`` call.

    Attributes:
        success: Whether the outer model authored a mechanic that validated
            and called ``resume_tick`` successfully.
        tick_id: The yield's tick id (echoed for log/diagnostics correlation).
        mechanic_id: The id of the authored mechanic (subagent's choice), or
            ``None`` on failure.
        attempts: Best-effort count of authoring attempts (parsed from the
            outer model's JSON summary; ``0`` if unparseable).
        final_message: The outer model's terminating message (raw string).
        cost_usd: Total LLM cost across the session, or ``None`` if the SDK
            didn't report it.
        turns: Outer-session turn count from ``ResultMessage.num_turns``.
        error: Brief error string on failure; ``None`` on success.
    """

    success: bool
    tick_id: str
    mechanic_id: str | None
    attempts: int
    final_message: str
    cost_usd: float | None
    turns: int
    error: str | None = None


class OperatorHarness:
    """Drives the yield→author→validate→resume loop for one tick.

    Construct once per universe; call :meth:`handle_yield` per stalled tick.

    Programmatic use::

        harness = OperatorHarness(universe=Path("universes/my-world"))
        result = await harness.handle_yield(yield_signal)
        if result.success:
            print(f"Authored {result.mechanic_id}; tick continued.")

    The interactive Claude Code path (Plan 04.1-05) does NOT use this class —
    Claude Code manages its own permissions and tool surface; this harness is
    the programmatic equivalent that opens an Agent SDK session with the same
    underlying MCP tools and subagent definition.
    """

    universe: Path
    model: str
    max_turns: int
    max_budget_usd: float

    def __init__(
        self,
        universe: Path,
        *,
        model: str = "opus",
        max_turns: int = 20,
        max_budget_usd: float = 5.0,
    ) -> None:
        self.universe = universe
        self.model = model
        self.max_turns = max_turns
        self.max_budget_usd = max_budget_usd

    # ------------------------------------------------------------------
    # Options builder (pure; testable in isolation)
    # ------------------------------------------------------------------

    def _build_options(self, signal: YieldSignal) -> ClaudeAgentOptions:
        """Assemble the outer ``ClaudeAgentOptions`` for one ``handle_yield`` call.

        Pure function of ``self`` and ``signal`` so tests can introspect its
        output without invoking the SDK.
        """
        mcp_servers = load_universe_mcp_config(self.universe)
        mcp_servers["validation"] = build_validation_server(self.universe)
        agent_def = build_mechanic_author_agent(universe=self.universe, yield_signal=signal)
        return ClaudeAgentOptions(
            system_prompt=self._outer_system_prompt(signal),
            model=self.model,
            max_turns=self.max_turns,
            # BLOCKER-4 resolved: max_budget_usd IS a ClaudeAgentOptions field
            # on claude-agent-sdk 0.1.58 (probed via scripts/probe_agent_sdk.py).
            # Wired as a hard cap; SDK aborts the session if total cost exceeds.
            max_budget_usd=self.max_budget_usd,
            mcp_servers=mcp_servers,
            allowed_tools=[
                "mcp__token-world__resume_tick",
                "mcp__token-world__list_mechanics",
                "mcp__token-world__rollback",
                "mcp__validation__validate_mechanic",
                "Read",
                "Write",
                "Edit",
                "Bash",
                "Glob",
                "Grep",
                "Agent",  # Pitfall 1: required for subagent invocation
            ],
            agents={"mechanic-author": agent_def},
            permission_mode="bypassPermissions",
            cwd=str(self.universe),
        )

    def _outer_system_prompt(self, signal: YieldSignal) -> str:
        """Outer (orchestrator) system prompt — directs delegation, not authoring.

        The outer Claude must NOT author the mechanic itself; it must always
        delegate to the ``mechanic-author`` subagent. This separation keeps
        the subagent's tight tool whitelist (no ``Agent``, no
        ``rollback``/``resume_tick``) meaningful — if the outer authored
        directly, those guards would be bypassed.
        """
        return (
            "You are the Token World operator. The simulation on tick "
            f"{signal.tick_id!r} has halted because no mechanic matches the "
            f"resident agent's classified action. The universe is at "
            f"{self.universe}. "
            "Use the `mechanic-author` subagent to author the needed mechanic; "
            "it has the validation tool and will iterate until the mechanic "
            "passes validation. Once the subagent reports success, call "
            "`mcp__token-world__resume_tick` with the tick_id. "
            "Return a final JSON object on the last line of your reply: "
            '`{"success": bool, "mechanic_id": str|null, "attempts": int}`. '
            "Do NOT author the mechanic yourself — always delegate to the "
            "`mechanic-author` subagent via the Agent tool."
        )

    def _render_outer_prompt(self, signal: YieldSignal) -> str:
        """The first user message — concise, signal-bearing."""
        return (
            f"Tick {signal.tick_id} halted: no mechanic matched.\n\n"
            f"Yield signal:\n```json\n{signal.to_json()}\n```\n\n"
            "Delegate to `mechanic-author`, then call `resume_tick`, then "
            'return JSON: {"success": ..., "mechanic_id": ..., "attempts": ...}.'
        )

    # ------------------------------------------------------------------
    # Main entry-point
    # ------------------------------------------------------------------

    async def handle_yield(self, signal: YieldSignal) -> OperatorResult:
        """Author a mechanic in response to *signal* and resume the tick.

        Args:
            signal: The halting yield (produced by Phase 5's engine in real
                use; by :class:`EngineStub` in tests).

        Returns:
            :class:`OperatorResult` describing success, cost, turns, and the
            authored mechanic id.

        Raises:
            Exception: if the SDK ``query`` raises, the diagnostics safety-net
                still records the failure, then the original exception is
                re-raised so the asyncio caller can react.
        """
        sink = DiagnosticsSink(self.universe)
        with sink.open_operator_session(signal.tick_id) as ctx:
            ctx.write_yield_signal(signal)

            options = self._build_options(signal)
            outer_prompt = self._render_outer_prompt(signal)

            final_text = ""
            cost: float | None = None
            turns = 0

            try:
                async for msg in query(prompt=outer_prompt, options=options):
                    ctx.append_attempt(self._serialise_message(msg))
                    if isinstance(msg, ResultMessage):
                        final_text = getattr(msg, "result", "") or ""
                        cost = getattr(msg, "total_cost_usd", None)
                        turns = getattr(msg, "num_turns", 0) or 0
            except Exception as exc:
                # Land an explicit failure outcome and re-raise. The
                # context-manager's __exit__ would also write a fallback,
                # but we want a precise error string on disk and we want
                # to set tick_continued=False.
                ctx.close(
                    {
                        "success": False,
                        "mechanic_id": None,
                        "cost_usd": cost,
                        "turns": turns,
                        "tick_continued": False,
                        "error": repr(exc),
                    }
                )
                raise

            success, mechanic_id, attempts = self._parse_final(final_text)
            ctx.close(
                {
                    "success": success,
                    "mechanic_id": mechanic_id,
                    "cost_usd": cost,
                    "turns": turns,
                    "tick_continued": success,
                    "error": None if success else "authoring_unsuccessful",
                }
            )
            return OperatorResult(
                success=success,
                tick_id=signal.tick_id,
                mechanic_id=mechanic_id,
                attempts=attempts,
                final_message=final_text,
                cost_usd=cost,
                turns=turns,
                error=None if success else "authoring_unsuccessful",
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialise_message(msg: Any) -> dict[str, Any]:
        """Convert an SDK Message into a JSONL-safe dict.

        Tolerant of unexpected message shapes — the JSONL append path must
        not crash on weird inputs. Records the message type plus a few
        well-known attributes when present.
        """
        out: dict[str, Any] = {"type": type(msg).__name__}
        for attr in (
            "subtype",
            "message_id",
            "model",
            "stop_reason",
            "parent_tool_use_id",
            "tool_use_id",
            "uuid",
            "session_id",
            "is_error",
            "num_turns",
            "total_cost_usd",
        ):
            if hasattr(msg, attr):
                value = getattr(msg, attr)
                if value is None or isinstance(value, str | int | float | bool):
                    out[attr] = value
        # Content is best-effort: serialise to repr if not JSON-safe.
        if hasattr(msg, "content"):
            try:
                json.dumps(msg.content)
                out["content"] = msg.content
            except TypeError:
                out["content_repr"] = repr(msg.content)
        if hasattr(msg, "result"):
            result_val = msg.result
            if isinstance(result_val, str):
                out["result"] = result_val
        return out

    @staticmethod
    def _parse_final(text: str) -> tuple[bool, str | None, int]:
        """Parse the outer model's terminating message.

        Strategy:
            1. Try plain ``json.loads`` (the prompt instructs JSON output).
            2. If that fails, scan for the last ``{...}`` JSON object in the
               text (LLMs sometimes wrap JSON in prose).
            3. If everything fails, log a warning and return
               ``(False, None, 0)``.

        Returns:
            ``(success, mechanic_id, attempts)``.
        """
        candidates: list[str] = []
        stripped = text.strip()
        if stripped:
            candidates.append(stripped)
        # Look for the LAST {...} block in the text — code-fence-friendly.
        for match in re.finditer(r"\{[^{}]*\}", text):
            candidates.append(match.group(0))
        for raw in reversed(candidates):
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(parsed, dict):
                continue
            success = bool(parsed.get("success", False))
            mechanic_id = parsed.get("mechanic_id")
            if mechanic_id is not None and not isinstance(mechanic_id, str):
                mechanic_id = None
            attempts_val = parsed.get("attempts", 0)
            attempts = int(attempts_val) if isinstance(attempts_val, int | float) else 0
            return success, mechanic_id, attempts
        if text:  # only warn if there was something to parse
            logger.warning(
                "Could not parse final OperatorHarness JSON from message; "
                "treating as failure. Final text head: {}",
                text[:200],
            )
        return False, None, 0
