"""Tests for the module-based mechanic loader (D-10)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from token_world.mechanic.loader import (
    discover_mechanic_modules,
    load_mechanic_classes,
)


def _write_mechanic_module(
    path: Path,
    *,
    cls_name: str = "TestMechanic",
    id_: str = "test_mech",
    extra_body: str = "",
) -> None:
    path.write_text(
        textwrap.dedent(
            f"""\
            from __future__ import annotations

            from token_world.graph import Mutation
            from token_world.mechanic.protocol import CheckResult, Mechanic


            class {cls_name}(Mechanic):
                id = {id_!r}
                description = "Test"
                voluntary = True
                tags = []

                def check(self, ctx) -> CheckResult:
                    return CheckResult(passed=True)

                def apply(self, ctx) -> list[Mutation]:
                    return []

            {extra_body}
            """
        )
    )


class TestLoadMechanicClasses:
    def test_load_mechanic_classes_returns_subclasses(self, tmp_path: Path) -> None:
        """Module with one Mechanic subclass returns list of length 1."""
        module_path = tmp_path / "m.py"
        _write_mechanic_module(module_path)
        classes = load_mechanic_classes(module_path)
        assert len(classes) == 1
        assert classes[0].id == "test_mech"

    def test_load_mechanic_classes_empty_module_returns_empty_list(self, tmp_path: Path) -> None:
        """Module without Mechanic subclass returns [] (not an error)."""
        module_path = tmp_path / "empty.py"
        module_path.write_text("# No Mechanic subclass here\nx = 1\n")
        assert load_mechanic_classes(module_path) == []

    def test_load_mechanic_classes_missing_file_raises_filenotfound(self, tmp_path: Path) -> None:
        """Non-existent module path -> FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_mechanic_classes(tmp_path / "does_not_exist.py")

    def test_load_mechanic_classes_filters_imported_bases(self, tmp_path: Path) -> None:
        """Mechanic bases imported from other modules must NOT be returned."""
        module_path = tmp_path / "m.py"
        _write_mechanic_module(module_path)
        # The module imports ``Mechanic`` at module level; it must not appear
        # in the returned list (filter: attr.__module__ == module_name).
        classes = load_mechanic_classes(module_path)
        assert all(cls.__module__ == f"mechanic_{module_path.stem}" for cls in classes)
        assert len(classes) == 1  # only TestMechanic, not the imported Mechanic base

    def test_load_mechanic_classes_multiple_subclasses(self, tmp_path: Path) -> None:
        """Multiple Mechanic subclasses in one module are all returned (D-03)."""
        module_path = tmp_path / "multi.py"
        module_path.write_text(
            textwrap.dedent(
                """\
                from __future__ import annotations

                from token_world.graph import Mutation
                from token_world.mechanic.protocol import CheckResult, Mechanic


                class FirstMechanic(Mechanic):
                    id = "first"
                    description = "First"
                    voluntary = True
                    tags = []

                    def check(self, ctx) -> CheckResult:
                        return CheckResult(passed=True)

                    def apply(self, ctx) -> list[Mutation]:
                        return []


                class SecondMechanic(Mechanic):
                    id = "second"
                    description = "Second"
                    voluntary = False
                    tags = []

                    def check(self, ctx) -> CheckResult:
                        return CheckResult(passed=True)

                    def apply(self, ctx) -> list[Mutation]:
                        return []
                """
            )
        )
        classes = load_mechanic_classes(module_path)
        assert len(classes) == 2
        ids = sorted(c.id for c in classes)
        assert ids == ["first", "second"]


class TestDiscoverMechanicModules:
    def test_discover_mechanic_modules_filters_underscore_and_init(self, tmp_path: Path) -> None:
        """Directory with .py + _helpers.py + __init__.py returns only .py modules."""
        (tmp_path / "movement.py").write_text("# ok\n")
        (tmp_path / "_helpers.py").write_text("# skip\n")
        (tmp_path / "__init__.py").write_text("# skip\n")
        modules = discover_mechanic_modules(tmp_path)
        assert [m.name for m in modules] == ["movement.py"]

    def test_discover_mechanic_modules_sorted(self, tmp_path: Path) -> None:
        """Return value is sorted for deterministic scan order."""
        (tmp_path / "zeta.py").write_text("# ok\n")
        (tmp_path / "alpha.py").write_text("# ok\n")
        (tmp_path / "mu.py").write_text("# ok\n")
        modules = discover_mechanic_modules(tmp_path)
        assert [m.name for m in modules] == ["alpha.py", "mu.py", "zeta.py"]

    def test_discover_mechanic_modules_missing_dir_returns_empty(self, tmp_path: Path) -> None:
        """A non-existent directory returns [] rather than raising."""
        assert discover_mechanic_modules(tmp_path / "does_not_exist") == []

    def test_discover_mechanic_modules_skips_subdirectories(self, tmp_path: Path) -> None:
        """Subdirectories are ignored (flat layout per D-10)."""
        (tmp_path / "movement.py").write_text("# ok\n")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "nested.py").write_text("# nested; must be ignored\n")
        modules = discover_mechanic_modules(tmp_path)
        assert [m.name for m in modules] == ["movement.py"]
