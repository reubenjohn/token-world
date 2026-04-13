"""Shared fixtures for playtest tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def tmp_scenario_path(tmp_path: Path) -> Path:
    """Write a known-good YAML scenario to tmp_path and return the path."""
    data = {
        "name": "test_scenario",
        "description": "A test scenario for unit tests",
        "adversarial_rate": 0.1,
        "seed": 42,
        "turns": [
            {"action": "look around"},
            {"action": "pick up the lantern"},
            {"inject": "nonsense"},
            {"inject": "adversarial"},
            {"action": None},
        ],
    }
    scenario_path = tmp_path / "test_scenario.yaml"
    scenario_path.write_text(yaml.dump(data), encoding="utf-8")
    return scenario_path
