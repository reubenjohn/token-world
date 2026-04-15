---
phase: 03-design-validation
plan: 07
subsystem: use-cases
tags:
  - use-cases
  - authoring
  - social
dependency_graph:
  requires:
    - .planning/use-cases/_README.md
    - .planning/use-cases/_TEMPLATE.md
    - .planning/use-cases/social/MANIFEST.md
    - src/token_world/use_cases/loader.py
  provides:
    - .planning/use-cases/social/UC-O01-trade-negotiation.md
    - .planning/use-cases/social/UC-O02-persuasion-check.md
    - .planning/use-cases/social/UC-O03-give-sword-to-bob.md
    - .planning/use-cases/social/UC-O04-deception.md
    - .planning/use-cases/social/UC-O05-teaching.md
    - .planning/use-cases/social/UC-O06-cooperation-lift-heavy.md
    - .planning/use-cases/social/UC-O07-observation-of-agent.md
    - .planning/use-cases/social/UC-O08-speech-broadcast.md
  affects:
    - Wave 4 gap synthesis (consumes gaps[] from these 8 files)
    - Phase 6 regression harness (consumes setup/actions/observations)
tech_stack:
  added: []
  patterns:
    - "YAML frontmatter + markdown body authoring model (per _README.md)"
    - "Structured gap taxonomy: layer ∈ {graph, mechanic, engine}, severity ∈ {address-now, defer, out-of-scope}"
    - "Ditransitive action shape: verb + target + indirect_object for give/tell/teach/offer"
    - "Multi-actor action shape: verb + target + co_actors[] for cooperation"
key_files:
  created:
    - .planning/use-cases/social/UC-O01-trade-negotiation.md
    - .planning/use-cases/social/UC-O02-persuasion-check.md
    - .planning/use-cases/social/UC-O03-give-sword-to-bob.md
    - .planning/use-cases/social/UC-O04-deception.md
    - .planning/use-cases/social/UC-O05-teaching.md
    - .planning/use-cases/social/UC-O06-cooperation-lift-heavy.md
    - .planning/use-cases/social/UC-O07-observation-of-agent.md
    - .planning/use-cases/social/UC-O08-speech-broadcast.md
  modified:
    - .planning/use-cases/social/MANIFEST.md
decisions:
  - "All 8 social scenarios surface at least one address-now gap (15 total across the set) — confirms manifest hypothesis that social is a greenfield category for the framework."
  - "Introduced an `indirect_object` field in classified actions (UC-O03, O04, O05) to structurally represent ditransitive verbs."
  - "Introduced a `co_actors` field in classified actions (UC-O06) to structurally represent intents that must fuse across agents."
  - "Flagged property-visibility classification as the core design decision behind UC-O07 (observation seed leaks private state today)."
  - "Flagged per-agent belief modeling as the core design decision behind UC-O04 (ground-truth and belief must diverge without overwriting)."
metrics:
  duration: "~25 minutes (parallel authoring, one commit per file)"
  completed_date: "2026-04-12"
---

# Phase 3 Plan 07: Authoring Social Use Cases Summary

One-liner: Authored the 8 social use cases (UC-O01..UC-O08) covering trade, persuasion, deception, teaching, cooperation, observation, and speech broadcast — surfacing 15 address-now gaps across mechanic, engine, and graph layers that feed Wave 4 synthesis.

## What was built

Eight new use-case markdown files in `.planning/use-cases/social/`, each pairing a narrative vignette with fully validated YAML frontmatter (id, category, title, status, setup.graph_builder, actions, expected_observations, gaps). All 8 files parse cleanly under `token_world.use_cases.validate_frontmatter`, every action's actor/target resolves to a node in the same file's `setup.graph_builder`, and every file includes the required `## Vignette` and `## Why this matters` sections.

| UC ID   | Title                              | File                                                                  | Key gaps (address-now)                                                                 |
|---------|------------------------------------|-----------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| UC-O01  | Trade negotiation                  | `.planning/use-cases/social/UC-O01-trade-negotiation.md`              | No trade mechanic; no offer/accept protocol in classifier.                             |
| UC-O02  | Persuasion check                   | `.planning/use-cases/social/UC-O02-persuasion-check.md`               | No llm-adjudicated mechanic category; no persuade mechanic w/ disposition.             |
| UC-O03  | Give sword to bob                  | `.planning/use-cases/social/UC-O03-give-sword-to-bob.md`              | Classifier schema missing `indirect_object` field; no give/transfer mechanic.          |
| UC-O04  | Deception                          | `.planning/use-cases/social/UC-O04-deception.md`                      | No belief-tracking mechanic; graph conflates ground-truth with per-agent beliefs.      |
| UC-O05  | Teaching a skill                   | `.planning/use-cases/social/UC-O05-teaching.md`                       | No teach/learn mechanic; skill-name strings vs. first-class skill entities.            |
| UC-O06  | Cooperation to lift a heavy object | `.planning/use-cases/social/UC-O06-cooperation-lift-heavy.md`         | No multi-actor intent fusion in engine; mechanic API assumes single actor.             |
| UC-O07  | Observation of another agent       | `.planning/use-cases/social/UC-O07-observation-of-agent.md`           | Observation seed has no property-visibility classification; leaks private state.       |
| UC-O08  | Speech broadcast                   | `.planning/use-cases/social/UC-O08-speech-broadcast.md`               | No `agents_within` graph query with occluders; no speech-propagation mechanic.         |

