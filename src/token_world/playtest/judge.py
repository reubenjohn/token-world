"""Optional Sonnet-based playtest judge (D-13, TEST-04).

Evaluates a completed playtest transcript across three subjective dimensions
scored 0.0–1.0. Invoked via --judge flag on `token-world playtest`.

Does NOT re-run the engine — only evaluates the existing report transcript.
Does NOT score groundedness (that is deterministic per D-12; judge scores only
subjective dimensions: coherence, personality_consistency, world_rule_adherence).

Cost: ~$0.01/20 turns. Opt-in only (--judge flag). Not used in CI.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Judge prompt template
# ---------------------------------------------------------------------------

_JUDGE_PROMPT_TEMPLATE = """\
You are a simulation quality auditor. Evaluate the following resident-agent \
playtest transcript across three dimensions, each scored 0.0 to 1.0:

1. coherence - do agent actions make sense in sequence?
2. personality_consistency - does the agent stay in character?
3. world_rule_adherence - do actions respect the stated world rules?

Transcript:
{transcript}

Return JSON exactly matching:
{{
  "scores": {{
    "coherence": <0..1 float>,
    "personality_consistency": <0..1 float>,
    "world_rule_adherence": <0..1 float>
  }},
  "rationale": "<1-3 sentence explanation>"
}}"""

_DEFAULT_MODEL = "claude-sonnet-4-5"


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _judge_prompt_hash() -> str:
    """Return SHA-256 hex of the judge prompt template."""
    return hashlib.sha256(_JUDGE_PROMPT_TEMPLATE.encode("utf-8")).hexdigest()


def build_transcript(report: Any) -> str:
    """Concatenate turns into a readable transcript string.

    Args:
        report: PlaytestReport instance (or any object with a .turns iterable
                whose items have .turn_number, .action_text, .observation_text).

    Returns:
        Multi-line string with one block per turn.
    """
    lines: list[str] = []
    for t in report.turns:
        lines.append(f"[Turn {t.turn_number}] Action: {t.action_text}")
        lines.append(f"Observation: {t.observation_text or '(no observation)'}")
        lines.append("")
    return "\n".join(lines)


def evaluate(
    report: Any,
    client: Any,
    *,
    model: str = _DEFAULT_MODEL,
) -> dict[str, Any]:
    """Run one Sonnet call over the transcript; return parsed judge dict.

    On success returns:
        {"scores": {"coherence": float, ...}, "rationale": str,
         "model": str, "prompt_hash": str}

    On error returns:
        {"error": str, "model": str, "prompt_hash": str}
        (optionally "raw": str for malformed-response errors)

    Never raises — callers (CLI) expect this to always return a dict.

    Args:
        report: PlaytestReport instance.
        client: anthropic.Anthropic instance (or test double).
        model: Model string; default "claude-sonnet-4-5" per D-13.
    """
    transcript = build_transcript(report)
    prompt = _JUDGE_PROMPT_TEMPLATE.format(transcript=transcript)
    ph = _judge_prompt_hash()

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text

        # Extract the first {...} block from the response
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            logger.warning("Judge response contained no JSON block")
            return {
                "error": "no JSON block",
                "raw": text,
                "model": model,
                "prompt_hash": ph,
            }

        parsed = json.loads(match.group(0))
        return {
            "scores": parsed.get("scores", {}),
            "rationale": parsed.get("rationale", ""),
            "model": model,
            "prompt_hash": ph,
        }

    except json.JSONDecodeError as exc:
        logger.warning("Judge response JSON parse failed: %s", exc)
        return {
            "error": f"malformed response: {exc}",
            "model": model,
            "prompt_hash": ph,
        }
    except (AttributeError, KeyError, IndexError) as exc:
        logger.warning("Judge response structure unexpected: %s", exc)
        return {
            "error": f"malformed response: {exc}",
            "model": model,
            "prompt_hash": ph,
        }
    except Exception as exc:  # network errors, etc.
        logger.warning("Judge call failed: %s: %s", type(exc).__name__, exc)
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "model": model,
            "prompt_hash": ph,
        }


def prompt_hash() -> str:
    """Expose the judge prompt template SHA-256 hash for reporting / change-detection."""
    return _judge_prompt_hash()
