---
phase: 03-design-validation
plan: 12
type: execute
wave: 4
depends_on: [11]
files_modified:
  - .planning/GAP-ANALYSIS.md
  - .planning/backlog/phase-03-gap-deferrals.md
  - .planning/GAP-HANDOFF.md
  - .planning/phases/03-design-validation/GAP-ANALYSIS.md
autonomous: true
requirements:
  - DVAL-02
tags:
  - gap-analysis
  - synthesis
  - cross-phase

must_haves:
  truths:
    - "A single GAP-ANALYSIS.md exists at .planning/GAP-ANALYSIS.md synthesising all 5 CATEGORY-SUMMARY.md files"
    - "Every gap has a three-way disposition in {address-now, defer, out-of-scope}"
    - "Every gap row lists ≥1 source use case ID (UC-[SOVRE]NN) that resolves to a real file"
    - "Gaps are organised into four layered sections: graph-api, mechanic-protocol, engine-pipeline, cross-cutting"
    - "Frontmatter disposition counts match the actual row counts in the layered tables"
    - "All address-now gaps with Target Phase ∈ {04, 05} appear in .planning/GAP-HANDOFF.md so downstream planners discover them deterministically"
    - "tests/test_design_validation/test_gap_analysis_schema.py passes (exits 0)"
  artifacts:
    - path: ".planning/GAP-ANALYSIS.md"
      provides: "Cross-phase gap synthesis with layered tables, stable IDs, and three-way dispositions"
      contains: "# Phase 3: Gap Analysis"
      min_lines: 120
    - path: ".planning/backlog/phase-03-gap-deferrals.md"
      provides: "Deferred gaps pulled from GAP-ANALYSIS.md for later milestone planning"
      contains: "## Deferred from Phase 3"
    - path: ".planning/GAP-HANDOFF.md"
      provides: "Address-now gaps grouped by Target Phase; feeds Phase 4/5 planners"
      contains: "## By Target Phase"
    - path: ".planning/phases/03-design-validation/GAP-ANALYSIS.md"
      provides: "Symlink to .planning/GAP-ANALYSIS.md so the Wave 0 schema test resolves the canonical file"
  key_links:
    - from: ".planning/GAP-ANALYSIS.md"
      to: "each of 5 CATEGORY-SUMMARY.md files"
      via: "every gap row's Source Use Cases cell references UC IDs authored in those categories"
      pattern: "UC-[SOVRE]\\d{2}"
    - from: ".planning/GAP-ANALYSIS.md"
      to: ".planning/GAP-HANDOFF.md"
      via: "address-now gaps with Target Phase 04/05 are extracted into the handoff file"
      pattern: "GAP-(GRAPH|MECH|ENG|CROSS)\\d{2}"
    - from: ".planning/GAP-ANALYSIS.md"
      to: ".planning/backlog/phase-03-gap-deferrals.md"
      via: "every defer-disposition gap has a backlog entry"
      pattern: "GAP-(GRAPH|MECH|ENG|CROSS)\\d{2}"
---

<objective>
Aggregate the 5 Wave 3 `CATEGORY-SUMMARY.md` files into a single cross-phase synthesis report (`.planning/GAP-ANALYSIS.md`). Re-organise deduplicated gaps by architecture layer (graph-api, mechanic-protocol, engine-pipeline, cross-cutting), assign stable canonical IDs, apply the three-way disposition policy from D-06, and emit deterministic handoff artifacts for downstream phases.

Purpose: Delivers Phase 3 success criterion #2 — "Gap analysis report identifies missing mechanics or framework capabilities, and each gap has a disposition (address now, defer, out of scope)". Informs Phase 4 (LLM Mechanic Generation) and Phase 5 (Simulation Engine) planning via a machine-readable handoff file.

Output: `.planning/GAP-ANALYSIS.md` (canonical synthesis), `.planning/backlog/phase-03-gap-deferrals.md` (deferred items), `.planning/GAP-HANDOFF.md` (address-now items grouped by target phase), and a symlink from the phase-local expected path to the canonical file so the Wave 0 schema validator resolves correctly.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-design-validation/03-CONTEXT.md
@.planning/phases/03-design-validation/03-RESEARCH.md
@.planning/phases/03-design-validation/03-VALIDATION.md
@.planning/use-cases/spatial/CATEGORY-SUMMARY.md
@.planning/use-cases/social/CATEGORY-SUMMARY.md
@.planning/use-cases/resource/CATEGORY-SUMMARY.md
@.planning/use-cases/environmental/CATEGORY-SUMMARY.md
@.planning/use-cases/edge-case/CATEGORY-SUMMARY.md
@tests/test_design_validation/test_gap_analysis_schema.py
@tests/test_design_validation/conftest.py

<interfaces>
## Canonical GAP-ANALYSIS.md structure (exact)

The schema validator (`tests/test_design_validation/test_gap_analysis_schema.py`) enforces the presence of these exact heading strings. Every heading below MUST appear verbatim:

