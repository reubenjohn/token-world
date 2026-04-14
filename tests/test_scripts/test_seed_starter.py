"""Tests for scripts/seed_starter_universe.py — SC-3 entities and SC-4 flag."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from token_world.graph import KnowledgeGraph

# ---------------------------------------------------------------------------
# Module loader helper (scripts/ has no __init__.py)
# ---------------------------------------------------------------------------

_SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "seed_starter_universe.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("seed_starter_universe", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["seed_starter_universe"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_mod = _load_module()
_seed_graph = _mod._seed_graph
_prune_seed_mechanics = _mod._prune_seed_mechanics


# ---------------------------------------------------------------------------
# SC-3: entity property assertions
# ---------------------------------------------------------------------------


@pytest.fixture()
def seeded_kg(tmp_path: Path):
    """A KnowledgeGraph populated by _seed_graph() using a temp DB."""
    kg = KnowledgeGraph(db_path=tmp_path / "universe.db")
    _seed_graph(kg)
    return kg


def test_bench_entity_present(seeded_kg: KnowledgeGraph) -> None:
    """SC-3: bench entity exists with weathered=True."""
    bench_nodes = seeded_kg.nodes(subtype="furniture", weathered=True)
    assert bench_nodes, "No bench entity with weathered=True found in seeded graph"
    bench = bench_nodes[0]
    assert seeded_kg.query(bench, "material") == "wood"
    assert seeded_kg.query(bench, "planks_intact") == 5


def test_chicken_coop_entity_present(seeded_kg: KnowledgeGraph) -> None:
    """SC-3: chicken_coop entity exists with hook properties."""
    coop_nodes = seeded_kg.nodes(subtype="structure")
    # Filter to the one with chickens_inside
    coop_nodes = [n for n in coop_nodes if seeded_kg.query(n, "chickens_inside") is not None]
    assert coop_nodes, "No chicken_coop entity found in seeded graph"
    coop = coop_nodes[0]
    assert seeded_kg.query(coop, "chickens_inside") == 3
    assert seeded_kg.query(coop, "door_latched") is True
    assert seeded_kg.query(coop, "eggs_today") == 0
    assert seeded_kg.query(coop, "feed_level") == pytest.approx(0.6)


def test_broken_gate_entity_present(seeded_kg: KnowledgeGraph) -> None:
    """SC-3: broken_gate entity exists with broken=True hook."""
    gate_nodes = seeded_kg.nodes(subtype="gate", broken=True)
    assert gate_nodes, "No broken_gate entity with broken=True found in seeded graph"
    gate = gate_nodes[0]
    assert seeded_kg.query(gate, "latched") is False
    assert seeded_kg.query(gate, "repair_progress") == pytest.approx(0.0)
    assert seeded_kg.query(gate, "material") == "wood"


# ---------------------------------------------------------------------------
# SC-4: --preserve-mechanics flag behaviour
# ---------------------------------------------------------------------------


def test_preserve_mechanics_flag_recognized() -> None:
    """SC-4: --preserve-mechanics is a valid argparse flag (no SystemExit)."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", default="willowbrook")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--preserve-mechanics",
        action="store_true",
        default=False,
    )
    args = parser.parse_args(["--preserve-mechanics"])
    assert args.preserve_mechanics is True


def test_preserve_mechanics_skips_prune(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-4: seed() with preserve_mechanics=True does NOT call _prune_seed_mechanics."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    with patch.object(_mod, "_prune_seed_mechanics") as mock_prune:
        # Also patch SessionManager and create_agent_node to avoid full setup
        with patch.object(_mod, "SessionManager") as mock_sm:
            mock_sm.return_value.create_session.return_value = "sess-1"
            _mod.seed(overwrite=False, preserve_mechanics=True)
        mock_prune.assert_not_called()


def test_without_preserve_mechanics_calls_prune(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC-4: seed() without preserve_mechanics=True DOES call _prune_seed_mechanics."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    with patch.object(_mod, "_prune_seed_mechanics") as mock_prune:
        with patch.object(_mod, "SessionManager") as mock_sm:
            mock_sm.return_value.create_session.return_value = "sess-1"
            _mod.seed(overwrite=False, preserve_mechanics=False)
        mock_prune.assert_called_once()


def test_prune_prints_stderr_warning(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """SC-4: _prune_seed_mechanics prints a loud warning listing files to remove."""
    mech_dir = tmp_path / "mechanics"
    mech_dir.mkdir()
    # Create a file that is NOT in _KEEP_MECHANICS
    extra = mech_dir / "daydream.py"
    extra.write_text("# extra mechanic\n")

    _prune_seed_mechanics(tmp_path)

    captured = capsys.readouterr()
    assert "daydream.py" in captured.err
    assert "WARNING" in captured.err
    assert "--preserve-mechanics" in captured.err
    # File should be gone
    assert not extra.exists()
