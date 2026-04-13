"""EngineConfig -- per-universe engine parameters loaded from universe.yaml.

Per CONTEXT D-03 + D-07 + D-19. All keys have defaults; missing or malformed
YAML is a soft failure (warn-to-stderr, use defaults) to avoid blocking the
engine on a config typo.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EngineConfig:
    """Per-universe engine parameters."""

    max_chain_depth: int = 10
    classifier_min_confidence: float = 0.6
    universe_seed: int = 0  # 0 = unseeded; effectively-deterministic fallback


def load_engine_config(universe_path: Path) -> EngineConfig:
    """Load engine config from ``<universe>/universe.yaml`` or return defaults."""
    config_path = universe_path / "universe.yaml"
    if not config_path.exists():
        return EngineConfig()
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        logger.warning("Malformed universe.yaml at %s: %s — using defaults", config_path, e)
        return EngineConfig()
    if not isinstance(raw, dict):
        logger.warning("universe.yaml root is not a mapping at %s — using defaults", config_path)
        return EngineConfig()

    engine_section = raw.get("engine", {}) if isinstance(raw.get("engine"), dict) else {}
    universe_seed = raw.get("universe_seed", 0)
    if not isinstance(universe_seed, int):
        logger.warning("universe_seed in %s is not int — using 0", config_path)
        universe_seed = 0

    return EngineConfig(
        max_chain_depth=int(engine_section.get("max_chain_depth", 10)),
        classifier_min_confidence=float(engine_section.get("classifier_min_confidence", 0.6)),
        universe_seed=universe_seed,
    )


def generate_universe_seed() -> int:
    """Generate a fresh random universe seed. 63-bit positive integer."""
    return secrets.randbits(63)
