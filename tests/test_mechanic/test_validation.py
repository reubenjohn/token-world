"""Unit tests for the mechanic validation pipeline (MECH-04).

Covers every stage (syntax -> ast -> import -> contract -> tests -> smoke)
and every AST rule from D-14. All tests author minimal mechanic modules
under ``tmp_path`` so nothing is written into the checked-in tree.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from token_world.mechanic.validation import (
    FORBIDDEN_CALL_NAMES,
    FORBIDDEN_IMPORT_PREFIXES,
    ValidationFinding,
    ValidationReport,
    validate,
)

# ---------------------------------------------------------------------------
# Module-level smoke assertions (Task 1 acceptance: constants match D-14)
# ---------------------------------------------------------------------------


def test_forbidden_call_names_match_d14() -> None:
    assert (
        frozenset({"eval", "exec", "__import__", "compile", "globals", "open"})
        == FORBIDDEN_CALL_NAMES
    )


def test_forbidden_import_prefixes_contain_required_entries() -> None:
    assert "networkx" in FORBIDDEN_IMPORT_PREFIXES
    assert "token_world.graph.knowledge_graph" in FORBIDDEN_IMPORT_PREFIXES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_OK_MECHANIC_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations
    from token_world.graph import Mutation
    from token_world.mechanic.protocol import CheckResult, Mechanic


    class TMechanic(Mechanic):
        id = "t"
        description = "test mechanic"
        voluntary = True
        tags: list[str] = []

        def check(self, ctx):
            return CheckResult(passed=False, reasons=["test refusal"])

        def apply(self, ctx):
            return []
    """
)


def _write_mechanic(tmp_path: Path, name: str, source: str) -> Path:
    """Write *source* to ``<tmp_path>/<name>.py`` and return the path."""
    path = tmp_path / f"{name}.py"
    path.write_text(source, encoding="utf-8")
    return path


def _findings_by_stage(report: ValidationReport, stage: str) -> list[ValidationFinding]:
    return [f for f in report.findings if f.stage == stage]


def _findings_by_rule(report: ValidationReport, rule: str) -> list[ValidationFinding]:
    return [f for f in report.findings if f.rule == rule]


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


def test_passes_valid_mechanic(tmp_path: Path) -> None:
    """A minimal, clean Mechanic subclass passes the pipeline."""
    path = _write_mechanic(tmp_path, "t", _OK_MECHANIC_SOURCE)
    report = validate(path)
    assert report.passed is True
    # No error-severity findings
    errors = [f for f in report.findings if f.severity == "error"]
    assert errors == []


# ---------------------------------------------------------------------------
# 2. Syntax stage
# ---------------------------------------------------------------------------


def test_syntax_error_fails_stage_syntax(tmp_path: Path) -> None:
    """Un-parseable source fails at the syntax stage with line/col."""
    path = _write_mechanic(tmp_path, "broken", "def foo(:\n    pass\n")
    report = validate(path)
    assert report.passed is False
    syntax_findings = _findings_by_stage(report, "syntax")
    assert len(syntax_findings) == 1
    f = syntax_findings[0]
    assert f.rule == "parse_error"
    assert f.severity == "error"
    assert f.line is not None
    # Pipeline stopped at syntax -- no ast/import findings
    assert _findings_by_stage(report, "ast") == []
    assert _findings_by_stage(report, "import") == []


# ---------------------------------------------------------------------------
# 3-5. AST stage -- forbidden imports
# ---------------------------------------------------------------------------


def test_forbidden_import_networkx(tmp_path: Path) -> None:
    """``import networkx`` is flagged by the AST stage."""
    source = textwrap.dedent(
        """\
        import networkx
        from token_world.mechanic.protocol import CheckResult, Mechanic


        class M(Mechanic):
            id = "m"
            description = "d"
            def check(self, ctx): return CheckResult(passed=False)
            def apply(self, ctx): return []
        """
    )
    path = _write_mechanic(tmp_path, "m", source)
    report = validate(path)
    assert report.passed is False
    hits = _findings_by_rule(report, "forbidden_import")
    assert len(hits) >= 1
    assert any("networkx" in f.message for f in hits)
    assert all(f.stage == "ast" for f in hits)


