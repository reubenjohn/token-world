# Phase 1: Graph Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 01-graph-foundation
**Areas discussed:** Node identity & typing, Property value flexibility, Snapshot semantics, CLAUDE.md update scope

---

## Node Identity & Typing

| Option | Description | Selected |
|--------|-------------|----------|
| UUID-based IDs | Globally unique, no collisions, but opaque | |
| Human-readable slugs | Debuggable, but collision risk | |
| Mechanic-driven claim_id() | Readable IDs with automatic deconfliction | ✓ |

**User's choice:** Mechanic-driven `claim_id("wallet")` that returns "wallet" or "wallet_a7" if taken. Minimize framework-known types to just `agent` and `entity` — everything else is emergent. No other framework-enforced properties.

**Notes:** User explicitly wants to minimize framework assumptions to maximize mechanic flexibility. The framework should make as few constraints as possible on what mechanics can express. Type labels should only exist for truly fundamental distinctions (agent vs entity).

---

## Property Value Flexibility

| Option | Description | Selected |
|--------|-------------|----------|
| Primitives only | str, int, float, bool — simple, safe | |
| Primitives + nested | Also dicts and lists — richer but harder to persist | |
| Claude's discretion | Let Claude balance flexibility vs reliability | ✓ |

**User's choice:** "What would you do?" — delegated to Claude's discretion.

**Notes:** No specific preference expressed. Claude should balance emergent-property philosophy with persistence reliability.

---

## Snapshot Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Named checkpoints | Manual, operator-named | |
| Numbered/timestamped | Automatic, sequential | |
| Tick-linked with summary names | Linked to tick IDs, named from change summaries | ✓ |

**User's choice:** Every tick identifiable, snapshots linked to tick identifiers. Names derived from hierarchical tick summaries (e.g., summary of batch-300-400 + batch-400-500 + tick-501 + tick-502). Other details at Claude's discretion.

**Notes:** User referenced the hierarchical tick summary system from PROJECT.md. Wants snapshots to feel like a timeline of "what happened" rather than opaque identifiers.

---

## CLAUDE.md Update Scope (AUTO-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Quick-reference card | Minimal, key facts only | |
| Deep architecture doc | Comprehensive, full detail | |
| Claude's discretion | Whatever achieves agent autonomy | ✓ |

**User's choice:** "You decide what's needed to make you achieve that level of autonomy."

**Notes:** Full delegation. Claude should produce whatever documentation enables an agent to understand and work on the project without human guidance.

---

## Claude's Discretion

- Property value types (D-04)
- Snapshot storage details (D-07)
- CLAUDE.md content and depth (D-08)

## Deferred Ideas

None — discussion stayed within phase scope.
