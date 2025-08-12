#!/usr/bin/env python3
"""
Test CLI for hierarchical commands with Click context passing.

This CLI has a parent command that sets ctx.obj and child commands
that access that context, demonstrating hierarchical tool execution.
"""

import click
from click_mcp import click_mcp


@click_mcp(server_name="context-test-cli")
@click.group()
@click.option('--env', default='DEFAULT', help='Environment to use')
@click.pass_context
def parent(ctx, env):
    """Parent command that sets up context."""
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
@click.option('--child-flag', help='Child-specific flag')
@click.pass_context
def child_b(ctx, child_flag):
    """Child command B that should access parent context."""
    if ctx.obj is None:
        click.echo("Child B: ERROR - ctx.obj is None!")
        return
    
    env = ctx.obj.get('env', 'UNKNOWN')
    click.echo(f"Child B: Using env {env} with flag {child_flag}")


@parent.command()
@click.argument('message')
@click.pass_context
def child_c(ctx, message):
    """Child command C with argument that should access parent context."""
    if ctx.obj is None:
        click.echo("Child C: ERROR - ctx.obj is None!")
        return
    
    env = ctx.obj.get('env', 'UNKNOWN')
    click.echo(f"Child C: Message '{message}' in env {env}")


if __name__ == '__main__':
    parent()
