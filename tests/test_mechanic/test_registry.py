"""Tests for MechanicRegistry (flat module scanning, per D-10)."""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from token_world.mechanic.protocol import Mechanic

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_universe(tmp_path: Path) -> Path:
    """Create a temporary universe directory with flat seed mechanics + git.

    Copies flat seed ``.py`` modules from the package into a ``mechanics/``
    subdirectory, initialises a git repo, and creates an initial commit.
    """
    mechanics_dir = tmp_path / "mechanics"
    mechanics_dir.mkdir()

    seeds_dir = (
        Path(__file__).resolve().parent.parent.parent / "src" / "token_world" / "mechanic" / "seeds"
    )
    for entry in sorted(seeds_dir.iterdir()):
        if entry.is_file() and entry.suffix == ".py" and entry.name != "__init__.py":
            shutil.copy2(entry, mechanics_dir / entry.name)

    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@localhost",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@localhost",
    }
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env=git_env,
    )
    return tmp_path


@pytest.fixture
def non_git_universe(tmp_path: Path) -> Path:
    """Universe dir with flat seed mechanics but no git repo."""
    mechanics_dir = tmp_path / "mechanics"
    mechanics_dir.mkdir()

    seeds_dir = (
        Path(__file__).resolve().parent.parent.parent / "src" / "token_world" / "mechanic" / "seeds"
    )
    for entry in sorted(seeds_dir.iterdir()):
        if entry.is_file() and entry.suffix == ".py" and entry.name != "__init__.py":
            shutil.copy2(entry, mechanics_dir / entry.name)

    return tmp_path


def _write_mechanic_module(path: Path, *, cls_name: str, id_: str, tags: list[str]) -> None:
    """Write a minimal mechanic module to *path*."""
    path.write_text(
        textwrap.dedent(
            f"""\
            from __future__ import annotations

            from token_world.graph import Mutation
            from token_world.mechanic.protocol import CheckResult, Mechanic


            class {cls_name}(Mechanic):
                id = {id_!r}
                description = "Test mechanic {id_}"
                voluntary = True
                tags = {tags!r}

                def check(self, ctx) -> CheckResult:
                    return CheckResult(passed=True)

                def apply(self, ctx) -> list[Mutation]:
                    return []
            """
        )
    )


# ---------------------------------------------------------------------------
# Registry / Scan Tests (flat layout)
# ---------------------------------------------------------------------------


class TestRegistryScan:
    def test_scan_discovers_flat_modules(self, tmp_path: Path) -> None:
        """Registry scans ``<id>.py`` files and indexes them."""
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()
        _write_mechanic_module(
            mechanics / "movement.py",
            cls_name="MovementMechanic",
            id_="movement",
            tags=["spatial"],
        )

        registry = MechanicRegistry(mechanics, universe_dir=tmp_path)
        infos = registry.list_mechanics()
        assert len(infos) == 1
        assert infos[0].id == "movement"
        assert infos[0].path.is_file()
        assert infos[0].path.suffix == ".py"
        assert "spatial" in infos[0].tags

    def test_scan_skips_underscore_prefixed_modules(self, tmp_path: Path) -> None:
        """Registry skips ``_helpers.py`` and similar underscore-prefixed files,
        even if they contain Mechanic subclasses."""
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()
        # Real module
        _write_mechanic_module(
            mechanics / "real.py",
            cls_name="RealMechanic",
            id_="real",
            tags=[],
        )
        # Pathological: underscore-prefixed with a Mechanic subclass
        _write_mechanic_module(
            mechanics / "_helpers.py",
            cls_name="SneakyMechanic",
            id_="sneaky",
            tags=[],
        )

        registry = MechanicRegistry(mechanics, universe_dir=tmp_path)
        ids = [m.id for m in registry.list_mechanics()]
        assert ids == ["real"]
        assert "sneaky" not in ids

    def test_scan_skips_init_py(self, tmp_path: Path) -> None:
        """Registry skips ``__init__.py`` even if it contains a Mechanic subclass."""
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()
        _write_mechanic_module(
            mechanics / "real.py",
            cls_name="RealMechanic",
            id_="real",
            tags=[],
        )
        _write_mechanic_module(
            mechanics / "__init__.py",
            cls_name="InitMechanic",
            id_="init_sneak",
            tags=[],
        )

        registry = MechanicRegistry(mechanics, universe_dir=tmp_path)
        ids = [m.id for m in registry.list_mechanics()]
        assert ids == ["real"]
        assert "init_sneak" not in ids

    def test_duplicate_id_raises(self, tmp_path: Path) -> None:
        """Two modules declaring the same ``id`` -> ValueError (T-04)."""
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()
        _write_mechanic_module(
            mechanics / "a.py",
            cls_name="AMechanic",
            id_="same_id",
            tags=[],
        )
        _write_mechanic_module(
            mechanics / "b.py",
            cls_name="BMechanic",
            id_="same_id",
            tags=[],
        )

        with pytest.raises(ValueError, match="Duplicate mechanic id"):
            MechanicRegistry(mechanics, universe_dir=tmp_path)

    def test_scan_reads_from_class_attributes_no_meta_yaml(self, tmp_path: Path) -> None:
        """Metadata comes from class attributes only; no meta.yaml anywhere."""
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()
        _write_mechanic_module(
            mechanics / "m.py",
            cls_name="MMechanic",
            id_="m",
            tags=["x", "y"],
        )
        # A stray meta.yaml must NOT be picked up by the registry.
        (mechanics / "meta.yaml").write_text("id: ignored\n")

        registry = MechanicRegistry(mechanics, universe_dir=tmp_path)
        info = registry.get_info("m")
        assert info.description == "Test mechanic m"
        assert info.tags == ["x", "y"]
        assert (
            registry.get_info("ignored")
            if "ignored" in [i.id for i in registry.list_mechanics()]
            else True
        )  # noqa: E501 -- defensive; "ignored" must not be present
        assert "ignored" not in [i.id for i in registry.list_mechanics()]