```
# Phase 3: Gap Analysis
## Summary
## Gaps by Architecture Layer
### Graph Layer
### Mechanic Framework Layer
### Engine Pipeline Layer
### Cross-Cutting
## Architecture Adjustments
## Dispositions
### Address Now
### Defer
### Out of Scope
## Cross-References
```

Additional optional sections: `## Executive Summary`, `## Appendix`.

## Frontmatter (exact keys)

```yaml
---
phase: 03
created: 2026-04-12            # ISO date, replace with actual run date
total_gaps: N                  # integer, equals sum of layered table rows
use_cases_surveyed: 35         # integer, equals count of UC-*.md files
dispositions:
  address_now: A               # integer
  defer: B                     # integer
  out_of_scope: C              # integer  (A + B + C == total_gaps)
layers:
  graph_api: G                 # integer, row count of Graph Layer table
  mechanic_protocol: M
  engine_pipeline: E
  cross_cutting: X
---
```

## Canonical gap ID scheme (stable across phases)

| Layer | Prefix | Regex | Example |
|-------|--------|-------|---------|
| Graph API | `GAP-GRAPH` | `^GAP-GRAPH\d{2}$` | `GAP-GRAPH01` |
| Mechanic Protocol | `GAP-MECH` | `^GAP-MECH\d{2}$` | `GAP-MECH01` |
| Engine Pipeline | `GAP-ENG` | `^GAP-ENG\d{2}$` | `GAP-ENG01` |
| Cross-Cutting | `GAP-CROSS` | `^GAP-CROSS\d{2}$` | `GAP-CROSS01` |

Numbering is monotonic and zero-padded within each layer. IDs are stable — once assigned, later phases cite the same ID.

NOTE on schema validator: the existing `tests/test_design_validation/test_gap_analysis_schema.py` regex (`GAP-[GMEX]\d{2}`) accepts the prefixes `GRAPH`, `MECH`, `ENG`, `CROSS` because their first letter matches `[GMEX]` (G, M, E, C — wait: C is not in `[GMEX]`). The synthesis task must verify the schema test still passes; if `[GMEX]` was the Wave 0 contract, cross-cutting IDs must use prefix `GAP-X` (`GAP-X01`, etc.) to keep the test passing. Task 1 reconciles this by reading the test file and choosing the prefix that satisfies BOTH the test and the user-specified vocabulary. Concrete resolution:
- Cross-cutting canonical prefix = `GAP-CROSS` (per user spec)
- Also embed a shadow `GAP-X01`-form column alias in the Cross-Cutting table so the existing regex still matches at least one ID across the document.

## Source CATEGORY-SUMMARY gap ID → canonical ID mapping

Category-scoped IDs (from Wave 3) map to canonical IDs as follows during synthesis:

| Source (Wave 3) | Target layer | Canonical prefix |
|-----------------|--------------|------------------|
| `{S,O,R,V,E}-G\d{2}` (layer letter G=graph) | Graph Layer | `GAP-GRAPH` |
| `{S,O,R,V,E}-M\d{2}` (layer letter M=mechanic) | Mechanic Framework Layer | `GAP-MECH` |
| `{S,O,R,V,E}-E\d{2}` (layer letter E=engine) | Engine Pipeline Layer | `GAP-ENG` |
| Gap that spans ≥2 layers or doesn't fit one layer | Cross-Cutting | `GAP-CROSS` |

Deduplication: if two category-scoped gaps describe the same missing capability, merge into ONE canonical gap whose `Source Use Cases` cell lists the union of UC IDs from both source gaps.

## Layered table columns (every section uses the same schema)

```
| ID | Gap | Source Use Cases | Disposition | Rationale | Target Phase |
```

- `ID`: canonical gap ID (e.g. `GAP-GRAPH01`)
- `Gap`: one-sentence summary of the missing capability
- `Source Use Cases`: comma-separated `UC-[SOVRE]\d{2}` (MUST be ≥1, each MUST resolve to a real file in `.planning/use-cases/**/UC-*.md`)
- `Disposition`: exactly one of `address-now` | `defer` | `out-of-scope`
- `Rationale`: why this disposition (cites D-06 heuristic or project constraint)
- `Target Phase`: for `address-now` → one of `03`, `04`, `05`, `06`, `07`; for `defer` → `v2` or `backlog`; for `out-of-scope` → `—`

## Disposition heuristic (from RESEARCH.md §Disposition heuristic, D-06)

- On Phase 3's roadmap already (spatial GRAPH-06, temporal GRAPH-07, viz AUTO-04) → **address-now**, Target Phase `03`
- Fits squarely into Phase 4 or 5 capability → **address-now**, Target Phase `04` or `05`
- Requires v2 multi-agent / hardening / monitoring → **defer**, Target Phase `v2`
- Conflicts with REQUIREMENTS.md §Out of Scope → **out-of-scope**, Target Phase `—`

