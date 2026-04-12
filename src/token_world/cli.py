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
        raise SystemExit(1)


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
        raise SystemExit(1)
