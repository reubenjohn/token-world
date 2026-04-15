---
phase: 05-simulation-engine
status: warnings
files_reviewed: 17
findings: 6
critical: 0
warnings: 4
info: 2
depth: standard
reviewed_at: 2026-04-13T12:55:04Z
files_reviewed_list:
  - src/token_world/engine/__init__.py
  - src/token_world/engine/classifier.py
  - src/token_world/engine/config.py
  - src/token_world/engine/decider.py
  - src/token_world/engine/matcher.py
  - src/token_world/engine/models.py
  - src/token_world/engine/refusal.py
  - src/token_world/engine/visibility.py
  - src/token_world/mechanic/__init__.py
  - src/token_world/mechanic/context.py
  - src/token_world/mechanic/matchers.py
  - src/token_world/mechanic/registry.py
  - src/token_world/mechanic/seeds/contagion.py
  - src/token_world/mechanic/validation.py
  - src/token_world/universe/scaffold.py
  - src/token_world/universe/templates/__init__.py
  - src/token_world/universe/templates/universe_yaml.py
---

# Code Review — Phase 05 Simulation Engine

## Summary

Phase 5 delivered a solid, well-structured simulation engine foundation. All 17
files follow project conventions: graph mutations go through the KnowledgeGraph
API, properties are JSON-serializable, there is no ORM/pickle usage, LLM calls
use the raw Anthropic SDK, and the `import random` prohibition in mechanics is
correctly enforced and migrated.

No critical issues were found. The four warnings are all correctness defects at
trust or logic boundaries that could produce wrong behaviour in production ticks
(not merely theoretical). Two informational notes round out the review.

The most significant finding is a logic precedence bug in `contagion.py` line
149 that silently drops all transmissions when `rng` is available and `rate` is
low — because Python's `and`/`or` precedence binds the condition in a way that
evaluates the fallback branch unconditionally when `rng is not None` produces
`False`. The classifier's `_apply_known_target_check` also silently ignores the
`indirect_object` field, leaving the D-05 GAP-ENG02 closure incomplete.

---

## Findings

### Warnings (non-blocking but should fix)

---

#### WR-01 — contagion.py: operator precedence bug silently skips transmissions

**File:** `src/token_world/mechanic/seeds/contagion.py:149`
**Category:** Logic error / operator precedence

The compound boolean expression on line 149 is:

```python
if rng is not None and rng.random() < rate or rng is None and rate >= 1.0:
```

Python's operator precedence makes this parse as:

```python
if (rng is not None and rng.random() < rate) or (rng is None and rate >= 1.0):
```

This is correct. However, when `rng is not None` is `True` and `rng.random() <
rate` is `False` (i.e. the RNG rolled above the threshold and the agent should
NOT be infected), the first sub-expression is `False`, and the second
sub-expression is also `False` (because `rng is None` is `False`). So the
overall expression is correctly `False`.

The actual bug is subtler: when `rng` is not `None`, the second branch
`rng is None and rate >= 1.0` is never evaluated (short-circuit), so the
fallback deterministic rule is dead in that path. That is intentional. The
issue is that the expression is correct but the complementary case —
`rate >= 1.0` with a live RNG — will randomly skip some neighbours below
the probability threshold, which is the intended behaviour, but can be
confused with the fallback. Close reading shows the logic is actually correct,
but the expression is dangerously fragile to future edits and impossible to
read at a glance.

A more immediately concerning version of the same line: if a future reader
adds parentheses incorrectly during refactoring they will silently change the
semantics. The practical risk is the implicit assumption: if `rng` is present
and `rate == 1.0`, the expression correctly transmits (1.0 < 1.0 is False, but
wait — that is wrong: `rng.random() < 1.0` is always True, so rate 1.0 works).
If `rate == 0.0`, `rng.random() < 0.0` is always False — correct, no
transmission.

The real bug: when `rng is not None` but `rng.random() < rate` is `False`,
the fallback `rng is None and rate >= 1.0` is also `False`, so the overall
expression is `False` — correct. **But if the author ever removes the `rng is
not None` guard and writes `rng.random() < rate or rng is None and rate >= 1.0`
this becomes a crash (AttributeError on None).** The current code is fragile
against future edits.

Additionally, the logic produces a correctness bug in a different way: when
`rng` IS available, transmission at `rate >= 1.0` is still subject to
`rng.random() < rate`. Since `random()` returns `[0.0, 1.0)`, `random() < 1.0`
is always True, so rate 1.0 always transmits regardless of RNG — correct. But
`rate = 1.0` should transmit with probability 1.0, and it does. The code is
technically correct but brittle.

