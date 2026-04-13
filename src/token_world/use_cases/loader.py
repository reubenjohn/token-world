"""Use-case file loader: splits YAML frontmatter from markdown body and validates shape."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REQUIRED_KEYS = {
    "id",
    "category",
    "title",
    "status",
    "setup",
    "actions",
    "expected_observations",
    "gaps",
}
VALID_CATEGORIES = {"spatial", "social", "resource", "environmental", "edge-case"}
VALID_STATUSES = {"draft", "reviewed", "locked"}
ID_PATTERN = re.compile(r"^UC-[SOVRE]\d{2}$")
GAP_KEYS = {"layer", "severity", "summary", "proposed_fix"}
VALID_LAYERS = {"graph", "mechanic", "engine"}
VALID_SEVERITIES = {"address-now", "defer", "out-of-scope"}


def load_use_case(path: Path) -> tuple[dict[str, Any], str]:
    """Return ``(frontmatter_dict, markdown_body)``.

    Raises ``ValueError`` if the file is missing frontmatter or the YAML is
    invalid.
    """
    raw = path.read_text(encoding="utf-8")
    # Normalise line endings so use-case files authored on Windows/VSCode
    # (CRLF or bare CR) load the same way as files authored on Unix.
    # REVIEW M-04: the frontmatter framing check is strict on "---\n", so we
    # pre-normalise before inspecting it. yaml.safe_load is CRLF-tolerant.
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing YAML frontmatter")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError(f"{path}: malformed frontmatter (no closing '---')")
    _, fm_text, body = parts
    fm = yaml.safe_load(fm_text) or {}
    if not isinstance(fm, dict):
        raise ValueError(f"{path}: frontmatter must be a mapping")
    return fm, body


def validate_frontmatter(fm: dict[str, Any], *, source: str = "<unknown>") -> list[str]:
    """Return a list of human-readable validation errors (empty = valid)."""
    errors: list[str] = []
    missing = REQUIRED_KEYS - fm.keys()
    if missing:
        errors.append(f"{source}: missing required keys: {sorted(missing)}")
    if "id" in fm and not ID_PATTERN.match(str(fm["id"])):
        errors.append(f"{source}: id {fm['id']!r} does not match UC-[SOVRE]NN")
    if fm.get("category") not in VALID_CATEGORIES:
        errors.append(
            f"{source}: category {fm.get('category')!r} not in {sorted(VALID_CATEGORIES)}"
        )
    if fm.get("status") not in VALID_STATUSES:
        errors.append(f"{source}: status {fm.get('status')!r} not in {sorted(VALID_STATUSES)}")
    setup = fm.get("setup")
    if not isinstance(setup, dict) or "graph_builder" not in setup:
        errors.append(f"{source}: setup must be dict with 'graph_builder' key")
    for idx, gap in enumerate(fm.get("gaps", []) or []):
        if not isinstance(gap, dict):
            errors.append(f"{source}: gaps[{idx}] must be a mapping")
            continue
        gap_missing = GAP_KEYS - gap.keys()
        if gap_missing:
            errors.append(f"{source}: gaps[{idx}] missing keys {sorted(gap_missing)}")
        if gap.get("layer") not in VALID_LAYERS:
            errors.append(f"{source}: gaps[{idx}].layer {gap.get('layer')!r} invalid")
        if gap.get("severity") not in VALID_SEVERITIES:
            errors.append(f"{source}: gaps[{idx}].severity {gap.get('severity')!r} invalid")
    return errors
