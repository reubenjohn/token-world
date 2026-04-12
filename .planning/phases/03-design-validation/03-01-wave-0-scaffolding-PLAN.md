---
phase: 03-design-validation
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - pyproject.toml
  - uv.lock
  - src/token_world/viz/__init__.py
  - src/token_world/viz/mermaid.py
  - src/token_world/use_cases/__init__.py
  - src/token_world/use_cases/loader.py
  - tests/test_design_validation/__init__.py
  - tests/test_design_validation/conftest.py
  - tests/test_design_validation/test_use_case_schema.py
  - tests/test_design_validation/test_gap_analysis_schema.py
  - tests/test_graph/test_spatial_index.py
  - tests/test_graph/test_temporal_index.py
  - tests/test_viz/__init__.py
  - tests/test_viz/conftest.py
  - tests/test_viz/test_viz_graph.py
  - tests/test_viz/test_mermaid_escape.py
autonomous: true
requirements:
  - DVAL-01
  - DVAL-02
  - GRAPH-06
  - GRAPH-07
  - AUTO-04
tags:
  - test-scaffolding
  - dependencies

must_haves:
  truths:
    - "rtree is an installable project dependency (uv sync succeeds)"
    - "src/token_world/viz/ and src/token_world/use_cases/ packages exist and are importable"
    - "Failing pytest stubs exist for every Phase 3 capability (schema, spatial, temporal, viz, mermaid escape)"
    - "Use-case YAML loader and gap-analysis schema validator exist as importable utilities"
  artifacts:
    - path: "pyproject.toml"
      provides: "rtree>=1.4 in [project.dependencies]"
      contains: "rtree"
    - path: "src/token_world/viz/__init__.py"
      provides: "viz package init"
    - path: "src/token_world/viz/mermaid.py"
      provides: "escape_label() helper with Mermaid-safe character replacement"
      exports: ["escape_label"]
    - path: "src/token_world/use_cases/loader.py"
      provides: "load_use_case(path) returning (frontmatter_dict, body_str); required-keys schema check"
      exports: ["load_use_case", "validate_frontmatter", "REQUIRED_KEYS"]
    - path: "tests/test_design_validation/test_use_case_schema.py"
      provides: "Parametric schema check running on every use-cases/**/*.md file present at collection time"
    - path: "tests/test_design_validation/test_gap_analysis_schema.py"
      provides: "Schema check validating GAP-ANALYSIS.md layer sections + disposition table"
    - path: "tests/test_graph/test_spatial_index.py"
      provides: "Failing stubs for SpatialIndex.nearest, within, intersects, lazy build cost, missing-position safety"
    - path: "tests/test_graph/test_temporal_index.py"
      provides: "Failing stubs for query_history, query_changes, find_state_at_tick, TemporalQueryOutOfRange"
    - path: "tests/test_viz/test_viz_graph.py"
      provides: "Failing smoke tests: anchor-required, ego-graph emission, 150-node cap, type filter"
    - path: "tests/test_viz/test_mermaid_escape.py"
      provides: "Failing escape tests covering quotes, newlines, brackets, pipe, length truncation"
  key_links:
    - from: "tests/test_design_validation/conftest.py"
      to: "src/token_world/use_cases/loader.py"
      via: "use_case_files fixture iterating .planning/use-cases/**/*.md"
      pattern: "from token_world.use_cases"
    - from: "tests/test_graph/test_spatial_index.py"
      to: "src/token_world/graph/spatial.py (not yet created — stubs must import by path; skip if module missing)"
      via: "pytest.importorskip('token_world.graph.spatial')"
      pattern: "importorskip"
---

<objective>
Establish Phase 3 test scaffolding, register the `rtree` dependency, and create the empty package skeletons so Wave 1 implementation plans have a place to land and tests to fail against.

Purpose: Enforces the Nyquist sampling rule — every later task has a `<verify>` command it can run, and those commands exist before the feature does (tests fail RED first).

