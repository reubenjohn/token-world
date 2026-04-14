"""Live tail of new tick events (``token-world watch <slug>``).

Polls ``<universe>/tick_summaries/ticks/`` at a fixed interval and emits
each newly-appeared file as a one-line summary. Pure-stdlib
implementation — no fsnotify / watchdog dependency.

The function returns control via Ctrl-C (handled by the CLI wrapper).
For test-friendliness, :func:`watch_loop` accepts ``poll_interval``,
``max_iterations`` and an injectable clock so tests can run a single
poll cycle without sleeping.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import IO, Any

from token_world.inspect._shared import iter_tick_files, read_json_file


def _format_tick_line(data: dict[str, Any]) -> str:
    """One-line summary for a tick dict, suitable for stdout streaming."""
    tick_id = data.get("tick_id", "?")
    ts = data.get("timestamp_iso", "")
    if data.get("yielded"):
        status = "yield"
    elif data.get("refused"):
        reason = data.get("refusal_reason") or "?"
        status = f"refuse({reason})"
    elif data.get("matched_mechanic_id"):
        status = data["matched_mechanic_id"]
    else:
        status = "no-match"
    mut_count = (data.get("mutations") or {}).get("count", 0)
    obs = data.get("observation_text") or ""
    obs_excerpt = " ".join(obs.split())
    if len(obs_excerpt) > 60:
        obs_excerpt = obs_excerpt[:57] + "..."
    return f"[{tick_id:>4}] {ts} {status:<24} ({mut_count} mut) {obs_excerpt}"


def watch_loop(
    universe_dir: Path,
    *,
    out: IO[str],
    poll_interval: float = 1.0,
    max_iterations: int | None = None,
    sleep: Callable[[float], None] = time.sleep,
    initial_seen: Iterable[str] | None = None,
) -> set[str]:
    """Tail tick files, emitting one line per new file.

    Args:
        universe_dir: Universe root directory.
        out: Open writable text stream (typically ``sys.stdout``).
        poll_interval: Seconds between polls.
        max_iterations: When set, stop after N polls. ``None`` (default) =
            run until interrupted.
        sleep: Injectable sleep function for tests.
        initial_seen: Tick IDs to consider as already-emitted on entry. When
            ``None``, the loop pre-seeds with the current contents (so
            existing files are NOT re-emitted on startup).

    Returns:
        The final set of seen tick IDs (useful for tests).
    """
    ticks_dir = universe_dir / "tick_summaries" / "ticks"
    if initial_seen is None:
        seen: set[str] = {p.stem.removeprefix("tick_") for p in iter_tick_files(ticks_dir)}
    else:
        seen = set(initial_seen)

    iteration = 0
    while True:
        if max_iterations is not None and iteration >= max_iterations:
            break
        iteration += 1
        for path in iter_tick_files(ticks_dir):
            tick_id = path.stem.removeprefix("tick_")
            if tick_id in seen:
                continue
            data = read_json_file(path)
            if data is None:
                # Mark the path as seen even when malformed so we don't loop.
                seen.add(tick_id)
                continue
            seen.add(tick_id)
            out.write(_format_tick_line(data) + "\n")
            out.flush()
        if max_iterations is not None and iteration >= max_iterations:
            break
        sleep(poll_interval)
    return seen


__all__ = ["_format_tick_line", "watch_loop"]
