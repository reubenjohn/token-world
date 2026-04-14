#!/usr/bin/env python3
"""Refresh <universe>/prompts.sha256.json baseline to match current source prompts.

Use after reverting an experimental prompt modification (e.g., during UAT) to
prevent the next playtest run from spuriously re-triggering a regression event.

Usage: uv run python scripts/update_prompt_hashes.py <universe_slug>

Example:
    # After reverting a classifier prompt edit used for UAT 2:
    uv run python scripts/update_prompt_hashes.py uatworld
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from token_world.engine.classifier import Classifier
from token_world.engine.observer import Observer


def resolve_universe_path(slug: str) -> Path:
    xdg_data = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(xdg_data) / "token_world" / "universes" / slug


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def update(slug: str) -> int:
    universe_path = resolve_universe_path(slug)
    if not universe_path.is_dir():
        print(f"Universe not found: {universe_path}", file=sys.stderr)
        return 1

    target = universe_path / "prompts.sha256.json"
    existing: dict[str, str] = {}
    if target.exists():
        existing = json.loads(target.read_text())

    baseline = {
        # Agent prompt is personality-bound (instance-method). Preserve whatever
        # hash the registry last computed on a real run — do not recompute here.
        "agent_system_prompt": existing.get("agent_system_prompt", ""),
        "classifier_system_prompt": _sha256(Classifier.system_prompt_text()),
        "observer_system_prompt": _sha256(Observer.system_prompt_text()),
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    target.write_text(json.dumps(baseline, indent=2) + "\n")
    print(f"Updated {target}")
    for key, value in baseline.items():
        if key != "updated_at":
            print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: update_prompt_hashes.py <universe_slug>", file=sys.stderr)
        sys.exit(2)
    sys.exit(update(sys.argv[1]))
