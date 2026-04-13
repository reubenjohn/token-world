"""Click CLI entry point for Token World."""

from __future__ import annotations

import asyncio
import json as _json
import re
import sys
from pathlib import Path

import anthropic
import click

from token_world.engine.engine import SimulationEngine
from token_world.graph import KnowledgeGraph
from token_world.operator.cli_support import (
    latest_halted_tick,
    render_replay_human,
    render_replay_json,
    render_yield_human,
    render_yield_json,
    resolve_universe,
)
from token_world.operator.diagnostics import OperatorDiagnosticsReader
from token_world.operator.harness import OperatorHarness
from token_world.operator.testing import EngineStub
from token_world.operator.yield_signal import YieldSignal
from token_world.resident import (
    AgentMemory,
    PersonalityBundle,
    PersonalityGenerator,
    ResidentAgent,
    SessionManager,
    create_agent_node,
)
from token_world.universe.manager import UniverseManager


@click.group()
def cli() -> None:
    """Token World - Universe Simulator"""


@cli.command()
@click.argument("name")
def create(name: str) -> None:
    """Create a new universe with the given name."""
    manager = UniverseManager()
    try:
        path = manager.create(name)
        click.echo(f"Universe created at {path}")
    except (ValueError, FileExistsError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e


@cli.command("list")
def list_universes() -> None:
    """List all universes."""
    manager = UniverseManager()
    universes = manager.list()
    if not universes:
        click.echo("No universes found.")
        return
    for u in universes:
        click.echo(f"  {u.slug}  ({u.name})")


@cli.command()
@click.argument("slug")
def delete(slug: str) -> None:
    """Delete a universe by slug."""
    manager = UniverseManager()
    try:
        manager.delete(slug)
        click.echo(f"Universe '{slug}' deleted")
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e


@cli.command("list-mechanics")
@click.argument("universe")
def list_mechanics(universe: str) -> None:
    """List all mechanics in a universe."""
    manager = UniverseManager()
    try:
        universe_dir = manager.load(universe)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e
    mechanics_dir = universe_dir / "mechanics"
    if not mechanics_dir.exists():
        click.echo("No mechanics directory found.")
        return
    from token_world.mechanic.registry import MechanicRegistry

    registry = MechanicRegistry(mechanics_dir, universe_dir=universe_dir)
    mechanics = registry.list_mechanics()
    if not mechanics:
        click.echo("No mechanics found.")
        return
    for m in mechanics:
        vol = "voluntary" if m.voluntary else "involuntary"
        click.echo(f"  {m.id:<30} {vol:<15} {m.description}")


@cli.command("run-mechanic")
@click.argument("universe")
@click.argument("mechanic_id")
@click.option("--actor", required=True, help="Actor node ID")
@click.option("--target", required=True, help="Target node ID")
def run_mechanic(universe: str, mechanic_id: str, actor: str, target: str) -> None:
    """Execute a mechanic against a universe's graph."""
    manager = UniverseManager()
    try:
        universe_dir = manager.load(universe)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e

    from token_world.graph import KnowledgeGraph
    from token_world.mechanic import ChainExecutionEngine, MechanicContext
    from token_world.mechanic.registry import MechanicRegistry

    # Load graph from universe.db
    kg = KnowledgeGraph(db_path=universe_dir / "universe.db")
    kg.load()

    # Load registry and get mechanic
    mechanics_dir = universe_dir / "mechanics"
    registry = MechanicRegistry(mechanics_dir, universe_dir=universe_dir)
    try:
        mechanic = registry.get_mechanic(mechanic_id)
    except KeyError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e

    # Build context
    ctx = MechanicContext(kg, actor=actor, target=target)

    # Get all involuntary mechanics for chain execution
    involuntary = [
        registry.get_mechanic(m.id) for m in registry.list_mechanics() if not m.voluntary
    ]
    engine = ChainExecutionEngine(involuntary)
    trace = engine.execute(mechanic, ctx)

    # Output results
    root = trace.root
    if not root.check_result.passed:
        click.echo(f"Check FAILED: {', '.join(root.check_result.reasons)}")
        raise SystemExit(1)
    click.echo("Check PASSED")
    click.echo(f"Mutations: {len(root.mutations)}")
    for m in root.mutations:
        click.echo(f"  {m.type}: {m.target} {m.property or ''} = {m.new_value}")
    click.echo(f"Total mechanics executed: {trace.total_mechanics_executed}")
    click.echo(f"Max depth reached: {trace.max_depth_reached}")
    if trace.truncated:
        click.echo("WARNING: Chain execution was truncated at max depth")

    # Save graph state
    kg.save()
    click.echo("Graph saved.")


@cli.command("query-graph")
@click.argument("universe")
@click.option(
    "--type",
    "node_type",
    type=click.Choice(["agent", "entity"]),
    help="Filter by node type",
)
@click.option("--has-property", "has_prop", help="Filter nodes having this property")
@click.option("--near", "near_node", help="Show neighbors of this node")
@click.option("--limit", default=50, help="Max nodes to show")
@click.option("--stats", is_flag=True, help="Show summary statistics only")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def query_graph(
    universe: str,
    node_type: str | None,
    has_prop: str | None,
    near_node: str | None,
    limit: int,
    stats: bool,
    as_json: bool,
) -> None:
    """Query and inspect a universe's knowledge graph."""
    import json as json_mod

    manager = UniverseManager()
    try:
        universe_dir = manager.load(universe)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e

    from token_world.graph import KnowledgeGraph

    kg = KnowledgeGraph(db_path=universe_dir / "universe.db")
    kg.load()

    # Build filter kwargs
    filters: dict[str, str] = {}
    if node_type:
        filters["type"] = node_type

    # Get candidate nodes
    if near_node:
        if not kg.has_node(near_node):
            click.echo(f"Error: Node '{near_node}' not found", err=True)
            raise SystemExit(1)
        candidates = kg.neighbors(near_node)
    else:
        candidates = kg.nodes(**filters)

    # Apply has-property filter
    if has_prop:
        candidates = [n for n in candidates if has_prop in kg.query(n)]

    # Apply type filter if near_node was used (filters not passed to kg.nodes)
    if near_node and node_type:
        candidates = [n for n in candidates if kg.query(n).get("type") == node_type]

    # Stats mode
    if stats:
        all_nodes = kg.nodes()
        agents = kg.nodes(type="agent")
        entities = kg.nodes(type="entity")
        if as_json:
            click.echo(
                json_mod.dumps(
                    {
                        "total_nodes": len(all_nodes),
                        "agents": len(agents),
                        "entities": len(entities),
                        "matching": len(candidates),
                    }
                )
            )
        else:
            click.echo(f"Total nodes: {len(all_nodes)}")
            click.echo(f"  Agents: {len(agents)}")
            click.echo(f"  Entities: {len(entities)}")
            click.echo(f"Matching filter: {len(candidates)}")
        return

    # Limit
    truncated = len(candidates) > limit
    candidates = candidates[:limit]

    # Output
    if as_json:
        result = []
        for n in candidates:
            result.append({"id": n, **kg.query(n)})
        click.echo(json_mod.dumps(result, indent=2, default=str))
    else:
        if not candidates:
            click.echo("No matching nodes.")
            return
        for n in candidates:
            props = kg.query(n)
            props_str = ", ".join(f"{k}={v!r}" for k, v in props.items())
            click.echo(f"  {n}: {props_str}")
    if truncated:
        click.echo(f"  ... (truncated at {limit})")


@cli.command("viz-graph")
@click.argument("universe")
@click.option("--node", "anchor_node", default=None, help="Anchor node for the ego-graph.")
@click.option(
    "--depth",
    type=int,
    default=1,
    show_default=True,
    help="Hops from anchor(s) to include.",
)
@click.option(
    "--seed-query",
    "seed_queries",
    multiple=True,
    help="KEY=VALUE; anchor set is all nodes where property KEY equals VALUE. Repeatable.",
)
@click.option(
    "--all-agents",
    is_flag=True,
    default=False,
    help="Use all agent-typed nodes as anchors (depth 1 unless --depth given).",
)
@click.option(
    "--type",
    "type_filter",
    type=click.Choice(["agent", "entity"]),
    default=None,
    help="Keep only this node type (anchors always preserved).",
)
@click.option(
    "--has-property",
    "has_property",
    default=None,
    help="Keep only nodes that have this property (anchors always preserved).",
)
@click.option(
    "--exclude-property",
    "exclude_property",
    default=None,
    help="Drop nodes that have this property (anchors always preserved).",
)
@click.option(
    "--max-nodes",
    type=int,
    default=150,
    show_default=True,
    help="Hard cap on node count; exceeds => error with tightening hint.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Write Mermaid output to FILE instead of stdout.",
)
@click.option(
    "--no-style",
    "no_style",
    is_flag=True,
    default=False,
    help="Emit minimal Mermaid (no classDef, no emoji).",
)
def viz_graph(
    universe: str,
    anchor_node: str | None,
    depth: int,
    seed_queries: tuple[str, ...],
    all_agents: bool,
    type_filter: str | None,
    has_property: str | None,
    exclude_property: str | None,
    max_nodes: int,
    output: str | None,
    no_style: bool,
) -> None:
    """Emit a filtered Mermaid flowchart for a universe's knowledge graph.

    An anchor is REQUIRED -- provide --node, --seed-query, or --all-agents.
    Whole-graph rendering is not supported; use filters to focus.
    """
    if not (anchor_node or seed_queries or all_agents):
        click.echo(
            "Error: an anchor is required. Use --node <id>, "
            "--seed-query KEY=VALUE, or --all-agents.",
            err=True,
        )
        raise SystemExit(2)

    from pathlib import Path

    from token_world.graph import KnowledgeGraph
    from token_world.viz import TooManyNodesError, extract_subgraph, to_mermaid

    manager = UniverseManager()
    try:
        universe_dir = manager.load(universe)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e

    kg = KnowledgeGraph(db_path=universe_dir / "universe.db")
    kg.load()

    anchors: list[str] = []
    if anchor_node:
        anchors.append(anchor_node)
    for sq in seed_queries:
        if "=" not in sq:
            click.echo(
                f"Error: --seed-query must be KEY=VALUE (got {sq!r})",
                err=True,
            )
            raise SystemExit(2)
        k, v = sq.split("=", 1)
        anchors.extend(kg.nodes(**{k: v}))
    if all_agents:
        # KnowledgeGraph stores node type under key "type"
        anchors.extend(kg.nodes(type="agent"))

    # Dedupe while preserving order
    anchors = list(dict.fromkeys(anchors))
    if not anchors:
        click.echo("Error: anchor set is empty (no matching nodes).", err=True)
        raise SystemExit(3)

    sub = extract_subgraph(kg, anchors=anchors, depth=depth)

    try:
        mermaid = to_mermaid(
            kg,
            sub,
            max_nodes=max_nodes,
            style=not no_style,
            type_filter=type_filter,
            has_property=has_property,
            exclude_property=exclude_property,
        )
    except TooManyNodesError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(4) from e

    if output:
        Path(output).write_text(mermaid, encoding="utf-8")
        click.echo(f"Wrote {len(mermaid)} bytes to {output}")
    else:
        click.echo(mermaid)


@cli.command("validate-mechanic")
@click.argument("universe_or_path")
@click.argument("mechanic_id", required=False, default=None)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["human", "json"]),
    default="human",
    show_default=True,
    help="Output format.",
)
def validate_mechanic(universe_or_path: str, mechanic_id: str | None, fmt: str) -> None:
    """Validate a mechanic module and print a structured report.

    Usage:

      token-world validate-mechanic <universe-slug> <mechanic-id>
      token-world validate-mechanic <path-to-module.py>

    Exit code 0 on pass, 1 on fail, 2 on resolver errors.
    """
    # Deferred import so importing ``token_world.cli`` stays cheap for the
    # other commands.
    from token_world.mechanic.validation import validate

    p = Path(universe_or_path)
    if p.is_file() and p.suffix == ".py":
        module_path = p
    else:
        if mechanic_id is None:
            click.echo(
                "Error: mechanic-id is required when universe-or-path is a slug",
                err=True,
            )
            raise SystemExit(2)
        manager = UniverseManager()
        try:
            universe_dir = manager.load(universe_or_path)
        except (FileNotFoundError, ValueError) as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(2) from e
        module_path = universe_dir / "mechanics" / f"{mechanic_id}.py"
        if not module_path.is_file():
            click.echo(f"Error: mechanic file not found: {module_path}", err=True)
            raise SystemExit(2)

    report = validate(module_path, run_tests=True)

    if fmt == "json":
        click.echo(_json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        status = "PASS" if report.passed else "FAIL"
        click.echo(f"{status} {module_path}")
        for f in report.findings:
            loc = f":{f.line}:{f.col}" if f.line is not None else ""
            click.echo(f"  [{f.severity}] [{f.stage}:{f.rule}] {f.path}{loc} -- {f.message}")

    raise SystemExit(0 if report.passed else 1)


_MECHANIC_SKELETON = '''"""{description}"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class {class_name}(Mechanic):
    """{description}.

    Preconditions:
        - TODO
    Side effects:
        - TODO
    """

    id = "{mechanic_id}"
    description = "{description}"
    voluntary = {voluntary}
    tags: list[str] = []

    def check(self, ctx: "MechanicContext") -> CheckResult:
        # TODO: implement preconditions
        return CheckResult(passed=False, reasons=["TODO: implement check"])

    def apply(self, ctx: "MechanicContext") -> list[Mutation]:
        # TODO: implement side effects
        return []
'''


_TEST_SKELETON = '''"""Tests for the ``{mechanic_id}`` mechanic."""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="TODO: implement test for {mechanic_id} mechanic")
def test_{mechanic_id}_placeholder() -> None:
    """Placeholder — fill in after implementing check()/apply()."""
    assert False, "TODO"
'''


def _camel_case(s: str) -> str:
    """Convert ``lowercase_with_underscores`` to ``UpperCamelCase``."""
    return "".join(part.capitalize() or "_" for part in s.split("_"))


@cli.command("scaffold-mechanic")
@click.argument("universe_slug")
@click.option(
    "--id",
    "mechanic_id",
    required=True,
    help="Unique mechanic id (lowercase_with_underscores)",
)
@click.option(
    "--voluntary/--involuntary",
    default=True,
    help="Voluntary (default) or involuntary",
)
@click.option(
    "--description",
    default="TODO: describe this mechanic",
    help="One-line description",
)
def scaffold_mechanic(
    universe_slug: str,
    mechanic_id: str,
    voluntary: bool,
    description: str,
) -> None:
    """Scaffold a new mechanic in a universe (module + test stub).

    Writes ``<universe>/mechanics/<id>.py`` and
    ``<universe>/tests/test_mechanics/test_<id>.py``. Refuses to overwrite
    existing files (exit 1). Invalid ids exit 2.
    """
    import re as _re

    if not _re.match(r"^[a-z][a-z0-9_]*$", mechanic_id):
        click.echo(
            f"Error: mechanic-id must be lowercase_with_underscores (got {mechanic_id!r})",
            err=True,
        )
        raise SystemExit(2)

    manager = UniverseManager()
    try:
        universe_dir = manager.load(universe_slug)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e

    module_path = universe_dir / "mechanics" / f"{mechanic_id}.py"
    test_path = universe_dir / "tests" / "test_mechanics" / f"test_{mechanic_id}.py"
    if module_path.exists():
        click.echo(f"Error: {module_path} already exists", err=True)
        raise SystemExit(1)
    if test_path.exists():
        click.echo(f"Error: {test_path} already exists", err=True)
        raise SystemExit(1)

    class_name = _camel_case(mechanic_id) + "Mechanic"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text(
        _MECHANIC_SKELETON.format(
            class_name=class_name,
            mechanic_id=mechanic_id,
            description=description,
            voluntary=voluntary,
        ),
        encoding="utf-8",
    )
    test_path.write_text(
        _TEST_SKELETON.format(mechanic_id=mechanic_id),
        encoding="utf-8",
    )
    click.echo(f"Scaffolded {module_path}")
    click.echo(f"Scaffolded {test_path}")


@cli.command("prune-diagnostics")
@click.argument("universe_slug")
@click.option(
    "--before-tick",
    type=int,
    default=None,
    help="Prune tick folders whose id is strictly less than N.",
)
@click.option(
    "--before-date",
    type=str,
    default=None,
    help="Prune folders older than YYYY-MM-DD.",
)
@click.option(
    "--confirm",
    is_flag=True,
    default=False,
    help="Actually delete (default is dry-run).",
)
def prune_diagnostics(
    universe_slug: str,
    before_tick: int | None,
    before_date: str | None,
    confirm: bool,
) -> None:
    """Prune old diagnostics folders from a universe. Dry-run by default.

    Exactly one of ``--before-tick`` or ``--before-date`` is required.
    Without ``--confirm`` the command prints the candidate list and exits 0
    without touching the filesystem (T-04-PRUNE-DESTRUCTION).
    """
    from datetime import date as _date

    if (before_tick is None) == (before_date is None):
        click.echo(
            "Error: specify exactly one of --before-tick or --before-date",
            err=True,
        )
        raise SystemExit(2)

    before_dt: _date | None = None
    if before_date is not None:
        try:
            before_dt = _date.fromisoformat(before_date)
        except ValueError as e:
            click.echo(
                f"Error: invalid --before-date (expected YYYY-MM-DD): {before_date}",
                err=True,
            )
            raise SystemExit(2) from e

    from token_world.mechanic.diagnostics import DiagnosticsSink

    manager = UniverseManager()
    try:
        universe_dir = manager.load(universe_slug)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e

    sink = DiagnosticsSink(universe_dir)
    candidates = sink.prune(
        before_tick=before_tick,
        before_date=before_dt,
        confirm=confirm,
    )
    verb = "Deleted" if confirm else "Would delete"
    click.echo(f"{verb} {len(candidates)} diagnostics folder(s):")
    for c in candidates:
        try:
            rel = c.relative_to(universe_dir)
            label: str = str(rel)
        except ValueError:
            label = str(c)
        click.echo(f"  {label}")
    if not confirm:
        click.echo("(dry-run -- rerun with --confirm to actually delete)")


# =========================================================================== #
# Operator commands (Phase 04.1-04)
#
# run-tick, inspect-yield, resume-tick, replay-tick: the developer-facing
# interface to the Agent SDK driver shipped by Plan 04.1-03. All four honour
# the standard universe-resolution order (slug > env > cwd) and ALL four
# follow the documented exit-code contract:
#
#   run-tick      0 success | 1 harness failure | 2 universe not found | 3 no halted
#   inspect-yield 0 success | 2 universe not found | 4 no yield
#   resume-tick   0 success | 1 MCP failure       | 2 universe not found
#   replay-tick   0 success | 2 universe not found | 4 tick not found
#
# Zero new MCP tools are added (D-06, UNIV-03). replay-tick and inspect-yield
# use the sole-sanctioned OperatorDiagnosticsReader (D-16).
# =========================================================================== #


# tick_id may safely appear as a path segment inside <universe>/diagnostics/.
# Keep the regex small — alphanumerics, underscore, hyphen, dot. Rejects
# traversal chars (/ \ ..) and shell metacharacters (T-04.1-18).
_TICK_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")

# --stub KEY=VALUE whitelist. Adding a key here is an intentional action;
# the default set is the minimum needed to fabricate a valid YieldSignal
# (T-04.1-19).
_STUB_ALLOWED_KEYS: frozenset[str] = frozenset({"verb", "actor", "target", "action_text"})


def _cli_resolve_or_exit(slug: str | None, *, exit_code: int) -> Path:
    """Resolve a universe or exit with *exit_code* and a user-readable error."""
    try:
        return resolve_universe(slug)
    except click.ClickException as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(exit_code)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(exit_code)


def _check_tick_id(tick_id: str) -> None:
    """Reject tick ids that would allow filesystem traversal (T-04.1-18)."""
    if not _TICK_ID_RE.match(tick_id):
        raise click.ClickException(f"Invalid tick id {tick_id!r}: must match [A-Za-z0-9_.-]+")


def _build_stub_signal(universe: Path, stub_kvs: tuple[str, ...], tick_id: str) -> YieldSignal:
    """Fabricate a :class:`YieldSignal` from ``--stub KEY=VALUE`` pairs.

    Whitelisted keys only (T-04.1-19). Missing ``verb`` or ``actor`` raises
    :class:`click.ClickException` with a remediation message.
    """
    kwargs: dict[str, object] = {}
    for kv in stub_kvs:
        if "=" not in kv:
            raise click.ClickException(f"--stub expects KEY=VALUE; got {kv!r}")
        key, value = kv.split("=", 1)
        if key not in _STUB_ALLOWED_KEYS:
            allowed = ", ".join(sorted(_STUB_ALLOWED_KEYS))
            raise click.ClickException(f"--stub key {key!r} not allowed. Allowed keys: {allowed}")
        kwargs[key] = value
    if "verb" not in kwargs or "actor" not in kwargs:
        raise click.ClickException(
            f"--stub requires at least verb=... and actor=... (got keys: {sorted(kwargs.keys())})"
        )
    return EngineStub(universe).fabricate_yield(tick_id=tick_id, **kwargs)  # type: ignore[arg-type]


async def _invoke_resume_tick_mcp(universe: Path, tick_id: str) -> None:
    """Call ``mcp__token-world__resume_tick`` via a short one-shot SDK session.

    Preserves D-05 parity: the programmatic CLI path uses the same MCP tool
    surface the interactive Claude Code path uses. No new MCP tools are added
    (UNIV-03 preserved).

    Monkeypatchable for tests via the module-level symbol; tests replace this
    function to avoid a real SDK subprocess.

    WR-02: the stream is NOT discarded blindly. Any ``ResultMessage`` carrying
    ``is_error=True`` or an ``error_*`` subtype is surfaced as a
    ``RuntimeError``. Without this check the documented exit-code contract at
    line ~689 (``resume-tick: 0 success | 1 MCP failure``) cannot fire on
    MCP-tool-level failures — an MCP server returning a structured error
    (e.g. Phase 0 ``token-world-mcp``'s "not yet implemented") would otherwise
    look identical to a successful resume.
    """
    import claude_agent_sdk
    from claude_agent_sdk import ClaudeAgentOptions, ResultMessage

    from token_world.operator.mcp_client import load_universe_mcp_config

    mcp_servers = load_universe_mcp_config(universe)
    prompt = (
        f"Call mcp__token-world__resume_tick with tick_id={tick_id!r}, "
        "then summarise the result as a single JSON object on the last line."
    )
    options = ClaudeAgentOptions(
        model="haiku",
        max_turns=3,
        mcp_servers=mcp_servers,
        allowed_tools=["mcp__token-world__resume_tick"],
        permission_mode="bypassPermissions",
        cwd=str(universe),
    )
    is_error = False
    error_subtype: str | None = None
    # Resolve query from the module attribute so tests can monkeypatch
    # ``claude_agent_sdk.query`` and exercise this function directly.
    async for msg in claude_agent_sdk.query(prompt=prompt, options=options):
        if isinstance(msg, ResultMessage):
            if getattr(msg, "is_error", False):
                is_error = True
            subtype = getattr(msg, "subtype", None)
            if isinstance(subtype, str) and subtype.startswith("error_"):
                error_subtype = subtype
    if is_error or error_subtype:
        raise RuntimeError(
            f"resume_tick MCP call failed (is_error={is_error}, subtype={error_subtype!r})"
        )


# --------------------------------------------------------------------------- #
# run-tick
# --------------------------------------------------------------------------- #


@cli.command("run-tick")
@click.argument("universe_slug", required=False)
@click.option(
    "--manual",
    is_flag=True,
    help="Print the yield and exit; do NOT invoke the mechanic-author subagent.",
)
@click.option(
    "--tick",
    "tick_id",
    default=None,
    help="Specific halted tick id; defaults to the latest halted tick.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json"]),
    default="json",
    show_default=True,
    help="Output format (default json for programmatic callers).",
)
@click.option(
    "--stub",
    "stub_kvs",
    multiple=True,
    metavar="KEY=VALUE",
    help=(
        "Fabricate a yield via EngineStub. Repeatable KEY=VALUE. Required: "
        "verb=..., actor=...; optional: target=..., action_text=..."
    ),
)
def run_tick(
    universe_slug: str | None,
    manual: bool,
    tick_id: str | None,
    output_format: str,
    stub_kvs: tuple[str, ...],
) -> None:
    """Drain one halted tick via the OperatorHarness.

    If a halted tick exists (``--tick`` or the latest detected), load its
    :class:`YieldSignal`. Otherwise if ``--stub verb=... --stub actor=...``
    is given, fabricate one via :class:`EngineStub`.

    ``--manual`` skips the mechanic-author subagent (prints the yield and
    exits 0); use :command:`token-world resume-tick` after hand-authoring.
    """
    universe = _cli_resolve_or_exit(universe_slug, exit_code=2)

    if stub_kvs:
        effective_tick = tick_id or "tick_1"
        _check_tick_id(effective_tick)
        signal = _build_stub_signal(universe, stub_kvs, effective_tick)
        # BLOCKER-3: persist the fabricated signal BEFORE deciding about
        # --manual. Both inspect-yield and replay-tick depend on it existing
        # on disk; a mid-harness crash without this persistence would leave
        # no artefact to debug from.
        from token_world.mechanic.diagnostics import DiagnosticsSink

        sink = DiagnosticsSink(universe)
        with sink.open_operator_session(effective_tick) as ctx:
            ctx.write_yield_signal(signal)
            if manual:
                # Close immediately with a pending outcome so latest_halted_tick
                # picks up the tick on subsequent invocations.
                ctx.close(
                    {
                        "success": False,
                        "mechanic_id": None,
                        "cost_usd": None,
                        "turns": 0,
                        "tick_continued": False,
                        "error": "manual_mode_no_harness_invoked",
                    }
                )
        tick_id = effective_tick
    else:
        tick_id = tick_id or latest_halted_tick(universe)
        if tick_id is None:
            click.echo(
                "No halted ticks. Use --stub to fabricate one, or wait for "
                "the Phase 5 engine to produce a real yield.",
                err=True,
            )
            sys.exit(3)
        _check_tick_id(tick_id)
        try:
            signal = OperatorDiagnosticsReader(universe, tick_id).yield_signal()
        except FileNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(3)

    if manual:
        if output_format == "json":
            click.echo(render_yield_json(signal))
        else:
            click.echo(render_yield_human(signal))
        return  # exit 0

    try:
        harness = OperatorHarness(universe)
        result = asyncio.run(harness.handle_yield(signal))
    except Exception as e:
        click.echo(f"Harness failed: {e}", err=True)
        sys.exit(1)

    payload: dict[str, object] = {
        "success": result.success,
        "tick_id": result.tick_id,
        "mechanic_id": result.mechanic_id,
        "attempts": result.attempts,
        "cost_usd": result.cost_usd,
        "turns": result.turns,
        "error": result.error,
    }
    if output_format == "json":
        click.echo(_json.dumps(payload, indent=2, sort_keys=True))
    else:
        status = "SUCCESS" if result.success else "FAILURE"
        click.echo(
            f"{status} tick={result.tick_id} mechanic={result.mechanic_id} "
            f"attempts={result.attempts} cost_usd={result.cost_usd}"
        )
    if not result.success:
        sys.exit(1)


