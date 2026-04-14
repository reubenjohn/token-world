"""CLI tests for ``token-world scaffold-mechanic`` (D-32)."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from token_world.cli import cli
from token_world.universe.manager import UniverseManager


def _create_universe(tmp_data_dir: Path) -> tuple[str, Path]:
    """Create a universe via the manager; return (slug, universe_dir)."""
    manager = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = manager.create("Scaffold Mechanic Test")
    return universe_dir.name, universe_dir


def test_scaffolds_module_and_test_files(tmp_data_dir: Path, monkeypatch) -> None:
    """``scaffold-mechanic <slug> --id forage`` writes both skeleton files.

    ``forage`` is chosen over a seed id (e.g. ``pickup``) because
    ``token-world create`` copies every seed under
    ``src/token_world/mechanic/seeds/`` into the new universe's
    ``mechanics/``, so scaffolding under a seed id would collide with
    the copied file. A non-seed id keeps the test purely about the
    scaffold-CLI surface.
    """
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, universe_dir = _create_universe(tmp_data_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["scaffold-mechanic", slug, "--id", "forage"])
    assert result.exit_code == 0, result.output

    module_path = universe_dir / "mechanics" / "forage.py"
    test_path = universe_dir / "tests" / "test_mechanics" / "test_forage.py"
    assert module_path.is_file(), f"module not created: {module_path}"
    assert test_path.is_file(), f"test not created: {test_path}"

    module_src = module_path.read_text(encoding="utf-8")
    # Class name is CamelCase of id + "Mechanic"
    assert "class ForageMechanic(Mechanic):" in module_src
    assert 'id = "forage"' in module_src
    assert "def check(self, ctx" in module_src
    assert "def apply(self, ctx" in module_src


def test_invalid_id_errors(tmp_data_dir: Path, monkeypatch) -> None:
    """Capital letters / hyphens / etc. in --id exit 2 with a clear message."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, _ = _create_universe(tmp_data_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["scaffold-mechanic", slug, "--id", "InvalidName"])
    assert result.exit_code == 2, result.output
    # Message should mention the naming rule.
    assert "lowercase" in result.output.lower()


def test_refuses_to_overwrite_existing_module(tmp_data_dir: Path, monkeypatch) -> None:
    """A second run with the same --id exits 1 with 'already exists'."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, _ = _create_universe(tmp_data_dir)

    runner = CliRunner()
    first = runner.invoke(cli, ["scaffold-mechanic", slug, "--id", "take"])
    assert first.exit_code == 0, first.output

    second = runner.invoke(cli, ["scaffold-mechanic", slug, "--id", "take"])
    assert second.exit_code == 1, second.output
    assert "already exists" in second.output


def test_voluntary_flag_sets_class_attr(tmp_data_dir: Path, monkeypatch) -> None:
    """``--involuntary`` flips the ``voluntary`` class attribute to False."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, universe_dir = _create_universe(tmp_data_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["scaffold-mechanic", slug, "--id", "foo", "--involuntary"])
    assert result.exit_code == 0, result.output

    module_src = (universe_dir / "mechanics" / "foo.py").read_text(encoding="utf-8")
    assert "voluntary = False" in module_src


def test_scaffolded_module_passes_validation(tmp_data_dir: Path, monkeypatch) -> None:
    """A freshly scaffolded skeleton must pass the full validation pipeline.

    Uses ``--id toss`` (not a seed name) so it doesn't collide with the
    drop.py seed mechanic that ships with every scaffolded universe.
    """
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, universe_dir = _create_universe(tmp_data_dir)

    runner = CliRunner()
    scaffold_result = runner.invoke(cli, ["scaffold-mechanic", slug, "--id", "toss"])
    assert scaffold_result.exit_code == 0, scaffold_result.output

    # Now validate via the CLI. Skeleton uses only allowed imports and defines
    # all required attributes + methods, so D-14 gate should pass.
    validate_result = runner.invoke(cli, ["validate-mechanic", slug, "toss"])
    assert validate_result.exit_code == 0, validate_result.output
    assert "PASS" in validate_result.output
