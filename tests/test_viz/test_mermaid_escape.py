"""escape_label() must neutralize Mermaid-hostile characters."""

from __future__ import annotations

import pytest

from token_world.viz import escape_label


@pytest.mark.parametrize(
    "raw,needle",
    [
        ('alice"foo', "#quot;"),
        ("multi\nline", "<br/>"),
        ("[bracket]", "&#91;"),
        ("[bracket]", "&#93;"),
        ("pipe|label", "&#124;"),
    ],
)
def test_escape_replaces_dangerous_char(raw: str, needle: str) -> None:
    assert needle in escape_label(raw, max_len=100)


def test_truncates_long_labels() -> None:
    long = "x" * 200
    out = escape_label(long, max_len=60)
    assert len(out) == 60
    assert out.endswith("…")


def test_leaves_safe_strings_alone() -> None:
    assert escape_label("alice hp=100", max_len=60) == "alice hp=100"


@pytest.mark.parametrize(
    "raw,max_len",
    [
        ("|" * 20, 60),  # dense pipe entities
        ("[" * 20, 60),  # dense bracket entities
        ('"' * 20, 60),  # dense quote entities
        ("\n" * 20, 60),  # dense <br/> entities
    ],
)
def test_truncation_never_produces_malformed_entity(raw: str, max_len: int) -> None:
    """REVIEW M-01 regression: truncation must not cut HTML entities mid-sequence."""
    out = escape_label(raw, max_len=max_len)
    # If an ampersand appears, it must be followed by a terminating ';' in the
    # remainder of the string (the ellipsis terminates, so we trim it first).
    body = out.rstrip("…")
    # No bare '&#' without a following ';' before end-of-body.
    idx = 0
    while True:
        amp = body.find("&", idx)
        if amp == -1:
            break
        # Find next ';' or newline equivalent
        semi = body.find(";", amp)
        assert semi != -1, f"truncation produced unterminated '&' entity: {out!r}"
        idx = semi + 1
    # No bare '<' without matching '>' either (<br/>)
    idx = 0
    while True:
        lt = body.find("<", idx)
        if lt == -1:
            break
        gt = body.find(">", lt)
        assert gt != -1, f"truncation produced unterminated '<' tag: {out!r}"
        idx = gt + 1


@pytest.mark.parametrize(
    "payload",
    [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<iframe src=//evil></iframe>",
        "<b>bold</b>",
        "a < b and c > d",
    ],
)
def test_escape_neutralises_angle_brackets(payload: str) -> None:
    """UAT #7 regression: raw < and > must be entity-escaped.

    The only <...> token permitted in the output is the literal <br/>
    inserted BY escape_label in response to a real newline in the input.
    """
    out = escape_label(payload, max_len=200)
    assert "<script" not in out, f"raw <script survived: {out!r}"
    assert "<img" not in out, f"raw <img survived: {out!r}"
    assert "<iframe" not in out, f"raw <iframe survived: {out!r}"
    assert "<b>" not in out, f"raw <b> survived: {out!r}"
    # No raw < > at all (except any <br/> which we assert separately)
    residue = out.replace("<br/>", "")
    assert "<" not in residue, f"raw '<' survived: {out!r}"
    assert ">" not in residue, f"raw '>' survived: {out!r}"


def test_escape_preserves_newline_as_br() -> None:
    """Newlines in input -> literal <br/> in output (the ONE legal <> token)."""
    out = escape_label("line1\nline2", max_len=100)
    assert "<br/>" in out
    # The <br/> is the only < in the output
    assert out.count("<") == 1
    assert out.count(">") == 1


def test_attacker_supplied_br_is_escaped() -> None:
    """A <br/> token already present in the input must be neutralised;
    only our injected <br/> (from real \\n) is legal."""
    out = escape_label("safe<br/>attacker", max_len=100)
    # Attacker's <br/> must be entity-escaped -- no literal <br/> at all
    # (since input had no \n, escape_label did not inject one).
    assert "<br/>" not in out, f"attacker <br/> survived: {out!r}"
    assert "&lt;br/&gt;" in out
