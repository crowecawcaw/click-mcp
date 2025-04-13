"""
Basic CLI example for integration tests.
"""

import os
import sys

# Add parent directory to path so we can import click_mcp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import click

from click_mcp import click_mcp


@click_mcp(server_name="basic-cli")
@click.group()
def cli():
    """Basic CLI application."""
    pass


@cli.command()
@click.option("--name", required=True, help="Name to greet")
def greet(name):
    """Greet someone with a friendly message."""
    click.echo(f"Hello, {name}!")


@cli.group()
def users():
    """User management commands."""
    pass


@users.command()
def list():
    """List all users in the system."""
    click.echo("User1\nUser2\nUser3")


@cli.command()
@click.option("--message", required=True, help="Message to echo")
@click.option("--count", type=int, default=1, help="Number of times to echo")
def echo(message, count):
    """Echo a message multiple times."""
    click.echo("\n".join([message] * count))


if __name__ == "__main__":
    cli()