def test_forbidden_import_from_networkx_utils(tmp_path: Path) -> None:
    """``from networkx.utils import X`` is flagged."""
    source = textwrap.dedent(
        """\
        from networkx.utils import foo
        from token_world.mechanic.protocol import CheckResult, Mechanic


        class M(Mechanic):
            id = "m"
            description = "d"
            def check(self, ctx): return CheckResult(passed=False)
            def apply(self, ctx): return []
        """
    )
    path = _write_mechanic(tmp_path, "m", source)
    report = validate(path)
    assert report.passed is False
    hits = _findings_by_rule(report, "forbidden_import")
    assert any("networkx.utils" in f.message for f in hits)


def test_forbidden_import_knowledge_graph(tmp_path: Path) -> None:
    """Direct import of the internal knowledge_graph module is flagged."""
    source = textwrap.dedent(
        """\
        from token_world.graph.knowledge_graph import KnowledgeGraph
        from token_world.mechanic.protocol import CheckResult, Mechanic


        class M(Mechanic):
            id = "m"
            description = "d"
            def check(self, ctx): return CheckResult(passed=False)
            def apply(self, ctx): return []
        """
    )
    path = _write_mechanic(tmp_path, "m", source)
    report = validate(path)
    assert report.passed is False
    hits = _findings_by_rule(report, "forbidden_import")
    assert any("token_world.graph.knowledge_graph" in f.message for f in hits)


# ---------------------------------------------------------------------------
# 6-7. AST stage -- forbidden calls
# ---------------------------------------------------------------------------


def test_forbidden_call_eval(tmp_path: Path) -> None:
    """Bare ``eval("...")`` inside a method body is flagged."""
    source = textwrap.dedent(
        """\
        from token_world.mechanic.protocol import CheckResult, Mechanic


        class M(Mechanic):
            id = "m"
            description = "d"

            def check(self, ctx):
                eval("1 + 1")
                return CheckResult(passed=False)

            def apply(self, ctx):
                return []
        """
    )
    path = _write_mechanic(tmp_path, "m", source)
    report = validate(path)
    assert report.passed is False
    hits = _findings_by_rule(report, "forbidden_call")
    assert any("eval" in f.message for f in hits)
    assert all(f.stage == "ast" for f in hits)


def test_forbidden_call_exec_and_open_accumulate(tmp_path: Path) -> None:
    """Both ``exec`` and ``open`` at module level -> two findings (accumulate, no short-circuit)."""
    source = textwrap.dedent(
        """\
        exec("x = 1")
        open("/tmp/ignored")
        from token_world.mechanic.protocol import CheckResult, Mechanic


        class M(Mechanic):
            id = "m"
            description = "d"
            def check(self, ctx): return CheckResult(passed=False)
            def apply(self, ctx): return []
        """
    )
    path = _write_mechanic(tmp_path, "m", source)
    report = validate(path)
    assert report.passed is False
    hits = _findings_by_rule(report, "forbidden_call")
    names_flagged = {
        msg_word for f in hits for msg_word in ("exec", "open") if msg_word in f.message
    }
    assert "exec" in names_flagged
    assert "open" in names_flagged


def test_attribute_eval_is_allowed(tmp_path: Path) -> None:
    """``foo.eval()`` (attribute call) is NOT flagged -- only bare-name calls are."""
    source = textwrap.dedent(
        """\
        from token_world.mechanic.protocol import CheckResult, Mechanic


        class Helper:
            def eval(self):
                return 1


        class M(Mechanic):
            id = "m"
            description = "d"

            def check(self, ctx):
                Helper().eval()
                return CheckResult(passed=False)

            def apply(self, ctx):
                return []
        """
    )
    path = _write_mechanic(tmp_path, "m", source)
    report = validate(path)
    # The attribute call must not produce a forbidden_call finding.
    forbidden_calls = _findings_by_rule(report, "forbidden_call")
    assert forbidden_calls == []


# ---------------------------------------------------------------------------
# 8. AST warning vs. contract error -- "no Mechanic subclass"
# ---------------------------------------------------------------------------


def test_ast_warning_no_mechanic_subclass_does_not_fail_stage_ast(tmp_path: Path) -> None:
    """Module without any Mechanic subclass -> ast warning + contract error of the same rule."""
    source = textwrap.dedent(
        """\
        def helper():
            return 1
        """
    )
    path = _write_mechanic(tmp_path, "helper", source)
    report = validate(path)
    assert report.passed is False

    ast_warnings = [
        f for f in report.findings if f.stage == "ast" and f.rule == "no_mechanic_subclass"
    ]
    assert len(ast_warnings) == 1
    assert ast_warnings[0].severity == "warning"

    # Contract stage should also flag the module (now as an error).
    contract_errors = [
        f for f in report.findings if f.stage == "contract" and f.rule == "no_mechanic_subclass"
    ]
    assert len(contract_errors) == 1
    assert contract_errors[0].severity == "error"


