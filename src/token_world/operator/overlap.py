"""Mechanic overlap detector (REQ-V12-EMERGE-01).

Computes a similarity score between a proposed mechanic spec (verb + watches)
and the existing registry. Used by the yield-handler subagent to decide whether
to author a new mechanic or edit an existing one.

Score = max over all existing mechanics of max(verb_jaccard, watches_jaccard).
Threshold 0.7 means "strongly prefer editing existing mechanic".
"""

from __future__ import annotations

from typing import Any


def _tokenize(text: str) -> frozenset[str]:
    """Split text into lowercase word tokens."""
    return frozenset(text.lower().split())


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard similarity between two token sets. Returns 0.0 for both-empty."""
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def compute_overlap(
    proposed_verb: str,
    proposed_watches: set[str] | list[str],
    registry_mechanics: list[Any],
) -> float:
    """Return the maximum overlap score [0.0, 1.0] between the proposed spec
    and any existing mechanic in the registry.

    Args:
        proposed_verb: The classified action verb (e.g. "pet", "pick up").
        proposed_watches: Properties/nodes the proposed mechanic would read.
        registry_mechanics: List of MechanicInfo (or any object with .id and
            optionally .verb / .watches attributes).

    Returns:
        Max overlap score. 0.0 means no registry match; 1.0 means exact match.
    """
    if not registry_mechanics:
        return 0.0

    proposed_verb_tokens = _tokenize(proposed_verb)
    proposed_watches_set = frozenset(proposed_watches)
    max_score = 0.0

    for mech in registry_mechanics:
        # Verb jaccard — use .id as fallback verb proxy if no .verb field
        mech_verb = getattr(mech, "verb", None) or getattr(mech, "id", "") or ""
        verb_score = _jaccard(proposed_verb_tokens, _tokenize(str(mech_verb)))

        # Watches jaccard — skip if mechanic has no watches (T-17-04-04)
        mech_watches = getattr(mech, "watches", None)
        if mech_watches:
            watches_score = _jaccard(proposed_watches_set, frozenset(mech_watches))
        else:
            watches_score = 0.0

        mech_score = max(verb_score, watches_score)
        if mech_score > max_score:
            max_score = mech_score

    return max_score


def compute_overlap_report(
    proposed_verb: str,
    proposed_watches: set[str] | list[str],
    registry_mechanics: list[Any],
    *,
    threshold: float = 0.7,
    top_n: int = 3,
) -> str:
    """Return a human-readable overlap report for prompt injection.

    Lists the top N mechanics by overlap score, flags whether the threshold
    is exceeded, and gives the "prefer edit-existing" recommendation.

    Args:
        proposed_verb: The classified action verb.
        proposed_watches: Properties/nodes the proposed mechanic would read.
        registry_mechanics: List of MechanicInfo objects.
        threshold: Score threshold above which edit-existing is recommended.
        top_n: Number of top mechanics to include in the report.

    Returns:
        Multi-line string suitable for embedding in a prompt.
    """
    if not registry_mechanics:
        return "Overlap check: registry is empty — author new mechanic."

    proposed_verb_tokens = _tokenize(proposed_verb)
    proposed_watches_set = frozenset(proposed_watches)
    scores: list[tuple[float, str]] = []

    for mech in registry_mechanics:
        mech_verb = getattr(mech, "verb", None) or getattr(mech, "id", "") or ""
        verb_score = _jaccard(proposed_verb_tokens, _tokenize(str(mech_verb)))
        mech_watches = getattr(mech, "watches", None)
        watches_score = _jaccard(proposed_watches_set, frozenset(mech_watches or []))
        scores.append((max(verb_score, watches_score), getattr(mech, "id", str(mech))))

    scores.sort(reverse=True)
    top = scores[:top_n]
    max_score = top[0][0] if top else 0.0

    lines: list[str] = [f"Overlap report (proposed verb: {proposed_verb!r}):"]
    for score, mid in top:
        lines.append(f"  {mid}: {score:.2f}")
    if max_score >= threshold:
        lines.append(
            f"RECOMMENDATION: overlap {max_score:.2f} >= {threshold}"
            f" — PREFER editing existing mechanic '{top[0][1]}'."
        )
    else:
        lines.append(
            f"Overlap {max_score:.2f} < {threshold} — authoring new mechanic is appropriate."
        )
    return "\n".join(lines)
