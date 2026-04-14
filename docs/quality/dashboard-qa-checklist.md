---
Status: canonical / adopted 2026-04-15
Scope: every PR that touches `src/token_world/dashboard/`
Companion: [sim-quality-rubric.md](sim-quality-rubric.md)
---

# Dashboard QA Checklist

## Why this exists

Session 4 shipped a dashboard with a scroll-reset bug. Every poll cycle
called `outer.clear()` on the tick-stream container, which destroyed the
scroll offset on every refresh. I never caught it because I treated
`playwright_take_screenshot` as the whole validation step. A screenshot
is a still photograph of a live UI; the bug lives in the *interaction*.

The discipline is simple: **a dashboard panel is not shipped until it
has been used**. Used means scrolled, clicked, resized, waited through,
opened and re-opened. This doc is the required QA pass gate that turns
"I looked at it" into "I used it."

If the checklist feels long — good. Every item corresponds to a
real-world bug we missed or nearly missed. Cutting the list is how
regressions ship.

---

## Section 1 — Required Checks

Every dashboard PR must pass all nine before the panel is marked
"shipped." Evidence is a screenshot, a log line, or a pytest assertion;
"I looked and it seemed fine" does not count.

### 1. Initial render

- **Why:** most visible layout bugs (overflow, clipped cells, wrong
  aspect ratio) show up as soon as the page loads at a real viewport.
- **How:** launch `token-world dashboard <slug>`, navigate with
  Playwright at both `1280x800` and `1920x1080`. Capture a fullPage
  screenshot at each. Compare header, left column, right column — no
  element should be clipped or overflowing.

### 2. Scroll preservation across poll cycles

- **Why:** this is the Session 4 regression. A naïve `outer.clear()` in
  a `ui.timer` callback nukes scroll, focus, and text selection every
  refresh. The panel *looks* correct in screenshots but is unusable the
  moment the user tries to read it.
- **How:** scroll to ~50% depth inside every scrollable region (tick
  stream, graph canvas, property drawer body, causal chain results).
  Wait *at least 3× the poll interval* (poll is 2s; wait ≥6s). Assert
  the scroll offset has not changed. Run one cycle at default
  `1280x800`, one at `1920x1080`.

### 3. Focus and text-selection preservation

- **Why:** users type node ids into the causal-chain input. If focus is
  lost every 2s, the field is unusable. Same for highlighting tick
  payload text in the card expansion.
- **How:** click into every text input, wait 3× poll. Focus must
  persist. Highlight a run of text in a read-only region; wait 3×
  poll. Selection must persist.

### 4. Interactive elements

- **Why:** every click-target is a state-change vector the dashboard
  must handle without breakage. "Expand tick card," "click node in
  graph," "trace property" — each has its own DOM path that poll may
  or may not survive.
- **How:** click every button, expansion arrow, node button, and
  dropdown at least once. For each triggered state, capture a
  screenshot named after the state
  (`expanded-tick-042.png`, `drawer-cottage.png`, etc.). If anything
  fails to respond, log the console and add it to the PR review.

### 5. Drawer / modal state persistence

- **Why:** the graph-canvas drawer is the worst offender for
  poll-induced destruction, because its content comes from a `select`
  on a node id that re-evaluates on every `_rebuild`.
- **How:** open the property drawer for a specific node. Wait 3× poll.
  Drawer must stay open with identical content (same header, same
  JSON body). Repeat with a second node to confirm the state isn't
  pinned to the first id by accident.

### 6. Polling no-op

- **Why:** if `_rebuild` fires on every tick even when nothing changed,
  every other check here is at risk. The positive test is "during an
  idle window, the DOM-mutation log stays empty."
- **How:** instrument whichever `_rebuild` / `refresh()` callback
  drives the panel with a log line that fires *only when it actually
  changes the DOM*. Point the dashboard at a stable universe (no
  active runner). Leave the browser idle for 30s. Expect zero log
  lines. Non-zero means poll is rebuilding pointlessly and killing
  interaction.

### 7. Empty / missing universe graceful degradation

- **Why:** a stack trace at the first 500 breaks trust. The dashboard
  must render a friendly banner at every failure boundary.
- **How:** point the dashboard at a non-existent slug
  (`token-world dashboard does-not-exist`). CLI should exit 1 *before*
  NiceGUI starts. Point it at an empty but valid universe (0 ticks);
  every panel must render a placeholder, nothing crashes. Delete the
  universe.db mid-session; graph panel surfaces an error, other
  panels keep polling without wedging.

