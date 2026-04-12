# Social Use Cases — Manifest

Social is the variety-heavy category: trade, persuasion, deception, teaching,
cooperation, observation, and communication each exercise different
engine-layer concerns (indirect objects, belief modeling, broadcast scope).
No seed mechanic covers social interaction today, so nearly every case here
surfaces a gap. The outlier (UC-O07) leans on the observation seed.

| ID     | Slug                     | Title                              | Scenario (one line)                                                                 | No seed mechanic? | Notes                                                                             |
|--------|--------------------------|------------------------------------|-------------------------------------------------------------------------------------|--------------------|-----------------------------------------------------------------------------------|
| UC-O01 | trade-negotiation        | Trade negotiation                  | Alice offers bob a sword for 10 coin.                                               | YES                | No trade/negotiation mechanic; tests multi-actor commit semantics.                |
| UC-O02 | persuasion-check         | Persuasion check                   | Alice tries to convince bob to unlock a door.                                       | YES                | Needs belief/disposition state + persuasion mechanic.                             |
| UC-O03 | give-sword-to-bob        | Give sword to bob                  | Multi-object: alice gives the sword to bob.                                         | YES                | Tests indirect-object modeling in classifier + transfer mechanic.                 |
| UC-O04 | deception                | Deception                          | Alice tells bob the chest is empty when it isn't.                                   | YES                | Needs per-agent belief graph (separate from ground truth).                        |
| UC-O05 | teaching                 | Teaching a skill                   | Alice teaches bob how to use a lockpick.                                            | YES                | Needs skill/capability mechanic + knowledge transfer.                             |
| UC-O06 | cooperation-lift-heavy   | Cooperation to lift a heavy object | Alice and bob lift a boulder together.                                              | YES                | No multi-actor precondition in seed mechanics; exercises concurrent intent.       |
| UC-O07 | observation-of-agent     | Observation of another agent       | Alice looks at bob and observes bob's visible state.                                | no                 | Observation seed partially covers; reveals gaps in what counts as "visible."      |
| UC-O08 | speech-broadcast         | Speech broadcast                   | Alice shouts; all agents within earshot hear.                                       | YES                | Needs spatial + social composition: `within` radius + broadcast mechanic.         |

## Wave 2 Authoring Checklist

- [ ] `.planning/use-cases/social/UC-O01-trade-negotiation.md`
- [ ] `.planning/use-cases/social/UC-O02-persuasion-check.md`
- [ ] `.planning/use-cases/social/UC-O03-give-sword-to-bob.md`
- [ ] `.planning/use-cases/social/UC-O04-deception.md`
- [ ] `.planning/use-cases/social/UC-O05-teaching.md`
- [ ] `.planning/use-cases/social/UC-O06-cooperation-lift-heavy.md`
- [ ] `.planning/use-cases/social/UC-O07-observation-of-agent.md`
- [ ] `.planning/use-cases/social/UC-O08-speech-broadcast.md`
