"""Unit tests for EngineConfig loader.

Covers all failure modes: missing file, malformed YAML, type errors, and
the generate_universe_seed() entropy helper.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from token_world.engine.config import generate_universe_seed, load_engine_config


class TestLoadEngineConfigMissingFile:
    """Missing universe.yaml yields defaults."""

    def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        """No universe.yaml -> EngineConfig with all defaults."""
        cfg = load_engine_config(tmp_path)
        assert cfg.max_chain_depth == 10
        assert cfg.classifier_min_confidence == 0.6
        assert cfg.universe_seed == 0


class TestLoadEngineConfigWellFormed:
    """Well-formed universe.yaml yields parsed values."""

    def test_parses_all_fields(self, tmp_path: Path) -> None:
        """universe.yaml with full engine section and universe_seed."""
        (tmp_path / "universe.yaml").write_text(
            "universe_seed: 12345\n"
            "engine:\n"
            "  max_chain_depth: 20\n"
            "  classifier_min_confidence: 0.75\n",
            encoding="utf-8",
        )
        cfg = load_engine_config(tmp_path)
        assert cfg.universe_seed == 12345
        assert cfg.max_chain_depth == 20
        assert cfg.classifier_min_confidence == 0.75

    def test_engine_section_missing_uses_defaults(self, tmp_path: Path) -> None:
        """universe_seed present but engine: absent -> engine defaults."""
        (tmp_path / "universe.yaml").write_text(
            "universe_seed: 999\n",
            encoding="utf-8",
        )
        cfg = load_engine_config(tmp_path)
        assert cfg.universe_seed == 999
        assert cfg.max_chain_depth == 10
        assert cfg.classifier_min_confidence == 0.6


class TestLoadEngineConfigMalformed:
    """Malformed inputs fall back to defaults with a WARNING logged."""

    def test_malformed_yaml_returns_defaults(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Invalid YAML -> defaults + WARNING log."""
        (tmp_path / "universe.yaml").write_text(
            "invalid: yaml: [unclosed\n",
            encoding="utf-8",
        )
        with caplog.at_level(logging.WARNING, logger="token_world.engine.config"):
            cfg = load_engine_config(tmp_path)
        assert cfg.max_chain_depth == 10
        assert cfg.universe_seed == 0
        assert any(
            "Malformed" in r.message or "malformed" in r.message.lower() for r in caplog.records
        )

    def test_root_is_list_returns_defaults(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Root is a YAML list, not mapping -> defaults + WARNING."""
        (tmp_path / "universe.yaml").write_text(
            "- item1\n- item2\n",
            encoding="utf-8",
        )
        with caplog.at_level(logging.WARNING, logger="token_world.engine.config"):
            cfg = load_engine_config(tmp_path)
        assert cfg.max_chain_depth == 10
        assert len(caplog.records) >= 1

    def test_universe_seed_not_int_uses_zero(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """universe_seed that is a string -> defaults to 0 + WARNING."""
        (tmp_path / "universe.yaml").write_text(
            "universe_seed: 'not-an-int'\n",
            encoding="utf-8",
        )
        with caplog.at_level(logging.WARNING, logger="token_world.engine.config"):
            cfg = load_engine_config(tmp_path)
        assert cfg.universe_seed == 0
        assert any(record.levelno >= logging.WARNING for record in caplog.records)


class TestLoadEngineConfigSoftFailEngineSection:
    """WR-03: engine section fields must soft-fail (warn + defaults) on bad values."""

    def test_max_chain_depth_string_uses_default(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """engine.max_chain_depth='ten' (string) -> default 10 + WARNING."""
        (tmp_path / "universe.yaml").write_text(
            "engine:\n  max_chain_depth: 'ten'\n",
            encoding="utf-8",
        )
        with caplog.at_level(logging.WARNING, logger="token_world.engine.config"):
            cfg = load_engine_config(tmp_path)
        assert cfg.max_chain_depth == 10
        assert any("max_chain_depth" in r.message for r in caplog.records)

    def test_max_chain_depth_null_uses_default(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """engine.max_chain_depth=null (None) -> default 10 + WARNING."""
        (tmp_path / "universe.yaml").write_text(
            "engine:\n  max_chain_depth: null\n",
            encoding="utf-8",
        )
        with caplog.at_level(logging.WARNING, logger="token_world.engine.config"):
            cfg = load_engine_config(tmp_path)
        assert cfg.max_chain_depth == 10
        assert any("max_chain_depth" in r.message for r in caplog.records)

    def test_classifier_min_confidence_string_uses_default(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """engine.classifier_min_confidence='high' (string) -> default 0.6 + WARNING."""
        (tmp_path / "universe.yaml").write_text(
            "engine:\n  classifier_min_confidence: 'high'\n",
            encoding="utf-8",
        )
        with caplog.at_level(logging.WARNING, logger="token_world.engine.config"):
            cfg = load_engine_config(tmp_path)
        assert cfg.classifier_min_confidence == 0.6
        assert any("classifier_min_confidence" in r.message for r in caplog.records)

    def test_classifier_min_confidence_null_uses_default(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """engine.classifier_min_confidence=null (None) -> default 0.6 + WARNING."""
        (tmp_path / "universe.yaml").write_text(
            "engine:\n  classifier_min_confidence: null\n",
            encoding="utf-8",
        )
        with caplog.at_level(logging.WARNING, logger="token_world.engine.config"):
            cfg = load_engine_config(tmp_path)
        assert cfg.classifier_min_confidence == 0.6
        assert any("classifier_min_confidence" in r.message for r in caplog.records)

    def test_valid_int_max_chain_depth_parsed_correctly(self, tmp_path: Path) -> None:
        """engine.max_chain_depth=5 (valid int) -> 5, no warning."""
        (tmp_path / "universe.yaml").write_text(
            "engine:\n  max_chain_depth: 5\n",
            encoding="utf-8",
        )
        cfg = load_engine_config(tmp_path)
        assert cfg.max_chain_depth == 5


class TestGenerateUniverseSeed:
    """generate_universe_seed() entropy tests."""

    def test_returns_positive_int(self) -> None:
        """Seed is a positive integer."""
        seed = generate_universe_seed()
        assert isinstance(seed, int)
        assert seed > 0

    def test_within_63_bit_range(self) -> None:
        """Seed fits within 63 bits (< 2**63)."""
        seed = generate_universe_seed()
        assert seed < 2**63

    def test_two_calls_differ(self) -> None:
        """Two successive calls produce distinct seeds (collision probability ~0)."""
        a = generate_universe_seed()
        b = generate_universe_seed()
        assert a != b
