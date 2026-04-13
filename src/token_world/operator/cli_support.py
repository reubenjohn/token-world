"""Shared helpers for the operator CLI commands (Phase 04.1-04).

Factored out of :mod:`token_world.cli` so unit tests can exercise the universe-
resolution / renderer / halted-tick logic independently of Click dispatch.

Split at a glance:

- :func:`resolve_universe` — slug > env > cwd > error (RESEARCH §Pattern 6).
- :func:`render_yield_human` / :func:`render_yield_json` — human-readable and
  canonical-JSON renderers for :class:`YieldSignal`.
- :func:`render_replay_human` / :func:`render_replay_json` — renderers for the
  full operator namespace via :class:`OperatorDiagnosticsReader` (D-16).
- :func:`latest_halted_tick` — directory scan that picks the newest halted
  tick (no outcome OR ``success=False``).

All diagnostics parsing happens through
:class:`token_world.operator.diagnostics.OperatorDiagnosticsReader`; there is
no regex file-name parsing anywhere (D-16 invariant preserved).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import click

from token_world.operator.diagnostics import OperatorDiagnosticsReader
from token_world.operator.yield_signal import YieldSignal

if TYPE_CHECKING:
    pass

__all__ = [
    "latest_halted_tick",
    "render_replay_human",
    "render_replay_json",
    "render_yield_human",
    "render_yield_json",
    "resolve_universe",
]


# Cwd-universe markers: a directory is treated as a universe if it has ALL of
# these. Keep the list minimal; false positives here leak into T-04.1-20.
_UNIVERSE_FILE_MARKERS: tuple[str, ...] = (".mcp.json",)
_UNIVERSE_DIR_MARKERS: tuple[str, ...] = ("mechanics",)


# --------------------------------------------------------------------------- #
# Universe resolution (RESEARCH §Pattern 6)
# --------------------------------------------------------------------------- #


def resolve_universe(slug_or_none: str | None) -> Path:
    """Locate the universe directory to operate on.

    Resolution order (RESEARCH §Pattern 6; D-11):

    1. **Explicit slug**: ``UniverseManager().load(slug)``.
    2. **Env var**: ``TOKEN_WORLD_UNIVERSE=/absolute/path``.
    3. **CWD**: if it contains ``.mcp.json`` + ``mechanics/``.
    4. **Error**: raises :class:`click.ClickException` with remediation.

    Args:
        slug_or_none: Explicit universe slug, or ``None`` to fall through to
            env / cwd.

    Returns:
        Absolute :class:`pathlib.Path` to the universe directory.

    Raises:
        click.ClickException: if no resolution strategy yields a universe.
        FileNotFoundError: if the explicit slug does not name an existing
            universe (propagated from :class:`UniverseManager`).
    """
    if slug_or_none:
        # Local import keeps import-time work tiny for non-universe commands
        from token_world.universe.manager import UniverseManager

        return UniverseManager().load(slug_or_none)
    env = os.environ.get("TOKEN_WORLD_UNIVERSE")
    if env:
        return Path(env)
    cwd = Path.cwd()
    files_ok = all((cwd / m).exists() for m in _UNIVERSE_FILE_MARKERS)
    dirs_ok = all((cwd / d).is_dir() for d in _UNIVERSE_DIR_MARKERS)
    if files_ok and dirs_ok:
        return cwd
    raise click.ClickException(
        "No universe specified. Options:\n"
        "  (1) pass a slug: `token-world <cmd> <slug>`\n"
        "  (2) set env var: `TOKEN_WORLD_UNIVERSE=/path/to/universe`\n"
        "  (3) run inside a universe folder (one containing .mcp.json and mechanics/)"
    )


# --------------------------------------------------------------------------- #
# Renderers: YieldSignal
# --------------------------------------------------------------------------- #


def render_yield_human(signal: YieldSignal) -> str:
    """Render a :class:`YieldSignal` as human-readable multi-line text.

    Designed for an operator reading ``inspect-yield`` or ``replay-tick``
    output in a terminal — not machine-parsable; use :func:`render_yield_json`
    for that.
    """
    classified = signal.classified_action
    params = classified.get("params", {})
    lines = [
        f"Tick {signal.tick_id} — yielded ({signal.reason})",
        f"Universe: {signal.universe_path}",
        f"Action text: {signal.action_text!r}",
        "",
        "Classified action:",
        f"  verb:   {classified.get('verb')}",
        f"  actor:  {classified.get('actor')}",
        f"  target: {classified.get('target')}",
        f"  params: {json.dumps(params, indent=2)}",
        "",
        f"Actor state: {json.dumps(signal.actor_state, indent=2)}",
        f"Candidate mechanics: {signal.candidate_mechanic_ids or '(none)'}",
    ]
    return "\n".join(lines)


def render_yield_json(signal: YieldSignal) -> str:
    """Return the canonical (deterministic) JSON form of the signal."""
    return signal.to_json()


# --------------------------------------------------------------------------- #
# Renderers: operator replay
# --------------------------------------------------------------------------- #


def render_replay_human(reader: OperatorDiagnosticsReader) -> str:
    """Render the full operator diagnostics namespace for human reading.

    Missing artefacts degrade gracefully:
        - No ``yield_signal.json`` -> single-line "no session" message.
        - No ``resume_outcome.json`` -> "session not closed" note.
        - No ``mechanic_diff.patch`` -> "(none written)" note.
    """
    try:
        signal = reader.yield_signal()
    except FileNotFoundError:
        return f"No operator session found for tick {reader.tick_id}."

    attempts = reader.attempts()
    validations = reader.validation_reports()
    diff = reader.mechanic_diff()
    outcome = reader.resume_outcome()

    out: list[str] = [
        render_yield_human(signal),
        "",
        f"Authoring attempts: {len(attempts)} message(s)",
        f"Validation reports: {len(validations)}",
    ]
    for i, rep in enumerate(validations, 1):
        passed = "PASS" if rep.get("passed") else "FAIL"
        findings = rep.get("findings", [])
        out.append(f"  attempt_{i:02d}: {passed} ({len(findings)} findings)")

    out.append("")
    if diff is not None:
        out.append(f"Mechanic diff ({len(diff)} chars):")
        snippet = diff[:500] + ("..." if len(diff) > 500 else "")
        out.append(snippet)
    else:
        out.append("Mechanic diff: (none written)")

    if outcome is None:
        out.append("")
        out.append("Session not closed (resume_outcome.json missing).")
    else:
        out.append("")
        out.append(
            f"Outcome: success={outcome.get('success')} "
            f"mechanic_id={outcome.get('mechanic_id')!r} "
            f"cost_usd={outcome.get('cost_usd')} turns={outcome.get('turns')}"
        )
        if outcome.get("error"):
            out.append(f"Error: {outcome['error']}")

    return "\n".join(out)


def render_replay_json(reader: OperatorDiagnosticsReader) -> str:
    """Render the full operator namespace as a deterministic JSON document.

    Shape::

        {
          "yield_signal": {...},          # parsed YieldSignal (object)
          "attempts": [...],              # JSONL lines (tolerant)
          "validation_reports": [...],    # attempt_NN.json contents
          "mechanic_diff": "..." | null,
          "resume_outcome": {...} | null,
        }

    When ``yield_signal.json`` is missing, emits ``{"error": "no_session",
    "tick_id": "..."}`` instead — lets automation detect "no session here"
    without exception handling in the caller.
    """
    try:
        signal_json = reader.yield_signal().to_json()
    except FileNotFoundError:
        return json.dumps(
            {"error": "no_session", "tick_id": reader.tick_id}, indent=2, sort_keys=True
        )

    payload = {
        "yield_signal": json.loads(signal_json),
        "attempts": reader.attempts(),
        "validation_reports": reader.validation_reports(),
        "mechanic_diff": reader.mechanic_diff(),
        "resume_outcome": reader.resume_outcome(),
    }
    return json.dumps(payload, indent=2, sort_keys=True)


# --------------------------------------------------------------------------- #
# Halted-tick scanner
# --------------------------------------------------------------------------- #


def latest_halted_tick(universe: Path) -> str | None:
    """Return the id (without ``tick_`` prefix) of the newest halted tick.

    A tick is considered **halted** if:

    - Its operator folder exists AND
    - ``resume_outcome.json`` is missing, OR
    - ``resume_outcome.json`` is corrupt (fails :func:`json.loads`), OR
    - ``resume_outcome.json`` has ``success=False``.

    Sort order: numerical on the id suffix if parseable as ``int``; falls
    through to lexicographic for non-numeric ids (which sort *before* any
    numeric id under the implementation rule). The caller receives the
    maximum halted tick under that ordering.

    Args:
        universe: Universe root (contains ``diagnostics/``).

    Returns:
        ``"tick_id_string"`` if a halted tick exists; ``None`` otherwise
        (empty diagnostics dir, missing dir, or all ticks succeeded).
    """
    diag_dir = universe / "diagnostics"
    if not diag_dir.is_dir():
        return None

    halted: list[str] = []
    for tick_dir in diag_dir.iterdir():
        if not tick_dir.is_dir() or not tick_dir.name.startswith("tick_"):
            continue
        op_dir = tick_dir / "operator"
        if not op_dir.is_dir():
            # Tick folders without operator/ are Phase-4-only and not halted.
            continue
        outcome_file = op_dir / "resume_outcome.json"
        if not outcome_file.exists():
            halted.append(tick_dir.name)
            continue
        try:
            outcome = json.loads(outcome_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # Corruption == needs investigation == halted.
            halted.append(tick_dir.name)
            continue
        if not isinstance(outcome, dict) or not outcome.get("success", False):
            halted.append(tick_dir.name)

    if not halted:
        return None

    def sort_key(name: str) -> tuple[int, str]:
        suffix = name.removeprefix("tick_")
        try:
            return (int(suffix), name)
        except ValueError:
            # Non-numeric ids sort before numeric under this key.
            return (-1, name)

    halted.sort(key=sort_key)
    return halted[-1].removeprefix("tick_")