Output: `pyproject.toml` updated with rtree, viz and use_cases packages exist, schema validators exist, all Wave 0 test files listed in VALIDATION.md §Wave 0 Requirements exist and fail cleanly.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03-design-validation/03-CONTEXT.md
@.planning/phases/03-design-validation/03-RESEARCH.md
@.planning/phases/03-design-validation/03-VALIDATION.md
@pyproject.toml
@src/token_world/graph/knowledge_graph.py
@src/token_world/graph/events.py
@src/token_world/mechanic/context.py
@tests/test_graph/conftest.py

<interfaces>
From src/token_world/graph/events.py:
```python
@dataclass(frozen=True)
class GraphEvent:
    tick_id: int
    event_type: str       # "add_node" | "add_edge" | "set_property" | "remove_node" | "remove_edge"
    target_id: str
    property_name: str | None
    old_value_json: str | None
    new_value_json: str | None

class EventStore:
    def get_events(self, tick_id: int | None = None) -> list[GraphEvent]: ...
```

From src/token_world/mechanic/context.py:
```python
class MechanicContext:
    def __init__(self, graph: KnowledgeGraph, *, actor: str, target: str) -> None: ...
```
(Wave 1 `spatial-index` and `temporal-index` plans will add `@property spatial` and `@property temporal` lazy accessors — tests in this plan assume that API.)

