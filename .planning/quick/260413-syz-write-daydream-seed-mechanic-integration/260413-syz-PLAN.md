---
phase: 260413-syz-write-daydream-seed-mechanic-integration
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/token_world/mechanic/seeds/daydream.py
  - tests/test_engine/test_daydream_integration.py
  - .planning/phases/07-attention-and-consciousness/07-VERIFICATION.md
autonomous: true
requirements:
  - SIM-10
must_haves:
  truths:
    - "daydream seed file exists and mirrors sleep.py structure (bounded turns_total=4, noise threshold at 0.4, health threshold at 0.2, attention_state suppresses ambient_sound + peripheral_vision, boosts noise_level)"
    - "integration tests all pass (at least 5 scenarios: full 4-tick completion, noise threshold fires at 0.4 not 0.3, attention_state suppression, D-11 cancellation, classifier not called on continuation)"
    - "07-VERIFICATION.md status flipped from human_needed to passed with 6/6 must_haves_verified; narrative updated to describe 4-seed composability proof (daydream + drunk + sleep + autopilot_travel)"
    - "existing Phase 7 tests continue to pass (no regression in 771-test baseline)"
  artifacts:
    - path: "src/token_world/mechanic/seeds/daydream.py"
      provides: "DaydreamMechanic — bounded 4-tick cognitive LRA mirroring sleep.py's shape with daydream-specific values"
      min_lines: 60
    - path: "tests/test_engine/test_daydream_integration.py"
      provides: "Deterministic end-to-end tests: completion cycle, threshold semantics, attention filtering, cancellation, classifier-skip"
      min_lines: 200
    - path: ".planning/phases/07-attention-and-consciousness/07-VERIFICATION.md"
      provides: "Verification frontmatter + body narrative updated to reflect daydream-as-fourth-seed (additive, not replacement)"
      contains: "status: passed"
  key_links:
    - from: "src/token_world/mechanic/seeds/daydream.py"
      to: "ctx.begin_long_action"
      via: "apply() returns ctx.set(...) + ctx.begin_long_action(...) per the sleep.py pattern"
      pattern: "ctx\\.begin_long_action"
    - from: "tests/test_engine/test_daydream_integration.py"
      to: "src/token_world/mechanic/seeds/daydream.py"
      via: "shutil.copy from _SEEDS_DIR into tmp_universe/mechanics/"
      pattern: "shutil\\.copy.*daydream\\.py"
    - from: "DaydreamMechanic"
      to: "VerbMatcher(verb='daydream')"
      via: "watches() returns [VerbMatcher(verb='daydream')] — same mechanism as sleep/drunk"
      pattern: "VerbMatcher\\(verb=.daydream."
---

<objective>
Add a `daydream` seed mechanic as the FOURTH composability demonstrator (alongside sleep, autopilot_travel, drunk), closing Phase 7 VERIFICATION's last human_needed item by converting the D-18 "drunk substituted for daydream" situation from a substitution into a pure addition.

**Purpose:** ROADMAP SC2 names "sleep, daydreaming, autopilot travel" verbatim. Phase 7 shipped drunk instead of daydream (per auto-mode D-18) to prove the turns_total=None composability axis. Adding daydream NOW as a fourth seed (keeping drunk) satisfies SC2 literally AND strengthens the composability proof — one pattern now demonstrably handles 4 distinct states: physiological (sleep), cognitive (daydream), chemical (drunk), movement (autopilot_travel).

**Output:**
  - `src/token_world/mechanic/seeds/daydream.py` — new 60-ish-line seed mechanic mirroring sleep.py's template
  - `tests/test_engine/test_daydream_integration.py` — new integration test file mirroring test_sleep_integration.py structure
  - `.planning/phases/07-attention-and-consciousness/07-VERIFICATION.md` — verification report updated to status=passed with 4-seed narrative

**Scope guardrails (do NOT violate):**
  - DO NOT modify sleep.py, drunk.py, autopilot_travel.py, sober_up.py, or autopilot_advance.py
  - DO NOT modify any engine code — seed mechanics are pure data; they ride the existing LongRunningHook unchanged
  - DO NOT register daydream in any global registry — seed mechanics are discovered from the universe's `mechanics/` folder at test time via `shutil.copy` (the precedent from test_sleep_integration.py)
  - DO NOT rewrite the Truth table in 07-VERIFICATION.md beyond the minimal fields specified in must_haves; preserve all existing VERIFIED rows as-is
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@src/token_world/mechanic/seeds/sleep.py
@src/token_world/mechanic/seeds/drunk.py
@tests/test_engine/test_sleep_integration.py
@tests/test_engine/test_drunk_integration.py
@.planning/phases/07-attention-and-consciousness/07-VERIFICATION.md
@.planning/phases/07-attention-and-consciousness/07-CONTEXT.md

