# Phase 11 — NiceGUI Dashboard — SUMMARY

**Status:** Shipped 2026-04-15 (Session 4, Track B)
**Retroactively archived:** 2026-04-14 at v1.2 milestone open — see
[../../milestones/v1.1-ROADMAP.md](../../milestones/v1.1-ROADMAP.md) for
milestone-level context.

## Delivered

Four read-only NiceGUI panels mounted at `localhost:PORT` consuming the
Operator CLI JSON surface (Track A):

- **Stats strip** — always-visible header (tick #, tick/min, yield %,
  novel mechanics, cost). Commit `41e8f30` (Plan 11-01).
- **Live tick stream** — card feed auto-refreshed every 2s; cards expand
  to show the full action/classification/observation tree. Commit
  `41e8f30` (Plan 11-01) with progressive refinements across
  `f84c9b2`..`8a09f14`.
- **Graph canvas** — Mermaid node-link view with property drawer on
  click. Commit `f84c9b2` (Plan 11-03).
- **Causal chain viewer** — walks a single node/property backward in
  time through mutations (consumes `token-world trace` JSON). Commit
  `0781543` (Plan 11-04); renamed to "Property history" in v1.2 per
  §A5a.

Polish pass closed with commit `8a09f14` (Plan 11-05): layout cleanup,
docs page, Script Catalog entry, dark-mode toggle default-on.

## Scope cuts honoured

Every deferral listed in the PLAN's "Scope cuts (make tonight
shippable)" section was respected. The deferred items moved to v1.2 as
their own REQ entries:

- No tick scrubber → carry to v2 if ever needed
- No agent inspector drawer → REQ-V12-DASHBOARD-08 in v1.2
- No 8-bit canvas styling → cosmetic, never surfaced as blocking
- No SSE (polled instead) → poll model exposed REQ-V12-DASHBOARD-01
  (scroll-preservation) but the tradeoff was correct for the ship

## Tests

26 tests landed with the phase (app module import, stats rendering,
tick-card DOM structure, graph rendering smoke, causal chain query).
Playwright verification in session 6 caught the scroll-preservation bug
that escaped Phase 11's test coverage — captured as REQ-V12-DASHBOARD-01
warm-up (shipped `d31090d`).

## Decisions

- **D-01 (v1.1):** NiceGUI is the dashboard stack. Revisits the
  FastAPI/Flask ban — NiceGUI is Python-native reactive; FastAPI is
  transitive, not direct. Ban targets direct-app-framework use.
  Validated through ship.

## Commits (chronological)

- `41e8f30` — Plan 11-01 NiceGUI skeleton + stats strip
- `131b787` — mypy override for transitive nicegui
- `f84c9b2` — Plan 11-03 graph canvas + Mermaid + property drawer
- `0781543` — Plan 11-04 causal chain viewer panel
- `8a09f14` — Plan 11-05 polish
- `168cdc7` (retroactive) — declare nicegui as `dashboard` optional extra
- `f857acc` (retroactive) — CI installs dashboard extra

## Follow-up (lands in v1.2)

- REQ-V12-DASHBOARD-01 scroll preservation (shipped warm-up `d31090d`, `6101da0`)
- REQ-V12-DASHBOARD-02 structured tick expansion (shipped warm-up `d31090d`)
- REQ-V12-DASHBOARD-03 side-effect chain tree (shipped warm-up `d31090d`)
- REQ-V12-DASHBOARD-04 graph label + located_in edges (shipped warm-up `6101da0`)
- REQ-V12-DASHBOARD-05..09 multi-agent scaffold + inspector + run-status + timeline (active, not yet landed)

---

*Retroactive summary — the Phase 11 work shipped in session 4 without
a formal SUMMARY.md alongside the landed commits. This file is
reconstructed from commit log + PLAN.md checkboxes + v1.1 archive at
v1.2 milestone open.*
