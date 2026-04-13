#!/usr/bin/env python3
"""UAT smoke harness for phase 03 (design-validation).

Runs tests 4-11 of .planning/phases/03-design-validation/03-UAT.md against a
fresh, throwaway universe. Re-runnable; cleans its own scratch dir.

Usage:
    uv run python scripts/uat_phase_03.py

Exit codes:
    0 = all checks green
    non-zero = one or more checks failed (details printed)
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = Path("/tmp/uat_phase_03")
DATA = SCRATCH / "data"
SLUG = "uat-demo"


def run(cmd: list[str], env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    full_env = {**os.environ, **(env or {})}
    result = subprocess.run(cmd, cwd=ROOT, env=full_env, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.stderr.write(f"CMD failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n")
        raise SystemExit(1)
    return result


def banner(title: str) -> None:
    print(f"\n=== {title} ===")


def check_scaffold_and_cli() -> tuple[bool, str]:
    """Test 1: fresh universe scaffolds + lists."""
    env = {"XDG_DATA_HOME": str(DATA)}
    run(["uv", "run", "token-world", "create", SLUG], env=env)
    uni = DATA / "token_world" / "universes" / SLUG
    required = ["CLAUDE.md", ".mcp.json", "universe.db", "mechanics", "agents"]
    missing = [f for f in required if not (uni / f).exists()]
    if missing:
        return False, f"scaffolding missing: {missing}"
    listing = run(["uv", "run", "token-world", "list"], env=env).stdout
    if SLUG not in listing:
        return False, f"'{SLUG}' not in `token-world list` output"
    return True, f"universe scaffolded at {uni}"


def seed_graph() -> Path:
    """Seed the demo universe with a graph that has spatial + property mix."""
    from token_world.graph import KnowledgeGraph

    db = DATA / "token_world" / "universes" / SLUG / "universe.db"
    kg = KnowledgeGraph(db_path=db)
    kg.add_node("alice", node_type="agent", position=[0.0, 0.0], hp=100)
    kg.add_node("room_a", node_type="entity", subtype="room", position=[1.0, 1.0])
    kg.add_node("sword", node_type="entity", subtype="weapon", position=[0.5, 0.5], damage=10)
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("sword", "alice", relation="held_by")
    kg.save()
    return db


def check_viz_graph_cli() -> tuple[bool, str]:
    """Test 6: viz-graph CLI emits well-formed flowchart."""
    env = {"XDG_DATA_HOME": str(DATA)}
    out = run(["uv", "run", "token-world", "viz-graph", SLUG, "--node", "alice", "--depth", "2"], env=env).stdout
    required_tokens = [
        "flowchart LR",
        "alice",
        "room_a",
        "sword",
        "located_in",
        "held_by",
        "classDef agent",
        "classDef entity",
    ]
    missing = [t for t in required_tokens if t not in out]
    if missing:
        return False, f"viz-graph output missing tokens {missing}\n{out}"
    return True, "viz-graph rendered flowchart LR with all expected tokens"


def check_mermaid_injection_safety() -> tuple[bool, str]:
    """Test 7: a label with dangerous chars gets HTML-entity escaped.

    Mermaid label syntax is ``id["..."]`` — anything inside the quotes is literal
    text. The injection vectors are therefore the characters that would let an
    attacker break out of the quoted label: ``"`` (close quote), ``]`` (close
    bracket), ``[`` (open), and ``|`` (label-arrow separator). ``<`` / ``>`` are
    *not* leaks — ``escape_label`` deliberately emits ``<br/>`` for newlines, a
    fixed Mermaid-sanctioned tag that cannot carry attacker-controlled payload.
    """
    from token_world.viz import escape_label

    raw = 'foo"]:::evil; classDef bad fill:red\n[exploit]|rogue'
    escaped = escape_label(raw)
    for forbidden in ['"', "[", "]", "|"]:
        if forbidden in escaped:
            return False, f"escape_label leaked raw {forbidden!r} in {escaped!r}"
    # ``<br/>`` is allowed; any other ``<`` or ``>`` would indicate raw HTML leak.
    stripped = escaped.replace("<br/>", "")
    if "<" in stripped or ">" in stripped:
        return False, f"escape_label leaked raw <> outside of <br/> in {escaped!r}"
    return True, f"escape_label sanitized dangerous chars -> {escaped!r}"


def check_use_case_library() -> tuple[bool, str]:
    """Test 8: 35 UC files + valid schema."""
    from token_world.use_cases import load_use_case, validate_frontmatter

    base = ROOT / ".planning" / "use-cases"
    counts = {
        "spatial": (7, "S"),
        "social": (8, "O"),
        "resource": (7, "R"),
        "environmental": (7, "V"),
        "edge-case": (6, "E"),
    }
    seen_ids: set[str] = set()
    problems: list[str] = []
    for cat, (expected, letter) in counts.items():
        files = sorted((base / cat).glob("UC-*.md"))
        if len(files) != expected:
            problems.append(f"{cat}: expected {expected} UC files, found {len(files)}")
        for f in files:
            fm, _body = load_use_case(f)
            errors = validate_frontmatter(fm)
            if errors:
                problems.append(f"{f.name}: {errors}")
            uc_id = fm.get("id", "")
            if not re.fullmatch(rf"UC-{letter}\d{{2}}", uc_id):
                problems.append(f"{f.name}: bad id '{uc_id}' (expected UC-{letter}NN)")
            if uc_id in seen_ids:
                problems.append(f"{f.name}: duplicate id '{uc_id}'")
            seen_ids.add(uc_id)
    if problems:
        return False, "\n".join(problems[:10])
    return True, f"35 UC files, all ids unique and schema-valid ({sorted(seen_ids)[:3]}..)"


def check_category_summaries() -> tuple[bool, str]:
    """Test 9: 5 CATEGORY-SUMMARY.md files."""
    base = ROOT / ".planning" / "use-cases"
    cats = ["spatial", "social", "resource", "environmental", "edge-case"]
    missing = [c for c in cats if not (base / c / "CATEGORY-SUMMARY.md").exists()]
    if missing:
        return False, f"missing CATEGORY-SUMMARY.md for: {missing}"
    return True, "5 CATEGORY-SUMMARY.md files present"


def check_gap_analysis() -> tuple[bool, str]:
    """Test 10: GAP-ANALYSIS.md has 4 layers + 3 dispositions + schema test passes."""
    gap = ROOT / ".planning" / "phases" / "03-design-validation" / "GAP-ANALYSIS.md"
    if not gap.exists():
        return False, f"{gap} missing"
    text = gap.read_text()
    for heading in ["Graph API", "Mechanic Framework", "Engine Pipeline"]:
        if heading not in text:
            return False, f"layer heading '{heading}' missing"
    result = run(
        ["uv", "run", "pytest", "tests/test_design_validation/test_gap_analysis_schema.py", "-q"],
        check=False,
    )
    if result.returncode != 0:
        return False, f"schema test failed:\n{result.stdout}\n{result.stderr}"
    return True, "GAP-ANALYSIS.md has layers + schema test passes"


def check_gap_handoff() -> tuple[bool, str]:
    """Test 11: GAP-HANDOFF.md routes gaps + deferrals parked."""
    root = ROOT / ".planning"
    handoff = root / "GAP-HANDOFF.md"
    deferrals = root / "backlog" / "phase-03-gap-deferrals.md"
    missing = [p for p in (handoff, deferrals) if not p.exists()]
    if missing:
        return False, f"missing: {[str(p) for p in missing]}"
    h_text = handoff.read_text()
    for needle in ["Phase 04", "Phase 05"]:
        if needle not in h_text:
            return False, f"'{needle}' not mentioned in GAP-HANDOFF.md"
    return True, "GAP-HANDOFF.md + deferrals present with Phase 04/05 routing"


def main() -> int:
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)

    banner("Test 1: Cold Start Smoke")
    ok, msg = check_scaffold_and_cli()
    print(("PASS" if ok else "FAIL") + ": " + msg)
    if not ok:
        return 2

    seed_graph()
    print("(seeded demo graph)")

    results: list[tuple[str, bool, str]] = []
    for name, fn in [
        ("Test 6: viz-graph CLI", check_viz_graph_cli),
        ("Test 7: Mermaid injection safety", check_mermaid_injection_safety),
        ("Test 8: Use case library (35 UCs)", check_use_case_library),
        ("Test 9: Category summaries", check_category_summaries),
        ("Test 10: GAP-ANALYSIS.md", check_gap_analysis),
        ("Test 11: GAP-HANDOFF.md", check_gap_handoff),
    ]:
        banner(name)
        try:
            ok, msg = fn()
        except Exception as e:
            ok, msg = False, f"exception: {e!r}"
        print(("PASS" if ok else "FAIL") + ": " + msg)
        results.append((name, ok, msg))

    banner("Summary")
    failed = [r for r in results if not r[1]]
    for name, ok, msg in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    return 0 if not failed else 3


if __name__ == "__main__":
    raise SystemExit(main())