<interfaces>
<!-- All interfaces already exist in the codebase — daydream.py only consumes them. -->
<!-- No new contracts introduced; no contracts modified. -->

From src/token_world/mechanic/protocol.py:
```python
class Mechanic:
    id: str
    description: str
    voluntary: bool
    tags: list[str]
    def watches(self) -> list[Matcher]: ...
    def check(self, ctx: MechanicContext) -> CheckResult: ...
    def apply(self, ctx: MechanicContext) -> list[Mutation]: ...

@dataclass(frozen=True)
class CheckResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
```

From src/token_world/mechanic/context.py (the key API daydream uses):
```python
class MechanicContext:
    actor: str
    target: str
    def query_node(self, node_id: str) -> dict: ...
    def has_node(self, node_id: str) -> bool: ...
    def set(self, node_id: str, prop: str, value: Any) -> Mutation: ...
    def refuse(self, error_type: str, params: dict) -> CheckResult: ...
    def begin_long_action(
        self,
        action_text: str,
        turns_total: int | None,
        thresholds: list[dict],
        attention_state: dict,
        clear_on_end: dict,
    ) -> Mutation: ...
```

From src/token_world/mechanic/matchers.py:
```python
class VerbMatcher:
    def __init__(self, verb: str) -> None: ...
```

From src/token_world/graph/__init__.py:
```python
# Mutation dataclass — do not instantiate directly; use ctx.set / ctx.begin_long_action
class Mutation: ...
```
</interfaces>

<locked_design>
<!-- Per user constraints — do NOT re-open these. Copy exactly. -->

Seed file: `src/token_world/mechanic/seeds/daydream.py`
id: `"daydream"`
description: "Agent drifts into daydreaming for 4 ticks; snaps out on loud noise or health crisis"
voluntary: True
tags: `["cognitive", "long_running"]`
watches: `[VerbMatcher(verb="daydream")]`
turns_total: 4 (bounded — shorter than sleep's 8; distinguishes from drunk's None)

Thresholds (in the order sleep.py emits them — noise first if resolvable, then health):
  1. `{"property": f"{location_id}.noise_level", "op": ">", "value": 0.4}` — ONLY if actor has a string `location` property AND that node exists in the graph (same graceful-degradation policy as sleep.py)
  2. `{"property": f"{ctx.actor}.health", "op": "<", "value": 0.2}` — ALWAYS present

attention_state:
  - suppress: `["ambient_sound", "peripheral_vision"]`
  - boost: `["noise_level"]`

Companion property: `is_daydreaming = True` set on start via `ctx.set(ctx.actor, "is_daydreaming", True)`
clear_on_end: `{"is_daydreaming": False}`

action_text passed to begin_long_action: `"daydreaming"` (matches the sleep.py pattern of using the gerund)

check() logic (identical shape to sleep.py):
  - If actor does not exist → CheckResult(passed=False, reasons=["actor does not exist"])
  - If actor already has current_long_action dict → ctx.refuse("mechanic_check_failed", {"reason": "actor is already in a long-running action"})
  - Otherwise → CheckResult(passed=True)

apply() logic (identical shape to sleep.py):
  - Build thresholds list starting with health
  - Insert noise threshold at index 0 if location resolvable
  - Return `[ctx.set(ctx.actor, "is_daydreaming", True), ctx.begin_long_action(...)]`
</locked_design>

<test_scenarios>
<!-- MINIMUM 5 scenarios, mirroring test_sleep_integration.py structure. -->
<!-- Reuse the MockAnthropicClient + tmp_universe + kg fixture approach verbatim. -->
<!-- File: tests/test_engine/test_daydream_integration.py -->

