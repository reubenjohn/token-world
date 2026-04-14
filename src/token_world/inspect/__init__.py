"""Universe inspection utilities (Phase 7+, Track A: Operator CLI Surface).

Read-only modules that aggregate universe state from on-disk artefacts
(``universe.db``, ``mechanics/``, ``tick_summaries/``, ``operator-log.jsonl``)
and produce table/JSON renderings for the ``token-world inspect``,
``token-world tick``, ``token-world stats``, ``token-world mechanics``,
``token-world watch`` and ``token-world trace`` commands.

The contract every module here MUST honour:

- Pure read-only — never mutates on-disk state.
- Pure-stdlib aggregation — Anthropic SDK is not imported anywhere in this
  subpackage. (Inspection must work even if the universe was built without
  network access.)
- Dual rendering — ``render_table()`` and ``render_json()`` are siblings;
  the JSON shape is the stable consumer contract (dashboard / scripts).
- Graceful degradation — missing files / empty dirs produce a sensible
  empty report, never a crash.
"""
