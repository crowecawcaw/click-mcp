"""
Custom server name CLI example for integration tests.
"""

import os
import sys

# Add parent directory to path so we can import click_mcp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import click

from click_mcp import click_mcp


@click_mcp(command_name="mcp", server_name="custom-server-name")
@click.group()
def cli():
    """CLI with custom server name."""
    pass


@cli.command()
@click.option("--name", required=True, help="Name to greet")
def greet(name):
    """Greet someone."""
    click.echo(f"Hello, {name}!")


if __name__ == "__main__":
    cli()
