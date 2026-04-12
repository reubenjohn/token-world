# Token World Use Case Library

This directory holds the pressure-test corpus for the Token World simulation
framework. Each use case is a single markdown file that pairs a human-readable
vignette with machine-parseable YAML frontmatter describing the initial graph,
the actor's intent, the expected observations, and any gaps the scenario
surfaces. The library is authored in Phase 3 and consumed in two ways: Phase 3
gap analysis distills per-layer weaknesses from the `gaps[]` fields, and Phase
6 regression uses `setup.graph_builder` + `actions[]` + `expected_observations[]`
as an integration test spec.

The authoring trust model treats these files as committed code, not data. The
`setup.graph_builder` string is executed as Python by the Phase 6 regression
harness. Use cases therefore pass through the same review gates as source
code — no untrusted input ever crosses this boundary.

## How to author a new use case

1. Pick an unclaimed row from your category's `MANIFEST.md`. The manifest
   specifies the exact `UC-ID`, slug, and target file path.
2. Copy `_TEMPLATE.md` to `<category>/UC-XX-<slug>.md` (the filename pattern
   must match `UC-[SOVRE]\d{2}-<kebab-slug>.md`).
3. Fill the frontmatter, keeping every key required by
   `src/token_world/use_cases/loader.py::validate_frontmatter`.
4. Write the narrative sections (`# Title`, `## Vignette`, `## Why this
   matters`, `## Related use cases`). Vignettes should read like a short
   scene; "Why this matters" names the framework concern being exercised.
5. For every gap the scenario exposes, add a `gaps[]` entry with `layer`,
   `severity`, `summary`, and `proposed_fix`. Inline gap capture is where
   Phase 3 draws its signal — do not skip this even for "obvious" misses.
6. Validate locally:
   `uv run pytest tests/test_design_validation/test_use_case_schema.py -v`
7. Commit only after the schema tests pass.

## ID scheme

Stable IDs are assigned up front in each category's `MANIFEST.md`; authors do
not invent new IDs. The letter in the ID denotes the category:

| Category       | Letter | ID range         |
|----------------|--------|------------------|
| spatial        | S      | UC-S01..UC-S07   |
| social         | O      | UC-O01..UC-O08   |
| resource       | R      | UC-R01..UC-R07   |
| environmental  | V      | UC-V01..UC-V07   |
| edge-case      | E      | UC-E01..UC-E06   |

Total: 7 + 8 + 7 + 7 + 6 = 35 use cases. The validator enforces the regex
`^UC-[SOVRE]\d{2}$` on every file's `id` field. `V` covers environmental
because `E` is reserved for edge-case; `O` covers social because `S` is
reserved for spatial.

## Required frontmatter keys

Every key listed here is enforced by `validate_frontmatter`; files missing
any of them will fail the schema test.

| Key                           | Description                                                                                              |
|-------------------------------|----------------------------------------------------------------------------------------------------------|
| `id`                          | Matches `^UC-[SOVRE]\d{2}$`. Must be unique across the library.                                          |
| `category`                    | One of `spatial`, `social`, `resource`, `environmental`, `edge-case`. Must match the enclosing folder.   |
| `title`                       | Short human-readable title; shown in summaries.                                                          |
| `status`                      | One of `draft`, `reviewed`, `locked` (see Status lifecycle).                                             |
| `setup.graph_builder`         | Multi-line Python string. Executed by Phase 6 harness against a fresh `KnowledgeGraph` named `kg`.       |
| `actions[]`                   | List of `{actor, intent, classified}` entries. See Structured action format.                             |
| `expected_observations[]`     | List of `{actor, narrative_contains, graph_assertions}` entries. See Structured observation format.      |
| `gaps[]`                      | List of `{layer, severity, summary, proposed_fix}` entries. Empty list is allowed if nothing is missing. |
| `gaps[].layer`                | One of `graph`, `mechanic`, `engine`.                                                                    |
| `gaps[].severity`             | One of `address-now`, `defer`, `out-of-scope`.                                                           |
| `gaps[].summary`              | One-sentence description of the missing capability.                                                      |
| `gaps[].proposed_fix`         | Concrete suggestion for how the gap could be closed (may name a mechanic, a graph API, an engine hook).  |