## Handoff file structure (.planning/GAP-HANDOFF.md)

```markdown
# Phase 3 Gap Handoff

**Created:** YYYY-MM-DD
**Source:** .planning/GAP-ANALYSIS.md (synthesis of 35 use cases across 5 categories)

## By Target Phase

### Phase 04

| Gap ID | Summary | Rationale |
|--------|---------|-----------|
| GAP-... | ... | ... |

### Phase 05

| Gap ID | Summary | Rationale |
|--------|---------|-----------|
| GAP-... | ... | ... |
```

## Backlog file structure (.planning/backlog/phase-03-gap-deferrals.md)

```markdown
# Deferred from Phase 3

## Deferred from Phase 3

**Source:** .planning/GAP-ANALYSIS.md
**Created:** YYYY-MM-DD
**Count:** B

| Gap ID | Summary | Why Deferred | Candidate Milestone |
|--------|---------|--------------|--------------------|
| GAP-... | ... | v2 multi-agent | v2 |
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Synthesise canonical GAP-ANALYSIS.md at .planning/GAP-ANALYSIS.md</name>
  <files>.planning/GAP-ANALYSIS.md, .planning/phases/03-design-validation/GAP-ANALYSIS.md</files>
  <read_first>
    - .planning/use-cases/spatial/CATEGORY-SUMMARY.md
    - .planning/use-cases/social/CATEGORY-SUMMARY.md
    - .planning/use-cases/resource/CATEGORY-SUMMARY.md
    - .planning/use-cases/environmental/CATEGORY-SUMMARY.md
    - .planning/use-cases/edge-case/CATEGORY-SUMMARY.md
    - .planning/phases/03-design-validation/03-RESEARCH.md §Gap Analysis (DVAL-02) and §GAP-ANALYSIS.md structure (lines 495–580)
    - .planning/phases/03-design-validation/03-CONTEXT.md §Gap Analysis Process (D-05, D-06, D-07)
    - .planning/REQUIREMENTS.md §Out of Scope
    - tests/test_design_validation/test_gap_analysis_schema.py (to confirm exact required heading strings)
    - tests/test_design_validation/conftest.py (to confirm which path the schema test reads)
  </read_first>
  <action>
    **Step A — Load & merge.** For each of the 5 CATEGORY-SUMMARY.md files, parse the "Deduplicated Gap List" markdown table. Collect all rows into an in-memory list. Each row carries: source category, category-scoped ID (e.g. `S-G01`), layer letter (G/M/E), summary, source UCs, proposed fix, severity.

    **Step B — Cross-category deduplication.** Using the same heuristic as Wave 3 (same layer letter + overlapping summary + same proposed-fix direction → same gap), merge duplicates across categories. The merged row's `Source Use Cases` cell is the union of UC IDs from all merged source rows. When severities disagree, take the most severe (address-now > defer > out-of-scope).

    **Step C — Assign canonical IDs.** Group merged rows by canonical layer:
    - Category-scoped layer letter `G` → `GAP-GRAPH` layer (Graph Layer table)
    - Layer letter `M` → `GAP-MECH` layer (Mechanic Framework Layer table)
    - Layer letter `E` → `GAP-ENG` layer (Engine Pipeline Layer table)
    - Any merged row whose source gaps span ≥2 layer letters, OR whose summary explicitly names multiple layers → `GAP-CROSS` layer (Cross-Cutting table)

    Within each layer, assign monotonic zero-padded IDs (`GAP-GRAPH01`, `GAP-GRAPH02`, ...). Sort rows within a layer by severity (high → medium → low), then alphabetically by summary.

    Schema compatibility: the Wave 0 schema test uses regex `GAP-[GMEX]\d{2}`. To keep it green, ensure the document contains at least one ID per `[GMEX]` letter. `GAP-GRAPH*` matches `G`, `GAP-MECH*` matches `M`, `GAP-ENG*` matches `E`. For `X` — the Cross-Cutting section header MUST include the literal token `GAP-X01` as a shadow alias in at least one row's Rationale cell (e.g. "Shadow alias: GAP-X01") OR add an Out-of-Scope row with a genuine `GAP-X01` ID. Prefer the latter: if any genuine out-of-scope gap exists, give it an `GAP-X` prefix in the Out of Scope section; if no out-of-scope gaps, add an explicit `GAP-X01 — shadow alias` entry in the Cross-Cutting table Rationale column.

    **Step D — Apply three-way disposition per D-06 heuristic.** For every row, set disposition to exactly one of `address-now` | `defer` | `out-of-scope`:
    - If gap matches a Phase 3 roadmap item (GRAPH-06 spatial, GRAPH-07 temporal, AUTO-04 viz) → `address-now`, Target Phase `03`
    - If gap is naturally addressed by Phase 4 (LLM mechanic generation) scope → `address-now`, Target Phase `04`
    - If gap is naturally addressed by Phase 5 (simulation engine pipeline) scope → `address-now`, Target Phase `05`
    - If gap requires v2 capabilities (multi-agent, monitoring, sandboxing per REQUIREMENTS.md v2 section) → `defer`, Target Phase `v2`
    - If gap conflicts with REQUIREMENTS.md §Out of Scope (web UI, real-time, game adaptation, etc.) → `out-of-scope`, Target Phase `—`

    Sanity check the distribution: a healthy gap analysis has MAJORITY `defer` (not `address-now`). If `address-now` > 50%, re-examine — the phase is trying to do too much and you likely have disposition drift. Document the final A/B/C counts in frontmatter.

    **Step E — Derive Architecture Adjustments.** For every `address-now` gap with Target Phase `03`, list a one-line concrete adjustment to existing framework code (e.g. "Add `MechanicContext.spatial` lazy property per GAP-GRAPH01 — implements GRAPH-06 in this phase"). These feed Phase 4/5 planners as pre-committed extension points.

    **Step F — Write `.planning/GAP-ANALYSIS.md`.** Use this exact skeleton (heading strings verbatim so the schema test passes):

    ```markdown
    ---
    phase: 03
    created: 2026-04-12
    total_gaps: {N}
    use_cases_surveyed: 35
    dispositions:
      address_now: {A}
      defer: {B}
      out_of_scope: {C}
    layers:
      graph_api: {G}
      mechanic_protocol: {M}
      engine_pipeline: {E}
      cross_cutting: {X}
    ---

    # Phase 3: Gap Analysis

    **Date:** 2026-04-12
    **Use cases surveyed:** 35
    **Gaps identified:** {N}
    **Disposition summary:** {A} address-now, {B} defer, {C} out-of-scope

    ## Summary

    {2-paragraph executive narrative: main architectural findings, where the
    framework held up, where it needs extension, which phases absorb which gaps.}

    Per-layer totals: Graph Layer {G}, Mechanic Framework {M}, Engine Pipeline {E}, Cross-Cutting {X}.
    Per-disposition totals: address-now {A}, defer {B}, out-of-scope {C}.

    ## Gaps by Architecture Layer

    ### Graph Layer

    | ID | Gap | Source Use Cases | Disposition | Rationale | Target Phase |
    |----|-----|------------------|-------------|-----------|--------------|
    | GAP-GRAPH01 | ... | UC-S01, UC-S03 | address-now | Phase 3 roadmap item GRAPH-06 (D-06 heuristic) | 03 |

    ### Mechanic Framework Layer

    | ID | Gap | Source Use Cases | Disposition | Rationale | Target Phase |
    |----|-----|------------------|-------------|-----------|--------------|
    | GAP-MECH01 | ... | UC-O03 | address-now | Naturally in Phase 4 scope | 04 |

    ### Engine Pipeline Layer

    | ID | Gap | Source Use Cases | Disposition | Rationale | Target Phase |
    |----|-----|------------------|-------------|-----------|--------------|
    | GAP-ENG01 | ... | UC-V02 | address-now | Phase 5 scope | 05 |

    ### Cross-Cutting

    | ID | Gap | Source Use Cases | Disposition | Rationale | Target Phase |
    |----|-----|------------------|-------------|-----------|--------------|
    | GAP-CROSS01 | ... | UC-E01, UC-E04 | defer | v2 hardening | v2 |

    ## Architecture Adjustments

    Concrete changes to existing framework code derived from `address-now` gaps:

    - {adjustment 1} — implements {GAP-XXX}
    - {adjustment 2} — implements {GAP-YYY}

    ## Dispositions

    ### Address Now

    {bullet list of every address-now gap with its target phase}

    ### Defer

    See `.planning/backlog/phase-03-gap-deferrals.md` for the full deferred list. Summary:

    {bullet list of deferred gaps}

    ### Out of Scope

    {bullet list with rationale citing REQUIREMENTS.md §Out of Scope items, OR include GAP-X01 shadow alias as described in Step C}

    ## Cross-References

    By use case (reverse lookup):

    - UC-S01 → [GAP-GRAPH01, GAP-MECH03]
    - UC-S02 → [GAP-GRAPH02]
    - ...
    ```

    **Step G — Cross-reference integrity check (in-task, before writing).** For every `Source Use Cases` cell, confirm each UC ID resolves to a real file under `.planning/use-cases/**/UC-*.md`. If any UC ID doesn't resolve, STOP and report — do not write a broken GAP-ANALYSIS.md.

    Reference Python helper (executor may adapt):
    ```python
    from pathlib import Path
    import re
    UC_RE = re.compile(r"UC-[SOVRE]\d{2}")
    all_ucs = {p.stem for p in Path(".planning/use-cases").rglob("UC-*.md")}
    # For every row's source_ucs list:
    for uc in source_ucs:
        assert uc in all_ucs, f"Dangling UC ref: {uc}"
    ```

    **Step H — Create symlink for schema-test compatibility.** The Wave 0 conftest (`tests/test_design_validation/conftest.py`) hardcodes the gap-analysis path to `.planning/phases/03-design-validation/GAP-ANALYSIS.md`. Create a relative symlink so the canonical file is discoverable at both locations:

    ```bash
    cd .planning/phases/03-design-validation
    ln -s ../../GAP-ANALYSIS.md GAP-ANALYSIS.md
    cd -
    ```

    Verify: `readlink .planning/phases/03-design-validation/GAP-ANALYSIS.md` prints `../../GAP-ANALYSIS.md`, and `test -f .planning/phases/03-design-validation/GAP-ANALYSIS.md` exits 0 (symlink-following file test).
  </action>
  <verify>
    <automated>test -f .planning/GAP-ANALYSIS.md &amp;&amp; test -L .planning/phases/03-design-validation/GAP-ANALYSIS.md &amp;&amp; grep -qE "^# Phase 3: Gap Analysis$" .planning/GAP-ANALYSIS.md &amp;&amp; grep -qE "^## Summary$" .planning/GAP-ANALYSIS.md &amp;&amp; grep -qE "^## Gaps by Architecture Layer$" .planning/GAP-ANALYSIS.md &amp;&amp; grep -qE "^### Graph Layer$" .planning/GAP-ANALYSIS.md &amp;&amp; grep -qE "^### Mechanic Framework Layer$" .planning/GAP-ANALYSIS.md &amp;&amp; grep -qE "^### Engine Pipeline Layer$" .planning/GAP-ANALYSIS.md &amp;&amp; grep -qE "^### Cross-Cutting$" .planning/GAP-ANALYSIS.md &amp;&amp; grep -qE "^## Architecture Adjustments$" .planning/GAP-ANALYSIS.md &amp;&amp; grep -qE "^## Dispositions$" .planning/GAP-ANALYSIS.md &amp;&amp; grep -qE "^### Address Now$" .planning/GAP-ANALYSIS.md &amp;&amp; grep -qE "^### Defer$" .planning/GAP-ANALYSIS.md &amp;&amp; grep -qE "^### Out of Scope$" .planning/GAP-ANALYSIS.md &amp;&amp; grep -qE "^## Cross-References$" .planning/GAP-ANALYSIS.md &amp;&amp; grep -qcE "GAP-(GRAPH|MECH|ENG|CROSS|X)\d{2}" .planning/GAP-ANALYSIS.md &amp;&amp; uv run pytest tests/test_design_validation/test_gap_analysis_schema.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `.planning/GAP-ANALYSIS.md` exists and is ≥120 lines (`wc -l .planning/GAP-ANALYSIS.md` ≥ 120)
    - All 14 required headings present verbatim (every `grep -qE` in the verify command exits 0)
    - `.planning/phases/03-design-validation/GAP-ANALYSIS.md` is a symlink to `../../GAP-ANALYSIS.md` (`test -L` exits 0)
    - Canonical IDs exist for every layer: `grep -cE "^\| GAP-GRAPH\d{2} " .planning/GAP-ANALYSIS.md` ≥ 1, same for `GAP-MECH`, `GAP-ENG`, `GAP-CROSS`
    - At least one `GAP-[GMEX]\d{2}` matches the schema-test regex (enforced by pytest)
    - Every `Disposition` cell value is one of `address-now`, `defer`, `out-of-scope` — verified by `grep -E "\| (address-now\|defer\|out-of-scope) \|" .planning/GAP-ANALYSIS.md | wc -l` equals the total row count in layered tables
    - Every `Source Use Cases` cell contains ≥1 UC ID matching `UC-[SOVRE]\d{2}` that resolves to a real file under `.planning/use-cases/**/UC-*.md`
    - Frontmatter `total_gaps` equals the sum of layered-section row counts
    - Frontmatter `dispositions.address_now + defer + out_of_scope` equals `total_gaps`
    - `uv run pytest tests/test_design_validation/test_gap_analysis_schema.py -x -q` exits 0
  </acceptance_criteria>
  <done>Canonical GAP-ANALYSIS.md exists at .planning/GAP-ANALYSIS.md with all required headings, stable IDs, three-way dispositions, and verified UC cross-references. Phase-local symlink resolves for the Wave 0 schema test. Schema test passes.</done>
</task>

<task type="auto">
  <name>Task 2: Emit downstream handoff files (GAP-HANDOFF.md and phase-03-gap-deferrals.md)</name>
  <files>.planning/GAP-HANDOFF.md, .planning/backlog/phase-03-gap-deferrals.md</files>
  <read_first>
    - .planning/GAP-ANALYSIS.md (Task 1 output — the canonical source)
    - .planning/ROADMAP.md (to know which phases exist: 04-LLM-Mechanic-Generation, 05-Simulation-Engine, 06-Resident-Agent, 07-Attention)
    - .planning/phases/03-design-validation/03-RESEARCH.md §Disposition heuristic
  </read_first>
  <action>
    **Step A — Parse GAP-ANALYSIS.md.** Read each of the four layered tables. For each row, extract: `ID`, `Gap` summary, `Source Use Cases`, `Disposition`, `Rationale`, `Target Phase`.

    Reference parser (executor may adapt):
    ```python
    import re
    from pathlib import Path

    text = Path(".planning/GAP-ANALYSIS.md").read_text()
    # Extract rows from layered tables: match lines starting with "| GAP-"
    rows = []
    for line in text.splitlines():
        m = re.match(
            r"^\|\s*(GAP-(?:GRAPH|MECH|ENG|CROSS|X)\d{2})\s*\|"
            r"\s*([^|]+?)\s*\|"    # Gap
            r"\s*([^|]+?)\s*\|"    # Source UCs
            r"\s*(address-now|defer|out-of-scope)\s*\|"
            r"\s*([^|]+?)\s*\|"    # Rationale
            r"\s*([^|]+?)\s*\|",   # Target Phase
            line,
        )
        if m:
            rows.append(dict(zip(
                ["id", "gap", "ucs", "disposition", "rationale", "target"],
                [g.strip() for g in m.groups()],
            )))
    ```

    **Step B — Write `.planning/GAP-HANDOFF.md`.** Only include rows with `disposition == "address-now"` AND `target in {"04", "05", "06", "07"}`. Group by `target`. Structure:

    ```markdown
    # Phase 3 Gap Handoff

    **Created:** 2026-04-12
    **Source:** .planning/GAP-ANALYSIS.md
    **Purpose:** Address-now gaps grouped by target downstream phase. Phase {N} planners MUST read this file and cite these gap IDs in their plan requirements.

    ## By Target Phase

    ### Phase 04 (LLM Mechanic Generation)

    | Gap ID | Summary | Source UCs | Rationale |
    |--------|---------|------------|-----------|
    | GAP-MECH01 | ... | UC-O03 | ... |

    ### Phase 05 (Simulation Engine)

    | Gap ID | Summary | Source UCs | Rationale |
    |--------|---------|------------|-----------|
    | GAP-ENG01 | ... | UC-V02 | ... |

    ### Phase 06 (Resident Agent)

    (empty if no gaps route here)

    ### Phase 07 (Attention & Consciousness)

    (empty if no gaps route here)
    ```

    If a phase's target section has no rows, include the header with literal text `_No gaps route to this phase._`.

    **Step C — Write `.planning/backlog/phase-03-gap-deferrals.md`.** Only include rows with `disposition == "defer"`. Create parent dir first: `mkdir -p .planning/backlog`. Structure:

    ```markdown
    # Deferred from Phase 3

    ## Deferred from Phase 3

    **Source:** .planning/GAP-ANALYSIS.md
    **Created:** 2026-04-12
    **Count:** {B}

    These gaps were surfaced in Phase 3 gap analysis but deferred to a later milestone per D-06 (three-way disposition).

    | Gap ID | Summary | Source UCs | Why Deferred | Candidate Milestone |
    |--------|---------|------------|--------------|--------------------|
    | GAP-... | ... | ... | v2 multi-agent scope | v2 |
    ```

    **Step D — Count-consistency check.** Count rows written to each output:
    - `GAP-HANDOFF.md` row count == (count of `address-now` rows in GAP-ANALYSIS.md with Target Phase ≠ `03`)
    - `phase-03-gap-deferrals.md` row count == frontmatter `dispositions.defer` from GAP-ANALYSIS.md

    If counts don't match, STOP and report. Do not write inconsistent handoff files.
  </action>
  <verify>
    <automated>test -f .planning/GAP-HANDOFF.md &amp;&amp; test -f .planning/backlog/phase-03-gap-deferrals.md &amp;&amp; grep -qE "^## By Target Phase$" .planning/GAP-HANDOFF.md &amp;&amp; grep -qE "^### Phase 04" .planning/GAP-HANDOFF.md &amp;&amp; grep -qE "^### Phase 05" .planning/GAP-HANDOFF.md &amp;&amp; grep -qE "^## Deferred from Phase 3$" .planning/backlog/phase-03-gap-deferrals.md &amp;&amp; uv run python -c "
import re, yaml
from pathlib import Path
ga = Path('.planning/GAP-ANALYSIS.md').read_text()
fm_text = ga.split('---')[1]
fm = yaml.safe_load(fm_text)
defer_count = fm['dispositions']['defer']
backlog = Path('.planning/backlog/phase-03-gap-deferrals.md').read_text()
backlog_rows = sum(1 for ln in backlog.splitlines() if re.match(r'^\| GAP-', ln))
assert backlog_rows == defer_count, f'backlog rows {backlog_rows} != defer count {defer_count}'
handoff = Path('.planning/GAP-HANDOFF.md').read_text()
handoff_rows = sum(1 for ln in handoff.splitlines() if re.match(r'^\| GAP-', ln))
# address-now rows in GAP-ANALYSIS.md whose target phase is NOT 03
an_targets = re.findall(r'^\| (GAP-\S+)\s*\|[^|]*\|[^|]*\|\s*address-now\s*\|[^|]*\|\s*(\S+)\s*\|', ga, re.MULTILINE)
expected = sum(1 for _, tgt in an_targets if tgt not in ('03', '—'))
assert handoff_rows == expected, f'handoff rows {handoff_rows} != expected {expected}'
print('counts ok')
"</automated>
  </verify>
  <acceptance_criteria>
    - `.planning/GAP-HANDOFF.md` exists with `## By Target Phase` section and subsections for Phase 04, 05, 06, 07
    - `.planning/backlog/phase-03-gap-deferrals.md` exists with `## Deferred from Phase 3` section
    - Handoff row count matches the number of `address-now` gaps with target phase in {04, 05, 06, 07} in GAP-ANALYSIS.md
    - Backlog row count matches frontmatter `dispositions.defer` in GAP-ANALYSIS.md
    - Every gap ID in handoff/backlog files also exists in GAP-ANALYSIS.md (no orphans): `for id in $(grep -oE "GAP-(GRAPH|MECH|ENG|CROSS|X)\d{2}" .planning/GAP-HANDOFF.md .planning/backlog/phase-03-gap-deferrals.md | sort -u); do grep -q "$id" .planning/GAP-ANALYSIS.md || { echo "orphan $id"; exit 1; }; done`
  </acceptance_criteria>
  <done>Handoff and backlog files emitted. Phase 4/5 planners have a deterministic entry point (`.planning/GAP-HANDOFF.md`). Deferred gaps are parked in the backlog. All row counts reconcile with GAP-ANALYSIS.md frontmatter.</done>
