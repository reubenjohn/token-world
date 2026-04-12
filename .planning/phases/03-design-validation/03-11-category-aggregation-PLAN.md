---
phase: 03-design-validation
plan: 11
type: execute
wave: 3
depends_on: [06, 07, 08, 09, 10]
files_modified:
  - .planning/use-cases/spatial/CATEGORY-SUMMARY.md
  - .planning/use-cases/social/CATEGORY-SUMMARY.md
  - .planning/use-cases/resource/CATEGORY-SUMMARY.md
  - .planning/use-cases/environmental/CATEGORY-SUMMARY.md
  - .planning/use-cases/edge-case/CATEGORY-SUMMARY.md
autonomous: true
requirements:
  - DVAL-02
tags:
  - gap-analysis
  - aggregation
  - review

must_haves:
  truths:
    - "Each category has a CATEGORY-SUMMARY.md aggregating gaps from its use cases"
    - "Each summary's gap list is deduplicated (gaps that appear in multiple UCs within a category are merged with cross-references)"
    - "Each summary performs a runtime sanity check: every UC's setup.graph_builder actually creates the actors/targets its actions reference"
    - "Each summary includes the status review: all UCs in the category transition draft → reviewed OR the summary calls out what needs fixing"
    - "All 5 CATEGORY-SUMMARY.md files ready to feed Wave 4 synthesis"
  artifacts:
    - path: ".planning/use-cases/spatial/CATEGORY-SUMMARY.md"
      provides: "Deduplicated gaps for spatial category with UC cross-refs + review findings"
      min_lines: 40
    - path: ".planning/use-cases/social/CATEGORY-SUMMARY.md"
      min_lines: 40
    - path: ".planning/use-cases/resource/CATEGORY-SUMMARY.md"
      min_lines: 40
    - path: ".planning/use-cases/environmental/CATEGORY-SUMMARY.md"
      min_lines: 40
    - path: ".planning/use-cases/edge-case/CATEGORY-SUMMARY.md"
      min_lines: 40
  key_links:
    - from: "CATEGORY-SUMMARY.md"
      to: "each UC file"
      via: "every gap entry has UC backlinks showing source use cases"
      pattern: "UC-[SOVRE]\\d{2}"
---