### 8. Rendering correctness

- **Why:** this catches escape-leakage, mis-coloured nodes, missing
  edges — the class of bugs where the DOM is "right" but the *mapping
  from graph state to DOM* is wrong. See §A3 and §A4 in
  `MORNING-HANDOFF.md`.
- **How:** inspect every label for literal `&lt;`, `&#91;`, `&amp;`
  leakage. Cross-reference node colours against
  `docs/guides/dashboard.md` (agent=blue, container=amber, etc.).
  Walk the graph: for every node property whose value is a known node
  id (`located_in`, `contains`, `held_by`, …), there MUST be a
  corresponding rendered edge, or the property must be explicitly
  excluded with a documented reason. Property drawer contents must
  exactly match `kg.query(<node>, <prop>)` for the live graph.

### 9. Automated test

- **Why:** manual QA is a guardrail, not a gate. The only QA that
  scales is executable QA. Section 2 below is the Playwright routine
  this test embodies.
- **How:** the above 1-8 are encoded as
  `tests/test_dashboard/test_qa_interactive.py`. It runs the
  Playwright routine against a fixture universe and a synthetic poll
  cycle, asserts each check. The test is a required CI gate — a PR
  that regresses any of 1-8 fails CI, not just human review.

---

## Section 2 — Playwright MCP Routine

This is the concrete recipe for Section 1's checks. It uses the
`mcp__playwright__*` tools available in-session. Run it as a fresh
sequence each time — no "still have the browser open from earlier"
assumptions.

### Setup

- Launch the dashboard in a background bash:
  `uv run token-world dashboard <slug> --port 8080 --no-show`
- Wait 2s for the server to bind (NiceGUI startup is fast but not
  instant).

### Routine

```
# 1. Open + viewport sweep
mcp__playwright__browser_navigate(url="http://localhost:8080")
mcp__playwright__browser_resize(width=1280, height=800)
mcp__playwright__browser_take_screenshot(filename="initial-1280.png", fullPage=true)
mcp__playwright__browser_resize(width=1920, height=1080)
mcp__playwright__browser_take_screenshot(filename="initial-1920.png", fullPage=true)

# 2. Snapshot the DOM for element refs
mcp__playwright__browser_snapshot()

# 3. Scroll + wait + re-snapshot (checks 2, 6)
#    For each scrollable region, scroll to mid-depth, wait 3x poll,
#    snapshot again, assert scroll offset unchanged.
mcp__playwright__browser_evaluate(function="() => { document.querySelector('#tick-stream').scrollTop = 400; }")
# wait >= 6s
mcp__playwright__browser_wait_for(time=7)
mcp__playwright__browser_evaluate(function="() => document.querySelector('#tick-stream').scrollTop")
# ^ expect 400, not 0

# 4. Interactive elements (check 4)
#    For each button / expansion / node click-target:
mcp__playwright__browser_click(element="tick card 042 expander", ref="<ref from snapshot>")
mcp__playwright__browser_wait_for(text="<expected content after expansion>")
mcp__playwright__browser_take_screenshot(filename="expanded-042.png")

# 5. Drawer persistence (check 5)
mcp__playwright__browser_click(element="graph node: cottage", ref="<ref>")
mcp__playwright__browser_wait_for(time=7)
mcp__playwright__browser_snapshot()
# ^ drawer should still show cottage properties

# 6. Focus preservation (check 3)
mcp__playwright__browser_click(element="causal-chain node input", ref="<ref>")
mcp__playwright__browser_type(element="...", ref="...", text="mira")
mcp__playwright__browser_wait_for(time=7)
mcp__playwright__browser_evaluate(function="() => document.activeElement.id")
# ^ expect the input's id, not body

# 7. Final full-page capture
mcp__playwright__browser_take_screenshot(filename="final.png", fullPage=true)

# 8. Close
mcp__playwright__browser_close()
```

### Notes

- **`browser_snapshot` before `browser_click`**: click needs an element
  `ref` which you extract from the accessibility-tree snapshot. Don't
  try to click by CSS selector alone.
- **`browser_resize` twice**: responsiveness bugs only show at exactly
  one of the two viewports. Both must be screenshotted.
- **`browser_wait_for(time=N)` vs `browser_wait_for(text=...)`**: use
  `text` when you're waiting for a specific UI change (content to
  appear after a click). Use `time` for "let the poll cycle through
  at least twice." 7s covers a 2s poll comfortably.
- **`browser_evaluate`**: the only way to read scrollTop, focus target,
  CSS state directly. Keep the JS one-liner.
