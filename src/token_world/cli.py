"""Click CLI entry point for Token World."""

from __future__ import annotations

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
