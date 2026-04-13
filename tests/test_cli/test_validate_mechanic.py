"""CLI tests for ``token-world validate-mechanic``."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from click.testing import CliRunner

from token_world.cli import cli

_SEEDS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "src" / "token_world" / "mechanic" / "seeds"
)


_OK_MECHANIC_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations
    from token_world.graph import Mutation
    from token_world.mechanic.protocol import CheckResult, Mechanic


    class T(Mechanic):
        id = "t"
        description = "test"
        voluntary = True
        tags: list[str] = []

        def check(self, ctx):
            return CheckResult(passed=False, reasons=["no"])

        def apply(self, ctx):
            return []
    """
)


def test_validates_valid_seed_module() -> None:
    """Running the CLI with a direct seed path prints PASS and exits 0."""
    runner = CliRunner()
    seed_path = _SEEDS_DIR / "movement.py"
    assert seed_path.is_file()
    result = runner.invoke(cli, ["validate-mechanic", str(seed_path)])
    assert result.exit_code == 0, result.output
    assert "PASS" in result.output


def test_reports_forbidden_import_as_fail(tmp_path: Path) -> None:
    """A mechanic that imports networkx -> exit 1 + forbidden_import in output."""
    runner = CliRunner()
    bad = tmp_path / "bad.py"
    bad.write_text(
        textwrap.dedent(
            """\
            import networkx
            from token_world.mechanic.protocol import CheckResult, Mechanic


            class M(Mechanic):
                id = "bad"
                description = "d"
                def check(self, ctx): return CheckResult(passed=False)
                def apply(self, ctx): return []
            """
        ),
        encoding="utf-8",
    )
    result = runner.invoke(cli, ["validate-mechanic", str(bad)])
    assert result.exit_code == 1, result.output
    assert "forbidden_import" in result.output
    assert "networkx" in result.output


def test_format_json_emits_valid_json(tmp_path: Path) -> None:
    """``--format json`` emits a parsable JSON object with the expected keys."""
    runner = CliRunner()
    path = tmp_path / "t.py"
    path.write_text(_OK_MECHANIC_SOURCE, encoding="utf-8")
    result = runner.invoke(cli, ["validate-mechanic", str(path), "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert set(payload.keys()) == {"module_path", "passed", "findings"}
    assert payload["passed"] is True
    assert isinstance(payload["findings"], list)


def test_cli_missing_mechanic_id_errors(tmp_path: Path, monkeypatch) -> None:
    """Slug-mode without a mechanic-id -> exit 2 + clear error."""
    # Point XDG_DATA_HOME at a tmp dir so the UniverseManager lookup fails
    # with a deterministic 'slug not found' rather than consulting the real
    # home directory.
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    runner = CliRunner()
    result = runner.invoke(cli, ["validate-mechanic", "nonexistent-slug"])
    # No second arg -> should hit the "mechanic-id is required" branch.
    assert result.exit_code == 2, result.output
    assert "mechanic-id is required" in result.output


def test_exit_code_matches_pass_fail(tmp_path: Path, monkeypatch) -> None:
    """Explicit exit-code contract: valid=0, invalid=1, resolver-error=2."""
    runner = CliRunner()

    # 0 -- valid mechanic (direct path)
    good = tmp_path / "good.py"
    good.write_text(_OK_MECHANIC_SOURCE, encoding="utf-8")
    result_pass = runner.invoke(cli, ["validate-mechanic", str(good)])
    assert result_pass.exit_code == 0, result_pass.output

    # 1 -- invalid mechanic (bare eval call)
    bad = tmp_path / "bad.py"
    bad.write_text(
        textwrap.dedent(
            """\
            from token_world.mechanic.protocol import CheckResult, Mechanic


            class M(Mechanic):
                id = "bad"
                description = "d"
                def check(self, ctx):
                    eval("1+1")
                    return CheckResult(passed=False)
                def apply(self, ctx): return []
            """
        ),
        encoding="utf-8",
    )
    result_fail = runner.invoke(cli, ["validate-mechanic", str(bad)])
    assert result_fail.exit_code == 1, result_fail.output

    # 2 -- resolver error (unknown universe slug)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    result_resolver = runner.invoke(cli, ["validate-mechanic", "no-such-universe", "some-mech"])
    assert result_resolver.exit_code == 2, result_resolver.output
