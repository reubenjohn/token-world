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
