# Phase 4: Discussion Log

**Gathered:** 2026-04-12
**Status:** Audit trail for CONTEXT.md (human reference only; not consumed by downstream agents)

---

## Gray areas presented

Two batches of four areas each (eight total):

1. Generation architecture
2. Validation pipeline
3. Retry & repair loop
4. Prompt context assembly
5. Generated artifacts
6. Diagnostics filesystem
7. Integration-test harness
8. Generator invocation surface

User selected: all eight, with a large free-text overlay that reframed the phase.

---

## User's reframe (verbatim highlights)

> "The main course correction is an inversion of control where now we have a highly capable and sophisticated top level coding agent like Claude Code with Opus driving the simulation in collaboration with a human, and the entire simulation is basically just tool calls for that agent. So the simulation instance folder acts just like a codebase and the tool calls elegantly make that codebase come to life by simulating agents and running those mechanics."

> "I think we don't need to do a lot of heavy engineering for mechanic generation. Developing a codebase with sophisticated SDLC is the bread and butter of these modern coding agents."

> "Whether we need a dedicated folder for each mechanic, or can we have it a bit more like a regular codebase where we have more code reuse between mechanics somehow and essentially these mechanics just provide abstractions or conveniences over the framework primitives with clear API contracts that can be run within the simulation."

> "I would like you to be as autonomous as possible and generously leverage subagents. Token cost is no barrier, filling context is."

---

## Decisions recorded (one-line per area; full rationale in CONTEXT.md)

| Area | Decision |
|------|----------|
| Generation architecture | No bespoke pipeline. Operator (Claude Code + Opus via Agent SDK) authors mechanics as Python code. → D-01, D-02 |
| Mechanic layout | Flat Python modules (`mechanics/<id>.py`); class attributes replace meta.yaml; shared helpers as `_*.py`. **Supersedes Phase 2 D-15/D-16.** → D-03..D-09 |
| Code-reuse style | Free functions in `_*.py` default; base classes only when 3+ mechanics share a pattern. → D-11 |
| Validation pipeline | Single implementation; stages: syntax → AST rules → import → contract → tests → dry-execute. → D-12..D-16 |
| AST rules | Must subclass Mechanic; no `networkx`, no `eval/exec/__import__/compile/globals/open`. Allows stdlib, `token_world.mechanic.*`, sibling `_*.py`. → D-14 |
| Retry/repair | Not a pipeline. Operator iterates naturally. → D-17 |
| Prompt context | Not a pipeline. Replaced by authoring guides + clean codebase. → D-18 |
| MCP tool surface | Drop `register_mechanic`. Minimal tools: `resume_tick`, `rollback`, `list_mechanics`. Auto-scan + CLI `validate-mechanic` replace it. → D-19, D-20 |
| Diagnostics filesystem | Per-tick folders under `universe/diagnostics/tick_<id>/`; schema versioned; manual pruning. → D-21..D-25 |
| Integration test harness | pytest parametrized over Phase 3 use-case manifests. → D-26..D-29 |
| Authoring guides | `docs/guides/authoring-mechanics.md` + universe-local CLAUDE.md section + `scaffold-mechanic` CLI helper. → D-30..D-32 |

---

## User interventions during discussion

1. **Interrupt:** "Sorry increased your effort setting to max because this needs to be thought through carefully." → Stopped mid-write, restructured approach: more analysis before writing CONTEXT.md.

2. **Confidence challenge:** "Are you confident about 'Phase 2 revision (challenging D-15)' and what it might look like?" → Reconsidered initial default. Revised from "multi-mechanic per thematic file" to "one mechanic per file (`mechanics/<id>.py`)" to preserve per-file git history. Blast-radius estimate revised down from ~300 LOC to ~200 LOC.

3. **Follow-up questions:** "What is the purpose of tags?", "What about non-seed mechanics?", "register_mechanic — tool or automatic?", "What do you mean same validation pipeline?" → Answered each explicitly; confirmed tags are actively used for filtering; non-seed mechanics follow identical layout; dropped `register_mechanic` MCP tool; clarified "same validation pipeline" = single implementation, multiple entry points.

4. **Directive:** "Update any documents in the codebase to reflect the current intention or at the very least mark obsolete content as superseded, but ideally just replace obsolete content." → Dispatched subagent to update all living docs; Phase 2's CONTEXT.md got SUPERSEDED annotations rather than rewrite (historical artifact).

---

## Subagent work commissioned

1. **Codebase assessment** (Explore agent): surveyed `src/token_world/mechanic/*` to estimate blast radius of folder → flat migration. Delivered layout proposal, LOC estimate, tag-usage confirmation, redundancy analysis. Used to validate D-03..D-09.

2. **Doc updates** (general-purpose agent): surgical edits across PROJECT.md, REQUIREMENTS.md, DECISIONS.md, root CLAUDE.md, STACK.md, THEACT-PATTERNS.md, architecture.md, Phase 2 CONTEXT.md (supersession annotations). Completed successfully.

---

## Deferred / noted for later

- Runtime sandboxing (v2)
- Automatic diagnostics rotation (v2)
- Lazy mechanic loading (optimization, if needed)
- `.claude/skills/author-mechanic/` inside universes (only if authoring friction emerges)
- Coherence checking HARD-02 (v2)
- Cost monitoring HARD-03 (v2)

---

*Phase: 04-llm-mechanic-generation*
*Log: 2026-04-12*
