"""Single-tick detail aggregator (``token-world tick <slug> <tick_id>``).

Loads ``<universe>/tick_summaries/ticks/tick_<tick_id>.json`` and renders
the full action -> classification -> mechanic -> mutations -> observation
chain as either a tree (default) or raw JSON.

The JSON output is exactly the on-disk TickSummary v1 payload (forward-
compatible — extra fields pass through unchanged). The tree renderer is
formatted for human reading and is NOT a stable contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TickNotFoundError(LookupError):
    """Raised when the requested tick file does not exist."""


def load_tick(universe_dir: Path, tick_id: str) -> dict[str, Any]:
    """Read ``tick_<tick_id>.json`` and return the parsed payload.

    Args:
        universe_dir: Universe root directory.
        tick_id: Stringified tick identifier (e.g. ``"42"``).

    Returns:
        The parsed JSON object.

    Raises:
        TickNotFoundError: If no such tick file exists.
        json.JSONDecodeError: If the file is unreadable as JSON.
    """
    path = universe_dir / "tick_summaries" / "ticks" / f"tick_{tick_id}.json"
    if not path.is_file():
        raise TickNotFoundError(
            f"No tick summary at {path}. "
            f"Try `token-world inspect <slug>` to see available tick IDs."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise json.JSONDecodeError(
            "tick file top-level JSON is not an object", path.read_text(encoding="utf-8"), 0
        )
    return payload


def _wrap(text: str | None, *, prefix: str = "    ", width: int = 80) -> list[str]:
    """Render ``text`` as wrapped lines with a uniform prefix.

    Returns ``[]`` for ``None`` so callers can ``extend`` unconditionally.
    """
    if text is None:
        return []
    flat = " ".join(text.split())
    if not flat:
        return []
    out: list[str] = []
    while len(flat) > width:
        out.append(prefix + flat[:width])
        flat = flat[width:]
    out.append(prefix + flat)
    return out


def render_tree(tick: dict[str, Any]) -> str:
    """Render a tick payload as an indent-based tree.

    The tree maps to the engine pipeline:

    - tick_id / timestamp_iso (header)
    - action_text (raw resident input)
    - classified_action (verb / subject / object / modifier / confidence)
    - matched_mechanic_id (or refusal / yield reason)
    - mutations (target / property / old -> new, one per line)
    - observation_text (truncated body)
    - long_running_action (when present)
    - duration_ms / token + cost summary
    """
    out: list[str] = []
    tid = tick.get("tick_id", "?")
    ts = tick.get("timestamp_iso", "?")
    out.append(f"=== Tick {tid} @ {ts} ===")

    out.append("")
    out.append("action_text:")
    out.extend(_wrap(tick.get("action_text"), prefix="  "))

    out.append("")
    out.append("classification:")
    classified = tick.get("classified_action")
    if classified is None:
        out.append("  (none — pre-classifier or unparsed)")
    else:
        for key in ("verb", "subject", "object", "modifier", "confidence"):
            if key in classified:
                out.append(f"  {key}: {classified[key]!r}")
        # Surface any extra fields without losing them.
        extras = {
            k: v
            for k, v in classified.items()
            if k not in {"verb", "subject", "object", "modifier", "confidence"}
        }
        for k, v in extras.items():
            out.append(f"  {k}: {v!r}")

    out.append("")
    out.append("decision:")
    if tick.get("yielded"):
        out.append("  status: YIELDED to operator")
    elif tick.get("refused"):
        reason = tick.get("refusal_reason") or "(no reason given)"
        out.append(f"  status: REFUSED ({reason})")
    elif tick.get("matched_mechanic_id"):
        out.append("  status: EXECUTED")
        out.append(f"  mechanic: {tick['matched_mechanic_id']}")
    else:
        out.append("  status: (no mechanic match)")

    out.append("")
    out.append("mutations:")
    mutations = tick.get("mutations") or {}
    mut_list = mutations.get("list") or []
    if not mut_list:
        out.append("  (none)")
    else:
        out.append(f"  count: {mutations.get('count', len(mut_list))}")
        for entry in mut_list:
            # On-disk format: [target, property, old, new]
            if isinstance(entry, list) and len(entry) == 4:
                target, prop, old, new = entry
                if prop is None:
                    out.append(f"  - {target}: {old!r} -> {new!r}")
                else:
                    out.append(f"  - {target}.{prop}: {old!r} -> {new!r}")
            else:
                out.append(f"  - {entry!r}")

    out.append("")
    out.append("observation:")
    obs = tick.get("observation_text")
    if obs is None:
        out.append("  (none)")
    else:
        out.extend(_wrap(obs, prefix="  "))

    lra = tick.get("long_running_action")
    if lra:
        out.append("")
        out.append("long_running_action:")
        for k, v in lra.items():
            out.append(f"  {k}: {v!r}")

    out.append("")
    out.append("metadata:")
    out.append(f"  duration_ms: {tick.get('duration_ms', '?')}")
    tok_by_stage = tick.get("llm_tokens_by_stage") or {}
    cost_by_stage = tick.get("llm_cost_usd_by_stage") or {}
    if tok_by_stage or cost_by_stage:
        for stage in sorted(set(tok_by_stage) | set(cost_by_stage)):
            tok = tok_by_stage.get(stage) or {}
            in_tok = int(tok.get("in", 0) or 0)
            out_tok = int(tok.get("out", 0) or 0)
            cost = float(cost_by_stage.get(stage, 0.0) or 0.0)
            out.append(f"  llm[{stage}]: in={in_tok} out={out_tok} cost=${cost:.4f}")

    return "\n".join(out) + "\n"


def render_json(tick: dict[str, Any], *, indent: int | None = 2) -> str:
    """Pass-through JSON renderer — emits the on-disk payload unchanged."""
    return json.dumps(tick, indent=indent, sort_keys=True) + "\n"
