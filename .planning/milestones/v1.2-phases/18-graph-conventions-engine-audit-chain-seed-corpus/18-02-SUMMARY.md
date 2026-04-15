---
phase: 18
plan: "02"
subsystem: engine, mechanic
tags: [engine-audit, emergent-properties, regression-test]
key-files:
  created: [tests/test_regression/test_engine_audit_emergent_props.py]
  modified: [src/token_world/engine/refusal.py, src/token_world/mechanic/context.py]
decisions:
  - "refusal.py template keys (locked/blocked/inventory_full) annotated as reads-only convenience shortcuts — not removed, as they provide useful narrative polish for mechanics that choose to use them"
  - "context.py docstring updated to clarify any string is valid as reason_code"
metrics:
  duration: "~10 min"
  completed: "2026-04-14"
  tasks: 2
  files: 3
---

# Phase 18 Plan 02: Engine Audit + Hardcoded String Removal — Summary

Engine audit per REQ-V12-ENGINE-03. All semantic `locked`/`blocked`/`inventory_full`
references in engine/ and mechanic/ (excluding seeds/) are either annotated as
framework-level convenience hooks or are local variable names unrelated to graph state.

## One-liner

Engine audit annotates refusal.py narrative shortcuts and adds SC-3 regression test proving warded/trapped receive identical treatment as locked (8 tests pass).

## Key finding

The three names appear in `refusal.py` as *narrative template keys* — not as semantic checks on graph state. The engine never reads these property names from the graph. They were already non-privileged; the audit makes that contract explicit via code comments and updates the `context.py` docstring.

## Deviations from Plan

None — plan executed exactly as written.

## Pre-existing issue noted (out of scope)

`tests/test_meta/test_requirements_traceability.py` fails due to ROADMAP/REQUIREMENTS drift for phases 13-17. Pre-dated this wave (verified via git stash). Logged as deferred.
