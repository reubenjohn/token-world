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
    "inventory_full": ("You try to pick up {target}, but your hands and pack are already full."),
    "locked": ("You try, but {target} is locked."),
    "blocked": ("You try, but {reason} is in the way."),
}

_FALLBACK_TEMPLATE = "You try, but the attempt fails — {reason_code}."


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
        return template.format_map(format_map)
