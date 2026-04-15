# Phase 18 Context — Graph Conventions + Engine Audit + Chain Seed Corpus

## Goal
Harden the graph-is-ground-truth invariant by:
1. Documenting canonical graph representations for common world objects
2. Auditing and removing semantic hardcodes from engine/mechanic non-seed code
3. Adding chain-ready seed mechanics that demonstrate PropertyChangeMatcher / EdgeMatcher

## Success Criteria
- SC-1: `docs/design/graph-conventions.md` documents doors, containers, portals/passages, fungible amounts
- SC-2: Zero semantic `locked`/`blocked`/`inventory_full` references in engine/ and mechanic/ (excluding seeds/); legitimate reads have code comments
- SC-3: Regression test: `warded`/`trapped` property names receive identical engine treatment as `locked`
- SC-4: 3 new seed mechanics (mood_change_watcher, contains_edge_watcher, temperature_watcher); registry audit in tests

## Requirements
REQ-V12-ENGINE-03, REQ-V12-GRAPH-01, REQ-V12-GRAPH-02, REQ-V12-GRAPH-03, REQ-V12-GRAPH-04, REQ-V12-DASHBOARD-06

## Wave Structure
- Wave 1 (18-01): Graph conventions doc
- Wave 2 (18-02): Engine audit + hardcoded string removal + regression test
- Wave 3 (18-03): Chain seed mechanics
