---
phase: 03-design-validation
plan: 15
type: gap-closure
wave: 5
depends_on: [12]
files_modified:
  - src/token_world/use_cases/loader.py
  - tests/test_design_validation/test_use_case_schema.py
  - tests/test_design_validation/test_use_case_loader.py
autonomous: true
requirements:
  - DVAL-01
  - DVAL-02
tags:
  - gap-closure
  - schema
  - use-cases
  - validation

must_haves:
  truths:
    - "validate_frontmatter rejects any graph_assertion whose kind is not one of {has_node, has_edge, has_property, property_equals, not_has_edge, not_has_property}"
    - "A use-case fixture containing kind: totally_fake_kind produces at least one validation error mentioning 'kind' and the offending value"
    - "All 35 existing UC-*.md files still pass validation unchanged (no collateral rejection)"
    - "VALID_ASSERTION_KINDS is exposed from src/token_world/use_cases/loader.py as a frozenset constant"
    - "tests/test_design_validation/test_use_case_schema.py passes with a new parametrized test for each of the 6 valid kinds + at least 2 invalid kinds"
    - "uv run pytest tests/test_design_validation/ -q exits 0"
  artifacts:
    - path: "src/token_world/use_cases/loader.py"
      provides: "validate_frontmatter that enforces the fixed 6-kind graph_assertion vocabulary"
      contains: "VALID_ASSERTION_KINDS"
    - path: "tests/test_design_validation/test_use_case_schema.py"
      provides: "Failing-then-passing regression test for the assertion-kind whitelist"
      contains: "totally_fake_kind"
  key_links:
    - from: "src/token_world/use_cases/loader.py:VALID_ASSERTION_KINDS"
      to: ".planning/use-cases/_README.md"
      via: "the 6-kind vocabulary documented in _README.md is now enforced in code, not just convention"
      pattern: "has_node|has_edge|has_property|property_equals|not_has_edge|not_has_property"
    - from: "validate_frontmatter iteration"
      to: "expected_observations[].graph_assertions[].kind"
      via: "for each observation in fm['expected_observations'], for each assertion in observation['graph_assertions'], assert assertion['kind'] in VALID_ASSERTION_KINDS"
      pattern: "graph_assertions"
---

<objective>
Close UAT gap (Test 8, severity: major) — `src/token_world/use_cases/loader.py:validate_frontmatter` does NOT enforce the documented 6-kind `graph_assertion` vocabulary. An independent agent injected `kind: totally_fake_kind` into a UC and validation returned zero errors. The vocabulary `{has_node, has_edge, has_property, property_equals, not_has_edge, not_has_property}` is currently enforced by human convention only — the first LLM-authored UC in Phase 04 that drifts will introduce silent schema rot.

Note on assertion location: the UAT `missing` field mentions "setup.graph_assertions and action.graph_assertions", but the actual UC files (verified by grepping `.planning/use-cases/`) place `graph_assertions` under `expected_observations[].graph_assertions`. The fix MUST iterate the real location (plus any future `setup`/`action` placements if they exist in any UC, as defense-in-depth).

Purpose: Phase 04 mechanic-authoring pipeline will parse these UCs as integration-test fixtures (see 04-04-PLAN.md in the roadmap). A silent schema-rot gap here becomes a runtime AttributeError there. Fixing the validator at the edge is cheaper than triaging downstream failures.

Output: A `VALID_ASSERTION_KINDS` frozenset, a validator that iterates every `graph_assertion`'s `kind`, and a failing-then-passing test.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/03-design-validation/03-UAT.md
@.planning/phases/03-design-validation/03-05-use-case-manifests-PLAN.md
@.planning/use-cases/_README.md
@.planning/use-cases/_TEMPLATE.md
@src/token_world/use_cases/loader.py
@tests/test_design_validation/test_use_case_schema.py
@tests/test_design_validation/test_use_case_loader.py
</context>

<threat_model>
**Threat:** Schema-rot via silent acceptance. If an LLM-authored UC (Phase 04) introduces a typo'd or invented kind — e.g. `has_attribute`, `property_eq`, `HAS_EDGE` — the validator accepts it. Downstream code that pattern-matches on `kind` then silently omits that assertion from checking, or crashes with `KeyError` deep in a harness.

**STRIDE:**
- **Tampering (via drift):** Not a classic security threat but a data-integrity threat — the assertions serialised into UCs are the source of truth for Phase 04's integration harness.

**Mitigation:** Whitelist enforcement at the validator boundary. Defense-in-depth: the harness that consumes these can also `assert kind in VALID_ASSERTION_KINDS`, but the validator is the earliest and cheapest checkpoint.

