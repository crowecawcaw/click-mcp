"""
Test CLI example for integration tests.
"""

import sys
import os

# Add parent directory to path so we can import click_mcp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import click
from click_mcp import click_mcp


@click_mcp
@click.group()
def cli():
    """Test CLI application."""
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
@click.option("--count", type=int, default=1, help="Number of times to repeat")
@click.option("--message", required=True, help="Message to echo")
def echo(count, message):
    """Echo a message multiple times."""
    for _ in range(count):
        click.echo(message)


if __name__ == "__main__":
    cli()
