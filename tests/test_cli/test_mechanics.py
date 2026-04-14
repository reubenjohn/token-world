"""Tests for ``token_world.inspect.mechanics`` and ``token-world mechanics``."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from token_world.cli import cli
from token_world.inspect.mechanics import aggregate, render_json, render_table
from token_world.universe.manager import UniverseManager

_SEED_MODULE_TEMPLATE = '''"""{description}"""
from __future__ import annotations
from typing import TYPE_CHECKING
from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

{author_line}
if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class TestMech_{mech_id_suffix}(Mechanic):
    id = "{mech_id}"
    description = "{description}"
    voluntary = {voluntary}
    tags: list[str] = [{tags_list}]

    def check(self, ctx: "MechanicContext") -> CheckResult:
        return CheckResult(passed=True)

    def apply(self, ctx: "MechanicContext") -> list[Mutation]:
        return []
'''


def _write_mechanic_module(
    mech_dir: Path,
    *,
    mech_id: str,
    description: str = "test mechanic",
    voluntary: bool = True,
    tags: tuple[str, ...] = (),
    verb: str = "do",  # kept for back-compat; unused
    author_marker: bool = False,
) -> Path:
    """Drop a minimal-but-valid Mechanic module into ``mech_dir``."""
    del verb  # kept for arg compat
    tags_list = ", ".join(f'"{t}"' for t in tags)
    author_line = '__author__ = "operator"' if author_marker else ""
    body = _SEED_MODULE_TEMPLATE.format(
        mech_id=mech_id,
        mech_id_suffix=mech_id.replace("-", "_"),
        description=description,
        voluntary="True" if voluntary else "False",
        tags_list=tags_list,
        author_line=author_line,
    )
    path = mech_dir / f"{mech_id}.py"
    path.write_text(body, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# aggregate() unit tests
# ---------------------------------------------------------------------------


def test_aggregate_no_mechanics_dir(fake_universe: Path) -> None:
    """A universe with an empty mechanics dir yields an empty report."""
    shutil.rmtree(fake_universe / "mechanics")
    report = aggregate(fake_universe, slug="t")
    assert report.mechanics == []


def test_aggregate_lists_seed_mechanics(fake_universe: Path) -> None:
    _write_mechanic_module(fake_universe / "mechanics", mech_id="walk", verb="walk")
    _write_mechanic_module(fake_universe / "mechanics", mech_id="look", verb="look")
    report = aggregate(fake_universe, slug="t")
    ids = [m.id for m in report.mechanics]
    assert sorted(ids) == ["look", "walk"]
    for row in report.mechanics:
        assert row.author == "seed"
        assert row.call_count == 0
        assert row.last_invoked_tick is None


def test_aggregate_classifies_operator_authored(fake_universe: Path) -> None:
    _write_mechanic_module(fake_universe / "mechanics", mech_id="walk", verb="walk")
    _write_mechanic_module(
        fake_universe / "mechanics",
        mech_id="hack",
        verb="hack",
        author_marker=True,
    )
    report = aggregate(fake_universe, slug="t")
    by_id = {m.id: m for m in report.mechanics}
    assert by_id["walk"].author == "seed"
    assert by_id["hack"].author == "operator"


def test_aggregate_author_filter(fake_universe: Path) -> None:
    _write_mechanic_module(fake_universe / "mechanics", mech_id="walk", verb="walk")
    _write_mechanic_module(
        fake_universe / "mechanics",
        mech_id="hack",
        verb="hack",
        author_marker=True,
    )
    only_op = aggregate(fake_universe, slug="t", author_filter="operator")
    assert [m.id for m in only_op.mechanics] == ["hack"]
    only_seed = aggregate(fake_universe, slug="t", author_filter="seed")
    assert [m.id for m in only_seed.mechanics] == ["walk"]


def test_aggregate_call_counts_and_last_tick(fake_universe: Path, write_tick) -> None:
    """Call counts come from ticks where the mechanic matched."""
    _write_mechanic_module(fake_universe / "mechanics", mech_id="walk", verb="walk")
    _write_mechanic_module(fake_universe / "mechanics", mech_id="look", verb="look")
    ticks_dir = fake_universe / "tick_summaries" / "ticks"
    write_tick(ticks_dir, "1", matched_mechanic_id="walk")
    write_tick(ticks_dir, "2", matched_mechanic_id="walk")
    write_tick(ticks_dir, "5", matched_mechanic_id="walk")
    write_tick(ticks_dir, "3", matched_mechanic_id="look")
    write_tick(ticks_dir, "4")  # no mechanic match
    report = aggregate(fake_universe, slug="t")
    by_id = {m.id: m for m in report.mechanics}
    assert by_id["walk"].call_count == 3
    assert by_id["walk"].last_invoked_tick == "5"
    assert by_id["look"].call_count == 1
    assert by_id["look"].last_invoked_tick == "3"


# ---------------------------------------------------------------------------
# Renderer unit tests
# ---------------------------------------------------------------------------


def test_render_table_smoke(fake_universe: Path) -> None:
    _write_mechanic_module(fake_universe / "mechanics", mech_id="walk", verb="walk")
    report = aggregate(fake_universe, slug="t")
    out = render_table(report)
    assert "Mechanics Registry: t" in out
    assert "walk" in out


def test_render_json_valid(fake_universe: Path) -> None:
    _write_mechanic_module(fake_universe / "mechanics", mech_id="walk", verb="walk")
    report = aggregate(fake_universe, slug="t")
    payload = json.loads(render_json(report))
    assert payload["slug"] == "t"
    assert payload["author_filter"] is None
    assert any(m["id"] == "walk" for m in payload["mechanics"])


def test_render_table_empty() -> None:
    from token_world.inspect.mechanics import MechanicsReport

    out = render_table(MechanicsReport(slug="t"))
    assert "(no mechanics matched)" in out


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def _mk_universe_with_mech(
    tmp_data_dir: Path, name: str, mech_id: str = "walk"
) -> tuple[str, Path]:
    mgr = UniverseManager(data_dir=tmp_data_dir)
    universe_dir = mgr.create(name)
    _write_mechanic_module(universe_dir / "mechanics", mech_id=mech_id, verb=mech_id)
    return universe_dir.name, universe_dir


def test_cli_unknown_universe_exits_1(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    runner = CliRunner()
    result = runner.invoke(cli, ["mechanics", "nope"])
    assert result.exit_code == 1


def test_cli_table_smoke(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, _ = _mk_universe_with_mech(tmp_data_dir, "mech tab")
    runner = CliRunner()
    result = runner.invoke(cli, ["mechanics", slug])
    assert result.exit_code == 0, result.output
    assert "Mechanics Registry" in result.output
    assert "walk" in result.output


def test_cli_json_is_valid_json(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, _ = _mk_universe_with_mech(tmp_data_dir, "mech json")
    runner = CliRunner()
    result = runner.invoke(cli, ["mechanics", slug, "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["slug"] == slug
    assert "mechanics" in payload


def test_cli_author_filter(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_data_dir.parent.parent))
    slug, universe_dir = _mk_universe_with_mech(tmp_data_dir, "mech filter")
    _write_mechanic_module(
        universe_dir / "mechanics",
        mech_id="hack",
        verb="hack",
        author_marker=True,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["mechanics", slug, "--author", "operator", "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    ids = [m["id"] for m in payload["mechanics"]]
    assert ids == ["hack"]
