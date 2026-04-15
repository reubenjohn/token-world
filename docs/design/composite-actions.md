# Composite Actions — Design Document

**Phase:** 16 (v1.2 D-01)
**Status:** Implemented (Wave 1)
**Requirement:** REQ-V12-ENGINE-04

## Overview

Phase 16 adds support for one agent action firing multiple primary mechanics within a
single tick (REQ-V12-ENGINE-04). This unblocks richer narrative — e.g., "I open the
chest and take the key" — without changing the mechanic protocol or adding new
simulation stages. The authoritative decision log is `.planning/PROJECT.md` Key
Decisions, where this appears as v1.2 D-01.

## Problem

Today's classifier emits a single `ClassifiedAction`; an action like "I open the chest
and take the key" collapses to one verb (e.g., `open`), silently dropping the second
sub-action (`take`). The resident agent then receives an observation describing only
the first mechanic outcome, which is incoherent with their stated intent.

## Design Options Considered (MORNING-HANDOFF §E1)

### Option 1: Classifier emits `actions: [...]` list (CHOSEN)

The classifier already understands sequential English ("and", "then"). The change is to
update `VerdictOk` to hold `actions: list[ClassifiedAction]` instead of a single
`classified: ClassifiedAction`. Single-verb inputs wrap as a one-element list, giving
full back-compat to all existing callers.

No new component, no extra LLM call. Back-compat property `verdict.classified` returns
`actions[0]` so all existing engine.py call sites compile and run without modification.

Blast radius is contained to three files:
- `src/token_world/engine/models.py` — schema change: `classified` field → `actions` list
- `src/token_world/engine/classifier.py` — system prompt update + `SCHEMA_VERSION` bump
- `src/token_world/engine/engine.py` — iteration loop over `verdict.actions` (Wave 2)

### Option 2: Top-K mechanic matching (REJECTED)

Instead of teaching the classifier to decompose, the matcher would return the top-K
mechanics by score. Rejected because `check()` may pass for accidentally-overlapping
mechanics not intended to fire together. Correctness risk without additional guardrails
that would increase complexity beyond Option 1's blast radius.

### Option 3: ActionDecomposer stage (REJECTED)

A dedicated `ActionDecomposer` pre-stage (separate LLM call) would split multi-verb
input before classification. Rejected because it adds an extra LLM call per multi-verb
action, increasing latency and cost — directly violating the hobby-project budget
constraint in `PROJECT.md` Constraints section.

## Implementation Contract

### Data flow

```
classifier → VerdictOk.actions: list[ClassifiedAction]   (non-empty; validated by Pydantic)
           ↓
engine Wave 2: for each sub-action in verdict.actions:
    match → decide → execute
    collect all ExecutionTrace nodes
           ↓
TickSummary: classified_action = actions[0]  (back-compat)
             classified_actions = [all sub-actions]  (new field, Wave 2)
```

### Classifier system prompt contract (schema version 2.0)

The classifier emits one of four JSON shapes. The `ok` shape is:

```json
{"kind":"ok","actions":[{"verb":"<verb>","actor":"<actor id>","target":"<target id|null>","indirect_object":"<recipient id|null>","params":{}}],"confidence":0.0-1.0}
```

For multi-verb actions, the `actions` array contains one entry per sub-action:

```
action 'I open the chest and take the key'
→ ok, actions=[{verb='open',target='chest'},{verb='take',target='key'}]
```

### VerdictOk schema

```python
class VerdictOk(BaseModel):
    kind: Literal["ok"] = "ok"
    actions: list[ClassifiedAction] = Field(min_length=1)  # non-empty; Pydantic-enforced
    confidence: float = Field(ge=0.0, le=1.0)

    @property
    def classified(self) -> ClassifiedAction:
        """Back-compat: returns actions[0]. All existing callers work unchanged."""
        return self.actions[0]
```

Empty `actions` lists raise `ValidationError` before reaching the engine (mitigates T-16-01).

### Engine iteration (Wave 2)

- For each sub-action in `verdict.actions`: run `match → decide → execute`
- First `YieldDecision` on any sub-action halts the whole tick (first-yield-wins)
- `RefuseDecision` on a sub-action is recorded but other sub-actions still run
- Combined `ExecutionTrace` returned from all sub-actions (root trace chains sub-results)

### TickSummary back-compat (Wave 2)

- `classified_action` field: unchanged — uses `actions[0]`
- `classified_actions` field: new list field recording all sub-actions

## Key Decisions

| Decision | Value | Rationale |
|----------|-------|-----------|
| Single-action back-compat | `verdict.classified` property | Minimises diff to engine.py callers |
| Refuse-continues policy | Other sub-actions run after a refuse | Consistent with independent-action semantics |
| First-yield-wins | YieldDecision on any sub-action halts the tick | Avoids partial mechanic authoring loops |
| SCHEMA_VERSION | bumped to "2.0" | Signals prompt contract change to hash registry |

## Non-Goals (this phase)

- Per-sub-action diagnostics dashboard panels (v2.0)
- Multi-agent conflict detection (v2.0 D-18)
- Option 2 top-K matching
- Option 3 ActionDecomposer stage
