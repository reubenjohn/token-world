---
phase: 18
plan: "01"
subsystem: docs
tags: [graph-conventions, design-doc, requirements]
key-files:
  created: [docs/design/graph-conventions.md]
  modified: []
decisions:
  - "Document canonical property shapes as recommendations, not enforcement — graph accepts any property"
  - "Use directed contains edges (not inventory list properties) for container contents"
  - "Portal bidirectionality encoded as bool property, not edge direction"
metrics:
  duration: "~5 min"
  completed: "2026-04-14"
  tasks: 1
  files: 1
---

# Phase 18 Plan 01: Graph Conventions Design Doc — Summary

Docs-only wave that creates `docs/design/graph-conventions.md` with canonical
representations for 4 common world-object categories.

## One-liner

Graph-conventions.md documents doors (state+locked+connects), containers (capacity+contains-edge), portals (connects+bidirectional), and fungible amounts (amount+unit) per REQ-V12-GRAPH-01..04.

## Deviations from Plan

None — plan executed exactly as written.
