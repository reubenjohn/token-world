# Regression Suite — DVAL-03

Use-case regression suite: 35 Phase-3 UC manifests exercised through the real
engine pipeline with fake LLM clients.

## Purpose

This suite operationalises **DVAL-03**: ensure the simulation engine correctly
processes the 35 canonical use-case manifests authored in Phase 3. Each manifest
specifies an action, a pre-seeded graph, an `expected_outcome`, and
`graph_assertions` to verify post-tick state.

The suite answers the question: "Given this pre-classified action and this graph
state, does the engine + mechanic library produce the declared outcome?"

**What it validates:**

- Mechanic matching (does the right seed mechanic score highest for the verb?)
- Mechanic `check()` preconditions (does the gate logic fire correctly?)
- Mechanic `apply()` mutations (does the graph reach the asserted state?)
- Conservation checker (does the conservation layer catch violations?)
- Expected outcomes: `pass` → `ok`, `blocked` → `refused`, `yield` → `yielded`

**What it does NOT validate:**

- Observer prose quality (FakeObserver returns a fixed string — no Sonnet calls)
- Classification accuracy (FakeClassifier bypasses Haiku — no real LLM)
- Novel mechanic generation (operator harness not invoked)

## Running the Suite

```bash
# Run all 35 regression tests
uv run pytest -m regression

# Run with verbose output (shows each UC id)
uv run pytest -m regression -v

# Run a specific UC
uv run pytest -m regression -k UC-R02

# Run and stop on first failure
uv run pytest -m regression -x

# Run with detailed failure info
uv run pytest -m regression --tb=short
```

The suite is **excluded from the default `uv run pytest` run** via
`addopts = "-m 'not integration and not regression'"` in `pyproject.toml`.
This keeps CI fast and avoids 35 engine ticks on every normal dev cycle.

## How Failures are Interpreted

A failing regression test means one of:

1. **Missing `watches(VerbMatcher)` in the seed mechanic** — the mechanic
   doesn't declare its verb, so the DeterministicMatcher scores it 0 and the
   engine yields instead of executing. Fix: add `watches()` returning a
   `VerbMatcher` to the seed mechanic.

2. **Mechanic `check()` preconditions too strict** — the graph setup meets
   the UC's intent but the mechanic refuses (e.g., wrong edge relation name).

3. **Graph assertions wrong** — the mechanic executes but leaves a different
   graph state than the UC author expected.

4. **Expected outcome mismatch** — the UC says `blocked` but the engine
   yields (no mechanic found). Both indicate missing mechanics.

**Failures are intentional signals, not noise.** Do NOT mark them `xfail`.
Each failure maps to a `gaps:` entry in the manifest.

## Adding a New Use-Case

1. Drop a `UC-<Category><NN>-<slug>.md` file in
   `.planning/use-cases/<category>/` (e.g., `spatial/UC-S08-foo.md`).
2. Ensure the frontmatter has `actions[0].classified:` with a `verb` field.
   Without `classified`, the test skips with a human-readable reason.
3. Run `uv run pytest -m regression -k UC-S08` to see the new test.
4. Fix any failing mechanics to close the gap.

The test is auto-discovered via `_UC_ROOT.rglob("UC-*.md")` — no code changes
needed.

## Fake LLM Strategy

Per 06-RESEARCH §Open Question 2 and D-25:

- **FakeClassifier**: Returns `VerdictOk` with the manifest's
  `actions[0].classified` dict verbatim. No Haiku call. Makes the test
  deterministic and free.
- **FakeObserver**: Returns `"Action succeeded."` always (or the
  `refusal_narrative` verbatim when provided). No Sonnet call.

Rationale: 35 × 2 LLM calls per CI run = ~$0.05–0.50 and 2+ minutes. The
regression suite's value is mechanic correctness, not observer prose. Real
observer quality is validated by the playtest runner (`uv run token-world playtest`).

## Relationship to Plan 06-05 (Prompt Hash Change Detection)

Plan 06-05 implements `prompts.sha256.json` tracking. When any system prompt
hash changes (classifier, observer, or agent), the playtest runner automatically
triggers this regression suite via subprocess:

```bash
uv run pytest -m regression --tb=short --json-report \
    --json-report-file universe/regression-history.jsonl
```

Results are appended to `universe/regression-history.jsonl` for trend tracking
(AUTO-07). The regression suite is the "smoke test" that fires on every
prompt-engineering change.

## Extending Assertion Kinds

The `_verify_assertion()` function in `test_use_cases.py` supports the six
kinds from `use_cases.loader.VALID_ASSERTION_KINDS`:

| Kind              | Checks                                      |
|-------------------|---------------------------------------------|
| `has_node`        | Node exists in graph                        |
| `has_edge`        | Directed edge exists                        |
| `has_property`    | Node has named property (any value)         |
| `property_equals` | Node's property equals expected value       |
| `not_has_edge`    | Directed edge must NOT exist                |
| `not_has_property`| Node must NOT have named property           |

To add a new kind: (1) add it to `VALID_ASSERTION_KINDS` in
`src/token_world/use_cases/loader.py`, (2) add the matching `elif` branch in
`_verify_assertion()` in `test_use_cases.py`.