1. **test_daydream_happy_path_completes_after_4_ticks** — full cycle:
   - Alice in quiet study (noise_level=0.2); issue `"daydream"` action
   - Assert LRA set with turns_total=4, turns_elapsed=0, is_daydreaming=True, both thresholds present (noise on study and health on alice)
   - Run 3 continuation ticks with `run_tick(None, actor="alice")` and empty response list (no classifier, no observer — static "Time passes" template)
   - Assert turns_elapsed advances to 1, 2, 3 and LRA still present
   - Run 4th continuation with observer response → LRA cleared (completion path)

2. **test_daydream_threshold_fires_at_noise_above_0_4_not_at_0_3** — threshold semantics:
   - Alice in quiet study (noise_level=0.3); issue `"daydream"`
   - Run one continuation tick with empty responses — LRA must still be active (0.3 > 0.4 is False)
   - kg.set study noise_level = 0.4 → one more continuation tick — LRA must STILL be active (0.4 > 0.4 is False — strictly greater, matches drunk.py semantics)
   - kg.set study noise_level = 0.5 → one continuation tick with wake observer response — LRA cleared

3. **test_daydream_attention_state_suppresses_ambient_sound_during_continuation** — attention filter:
   - Alice in study with `ambient_sound="birds chirping"` and `peripheral_vision="moving shadows"` properties on the study
   - Start daydream; run one continuation tick
   - Assert result.projected_state's study properties do NOT include `ambient_sound` or `peripheral_vision` (suppressed per attention_state)

4. **test_daydream_cancelled_by_new_agent_action (D-11)** — implicit cancellation:
   - Alice starts daydreaming; run 2 continuation ticks (turns_elapsed=2)
   - Issue a new action string (e.g., `"look around"`) via `run_tick("look around", actor="alice")` with _CLASSIFY_NO_MATCH response
   - Assert LRA cleared (`current_long_action is None`); result.kind in ("refused", "ok", "yielded")

5. **test_daydream_continuation_does_not_call_classifier** — run_tick(None) path:
   - Alice starts daydreaming with classifier+observer responses consumed
   - 3 continuation ticks with `MockAnthropicClient([])` — any classifier call would raise RuntimeError when the mock runs out of responses
   - After each, assert `client.messages.calls == []` (no Haiku call happened)

**Copy-from-test_sleep_integration.py verbatim:**
  - `_SEEDS_DIR = Path(seeds_pkg.__file__).parent`
  - `_install_daydream_mechanic(tmp_universe)` helper using `shutil.copy`
  - `kg` fixture with SQLite-backed temp DB (`daydream_int_test.db`)
  - `_make_engine(tmp_universe, kg, responses)` helper
  - `_setup_alice_in_study(kg)` helper setting up alice + study with location property AND `type=location` edge (both required — see STATE.md line 145)
  - Classifier constants:
    - `_CLASSIFY_DAYDREAM` with verb=daydream, actor=alice, target=alice
    - `_CLASSIFY_NO_MATCH` with kind=no_viable_action
  - Static wake narrative constants: `_WAKE_NOISE` and `_SNAP_OUT` for use in relevant tests
</test_scenarios>

<verification_update>
<!-- Exact frontmatter + body changes to .planning/phases/07-attention-and-consciousness/07-VERIFICATION.md -->

Frontmatter changes:
  - `status: human_needed` → `status: passed`
  - `score: 5/6 must-haves verified` → `score: 6/6 must-haves verified`
  - `must_haves_verified: 5` → `must_haves_verified: 6`
  - REMOVE the entire `human_verification:` block (lines 16-19)
  - ADD a new `overrides_applied: 1` counter (replacing the current `overrides_applied: 0`)
  - ADD a new `overrides:` block:
    ```yaml
    overrides:
      - must_have: "Sleep, daydreaming, and autopilot travel all use the same interruption threshold infrastructure"
        reason: "Originally substituted with drunk per CONTEXT D-18 (auto-mode). Resolved 2026-04-13 by adding daydream as a FOURTH seed mechanic (sleep + autopilot_travel + drunk + daydream), converting the D-18 substitution into an addition. SC2 now satisfied literally AND composability is proven more strongly across 4 distinct state categories (physiological / cognitive / chemical / movement)."
        accepted_by: "developer"
        accepted_at: "2026-04-13T21:30:00Z"
    ```

