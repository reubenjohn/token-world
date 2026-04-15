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
import os
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
from token_world.operator.overlap import compute_overlap_report
from token_world.operator.subagent import append_decision_log, build_mechanic_author_agent
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
        model: str = os.environ.get("OPERATOR_MODEL", "opus"),
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

    def _build_options(
        self, signal: YieldSignal, *, overlap_report: str = ""
    ) -> ClaudeAgentOptions:
        """Assemble the outer ``ClaudeAgentOptions`` for one ``handle_yield`` call.

        Pure function of ``self``, ``signal``, and ``overlap_report`` so tests
        can introspect its output without invoking the SDK.

        Args:
            signal: The halting yield signal.
            overlap_report: Pre-computed overlap analysis string from
                :func:`~token_world.operator.overlap.compute_overlap_report`.
                Injected into the mechanic-author subagent prompt.
        """
        mcp_servers = load_universe_mcp_config(self.universe)
        mcp_servers["validation"] = build_validation_server(self.universe)
        agent_def = build_mechanic_author_agent(
            universe=self.universe,
            yield_signal=signal,
            model=self.model,
            overlap_report=overlap_report,
        )
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

            # SC-5: compute overlap report before building subagent options so
            # the mechanic-author prompt receives the analysis inline.
            overlap_str = self._compute_overlap(signal)
            options = self._build_options(signal, overlap_report=overlap_str)
            outer_prompt = self._render_outer_prompt(signal)

            final_text = ""
            cost: float | None = None
            turns = 0
            result_received = False
            sdk_subtype: str | None = None
            sdk_error_str: str | None = None
            # Map tool_use_id -> "validate_mechanic" for matching subsequent
            # ToolResultBlocks; per-attempt counter for validation/attempt_NN.json.
            pending_validations: dict[str, int] = {}
            validation_attempt_counter = 0

            try:
                async for msg in query(prompt=outer_prompt, options=options):
                    ctx.append_attempt(self._serialise_message(msg))
                    # Side-effect: when a validate_mechanic ToolResultBlock
                    # arrives, write the report to validation/attempt_NN.json
                    # (D-15 substrate).
                    validation_attempt_counter = self._track_validation(
                        msg=msg,
                        ctx=ctx,
                        pending=pending_validations,
                        counter=validation_attempt_counter,
                    )
                    if isinstance(msg, ResultMessage):
                        final_text = getattr(msg, "result", "") or ""
                        cost = getattr(msg, "total_cost_usd", None)
                        turns = getattr(msg, "num_turns", 0) or 0
                        sdk_subtype = getattr(msg, "subtype", None)
                        result_received = True
            except Exception as exc:
                # Two distinct cases:
                # (a) Exception BEFORE any ResultMessage — genuine failure;
                #     close diagnostics with the error and re-raise so the
                #     caller can react.
                # (b) Exception AFTER a ResultMessage — the SDK sometimes
                #     raises during stream cleanup (observed: "Command failed
                #     with exit code 1" after error_max_turns ResultMessage).
                #     Log + capture the exception in the outcome but do NOT
                #     re-raise; we already have the structured result the
                #     caller needs. Re-raising here would lose the partial
                #     result and break the integration test path.
                if not result_received:
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
                sdk_error_str = repr(exc)
                logger.warning(
                    "SDK query raised after ResultMessage (subtype={}); "
                    "treating as soft failure: {}",
                    sdk_subtype,
                    sdk_error_str,
                )

            success, mechanic_id, attempts = self._parse_final(final_text)
            # If the SDK reported error_max_turns or a stream-cleanup
            # exception fired post-ResultMessage, override success to False
            # even if _parse_final salvaged a JSON-shaped payload.
            if sdk_subtype and sdk_subtype.startswith("error_"):
                success = False
            error_str: str | None
            if success:
                error_str = None
            elif sdk_error_str:
                error_str = sdk_error_str
            elif sdk_subtype:
                error_str = f"sdk_{sdk_subtype}"
            else:
                error_str = "authoring_unsuccessful"
            outcome = {
                "success": success,
                "mechanic_id": mechanic_id,
                "cost_usd": cost,
                "turns": turns,
                "tick_continued": success,
                "error": error_str,
            }
            ctx.close(outcome)
            # SC-5: append to operator-log.jsonl after every yield resolution.
            try:
                append_decision_log(self.universe, signal.tick_id, outcome)
            except Exception as exc:  # pragma: no cover — best-effort
                logger.warning("append_decision_log failed for tick {}: {}", signal.tick_id, exc)
            return OperatorResult(
                success=success,
                tick_id=signal.tick_id,
                mechanic_id=mechanic_id,
                attempts=attempts,
                final_message=final_text,
                cost_usd=cost,
                turns=turns,
                error=error_str,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_overlap(self, signal: YieldSignal) -> str:
        """Compute an overlap report for the classified action verb + watches.

        Loads the mechanic registry from the universe directory and delegates to
        :func:`~token_world.operator.overlap.compute_overlap_report`. Returns an
        empty string on any error so the subagent prompt degrades gracefully.
        """
        try:
            from token_world.mechanic.registry import MechanicRegistry

            mechanics_dir = self.universe / "mechanics"
            if not mechanics_dir.is_dir():
                return ""
            registry = MechanicRegistry(mechanics_dir, universe_dir=self.universe)
            mechanics = list(registry.list_mechanics())
            verb = signal.classified_action.get("verb", "") or ""
            watches = signal.classified_action.get("watches") or []
            if isinstance(watches, str):
                watches = [watches]
            return compute_overlap_report(verb, list(watches), mechanics)
        except Exception as exc:  # noqa: BLE001
            logger.debug("_compute_overlap failed (non-fatal): {}", exc)
            return ""

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
    def _track_validation(
        *,
        msg: Any,
        ctx: Any,
        pending: dict[str, int],
        counter: int,
    ) -> int:
        """Persist validate_mechanic tool reports to ``validation/attempt_NN.json``.

        Two-pass scan over ``msg.content``:

        1. ToolUseBlock with ``name == "validate_mechanic"`` (or
           ``"mcp__validation__validate_mechanic"``): record the
           ``tool_use_id`` and assign it the next attempt number.
        2. ToolResultBlock pointing back at a tracked id: parse the JSON
           report from the content string and atomically write it.

        SDK message contents are lists of typed blocks; we duck-type via
        attribute presence so unexpected shapes don't crash the harness
        (consistency with :meth:`_serialise_message`).

        Args:
            msg: One SDK message yielded by ``query()``.
            ctx: Active :class:`OperatorDiagnosticsContext`.
            pending: Mutating map of tool_use_id -> attempt number.
            counter: Current attempt counter (last-assigned attempt number).

        Returns:
            Updated counter (incremented for each new validate_mechanic use).
        """
        content = getattr(msg, "content", None)
        if not isinstance(content, list):
            return counter
        for block in content:
            block_cls = type(block).__name__
            # ToolUseBlock — assign attempt number on the way in.
            if block_cls == "ToolUseBlock":
                name = getattr(block, "name", "")
                if name == "validate_mechanic" or name.endswith("__validate_mechanic"):
                    tool_use_id = getattr(block, "id", None) or getattr(block, "tool_use_id", None)
                    if isinstance(tool_use_id, str):
                        counter += 1
                        pending[tool_use_id] = counter
            # ToolResultBlock — match against pending, write report.
            elif block_cls == "ToolResultBlock":
                tool_use_id = getattr(block, "tool_use_id", None) or getattr(block, "id", None)
                if not isinstance(tool_use_id, str):
                    continue
                if tool_use_id not in pending:
                    # WR-03: could be an unrelated tool's result OR a
                    # correlation miss (SDK reorders blocks, different SDK
                    # version, etc.). Behaviour unchanged — still skip — but
                    # log at DEBUG so forensic operators can spot misses in
                    # replay-tick / trace logs. Aggressive fallbacks ("claim
                    # the next pending slot") risk miscorrelating distinct
                    # overlapping validations; logging is the minimal fix.
                    logger.debug(
                        "Uncorrelated ToolResultBlock tool_use_id={} "
                        "(no pending validate_mechanic); skipping",
                        tool_use_id,
                    )
                    continue
                attempt_n = pending.pop(tool_use_id)
                report = OperatorHarness._extract_validation_report(block, attempt_n=attempt_n)
                try:
                    ctx.write_validation_report(attempt_n, report)
                except Exception as exc:  # pragma: no cover — best-effort
                    logger.warning(
                        "Failed to write validation/attempt_{:02d}.json: {}",
                        attempt_n,
                        exc,
                    )
        return counter

    @staticmethod
    def _extract_validation_report(block: Any, *, attempt_n: int) -> dict[str, Any]:
        """Pull the JSON validation report out of a ToolResultBlock.

        The validation @tool returns ``{"content": [{"type": "text", "text": "<json>"}],
        "is_error": ...}``. The block's ``content`` is either a string (single
        text result) or a list of those content blocks. We walk both shapes
        and try ``json.loads`` on every text payload until one parses as a
        dict (the report). On failure we record the raw text + an error flag
        so post-hoc inspection still has the signal.
        """
        raw = getattr(block, "content", None)
        candidates: list[str] = []
        if isinstance(raw, str):
            candidates.append(raw)
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        candidates.append(text)
                elif isinstance(item, str):
                    candidates.append(item)
        for text in candidates:
            try:
                parsed = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(parsed, dict):
                return parsed
        # Couldn't parse — preserve the raw payload for forensic readability.
        return {
            "attempt": attempt_n,
            "passed": False,
            "raw_content_repr": repr(raw),
            "_extraction_error": "no JSON-dict report found in tool result",
        }

    @staticmethod
    def _parse_final(text: str) -> tuple[bool, str | None, int]:
        """Parse the outer model's terminating message.

        Strategy (WR-01: the previous ``\\{[^{}]*\\}`` regex matched only the
        innermost brace-free substring, so payloads containing a nested
        ``params`` or other sub-object silently failed):

            1. Try plain ``json.loads`` on the whole stripped text (the prompt
               instructs the model to emit a JSON object).
            2. If (1) fails, walk the text with :class:`json.JSONDecoder.raw_decode`
               starting at each ``{`` — ``raw_decode`` respects brace nesting
               and gracefully returns the end index, so we collect every
               top-level object even when the model wraps JSON in prose.
            3. Prefer the LAST successfully decoded dict (LLMs tend to put the
               summary at the end of their reply).
            4. If everything fails, log a warning and return
               ``(False, None, 0)``.

        Returns:
            ``(success, mechanic_id, attempts)``.
        """
        decoder = json.JSONDecoder()
        candidates: list[dict[str, Any]] = []
        # 1. Plain parse on the full strip (the happy path when the model
        #    complies with the prompt's JSON-only instruction).
        stripped = text.strip()
        if stripped:
            try:
                obj = json.loads(stripped)
                if isinstance(obj, dict):
                    candidates.append(obj)
            except (json.JSONDecodeError, ValueError):
                pass
        # 2. Scan for embedded JSON objects using raw_decode, which honours
        #    brace nesting (fixes the WR-01 nested-object miss).
        i = 0
        n = len(text)
        while i < n:
            idx = text.find("{", i)
            if idx == -1:
                break
            try:
                obj, end = decoder.raw_decode(text, idx)
            except json.JSONDecodeError:
                i = idx + 1
                continue
            if isinstance(obj, dict):
                candidates.append(obj)
            # raw_decode returns an absolute end index into *text*; advance
            # past it so we can pick up subsequent objects in prose.
            i = end if end > idx else idx + 1
        # 3. Prefer the LAST candidate — LLMs put the summary last.
        for parsed in reversed(candidates):
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