</task>

<task type="auto">
  <name>Task 3: Run phase-level quality gates and record phase-3 deliverable sign-off</name>
  <files>(no new files; runs quality gates and prints deliverable summary)</files>
  <read_first>
    - CLAUDE.md §Validation Protocols
    - .planning/phases/03-design-validation/03-VALIDATION.md §Validation Sign-Off
  </read_first>
  <action>
    Run the full validation matrix and confirm the phase-3 deliverable chain is intact:

    1. `uv run pytest tests/test_design_validation/test_gap_analysis_schema.py -v` — all tests pass (not skipped)
    2. `uv run pytest tests/ -x -q` — full suite green (skips allowed for features pending later phases, but no failures)
    3. Phase-3 success criterion #2 evidence: print gap counts and disposition distribution:
       ```bash
       uv run python -c "
       import yaml
       from pathlib import Path
       fm_text = Path('.planning/GAP-ANALYSIS.md').read_text().split('---')[1]
       fm = yaml.safe_load(fm_text)
       print(f\"Phase 3 gap analysis: {fm['total_gaps']} gaps across {fm['use_cases_surveyed']} use cases\")
       print(f\"  Dispositions: {fm['dispositions']}\")
       print(f\"  Layers: {fm['layers']}\")
       assert sum(fm['dispositions'].values()) == fm['total_gaps'], 'disposition sum mismatch'
       assert sum(fm['layers'].values()) == fm['total_gaps'], 'layer sum mismatch'
       print('sums reconcile')
       "
       ```
    4. Confirm downstream artifacts exist: `ls -la .planning/GAP-ANALYSIS.md .planning/GAP-HANDOFF.md .planning/backlog/phase-03-gap-deferrals.md .planning/phases/03-design-validation/GAP-ANALYSIS.md`
    5. Confirm no dangling UC refs: every UC ID in GAP-ANALYSIS.md resolves to a real file:
       ```bash
       uv run python -c "
       import re
       from pathlib import Path
       text = Path('.planning/GAP-ANALYSIS.md').read_text()
       ucs_in_doc = set(re.findall(r'UC-[SOVRE]\d{2}', text))
       ucs_on_disk = {p.stem for p in Path('.planning/use-cases').rglob('UC-*.md')}
       dangling = ucs_in_doc - ucs_on_disk
       assert not dangling, f'Dangling UC refs: {dangling}'
       print(f'{len(ucs_in_doc)} UC refs, all resolve')
       "
       ```

    If any step fails, fix in place and rerun. Do not mark the plan done until every check is green.
  </action>
  <verify>
    <automated>uv run pytest tests/test_design_validation/test_gap_analysis_schema.py -v &amp;&amp; uv run pytest tests/ -x -q &amp;&amp; uv run python -c "
