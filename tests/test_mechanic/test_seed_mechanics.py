"""Importability and registry-registration tests for the 5 new seed mechanics.

Covers REQ-V12-SEEDS-01: examine, pet, sharpen, hum, drop are importable,
carry the expected interface, and all 5 filenames appear in _KEEP_MECHANICS
in seed_starter_universe.py.

Tests 1-6: import-only, no graph fixtures needed.
Test 7: reads seed_starter_universe.py as text to assert membership in
        the _KEEP_MECHANICS frozenset definition.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Tests 1-5: importability
# ---------------------------------------------------------------------------


def test_examine_importable() -> None:
    """ExamineMechanic is importable from token_world.mechanic.seeds.examine."""
    from token_world.mechanic.seeds.examine import ExamineMechanic  # noqa: F401


def test_pet_importable() -> None:
    """PetMechanic is importable from token_world.mechanic.seeds.pet."""
    from token_world.mechanic.seeds.pet import PetMechanic  # noqa: F401


def test_sharpen_importable() -> None:
    """SharpenMechanic is importable from token_world.mechanic.seeds.sharpen."""
    from token_world.mechanic.seeds.sharpen import SharpenMechanic  # noqa: F401


def test_hum_importable() -> None:
    """HumMechanic is importable from token_world.mechanic.seeds.hum."""
    from token_world.mechanic.seeds.hum import HumMechanic  # noqa: F401


def test_drop_importable() -> None:
    """DropMechanic is importable from token_world.mechanic.seeds.drop."""
    from token_world.mechanic.seeds.drop import DropMechanic  # noqa: F401


# ---------------------------------------------------------------------------
# Test 6: interface contract — id (str), description (str), check, apply callable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cls",
    [
        pytest.param("token_world.mechanic.seeds.examine.ExamineMechanic", id="examine"),
        pytest.param("token_world.mechanic.seeds.pet.PetMechanic", id="pet"),
        pytest.param("token_world.mechanic.seeds.sharpen.SharpenMechanic", id="sharpen"),
        pytest.param("token_world.mechanic.seeds.hum.HumMechanic", id="hum"),
        pytest.param("token_world.mechanic.seeds.drop.DropMechanic", id="drop"),
    ],
)
def test_mechanic_interface(cls: str) -> None:
    """Each mechanic class has id (str), description (str), check, apply (callable)."""
    import importlib

    module_path, class_name = cls.rsplit(".", 1)
    module = importlib.import_module(module_path)
    klass = getattr(module, class_name)
    instance = klass()

    assert isinstance(klass.id, str), f"{class_name}.id must be a str"
    assert isinstance(klass.description, str), f"{class_name}.description must be a str"
    assert callable(instance.check), f"{class_name}.check must be callable"
    assert callable(instance.apply), f"{class_name}.apply must be callable"


# ---------------------------------------------------------------------------
# Test 7: all 5 filenames appear in _KEEP_MECHANICS frozenset definition
# ---------------------------------------------------------------------------

_NEW_MECHANICS = frozenset(
    {
        "examine.py",
        "pet.py",
        "sharpen.py",
        "hum.py",
        "drop.py",
    }
)


def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (contains pyproject.toml)."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError(f"Could not find repo root from {here}")


def test_keep_mechanics_contains_new_seeds() -> None:
    """All 5 new filenames must appear in _KEEP_MECHANICS in seed_starter_universe.py.

    Reads the script as text and uses ``ast`` to extract the frozenset
    literal so this test is independent of the script's runtime imports.
    """
    repo_root = _find_repo_root()
    script = repo_root / "scripts" / "seed_starter_universe.py"
    assert script.exists(), f"seed_starter_universe.py not found at {script}"

    source = script.read_text(encoding="utf-8")

    # Parse the source into an AST and find the _KEEP_MECHANICS assignment.
    tree = ast.parse(source)
    keep_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_KEEP_MECHANICS":
                # The RHS should be a Call(frozenset, args=[Set(...)])
                # or a frozenset({...}) literal — walk the RHS for string constants.
                for child in ast.walk(node.value):
                    if isinstance(child, ast.Constant) and isinstance(child.value, str):
                        keep_names.add(child.value)

    missing = _NEW_MECHANICS - keep_names
    assert not missing, (
        f"These filenames are missing from _KEEP_MECHANICS: {sorted(missing)}\n"
        f"Found in _KEEP_MECHANICS: {sorted(keep_names)}"
    )