Body narrative changes:
  - Truth #5 row: change status from `PARTIAL` to `VERIFIED`; update evidence column to: `Sleep, autopilot_travel, drunk, AND daydream all use ctx.begin_long_action via the same LongRunningHook infrastructure. Daydream (src/token_world/mechanic/seeds/daydream.py) added 2026-04-13 as a 4th seed — SC2 literal wording satisfied; composability demonstrated across 4 state categories.`
  - **Score** line (after the table): `5/6 truths verified (1 pending human confirmation)` → `6/6 truths verified`
  - Required Artifacts table: ADD a new row for daydream.py:
    ```
    | `src/token_world/mechanic/seeds/daydream.py` | Bounded (turns_total=4), noise (>0.4) and health thresholds, attention_state, clear_on_end | VERIFIED | Added 2026-04-13; mirrors sleep.py; differentiates via turns_total=4, noise_level>0.4, suppress=[ambient_sound, peripheral_vision] |
    ```
  - Required Artifacts table: ADD a new row for test_daydream_integration.py:
    ```
    | `tests/test_engine/test_daydream_integration.py` | Daydream integration test (5+ scenarios) | VERIFIED | Added 2026-04-13; mirrors test_sleep_integration.py structure |
    ```
  - Composition-Pattern Check section #6 ("Variation lives in data, not code"): update bullet list to include daydream:
    ```
    - `sleep`: turns_total=8, suppress=[visual_detail, smell], noise>0.7
    - `daydream`: turns_total=4, suppress=[ambient_sound, peripheral_vision], noise>0.4
    - `autopilot_travel`: turns_total=path_len, thresholds per-room
    - `drunk`: turns_total=None (indefinite), suppress=[fine_detail, social_nuance]
    ```
  - Requirements Coverage section, "Note on daydreaming" paragraph: REPLACE entirely with:
    ```
    **Note on daydreaming (resolved 2026-04-13):** REQUIREMENTS.md SIM-10 lists "sleep, daydreaming, drunkenness, autopilot" as examples. CONTEXT D-18 originally chose drunk over daydreaming as the third seed demonstrator. On 2026-04-13, daydream was added as a FOURTH seed mechanic, converting the substitution into an addition. SC2 is now satisfied both literally (daydream exists) and in spirit (composability across 4 state categories). See `overrides_applied` in frontmatter.
    ```
  - REMOVE the entire `### Human Verification Required` section (lines 148-163)
  - Update Gaps Summary: `The single pending item is a roadmap naming deviation (daydreaming → drunk) requiring human acceptance, not a technical failure.` → `All items closed. Daydream added 2026-04-13 as a 4th seed mechanic to literally satisfy SC2. 771+ tests pass (including new daydream integration tests).`
</verification_update>

