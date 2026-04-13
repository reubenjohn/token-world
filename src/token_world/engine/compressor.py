"""TickCompressor — online hierarchical tick-summary compression (D-17, D-19, SIM-12).

After every tick write, :meth:`TickCompressor.maybe_compress` checks whether
the universe's ``tick_summaries/ticks/`` directory has accumulated enough
tick files to trigger a batch pass.  When batch files accumulate enough, an
epoch pass fires.

Crash-safety (06-RESEARCH Pitfall 5):
    The batch/epoch output file is written (atomically via
    :func:`~token_world.mechanic.diagnostics._atomic_write_json`) **before** the
    input files are deleted.  If the process crashes between write and delete,
    the next run finds the output file already present (batch_id collision is
    avoided via ``_next_batch_id``) and the input files — a harmless duplicate;
    at worst the next compression pass re-reads the already-batched ticks and
    creates a second batch.  This is correct: at-least-once is acceptable;
    at-most-once is not required for summaries.

Stateless design (D-19):
    ``TickCompressor`` reads and writes only the filesystem.  It does not
    mutate the KnowledgeGraph or touch ``universe.db``.  It can be instantiated
    once and reused across many :meth:`maybe_compress` calls without concern.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from token_world.engine.models import BatchSummary, EpochSummary
from token_world.mechanic.diagnostics import _atomic_write_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Haiku compression prompts (D-27 scope: prompt wording is at Claude's
# discretion; SHA-256 stored in BatchSummary for prompt-change detection).
# ---------------------------------------------------------------------------

_BATCH_PROMPT_TEMPLATE = (
    "Given these {N} sequential simulation tick summaries, produce a concise batch summary.\n"
    "Each tick has: tick_id, action_text, matched_mechanic_id, mutation count,"
    " observation_text.\n\n"
    "Return JSON exactly matching:\n"
    "{{\n"
    '  "key_events": [<3-5 short strings describing notable events>],\n'
    '  "mechanic_ids_used": [<union of matched_mechanic_id values, null filtered>],\n'
    '  "total_mutations": <sum of mutation counts>\n'
    "}}\n\n"
    "Ticks:\n"
    "{tick_payloads}"
)

_EPOCH_PROMPT_TEMPLATE = (
    "Given these {N} batch summaries of a simulation's history, produce a"
    " one-paragraph synopsis\n"
    "covering the major arcs and any patterns across batches.\n\n"
    'Return JSON:\n{{"synopsis": "<paragraph>"}}\n\n'
    "Batches:\n"
    "{batch_payloads}"
)

_BATCH_PROMPT_HASH: str = hashlib.sha256(_BATCH_PROMPT_TEMPLATE.encode()).hexdigest()


def _numeric_id_from_stem(pattern: str, stem: str) -> int | None:
    """Extract a numeric ID from a file stem using *pattern* (one capture group)."""
    m = re.search(pattern, stem)
    if m is None:
        return None
    try:
        return int(m.group(1))
    except (IndexError, ValueError):
        return None


def _sort_key_tick(p: Path) -> int:
    """Numeric sort key for tick_<N>.json files."""
    return _numeric_id_from_stem(r"tick_(\d+)", p.stem) or 0


def _sort_key_batch(p: Path) -> int:
    """Numeric sort key for batch_<N>.json files."""
    return _numeric_id_from_stem(r"batch_(\d+)", p.stem) or 0


def _sort_key_epoch(p: Path) -> int:
    """Numeric sort key for epoch_<N>.json files."""
    return _numeric_id_from_stem(r"epoch_(\d+)", p.stem) or 0


def _parse_haiku_json(text: str) -> dict[str, Any]:
    """Extract the first JSON object from *text*.

    Uses a simple regex to find the outermost ``{...}`` block.  On first
    failure, strips leading/trailing whitespace and retries once.  Raises
    ``ValueError`` if both attempts fail.
    """
    for attempt, candidate in enumerate([text, text.strip()]):
        m = re.search(r"\{.*\}", candidate, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))  # type: ignore[return-value]
            except json.JSONDecodeError:
                pass
        if attempt == 1:
            break
    raise ValueError(f"Could not parse JSON from Haiku response: {text!r}")


@dataclass(slots=True)
class TickCompressor:
    """Stateless online batch + epoch compressor for tick summaries (D-17, D-19).

    The module-level ``_BATCH_PROMPT_TEMPLATE`` constant is accessible on the
    class as ``TickCompressor._BATCH_PROMPT_TEMPLATE`` via the class ``__dict__``
    — but NOT as a slot field.  Tests that need the template string should
    import it directly: ``from token_world.engine.compressor import
    _BATCH_PROMPT_TEMPLATE``.  Alternatively, access via the class attribute
    set below using ``__init_subclass__`` trick is too complex; we simply expose
    it as a module-level constant and alias it at the class level via a
    ``ClassVar``.

    Attributes:
        batch_size: Number of tick files that trigger a batch compression pass.
            Set to ``<= 0`` to disable compression entirely.
        epoch_size: Number of batch files that trigger an epoch compression pass.
        model: Anthropic model used for Haiku compression calls.
    """

    batch_size: int = 100
    epoch_size: int = 100
    model: str = "claude-haiku-4-5"

    def maybe_compress(self, universe_dir: Path, client: Any) -> None:
        """Run compression passes if thresholds are met.

        Called by :class:`~token_world.engine.engine.SimulationEngine` after
        every :meth:`~token_world.engine.summary_writer.TickSummaryWriter.write`
        call.  Both passes (batch and epoch) are checked in sequence within a
        single call so that a run that crosses both thresholds at once is handled
        correctly.

        Args:
            universe_dir: Root of the universe directory.  Must contain
                ``tick_summaries/ticks/`` for the batch pass to fire.
            client: An ``anthropic.Anthropic`` instance (or test fake) used for
                Haiku compression synthesis calls.
        """
        if self.batch_size <= 0 or self.epoch_size <= 0:
            return

        tick_dir = universe_dir / "tick_summaries" / "ticks"
        if tick_dir.exists():
            tick_files = sorted(tick_dir.glob("tick_*.json"), key=_sort_key_tick)

            if len(tick_files) >= self.batch_size:
                to_compress = tick_files[: self.batch_size]
                try:
                    self._compress_batch(to_compress, universe_dir, client)
                except Exception as exc:
                    logger.warning("Batch compression failed: %s", exc)
                    # Don't proceed to epoch if batch failed to avoid partial state
                    return

        # Re-scan batch files after potential batch compression (or if tick dir absent)
        summary_dir = universe_dir / "tick_summaries"
        if not summary_dir.exists():
            return

        batch_files = sorted(summary_dir.glob("batch_*.json"), key=_sort_key_batch)

        if len(batch_files) >= self.epoch_size:
            to_compress_batches = batch_files[: self.epoch_size]
            try:
                self._compress_epoch(to_compress_batches, universe_dir, client)
            except Exception as exc:
                logger.warning("Epoch compression failed: %s", exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compress_batch(self, tick_files: list[Path], universe_dir: Path, client: Any) -> None:
        """Compress *tick_files* into a single batch_<id>.json.

        Crash-safety: the batch file is written **before** tick files are
        deleted (06-RESEARCH Pitfall 5 mitigation).
        """
        payloads: list[dict[str, Any]] = []
        for tf in tick_files:
            try:
                raw = json.loads(tf.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Skipping unreadable tick file %s: %s", tf, exc)
                continue
            payloads.append(
                {
                    "tick_id": raw.get("tick_id", "?"),
                    "action_text": raw.get("action_text", ""),
                    "matched_mechanic_id": raw.get("matched_mechanic_id"),
                    "mutation_count": raw.get("mutations", {}).get("count", 0),
                    "observation_text": raw.get("observation_text"),
                }
            )

        prompt = _BATCH_PROMPT_TEMPLATE.format(
            N=len(payloads),
            tick_payloads=json.dumps(payloads, indent=2),
        )
        response = client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = response.content[0].text
        parsed = _parse_haiku_json(response_text)

        batch_id = self._next_batch_id(universe_dir)
        first_tick = payloads[0]["tick_id"] if payloads else "?"
        last_tick = payloads[-1]["tick_id"] if payloads else "?"

        batch = BatchSummary(
            batch_id=batch_id,
            first_tick=str(first_tick),
            last_tick=str(last_tick),
            tick_count=len(tick_files),
            key_events=parsed.get("key_events", []),
            mechanic_ids_used=parsed.get("mechanic_ids_used", []),
            total_mutations=int(parsed.get("total_mutations", 0)),
            agent_id="unknown",
            haiku_prompt_hash=_BATCH_PROMPT_HASH,
        )

        summary_dir = universe_dir / "tick_summaries"
        batch_path = summary_dir / f"batch_{batch_id}.json"
        _atomic_write_json(batch_path, json.loads(batch.model_dump_json()))

        # WRITE-THEN-DELETE: batch file must exist before any tick is deleted.
        for tf in tick_files:
            tf.unlink(missing_ok=True)

        logger.debug(
            "Batch %d created from %d ticks (%s–%s)",
            batch_id,
            len(tick_files),
            first_tick,
            last_tick,
        )

    def _compress_epoch(self, batch_files: list[Path], universe_dir: Path, client: Any) -> None:
        """Compress *batch_files* into a single epoch_<id>.json."""
        payloads: list[dict[str, Any]] = []
        for bf in batch_files:
            try:
                raw = json.loads(bf.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Skipping unreadable batch file %s: %s", bf, exc)
                continue
            payloads.append(
                {
                    "batch_id": raw.get("batch_id", "?"),
                    "tick_count": raw.get("tick_count", 0),
                    "key_events": raw.get("key_events", []),
                    "total_mutations": raw.get("total_mutations", 0),
                }
            )

        prompt = _EPOCH_PROMPT_TEMPLATE.format(
            N=len(payloads),
            batch_payloads=json.dumps(payloads, indent=2),
        )
        response = client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = response.content[0].text
        parsed = _parse_haiku_json(response_text)

        epoch_id = self._next_epoch_id(universe_dir)
        batch_ids = [p.get("batch_id", 0) for p in payloads]
        first_batch = min(batch_ids) if batch_ids else 0
        last_batch = max(batch_ids) if batch_ids else 0

        epoch = EpochSummary(
            epoch_id=epoch_id,
            first_batch=int(first_batch),
            last_batch=int(last_batch),
            batch_count=len(batch_files),
            synopsis=parsed.get("synopsis", ""),
        )

        summary_dir = universe_dir / "tick_summaries"
        epoch_path = summary_dir / f"epoch_{epoch_id}.json"
        _atomic_write_json(epoch_path, json.loads(epoch.model_dump_json()))

        # WRITE-THEN-DELETE: epoch file must exist before any batch is deleted.
        for bf in batch_files:
            bf.unlink(missing_ok=True)

        logger.debug(
            "Epoch %d created from %d batches (batch %d–%d)",
            epoch_id,
            len(batch_files),
            first_batch,
            last_batch,
        )

    def _next_batch_id(self, universe_dir: Path) -> int:
        """Return the next monotonic batch ID (max existing + 1, or 0 if none)."""
        summary_dir = universe_dir / "tick_summaries"
        existing = list(summary_dir.glob("batch_*.json"))
        if not existing:
            return 0
        ids = [_numeric_id_from_stem(r"batch_(\d+)", p.stem) for p in existing]
        valid_ids = [i for i in ids if i is not None]
        return max(valid_ids) + 1 if valid_ids else 0

    def _next_epoch_id(self, universe_dir: Path) -> int:
        """Return the next monotonic epoch ID (max existing + 1, or 0 if none)."""
        summary_dir = universe_dir / "tick_summaries"
        existing = list(summary_dir.glob("epoch_*.json"))
        if not existing:
            return 0
        ids = [_numeric_id_from_stem(r"epoch_(\d+)", p.stem) for p in existing]
        valid_ids = [i for i in ids if i is not None]
        return max(valid_ids) + 1 if valid_ids else 0


# Expose the batch prompt template on the class so tests can verify the stored
# SHA-256 without importing the module-level constant directly.
# ``slots=True`` prevents setting class attributes inside the class body, but
# setting them AFTER the class definition is allowed.
TickCompressor._BATCH_PROMPT_TEMPLATE = _BATCH_PROMPT_TEMPLATE  # type: ignore[attr-defined]