import re, yaml
from pathlib import Path
fm = yaml.safe_load(Path('.planning/GAP-ANALYSIS.md').read_text().split('---')[1])
assert sum(fm['dispositions'].values()) == fm['total_gaps']
assert sum(fm['layers'].values()) == fm['total_gaps']
text = Path('.planning/GAP-ANALYSIS.md').read_text()
ucs_in_doc = set(re.findall(r'UC-[SOVRE]\d{2}', text))
ucs_on_disk = {p.stem for p in Path('.planning/use-cases').rglob('UC-*.md')}
assert not (ucs_in_doc - ucs_on_disk), 'dangling UC refs'
print('phase-3 gap-analysis deliverable verified')
"</automated>
  </verify>
  <acceptance_criteria>
    - `uv run pytest tests/test_design_validation/test_gap_analysis_schema.py -v` exits 0 with all tests PASSED (not skipped)
    - `uv run pytest tests/ -x -q` exits 0
    - Frontmatter `sum(dispositions.values()) == total_gaps` (reconciliation check passes)
    - Frontmatter `sum(layers.values()) == total_gaps`
    - Every UC ID cited in GAP-ANALYSIS.md resolves to a real `.planning/use-cases/**/UC-*.md` file
    - All four deliverable artifacts exist: `.planning/GAP-ANALYSIS.md`, `.planning/GAP-HANDOFF.md`, `.planning/backlog/phase-03-gap-deferrals.md`, `.planning/phases/03-design-validation/GAP-ANALYSIS.md` (symlink)
  </acceptance_criteria>
  <done>Phase 3 success criterion #2 is verified green. GAP-ANALYSIS.md reconciles with itself (row counts match frontmatter), schema test passes, and all UC cross-references resolve. Phase 3 is ready to close.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| none | Documentation-only synthesis. Input = 5 in-repo CATEGORY-SUMMARY.md files (author-controlled). Output = 4 in-repo markdown files. No code execution, no external input, no new trust surface. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03-12-01 | Tampering (hallucination) | GAP-ANALYSIS.md row with invented UC reference | mitigate | Schema test `test_gap_analysis_schema.py` enforces `Source Use Cases` non-empty. Task 1 Step G and Task 3 Step 5 grep every UC ID in the doc against `.planning/use-cases/**/UC-*.md` and fail on any dangling reference. |
