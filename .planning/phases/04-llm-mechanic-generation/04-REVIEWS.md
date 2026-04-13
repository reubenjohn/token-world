---
phase: 4
reviewers: [claude]
reviewed_at: 2026-04-13T03:04:42Z
plans_reviewed: [04-01-PLAN.md, 04-02-PLAN.md, 04-03-PLAN.md, 04-04-PLAN.md, 04-05-PLAN.md, 04-06-PLAN.md, 04-07-PLAN.md, 04-08-PLAN.md, 04-09-PLAN.md, 04-10-PLAN.md, 04-11-PLAN.md, 04-12-PLAN.md]
---

# Cross-AI Plan Review — Phase 4

> **Note:** Only `claude` CLI was available locally. `gemini`, `codex`, `coderabbit`, and `opencode` are not installed. Self-skip rule was bypassed at user direction since this review session has clean context. Single-reviewer; no consensus synthesis possible.

## Claude Review

# Phase 4 Plan Review: Mechanic Authoring & Validation Infrastructure

## 1. Summary

This is an ambitious, well-structured phase that delivers five infrastructure plans (01-05) followed by six seed-authoring clusters (06-11) and a final gate (12), closing 28 gaps and flipping ~28 of 35 use cases to pass. The plans are notably mature: they cite prior decisions precisely, reuse Phase 3 artifacts rather than reinventing them, and consistently wire the validation gate → registry → diagnostics → integration-harness chain. The inversion-of-control reframe (D-01/D-02) is honored throughout — no bespoke generation pipeline is built. The primary concerns are **cluster-scope underestimation** in plans 06-11 (each authors 3-5 mechanics + tests + UC manifest edits + potentially harness tweaks, which is substantial for a single plan), **naive verb→mechanic matching** that accumulates harness extensions across clusters, and a few **contract ambiguities** between what plan 02 delivers and what plans 06-11 assume about `MechanicContext`.

## 2. Strengths

- **Decision traceability is excellent** — every plan cites D-## from CONTEXT.md in its frontmatter and tasks; deviations (e.g., UC-O01 single-tick vs multi-turn, UC-R05 ambient-decay) have explicit decision trees
- **D-15 wiring loop is explicitly closed** in 04-03 Task 4 — the registry→sink write was flagged as a hook in 04-02 and properly wired later rather than being orphaned
- **W-prefixed fixes** (W2, W5, W7, W8, W9) in plans 04, 12 show the plans have been through at least one critique cycle — outcome branching is explicit in the test body, invariant is pytest-enforced not grep-enforced, Wave 0 files are gated before the compliance flip
- **Reuse discipline**: 04-04 consumes existing `use_cases/loader.py` per D-28; 04-06 builds `_find_open_passage` as a helper that 04-07 explicitly reuses; `_count_holds` / `_refuse_with_narrative` in 04-08 are cited by downstream plans
- **Security hygiene is consistent**: no `shell=True`, argv-list subprocess, path-traversal mitigations via `resolve().relative_to(root)`, symlink refusal in prune, boot-time `.tmp.*` cleanup, mechanic-id regex gate on scaffold
- **T-04-AST-BYPASS is honestly disclosed** rather than hidden — 04-05 guide section 6 explicitly states "NOT a sandbox"
- **Framework-gap-stub convention** (04-05 § 8 + 04-09 Task 2) is well-specified: class-level `blocked_by`, check() returns passed=False with gap ID in reason, no undefined symbols imported (Pitfall 6)
- **04-04's outcome branching redesign (W5)** — moving xfail/fail/skip into the test body rather than collection-time markers correctly handles the "yield-that-actually-fires" case, which is the whole point of making UCs flip yield→pass incrementally

## 3. Concerns

### HIGH severity

- **Naive verb→mechanic matcher accumulates fragile extensions across plans.** 04-04 Task 2 uses `info.voluntary and info.id == verb` as the matcher. 04-06, 04-07, 04-08 each admit in their SUMMARY outputs that they "may extend" the matcher (alias mapping, tag fallback, blocked_by routing, refusal-narrative synthesis). By 04-09 this matcher has grown at least 3 extensions without any single plan owning the contract. **Risk:** silent behavior drift between clusters; harness behavior becomes impossible to reason about without reading all SUMMARY files. **The matcher contract should be owned by 04-04 and extended only via explicit additions recorded in 04-04's test file**, not grown opportunistically inside seed plans.