## Gap taxonomy

Every gap is classified by **layer** (where the fix belongs) and **severity**
(when/whether to fix). These two axes are what Wave 4 synthesis aggregates
across all use cases.

### Layers

- **graph** — A missing query, index, or property access pattern on the
  `KnowledgeGraph` API. Example: "no built-in line-of-sight query across
  occluding entities."
- **mechanic** — A missing rule or side effect. The graph could express it,
  but no mechanic reads/writes the relevant properties. Example: "no
  doorway traversal mechanic; movement seed only handles direct edges."
- **engine** — A missing orchestration capability. Example: "no cycle
  detection when mechanic A triggers B triggers A."

### Severities

- **address-now** — Blocks a realistic v1 scenario. Must be resolved before
  Phase 6 regression is meaningful. Expect one or more Phase 4/5 plans to
  close these.
- **defer** — Nice-to-have but not blocking v1. Captured for the backlog and
  revisited at milestone boundaries.
- **out-of-scope** — Explicitly excluded by `PROJECT.md` (multi-agent,
  multimodal, dashboards, etc.). Document the gap so future planners don't
  re-discover it.

## Structured action format

Each `actions[]` entry captures one actor's input to the simulation engine
along with the already-classified verb/target it should resolve to. The
engine's classifier is graded against the `classified` subfield in Phase 6.

```yaml
actions:
  - actor: alice
    intent: "walk east through the doorway into room_b"
    classified:
      verb: move
      direction: east
      target: doorway_1
```

`classified` may contain any keys relevant to the verb (`target`, `direction`,
`indirect_object`, `amount`, `utterance`, etc.). The Phase 6 harness supplies
`intent` to the classifier and asserts the resulting dict is a superset of
`classified`.

## Structured observation format

Each `expected_observations[]` entry is what the engine should produce after
all mechanics fire. Narrative checks are fuzzy substring matches; graph
assertions are a fixed declarative vocabulary.

```yaml
expected_observations:
  - actor: alice
    narrative_contains: ["room_b", "doorway"]
    graph_assertions:
      - kind: has_edge
        src: alice
        dst: room_b
        relation: located_in
      - kind: not_has_edge
        src: alice
        dst: room_a
        relation: located_in
      - kind: property_equals
        node: alice
        property: stamina
        value: 9
```

Supported `graph_assertion` kinds (fixed vocabulary; Phase 6 harness
implements exactly these):

| kind               | required keys                             | meaning                                                      |
|--------------------|-------------------------------------------|--------------------------------------------------------------|
| `has_node`         | `node`                                    | Node exists in the graph.                                    |
| `has_edge`         | `src`, `dst`, `relation`                  | Directed edge with the given relation is present.            |
| `not_has_edge`     | `src`, `dst`, `relation`                  | Directed edge with that relation is absent.                  |
| `has_property`     | `node`, `property`                        | Node has the property (any value).                           |
| `property_equals`  | `node`, `property`, `value`               | Node's property equals the literal value.                    |
| `not_has_property` | `node`, `property`                        | Node does not have the property.                             |

Do not invent new assertion kinds; if a scenario needs one, record it in
`gaps[]` with `layer: engine` so the regression harness can be extended.

## Status lifecycle

- **draft** — Author wrote the file during Wave 2. Schema passes; content
  may be rough.
- **reviewed** — Wave 3 category aggregator has sanity-checked the
  structured pairs (graph_builder executes, assertions are consistent),
  deduplicated gaps, and confirmed the vignette matches the YAML.
- **locked** — Phase 6 regression harness depends on the file. Changes
  require coordinated updates to the harness or a versioned migration.

## Authoring trust model

Use-case files are committed repo code. The Phase 6 regression harness
executes `setup.graph_builder` as Python against a live `KnowledgeGraph`.
Treat every file the same way you would treat test fixtures: reviewed,
owned by the team, never touched by external input at runtime. There is
no sandbox here by design — if a graph_builder string needs to evolve, it
evolves through the normal code review path.
