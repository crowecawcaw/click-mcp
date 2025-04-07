"""
Advanced CLI example for integration tests.
"""

import sys
import os

# Add parent directory to path so we can import click_mcp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import click
from click_mcp import click_mcp


@click_mcp(command_name="start-mcp", include_all_commands=False)
@click.group()
def cli():
    """Advanced CLI application."""
    pass


@cli.command()
@click_mcp.command(include=True, name="say-hello")
@click.option("--name", required=True, help="Name to greet")
def greet(name):
    """Greet someone with a custom command name."""
    click.echo(f"Hello, {name}!")


@cli.command()
@click_mcp.command(include=False)
def hidden():
    """This command should not be exposed in MCP."""
    click.echo("Hidden command")


@cli.group()
@click_mcp.command(include=True, name="api")
def endpoints():
    """API endpoints with a custom group name."""
    pass


@endpoints.command()
def list():
    """List all API endpoints."""
    click.echo("Endpoint1\nEndpoint2")


if __name__ == "__main__":
    cli()