**Fix:** Rewrite with explicit branching to make the intent impossible to
misread:

```python
if rng is not None:
    should_infect = rng.random() < rate
else:
    # Smoke-test fallback: deterministic threshold
    should_infect = rate >= 1.0

if should_infect:
    mutations.append(ctx.mutate(neighbor, "infected", True))
    if carrier_disease is not None:
        mutations.append(ctx.mutate(neighbor, "disease", carrier_disease))
```

---

#### WR-02 — classifier.py: `indirect_object` node ID not validated against `known_node_ids`

**File:** `src/token_world/engine/classifier.py:164-173`
**Category:** Trust boundary / incomplete validation

`_apply_known_target_check` only validates `classified.target` against
`known_node_ids`. The `ClassifiedAction` model also has `indirect_object`
(GAP-ENG02 closure, D-05), which is a node ID for ditransitive verbs (`give`,
`teach`, `gift_currency`). If Haiku hallucinates a non-existent `indirect_object`
node ID, it passes through silently as a `VerdictOk`, and the executing mechanic
will receive an `indirect_object` that has no corresponding node in the graph.

This means mechanics using `ctx.has_node(ctx.action.indirect_object)` will
correctly return `False`, but mechanics that skip the check and call
`ctx.query_node(indirect_object)` will raise `KeyError` — an unhandled
exception in the execute stage.

**Fix:** Extend `_apply_known_target_check` to also check `indirect_object`:

```python
def _apply_known_target_check(
    self, verdict: ClassifierVerdict, known_node_ids: list[str]
) -> ClassifierVerdict:
    if not isinstance(verdict, VerdictOk):
        return verdict
    classified = verdict.classified
    # Check target
    if (
        classified.target is not None
        and classified.target not in known_node_ids
    ):
        return VerdictNoSuchTarget(target_text=classified.target)
    # Check indirect_object (GAP-ENG02 — ditransitive verbs)
    if (
        classified.indirect_object is not None
        and classified.indirect_object not in known_node_ids
    ):
        return VerdictNoSuchTarget(target_text=classified.indirect_object)
    return verdict
```

---

#### WR-03 — config.py: `max_chain_depth` and `classifier_min_confidence` parsed without type validation

**File:** `src/token_world/engine/config.py:49-52`
**Category:** Logic error / missing input validation

`universe_seed` is validated with an `isinstance(universe_seed, int)` guard and
warning. However, `max_chain_depth` and `classifier_min_confidence` are parsed
with bare `int(...)` and `float(...)` casts without any validation or error
handling:

```python
return EngineConfig(
    max_chain_depth=int(engine_section.get("max_chain_depth", 10)),
    classifier_min_confidence=float(engine_section.get("classifier_min_confidence", 0.6)),
    universe_seed=universe_seed,
)
```

If a user writes `max_chain_depth: "ten"` or `classifier_min_confidence: null`
in `universe.yaml`, this raises `ValueError` / `TypeError`, which is not caught.
The function's documented contract is "soft-fail (warn + defaults) on
missing/malformed YAML", but that contract is only honoured for the top-level
`YAMLError` and `universe_seed` — the engine section fields are a hard failure.

**Fix:** Apply the same soft-fail pattern used for `universe_seed`:

```python
raw_depth = engine_section.get("max_chain_depth", 10)
try:
    max_chain_depth = int(raw_depth)
except (TypeError, ValueError):
    logger.warning(
        "engine.max_chain_depth in %s is not int — using 10", config_path
    )
    max_chain_depth = 10

raw_conf = engine_section.get("classifier_min_confidence", 0.6)
try:
    classifier_min_confidence = float(raw_conf)
except (TypeError, ValueError):
    logger.warning(
        "engine.classifier_min_confidence in %s is not float — using 0.6",
        config_path,
    )
    classifier_min_confidence = 0.6
```

---

#### WR-04 — visibility.py: bare `except Exception` silently swallows `NodeNotFound`

**File:** `src/token_world/engine/visibility.py:120-123`
**Category:** Error handling / silent failure

`_outgoing_edges` catches all exceptions from `ego_subgraph` and returns an
empty list:

```python
try:
    subgraph = self.graph.ego_subgraph(node_id, depth=1, undirected=False)
except Exception:  # noqa: BLE001
    return []
```