</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Write daydream seed mechanic</name>
  <files>src/token_world/mechanic/seeds/daydream.py</files>
  <behavior>
    DaydreamMechanic (mirrors SleepMechanic structure exactly; only values differ):
    - id="daydream", description, voluntary=True, tags=["cognitive", "long_running"]
    - watches() returns [VerbMatcher(verb="daydream")]
    - check(): actor existence + no-existing-LRA; refuses if already in LRA
    - apply():
      - Builds thresholds list starting with [health<0.2]
      - Inserts noise>0.4 threshold at index 0 iff actor.location is a string and that node exists
      - Returns [ctx.set(actor, "is_daydreaming", True), ctx.begin_long_action(
          action_text="daydreaming", turns_total=4, thresholds=..., attention_state={suppress:["ambient_sound","peripheral_vision"], boost:["noise_level"]}, clear_on_end={"is_daydreaming": False})]
    No imports beyond those sleep.py already uses (Mutation, VerbMatcher, CheckResult, Mechanic, TYPE_CHECKING imports for MechanicContext + Matcher).
  </behavior>
  <action>
    1. Open src/token_world/mechanic/seeds/sleep.py as the template.
    2. Create src/token_world/mechanic/seeds/daydream.py by adapting sleep.py structure:
       - Replace class name: SleepMechanic → DaydreamMechanic
       - Replace id: "sleep" → "daydream"
       - Replace description: update to "Agent drifts into daydreaming for 4 ticks; snaps out on loud noise or health crisis"
       - Replace tags: ["rest", "long_running"] → ["cognitive", "long_running"]
       - Replace VerbMatcher verb: "sleep" → "daydream"
       - In apply() thresholds build:
         * Keep health threshold as-is (alice.health < 0.2)
         * Change noise threshold value: 0.7 → 0.4 (same > operator, same location resolution path)
       - In begin_long_action call:
         * action_text: "sleeping" → "daydreaming"
         * turns_total: 8 → 4
         * attention_state suppress: ["visual_detail", "smell"] → ["ambient_sound", "peripheral_vision"]
         * attention_state boost: keep ["noise_level"]
         * clear_on_end: {"is_sleeping": False} → {"is_daydreaming": False}
       - In the ctx.set call before begin_long_action: "is_sleeping" → "is_daydreaming"
       - Update module docstring to describe daydream (bounded 4-tick cognitive state) with same fallback-policy note (location fallback identical to sleep's Q8 policy)
    3. Run `uv run ruff check src/token_world/mechanic/seeds/daydream.py && uv run ruff format --check src/token_world/mechanic/seeds/daydream.py && uv run mypy src/token_world/mechanic/seeds/daydream.py` — fix anything non-clean.
    4. Run `uv run pytest tests/test_mechanic/test_seeds/ -x -q` — new file must not break the existing seed discovery (pytest collection); if a smoke-import test exists and fails, add whatever import fix is needed (likely nothing).
  </action>
  <verify>
    <automated>uv run ruff check src/token_world/mechanic/seeds/daydream.py && uv run ruff format --check src/token_world/mechanic/seeds/daydream.py && uv run mypy src/token_world/mechanic/seeds/daydream.py && uv run python -c "from token_world.mechanic.seeds.daydream import DaydreamMechanic; m=DaydreamMechanic(); assert m.id=='daydream'; assert m.tags==['cognitive','long_running']; assert m.voluntary is True; w=m.watches(); assert len(w)==1; print('daydream mechanic loads OK')"</automated>
  </verify>
  <done>
    daydream.py exists, imports cleanly, instantiates, has id="daydream", tags=["cognitive","long_running"], voluntary=True, exactly one VerbMatcher for "daydream". Ruff clean, format clean, mypy clean. Existing seed tests still pass.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Write daydream integration tests</name>
  <files>tests/test_engine/test_daydream_integration.py</files>
  <behavior>
    Five deterministic end-to-end integration tests mirroring test_sleep_integration.py:
    1. test_daydream_happy_path_completes_after_4_ticks — LRA starts (turns_total=4), 3 continuation ticks (turns_elapsed → 1,2,3), 4th completes naturally, LRA cleared
    2. test_daydream_threshold_fires_at_noise_above_0_4_not_at_0_3 — noise=0.3 no fire, noise=0.4 no fire (strictly >), noise=0.5 fires
    3. test_daydream_attention_state_suppresses_ambient_sound_during_continuation — ambient_sound and peripheral_vision both absent from projected_state
    4. test_daydream_cancelled_by_new_agent_action — D-11 implicit cancellation clears LRA before pipeline
    5. test_daydream_continuation_does_not_call_classifier — run_tick(None) makes zero classifier calls (MockAnthropicClient([]) proves this)
    All tests deterministic using MockAnthropicClient; no @pytest.mark.integration marker needed (these are unit-speed).
  </behavior>
  <action>
    1. Open tests/test_engine/test_sleep_integration.py as the template.
    2. Create tests/test_engine/test_daydream_integration.py by adapting test_sleep_integration.py:
       - Replace all "sleep" identifiers with "daydream":
         * `_install_sleep_mechanic` → `_install_daydream_mechanic` (copies daydream.py instead)
         * `_setup_alice_in_bedroom` → `_setup_alice_in_study` (noise_level=0.2 instead of 0.3; use "study" as the room node_id)
         * `_CLASSIFY_SLEEP` → `_CLASSIFY_DAYDREAM` with verb="daydream", actor="alice", target="alice"
         * Rename observation constants: `_WAKE_NOISE` → `_SNAP_OUT_NOISE` ("You snap out of your daydream as a loud noise pierces the room."); `_WAKE_COMPLETED` → `_DAYDREAM_END` ("Your thoughts drift back to the present; you've been daydreaming.")
         * `kg` fixture db_path: "sleep_int_test.db" → "daydream_int_test.db"
       - Adapt Test 1 (happy path): change turns_total assertion from 8 → 4; change threshold assertion to `{"property": "study.noise_level", "op": ">", "value": 0.4}` and `{"property": "alice.health", "op": "<", "value": 0.2}`; check is_daydreaming=True; run 3 continuations then 4th for completion (mirroring sleep's 7+1=8 → daydream's 3+1=4).
       - Drop `test_sleep_continuation_tick_summary_has_long_running_action_field` (D-17 already covered by sleep + drunk; not needed for daydream). Drop `test_sleep_completes_after_turns_total_ticks` merged into happy path.
       - Adapt the equivalents for the FIVE required scenarios. Specifically for Test 2 (threshold semantics — NEW test not in sleep integration, but modelled on drunk's test_drunk_threshold_value_is_strictly_greater_than):
         * Setup alice_in_study with noise_level=0.3
         * Start daydream; kg.query verifies LRA active
         * Continuation tick with empty responses — assert LRA still active (0.3>0.4 False)
         * kg.set study noise_level=0.4; another continuation — LRA still active (0.4>0.4 False)
         * kg.set study noise_level=0.5; continuation with _SNAP_OUT_NOISE observer — LRA is None
       - Adapt Test 3 (attention_state): add `ambient_sound="birds chirping"` and `peripheral_vision="moving shadows"` on study; continuation tick; assert both properties absent from `result.projected_state["study"]["properties"]`
       - Adapt Test 4 (D-11 cancellation): copy test_sleep_cancelled_by_new_agent_action directly with sleep→daydream renames
       - Adapt Test 5 (no classifier on continuation): copy test_sleep_continuation_does_not_call_classifier directly with renames
    3. Ensure `_setup_alice_in_study` sets BOTH `alice.location = "study"` property AND `alice --[type=location]--> study` edge (STATE.md line 145 — both required for VisibilityProjector to include the room in projections).
    4. Run ruff/format: `uv run ruff check tests/test_engine/test_daydream_integration.py && uv run ruff format --check tests/test_engine/test_daydream_integration.py`.
    5. Run the new tests: `uv run pytest tests/test_engine/test_daydream_integration.py -x -v`. All 5 must pass.
    6. Run the full engine test suite to check for regression: `uv run pytest tests/test_engine/ tests/test_mechanic/test_seeds/ -x -q`. Pre-existing 771 must still pass; new file adds 5 → 776+ expected.
  </action>
  <verify>
    <automated>uv run ruff check tests/test_engine/test_daydream_integration.py && uv run ruff format --check tests/test_engine/test_daydream_integration.py && uv run pytest tests/test_engine/test_daydream_integration.py -x -v && uv run pytest tests/test_engine/ tests/test_mechanic/test_seeds/ -x -q</automated>
  </verify>
  <done>
    test_daydream_integration.py has at least 5 passing tests covering: full completion cycle, strict-> threshold semantics at 0.4, attention_state suppression of ambient_sound + peripheral_vision, D-11 cancellation, classifier-not-called-on-continuation. All existing Phase 7 tests still pass (no regression).
  </done>
</task>

<task type="auto">
  <name>Task 3: Flip 07-VERIFICATION.md to passed</name>
  <files>.planning/phases/07-attention-and-consciousness/07-VERIFICATION.md</files>
  <action>
    Apply the exact frontmatter + body edits specified in the `<verification_update>` block of this plan's context section. Use Edit (not Write) — preserve all other existing content byte-for-byte. Specifically:

    Frontmatter:
    1. Edit `status: human_needed` → `status: passed`
    2. Edit `score: 5/6 must-haves verified` → `score: 6/6 must-haves verified`
    3. Edit `overrides_applied: 0` → `overrides_applied: 1`
    4. Edit `must_haves_verified: 5` → `must_haves_verified: 6`
    5. Remove the `human_verification:` block (the entire 4-line block starting with `human_verification:` and its single nested item).
    6. Immediately after `must_haves_total: 6`, add the `overrides:` block with the single entry documented in the verification_update section above. Preserve YAML indentation (2-space, as existing lists in the frontmatter use).

    Body:
    7. In the "Observable Truths" table, find row "| 5 |" — change cell "PARTIAL" → "VERIFIED" and replace the evidence cell per the verification_update instructions (reference daydream.py; describe the 4-seed composability).
    8. Change the "**Score:** 5/6 truths verified (1 pending human confirmation)" line to "**Score:** 6/6 truths verified".
    9. In the "Required Artifacts" table, insert two new rows immediately after the `tests/test_engine/test_drunk_integration.py` row — one for `src/token_world/mechanic/seeds/daydream.py`, one for `tests/test_engine/test_daydream_integration.py` — with VERIFIED status and evidence as specified in verification_update.
    10. In "Composition-Pattern Check" section, point #6 ("Variation lives in data, not code"), add a `daydream` bullet between sleep and autopilot_travel (turns_total=4, suppress=[ambient_sound, peripheral_vision], noise>0.4).
    11. In "Requirements Coverage" section, REPLACE the entire "Note on daydreaming:" paragraph with the resolved-2026-04-13 version specified in verification_update.
    12. REMOVE the entire "### Human Verification Required" section, including its body subsection "#### 1. ROADMAP SC2 — "daydreaming" substituted with "drunk"" and its supplementary YAML block.
    13. In "Gaps Summary", replace the single-pending-item sentence with the all-items-closed version specified in verification_update.

    Do NOT change timestamps in the file body (the 2026-04-13T20:08:32Z verification timestamp stays — this is an update not a re-verification).
  </action>
  <verify>
    <automated>grep -q "^status: passed" .planning/phases/07-attention-and-consciousness/07-VERIFICATION.md && grep -q "^must_haves_verified: 6" .planning/phases/07-attention-and-consciousness/07-VERIFICATION.md && grep -q "^overrides_applied: 1" .planning/phases/07-attention-and-consciousness/07-VERIFICATION.md && ! grep -q "^human_verification:" .planning/phases/07-attention-and-consciousness/07-VERIFICATION.md && ! grep -q "### Human Verification Required" .planning/phases/07-attention-and-consciousness/07-VERIFICATION.md && grep -q "daydream\.py" .planning/phases/07-attention-and-consciousness/07-VERIFICATION.md && grep -q "6/6 truths verified" .planning/phases/07-attention-and-consciousness/07-VERIFICATION.md</automated>
  </verify>
  <done>
    07-VERIFICATION.md has status=passed, score=6/6, overrides_applied=1, overrides block present, no human_verification section, Truth #5 is VERIFIED, daydream.py listed as a VERIFIED artifact, composition-pattern check mentions daydream. All existing VERIFIED evidence for other truths preserved unchanged.
  </done>
</task>

</tasks>

<verification>
After all three tasks complete:
1. `uv run pytest tests/test_engine/ tests/test_mechanic/test_seeds/ -x -q` — all pre-existing 771 tests + at least 5 new daydream tests pass (776+ total)
2. `uv run ruff check src/ tests/` — clean
3. `uv run ruff format --check src/ tests/` — clean
4. `uv run mypy src/token_world/mechanic/seeds/daydream.py` — clean
5. grep confirms 07-VERIFICATION.md has status=passed, 6/6 verified, no human_verification block, daydream.py in artifacts table
</verification>

<success_criteria>
SC1: `src/token_world/mechanic/seeds/daydream.py` exists, mirrors sleep.py shape, differs only in the locked-design values (turns_total=4, noise>0.4, suppress=[ambient_sound, peripheral_vision], is_daydreaming).

SC2: `tests/test_engine/test_daydream_integration.py` exists with at least 5 passing deterministic tests covering the mandated scenarios (4-tick completion, strict-> threshold at 0.4, attention suppression, D-11 cancellation, no classifier on continuation).

SC3: `.planning/phases/07-attention-and-consciousness/07-VERIFICATION.md` frontmatter flipped to `status: passed`, `must_haves_verified: 6`, `overrides_applied: 1` with the override block documenting the substitution→addition conversion; body Truth #5 VERIFIED; human_verification section removed.

SC4: No regression — the pre-existing 771 Phase 7 tests continue to pass.

SC5: ROADMAP Phase 7 SC2 ("sleep, daydreaming, autopilot travel all use the same interruption threshold infrastructure") satisfied literally. Composability proven across 4 state categories.
</success_criteria>

<output>
After completion, create `.planning/quick/260413-syz-write-daydream-seed-mechanic-integration/260413-syz-SUMMARY.md` summarising:
- Files created (daydream.py, test_daydream_integration.py)
- Files modified (07-VERIFICATION.md)
- Test count delta (771 → 776+)
- The substitution→addition framing (drunk kept as 3rd seed demonstrating turns_total=None; daydream added as 4th seed demonstrating the bounded cognitive case)
- Confirmation that SC2 is now satisfied literally
</output>
