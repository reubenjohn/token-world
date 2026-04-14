"""Shared helpers for the inspect/ subpackage.

Pure utility module: tick-file iteration, JSON parsing, numeric tick-id
sorting. Modelled on (but intentionally not imported from)
``token_world.playtest.cost`` — the cost module owns its private copies
because that subpackage's contract pins the module to ``playtest/``.
Duplicating ~25 LOC is the right ROI here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def tick_id_sort_key(tick_id: str) -> tuple[int, str]:
    """Sort tick IDs numerically when possible, lexicographically otherwise.

    Mirrors ``cost._tick_id_sort_key`` so output ordering across CLI commands
    stays consistent.
    """
    try:
        return (int(tick_id), "")
    except (TypeError, ValueError):
        return (sys.maxsize, tick_id)


def iter_tick_files(ticks_dir: Path, since: int | None = None) -> list[Path]:
    """Return ``tick_*.json`` files sorted by numeric tick id.

    Args:
        ticks_dir: ``<universe>/tick_summaries/ticks`` directory.
        since: If provided and positive, keep only the LAST N files
            (highest tick IDs) — matches ``cost``'s ``--since`` semantics.

    Returns:
        Empty list when the directory is missing.
    """
    if not ticks_dir.is_dir():
        return []
    files = sorted(
        ticks_dir.glob("tick_*.json"),
        key=lambda p: tick_id_sort_key(p.stem.removeprefix("tick_")),
    )
    if since is not None and since > 0:
        files = files[-since:]
    return files


def read_json_file(path: Path) -> dict[str, Any] | None:
    """Return parsed JSON object, or ``None`` on malformed/non-object payloads.

    Errors are swallowed silently — callers that need warnings should
    re-implement (cost.py is the exemplar). Inspect modules trade
    granular reporting for caller simplicity.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data
