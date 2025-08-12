#!/usr/bin/env python3
"""
Test CLI with custom MCP command name to verify it's properly excluded.
"""

import click
from click_mcp import click_mcp


@click_mcp(server_name="custom-mcp-cli", command_name="start-server")
@click.group()
@click.option('--env', default='DEFAULT', help='Environment to use')
@click.pass_context
def parent(ctx, env):
    """Parent command with custom MCP command name."""
    ctx.ensure_object(dict)
    ctx.obj['env'] = env
    click.echo(f"Parent: Setting env to {env}")


@parent.command()
@click.pass_context
def child_a(ctx):
    """Child command A that should access parent context."""
    if ctx.obj is None:
        click.echo("Child A: ERROR - ctx.obj is None!")
        return
    
    env = ctx.obj.get('env', 'UNKNOWN')
    click.echo(f"Child A: Using env {env}")


@parent.command()
def regular_command():
    """A regular command that should be exposed as a tool."""
    click.echo("Regular command executed")


if __name__ == '__main__':
    parent()