- **Screenshots are evidence, not validation**: a screenshot proves
  what the DOM looked like at that instant; it cannot prove that
  scroll was preserved across a refresh. That's what
  `browser_evaluate` + an assertion is for.

---

## Section 3 — End-of-Build User Pass

After the Playwright routine passes, there's still one gap: the
routine only checks what it was told to check. Novel bugs — the
"would a real person expect this?" class — slip through any finite
checklist.

The antidote is a **5-minute user-mode cooldown** at the end of every
UI build session.

### The switch

- **Builder mode** (what you were in): "does the code I wrote do what
  I thought?" The fixation is on your own change. Shorthand, clipped
  labels, and truncations read as "rendered, fine."
- **User mode** (what you switch to): "does the output make sense to
  someone who has never seen this code?" The fixation is on the
  artefact. Every shorthand is a question: "would a real person
  expect that here?"

### The routine

1. Close every editor tab.
2. Launch the dashboard fresh (`token-world dashboard <slug>`).
3. Open the browser manually — do NOT use Playwright, do NOT automate.
4. Set a 5-minute timer.
5. Click around. Scroll. Open drawers. Type into the causal-chain
   input. Resize the window. Read every truncated label and ask: is
   this enough for a new user?
6. Write down every surprise in a scratch note. Even "huh, that's
   weird" counts.
7. At timer end: each scratch-note item becomes either a follow-up
   ticket or a fix before the PR merges. None are dismissed silently.

### Why 5 minutes

- Short enough that it's cheap.
- Long enough that you stop skimming and actually *use* the thing.
- Forces the switch from "is this correct?" to "is this good?"

### Enforcement

Hard to automate. Instead: every dashboard PR description must include
a `## User Pass` section that lists at least three observations from
the cooldown. "Nothing surprising" is a valid entry only if the
reviewer can independently verify; by default, expect at least one
item of friction per pass.

In autonomous overnight sessions, the orchestrator spawns a dedicated
**QA subagent** after the build subagent reports done. The QA subagent
runs the Playwright routine (Section 2) and then writes a
user-pass report. The orchestrator does not mark the build shipped
until the QA subagent's report lands in `docs/quality/runs/`.

---

## Section 4 — When to Gate

### Mandatory pass

- **PR touches `src/token_world/dashboard/`** (any file):
  - Section 1 checks 1-8 must pass (evidence in PR description).
  - Section 2 Playwright routine must run against the branch build.
  - Section 1 check 9 (automated test) must be green in CI.
  - Section 3 user pass: at least three observations in PR
    description.
- **PR adds a new panel**: treat the panel as a separate required
  sweep of all nine checks. The existing panels' test coverage does
  not extend to the new panel.
- **PR changes the poll interval or `_rebuild` cadence**: Section 1
  check 6 (polling no-op) is load-bearing; re-run it fresh.

### Optional (but advised)

- **PR touches shared NiceGUI utilities** but no panel directly: run
  Section 2 against an untouched panel as a smoke check. Polling
  helpers frequently regress everyone at once.
- **Monthly rhythm**: run the full Playwright routine against
  `master` once a month independent of any PR, and file the results
  under `docs/quality/runs/YYYY-MM-DD/`. Catches drift that no
  individual PR triggered.

### Non-gates (explicitly)

- **Docs-only PRs** touching `docs/guides/dashboard.md` alone — no
  panel QA needed.
- **Dashboard CLI flag additions** (e.g. `--port`, `--no-dark`) that
  don't touch panel code — smoke test the flag; skip the full sweep.

### Escalation

If a check fails and the fix is non-trivial (≥ 1 tick of engineering
work), the PR must either:
- carry the fix, or
- land behind a feature flag that disables the regressed surface
  until the fix is in, or
- be reverted.

"We'll fix it next sprint" is not an allowed option for checks 1-8.
Shipping a poll-regression dashboard into overnight runs means every
subsequent debugging session starts from bad telemetry.

---

## Related

- [sim-quality-rubric.md](sim-quality-rubric.md) — the sibling rubric
  for "is the simulation healthy?" Simulation-quality gates apply to
  overnight runs; dashboard QA gates apply to the panel PRs that
  surface those runs. Both are required; neither is sufficient.
- `MORNING-HANDOFF.md` §K1, §K3, §K4 — the process-gap discussion
  this checklist codifies.
- `docs/guides/dashboard.md` — user-facing dashboard guide. When a
  check here fails, the fix likely updates both files.
