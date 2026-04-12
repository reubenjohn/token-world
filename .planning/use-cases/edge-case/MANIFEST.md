# Edge-case Use Cases — Manifest

Edge-case is the framework robustness category: invalid targets, concurrent
actors, partial knowledge, nonsense input, circular chains, and locked-path
attempts. These are the scenarios where the engine must fail gracefully
rather than crash or hallucinate. All six surface engine-layer gaps since
no seed mechanic handles arbitrary invalid input.

| ID     | Slug                                | Title                              | Scenario (one line)                                                                  | No seed mechanic? | Notes                                                                             |
|--------|-------------------------------------|------------------------------------|--------------------------------------------------------------------------------------|--------------------|-----------------------------------------------------------------------------------|
| UC-E01 | action-against-nonexistent-target   | Action against nonexistent target  | Alice attacks a dragon; no dragon exists in graph.                                   | YES                | Tests engine error handling + graceful observation.                               |
| UC-E02 | concurrent-actors                   | Concurrent actors                  | Alice and bob both try to pick up the last apple on the same tick.                   | YES                | Turn-ordering; v1 may defer, but the scenario surfaces the engine decision.       |
| UC-E03 | partial-knowledge                   | Partial knowledge                  | Alice tries to open a locked chest she doesn't know is locked.                       | YES                | Needs per-agent belief graph vs ground truth; mirrors UC-O04 from the victim side. |
| UC-E04 | nonsense-input                      | Nonsense input                     | Alice says "gragh flibble xyzzy"; engine must respond coherently.                    | YES                | Classifier fallback behavior; no mechanic should fire.                            |
| UC-E05 | circular-chain                      | Circular mechanic chain            | Mechanic A triggers B triggers A; engine must detect and break the cycle.            | YES                | Engine-layer safety: cycle detection on triggered-mechanic stack.                 |
| UC-E06 | move-into-locked-room               | Move into a locked room            | Alice tries to walk through a locked door.                                           | YES                | Movement seed doesn't know about locks; graph has door.locked=true.               |

## Wave 2 Authoring Checklist

- [ ] `.planning/use-cases/edge-case/UC-E01-action-against-nonexistent-target.md`
- [ ] `.planning/use-cases/edge-case/UC-E02-concurrent-actors.md`
- [ ] `.planning/use-cases/edge-case/UC-E03-partial-knowledge.md`
- [ ] `.planning/use-cases/edge-case/UC-E04-nonsense-input.md`
- [ ] `.planning/use-cases/edge-case/UC-E05-circular-chain.md`
- [ ] `.planning/use-cases/edge-case/UC-E06-move-into-locked-room.md`