Required use-case YAML frontmatter keys (enforced by validate_frontmatter):
```
id: str            # matches pattern UC-[SOVRE]\d{2}
category: str      # one of {spatial, social, resource, environmental, edge-case}
title: str
status: str        # one of {draft, reviewed, locked}
setup: dict        # must contain graph_builder: str
actions: list[dict]
expected_observations: list[dict]
gaps: list[dict]   # each entry: {layer, severity, summary, proposed_fix}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add rtree dependency and create viz + use_cases packages</name>
  <files>pyproject.toml, src/token_world/viz/__init__.py, src/token_world/viz/mermaid.py, src/token_world/use_cases/__init__.py, src/token_world/use_cases/loader.py</files>
  <read_first>
    - pyproject.toml (to edit dependencies in place)
    - .planning/phases/03-design-validation/03-RESEARCH.md §Environment Availability and §Code Examples (for mermaid escape and loader code)
    - src/token_world/graph/__init__.py (package init style to mirror)
  </read_first>
  <action>
    1. Edit `pyproject.toml` `[project.dependencies]` — append `"rtree>=1.4"` after `"pyyaml>=6.0.3"`. Run `uv sync` to update lockfile.
    2. Create `src/token_world/viz/__init__.py` with module docstring and `__all__ = ["escape_label"]`. Re-export from `.mermaid`.
    3. Create `src/token_world/viz/mermaid.py`:
       ```python
       """Mermaid-safe label escaping."""
       from __future__ import annotations

       _ESCAPES = str.maketrans({
           '"': "#quot;",
           "\n": "<br/>",
           "[": "&#91;",
           "]": "&#93;",
           "|": "&#124;",
       })

       def escape_label(text: str, *, max_len: int = 60) -> str:
           """Escape characters that break Mermaid flowchart labels.

           Replaces `" \\n [ ] |` with Mermaid-safe HTML entities and truncates
           to max_len (appending '…').
           """
           escaped = text.translate(_ESCAPES)
           if len(escaped) > max_len:
               escaped = escaped[: max_len - 1] + "…"
           return escaped
       ```
    4. Create `src/token_world/use_cases/__init__.py` with `__all__ = ["load_use_case", "validate_frontmatter", "REQUIRED_KEYS"]`, re-exports from `.loader`.
    5. Create `src/token_world/use_cases/loader.py`:
       ```python
       """Use-case file loader: splits YAML frontmatter from markdown body and validates shape."""
       from __future__ import annotations

       import re
       from pathlib import Path
       from typing import Any

       import yaml

       REQUIRED_KEYS = {
           "id", "category", "title", "status",
           "setup", "actions", "expected_observations", "gaps",
       }
       VALID_CATEGORIES = {"spatial", "social", "resource", "environmental", "edge-case"}
       VALID_STATUSES = {"draft", "reviewed", "locked"}
       ID_PATTERN = re.compile(r"^UC-[SOVRE]\d{2}$")
       GAP_KEYS = {"layer", "severity", "summary", "proposed_fix"}
       VALID_LAYERS = {"graph", "mechanic", "engine"}
       VALID_SEVERITIES = {"address-now", "defer", "out-of-scope"}


       def load_use_case(path: Path) -> tuple[dict[str, Any], str]:
           """Return (frontmatter_dict, markdown_body).

           Raises ValueError if the file is missing frontmatter or the YAML is invalid.
           """
           text = path.read_text(encoding="utf-8")
           if not text.startswith("---\n"):
               raise ValueError(f"{path}: missing YAML frontmatter")
           parts = text.split("---\n", 2)
           if len(parts) < 3:
               raise ValueError(f"{path}: malformed frontmatter (no closing '---')")
           _, fm_text, body = parts
           fm = yaml.safe_load(fm_text) or {}
           if not isinstance(fm, dict):
               raise ValueError(f"{path}: frontmatter must be a mapping")
           return fm, body


       def validate_frontmatter(fm: dict[str, Any], *, source: str = "<unknown>") -> list[str]:
           """Return a list of human-readable validation errors (empty = valid)."""
           errors: list[str] = []
           missing = REQUIRED_KEYS - fm.keys()
           if missing:
               errors.append(f"{source}: missing required keys: {sorted(missing)}")
           if "id" in fm and not ID_PATTERN.match(str(fm["id"])):
               errors.append(f"{source}: id {fm['id']!r} does not match UC-[SOVRE]NN")
           if fm.get("category") not in VALID_CATEGORIES:
               errors.append(f"{source}: category {fm.get('category')!r} not in {sorted(VALID_CATEGORIES)}")
           if fm.get("status") not in VALID_STATUSES:
               errors.append(f"{source}: status {fm.get('status')!r} not in {sorted(VALID_STATUSES)}")
           setup = fm.get("setup")
           if not isinstance(setup, dict) or "graph_builder" not in setup:
               errors.append(f"{source}: setup must be dict with 'graph_builder' key")
           for idx, gap in enumerate(fm.get("gaps", []) or []):
               if not isinstance(gap, dict):
                   errors.append(f"{source}: gaps[{idx}] must be a mapping")
                   continue
               gap_missing = GAP_KEYS - gap.keys()
               if gap_missing:
                   errors.append(f"{source}: gaps[{idx}] missing keys {sorted(gap_missing)}")
               if gap.get("layer") not in VALID_LAYERS:
                   errors.append(f"{source}: gaps[{idx}].layer {gap.get('layer')!r} invalid")
               if gap.get("severity") not in VALID_SEVERITIES:
                   errors.append(f"{source}: gaps[{idx}].severity {gap.get('severity')!r} invalid")
           return errors
       ```
  </action>
  <verify>
    <automated>uv sync &amp;&amp; uv run python -c "import rtree; from token_world.viz import escape_label; from token_world.use_cases import load_use_case, validate_frontmatter, REQUIRED_KEYS; assert escape_label('a\"b|c', max_len=10) == 'a#quot;b&amp;#124;c'; assert 'id' in REQUIRED_KEYS; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "rtree" pyproject.toml` passes
    - `uv run python -c "import rtree"` exits 0
    - `uv run python -c "from token_world.viz import escape_label"` exits 0
    - `uv run python -c "from token_world.use_cases import load_use_case, validate_frontmatter"` exits 0
    - `escape_label('alice"foo|[bar]\n')` returns `'alice#quot;foo&amp;#124;&amp;#91;bar&amp;#93;&lt;br/&gt;'` (test via REPL)
    - `validate_frontmatter({})` returns non-empty list mentioning missing keys
  </acceptance_criteria>
  <done>rtree installable, viz + use_cases packages importable, escape_label and validate_frontmatter work on trivial inputs.</done>
