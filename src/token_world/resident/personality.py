"""Personality generation for resident agents (D-03, D-26).

PersonalityBundle: Pydantic model for the structured personality data.
PersonalityGenerator: One-shot Sonnet call to generate a personality bundle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

_TRAITS_MIN = 3
_TRAITS_MAX = 5


class PersonalityBundle(BaseModel):
    """Structured personality for a resident agent (D-03).

    Fields match the D-26 JSON schema produced by PersonalityGenerator.
    Stored as a dict property on the agent's graph node (JSON-serializable
    per CLAUDE.md property-value convention) and mirrored in agent_sessions.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    archetype: str
    traits: list[str]
    backstory: str
    speech_style: str

    @field_validator("traits")
    @classmethod
    def _validate_traits(cls, v: list[str]) -> list[str]:
        if not (_TRAITS_MIN <= len(v) <= _TRAITS_MAX):
            raise ValueError(
                f"traits must have between {_TRAITS_MIN} and {_TRAITS_MAX} items, got {len(v)}"
            )
        return v


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

_D26_PROMPT_TEMPLATE = (
    "Generate a unique character personality for a resident of {universe_description}. "
    "Return JSON matching: "
    "{{name: string, archetype: string, traits: array of 3-5 adjectives, "
    "backstory: string (2-3 sentences), speech_style: string}}. "
    "Make traits internally consistent. Do NOT include any prose outside the JSON."
)


@dataclass
class PersonalityGenerator:
    """One-shot Sonnet call that returns a validated PersonalityBundle (D-03, D-26)."""

    def generate(
        self,
        universe_description: str,
        *,
        client: Any,
        model: str = "claude-sonnet-4-5",
    ) -> PersonalityBundle:
        """Generate a personality bundle via a single Sonnet call.

        Retries once on malformed JSON or validation error. Raises ValueError
        after both attempts fail.
        """
        prompt = _D26_PROMPT_TEMPLATE.format(universe_description=universe_description)
        last_error: Exception | None = None

        for _ in range(2):
            response = client.messages.create(
                model=model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content
            if not content:
                raise ValueError("LLM returned empty response in PersonalityGenerator.generate()")
            raw_text = content[0].text

            try:
                json_text = _extract_json(raw_text)
                bundle = PersonalityBundle.model_validate_json(json_text)
                return bundle
            except Exception as exc:
                last_error = exc

        raise ValueError(f"personality generation failed after retry: {last_error}")


def _extract_json(text: str) -> str:
    """Extract first {...} JSON block from text, tolerant of surrounding prose.

    Same pattern as classifier.py: uses re.search to find the JSON substring.
    """
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"No JSON object found in text: {text!r}")
    return match.group(0)
