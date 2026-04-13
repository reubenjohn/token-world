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

    Truncation is performed on the *escaped* string, but the cut point is
    walked backwards off any incomplete escape entity (``&#NN...;`` / ``<br/>``)
    so the output never contains a malformed fragment like ``&#12…``.
    """
    escaped = text.translate(_ESCAPES)
    if len(escaped) > max_len:
        cut = max_len - 1
        # If the cut lands inside an unterminated entity, walk back to before
        # the opening sentinel. We look at the most recent opener (``&`` or
        # ``<``) in the kept prefix; if no corresponding terminator (``;`` or
        # ``>``) follows it, retreat the cut to just before the opener.
        prefix = escaped[:cut]
        amp = prefix.rfind("&")
        lt = prefix.rfind("<")
        opener = max(amp, lt)
        if opener != -1:
            closer_char = ";" if opener == amp else ">"
            if closer_char not in escaped[opener:cut]:
                cut = opener
        escaped = escaped[:cut] + "…"
    return escaped
