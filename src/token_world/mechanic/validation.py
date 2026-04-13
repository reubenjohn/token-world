"""Validation pipeline for mechanic modules (MECH-04).

Single entry :func:`validate` runs the 6-stage pipeline per D-12/D-13:

1. **syntax** -- ``ast.parse`` the source.
2. **ast** -- walk the tree and enforce D-14 rules (forbidden imports /
   forbidden calls / at least one ``Mechanic`` subclass).
3. **import** -- ``importlib`` runs the module-level code.
4. **contract** -- each concrete ``Mechanic`` subclass declares ``id``,
   ``description`` and defines ``check`` / ``apply`` with signature
   ``(self, ctx)``.
5. **tests** -- invoke ``pytest`` on the mirrored sibling test file if it
   exists.
6. **smoke** -- instantiate and call ``check`` with a minimal fixture
   :class:`MechanicContext`.

Stages stop at the first hard-failing stage but accumulate *all* findings
produced within that stage before bailing. Warnings never stop the
pipeline.

The result is a :class:`ValidationReport` carrying the module path, the
accumulated :class:`ValidationFinding` list, and an overall ``passed``
flag. :meth:`ValidationReport.to_dict` provides the JSON-serialisable
shape consumed by the diagnostics sink in 04-03 and by the
``validate-mechanic`` CLI's ``--format json``.

AST rules per D-14:

- ``FORBIDDEN_IMPORT_PREFIXES``: ``networkx``, ``token_world.graph.knowledge_graph``.
- ``FORBIDDEN_CALL_NAMES``: ``eval``, ``exec``, ``__import__``, ``compile``,
  ``globals``, bare ``open``.

Per T-04-FORBIDDEN-ATTR-CALL, only bare-name calls are flagged; attribute
calls (``foo.eval()``) are intentionally allowed -- the AST rules are a
reasonable-effort pre-runtime control, not a sandbox (v1 decision).
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from token_world.mechanic.protocol import Mechanic

FORBIDDEN_CALL_NAMES: frozenset[str] = frozenset(
    {
        "eval",
        "exec",
        "__import__",
        "compile",
        "globals",
        "open",
    }
)

FORBIDDEN_IMPORT_PREFIXES: tuple[str, ...] = (
    "networkx",
    "token_world.graph.knowledge_graph",
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ValidationFinding:
    """A single structured diagnostic emitted by a validation stage.

    Attributes:
        stage: One of ``"syntax" | "ast" | "import" | "contract" | "tests" | "smoke"``.
        rule: Short identifier (e.g. ``"forbidden_import"``, ``"missing_id_attr"``).
        severity: ``"error"`` (fails the stage) or ``"warning"`` (accumulates only).
        message: Human-readable explanation.
        path: Path to the module the finding applies to (stringified).
        line: Optional source line (``1``-based) for AST / syntax findings.
        col: Optional source column (``0``-based) for AST / syntax findings.
    """

    stage: str
    rule: str
    severity: str
    message: str
    path: str
    line: int | None = None
    col: int | None = None


@dataclass
class ValidationReport:
    """Aggregate result of running :func:`validate` on a mechanic module.

    Attributes:
        module_path: The mechanic module under validation.
        findings: Every finding emitted by the pipeline, in stage order.
        passed: ``True`` unless an ``error``-severity finding was appended.
    """

    module_path: Path
    findings: list[ValidationFinding] = field(default_factory=list)
    passed: bool = True

    def add(self, finding: ValidationFinding) -> None:
        """Append *finding*; flip ``passed`` to ``False`` on error severity."""
        self.findings.append(finding)
        if finding.severity == "error":
            self.passed = False

    def to_dict(self) -> dict:
        """Return a JSON-serialisable representation.

        Schema (consumed by 04-03 diagnostics sink and ``--format json``)::

            {
                "module_path": "<str>",
                "passed": <bool>,
                "findings": [
                    {"stage": ..., "rule": ..., "severity": ...,
                     "message": ..., "path": ..., "line": ..., "col": ...},
                    ...
                ],
            }
        """
        return {
            "module_path": str(self.module_path),
            "passed": self.passed,
            "findings": [asdict(f) for f in self.findings],
        }


# ---------------------------------------------------------------------------
# AST walker (D-14)
# ---------------------------------------------------------------------------


class _MechanicAstVisitor(ast.NodeVisitor):
    """Walks a mechanic module AST accumulating D-14 rule violations.

    After ``visit(tree)``, callers inspect:

    - ``self.errors``: :class:`ValidationFinding` objects (severity ``error``).
    - ``self.mechanic_classes``: ``ClassDef`` nodes whose bases include a
      name identified as ``"Mechanic"`` (direct inheritance only --
      transitive chains surface at the contract stage per Pitfall 1).
    """

    def __init__(self, module_path: Path) -> None:
        self._module_path = module_path
        self.errors: list[ValidationFinding] = []
        self.mechanic_classes: list[ast.ClassDef] = []

    # -- imports --

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802 (ast API)
        for alias in node.names:
            name = alias.name or ""
            if self._is_forbidden_import(name):
                self.errors.append(
                    ValidationFinding(
                        stage="ast",
                        rule="forbidden_import",
                        severity="error",
                        message=f"Forbidden import: {name!r}",
                        path=str(self._module_path),
                        line=node.lineno,
                        col=node.col_offset,
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        module = node.module or ""
        if self._is_forbidden_import(module):
            self.errors.append(
                ValidationFinding(
                    stage="ast",
                    rule="forbidden_import",
                    severity="error",
                    message=f"Forbidden import: {module!r}",
                    path=str(self._module_path),
                    line=node.lineno,
                    col=node.col_offset,
                )
            )
        self.generic_visit(node)

    # -- calls --

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        # Only flag bare-name calls; attribute calls (``foo.eval()``) are
        # explicitly allowed per T-04-FORBIDDEN-ATTR-CALL.
        if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALL_NAMES:
            self.errors.append(
                ValidationFinding(
                    stage="ast",
                    rule="forbidden_call",
                    severity="error",
                    message=f"Forbidden call: {func.id!r}",
                    path=str(self._module_path),
                    line=node.lineno,
                    col=node.col_offset,
                )
            )
        self.generic_visit(node)

    # -- class definitions --

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "Mechanic":
                self.mechanic_classes.append(node)
                break
            # Attribute form: ``foo.Mechanic`` -- also counts.
            if isinstance(base, ast.Attribute) and base.attr == "Mechanic":
                self.mechanic_classes.append(node)
                break
        self.generic_visit(node)

    # -- helpers --

    @staticmethod
    def _is_forbidden_import(name: str) -> bool:
        for prefix in FORBIDDEN_IMPORT_PREFIXES:
            if name == prefix or name.startswith(prefix + "."):
                return True
        return False


# ---------------------------------------------------------------------------
# Stage implementations
# ---------------------------------------------------------------------------


def _stage_syntax(report: ValidationReport, module_path: Path) -> ast.AST | None:
    """Parse the module source. Returns the AST or ``None`` on parse error."""
    try:
        source = module_path.read_text(encoding="utf-8")
    except OSError as e:
        report.add(
            ValidationFinding(
                stage="syntax",
                rule="read_failed",
                severity="error",
                message=f"Cannot read module: {type(e).__name__}: {e}",
                path=str(module_path),
            )
        )
        return None
    try:
        return ast.parse(source, filename=str(module_path))
    except SyntaxError as e:
        report.add(
            ValidationFinding(
                stage="syntax",
                rule="parse_error",
                severity="error",
                message=f"SyntaxError: {e.msg}",
                path=str(module_path),
                line=e.lineno,
                col=e.offset,
            )
        )
        return None


def _stage_ast(report: ValidationReport, tree: ast.AST, module_path: Path) -> None:
    """Walk the tree; accumulate ALL findings before returning."""
    visitor = _MechanicAstVisitor(module_path)
    visitor.visit(tree)
    for finding in visitor.errors:
        report.add(finding)
    if not visitor.mechanic_classes:
        # Warning, not error: a transitive subclass could still appear at the
        # contract stage (see Pitfall 1). If truly absent, the contract stage
        # surfaces an *error* finding of the same rule.
        report.add(
            ValidationFinding(
                stage="ast",
                rule="no_mechanic_subclass",
                severity="warning",
                message=(
                    "No class in this module directly inherits from Mechanic "
                    "(transitive subclasses checked at contract stage)"
                ),
                path=str(module_path),
            )
        )


def _stage_import(report: ValidationReport, module_path: Path) -> ModuleType | None:
    """Import the module via ``importlib``. Returns the module or ``None``."""
    # Unique-ish module name so repeated validate() calls during tests do not
    # collide in ``sys.modules``.
    module_name = f"_validate_{module_path.stem}_{id(module_path)}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        report.add(
            ValidationFinding(
                stage="import",
                rule="import_failed",
                severity="error",
                message=f"Cannot create module spec for {module_path}",
                path=str(module_path),
            )
        )
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:  # noqa: BLE001 (intentional broad catch at boundary)
        report.add(
            ValidationFinding(
                stage="import",
                rule="import_failed",
                severity="error",
                message=f"{type(e).__name__}: {e}",
                path=str(module_path),
            )
        )
        return None
    return module


def _stage_contract(
    report: ValidationReport, module: ModuleType, module_path: Path
) -> list[type[Mechanic]]:
    """Verify every concrete Mechanic subclass meets the class contract.

    Returns the list of classes that passed the contract checks.
    """
    from token_world.mechanic.protocol import Mechanic

    classes = [
        c
        for _, c in inspect.getmembers(module, inspect.isclass)
        if issubclass(c, Mechanic) and c is not Mechanic and c.__module__ == module.__name__
    ]
    if not classes:
        report.add(
            ValidationFinding(
                stage="contract",
                rule="no_mechanic_subclass",
                severity="error",
                message="Module defines no concrete Mechanic subclass",
                path=str(module_path),
            )
        )
        return []

    passing: list[type[Mechanic]] = []
    for cls in classes:
        cls_ok = True
        # id
        cls_id = getattr(cls, "id", None)
        if cls_id is None or not isinstance(cls_id, str) or cls_id == "":
            report.add(
                ValidationFinding(
                    stage="contract",
                    rule="missing_id_attr",
                    severity="error",
                    message=f"{cls.__name__} missing required class attribute 'id: str'",
                    path=str(module_path),
                )
            )
            cls_ok = False
        elif not isinstance(cls_id, str):
            report.add(
                ValidationFinding(
                    stage="contract",
                    rule="invalid_id_type",
                    severity="error",
                    message=f"{cls.__name__}.id must be str (got {type(cls_id).__name__})",
                    path=str(module_path),
                )
            )
            cls_ok = False
        # description
        cls_desc = getattr(cls, "description", None)
        if cls_desc is None or not isinstance(cls_desc, str):
            report.add(
                ValidationFinding(
                    stage="contract",
                    rule="missing_description_attr",
                    severity="error",
                    message=f"{cls.__name__} missing required class attribute 'description: str'",
                    path=str(module_path),
                )
            )
            cls_ok = False
        # check signature
        if not _has_valid_method(cls, "check"):
            report.add(
                ValidationFinding(
                    stage="contract",
                    rule="invalid_check_signature",
                    severity="error",
                    message=f"{cls.__name__}.check must be a callable with signature (self, ctx)",
                    path=str(module_path),
                )
            )
            cls_ok = False
        # apply signature
        if not _has_valid_method(cls, "apply"):
            report.add(
                ValidationFinding(
                    stage="contract",
                    rule="invalid_apply_signature",
                    severity="error",
                    message=f"{cls.__name__}.apply must be a callable with signature (self, ctx)",
                    path=str(module_path),
                )
            )
            cls_ok = False
        if cls_ok:
            passing.append(cls)
    return passing


def _has_valid_method(cls: type, name: str) -> bool:
    """Return True iff ``cls.<name>`` is a callable with signature ``(self, ctx)``."""
    method = getattr(cls, name, None)
    if method is None or not callable(method):
        return False
    try:
        params = list(inspect.signature(method).parameters)
    except (TypeError, ValueError):
        return False
    return params == ["self", "ctx"]


def _stage_tests(report: ValidationReport, module_path: Path, mechanic_classes: list[type[Mechanic]]) -> None:
    """Run pytest on the sibling test file if one exists (D-13 stage 5).

    Subprocess is invoked with an argv list (never ``shell=True``) so the
    mechanic path is not interpolated into a shell command string
    (T-04-TEST-EXEC mitigation).
    """
    if not mechanic_classes:
        return
    # Resolve candidate test paths. We check the project-style and the
    # universe-style layouts; the first one that exists wins.
    candidate_paths: list[Path] = []
    for cls in mechanic_classes:
        candidate_paths.extend(_candidate_test_paths(module_path, cls.id))

    existing = [p for p in candidate_paths if p.is_file()]
    if not existing:
        report.add(
            ValidationFinding(
                stage="tests",
                rule="no_tests_found",
                severity="warning",
                message=(
                    f"No sibling test file found for {module_path.name} "
                    "(expected at tests/test_mechanic/test_seeds/test_<id>.py "
                    "or <universe>/tests/test_mechanics/test_<id>.py)"
                ),
                path=str(module_path),
            )
        )
        return

    # Deduplicate while preserving order.
    seen: set[Path] = set()
    unique_existing: list[Path] = []
    for p in existing:
        if p not in seen:
            seen.add(p)
            unique_existing.append(p)

    for test_path in unique_existing:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-q", "--no-header"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            tail = (proc.stdout or "")[-500:]
            report.add(
                ValidationFinding(
                    stage="tests",
                    rule="tests_failed",
                    severity="error",
                    message=f"pytest exit {proc.returncode}: {tail}",
                    path=str(test_path),
                )
            )


def _candidate_test_paths(module_path: Path, mechanic_id: str) -> list[Path]:
    """Return plausible sibling test-file locations for *mechanic_id*.

    Two layouts are supported (D-06):

    - Project seeds: ``src/token_world/mechanic/seeds/<id>.py`` ->
      ``tests/test_mechanic/test_seeds/test_<id>.py``.
    - Universe mechanics: ``<universe>/mechanics/<id>.py`` ->
      ``<universe>/tests/test_mechanics/test_<id>.py``.

    Both are probed; the first that exists on disk is used in
    :func:`_stage_tests`.
    """
    candidates: list[Path] = []
    test_filename = f"test_{mechanic_id}.py"

    # Universe layout: <universe>/mechanics/<id>.py ->
    # <universe>/tests/test_mechanics/test_<id>.py
    parent = module_path.parent  # mechanics/
    universe_dir = parent.parent
    candidates.append(universe_dir / "tests" / "test_mechanics" / test_filename)

    # Project-seed layout: src/token_world/mechanic/seeds/<id>.py ->
    # tests/test_mechanic/test_seeds/test_<id>.py (project root is universe_dir's
    # great-grand-parent in this layout).
    # parent        = .../mechanic/seeds
    # universe_dir  = .../mechanic
    # project_root  = three-up from parent (src/token_world/mechanic/seeds ->
    #                  src/token_world/mechanic -> src/token_world -> src -> <root>)
    # We walk upward looking for a 'src' sibling named 'tests'.
    probe = parent
    for _ in range(6):
        probe = probe.parent
        tests_dir = probe / "tests" / "test_mechanic" / "test_seeds" / test_filename
        if tests_dir.exists():
            candidates.append(tests_dir)
            break
        # Stop early if we hit filesystem root
        if probe == probe.parent:
            break
    return candidates


def _stage_smoke(report: ValidationReport, mechanic_classes: list[type[Mechanic]], module_path: Path) -> None:
    """Instantiate each Mechanic subclass and call ``check`` on a minimal fixture.

    ``CheckResult(passed=False, ...)`` is NOT a failure -- the mechanic is
    refusing an action, which is valid behavior. Only raised exceptions
    count as smoke-stage errors.
    """
    # Lazy imports keep this module importable from contexts that cannot
    # (yet) build a KnowledgeGraph (e.g., during test collection).
    from token_world.graph import KnowledgeGraph
    from token_world.mechanic.context import MechanicContext

    for cls in mechanic_classes:
        # Instantiation
        try:
            instance = cls()
        except Exception as e:  # noqa: BLE001
            report.add(
                ValidationFinding(
                    stage="smoke",
                    rule="smoke_instantiation_raised",
                    severity="error",
                    message=f"{cls.__name__}() raised {type(e).__name__}: {e}",
                    path=str(module_path),
                )
            )
            continue
        # Minimal fixture: empty graph + two claimable nodes.
        kg = KnowledgeGraph()
        kg.add_node("_smoke_actor", node_type="agent")
        kg.add_node("_smoke_target", node_type="entity")
        ctx = MechanicContext(kg, actor="_smoke_actor", target="_smoke_target")
        try:
            instance.check(ctx)
        except Exception as e:  # noqa: BLE001
            report.add(
                ValidationFinding(
                    stage="smoke",
                    rule="smoke_raised",
                    severity="error",
                    message=f"{cls.__name__}.check raised {type(e).__name__}: {e}",
                    path=str(module_path),
                )
            )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def validate(module_path: Path) -> ValidationReport:
    """Run the 6-stage validation pipeline against a mechanic module.

    Semantics (D-13):

    - Stop at the *first hard-failing* stage (``passed`` is ``False``
      before the next stage runs).
    - Within a stage, accumulate ALL findings before deciding to stop --
      callers see every AST violation at once, not just the first one.
    - Warnings never flip ``passed``; they are reported alongside errors.

    Args:
        module_path: Path to a ``.py`` mechanic module.

    Returns:
        :class:`ValidationReport` describing the result.
    """
    report = ValidationReport(module_path=module_path, findings=[], passed=True)

    tree = _stage_syntax(report, module_path)
    if not report.passed or tree is None:
        return report

    _stage_ast(report, tree, module_path)
    if not report.passed:
        return report

    module = _stage_import(report, module_path)
    if not report.passed or module is None:
        return report

    mechanic_classes = _stage_contract(report, module, module_path)
    if not report.passed:
        return report

    _stage_tests(report, module_path, mechanic_classes)
    if not report.passed:
        return report

    _stage_smoke(report, mechanic_classes, module_path)
    return report