- **Plan 04-09 Task 2 reaches into `registry._classes`** as a documented private-access fallback. The plan says "Add this accessor to MechanicRegistry now (cleaner than touching a private attr)" — good instinct, but the acceptance criteria still permit either approach. The accessor addition should be a Task 1 prerequisite of 04-09 or ideally baked into 04-02's registry rewrite so it's stable by the time any harness code reads `blocked_by`.

- **`MechanicContext` DSL surface assumed but not enforced.** Plans 06-11 freely call `ctx.neighbors(x, relation=...)`, `ctx.query_node`, `ctx.mutate`, `ctx.add_edge`, `ctx.remove_edge`, `ctx.remove_node`, `ctx.add_node`, `ctx.set`, `ctx.has_node`, `ctx.spatial.{nearest,within,segment_intersections}`, `ctx.claim_id`, and `ctx.actors`. Several of these appear as "check the actual signature" hedges in the plans (e.g., 04-06 helper: "If `ctx.neighbors` signature takes `relation=` differently — check `MechanicContext` — adapt"). **Risk:** seed plans executed in parallel may each invent slightly different adaptations; some of these methods may not exist and need to be added to `MechanicContext` as part of this phase. 04-02 builds the validator but does NOT own the DSL contract. **Recommendation:** add a preliminary task to 04-05 (or a new 04-05b) that freezes the `MechanicContext` public surface — enumerate methods, add a pytest test asserting the public API, and let seeds depend on that contract.

- **`ctx.spatial.*` fallback logic in 04-07 is hand-waved.** Plan says "If `ctx.spatial.segment_intersections` / `.nearest` / `.within` exist on MechanicContext (lazy rtree per Phase 3), use them. If not (some ARE listed as GAP-GRAPH01-03... but might be implemented in Phase 3 already — check)." This is a **research-not-yet-done** admission inside an execute plan. Plans 06, 07 should either (a) begin with a discovery task that enumerates what Phase 3 delivered, OR (b) plan 04-05b owns the DSL contract freeze.

### MEDIUM severity

- **Cluster size in 04-07 and 04-08 may exceed single-plan context budget.** 04-07 authors 5 mechanics (look, find_nearest, aoe, speak, try_door) + helper + 5 UC flips + 5 test files. 04-08 authors 5 mechanics + helpers + 6 UC flips. 04-11 authors 5 mechanics (including a stub). These are big plans. By contrast, 04-06 ships 3 mechanics and is a more comfortable size. **Suggest splitting 04-07 and 04-08 into 2 sub-plans each**, or acknowledging that these plans will consume more agent turns than 04-06.

- **"Annotate 35 manifests" in 04-04 Task 3 is scripted but not committed.** The script for annotating all 35 UCs is described in prose ("Save this as a one-off script if it helps, or do by hand — either is acceptable"). This violates the CLAUDE.md directive: "Ad-hoc bash is a missing-tool signal... promote it to a committed artifact." **Recommend:** commit the annotation as `scripts/annotate_uc_outcomes.py` so the logic is reproducible/auditable.

- **UC-O01 (trade), UC-R05 (decay), UC-V03 decision trees are deferred to execution time.** Plans 08, 10, 11 say "decide at execution time whether to flip to `pass` or leave `blocked` depending on the manifest's action shape." This is defensible — the plan honestly reports that it can't decide without reading the manifest closely — but it also means 3 of the 35 UCs have unknown final state until execution, and deviations aren't specified. **Suggest:** a 15-minute pre-task in 04-08/10/11 that reads the manifest and commits the decision before authoring the mechanic.

- **Harness extension for refusal-narrative (04-08 Task 3 Step B) crosses into harness territory from a seed plan.** "Add a hook in the harness: after a voluntary mechanic's check returns passed=False, emit ctx.mutate(actor, 'last_refusal_narrative', reasons[0])..." — this is a harness behavior change that belongs in 04-04 extension, not inside 04-08. If it fires for every failing check(), it may cause side effects in UCs that don't expect a `last_refusal_narrative` write.