<objective>
For each of the 5 categories, aggregate inline gaps from the 6-8 use cases into a deduplicated CATEGORY-SUMMARY.md. Perform a runtime sanity check (every UC's setup actually creates the graph state its actions reference). Transition UC statuses from draft → reviewed for UCs that pass.

Purpose: Wave 4's cross-category synthesis reads these 5 summaries instead of all 35 use cases — an expensive-read reduction step.

Output: 5 CATEGORY-SUMMARY.md files, one per category folder.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/use-cases/_README.md
@.planning/use-cases/spatial/MANIFEST.md
@.planning/use-cases/social/MANIFEST.md
@.planning/use-cases/resource/MANIFEST.md
@.planning/use-cases/environmental/MANIFEST.md
@.planning/use-cases/edge-case/MANIFEST.md
@.planning/phases/03-design-validation/03-RESEARCH.md
@src/token_world/use_cases/loader.py

<interfaces>
CATEGORY-SUMMARY.md structure (each category follows this):

# <Category> — Category Summary

**Use cases reviewed:** N (UC-X01..UC-XNN)
**Total inline gaps:** M
**Deduplicated gaps:** K

## Review Findings

- All UCs pass schema validator: YES/NO + list
- All UCs' setup.graph_builder creates every referenced actor/target: YES/NO + violations
- UC status transitions: draft → reviewed for [list]; remaining as draft: [list + reason]

## Deduplicated Gap List

Markdown table with columns: ID (within category) | Layer | Severity | Summary | Source UCs | Proposed Fix

Temporary category-scoped IDs, one per category first-letter + layer-letter + NN:
- spatial → S-G01, S-M01, S-E01, ...
- social → O-G01, O-M01, O-E01, ...
- resource → R-G01, R-M01, R-E01, ...
- environmental → V-G01, V-M01, V-E01, ...
- edge-case → E-G01, E-M01, E-E01, ...

Wave 4 renumbers these to canonical `GAP-<layer><NN>` globally.

## Patterns Noticed

3-5 sentences on cross-UC themes in this category.

Gap deduplication heuristic:
- Two gaps are "the same" if they describe the same missing capability (same layer, overlapping summary, same proposed_fix direction)
- Prefer the better-worded version; list all source UCs in the merged entry
- When severities disagree, take the most severe (address-now > defer > out-of-scope)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Runtime sanity-check all 35 UCs and write CATEGORY-SUMMARY.md for all 5 categories</name>
  <files>.planning/use-cases/spatial/CATEGORY-SUMMARY.md, .planning/use-cases/social/CATEGORY-SUMMARY.md, .planning/use-cases/resource/CATEGORY-SUMMARY.md, .planning/use-cases/environmental/CATEGORY-SUMMARY.md, .planning/use-cases/edge-case/CATEGORY-SUMMARY.md</files>
  <read_first>
    - All 35 authored UC files under .planning/use-cases/{spatial,social,resource,environmental,edge-case}/UC-*.md
    - .planning/use-cases/_README.md (format spec, gap taxonomy)
    - src/token_world/use_cases/loader.py (load_use_case, validate_frontmatter)
    - src/token_world/graph/knowledge_graph.py (KnowledgeGraph API that setup.graph_builder uses)
  </read_first>
  <action>
    For each category, execute this procedure:

    **Step A — Runtime sanity check.** For each UC in the category:
    1. Load via `load_use_case(path)`.
    2. Run `validate_frontmatter(fm)` — if errors, list in findings.
    3. Instantiate a throwaway `KnowledgeGraph(db_path=tmp/"c.db")`.
    4. `exec(fm["setup"]["graph_builder"], {"kg": kg})` — if raises, list under "setup failed".
    5. For each `actions[].actor` and `actions[].classified.target`, check `kg.has_node(id)`. Recognize UC-E01 style intentional exceptions: if frontmatter has `validator_exception: target_may_not_exist`, allow missing targets.
    6. Classify each UC as "passed" or "failed" with the reason.

    Reference script (executor can adapt):
    ```python
    from pathlib import Path
    from token_world.graph import KnowledgeGraph
    from token_world.use_cases import load_use_case, validate_frontmatter
    import tempfile

    def audit(category: str) -> dict:
        results = {"passed": [], "failed": []}
        folder = Path(f".planning/use-cases/{category}")
        for ucf in sorted(folder.glob("UC-*.md")):
            fm, _ = load_use_case(ucf)
            errs = validate_frontmatter(fm, source=str(ucf))
            if errs:
                results["failed"].append((ucf.name, "schema: " + "; ".join(errs)))
                continue
            with tempfile.TemporaryDirectory() as d:
                kg = KnowledgeGraph(db_path=Path(d) / "c.db")
                try:
                    exec(fm["setup"]["graph_builder"], {"kg": kg})
                except Exception as e:
                    results["failed"].append((ucf.name, f"setup exec: {e}"))
                    continue
                missing = []
                allow = fm.get("validator_exception") == "target_may_not_exist"
                for i, a in enumerate(fm.get("actions", [])):
                    if a.get("actor") and not kg.has_node(a["actor"]):
                        missing.append(f"actions[{i}].actor {a['actor']!r} missing")
                    t = (a.get("classified") or {}).get("target")
                    if t and not kg.has_node(t) and not allow:
                        missing.append(f"actions[{i}].target {t!r} missing")
                if missing:
                    results["failed"].append((ucf.name, "; ".join(missing)))
                else:
                    results["passed"].append(ucf.name)
        return results
    ```

    **Step B — Deduplicate gaps.** Load every UC's `gaps[]` list. Merge duplicates per heuristic (same layer + overlapping summary → one merged entry with all source UC IDs). Assign category-scoped IDs:
    - spatial: `S-G01`, `S-M01`, `S-E01`, ... incrementing per layer
    - social: `O-G01`, `O-M01`, `O-E01`
    - resource: `R-G01`, `R-M01`, `R-E01`
    - environmental: `V-G01`, `V-M01`, `V-E01`
    - edge-case: `E-G01`, `E-M01`, `E-E01`
    Layer letters: G=graph, M=mechanic, E=engine.

    **Step C — Status transition.** For each UC that passed Step A, edit its frontmatter `status: draft` → `status: reviewed` in place. For UCs that failed, leave as `draft`. (Executor note: when editing in place, use Read then Edit on the UC file since these files were written in Wave 2; this is a transitive edit not listed in this plan's files_modified since the changed content per UC is ~1 byte — document the exception in the summary.)

    **Step D — Write CATEGORY-SUMMARY.md** per the structure in `<interfaces>`.

    Do this for all 5 categories. Each is independent — may be parallelized.
  </action>
  <verify>
    <automated>for cat in spatial social resource environmental edge-case; do test -f .planning/use-cases/$cat/CATEGORY-SUMMARY.md || { echo "MISSING $cat"; exit 1; }; done &amp;&amp; uv run python -c "from pathlib import Path; import re;\nfor cat in ['spatial','social','resource','environmental','edge-case']:\n    p = Path(f'.planning/use-cases/{cat}/CATEGORY-SUMMARY.md')\n    t = p.read_text()\n    assert '## Review Findings' in t, cat\n    assert '## Deduplicated Gap List' in t, cat\n    assert '## Patterns Noticed' in t, cat\n    letter = {'spatial':'S','social':'O','resource':'R','environmental':'V','edge-case':'E'}[cat]\n    assert re.search(rf'\\\\b{letter}-[GME]\\\\d{{2}}\\\\b', t), f'{cat}: no category-scoped gap IDs'\n    assert re.search(r'UC-[SOVRE]\\\\d{{2}}', t), f'{cat}: no UC cross-refs'\n    assert len(t.splitlines()) &gt;= 40, f'{cat}: too short'\nprint('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - All 5 CATEGORY-SUMMARY.md files exist at the exact paths
    - Each has the three required sections (Review Findings, Deduplicated Gap List, Patterns Noticed)
    - Each has at least one category-scoped gap ID matching its letter prefix
    - Each cross-references at least one UC ID
    - Each is ≥40 lines
    - UCs that passed the runtime check have `status: reviewed` in their frontmatter (verifiable via grep across the `.planning/use-cases/<cat>/UC-*.md` files)
    - The findings table cites every failing UC by name and reason (if any failed)
  </acceptance_criteria>
  <done>5 CATEGORY-SUMMARY.md files exist with deduplicated gaps, review findings, and reviewed-status transitions completed. Wave 4 has a 5-file input set.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

- Step A executes `setup.graph_builder` Python from UC files. These are committed in-repo and treated as test code (see RESEARCH.md §Security Domain).

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03-01 | Tampering | UC `setup.graph_builder` Python exec | accept | Author-controlled, in-repo, same trust level as test code. `exec` runs in an isolated dict `{"kg": kg}` with no other globals. |
</threat_model>

<verification>
- 5 CATEGORY-SUMMARY.md files exist with all required sections and cross-references
- UCs that passed validation have `status: reviewed`
- Automated grep check passes
</verification>

<success_criteria>
1. Each of the 5 categories has a CATEGORY-SUMMARY.md with review findings, deduplicated gap list, and patterns paragraph.
2. Every gap in every summary lists its source UC IDs.
3. UCs that passed runtime sanity check are marked `reviewed`; others retain `draft` with explicit failure reason recorded.
4. Wave 4 agent has exactly 5 files to read.
</success_criteria>

<output>
Create `.planning/phases/03-design-validation/03-11-SUMMARY.md` listing per-category gap counts (total inline → deduplicated) and the list of any UCs that failed runtime validation.
</output>