**Gap totals:** 15 address-now, 9 defer, 0 out-of-scope across the 8 files — comfortably clears the ≥4 address-now requirement.

**Line counts:** 76–95 lines per file, all well above the ≥40 line minimum.

## Verification

```
$ uv run python -c "... (plan acceptance script) ..."
ok 8 social UCs, 15 address-now gaps

$ uv run pytest tests/test_design_validation/test_use_case_schema.py::test_each_use_case_has_valid_frontmatter -v
PASSED

$ uv run pytest tests/test_design_validation/test_use_case_schema.py::test_use_case_ids_are_unique -v
PASSED
```

`test_library_has_use_cases` (the ≥30-UC aggregate check) is expected to skip/fail until all five category-authoring plans complete in Wave 2; our 8 files do not violate it, they simply don't cover the full target alone.

## Deviations from Plan

None — plan executed exactly as written. All 8 scenarios match the per-file guidance in the plan; wording was enriched within the latitude the plan allowed ("authors may refine wording").

## Decisions Made

1. **Ditransitive action shape.** Three scenarios (UC-O03, O04, O05) adopt a `classified.indirect_object` field. This is flagged as an engine-layer address-now gap in UC-O03 so Wave 4 picks it up as the canonical fix across all three.
2. **Multi-actor action shape.** UC-O06 uses `classified.co_actors: [bob]` on both intents. Flagged as an engine-layer gap for the intent-fusion pass; this is the only scenario where two intents must be interpreted *together* rather than *sequentially*.
3. **Belief modeling as a dict on the agent node.** UC-O04's setup uses `bob.beliefs = {}` and the gap text proposes nested-dict-keyed-by-node-id as the minimum-viable representation. Authors deliberately did not introduce belief *edges* — the dict keeps it expressible under today's `ALLOWED_PROPERTY_TYPES` without requiring a graph-layer API change.
4. **Visibility classification tied to mechanic-level metadata, not property-level.** UC-O07's proposed_fix prefers "tag properties (or writing mechanics) with a visibility class" over a hardcoded allowlist. Keeps the fix composable with future custom mechanics.
5. **Spatial earshot as a graph primitive, not a mechanic helper.** UC-O08 puts `kg.agents_within(origin, radius, occluders=...)` at the graph layer so *any* mechanic (not just speech) can compose with it.

## Self-Check

**Files created:**

- FOUND: .planning/use-cases/social/UC-O01-trade-negotiation.md
- FOUND: .planning/use-cases/social/UC-O02-persuasion-check.md
- FOUND: .planning/use-cases/social/UC-O03-give-sword-to-bob.md
- FOUND: .planning/use-cases/social/UC-O04-deception.md
- FOUND: .planning/use-cases/social/UC-O05-teaching.md
- FOUND: .planning/use-cases/social/UC-O06-cooperation-lift-heavy.md
- FOUND: .planning/use-cases/social/UC-O07-observation-of-agent.md
- FOUND: .planning/use-cases/social/UC-O08-speech-broadcast.md

**Commits:**

- FOUND: c4d1902 docs(03-07): author UC-O01 trade-negotiation
- FOUND: 0d02211 docs(03-07): author UC-O02 persuasion-check
- FOUND: fffd329 docs(03-07): author UC-O03 give-sword-to-bob
- FOUND: 7627ab8 docs(03-07): author UC-O04 deception
- FOUND: 4c9f1dc docs(03-07): author UC-O05 teaching
- FOUND: 172ac67 docs(03-07): author UC-O06 cooperation-lift-heavy
- FOUND: 3748430 docs(03-07): author UC-O07 observation-of-agent
- FOUND: 4aa8d35 docs(03-07): author UC-O08 speech-broadcast

**Schema verification:** ok 8 social UCs, 15 address-now gaps

## Self-Check: PASSED