- **Plan 04-11 weather_reaction stub decision is committed in plan but the logic is tied to GAP-ENG09.** Plan says "If during execution it turns out GAP-ENG09 is NOT required (e.g., a workaround exists via existing matchers), that is a deviation." This is fine, but without a concrete spec for what GAP-ENG09 IS (WorldPropertyMatcher), there's no way to verify the stub choice is correct — the planner is trusting the gap analysis. Minor: include the 1-paragraph rationale from GAP-ANALYSIS in the plan body for self-containment.

- **Test-path resolution logic in 04-02 stage 5 is complex and under-tested.** "Look at the module_path: if module_path is under src/token_world/mechanic/seeds/, the test lives at tests/test_mechanic/test_seeds/test_<id>.py; if under <universe>/mechanics/, the test lives at <universe>/tests/test_mechanics/test_<id>.py. Resolve by walking parents..." — this heuristic has edge cases (mechanics in a non-standard location, symlinked paths, case sensitivity). Add 2 dedicated tests for the resolver.

- **`_stage_smoke` requires `KnowledgeGraph(db_path=None)` but the exact in-memory constructor signature isn't verified in any plan.** If Phase 1's KG doesn't support `db_path=None`, smoke stage breaks immediately and every seed mechanic fails validation. Add a one-line verification task at the start of 04-02.

### LOW severity

- **Plan 04-12 Task 1 Step D lists `test_loader_flat.py` as a Wave 0 gate file** but 04-01 creates `test_loader.py`. Filename mismatch — verify against actual VALIDATION.md Wave 0 list or fix the plan.

- **04-06 Task 2 position_sync tests optionally include `ChainExecutionEngine` integration** but "defer to the integration harness" if the API doesn't easily support it. Involuntary chain firing is the whole point of this mechanic — skipping the chain test leaves a test-coverage gap for the most important behavior.

- **Plans 06-11 do not explicitly run `validate-mechanic` in CI on the newly-authored files before pytest** — they rely on `uv run pytest` to catch issues. The validate-mechanic CLI is the authoring loop's Nyquist check; skipping it in verification means the CLI's test-exec stage could regress without anyone noticing.

- **`dataclasses.asdict` + `json.dumps` for `ValidationReport.to_dict()` in 04-02** — if `ValidationFinding.findings` grows to include non-dataclass members (Path is not JSON-serializable by default), serialization breaks. Add a test that round-trips `to_dict() → json.dumps → json.loads`.

- **04-04's `_run_graph_assertion` function assumes kg.has_node/has_edge/query signatures** — these are Phase 1 KG methods. Plan doesn't cite them. If Phase 1 uses different method names (`has_edge` might be `has_relation`), the harness breaks silently on assertion evaluation.

- **04-09 Task 2 blocked_by routing uses `action.get('classified').get('verb')` lookup** but the manifest's classified verb for "persuade" may literally be `persuade` only if Phase 3's manifests were authored that way. Cross-check with UC-O02's actual verb.

- **Plan 04-11 contagion.py mentions `ctx._seed`** — accessing a private attribute. Either `ctx.seed` is a public attribute (document in DSL contract) or contagion should document the nondeterminism until GAP-GRAPH05 lands.

## 4. Suggestions

1. **Add plan 04-05b: "MechanicContext DSL contract freeze."** Before any seed plan runs, enumerate the methods seeds rely on, add pytest tests that assert each method exists with expected signature, and document in `docs/guides/authoring-mechanics.md`. Eliminates HIGH concern #3.

2. **Move harness verb→mechanic matcher ownership to 04-04 and freeze its contract.** Subsequent plans append test cases + a table row in `04-04-SUMMARY.md` when they need an extension, but the matcher lives in one file and has one test suite.

3. **Split 04-07 (MECH02/03/04/13/27) into two plans** — spatial queries (look/find_nearest/aoe) and interaction (speak/try_door) — to keep per-plan context budget comfortable.

