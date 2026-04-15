"""Locked YieldSignal contract (Phase 4.1 D-07, D-10).

The simulation engine (Phase 5) emits a :class:`YieldSignal` when action
classification succeeds but no mechanic matches. The operator harness consumes
it, spawns an authoring subagent to write the missing mechanic, then calls
``resume_tick`` to continue the halted tick.

**This dataclass is the stable interface** between the engine and the operator.
Locked in Phase 4.1; Phase 5 produces instances of exactly this shape.
Breaking changes bump :data:`SCHEMA_VERSION`; :meth:`YieldSignal.from_json`
rejects unknown versions (threat T-04.1-01).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = ["SCHEMA_VERSION", "YieldSignal"]


SCHEMA_VERSION: int = 1
"""Version of the YieldSignal contract. Bump on any breaking field change."""


# Required keys inside ``classified_action``. ``target`` is required to be
# *present* but may have value ``None`` (e.g., verbs like "shout" with no
# target). ``params`` must be a dict; its shape is verb-specific.
_REQUIRED_CLASSIFIED_ACTION_KEYS: tuple[str, ...] = ("verb", "actor", "target", "params")


@dataclass(frozen=True, slots=True)
class YieldSignal:
    """Contract between simulation engine and operator.

    Emitted when the engine classifies a resident-agent action but finds no
    matching mechanic in the registry. The operator authors the missing
    mechanic, writes it to ``mechanics/<id>.py``, and calls ``resume_tick``
    to continue the halted tick.

    In composite-action ticks (Phase 16 D-01), a YieldSignal is emitted for the first
    sub-action that has no matching mechanic; subsequent sub-actions are not evaluated
    until the operator authors the missing mechanic and calls ``resume_tick``.

    Locked in Phase 4.1; Phase 5 engine produces instances of exactly this
    shape. See ``.planning/phases/04.1-operator-agent-harness/04.1-RESEARCH.md``
    §"Pattern 1: YieldSignal — Locked Contract" for the per-field rationale.
    """

    # --- Identity & provenance ---
    tick_id: str
    """The tick the engine halted on. ``resume_tick(tick_id=...)`` continues it."""

    universe_path: str
    """Absolute path to the universe folder. Disambiguates multi-universe setups."""

    schema_version: int = SCHEMA_VERSION
    """Bumped on breaking changes to this dataclass."""

    # --- Why we yielded ---
    reason: str = "no_mechanic_for_action"
    """Currently the only reason. Future reasons may be added in v2+."""

    # --- What the resident agent tried to do ---
    action_text: str = ""
    """Raw free-form text the resident agent produced (e.g., ``"pick up the rock"``).
    Unclassified. Preserved for the authoring subagent's context."""

    classified_action: dict[str, Any] = field(default_factory=dict)
    """Structured output from Phase 5's Haiku classifier. Required keys
    (enforced by :meth:`validate`):

    - ``verb`` (``str``): e.g., ``"pickup"``, ``"move"``, ``"speak"``.
    - ``actor`` (``str``): node id of the acting agent.
    - ``target`` (``str | None``): node id if applicable; ``None`` for targetless verbs.
    - ``params`` (``dict[str, Any]``): free-form, verb-specific payload.
    """

    # --- Context for the authoring subagent ---
    actor_state: dict[str, Any] = field(default_factory=dict)
    """Snapshot of the actor node's properties at halt. Enables the subagent
    to reason about preconditions without a second graph query."""

    candidate_mechanic_ids: list[str] = field(default_factory=list)
    """Engine's best guess at plausible existing mechanic IDs that were
    considered but ruled out. Helps the subagent decide between extending
    an existing mechanic and authoring a new one."""

    # --------------------------- Serialisation --------------------------- #

    def to_json(self) -> str:
        """Serialise to deterministic JSON (sorted keys, indent=2).

        Sorted keys + fixed indentation keep diagnostics diffs meaningful
        (threat T-04.1-04 — silent-change tampering through format drift).
        """
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, payload: str) -> YieldSignal:
        """Parse and validate a serialised YieldSignal.

        Raises:
            json.JSONDecodeError: payload is not valid JSON.
            TypeError: root is not a JSON object, or fields are missing/extra.
            ValueError: ``schema_version`` is not the currently-supported value.

        Threat T-04.1-01: yield signals are read from disk in ``inspect-yield``
        and ``replay-tick``; this method is the trust boundary enforcing that
        only well-shaped, version-matched payloads are accepted.
        """
        data = json.loads(payload)  # raises JSONDecodeError on malformed input
        if not isinstance(data, dict):
            raise TypeError(f"YieldSignal payload must be an object, got {type(data).__name__}")
        version = data.get("schema_version", SCHEMA_VERSION)
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported YieldSignal schema_version={version}; "
                f"this operator only understands v{SCHEMA_VERSION}. "
                f"Upgrade token-world or downgrade the emitter."
            )
        # Unpacking raises TypeError on missing required or unknown extra keys
        # (strict policy — see test_from_json_rejects_extra_fields).
        return cls(**data)

    # --------------------------- Validation ------------------------------ #

    def validate(self) -> None:
        """Enforce :attr:`classified_action` shape. No-op on success.

        Required keys: ``verb`` (str), ``actor`` (str), ``target`` (str | None),
        ``params`` (dict). Value types on ``verb``/``actor`` are checked; the
        shape of ``params`` is intentionally ``dict[str, Any]`` (verb-specific).

        Covers Pitfall 4: stub↔Phase-5 shape drift. The stub calls
        ``validate`` at fabrication time so any contract divergence surfaces
        inside the Phase 4.1 test suite, not in Phase 5 debugging.

        Raises:
            ValueError: with the first offending key named.
        """
        ca = self.classified_action
        for key in _REQUIRED_CLASSIFIED_ACTION_KEYS:
            if key not in ca:
                raise ValueError(
                    f"classified_action missing required key '{key}'; "
                    f"got keys={sorted(ca.keys())!r}"
                )
        if not isinstance(ca["verb"], str):
            raise ValueError(
                f"classified_action['verb'] must be str, got {type(ca['verb']).__name__}"
            )
        if not isinstance(ca["actor"], str):
            raise ValueError(
                f"classified_action['actor'] must be str, got {type(ca['actor']).__name__}"
            )
        target = ca["target"]
        if target is not None and not isinstance(target, str):
            raise ValueError(
                f"classified_action['target'] must be str or None, got {type(target).__name__}"
            )
        if not isinstance(ca["params"], dict):
            raise ValueError(
                f"classified_action['params'] must be dict, got {type(ca['params']).__name__}"
            )