# ---------------------------------------------------------------------------
# 9. Import stage
# ---------------------------------------------------------------------------


def test_import_failure_fails_stage_import(tmp_path: Path) -> None:
    """Valid AST + missing symbol at import -> stage 'import' error."""
    source = textwrap.dedent(
        """\
        from token_world.nonexistent import Foo  # type: ignore[import-not-found]
        from token_world.mechanic.protocol import CheckResult, Mechanic


        class M(Mechanic):
            id = "m"
            description = "d"
            def check(self, ctx): return CheckResult(passed=False)
            def apply(self, ctx): return []
        """
    )
    path = _write_mechanic(tmp_path, "m", source)
    report = validate(path)
    assert report.passed is False
    import_findings = _findings_by_stage(report, "import")
    assert len(import_findings) == 1
    assert import_findings[0].rule == "import_failed"


# ---------------------------------------------------------------------------
# 10-12. Contract stage
# ---------------------------------------------------------------------------


def test_missing_id_attr_fails_contract(tmp_path: Path) -> None:
    """Mechanic subclass without class-level ``id`` -> contract error."""
    source = textwrap.dedent(
        """\
        from token_world.mechanic.protocol import CheckResult, Mechanic


        class M(Mechanic):
            description = "d"
            def check(self, ctx): return CheckResult(passed=False)
            def apply(self, ctx): return []
        """
    )
    path = _write_mechanic(tmp_path, "m", source)
    report = validate(path)
    assert report.passed is False
    missing = _findings_by_rule(report, "missing_id_attr")
    assert len(missing) == 1
    assert missing[0].stage == "contract"


def test_missing_description_fails_contract(tmp_path: Path) -> None:
    """Mechanic subclass without class-level ``description`` -> contract error."""
    source = textwrap.dedent(
        """\
        from token_world.mechanic.protocol import CheckResult, Mechanic


        class M(Mechanic):
            id = "m"
            def check(self, ctx): return CheckResult(passed=False)
            def apply(self, ctx): return []
        """
    )
    path = _write_mechanic(tmp_path, "m", source)
    report = validate(path)
    assert report.passed is False
    missing = _findings_by_rule(report, "missing_description_attr")
    assert len(missing) == 1
    assert missing[0].stage == "contract"


def test_invalid_check_signature_fails_contract(tmp_path: Path) -> None:
    """``check(self, actor, target)`` (wrong signature) -> contract error."""
    source = textwrap.dedent(
        """\
        from token_world.mechanic.protocol import CheckResult, Mechanic


        class M(Mechanic):
            id = "m"
            description = "d"

            def check(self, actor, target):
                return CheckResult(passed=False)

            def apply(self, ctx):
                return []
        """
    )
    path = _write_mechanic(tmp_path, "m", source)
    report = validate(path)
    assert report.passed is False
    bad = _findings_by_rule(report, "invalid_check_signature")
    assert len(bad) == 1
    assert bad[0].stage == "contract"


# ---------------------------------------------------------------------------
# 13-14. Smoke stage
# ---------------------------------------------------------------------------


def test_smoke_stage_catches_runtime_exception(tmp_path: Path) -> None:
    """A mechanic whose ``check`` raises -> smoke-stage error."""
    source = textwrap.dedent(
        """\
        from token_world.mechanic.protocol import CheckResult, Mechanic


        class M(Mechanic):
            id = "m"
            description = "d"

            def check(self, ctx):
                raise RuntimeError("boom")

            def apply(self, ctx):
                return []
        """
    )
    path = _write_mechanic(tmp_path, "m", source)
    report = validate(path)
    assert report.passed is False
    smoke = _findings_by_stage(report, "smoke")
    assert len(smoke) == 1
    assert smoke[0].rule == "smoke_raised"
    assert "RuntimeError" in smoke[0].message


def test_smoke_stage_accepts_checkresult_false(tmp_path: Path) -> None:
    """``CheckResult(passed=False)`` is valid behavior -- pipeline passes overall."""
    path = _write_mechanic(tmp_path, "t", _OK_MECHANIC_SOURCE)
    report = validate(path)
    assert report.passed is True


# ---------------------------------------------------------------------------
# 15-16. Tests stage
# ---------------------------------------------------------------------------


