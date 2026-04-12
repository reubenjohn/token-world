---
phase: 03-design-validation
plan: 08
subsystem: use-cases/resource
tags: [use-cases, authoring, resource, conservation, SIM-08]
requires: [03-05]
provides:
  - 7 resource use case files (UC-R01..UC-R07)
  - 13 address-now gaps feeding Wave 4 synthesis
  - explicit SIM-08 traceability from UC-R07
affects:
  - .planning/use-cases/resource/*.md
tech-stack:
  added: []
  patterns:
    - "gap-taxonomy (layer × severity) applied per scenario"
    - "structured actions/observations with fixed graph_assertion vocabulary"
key-files:
  created:
    - .planning/use-cases/resource/UC-R01-craft-sword-from-materials.md
    - .planning/use-cases/resource/UC-R02-consume-food.md
    - .planning/use-cases/resource/UC-R03-gift-currency.md
    - .planning/use-cases/resource/UC-R04-inventory-limit.md
    - .planning/use-cases/resource/UC-R05-degradation-over-time.md
    - .planning/use-cases/resource/UC-R06-fungible-currency.md
    - .planning/use-cases/resource/UC-R07-conservation-violation-attempt.md
  modified:
    - .planning/use-cases/resource/MANIFEST.md
decisions:
  - "UC-R07 made SIM-08 its primary traceability target so Phase 5 has a first-class regression target for conservation enforcement."
  - "Represented coins as both scalar property (UC-R03) and discrete entities (UC-R06) deliberately, surfacing the representation-tension gap rather than picking a side."
  - "Refusal contract (ok=False, narrative=...) reused across UC-R04 and UC-R07 to keep the engine's action-failure shape consistent."
metrics:
  completed_date: 2026-04-12
  tasks_completed: 1
  files_created: 7
  files_modified: 1
  lines_added: 571
---

# Phase 03 Plan 08: Authoring Resource Use Cases Summary

Authored 7 resource-category use cases (UC-R01..UC-R07) covering crafting, consumption, currency transfer, inventory limits, degradation, fungibility, and conservation-violation attempts — surfacing 13 address-now gaps that feed Wave 4 synthesis and directly inform the SIM-08 conservation-law requirement in Phase 5.

## What was built

Each file follows the `_TEMPLATE.md` contract: YAML frontmatter with `setup.graph_builder`, `actions[]`, `expected_observations[]`, `gaps[]`, plus narrative sections (Vignette, Why this matters, Related use cases).

| ID     | Title                             | Primary gap (address-now)                                                   |
|--------|-----------------------------------|-----------------------------------------------------------------------------|
| UC-R01 | Craft sword from materials        | No crafting mechanic; engine does not enforce mass conservation             |
| UC-R02 | Consume food                      | No atomic `remove_node + set(property)` consume mechanic                    |
| UC-R03 | Gift currency                     | No transfer primitive; classifier lacks indirect_object slot                |
| UC-R04 | Inventory limit                   | No refusal contract — engine assumes every action mutates                   |
| UC-R05 | Degradation over time             | No wear mechanic; no threshold rule (durability→0 ⇒ broken)                 |
| UC-R06 | Fungible currency                 | No subset-sum fungibility mechanic over discrete denominations              |
| UC-R07 | Conservation violation attempt    | **SIM-08**: unbalanced conserved-property deltas must be rejected           |

## Conservation-related gaps surfaced (Phase 5 input)

Thirteen `address-now` gaps total, of which the following directly inform **SIM-08** (conservation laws) and the mechanic review pipeline:

- UC-R01: engine-level conservation hook for mass/value before crafting.
- UC-R03: paired-delta assertion — give-5/receive-5 must net zero.
- UC-R07: full SIM-08 pipeline — conserved-property registry, static-analysis review of LLM-generated mechanics, rollback-on-violation, observable failure narrative.
- UC-R04 + UC-R07: shared `ok=False, narrative=...` refusal contract the engine needs for any rule-driven rejection.

Additional mechanic-layer gaps (crafting, consume, transfer, inventory, wear, fungibility) are authored as concrete proposed fixes so Phase 5 plans can pick them up as seed mechanics without rediscovery.

## Deviations from Plan

None - plan executed exactly as written.

## Verification performed

- `uv run pytest tests/test_design_validation/test_use_case_schema.py` — 2/3 pass; the library-size test correctly reports 7/35 (other waves pending) and skips per its `<30 files` contract. Frontmatter validation + ID uniqueness both pass for all 7 files.
- Custom validator run: all 7 files parse, all 7 have `## Vignette`, 13 address-now gaps (≥4 required), UC-R07 contains "SIM-08".
- Graph-builder execution: each `setup.graph_builder` executes against a fresh `KnowledgeGraph` with no errors, and every actor / target / indirect_object / instrument referenced in `actions[]` exists in the post-setup graph.
- Line counts: all files 67–100 lines (≥40 required).

## Self-Check: PASSED

All created files exist:
- FOUND: .planning/use-cases/resource/UC-R01-craft-sword-from-materials.md
- FOUND: .planning/use-cases/resource/UC-R02-consume-food.md
- FOUND: .planning/use-cases/resource/UC-R03-gift-currency.md
- FOUND: .planning/use-cases/resource/UC-R04-inventory-limit.md
- FOUND: .planning/use-cases/resource/UC-R05-degradation-over-time.md
- FOUND: .planning/use-cases/resource/UC-R06-fungible-currency.md
- FOUND: .planning/use-cases/resource/UC-R07-conservation-violation-attempt.md

Commit: FOUND: 74aa762 (docs(03-08): author 7 resource use cases)
