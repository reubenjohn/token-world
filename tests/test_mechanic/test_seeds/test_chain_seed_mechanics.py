"""Tests for Phase 18 chain seed mechanics.

SC-4: mood_change_watcher, contains_edge_watcher, temperature_watcher
- Each mechanic is importable, has the Mechanic interface
- watches() returns the correct matcher types
- check() passes/fails on correct conditions
- apply() produces correct mutations
- Registry audit: all three are auto-discovered and registered
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic import MechanicContext
from token_world.mechanic.matchers import EdgeMatcher, PropertyChangeMatcher

# ---------------------------------------------------------------------------
# Importability
# ---------------------------------------------------------------------------


def test_mood_change_watcher_importable() -> None:
    from token_world.mechanic.seeds.mood_change_watcher import (
        MoodChangeWatcherMechanic,  # noqa: F401
    )


def test_contains_edge_watcher_importable() -> None:
    from token_world.mechanic.seeds.contains_edge_watcher import (
        ContainsEdgeWatcherMechanic,  # noqa: F401
    )


def test_temperature_watcher_importable() -> None:
    from token_world.mechanic.seeds.temperature_watcher import (
        TemperatureWatcherMechanic,  # noqa: F401
    )


# ---------------------------------------------------------------------------
# Interface contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module,cls",
    [
        (
            "token_world.mechanic.seeds.mood_change_watcher",
            "MoodChangeWatcherMechanic",
        ),
        (
            "token_world.mechanic.seeds.contains_edge_watcher",
            "ContainsEdgeWatcherMechanic",
        ),
        (
            "token_world.mechanic.seeds.temperature_watcher",
            "TemperatureWatcherMechanic",
        ),
    ],
)
def test_mechanic_interface(module: str, cls: str) -> None:
    import importlib

    mod = importlib.import_module(module)
    klass = getattr(mod, cls)
    instance = klass()
    assert isinstance(klass.id, str)
    assert isinstance(klass.description, str)
    assert callable(instance.check)
    assert callable(instance.apply)
    assert callable(instance.watches)
    assert callable(instance.describe)


# ---------------------------------------------------------------------------
# mood_change_watcher
# ---------------------------------------------------------------------------


def _kg_with_agent(mood: str = "happy") -> tuple[KnowledgeGraph, MechanicContext]:
    kg = KnowledgeGraph()
    kg.add_node("npc", node_type="agent")
    kg.set("npc", "mood", mood)
    ctx = MechanicContext(kg, actor="npc", target="npc")
    return kg, ctx


class TestMoodChangeWatcher:
    def test_watches_mood_property_matcher(self) -> None:
        from token_world.mechanic.seeds.mood_change_watcher import MoodChangeWatcherMechanic

        m = MoodChangeWatcherMechanic()
        watchers = m.watches()
        assert len(watchers) == 1
        assert isinstance(watchers[0], PropertyChangeMatcher)
        assert watchers[0].property_name == "mood"

    def test_check_passes_when_node_has_mood(self) -> None:
        from token_world.mechanic.seeds.mood_change_watcher import MoodChangeWatcherMechanic

        _, ctx = _kg_with_agent("happy")
        result = MoodChangeWatcherMechanic().check(ctx)
        assert result.passed is True

    def test_check_fails_when_no_mood(self) -> None:
        from token_world.mechanic.seeds.mood_change_watcher import MoodChangeWatcherMechanic

        kg = KnowledgeGraph()
        kg.add_node("npc", node_type="agent")
        ctx = MechanicContext(kg, actor="npc", target="npc")
        result = MoodChangeWatcherMechanic().check(ctx)
        assert result.passed is False

    def test_check_fails_when_node_missing(self) -> None:
        from token_world.mechanic.seeds.mood_change_watcher import MoodChangeWatcherMechanic

        kg = KnowledgeGraph()
        kg.add_node("npc", node_type="agent")
        ctx = MechanicContext(kg, actor="npc", target="ghost")
        result = MoodChangeWatcherMechanic().check(ctx)
        assert result.passed is False

    def test_apply_writes_previous_mood(self) -> None:
        from token_world.mechanic.seeds.mood_change_watcher import MoodChangeWatcherMechanic

        kg, ctx = _kg_with_agent("happy")
        mutations = MoodChangeWatcherMechanic().apply(ctx)
        assert len(mutations) == 1
        assert mutations[0].property == "previous_mood"
        assert mutations[0].new_value == "happy"

    def test_voluntary_is_false(self) -> None:
        from token_world.mechanic.seeds.mood_change_watcher import MoodChangeWatcherMechanic

        assert MoodChangeWatcherMechanic.voluntary is False


# ---------------------------------------------------------------------------
# contains_edge_watcher
# ---------------------------------------------------------------------------


def _kg_with_container() -> tuple[KnowledgeGraph, MechanicContext]:
    kg = KnowledgeGraph()
    kg.add_node("chest", node_type="entity")
    kg.set("chest", "subtype", "container")
    kg.add_node("sword", node_type="entity")
    kg.add_edge("chest", "sword", relation="contains")
    ctx = MechanicContext(kg, actor="chest", target="chest")
    return kg, ctx


class TestContainsEdgeWatcher:
    def test_watches_contains_edge_add_and_remove(self) -> None:
        from token_world.mechanic.seeds.contains_edge_watcher import ContainsEdgeWatcherMechanic

        m = ContainsEdgeWatcherMechanic()
        watchers = m.watches()
        assert len(watchers) == 2
        event_types = {w.event_type for w in watchers}
        assert "add_edge" in event_types
        assert "remove_edge" in event_types
        for w in watchers:
            assert isinstance(w, EdgeMatcher)
            assert w.edge_label == "contains"

    def test_check_passes_when_container_exists(self) -> None:
        from token_world.mechanic.seeds.contains_edge_watcher import ContainsEdgeWatcherMechanic

        _, ctx = _kg_with_container()
        result = ContainsEdgeWatcherMechanic().check(ctx)
        assert result.passed is True

    def test_check_fails_when_node_missing(self) -> None:
        from token_world.mechanic.seeds.contains_edge_watcher import ContainsEdgeWatcherMechanic

        kg = KnowledgeGraph()
        kg.add_node("actor", node_type="agent")
        ctx = MechanicContext(kg, actor="actor", target="missing_chest")
        result = ContainsEdgeWatcherMechanic().check(ctx)
        assert result.passed is False

    def test_apply_writes_item_count(self) -> None:
        from token_world.mechanic.seeds.contains_edge_watcher import ContainsEdgeWatcherMechanic

        _, ctx = _kg_with_container()
        mutations = ContainsEdgeWatcherMechanic().apply(ctx)
        assert len(mutations) == 1
        assert mutations[0].property == "item_count"
        assert mutations[0].new_value == 1

    def test_apply_counts_multiple_items(self) -> None:
        from token_world.mechanic.seeds.contains_edge_watcher import ContainsEdgeWatcherMechanic

        kg = KnowledgeGraph()
        kg.add_node("chest", node_type="entity")
        kg.set("chest", "subtype", "container")
        for i in range(3):
            kg.add_node(f"item_{i}", node_type="entity")
            kg.add_edge("chest", f"item_{i}", relation="contains")
        ctx = MechanicContext(kg, actor="chest", target="chest")
        mutations = ContainsEdgeWatcherMechanic().apply(ctx)
        assert mutations[0].new_value == 3

    def test_voluntary_is_false(self) -> None:
        from token_world.mechanic.seeds.contains_edge_watcher import ContainsEdgeWatcherMechanic

        assert ContainsEdgeWatcherMechanic.voluntary is False


# ---------------------------------------------------------------------------
# temperature_watcher
# ---------------------------------------------------------------------------


def _kg_with_temp(temp: float) -> tuple[KnowledgeGraph, MechanicContext]:
    kg = KnowledgeGraph()
    kg.add_node("brazier", node_type="entity")
    kg.set("brazier", "temperature", temp)
    ctx = MechanicContext(kg, actor="brazier", target="brazier")
    return kg, ctx


class TestTemperatureWatcher:
    def test_watches_temperature_property_matcher(self) -> None:
        from token_world.mechanic.seeds.temperature_watcher import TemperatureWatcherMechanic

        m = TemperatureWatcherMechanic()
        watchers = m.watches()
        assert len(watchers) == 1
        assert isinstance(watchers[0], PropertyChangeMatcher)
        assert watchers[0].property_name == "temperature"

    def test_check_passes_with_numeric_temperature(self) -> None:
        from token_world.mechanic.seeds.temperature_watcher import TemperatureWatcherMechanic

        _, ctx = _kg_with_temp(25.0)
        result = TemperatureWatcherMechanic().check(ctx)
        assert result.passed is True

    def test_check_fails_when_no_temperature(self) -> None:
        from token_world.mechanic.seeds.temperature_watcher import TemperatureWatcherMechanic

        kg = KnowledgeGraph()
        kg.add_node("thing", node_type="entity")
        ctx = MechanicContext(kg, actor="thing", target="thing")
        result = TemperatureWatcherMechanic().check(ctx)
        assert result.passed is False

    def test_check_fails_when_temperature_non_numeric(self) -> None:
        from token_world.mechanic.seeds.temperature_watcher import TemperatureWatcherMechanic

        kg = KnowledgeGraph()
        kg.add_node("thing", node_type="entity")
        kg.set("thing", "temperature", "hot")
        ctx = MechanicContext(kg, actor="thing", target="thing")
        result = TemperatureWatcherMechanic().check(ctx)
        assert result.passed is False

    @pytest.mark.parametrize(
        "temp,expected_label",
        [
            (-10, "freezing"),
            (0, "freezing"),
            (5, "freezing"),
            (10, "cold"),
            (20, "cold"),
            (25, "warm"),
            (50, "warm"),
            (60, "hot"),
            (90, "hot"),
            (100, "scorching"),
            (200, "scorching"),
        ],
    )
    def test_apply_writes_correct_temp_state(self, temp: float, expected_label: str) -> None:
        from token_world.mechanic.seeds.temperature_watcher import TemperatureWatcherMechanic

        _, ctx = _kg_with_temp(temp)
        mutations = TemperatureWatcherMechanic().apply(ctx)
        assert len(mutations) == 1
        assert mutations[0].property == "temp_state"
        assert mutations[0].new_value == expected_label

    def test_voluntary_is_false(self) -> None:
        from token_world.mechanic.seeds.temperature_watcher import TemperatureWatcherMechanic

        assert TemperatureWatcherMechanic.voluntary is False


# ---------------------------------------------------------------------------
# Registry audit — all three mechanics are auto-discovered from seeds/
# ---------------------------------------------------------------------------


def _seeds_registry(tmp_path_factory: pytest.TempPathFactory):
    """Build a MechanicRegistry by scanning a copy of the seeds/ directory."""
    import os
    import shutil
    import subprocess
    from pathlib import Path

    from token_world.mechanic.registry import MechanicRegistry

    seeds_dir = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "src"
        / "token_world"
        / "mechanic"
        / "seeds"
    )
    tmp = tmp_path_factory.mktemp("seeds_reg")
    mechanics_dir = tmp / "mechanics"
    mechanics_dir.mkdir()
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
    subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"],
        cwd=tmp,
        check=True,
        capture_output=True,
        env=git_env,
    )

    reg = MechanicRegistry(mechanics_dir)
    reg.scan()
    return reg


class TestRegistryAudit:
    """All three chain seed mechanics must be discoverable via the registry."""

    def test_mood_change_watcher_registered(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        reg = _seeds_registry(tmp_path_factory)
        ids = {m.id for m in reg.list_mechanics()}
        assert "mood_change_watcher" in ids, (
            "mood_change_watcher must be auto-registered from seeds/"
        )

    def test_contains_edge_watcher_registered(
        self, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        reg = _seeds_registry(tmp_path_factory)
        ids = {m.id for m in reg.list_mechanics()}
        assert "contains_edge_watcher" in ids, (
            "contains_edge_watcher must be auto-registered from seeds/"
        )

    def test_temperature_watcher_registered(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        reg = _seeds_registry(tmp_path_factory)
        ids = {m.id for m in reg.list_mechanics()}
        assert "temperature_watcher" in ids, (
            "temperature_watcher must be auto-registered from seeds/"
        )