</task>

<task type="auto">
  <name>Task 2: Create failing test stubs for use-case schema, gap-analysis schema, spatial, temporal, viz, mermaid escape</name>
  <files>tests/test_design_validation/__init__.py, tests/test_design_validation/conftest.py, tests/test_design_validation/test_use_case_schema.py, tests/test_design_validation/test_gap_analysis_schema.py, tests/test_graph/test_spatial_index.py, tests/test_graph/test_temporal_index.py, tests/test_viz/__init__.py, tests/test_viz/conftest.py, tests/test_viz/test_viz_graph.py, tests/test_viz/test_mermaid_escape.py</files>
  <read_first>
    - tests/test_graph/conftest.py (for GraphBuilder and kg fixture patterns)
    - tests/conftest.py (for top-level fixtures)
    - .planning/phases/03-design-validation/03-VALIDATION.md §Wave 0 Requirements
    - .planning/phases/03-design-validation/03-RESEARCH.md §Validation Architecture (test-to-req map)
    - src/token_world/use_cases/loader.py (Task 1 output, for REQUIRED_KEYS)
    - src/token_world/viz/mermaid.py (Task 1 output, for escape_label)
  </read_first>
  <action>
    Create test files. Tests should FAIL NOW (RED) because the target modules don't exist yet — use `pytest.importorskip` for modules that Wave 1 will create (`token_world.graph.spatial`, `token_world.graph.temporal`, `token_world.viz.graph_viz`). Escape tests and schema validators can pass now since Task 1 created them.

    **`tests/test_design_validation/__init__.py`** — empty.

    **`tests/test_design_validation/conftest.py`:**
    ```python
    """Fixtures for design validation tests (use-case loading, gap-analysis parsing)."""
    from __future__ import annotations

    from pathlib import Path
    import pytest

    USE_CASES_ROOT = Path(__file__).resolve().parents[2] / ".planning" / "use-cases"
    GAP_ANALYSIS_PATH = (
        Path(__file__).resolve().parents[2]
        / ".planning" / "phases" / "03-design-validation" / "GAP-ANALYSIS.md"
    )

    @pytest.fixture(scope="session")
    def use_case_files() -> list[Path]:
        if not USE_CASES_ROOT.exists():
            return []
        return sorted(
            p for p in USE_CASES_ROOT.rglob("UC-*.md")
            if p.is_file()
        )

    @pytest.fixture(scope="session")
    def gap_analysis_path() -> Path:
        return GAP_ANALYSIS_PATH
    ```

    **`tests/test_design_validation/test_use_case_schema.py`:**
    ```python
    """Every authored use case must parse and validate. Empty library → skip."""
    from __future__ import annotations

    from pathlib import Path
    import pytest

    from token_world.use_cases import load_use_case, validate_frontmatter


    def test_library_has_use_cases(use_case_files: list[Path]) -> None:
        """Phase 3 must produce at least 30 use cases (target 35)."""
        if not use_case_files:
            pytest.skip("No use-case files authored yet (Wave 2 pending)")
        assert len(use_case_files) >= 30, f"Only {len(use_case_files)} use cases found (target 35)"


    def test_each_use_case_has_valid_frontmatter(use_case_files: list[Path]) -> None:
        if not use_case_files:
            pytest.skip("No use-case files authored yet (Wave 2 pending)")
        all_errors: list[str] = []
        for path in use_case_files:
            fm, _ = load_use_case(path)
            errors = validate_frontmatter(fm, source=str(path))
            all_errors.extend(errors)
        assert not all_errors, "Frontmatter errors:\n" + "\n".join(all_errors)


    def test_use_case_ids_are_unique(use_case_files: list[Path]) -> None:
        if not use_case_files:
            pytest.skip("No use-case files authored yet (Wave 2 pending)")
        ids = []
        for path in use_case_files:
            fm, _ = load_use_case(path)
            ids.append(fm.get("id"))
        assert len(set(ids)) == len(ids), f"Duplicate UC IDs: {ids}"
    ```

    **`tests/test_design_validation/test_gap_analysis_schema.py`:**
    ```python
    """GAP-ANALYSIS.md must have layer sections and a disposition summary."""
    from __future__ import annotations

    from pathlib import Path
    import re
    import pytest


    def test_gap_analysis_exists_and_has_required_sections(gap_analysis_path: Path) -> None:
        if not gap_analysis_path.exists():
            pytest.skip("GAP-ANALYSIS.md not written yet (Wave 4 pending)")
        text = gap_analysis_path.read_text(encoding="utf-8")
        for heading in (
            "# Phase 3: Gap Analysis",
            "## Gaps by Architecture Layer",
            "### Graph Layer",
            "### Mechanic Framework Layer",
            "### Engine Pipeline Layer",
            "## Dispositions",
            "### Address Now",
            "### Defer",
            "### Out of Scope",
        ):
            assert heading in text, f"GAP-ANALYSIS.md missing heading: {heading!r}"


    def test_gap_ids_follow_scheme(gap_analysis_path: Path) -> None:
        if not gap_analysis_path.exists():
            pytest.skip("GAP-ANALYSIS.md not written yet (Wave 4 pending)")
        text = gap_analysis_path.read_text(encoding="utf-8")
        ids = re.findall(r"GAP-[GMEX]\d{2}", text)
        assert ids, "No GAP-<layer><NN> IDs found"
        assert all(re.match(r"^GAP-[GMEX]\d{2}$", i) for i in ids)
    ```

    **`tests/test_graph/test_spatial_index.py`:**
    ```python
    """Stubs for GRAPH-06 SpatialIndex (Wave 1 will implement)."""
    from __future__ import annotations

    import pytest

    spatial = pytest.importorskip("token_world.graph.spatial")


    def test_nearest_returns_closest_point(kg) -> None:
        kg.add_node("a", node_type="entity", position=[0.0, 0.0])
        kg.add_node("b", node_type="entity", position=[10.0, 10.0])
        idx = spatial.SpatialIndex(kg)
        idx.rebuild()
        assert idx.nearest((0.1, 0.1), k=1) == ["a"]


    def test_within_bbox_filters_correctly(kg) -> None:
        kg.add_node("a", node_type="entity", position=[1.0, 1.0])
        kg.add_node("b", node_type="entity", position=[50.0, 50.0])
        idx = spatial.SpatialIndex(kg)
        idx.rebuild()
        assert idx.within((0.0, 0.0, 5.0, 5.0)) == ["a"]


    def test_missing_position_is_not_indexed(kg) -> None:
        kg.add_node("has_pos", node_type="entity", position=[0.0, 0.0])
        kg.add_node("no_pos", node_type="entity")  # intentionally no position
        idx = spatial.SpatialIndex(kg)
        idx.rebuild()
        # Querying a huge bbox should return only the one with position
        assert idx.within((-1000.0, -1000.0, 1000.0, 1000.0)) == ["has_pos"]


    def test_bbox_node_intersects(kg) -> None:
        kg.add_node("room", node_type="entity", bbox=[0.0, 0.0, 10.0, 10.0])
        kg.add_node("table", node_type="entity", position=[5.0, 5.0])
        idx = spatial.SpatialIndex(kg)
        idx.rebuild()
        hits = idx.within((4.0, 4.0, 6.0, 6.0))
        assert "table" in hits
        assert "room" in hits  # bbox overlaps query region


    def test_lazy_access_on_mechanic_context(kg) -> None:
        """ctx.spatial must be a @property that builds on first access only."""
        from token_world.mechanic.context import MechanicContext
        kg.add_node("alice", node_type="agent", position=[0.0, 0.0])
        ctx = MechanicContext(kg, actor="alice", target="alice")
        # Access should succeed and return something with .nearest
        assert hasattr(ctx.spatial, "nearest")
    ```

    **`tests/test_graph/test_temporal_index.py`:**
    ```python
    """Stubs for GRAPH-07 TemporalIndex."""
    from __future__ import annotations

    import pytest

    temporal = pytest.importorskip("token_world.graph.temporal")


    def test_query_history_returns_events_for_node(kg) -> None:
        kg.add_node("alice", node_type="agent")
        kg.set("alice", "hp", 100)
        idx = temporal.TemporalIndex(kg)
        events = idx.query_history("alice")
        assert len(events) >= 2  # add_node + set_property


    def test_query_history_tick_range(kg) -> None:
        kg.add_node("alice", node_type="agent")
        kg.advance_tick()
        kg.set("alice", "hp", 50)
        idx = temporal.TemporalIndex(kg)
        events = idx.query_history("alice", tick_range=(1, 1))
        assert all(e.tick_id == 1 for e in events)


    def test_query_changes_for_property(kg) -> None:
        kg.add_node("a", node_type="entity")
        kg.set("a", "temp", 20)
        kg.set("a", "temp", 22)
        idx = temporal.TemporalIndex(kg)
        changes = idx.query_changes("temp")
        assert len(changes) >= 2


    def test_find_state_at_tick_reconstructs(kg) -> None:
        kg.add_node("a", node_type="entity")
        kg.set("a", "hp", 100)
        kg.advance_tick()
        kg.set("a", "hp", 50)
        idx = temporal.TemporalIndex(kg)
        state_at_0 = idx.find_state_at_tick("a", 0)
        assert state_at_0.get("hp") == 100


    def test_out_of_range_raises(kg) -> None:
        kg.add_node("a", node_type="entity")
        idx = temporal.TemporalIndex(kg)
        with pytest.raises(temporal.TemporalQueryOutOfRange):
            idx.find_state_at_tick("a", -999)
    ```

    **`tests/test_viz/__init__.py`** — empty.

    **`tests/test_viz/conftest.py`:**
    ```python
    """Small GraphBuilder-based fixtures for viz tests."""
    from __future__ import annotations

    import pytest

    from tests.test_graph.conftest import GraphBuilder


    @pytest.fixture
    def small_graph(tmp_path):
        from token_world.graph import KnowledgeGraph
        kg = KnowledgeGraph(db_path=tmp_path / "viz.db")
        kg.add_node("alice", node_type="agent", position=[0.0, 0.0])
        kg.add_node("room_a", node_type="entity", subtype="room")
        kg.add_node("sword", node_type="entity", subtype="weapon")
        kg.add_edge("alice", "room_a", relation="located_in")
        kg.add_edge("sword", "alice", relation="held_by")
        return kg
    ```

    **`tests/test_viz/test_viz_graph.py`:**
    ```python
    """Stubs for AUTO-04 viz-graph CLI + viz module."""
    from __future__ import annotations

    import pytest
    from click.testing import CliRunner

    graph_viz = pytest.importorskip("token_world.viz.graph_viz")


    def test_extract_ego_subgraph_respects_depth(small_graph) -> None:
        sub = graph_viz.extract_subgraph(small_graph, anchor="alice", depth=1)
        # Undirected ego_graph at depth 1 from alice: alice, room_a, sword
        assert set(sub.nodes) >= {"alice", "room_a", "sword"}


    def test_to_mermaid_emits_flowchart_header(small_graph) -> None:
        sub = graph_viz.extract_subgraph(small_graph, anchor="alice", depth=1)
        output = graph_viz.to_mermaid(small_graph, sub)
        assert output.startswith("flowchart"), f"expected flowchart header, got: {output[:40]!r}"


    def test_node_cap_refuses_huge_subgraph(small_graph) -> None:
        sub = graph_viz.extract_subgraph(small_graph, anchor="alice", depth=10)
        with pytest.raises(graph_viz.TooManyNodesError):
            graph_viz.to_mermaid(small_graph, sub, max_nodes=1)


    def test_cli_requires_anchor(tmp_path) -> None:
        """viz-graph without --node/--seed-query/--all-agents must error."""
        from token_world.cli import cli
        runner = CliRunner()
        # Use a universe slug that won't exist — CLI should still error on missing anchor first
        result = runner.invoke(cli, ["viz-graph", "nonexistent-universe"])
        assert result.exit_code != 0
        assert "anchor" in result.output.lower() or "--node" in result.output


    def test_cli_emits_mermaid_with_node_anchor(tmp_path, monkeypatch) -> None:
        """End-to-end smoke: viz-graph on a small real universe emits flowchart."""
        # This test is wired once Wave 1 viz plan creates the CLI command.
        from token_world.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["viz-graph", "--help"])
        assert result.exit_code == 0
        assert "--node" in result.output


    def test_injection_safe_node_id(small_graph) -> None:
        """Node IDs containing Mermaid-dangerous chars must not break output (T-03-02)."""
        small_graph.add_node("danger\"|[evil]", node_type="entity")
        small_graph.add_edge("alice", "danger\"|[evil]", relation="observes")
        sub = graph_viz.extract_subgraph(small_graph, anchor="alice", depth=1)
        output = graph_viz.to_mermaid(small_graph, sub)
        # Raw dangerous chars must be escaped in label output
        assert '"|[evil]' not in output or "#quot;" in output
    ```

    **`tests/test_viz/test_mermaid_escape.py`:**
    ```python
    """escape_label() must neutralize Mermaid-hostile characters."""
    from __future__ import annotations

    import pytest

    from token_world.viz import escape_label


    @pytest.mark.parametrize("raw,needle", [
        ('alice"foo', "#quot;"),
        ("multi\nline", "<br/>"),
        ("[bracket]", "&#91;"),
        ("[bracket]", "&#93;"),
        ("pipe|label", "&#124;"),
    ])
    def test_escape_replaces_dangerous_char(raw: str, needle: str) -> None:
        assert needle in escape_label(raw, max_len=100)


    def test_truncates_long_labels() -> None:
        long = "x" * 200
        out = escape_label(long, max_len=60)
        assert len(out) == 60
        assert out.endswith("…")


    def test_leaves_safe_strings_alone() -> None:
        assert escape_label("alice hp=100", max_len=60) == "alice hp=100"
    ```

    Ensure `tests/test_graph/conftest.py` already exposes `kg` and `GraphBuilder` — if the builder import path differs (historically `from tests.test_graph.conftest import GraphBuilder`), leave as is; this is reuse, not new setup.
  </action>
  <verify>
    <automated>uv run pytest tests/test_design_validation/ tests/test_viz/ tests/test_graph/test_spatial_index.py tests/test_graph/test_temporal_index.py -v --no-header 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - `ls tests/test_design_validation/conftest.py tests/test_design_validation/test_use_case_schema.py tests/test_design_validation/test_gap_analysis_schema.py tests/test_graph/test_spatial_index.py tests/test_graph/test_temporal_index.py tests/test_viz/conftest.py tests/test_viz/test_viz_graph.py tests/test_viz/test_mermaid_escape.py` — all present
    - `uv run pytest tests/test_viz/test_mermaid_escape.py -x` passes (the escape helper exists)
    - `uv run pytest tests/test_graph/test_spatial_index.py -v` shows tests as SKIPPED (importorskip — module not yet created)
    - `uv run pytest tests/test_graph/test_temporal_index.py -v` shows tests as SKIPPED
    - `uv run pytest tests/test_viz/test_viz_graph.py -v` shows tests as SKIPPED (token_world.viz.graph_viz not yet created)
    - `uv run pytest tests/test_design_validation/test_use_case_schema.py -v` shows tests as SKIPPED (no use cases yet)
    - No `ERROR` lines in pytest output (skips are fine, errors are not)
  </acceptance_criteria>
  <done>All Wave 0 test files exist. Escape tests pass. Feature-dependent tests skip cleanly pending Wave 1+. Zero collection errors.</done>
