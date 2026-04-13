"""Mermaid-safe label escaping."""

from __future__ import annotations

# Order matters: entity-escape all angle brackets and other hostile chars
# BEFORE we introduce our own literal '<br/>' for newlines. This prevents
# an attacker-supplied label like '<script>' from surviving the escape.
_ENTITY_ESCAPES = str.maketrans(
    {
        '"': "#quot;",
        "[": "&#91;",
        "]": "&#93;",
        "|": "&#124;",
        "<": "&lt;",
        ">": "&gt;",
    }
)

_NEWLINE_TOKEN = "<br/>"


def escape_label(text: str, *, max_len: int = 60) -> str:
    """Escape characters that break Mermaid flowchart labels.

    Steps:
      1. Entity-escape ``" [ ] | < >`` so attacker-controlled HTML/Mermaid
         syntax in ``text`` cannot survive.
      2. Replace each ``\\n`` with the literal token ``<br/>`` -- this is the
         ONLY ``<br/>`` that appears in output; any ``<br/>`` in the input has
         already been escaped to ``&lt;br/&gt;`` in step 1.
      3. Truncate to ``max_len``, walking the cut backwards off any
         incomplete ``&...;`` entity or ``<...>`` tag so the result never
         contains a malformed fragment (M-01 invariant).
    """
    escaped = text.translate(_ENTITY_ESCAPES).replace("\n", _NEWLINE_TOKEN)
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