# --------------------------------------------------------------------------- #
# inspect-yield
# --------------------------------------------------------------------------- #


@cli.command("inspect-yield")
@click.argument("universe_slug", required=False)
@click.option(
    "--tick",
    "tick_id",
    default=None,
    help="Specific tick id; defaults to the latest halted tick.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json"]),
    default="human",
    show_default=True,
)
def inspect_yield(universe_slug: str | None, tick_id: str | None, output_format: str) -> None:
    """Render the :class:`YieldSignal` for a halted tick."""
    universe = _cli_resolve_or_exit(universe_slug, exit_code=2)
    tick_id = tick_id or latest_halted_tick(universe)
    if tick_id is None:
        click.echo("No halted ticks found.", err=True)
        sys.exit(4)
    _check_tick_id(tick_id)
    try:
        signal = OperatorDiagnosticsReader(universe, tick_id).yield_signal()
    except FileNotFoundError:
        click.echo(f"No yield signal for tick {tick_id}.", err=True)
        sys.exit(4)
    if output_format == "json":
        click.echo(render_yield_json(signal))
    else:
        click.echo(render_yield_human(signal))


# --------------------------------------------------------------------------- #
# resume-tick
# --------------------------------------------------------------------------- #


@cli.command("resume-tick")
@click.argument("universe_slug", required=False)
@click.option("--tick", "tick_id", required=True, help="Tick id to resume.")
def resume_tick_cmd(universe_slug: str | None, tick_id: str) -> None:
    """Resume a manually-authored tick via the ``resume_tick`` MCP tool.

    Thin wrapper: opens a short one-shot Agent SDK session with only the
    token-world MCP server + ``resume_tick`` tool allowed. No authoring
    surface; for drain-and-author workflows use :command:`run-tick`.
    """
    universe = _cli_resolve_or_exit(universe_slug, exit_code=2)
    _check_tick_id(tick_id)
    try:
        asyncio.run(_invoke_resume_tick_mcp(universe, tick_id))
    except Exception as e:
        click.echo(f"Resume failed: {e}", err=True)
        sys.exit(1)
    click.echo(f"Resumed tick {tick_id}")


