"""Shared refusal narrative template (D-13).

Routes three refusal sources through one narrative surface:
1. Classifier verdicts that refuse (no_viable_action, no_such_target, low_confidence)
2. Conservation violations (engine-level)
3. Mechanic-level refusals via ``ctx.refuse(reason_code, details)`` helper

Keeps refusal language consistent from the resident agent's perspective —
"you can't do that" feels the same whether the classifier gave up, a mechanic
refused, or conservation caught a matter-creation attempt.
"""

from __future__ import annotations

from typing import Any

# Template keys: one per reason_code. Keep narratives short, grounded, second-person.
_TEMPLATES: dict[str, str] = {
    "no_viable_action": (
        "You try to {action_text}, but the attempt is incoherent — nothing in the world responds."
    ),
    "no_such_target": (
        "You try to act on {target_text}, but no such thing is here for you to act on."
    ),
    "low_confidence": (
        "You consider {action_text}, but the attempt feels confused — you aren't sure "
        "what you mean, and nothing happens."
    ),
    "mechanic_check_failed": ("You try, but {reason}."),
    "conservation_violation": (
        "You try, but the attempt would break a fundamental law: {violated_property} "
        "cannot simply appear or disappear."
    ),
    # The keys below are *mechanic-provided convenience shortcuts* only.
    # The engine never reads graph properties named "inventory_full", "locked",
    # or "blocked" to gate actions — these names are purely narrative sugar that
    # a mechanic may pass as reason_code to ctx.refuse().  Any arbitrary string
    # also works; these entries just give mechanics a polished pre-written
    # template so they don't have to craft their own prose.  Adding an entry
    # here does NOT give the engine knowledge of that property.
    # reads-only framework hook — not a semantic gate
    "inventory_full": ("You try to pick up {target}, but your hands and pack are already full."),
    # reads-only framework hook — not a semantic gate
    "locked": ("You try, but {target} is locked."),
    # reads-only framework hook — not a semantic gate
    "blocked": ("You try, but {reason} is in the way."),
}

_FALLBACK_TEMPLATE = "You try, but the attempt fails — {reason_code}."

_WRAPPER_PREFIX = "You try, but "


def _strip_wrapper(s: str) -> str:
    """Strip repeated 'You try, but ' prefix from a reason string."""
    while s.startswith(_WRAPPER_PREFIX):
        s = s[len(_WRAPPER_PREFIX) :]
    # Strip leading period/space left from prior formatting
    s = s.lstrip(". ")
    return s


class RefusalTemplate:
    """Narrative rendering for refusal reasons (D-13)."""

    @staticmethod
    def render(reason_code: str, details: dict[str, Any] | None = None) -> str:
        """Render a refusal narrative for the given reason code.

        Args:
            reason_code: One of the known reason codes (see _TEMPLATES) or arbitrary.
            details: Format kwargs for the template. Missing keys substitute to
                ``[key]`` rather than raising KeyError (defensive safe-map).

        Returns:
            A short (≤ 200 chars), grounded, second-person refusal narrative.
        """
        details = details or {}
        template = _TEMPLATES.get(reason_code, _FALLBACK_TEMPLATE)

        # Defensive: missing keys fall back to ``[key]`` rather than KeyError.
        class _SafeDict(dict):  # type: ignore[type-arg]
            def __missing__(self, k: str) -> str:
                return f"[{k}]"

        format_map = _SafeDict(details)
        format_map.setdefault("reason_code", reason_code)
        if "reason" in format_map:
            format_map["reason"] = _strip_wrapper(format_map["reason"])
        return template.format_map(format_map)