def test_tests_stage_skipped_with_warning_when_no_test_file(tmp_path: Path) -> None:
    """No sibling test file -> warning, pipeline still passes overall if smoke passes."""
    # Author the mechanic in a tmp dir with no mechanics/ ancestor structure --
    # neither the universe-layout test path nor the project-seed test path
    # will resolve on disk.
    path = _write_mechanic(tmp_path, "t", _OK_MECHANIC_SOURCE)
    report = validate(path, run_tests=True)
    warnings = [f for f in report.findings if f.stage == "tests" and f.rule == "no_tests_found"]
    assert len(warnings) == 1
    assert warnings[0].severity == "warning"
    # Pipeline still passes (only warnings in tests stage)
    assert report.passed is True


def test_tests_stage_fails_when_pytest_fails(tmp_path: Path) -> None:
    """Sibling test file with a failing assertion -> stage 'tests' error."""
    # Build the universe-style layout expected by _candidate_test_paths:
    #   <tmp_path>/mechanics/<id>.py
    #   <tmp_path>/tests/test_mechanics/test_<id>.py
    mechanics = tmp_path / "mechanics"
    mechanics.mkdir()
    mech_path = mechanics / "t.py"
    mech_path.write_text(_OK_MECHANIC_SOURCE, encoding="utf-8")

    tests_dir = tmp_path / "tests" / "test_mechanics"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_t.py").write_text(
        "def test_always_fails():\n    assert False, 'intentional fail'\n",
        encoding="utf-8",
    )

    report = validate(mech_path, run_tests=True)
    assert report.passed is False
    tests_findings = _findings_by_stage(report, "tests")
    assert any(f.rule == "tests_failed" for f in tests_findings)


def test_tests_stage_passes_with_passing_sibling_test(tmp_path: Path) -> None:
    """Sibling test file that passes -> no tests-stage findings; overall pass."""
    mechanics = tmp_path / "mechanics"
    mechanics.mkdir()
    mech_path = mechanics / "t.py"
    mech_path.write_text(_OK_MECHANIC_SOURCE, encoding="utf-8")

    tests_dir = tmp_path / "tests" / "test_mechanics"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_t.py").write_text(
        "def test_trivial():\n    assert True\n",
        encoding="utf-8",
    )

    report = validate(mech_path, run_tests=True)
    assert report.passed is True
    tests_errors = [f for f in report.findings if f.stage == "tests" and f.severity == "error"]
    assert tests_errors == []


def test_default_skips_stage_tests_to_prevent_fork_bomb(tmp_path: Path) -> None:
    """``validate(path)`` (default ``run_tests=False``) must not subprocess pytest.

    Regression guard: MechanicRegistry.scan() calls validate() on every
    mechanic. Before this fix, each scan forked ``python -m pytest`` per
    mechanic; the integration harness built a registry per test (35 UCs
    x N seeds = 500+ nested pytest processes), crashing the machine.

    Stage 5 is now opt-in via ``run_tests=True`` and reserved for the CLI.
    """
    from unittest.mock import patch

    mechanics = tmp_path / "mechanics"
    mechanics.mkdir()
    mech_path = mechanics / "t.py"
    mech_path.write_text(_OK_MECHANIC_SOURCE, encoding="utf-8")

    tests_dir = tmp_path / "tests" / "test_mechanics"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_t.py").write_text(
        "def test_trivial():\n    assert True\n",
        encoding="utf-8",
    )

    with patch("token_world.mechanic.validation.subprocess.run") as mock_run:
        report = validate(mech_path)  # no run_tests kwarg -> default False
    assert mock_run.call_count == 0, (
        "validate() default must not spawn subprocess pytest -- "
        "fork-bomb regression (see hotfix commit)."
    )
    assert report.passed is True
    # Stage 5 was skipped, so no tests-stage findings at all.
    tests_findings = [f for f in report.findings if f.stage == "tests"]
    assert tests_findings == []


# ---------------------------------------------------------------------------
# ValidationReport.to_dict schema (consumed by 04-03 diagnostics sink)
# ---------------------------------------------------------------------------


def test_to_dict_schema_is_stable(tmp_path: Path) -> None:
    """``ValidationReport.to_dict()`` has the keys 04-03 will index on."""
    path = _write_mechanic(tmp_path, "t", _OK_MECHANIC_SOURCE)
    report = validate(path)
    d = report.to_dict()
    assert set(d.keys()) == {"module_path", "passed", "findings"}
    assert isinstance(d["module_path"], str)
    assert isinstance(d["passed"], bool)
    assert isinstance(d["findings"], list)
    for finding in d["findings"]:
        assert set(finding.keys()) >= {
            "stage",
            "rule",
            "severity",
            "message",
            "path",
            "line",
            "col",
        }
