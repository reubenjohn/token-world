# Phase 17: Operator & Dev Ergonomics — Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous smart discuss)

<domain>
## Phase Boundary

8 requirements → 5 success criteria. Every operator investigation the author reached for during sessions 4-6 becomes a one-liner on the CLI or a sticky dashboard surface. CLI is canonical data producer; dashboard consumes JSON.

SC deliverables:
- SC-1 (REQ-V12-CLI-03): `token-world tick <slug> <id> --stage classification|matcher|observer [--raw]`
- SC-2 (REQ-V12-CLI-04 + DASHBOARD-09): `token-world mechanics --history` + dashboard registry timeline columns
- SC-3 (REQ-V12-DASHBOARD-07 + OPS-01): PID file + run-status dot + `.stop` warning
- SC-4 (REQ-V12-DASHBOARD-08): Agent inspector drawer on node click
- SC-5 (REQ-V12-EMERGE-01 + EMERGE-02): Overlap detector + decision-log enrichment

</domain>

<decisions>
## Implementation Decisions

### Wave structure (4 waves matching estimate)
- Wave 1 (17-01): CLI tick stage inspector + mechanics history (SC-1 + SC-2a)
- Wave 2 (17-02): Dashboard mechanics timeline + run-status dot + OPS-01 (SC-2b + SC-3)
- Wave 3 (17-03): Dashboard agent inspector drawer (SC-4)
- Wave 4 (17-04): Overlap detector + decision-log enrichment (SC-5)

### SC-1: Tick stage inspector
- Extend existing `token-world tick` command in `src/token_world/inspect/tick.py`
- Add `load_stage_data(universe_dir, tick_id, stage)` that reads from `diagnostics/tick_N/<stage>/`
- `--stage classification` → reads `diagnostics/tick_N/classification/` JSON
- `--stage matcher` → reads matching result from tick summary
- `--stage observer` → reads observer diagnostics
- `--raw` → print raw prompt+response text; default (no --raw) → print parsed payload
- `--format json` respects the stage filter

### SC-2: Mechanics history
- Extend `src/token_world/inspect/mechanics.py` with `--history` flag
- `MechanicRow` gains `first_authored_commit: str | None` and `first_authored_timestamp: str | None` fields
- Use `subprocess` + `git log --follow --format=... mechanics/<id>.py` inside universe dir
- `--history` flag: populate git fields; without flag: existing behavior unchanged (no git subprocess overhead)
- Dashboard registry panel adds "First authored" + "Last invoked" columns consuming `token-world mechanics <slug> --history --format json`

### SC-3: PID file + run-status dot
- `scripts/run_unattended.py`: write `<universe>/.run-pid` on startup (PID + start time JSON); remove on clean exit; handle SIGINT gracefully; check `.stop` at startup and exit with non-zero + stderr warning
- Dashboard stats strip: `load_run_status(universe_dir)` returns `{state: "running"|"stale"|"idle", pid: int|None, started_at: str|None}`; mount as colored dot in stats row
- OPS-01 covered: `.stop` check at startup + loud stderr + non-zero exit

### SC-4: Agent inspector drawer
- `src/token_world/dashboard/panels/graph_canvas.py` already has a property drawer
- When user clicks an agent node (node with `type=agent`): open a structured drawer instead of the generic property dump
- New helper `render_agent_inspector(agent_summary: AgentSummary)` in a new `agent_inspector.py` panel
- Sections: Identity, Location (from `located_in` pseudo-edge), Memory (last 10 entries), Active LRA, Attention state, Recent actions (last 10 action_texts from tick summaries)
- Scroll preservation: drawer is user state — never rebuild on poll (same as existing property drawer)

### SC-5: Overlap detector + decision log
- `src/token_world/operator/overlap.py`: `compute_overlap(proposed_verb, proposed_watches, registry)` → float 0.0–1.0
- Overlap score = max(verb match jaccard, watches match jaccard) against all existing mechanics
- Yield-handler subagent prompt (`.planning/agent-prompts/yield-handler.md` or wherever it lives): add overlap report + "prefer edit-existing when score > 0.7" instruction
- Decision-log enrichment: yield resolution writes subagent final JSON to `<universe>/operator-log.jsonl` (additive to existing events)
- `token-world yield <slug> --history` shows the log (optional, implement if time permits)

### Back-compat
- All CLI changes are additive flags; existing invocations unchanged
- Dashboard changes additive columns/sections
- operator-log.jsonl additions are additive (existing entries unchanged)

</decisions>

<code_context>
## Existing Code Insights

- `src/token_world/inspect/tick.py` — `load_tick()`, `render_tree()`, `format_table()`; need to add `load_stage_data()` and flag handling
- `src/token_world/inspect/mechanics.py` — `MechanicRow`, `MechanicsReport`, `aggregate()`; extend with git history
- `src/token_world/engine/diagnostics.py` — tick diagnostics storage format; read from `diagnostics/tick_N/`
- `src/token_world/mechanic/diagnostics.py` — DiagnosticsSink writes to `diagnostics/tick_N/`
- `scripts/run_unattended.py` — PID file + SIGINT handling + `.stop` check additions go here
- `src/token_world/dashboard/panels/stats.py` — add run-status dot to stats strip
- `src/token_world/dashboard/panels/graph_canvas.py` — property drawer is already there; extend for agent nodes
- `src/token_world/inspect/agents.py` — AgentSummary, AgentsReport; reuse for agent inspector
- `src/token_world/operator/` — overlap.py (new), subagent.py (yield resolution logging)
- `.planning/agent-prompts/` — yield-handler prompt location (find with glob)

</code_context>

<specifics>
## Specific Requirements

- CLI `--stage` flag must work with `--format json` and `--format table`
- Dashboard dots must NOT add a spinner or heavy animation (dark Tailwind only, static colored circle)
- Agent drawer must not rebuild on poll (user may be reading — §A7 scroll guarantee)
- Overlap score threshold 0.7 is the "prefer edit-existing" threshold (documented in REQUIREMENTS)
- `operator-log.jsonl` is newline-delimited JSON — append-only, never rewrite
- Wave 4 (overlap + decision log) is the most complex; if time runs short, SC-5 is lowest priority per ROADMAP

</specifics>

<deferred>
## Deferred Ideas

- `token-world yield <slug> --history` CLI command (optional SC-5 stretch)
- Per-sub-action diagnostics panels in dashboard
- Playwright e2e tests for drawer (SC-4 only needs unit/snapshot tests)

</deferred>
