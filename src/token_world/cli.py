"""Click CLI entry point for Token World."""

from __future__ import annotations

import json as _json
from pathlib import Path

import click

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

    report = validate(module_path)

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