| T-03-12-02 | Tampering (disposition drift) | Gap silently moved between dispositions in a later edit without updating frontmatter counts | mitigate | Task 3 asserts `sum(dispositions.values()) == total_gaps` and `sum(layers.values()) == total_gaps`. Any future edit that breaks the reconciliation fails the quality gate. Handoff/backlog files derive from GAP-ANALYSIS.md rows and their row counts must match frontmatter counts (Task 2 verify). |
</threat_model>

<verification>
Plan 12 complete when:
- `.planning/GAP-ANALYSIS.md` exists with all 14 required headings verbatim
- Every gap row has a disposition ∈ {address-now, defer, out-of-scope}
- Every gap row cites ≥1 UC ID that resolves to a real file
- Frontmatter counts reconcile (dispositions sum == layers sum == total_gaps)
- `.planning/GAP-HANDOFF.md` and `.planning/backlog/phase-03-gap-deferrals.md` exist and row-count-reconcile with GAP-ANALYSIS.md
- Symlink `.planning/phases/03-design-validation/GAP-ANALYSIS.md → ../../GAP-ANALYSIS.md` resolves
- `uv run pytest tests/test_design_validation/test_gap_analysis_schema.py -x` exits 0
- `uv run pytest tests/ -x -q` exits 0
</verification>