# ---------------------------------------------------------------------------
# Seed-universe Integration (flat copy)
# ---------------------------------------------------------------------------


class TestSeedUniverse:
    def test_scan_discovers_seeds(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        ids = sorted(m.id for m in registry.list_mechanics())
        assert ids == [
            "environmental_reaction",
            "movement",
            "observation",
            "passage_move",
        ]

    def test_list_mechanics_sorted(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        mechanics = registry.list_mechanics()
        ids = [m.id for m in mechanics]
        assert ids == sorted(ids)

    def test_get_mechanic_returns_instance(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        mechanic = registry.get_mechanic("movement")
        assert isinstance(mechanic, Mechanic)
        assert mechanic.id == "movement"

    def test_get_mechanic_unknown_raises(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        with pytest.raises(KeyError, match="nonexistent"):
            registry.get_mechanic("nonexistent")

    def test_mechanic_info_has_correct_fields(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        info = registry.get_info("movement")
        assert info.id == "movement"
        assert "move" in info.description.lower()
        assert info.voluntary is True
        assert "spatial" in info.tags
        assert info.path.is_file()
        assert info.path.name == "movement.py"


# ---------------------------------------------------------------------------
# get_class accessor (04-REVIEWS HIGH #2 / Suggestion #12)
# ---------------------------------------------------------------------------


class TestGetClass:
    """Public accessor returning the Mechanic subclass itself (not an instance).

    Motivates 04-09's ``blocked_by`` routing, which needs to read a
    class-level attribute without instantiating the mechanic and without
    reaching into ``registry._classes``.
    """

    def test_get_class_returns_registered_class(self, tmp_path: Path) -> None:
        """get_class returns the exact subclass object registered under id.

        Identity is asserted via two calls on the same registry: the accessor
        must hand back the *same* class object every time (i.e. it reads the
        stored value, it does not re-load the module). Name and Mechanic-
        subclass provenance round out the identity check.
        """
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()
        _write_mechanic_module(
            mechanics / "movement.py",
            cls_name="MovementMechanic",
            id_="movement",
            tags=["spatial"],
        )

        registry = MechanicRegistry(mechanics, universe_dir=tmp_path)

        cls = registry.get_class("movement")
        # Same class object on repeated lookup -- the accessor reads from
        # the registry's stored index, it does not re-import the module.
        assert registry.get_class("movement") is cls

        # It is the MovementMechanic subclass with the expected id.
        assert issubclass(cls, Mechanic)
        assert cls.__name__ == "MovementMechanic"
        assert cls.id == "movement"

    def test_get_class_raises_keyerror_for_unknown_id(self, tmp_path: Path) -> None:
        """Unknown id -> KeyError with the same repr-quoted convention as get_mechanic."""
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()
        _write_mechanic_module(
            mechanics / "only.py",
            cls_name="OnlyMechanic",
            id_="only",
            tags=[],
        )

        registry = MechanicRegistry(mechanics, universe_dir=tmp_path)
        with pytest.raises(KeyError, match="Unknown mechanic: 'nonexistent'"):
            registry.get_class("nonexistent")

    def test_get_class_exposes_class_not_instance(self, tmp_path: Path) -> None:
        """get_class returns a type; get_mechanic returns an instance of that type."""
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()
        _write_mechanic_module(
            mechanics / "movement.py",
            cls_name="MovementMechanic",
            id_="movement",
            tags=["spatial"],
        )

        registry = MechanicRegistry(mechanics, universe_dir=tmp_path)
        cls = registry.get_class("movement")
        instance = registry.get_mechanic("movement")

        # The accessor returns a class object (type), not an instance.
        assert isinstance(cls, type)
        assert issubclass(cls, Mechanic)
        assert not isinstance(cls, Mechanic)

        # The companion accessor produces an instance of that same class.
        assert isinstance(instance, cls)
        assert type(instance) is cls

        # Class-level attributes are readable without instantiation -- this
        # is the property 04-09's blocked_by routing relies on.
        assert cls.id == "movement"
        assert "spatial" in cls.tags


# ---------------------------------------------------------------------------
# Query by Tag
# ---------------------------------------------------------------------------


class TestQueryByTag:
    def test_query_by_tag_core(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        results = registry.query_by_tag("core")
        assert len(results) == 3

    def test_query_by_tag_returns_matching_mechanics(self, tmp_path: Path) -> None:
        """query_by_tag returns only mechanics whose tags contain the query tag."""
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()
        _write_mechanic_module(
            mechanics / "a.py",
            cls_name="AMechanic",
            id_="a",
            tags=["spatial"],
        )
        _write_mechanic_module(
            mechanics / "b.py",
            cls_name="BMechanic",
            id_="b",
            tags=["social"],
        )

        registry = MechanicRegistry(mechanics, universe_dir=tmp_path)
        results = registry.query_by_tag("spatial")
        assert len(results) == 1
        assert results[0].id == "a"


# ---------------------------------------------------------------------------
# Git History
# ---------------------------------------------------------------------------


class TestGitHistory:
    def test_get_history_returns_commits(self, tmp_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(tmp_universe / "mechanics", universe_dir=tmp_universe)
        history = registry.get_history("movement")
        assert len(history) >= 1
        assert history[0].commit_hash
        assert history[0].date
        assert history[0].message

    def test_get_history_not_git_repo(self, non_git_universe: Path) -> None:
        from token_world.mechanic.registry import MechanicRegistry

        registry = MechanicRegistry(non_git_universe / "mechanics", universe_dir=non_git_universe)
        history = registry.get_history("movement")
        assert history == []


# ---------------------------------------------------------------------------
# Validation wiring (04-02 Task 3)
# ---------------------------------------------------------------------------


class TestValidationWiring:
    def test_scan_returns_validation_reports(self, tmp_path: Path) -> None:
        """scan() returns a ValidationReport per discovered module."""
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()
        _write_mechanic_module(
            mechanics / "only.py",
            cls_name="OnlyMechanic",
            id_="only",
            tags=["core"],
        )

        registry = MechanicRegistry(mechanics, universe_dir=tmp_path)
        reports = registry.last_scan_reports
        assert len(reports) == 1
        assert reports[0].passed is True
        # Explicit scan() call returns an equivalent list.
        fresh = registry.scan()
        assert len(fresh) == 1
        assert fresh[0].passed is True

    def test_invalid_mechanic_excluded_from_index(self, tmp_path: Path) -> None:
        """Modules failing validation never enter the live index."""
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()

        # Valid mechanic
        _write_mechanic_module(
            mechanics / "good.py",
            cls_name="GoodMechanic",
            id_="good",
            tags=["core"],
        )

        # Invalid mechanic: imports networkx (forbidden by D-14)
        (mechanics / "bad.py").write_text(
            textwrap.dedent(
                """\
                import networkx
                from token_world.mechanic.protocol import CheckResult, Mechanic


                class BadMechanic(Mechanic):
                    id = "bad"
                    description = "imports networkx"
                    voluntary = True
                    tags: list[str] = []

                    def check(self, ctx):
                        return CheckResult(passed=False)

                    def apply(self, ctx):
                        return []
                """
            ),
            encoding="utf-8",
        )

        registry = MechanicRegistry(mechanics, universe_dir=tmp_path)

        reports = registry.last_scan_reports
        assert len(reports) == 2
        passed = [r for r in reports if r.passed]
        failed = [r for r in reports if not r.passed]
        assert len(passed) == 1
        assert len(failed) == 1

        ids = [m.id for m in registry.list_mechanics()]
        assert ids == ["good"]
        assert "bad" not in ids

        # The valid mechanic is retrievable
        mech = registry.get_mechanic("good")
        assert mech.id == "good"

        with pytest.raises(KeyError):
            registry.get_mechanic("bad")


# ---------------------------------------------------------------------------
# 04-03 Task 4: scan(diagnostics_sink=...) persists failing reports (D-15)
# ---------------------------------------------------------------------------


def _write_bad_mechanic(path: Path) -> None:
    """Write a mechanic module that fails D-14 AST rules (imports networkx)."""
    path.write_text(
        textwrap.dedent(
            """\
            import networkx
            from token_world.mechanic.protocol import CheckResult, Mechanic


            class BadMechanic(Mechanic):
                id = "bad"
                description = "imports networkx"
                voluntary = True
                tags: list[str] = []

                def check(self, ctx):
                    return CheckResult(passed=False)

                def apply(self, ctx):
                    return []
            """
        ),
        encoding="utf-8",
    )


class TestRegistrySinkWiring:
    """D-15 closure: scan(diagnostics_sink=sink) writes per-failure report.json."""

    def test_registry_writes_validation_failure_via_sink(self, tmp_path: Path) -> None:
        import json
        import re

        from token_world.mechanic.diagnostics import DiagnosticsSink
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()
        _write_bad_mechanic(mechanics / "bad.py")

        universe_dir = tmp_path / "universe"
        universe_dir.mkdir()
        sink = DiagnosticsSink(universe_dir)

        # __init__'s internal self.scan() fires with no sink (backward compat).
        registry = MechanicRegistry(mechanics, universe_dir=tmp_path)
        assert registry.last_scan_reports[0].passed is False

        # Explicit sink-aware scan persists the failure.
        reports = registry.scan(diagnostics_sink=sink)
        assert len(reports) == 1
        assert reports[0].passed is False

        validation_root = universe_dir / "diagnostics" / "validation"
        assert validation_root.is_dir()
        subfolders = [p for p in validation_root.iterdir() if p.is_dir()]
        assert len(subfolders) == 1

        # Folder name: <YYYYMMDDThhmmssZ>_<id>
        assert re.fullmatch(r"\d{8}T\d{6}Z_.+", subfolders[0].name)

        report_path = subfolders[0] / "report.json"
        assert report_path.is_file()
        data = json.loads(report_path.read_text())
        assert data["passed"] is False
        # findings list exists and every finding has stage + rule fields.
        assert isinstance(data["findings"], list)
        assert data["findings"]  # at least one
        assert all("stage" in f and "rule" in f for f in data["findings"])

    def test_registry_scan_without_sink_is_unchanged(self, tmp_path: Path) -> None:
        """Backward-compat guard: no sink -> no diagnostics side-effects."""
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()
        _write_bad_mechanic(mechanics / "bad.py")

        registry = MechanicRegistry(mechanics, universe_dir=tmp_path)
        reports = registry.scan()
        assert len(reports) == 1
        assert reports[0].passed is False
        # No diagnostics/ folder should have been created anywhere we can
        # observe -- we never passed a sink.
        assert not (tmp_path / "diagnostics").exists()

    def test_registry_sink_write_failure_is_warned_not_raised(self, tmp_path: Path) -> None:
        """Sink-write errors degrade to warnings; scan must still return reports."""
        from token_world.mechanic.diagnostics import DiagnosticsSink
        from token_world.mechanic.registry import MechanicRegistry

        mechanics = tmp_path / "mechanics"
        mechanics.mkdir()
        _write_bad_mechanic(mechanics / "bad.py")

        universe_dir = tmp_path / "universe"
        universe_dir.mkdir()
        sink = DiagnosticsSink(universe_dir)

        # Monkeypatch open_validation to raise OSError.
        def _boom(_mechanic_id: str) -> Path:
            raise OSError("simulated disk full")

        sink.open_validation = _boom  # type: ignore[method-assign]

        registry = MechanicRegistry(mechanics, universe_dir=tmp_path)

        with pytest.warns(UserWarning, match="Registry failed to write"):
            reports = registry.scan(diagnostics_sink=sink)

        # The scan still returned the report list.
        assert len(reports) == 1
        assert reports[0].passed is False
        # And no validation folder was created (the sink never completed).
        assert not (universe_dir / "diagnostics" / "validation").exists()
