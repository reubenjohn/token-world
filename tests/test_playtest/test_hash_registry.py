"""Tests for PromptHashRegistry (D-14 change detection, D-15 regression trigger)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from token_world.engine.classifier import Classifier
from token_world.engine.observer import Observer
from token_world.playtest import PromptHashRegistry

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


class FakeAgent:
    """Minimal fake ResidentAgent for hash testing."""

    def __init__(self, prompt_text: str = "default agent prompt"):
        self._prompt = prompt_text

    def system_prompt_text(self) -> str:
        return self._prompt


class FakeEngine:
    """Minimal fake SimulationEngine (not used directly by PromptHashRegistry)."""

    pass


# ---------------------------------------------------------------------------
# Task 1: classifier/observer expose system_prompt_text()
# ---------------------------------------------------------------------------


def test_classifier_exposes_system_prompt_text_classmethod() -> None:
    """Classifier.system_prompt_text() returns a non-empty string."""
    text = Classifier.system_prompt_text()
    assert isinstance(text, str)
    assert len(text) > 0


def test_observer_exposes_system_prompt_text_classmethod() -> None:
    """Observer.system_prompt_text() returns a non-empty string."""
    text = Observer.system_prompt_text()
    assert isinstance(text, str)
    assert len(text) > 0


# ---------------------------------------------------------------------------
# Task 1: PromptHashRegistry.compute_hashes()
# ---------------------------------------------------------------------------


def test_compute_hashes_returns_three_keys_with_sha256_values(tmp_path: Path) -> None:
    """compute_hashes returns dict with exactly 3 keys, each a 64-char hex SHA-256."""
    reg = PromptHashRegistry()
    engine = FakeEngine()
    agent = FakeAgent("some unique prompt")

    hashes = reg.compute_hashes(engine, agent)

    assert set(hashes.keys()) == {
        "classifier_system_prompt",
        "observer_system_prompt",
        "agent_system_prompt",
    }
    for v in hashes.values():
        assert re.fullmatch(r"[0-9a-f]{64}", v), f"Not a SHA-256 hex: {v!r}"


def test_compute_hashes_are_deterministic() -> None:
    """Two calls with the same engine/agent produce identical hashes."""
    reg = PromptHashRegistry()
    agent = FakeAgent("consistent prompt")
    engine = FakeEngine()

    h1 = reg.compute_hashes(engine, agent)
    h2 = reg.compute_hashes(engine, agent)

    assert h1 == h2


def test_compute_hashes_change_when_agent_personality_changes() -> None:
    """Different agent prompts yield different agent_system_prompt hash.

    classifier/observer hashes stay the same (class-level constants).
    """
    reg = PromptHashRegistry()
    engine = FakeEngine()
    agent_a = FakeAgent("personality A - curious wanderer")
    agent_b = FakeAgent("personality B - cautious merchant")

    h_a = reg.compute_hashes(engine, agent_a)
    h_b = reg.compute_hashes(engine, agent_b)

    # Agent prompt hashes differ
    assert h_a["agent_system_prompt"] != h_b["agent_system_prompt"]

    # Classifier and observer hashes are the same (they're class-level constants)
    assert h_a["classifier_system_prompt"] == h_b["classifier_system_prompt"]
    assert h_a["observer_system_prompt"] == h_b["observer_system_prompt"]


# ---------------------------------------------------------------------------
# Task 1: PromptHashRegistry.load() and save()
# ---------------------------------------------------------------------------


def test_load_returns_empty_dict_when_file_missing(tmp_path: Path) -> None:
    """load() returns {} when prompts.sha256.json does not exist — no crash."""
    reg = PromptHashRegistry()
    result = reg.load(tmp_path)
    assert result == {}


def test_save_writes_atomic_json_with_updated_at_timestamp(tmp_path: Path) -> None:
    """save() writes prompts.sha256.json with all hashes + updated_at ISO timestamp."""
    reg = PromptHashRegistry()
    hashes = {
        "classifier_system_prompt": "a" * 64,
        "observer_system_prompt": "b" * 64,
        "agent_system_prompt": "c" * 64,
    }
    reg.save(tmp_path, hashes)

    out_file = tmp_path / "prompts.sha256.json"
    assert out_file.exists()

    data = json.loads(out_file.read_text(encoding="utf-8"))
    # All hashes present
    for key, val in hashes.items():
        assert data[key] == val
    # updated_at is an ISO string
    assert "updated_at" in data
    assert isinstance(data["updated_at"], str)
    # Basic ISO format check: YYYY-MM-DDTHH:MM:SSZ
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", data["updated_at"])


# ---------------------------------------------------------------------------
# Task 1: PromptHashRegistry.detect_changes()
# ---------------------------------------------------------------------------


def test_detect_changes_returns_names_of_changed_prompts(tmp_path: Path) -> None:
    """detect_changes returns names of prompt keys whose hash changed from baseline."""
    reg = PromptHashRegistry()

    # Preseed baseline with 'old1' for classifier, same values for observer/agent
    baseline = {
        "classifier_system_prompt": "old1" + "x" * 60,
        "observer_system_prompt": "same" + "y" * 60,
        "agent_system_prompt": "same2" + "z" * 59,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (tmp_path / "prompts.sha256.json").write_text(json.dumps(baseline), encoding="utf-8")

    # Current hashes: classifier changed, observer/agent unchanged
    current = {
        "classifier_system_prompt": "new1" + "x" * 60,
        "observer_system_prompt": "same" + "y" * 60,
        "agent_system_prompt": "same2" + "z" * 59,
    }

    changed = reg.detect_changes(tmp_path, current)
    assert changed == ["classifier_system_prompt"]


def test_detect_changes_empty_list_when_no_baseline(tmp_path: Path) -> None:
    """detect_changes returns [] when no prompts.sha256.json exists (first run)."""
    reg = PromptHashRegistry()
    current = {
        "classifier_system_prompt": "a" * 64,
        "observer_system_prompt": "b" * 64,
        "agent_system_prompt": "c" * 64,
    }
    result = reg.detect_changes(tmp_path, current)
    assert result == []


def test_detect_changes_all_when_all_changed(tmp_path: Path) -> None:
    """detect_changes returns all three keys when all hashes differ from baseline."""
    reg = PromptHashRegistry()

    baseline = {
        "classifier_system_prompt": "old_c" + "x" * 59,
        "observer_system_prompt": "old_o" + "y" * 59,
        "agent_system_prompt": "old_a" + "z" * 59,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (tmp_path / "prompts.sha256.json").write_text(json.dumps(baseline), encoding="utf-8")

    current = {
        "classifier_system_prompt": "new_c" + "x" * 59,
        "observer_system_prompt": "new_o" + "y" * 59,
        "agent_system_prompt": "new_a" + "z" * 59,
    }

    changed = reg.detect_changes(tmp_path, current)
    assert set(changed) == {
        "classifier_system_prompt",
        "observer_system_prompt",
        "agent_system_prompt",
    }


# ---------------------------------------------------------------------------
# Task 2: regression trigger subprocess + history JSONL (tests 11-15)
# ---------------------------------------------------------------------------


def test_trigger_regression_runs_subprocess_with_expected_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """trigger_regression calls subprocess.run with the expected pytest args."""
    import subprocess

    captured_args = {}

    def fake_run(cmd, **kwargs):
        captured_args["cmd"] = cmd
        captured_args["kwargs"] = kwargs
        result = MagicMock()
        result.returncode = 0
        result.stdout = "1 passed in 0.5s"
        result.stderr = ""
        return result

    monkeypatch.setattr(subprocess, "run", fake_run)

    reg = PromptHashRegistry()
    reg.trigger_regression(tmp_path, ["agent_system_prompt"])

    assert captured_args["cmd"] == [
        "uv",
        "run",
        "pytest",
        "tests/test_regression/",
        "-m",
        "regression",
        "-x",
        "-q",
        "--tb=short",
    ]
    assert captured_args["kwargs"].get("timeout") == 600
    assert captured_args["kwargs"].get("text") is True
    assert captured_args["kwargs"].get("capture_output") is True


def test_trigger_regression_appends_to_history_jsonl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """trigger_regression appends a JSON line to regression-history.jsonl with correct fields."""
    import subprocess
    from subprocess import CompletedProcess

    def fake_run(cmd, **kwargs):
        return CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="4 passed, 0 failed in 2.3s",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    reg = PromptHashRegistry()
    reg.trigger_regression(tmp_path, ["agent_system_prompt"])

    history_path = tmp_path / "regression-history.jsonl"
    assert history_path.exists()

    lines = history_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    row = json.loads(lines[0])
    assert row["trigger"] == "prompt_hash_change"
    assert row["changed_prompts"] == ["agent_system_prompt"]
    assert row["exit_code"] == 0
    assert row["pass_count"] == 4
    assert row["fail_count"] == 0
    assert abs(row["duration_s"] - 2.3) < 0.01
    assert "timestamp_iso" in row
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", row["timestamp_iso"])


def test_trigger_regression_parses_pytest_summary_line(tmp_path: Path) -> None:
    """_parse_pytest_summary handles various stdout formats correctly."""
    from token_world.playtest.hash_registry import _parse_pytest_summary

    assert _parse_pytest_summary("4 passed, 2 failed in 3.5s") == (4, 2, 3.5)
    assert _parse_pytest_summary("4 passed in 2.1s") == (4, 0, 2.1)
    assert _parse_pytest_summary("2 failed in 1.0s") == (0, 2, 1.0)
    # Unparseable: returns (0, 0, 0.0)
    assert _parse_pytest_summary("something completely different") == (0, 0, 0.0)
    assert _parse_pytest_summary("") == (0, 0, 0.0)


def test_trigger_regression_handles_subprocess_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """trigger_regression catches TimeoutExpired and appends a row with exit_code=-1."""
    import subprocess

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 600)

    monkeypatch.setattr(subprocess, "run", fake_run)

    reg = PromptHashRegistry()
    # Should NOT raise
    entry = reg.trigger_regression(tmp_path, ["classifier_system_prompt"])

    assert entry["exit_code"] == -1
    assert entry["error"] == "timeout"

    # Still appended to history
    history_path = tmp_path / "regression-history.jsonl"
    assert history_path.exists()
    row = json.loads(history_path.read_text(encoding="utf-8").strip())
    assert row["exit_code"] == -1


def test_trigger_regression_appends_not_overwrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two trigger_regression calls produce 2 separate JSONL lines."""
    import subprocess
    from subprocess import CompletedProcess

    def fake_run(cmd, **kwargs):
        return CompletedProcess(args=cmd, returncode=0, stdout="1 passed in 0.1s", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    reg = PromptHashRegistry()
    reg.trigger_regression(tmp_path, ["agent_system_prompt"])
    reg.trigger_regression(tmp_path, ["observer_system_prompt"])

    history_path = tmp_path / "regression-history.jsonl"
    lines = history_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    # Both lines are valid JSON
    row1 = json.loads(lines[0])
    row2 = json.loads(lines[1])
    assert row1["changed_prompts"] == ["agent_system_prompt"]
    assert row2["changed_prompts"] == ["observer_system_prompt"]
