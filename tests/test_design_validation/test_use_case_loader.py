"""Use-case loader edge cases (framing, line-ending tolerance, errors)."""

from __future__ import annotations

from pathlib import Path

import pytest

from token_world.use_cases import load_use_case

VALID_FRONTMATTER = (
    "id: UC-S01\n"
    "category: spatial\n"
    "title: example\n"
    "status: draft\n"
    "setup:\n"
    "  graph_builder: example\n"
    "actions: []\n"
    "expected_observations: []\n"
    "gaps: []\n"
)


def _write(path: Path, frontmatter: str, body: str, *, line_ending: str) -> None:
    text = f"---\n{frontmatter}---\n{body}"
    if line_ending != "\n":
        text = text.replace("\n", line_ending)
    path.write_bytes(text.encode("utf-8"))


def test_loader_accepts_lf_frontmatter(tmp_path: Path) -> None:
    path = tmp_path / "uc.md"
    _write(path, VALID_FRONTMATTER, "body text\n", line_ending="\n")
    fm, body = load_use_case(path)
    assert fm["id"] == "UC-S01"
    assert "body text" in body


def test_loader_accepts_crlf_frontmatter(tmp_path: Path) -> None:
    """REVIEW M-04 regression: CRLF-framed files must load cleanly."""
    path = tmp_path / "uc_crlf.md"
    _write(path, VALID_FRONTMATTER, "body text\n", line_ending="\r\n")
    fm, body = load_use_case(path)
    assert fm["id"] == "UC-S01"
    assert "body text" in body


def test_loader_accepts_cr_frontmatter(tmp_path: Path) -> None:
    """Bare CR (classic-Mac-style) line endings also load."""
    path = tmp_path / "uc_cr.md"
    _write(path, VALID_FRONTMATTER, "body text\n", line_ending="\r")
    fm, body = load_use_case(path)
    assert fm["id"] == "UC-S01"
    assert "body text" in body


def test_loader_rejects_missing_frontmatter(tmp_path: Path) -> None:
    path = tmp_path / "plain.md"
    path.write_text("no frontmatter here\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing YAML frontmatter"):
        load_use_case(path)


def test_loader_rejects_unclosed_frontmatter(tmp_path: Path) -> None:
    path = tmp_path / "open.md"
    path.write_text("---\nid: UC-S01\nno-closing-delim here\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no closing '---'"):
        load_use_case(path)
