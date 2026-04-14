"""Prompt-hash registry for D-14 change detection and D-15 auto-regression trigger.

Satisfies:
- TEST-05: system prompt change detection
- AUTO-07: prompt/instruction change triggers automated regression validation
- D-14: SHA-256 hashing of the three system prompts (classifier, observer, agent)
- D-15: regression subprocess invocation + regression-history.jsonl logging
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from token_world.engine.classifier import Classifier
from token_world.engine.observer import Observer
from token_world.mechanic.diagnostics import _atomic_write_json

logger = logging.getLogger(__name__)

_HASH_FILE = "prompts.sha256.json"

# ---------------------------------------------------------------------------
# Pytest summary line parser (D-15)
# ---------------------------------------------------------------------------

_PASSED_RE = re.compile(r"(?P<passed>\d+)\s+passed")
_FAILED_RE = re.compile(r"(?P<failed>\d+)\s+failed")
_DURATION_RE = re.compile(r"in\s+(?P<duration>[\d.]+)s")


def _parse_pytest_summary(stdout: str) -> tuple[int, int, float]:
    """Extract (passed, failed, duration_s) from pytest's last summary line.

    Handles common formats:
    - "4 passed, 2 failed in 3.5s"
    - "4 passed in 2.1s"
    - "2 failed in 1.0s"
    - Unparseable -> (0, 0, 0.0)
    """
    # Filter to candidate summary lines
    lines = [
        line
        for line in stdout.strip().splitlines()
        if "passed" in line or "failed" in line or "no tests ran" in line or " in " in line
    ]
    if not lines:
        return (0, 0, 0.0)
    summary = lines[-1]

    # Use independent regexes so each count is found regardless of ordering
    m_passed = _PASSED_RE.search(summary)
    m_failed = _FAILED_RE.search(summary)
    m_duration = _DURATION_RE.search(summary)

    if not m_duration:
        return (0, 0, 0.0)

    passed = int(m_passed.group("passed")) if m_passed else 0
    failed = int(m_failed.group("failed")) if m_failed else 0
    try:
        duration = float(m_duration.group("duration"))
    except (ValueError, TypeError):
        duration = 0.0
    return (passed, failed, duration)


# ---------------------------------------------------------------------------
# PromptHashRegistry
# ---------------------------------------------------------------------------


class PromptHashRegistry:
    """Compute, store, and compare SHA-256 hashes of the three system prompts.

    Satisfies D-14 (change detection) and orchestrates D-15 (regression trigger).

    The three tracked prompts are:
    - classifier_system_prompt: Classifier._SYSTEM_PROMPT (Haiku action classifier)
    - observer_system_prompt: Observer._SYSTEM_PROMPT (Sonnet observation synthesiser)
    - agent_system_prompt: ResidentAgent.system_prompt_text() (personality-assembled)

    Only hashes are stored — never the raw prompt text (D-14 privacy).
    """

    @staticmethod
    def _sha256(text: str) -> str:
        """Return the full SHA-256 hex digest of the UTF-8 encoded text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def compute_hashes(self, engine: object, agent: object) -> dict[str, str]:
        """Return {key: sha256} for the three system prompts.

        Args:
            engine: SimulationEngine instance (used to reach Classifier/Observer
                    class-level prompts — the engine parameter is accepted for
                    forward-compatibility but the prompts are class constants).
            agent: ResidentAgent instance (calls agent.system_prompt_text()).

        Returns:
            Dict with exactly three keys: classifier_system_prompt,
            observer_system_prompt, agent_system_prompt.
        """
        return {
            "classifier_system_prompt": self._sha256(Classifier.system_prompt_text()),
            "observer_system_prompt": self._sha256(Observer.system_prompt_text()),
            "agent_system_prompt": self._sha256(agent.system_prompt_text()),  # type: ignore[attr-defined]
        }

    def load(self, universe_dir: Path) -> dict[str, str]:
        """Read stored hashes from universe_dir/prompts.sha256.json.

        Returns {} if the file is missing or malformed (no crash — first run).
        The 'updated_at' key is stripped from the returned dict.
        """
        path = universe_dir / _HASH_FILE
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        # Strip 'updated_at' — not a hash
        return {k: v for k, v in data.items() if k != "updated_at"}

    def save(self, universe_dir: Path, hashes: dict[str, str]) -> Path:
        """Write hashes + updated_at timestamp to universe_dir/prompts.sha256.json atomically.

        Uses _atomic_write_json to prevent readers from seeing partial writes.

        Returns:
            Path to the written file.
        """
        payload = {
            **hashes,
            "updated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        out_path = universe_dir / _HASH_FILE
        _atomic_write_json(out_path, payload)
        return out_path

    def detect_changes(self, universe_dir: Path, current: dict[str, str]) -> list[str]:
        """Return names of prompt keys whose hash changed since the stored baseline.

        Returns:
            Empty list if no baseline exists (first run = not a change).
            List of changed key names otherwise.
        """
        baseline = self.load(universe_dir)
        if not baseline:
            return []  # no baseline = no changes (first run)
        return [k for k, v in current.items() if baseline.get(k) != v]

    def trigger_regression(self, universe_dir: Path, changed_prompts: list[str]) -> dict:
        """Run pytest regression suite and append result to universe/regression-history.jsonl.

        Invokes: uv run pytest tests/test_regression/ -m regression -x -q --tb=short
        Timeout: 600s. Catches all exceptions — never crashes the caller.

        The result is always appended to regression-history.jsonl regardless of
        exit code (exit_code=1 from known gaps is informative, not an error).

        Args:
            universe_dir: Universe root directory (for history file path).
            changed_prompts: Names of prompts that triggered this run.

        Returns:
            The dict appended to the JSONL file.
        """
        cmd = [
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
        entry: dict = {
            "timestamp_iso": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger": "prompt_hash_change",
            "changed_prompts": list(changed_prompts),
            "exit_code": -1,
            "pass_count": 0,
            "fail_count": 0,
            "duration_s": 0.0,
            "error": None,
        }
        # Derive project root: hash_registry.py is at src/token_world/playtest/,
        # so .parents[3] walks up: playtest/ -> token_world/ -> src/ -> project root
        _project_root = Path(__file__).parents[3]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
                cwd=_project_root,
            )
            entry["exit_code"] = result.returncode
            passed, failed, duration = _parse_pytest_summary(result.stdout)
            entry["pass_count"] = passed
            entry["fail_count"] = failed
            entry["duration_s"] = duration
            logger.info(
                "Regression run complete: exit=%d passed=%d failed=%d duration=%.1fs",
                result.returncode,
                passed,
                failed,
                duration,
            )
        except subprocess.TimeoutExpired:
            entry["error"] = "timeout"
            logger.warning("Regression run timed out after 600s")
        except FileNotFoundError as exc:
            entry["error"] = f"uv/pytest not available: {exc}"
            logger.warning("Regression run failed: %s", exc)
        except Exception as exc:  # defensive: never crash the runner
            entry["error"] = f"{type(exc).__name__}: {exc}"
            logger.warning("Regression run failed unexpectedly: %s", exc)

        # Append JSONL row (append mode, never overwrite)
        history_path = universe_dir / "regression-history.jsonl"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        return entry