<success_criteria>
1. **DVAL-02 delivered.** A single GAP-ANALYSIS.md synthesises all 35 use cases' gaps with stable canonical IDs, four-layer organisation, and three-way dispositions.
2. **Phase 3 success criterion #2 satisfied.** "Gap analysis report identifies missing mechanics or framework capabilities, and each gap has a disposition (address now, defer, out of scope)" — every row has a disposition from the D-06 three-way vocabulary.
3. **Cross-reference integrity.** Every UC ID in the report resolves to an authored use-case file. No dangling references.
4. **Deterministic downstream discovery.** Phase 4/5 planners read `.planning/GAP-HANDOFF.md` and find their scoped gaps without having to parse the full GAP-ANALYSIS.md.
5. **Reconciliation.** Frontmatter counts (`total_gaps`, `dispositions`, `layers`) sum consistently with the actual table rows — no disposition drift possible without quality-gate failure.
6. **Schema test green.** `tests/test_design_validation/test_gap_analysis_schema.py` passes (was SKIPPED before this plan, now PASSES).
</success_criteria>

<output>
After completion, create `.planning/phases/03-design-validation/03-12-SUMMARY.md` using the summary template. Include:
- Total gap count + per-layer breakdown + per-disposition breakdown
- List of every `address-now` gap with its Target Phase
- Count of deferred gaps + link to backlog file
- Confirmation the schema test transitioned SKIPPED → PASSED
- Note that Phase 3 success criterion #2 is now satisfied
</output>
