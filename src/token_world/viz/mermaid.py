"""Mermaid-safe label escaping."""

from __future__ import annotations

_ESCAPES = str.maketrans(
    {
        '"': "#quot;",
        "\n": "<br/>",
        "[": "&#91;",
        "]": "&#93;",
        "|": "&#124;",
    }
)


def escape_label(text: str, *, max_len: int = 60) -> str:
    """Escape characters that break Mermaid flowchart labels.

    Replaces ``" \\n [ ] |`` with Mermaid-safe HTML entities and truncates the
    result to ``max_len`` characters (appending ``…`` when truncated).
    """
    escaped = text.translate(_ESCAPES)
    if len(escaped) > max_len:
        escaped = escaped[: max_len - 1] + "…"
    return escaped
