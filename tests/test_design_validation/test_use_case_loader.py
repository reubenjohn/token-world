"""Use-case loader edge cases (framing, line-ending tolerance, errors)."""

from __future__ import annotations

from pathlib import Path

import pytest

from token_world.use_cases import load_use_case
from token_world.use_cases.loader import VALID_ASSERTION_KINDS, validate_frontmatter

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


# ---------------------------------------------------------------------------
# UAT Test 8 regression — graph_assertion kind whitelist enforcement (03-15)
# ---------------------------------------------------------------------------


def _minimal_valid_fm(**overrides: object) -> dict[str, object]:
    """Return a frontmatter dict that validate_frontmatter accepts.

    Tests layer their own ``expected_observations`` / ``setup`` / ``actions``
    on top via overrides.
    """
    base: dict[str, object] = {
        "id": "UC-S99",
        "category": "spatial",
        "title": "synthetic",
        "status": "draft",
        "setup": {"graph_builder": "def build(b): pass"},
        "actions": [],
        "expected_observations": [],
        "gaps": [],
    }
    base.update(overrides)
    return base


def test_valid_assertion_kinds_contains_exactly_six() -> None:
    assert (
        frozenset(
            {
                "has_node",
                "has_edge",
                "has_property",
                "property_equals",
                "not_has_edge",
                "not_has_property",
            }
        )
        == VALID_ASSERTION_KINDS
    )


@pytest.mark.parametrize("kind", sorted(VALID_ASSERTION_KINDS))
def test_every_valid_kind_passes(kind: str) -> None:
    fm = _minimal_valid_fm(
        expected_observations=[{"graph_assertions": [{"kind": kind, "node": "x"}]}]
    )
    errors = validate_frontmatter(fm, source="synthetic.md")
    assert not errors, f"valid kind {kind!r} rejected: {errors}"


@pytest.mark.parametrize(
    "bad_kind",
    ["totally_fake_kind", "HAS_EDGE", "has_attribute", "", "property_eq", None],
)
def test_invalid_kind_rejected(bad_kind: object) -> None:
    fm = _minimal_valid_fm(
        expected_observations=[{"graph_assertions": [{"kind": bad_kind, "node": "x"}]}]
    )
    errors = validate_frontmatter(fm, source="synthetic.md")
    assert errors, f"invalid kind {bad_kind!r} accepted silently"
    joined = "\n".join(errors)
    assert "kind" in joined
    # The offending value should be referenced in the error (repr form preferred).
    assert repr(bad_kind) in joined or str(bad_kind) in joined


def test_invalid_kind_in_setup_graph_assertions_rejected() -> None:
    """Defense-in-depth: setup.graph_assertions is also checked."""
    fm = _minimal_valid_fm(
        setup={
            "graph_builder": "def build(b): pass",
            "graph_assertions": [{"kind": "totally_fake_kind"}],
        }
    )
    errors = validate_frontmatter(fm, source="synthetic.md")
    assert errors
    assert any("setup.graph_assertions" in e for e in errors)


def test_invalid_kind_in_actions_graph_assertions_rejected() -> None:
    """Defense-in-depth: actions[*].graph_assertions is also checked."""
    fm = _minimal_valid_fm(actions=[{"graph_assertions": [{"kind": "totally_fake_kind"}]}])
    errors = validate_frontmatter(fm, source="synthetic.md")
    assert errors
    assert any("actions[0].graph_assertions" in e for e in errors)


def test_missing_kind_key_rejected() -> None:
    """An assertion without a ``kind`` field is rejected (kind=None not in set)."""
    fm = _minimal_valid_fm(expected_observations=[{"graph_assertions": [{"node": "x"}]}])
    errors = validate_frontmatter(fm, source="synthetic.md")
    assert errors