# --------------------------------------------------------------------------- #
# replay-tick
# --------------------------------------------------------------------------- #


@cli.command("replay-tick")
@click.argument("universe_slug_or_tick_id")
@click.argument("tick_id", required=False)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json"]),
    default="human",
    show_default=True,
)
def replay_tick(
    universe_slug_or_tick_id: str,
    tick_id: str | None,
    output_format: str,
) -> None:
    """Render the full operator diagnostics namespace for a tick.

    Two calling forms:

    - ``replay-tick <slug> <tick_id>`` — explicit universe slug.
    - ``replay-tick <tick_id>`` — universe via env / cwd.
    """
    # Disambiguate: one positional = tick_id; two = slug + tick_id.
    if tick_id is None:
        slug_or_none: str | None = None
        actual_tick_id = universe_slug_or_tick_id
    else:
        slug_or_none = universe_slug_or_tick_id
        actual_tick_id = tick_id

    universe = _cli_resolve_or_exit(slug_or_none, exit_code=2)
    _check_tick_id(actual_tick_id)

    op_dir = universe / "diagnostics" / f"tick_{actual_tick_id}" / "operator"
    if not op_dir.is_dir():
        click.echo(f"No operator session for tick {actual_tick_id}.", err=True)
        sys.exit(4)

    reader = OperatorDiagnosticsReader(universe, actual_tick_id)
    if output_format == "json":
        click.echo(render_replay_json(reader))
    else:
        click.echo(render_replay_human(reader))


