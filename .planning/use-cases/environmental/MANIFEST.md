# Environmental Use Cases — Manifest

Environmental is the chain-execution heavy category: fire spread, weather,
decay, seasons, terrain effects, light/dark, and contagion. These exercise
the `environmental_reaction` seed mechanic and the engine's ability to
cascade mechanic triggers without infinite loops. UC-V01 is the one case
the seed mechanic nominally covers; the rest all extend into gap territory.

| ID     | Slug              | Title                          | Scenario (one line)                                                                          | No seed mechanic? | Notes                                                                                 |
|--------|-------------------|--------------------------------|----------------------------------------------------------------------------------------------|--------------------|---------------------------------------------------------------------------------------|
| UC-V01 | fire-spread       | Fire spread                    | Fire on torch spreads to adjacent flammable wooden table.                                    | no                 | environmental_reaction seed covers basic spread; chain-depth behavior may surface gap. |
| UC-V02 | weather-change    | Weather change                 | Rain begins; outdoor entities become wet; fire extinguishes.                                 | YES                | Needs global-state mechanic + cross-cutting property mutation.                        |
| UC-V03 | decay             | Decay                          | Uneaten apple rots after N ticks into rotten_apple.                                          | YES                | Tick-driven mechanic with transformation (remove + add).                              |
| UC-V04 | seasons           | Seasons                        | Season advances from summer to autumn; trees shed leaves.                                    | YES                | Cascading periodic mechanic; tests long-horizon scheduling.                           |
| UC-V05 | terrain-effect    | Terrain effect                 | Alice in swamp moves at half speed.                                                          | YES                | Needs terrain-property lookup + movement cost modifier.                               |
| UC-V06 | light-and-dark    | Light and dark                 | Alice in a dark room can't observe entities unless she has a torch.                          | YES                | Observation seed doesn't model light; needs light-aware LOS check.                    |
| UC-V07 | contagion         | Contagion                      | Bob contracts a cold from alice; symptoms cascade.                                           | YES                | Needs contact-triggered mechanic + symptom progression.                               |

## Wave 2 Authoring Checklist

- [ ] `.planning/use-cases/environmental/UC-V01-fire-spread.md`
- [ ] `.planning/use-cases/environmental/UC-V02-weather-change.md`
- [ ] `.planning/use-cases/environmental/UC-V03-decay.md`
- [ ] `.planning/use-cases/environmental/UC-V04-seasons.md`
- [ ] `.planning/use-cases/environmental/UC-V05-terrain-effect.md`
- [ ] `.planning/use-cases/environmental/UC-V06-light-and-dark.md`
- [ ] `.planning/use-cases/environmental/UC-V07-contagion.md`