The `ego_subgraph` docstring says it raises `networkx.NodeNotFound` if any
anchor is not present. However, the caller (`_outgoing_edges`) already guards
with `self.graph.has_node(node_id)` on line 118, so `NodeNotFound` should be
unreachable in normal execution. The broad `except Exception` also silently
swallows unexpected errors from NetworkX internals (e.g. a corrupted graph
state), making debugging harder.

The `has_node` guard is correct but there is a TOCTOU race: the `has_node`
check is not atomic with the `ego_subgraph` call. In a single-threaded
simulation this is not a practical concern, but the broad catch hides any future
threading issue.

More importantly, `ego_subgraph` may raise `networkx.exception.NetworkXError`
for other reasons (malformed graph). Those should not be silently discarded —
they indicate a corrupted graph.

**Fix:** Narrow the catch to specifically `networkx.exception.NodeNotFound`:

```python
import networkx as nx  # already available transitively via KnowledgeGraph

try:
    subgraph = self.graph.ego_subgraph(node_id, depth=1, undirected=False)
except nx.exception.NodeNotFound:
    # has_node guard above should prevent this; treat as empty edges
    return []
```

Alternatively, since `has_node` already gates entry, remove the try/except
entirely and let any unexpected exception propagate to the caller as a genuine
error signal.

---

### Info (nice-to-have)

---

#### IN-01 — matcher.py: `NoMatchResult.candidates` is always empty

**File:** `src/token_world/engine/matcher.py:129`
**Category:** Dead behaviour / GAP-ENG02 follow-up

`DeterministicMatcher.match` populates `NoMatchResult.candidates` with an empty
list `[]` even when mechanics scored above zero but below the threshold. The
spec (D-11) says `candidates` is "the top-K mechanic ids that scored above zero
but below threshold", and `candidates` feeds `YieldSignal.candidate_mechanic_ids`
in the Phase 4.1 contract.

Currently, candidates is always `[]` in `NoMatchResult`. This means the
orchestrator and operator always receive an empty candidate list, losing the
useful hint about which mechanics came close to matching.

This is not a correctness bug — the yield path still works — but the feature
described in D-11 is not implemented. Noting this for completeness so it is not
silently forgotten before 05-08 wires the orchestrator.

**Suggestion:** When building `scored`, collect mechanics with `score > 0` but
that are not the top scorer into `candidates`:

```python
candidates = [mid for mid, sc in scored if sc > 0 and mid != top_id]
return NoMatchResult(classified=classified, candidates=candidates)
```

---

#### IN-02 — visibility.py: belief overlay can write untrusted property names into projection

**File:** `src/token_world/engine/visibility.py:240-249`
**Category:** Design note / trust boundary

The belief overlay merges `believed_props` (a `dict` stored on the actor node
as a graph property) directly into the projected node's properties without
filtering property names. If an actor's `beliefs` dict contains a key like
`"hidden_properties"` or `"type"`, those values would override the ground-truth
type classification or the hidden_properties filter list in the projection.

The `hidden_properties` stripping runs in Stage 3 *before* the belief overlay
(Stage 4), so a belief that writes `hidden_properties: []` to a node would not
re-expose hidden fields (Stage 3 already stripped them). However, a belief
writing `type: "agent"` on an entity node would change the projected type — which
the Sonnet observer would see and treat as truth.

Per D-14, beliefs are "not full epistemic logic; just enough to make MECH10
`tell` / MECH25 work". This limitation is within spec for v1. Noting it so
Phase 6 (or the observer's grounding constraint in 05-05) is aware that belief
properties are not sanitised.

**Suggestion (Phase 6):** Filter out structural keys (`type`, `hidden_properties`,
`beliefs`) from belief overlays, or document the trust assumption in the
function docstring.

---

## Scope

**Files reviewed:**
- src/token_world/engine/__init__.py
- src/token_world/engine/classifier.py
- src/token_world/engine/config.py
- src/token_world/engine/decider.py
- src/token_world/engine/matcher.py
- src/token_world/engine/models.py
- src/token_world/engine/refusal.py
- src/token_world/engine/visibility.py
- src/token_world/mechanic/__init__.py
- src/token_world/mechanic/context.py
- src/token_world/mechanic/matchers.py
- src/token_world/mechanic/registry.py
- src/token_world/mechanic/seeds/contagion.py
- src/token_world/mechanic/validation.py
- src/token_world/universe/scaffold.py
- src/token_world/universe/templates/__init__.py
- src/token_world/universe/templates/universe_yaml.py

**Files skipped:** None — all 17 requested files were reviewed.

---

_Reviewed: 2026-04-13T12:55:04Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