</task>

<task type="auto">
  <name>Task 3: Commit baseline and run quality gates</name>
  <files>(no new files; runs quality gates)</files>
  <read_first>
    - CLAUDE.md §Validation Protocols
    - pyproject.toml (to confirm rtree is present)
  </read_first>
  <action>
    Run the phase-gate commands and confirm everything passes before Wave 1 starts:
    1. `uv run ruff check src/` — must pass
    2. `uv run ruff format --check src/` — must pass (run `uv run ruff format src/` if not)
    3. `uv run mypy src/token_world/viz/ src/token_world/use_cases/` — must pass
    4. `uv run pytest tests/ -x -q` — must exit green (skips OK, no failures or errors)

    If any fail, fix in-place (format violations, type annotations, etc.) and rerun. Do not proceed to Wave 1 until green.
  </action>
  <verify>
    <automated>uv run ruff check src/ &amp;&amp; uv run ruff format --check src/ &amp;&amp; uv run mypy src/token_world/viz/ src/token_world/use_cases/ &amp;&amp; uv run pytest tests/ -q</automated>
  </verify>
  <acceptance_criteria>
    - `uv run ruff check src/` exits 0
    - `uv run ruff format --check src/` exits 0
    - `uv run mypy src/token_world/viz/ src/token_world/use_cases/` exits 0
    - `uv run pytest tests/ -q` exits 0 (only skips allowed, no failures/errors)
  </acceptance_criteria>
  <done>Project is lint-clean, type-clean, and test-green with Phase 3 scaffolding in place. Wave 1 can start.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| none | Wave 0 adds only test/package scaffolding — no external input, no new trust surface. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03-01 | Tampering | Use-case YAML frontmatter | accept | Files are author-controlled in-repo; same trust level as test code. Documented in RESEARCH.md §Security Domain. |