4. **Commit the UC annotation script** (`scripts/annotate_uc_outcomes.py`) per CLAUDE.md's "ad-hoc bash is a missing-tool signal" rule.

5. **Tighten plan 04-12 Wave 0 gate.** The W8 check is good. Also add: `test_cli/test_validate_mechanic.py`, `test_cli/test_scaffold_mechanic.py`, `test_cli/test_prune_diagnostics.py` to the existence-check list. Confirm the `test_loader_flat.py` vs `test_loader.py` filename discrepancy.

6. **Have 04-02 Task 1 include an explicit verification that `KnowledgeGraph(db_path=None)` works.** If it doesn't, smoke stage needs a different fixture and every seed plan breaks.

7. **Move the "auto-write refusal narrative on check-fail" hook from 04-08 to 04-04** — it's a harness behavior, not a seed-plan concern, and it affects every UC.

8. **Plans 08, 10, 11 should include a "decide outcome" pre-task that reads the target UC and commits pass/blocked before mechanic authoring starts.** Eliminates execution-time decision trees for UC-O01/R05/V03.

9. **04-06 Task 2 should have a test that exercises position_sync via ChainExecutionEngine, not "maybe defer."** It's the only test that proves the involuntary wiring works.

10. **04-11 fire_spread and illumination need explicit reactive-cycle regression tests** — the plan mentions the guard but test_fire_spread.py minimum test list doesn't include it. Make "does not reignite already-burning nodes" a must-have test, not a nice-to-have.

11. **Consider adding `os.system`, `subprocess`, `socket` to FORBIDDEN_IMPORT_PREFIXES / call names list**, at least as warnings. The guide acknowledges v1 doesn't sandbox, but the AST rules catch bare `open` yet leave `os.system` free — that's an easy hardening win for near-zero cost.

12. **Plan 04-09's accessor-addition for MechanicRegistry.get_class should land in 04-02**, not be a side effect of a seed plan. It's core registry API.

## 5. Risk Assessment

**Overall: MEDIUM**

**Justification:**
- Infrastructure plans (01-05) are **LOW risk**. They are well-scoped, security-conscious, dependency-clean, and have solid test coverage. 04-01 is near-mechanical (flatten + drop register_mechanic + verify upstream fixes). 04-02's 6-stage validation pipeline is stdlib-only with no novel design. 04-03's DiagnosticsSink is thin. 04-04's harness redesign (W5/W9/W2) is mature. 04-05 is documentation + CLI.

- Seed plans (06-11) are **MEDIUM-HIGH risk** individually and as a group:
  - **DSL contract ambiguity** means some seeds may write working code that passes pytest against a stub `ctx` but fails in the real harness.
  - **Cluster scope** in 07/08 is genuinely large — each plan is arguably 2 plans' worth of work.
  - **Harness extensions** grow across plans without a single owner, creating compounding-drift risk.
  - **Framework-gap stubs (MECH09/12/21)** are pattern-clean but depend on the harness reading class attributes correctly — one wiring mistake and UC-O02/O06/V02/V04 silently pass or silently fail.
  - **UC flip counts are aggressive**: target is ~28 UCs flipped to `pass` across six seed plans. Any single mechanic bug cascades to a UC assertion failure and blocks 04-12.

- Plan 04-12 (gate) is **LOW risk** — it's a closeout with good W8 gating.

- **The biggest single risk is Plan 04-04's harness correctness** — if outcome branching / diagnostics wiring / matcher logic has a subtle bug, every subsequent plan's UC flips fail in ways that look like seed-mechanic bugs but are actually harness bugs. The W5/W9/W2 redesigns mitigate this significantly; extra care on 04-04 verification (explicit assertions that UC-S01 xfails and writes `tmp_path/diagnostics/tick_<N>/summary.json`) keeps this MEDIUM rather than HIGH.

**Recommendation:** Execute 01-05 as a block, then PAUSE and run the harness manually against 3-5 hand-picked UCs before starting the seed-authoring waves. If 04-04's harness is solid, 06-11 go smoothly; if not, discovering it early saves 6 plans' worth of false rework.