**Severity: MAJOR** (per UAT). Block on: high.
</threat_model>

<tasks>

<task id="15.1">
<title>Add VALID_ASSERTION_KINDS constant and iterate assertion kinds in validate_frontmatter</title>

<read_first>
  - src/token_world/use_cases/loader.py (full file — all existing constants and the shape of validate_frontmatter)
  - .planning/use-cases/_README.md (the documented 6-kind vocabulary — confirm it matches the UAT's list exactly)
  - .planning/use-cases/_TEMPLATE.md (the canonical structure — confirm where graph_assertions live)
  - One example file: .planning/use-cases/spatial/UC-S01-movement-through-doorway.md (concrete nesting: expected_observations[].graph_assertions[].kind)
</read_first>

<action>
Edit `src/token_world/use_cases/loader.py`. At the top near the other constants, add:

```python
VALID_ASSERTION_KINDS = frozenset(
    {
        "has_node",
        "has_edge",
        "has_property",
        "property_equals",
        "not_has_edge",
        "not_has_property",
    }
)
```

In `validate_frontmatter`, after the existing checks (missing keys / id / category / status / setup / gaps), add an iteration over `expected_observations[*].graph_assertions[*]`. Also defensively iterate any `setup.graph_assertions` and `actions[*].graph_assertions` if they exist, since the UAT `missing` field explicitly mentions those locations — even though current UCs don't place assertions there, a future refactor might, and defense-in-depth costs one extra for-loop.

Insert this block *before* the final `return errors`:

```python
    # Enforce the fixed 6-kind graph_assertion vocabulary (UAT #8).
    # Assertions live primarily under expected_observations[*].graph_assertions,
    # but defensively also check setup.graph_assertions and actions[*].graph_assertions
    # in case a future UC places them there.
    def _check_assertions(container: Any, ctx: str) -> None:
        if not isinstance(container, list):
            return
        for a_idx, assertion in enumerate(container):
            if not isinstance(assertion, dict):
                errors.append(f"{source}: {ctx}[{a_idx}] must be a mapping")
                continue
            kind = assertion.get("kind")
            if kind not in VALID_ASSERTION_KINDS:
                errors.append(
                    f"{source}: {ctx}[{a_idx}].kind {kind!r} not in "
                    f"{sorted(VALID_ASSERTION_KINDS)}"
                )

    for o_idx, obs in enumerate(fm.get("expected_observations", []) or []):
        if isinstance(obs, dict):
            _check_assertions(
                obs.get("graph_assertions"),
                f"expected_observations[{o_idx}].graph_assertions",
            )

    setup_block = fm.get("setup")
    if isinstance(setup_block, dict):
        _check_assertions(setup_block.get("graph_assertions"), "setup.graph_assertions")

    for a_idx, action in enumerate(fm.get("actions", []) or []):
        if isinstance(action, dict):
            _check_assertions(
                action.get("graph_assertions"), f"actions[{a_idx}].graph_assertions"
            )
```

Export `VALID_ASSERTION_KINDS` from the package if it is not already. Check `src/token_world/use_cases/__init__.py` — if it re-exports `REQUIRED_KEYS` / `VALID_CATEGORIES`, add `VALID_ASSERTION_KINDS` to the same export list so downstream code (Phase 04 harness) can import the single source of truth.
</action>

<acceptance_criteria>
  - `src/token_world/use_cases/loader.py` contains the literal string `VALID_ASSERTION_KINDS`
  - `VALID_ASSERTION_KINDS` is a `frozenset` containing exactly these 6 strings: `has_node`, `has_edge`, `has_property`, `property_equals`, `not_has_edge`, `not_has_property` — verified by: `python -c "from token_world.use_cases.loader import VALID_ASSERTION_KINDS; assert VALID_ASSERTION_KINDS == frozenset({'has_node','has_edge','has_property','property_equals','not_has_edge','not_has_property'}), sorted(VALID_ASSERTION_KINDS); print('OK')"` prints `OK`
  - `validate_frontmatter` body contains the string `expected_observations` and the string `graph_assertions`
  - Running validator against a synthetic fm with `{"expected_observations": [{"graph_assertions": [{"kind": "totally_fake_kind", ...}]}], ...rest valid...}` returns a non-empty errors list whose concatenation contains both `'totally_fake_kind'` and `'kind'` (verified by inline `python -c` smoke in task 15.3)
  - All 35 existing UC files still validate clean — `uv run pytest tests/test_design_validation/test_use_case_schema.py::test_each_use_case_has_valid_frontmatter -v` exits 0
  - `uv run ruff check src/token_world/use_cases/` exits 0
  - `uv run mypy src/token_world/` on files that import the loader exits 0 (or unchanged from baseline)
</acceptance_criteria>

</task>

<task id="15.2">
<title>Add failing-then-passing regression test for the assertion-kind whitelist</title>

<read_first>
  - tests/test_design_validation/test_use_case_schema.py (existing style — parametrize over use_case_files fixture)
  - tests/test_design_validation/test_use_case_loader.py (direct unit-test style on validate_frontmatter)
  - tests/test_design_validation/conftest.py (fixtures available)
</read_first>

<action>
Add unit tests to `tests/test_design_validation/test_use_case_loader.py` (the direct-validator file, not the library-sweep file). These tests build synthetic frontmatter dicts so they do not depend on the on-disk UC library.

Append:

```python
import pytest

from token_world.use_cases.loader import (
    VALID_ASSERTION_KINDS,
    validate_frontmatter,
)


def _minimal_valid_fm(**overrides: object) -> dict[str, object]:
    """Return a frontmatter dict that validate_frontmatter accepts.

    Tests layer their own `expected_observations` / `setup` on top via overrides.
    """
    base: dict[str, object] = {
        "id": "UC-S99",
        "category": "spatial",
        "title": "synthetic",
        "status": "draft",
        "setup": {"graph_builder": "def build(b): pass"},
        "actions": [],
        "expected_observations": [],
        "gaps": [],
    }
    base.update(overrides)
    return base


def test_valid_assertion_kinds_contains_exactly_six() -> None:
    assert VALID_ASSERTION_KINDS == frozenset(
        {
            "has_node",
            "has_edge",
            "has_property",
            "property_equals",
            "not_has_edge",
            "not_has_property",
        }
    )


@pytest.mark.parametrize("kind", sorted(VALID_ASSERTION_KINDS))
def test_every_valid_kind_passes(kind: str) -> None:
    fm = _minimal_valid_fm(
        expected_observations=[{"graph_assertions": [{"kind": kind, "node": "x"}]}]
    )
    errors = validate_frontmatter(fm, source="synthetic.md")
    assert not errors, f"valid kind {kind!r} rejected: {errors}"


@pytest.mark.parametrize(
    "bad_kind",
    ["totally_fake_kind", "HAS_EDGE", "has_attribute", "", "property_eq", None],
)
def test_invalid_kind_rejected(bad_kind: object) -> None:
    fm = _minimal_valid_fm(
        expected_observations=[{"graph_assertions": [{"kind": bad_kind, "node": "x"}]}]
    )
    errors = validate_frontmatter(fm, source="synthetic.md")
    assert errors, f"invalid kind {bad_kind!r} accepted silently"
    joined = "\n".join(errors)
    assert "kind" in joined
    # The offending value should be referenced in the error (repr form)
    assert repr(bad_kind) in joined or str(bad_kind) in joined


def test_invalid_kind_in_setup_graph_assertions_rejected() -> None:
    """Defense-in-depth: setup.graph_assertions is also checked."""
    fm = _minimal_valid_fm(
        setup={
            "graph_builder": "def build(b): pass",
            "graph_assertions": [{"kind": "totally_fake_kind"}],
        }
    )
    errors = validate_frontmatter(fm, source="synthetic.md")
    assert errors
    assert any("setup.graph_assertions" in e for e in errors)


def test_invalid_kind_in_actions_graph_assertions_rejected() -> None:
    """Defense-in-depth: actions[*].graph_assertions is also checked."""
    fm = _minimal_valid_fm(
        actions=[{"graph_assertions": [{"kind": "totally_fake_kind"}]}]
    )
    errors = validate_frontmatter(fm, source="synthetic.md")
    assert errors
    assert any("actions[0].graph_assertions" in e for e in errors)


def test_missing_kind_key_rejected() -> None:
    """An assertion without a `kind` field is rejected (kind=None not in set)."""
    fm = _minimal_valid_fm(
        expected_observations=[{"graph_assertions": [{"node": "x"}]}]
    )
    errors = validate_frontmatter(fm, source="synthetic.md")
    assert errors
```

No changes to `test_use_case_schema.py` are strictly required; the existing library sweep will continue to pass because none of the 35 real UCs use an invalid kind. But as a belt-and-suspenders guard, add one sweep test:

```python
# in tests/test_design_validation/test_use_case_schema.py, append:

from token_world.use_cases.loader import VALID_ASSERTION_KINDS


def test_every_authored_assertion_uses_a_valid_kind(use_case_files: list[Path]) -> None:
    """Cross-check: scan all authored UCs, every graph_assertion.kind must be whitelisted."""
    if not use_case_files:
        pytest.skip("No use-case files authored yet")
    bad: list[str] = []
    for path in use_case_files:
        fm, _ = load_use_case(path)
        for obs in fm.get("expected_observations", []) or []:
            for assertion in obs.get("graph_assertions", []) or []:
                kind = assertion.get("kind")
                if kind not in VALID_ASSERTION_KINDS:
                    bad.append(f"{path.name}: {kind!r}")
    assert not bad, "Assertions with invalid kinds in authored UCs:\n" + "\n".join(bad)
```
</action>

<acceptance_criteria>
  - `tests/test_design_validation/test_use_case_loader.py` contains the literal string `totally_fake_kind`
  - `tests/test_design_validation/test_use_case_loader.py` contains at least these new test names: `test_valid_assertion_kinds_contains_exactly_six`, `test_every_valid_kind_passes`, `test_invalid_kind_rejected`, `test_invalid_kind_in_setup_graph_assertions_rejected`, `test_invalid_kind_in_actions_graph_assertions_rejected`, `test_missing_kind_key_rejected`
  - `tests/test_design_validation/test_use_case_schema.py` contains the new test `test_every_authored_assertion_uses_a_valid_kind`
  - `uv run pytest tests/test_design_validation/ -v` exits 0
  - `uv run pytest tests/test_design_validation/test_use_case_loader.py::test_invalid_kind_rejected -v` reports all 6 parametrized cases pass (one per bad_kind value)
  - Total test count in tests/test_design_validation/ increases by at least 8 vs. baseline (6 valid kinds parametrized as one test + 6 invalid kinds parametrized + 4 scalar tests + 1 sweep)
</acceptance_criteria>

</task>

<task id="15.3">
<title>Live adversarial probe — inject a bad kind into a UC on disk and confirm validator rejects</title>

<read_first>
  - .planning/use-cases/spatial/UC-S01-movement-through-doorway.md (as the probe target)
  - scripts/uat_phase_03.py (existing UAT harness — this probe is a focused repeat of the independent-agent test mentioned in 03-UAT.md)
</read_first>

<action>
Execute a one-shot live probe to confirm the fix closes the exact hole the independent agent found. This is a shell task, not a committed test — its purpose is to reproduce and then resolve the UAT evidence:

```bash
# Snapshot, mutate, load via the actual loader, restore.
cp .planning/use-cases/spatial/UC-S01-movement-through-doorway.md /tmp/uc-s01-backup.md
python - <<'PY'
from pathlib import Path
p = Path(".planning/use-cases/spatial/UC-S01-movement-through-doorway.md")
txt = p.read_text()
# Inject a bogus kind on the first graph_assertions block
mutated = txt.replace("      - kind: has_edge\n", "      - kind: totally_fake_kind\n", 1)
p.write_text(mutated)
PY
# Run the validator. Expect at least one error mentioning totally_fake_kind.
uv run python - <<'PY'
from pathlib import Path
from token_world.use_cases.loader import load_use_case, validate_frontmatter
p = Path(".planning/use-cases/spatial/UC-S01-movement-through-doorway.md")
fm, _ = load_use_case(p)
errors = validate_frontmatter(fm, source=str(p))
assert any("totally_fake_kind" in e for e in errors), f"Validator did NOT catch the bad kind: {errors}"
print("PASS — validator rejected totally_fake_kind:", [e for e in errors if "totally_fake_kind" in e])
PY
# Restore
cp /tmp/uc-s01-backup.md .planning/use-cases/spatial/UC-S01-movement-through-doorway.md
# Confirm restore worked and the full suite is green again
uv run pytest tests/test_design_validation/ -q
```

If the python block raises `AssertionError`, task 15.1 was not applied correctly — stop and escalate.
</action>

<acceptance_criteria>
  - The shell block exits 0 end-to-end
  - The probe prints `PASS — validator rejected totally_fake_kind:` followed by at least one error string
  - After restore, `git diff .planning/use-cases/spatial/UC-S01-movement-through-doorway.md` is empty
  - `uv run pytest tests/test_design_validation/ -q` exits 0 after restore
</acceptance_criteria>

</task>

</tasks>

<verification>
  - `uv run pytest tests/test_design_validation/ -v` exits 0 with ≥8 new tests vs. baseline
  - `uv run pytest tests/ -q` exits 0 (no regression in other test dirs)
  - `uv run ruff check src/ tests/` exits 0
  - Live adversarial probe (task 15.3) completes with the expected PASS line
  - Re-run UAT Test 8 probe — flips from `issue` to `pass`
  - `VALID_ASSERTION_KINDS` is importable from both `token_world.use_cases.loader` and (if re-exported) `token_world.use_cases`
</verification>