| T-03-02 | Injection | `escape_label` in `viz/mermaid.py` | mitigate | Replace `"`, `\n`, `[`, `]`, `|` with Mermaid-safe entities before emitting labels (Task 1). Tested in `test_mermaid_escape.py` (Task 2). |
| T-03-04 | DoS | rtree library install | accept | rtree 1.4.1 has no known CVEs (verified via Snyk/PyPI). Version pinned `>=1.4`. |
</threat_model>

<verification>
Wave 0 complete when:
- `uv sync` succeeds with rtree resolved
- `uv run pytest tests/ -q` is green (skips allowed)
- `uv run ruff check src/ && uv run mypy src/token_world/viz/ src/token_world/use_cases/` is green
- All 8 files listed in VALIDATION.md §Wave 0 Requirements exist on disk
</verification>

<success_criteria>
1. rtree is an installable dependency; `import rtree` works inside the uv-managed venv.
2. `src/token_world/viz/` and `src/token_world/use_cases/` packages exist with docstrings, `__init__.py`, and a usable `escape_label` / `load_use_case` implementation.
3. Every file enumerated in VALIDATION.md §Wave 0 Requirements exists.
4. Running `uv run pytest tests/ -v` shows skips (not errors) for stubs that depend on Wave 1 modules.
5. Ruff, mypy, and pytest pass on the new code.
</success_criteria>

<output>
After completion, create `.planning/phases/03-design-validation/03-01-SUMMARY.md` using the summary template — list files created, list Wave 1 plans unblocked, note that schema validators + escape helper are live.
</output>