# --------------------------------------------------------------------------- #
# agent-turn  (Phase 06 Plan 01 — D-22, D-29)
# --------------------------------------------------------------------------- #


@cli.command("agent-turn")
@click.argument("slug")
@click.option(
    "--agent-id",
    default=None,
    help="Existing agent id; auto-created if omitted and no agent exists (D-29).",
)
@click.option(
    "--no-operator",
    is_flag=True,
    default=False,
    help="Do not invoke OperatorHarness on yield.",
)
def agent_turn(slug: str, agent_id: str | None, no_operator: bool) -> None:
    """Run one agent turn interactively: agent generates action -> engine -> print observation.

    If no agent exists in the universe, one is auto-created with a random personality
    (D-29). The universe's CLAUDE.md world-rules text is used as the agent's system
    prompt context (D-04). Memory is persisted to universe.db after each turn (D-05).
    """
    # (a) Load universe path
    manager = UniverseManager()
    try:
        universe_dir = manager.load(slug)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e

    # (b) Load graph
    kg = KnowledgeGraph(db_path=universe_dir / "universe.db")
    kg.load()

    # (c) Load world rules from universe's CLAUDE.md
    claude_md = universe_dir / "CLAUDE.md"
    world_rules = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""

    # (d) Anthropic client
    client = anthropic.Anthropic()  # type: ignore[attr-defined]

    # (e-f) Memory + sessions adapters
    db_path = universe_dir / "universe.db"
    memory = AgentMemory(db_path)
    sessions = SessionManager(db_path)

    session_id: str

    # (g-h) Resolve or auto-create agent
    if agent_id is None:
        existing_agents = sessions.list_agents()
        if not existing_agents:
            # Auto-create: generate personality, create graph node, start session
            universe_desc = world_rules.split("\n")[0] or "a fantasy world"
            personality = PersonalityGenerator().generate(universe_desc, client=client)
            agent_id = kg.claim_id("resident")
            create_agent_node(kg, agent_id, personality)
            session_id = sessions.create_session(agent_id, personality)
        else:
            agent_id = existing_agents[0]
            existing_sessions = sessions.list_sessions(agent_id)
            session_id = existing_sessions[-1]  # most recent
    else:
        existing_sessions = sessions.list_sessions(agent_id)
        if not existing_sessions:
            click.echo(f"Error: no sessions found for agent '{agent_id}'", err=True)
            raise SystemExit(1)
        session_id = existing_sessions[-1]

    # (i) Load personality from session
    session_row = sessions.get_session(session_id)
    if session_row and session_row.get("agent_personality"):
        personality = PersonalityBundle.model_validate_json(session_row["agent_personality"])
    else:
        # Fallback: personality is stored on graph node
        node_props = kg.query(agent_id)
        personality = PersonalityBundle.model_validate(node_props.get("personality", {}))

    # (j) Construct agent
    agent = ResidentAgent(
        agent_id=agent_id,
        session_id=session_id,
        personality=personality,
        memory=memory,
        client=client,
        world_rules=world_rules,
    )

    # (k) Generate action
    action = agent.run_turn()

    # (l-m) Run engine tick
    engine = SimulationEngine(universe_dir, graph=kg, anthropic_client=client)
    result = engine.run_tick(action, actor=agent_id)

    # (n) Handle yield via OperatorHarness
    if result.kind == "yielded" and not no_operator:
        harness = OperatorHarness(universe_dir)
        asyncio.run(harness.handle_yield(result.yield_signal))
        # Resume tick after mechanic was authored
        result = engine.run_tick(action, actor=agent_id)

    # (o) Persist turn to memory
    turn_number = sessions.get_next_turn_number(session_id)
    memory.store_turn(
        agent_id,
        session_id,
        turn_number,
        action,
        result.observation or "",
        result.tick_id,
    )
    memory.maybe_compact_summary(session_id, client)

    # (p) Save graph
    kg.save()

    # (q) Print output
    click.echo(f"Agent ({agent_id}): {action}\n\nObservation:\n{result.observation}")
    if result.kind == "refused":
        click.echo(f"(refused: {result.refusal_reason})")
