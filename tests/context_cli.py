#!/usr/bin/env python3
"""
Test CLI for hierarchical commands with Click context passing.

This CLI has multiple levels of nesting with context passing at each level,
demonstrating deeply nested hierarchical tool execution.
"""

import click
from click_mcp import click_mcp


@click_mcp(server_name="context-test-cli")
@click.group()
@click.option('--env', default='DEFAULT', help='Environment to use')
@click.option('--debug/--no-debug', default=False, help='Enable debug mode')
@click.option('--config', help='Configuration file path')
@click.pass_context
def parent(ctx, env, debug, config):
    """Parent command that sets up context."""
    ctx.ensure_object(dict)
    ctx.obj['env'] = env
    ctx.obj['debug'] = debug
    ctx.obj['config'] = config
    click.echo(f"Parent: Setting env={env}, debug={debug}, config={config}")


@parent.command()
@click.pass_context
def child_a(ctx):
    """Child command A that should access parent context."""
    if ctx.obj is None:
        click.echo("Child A: ERROR - ctx.obj is None!")
        return
    
    env = ctx.obj.get('env', 'UNKNOWN')
    debug = ctx.obj.get('debug', False)
    click.echo(f"Child A: Using env={env}, debug={debug}")


@parent.command()
@click.option('--child-flag', help='Child-specific flag')
@click.pass_context
def child_b(ctx, child_flag):
    """Child command B that should access parent context."""
    if ctx.obj is None:
        click.echo("Child B: ERROR - ctx.obj is None!")
        return
    
    env = ctx.obj.get('env', 'UNKNOWN')
    debug = ctx.obj.get('debug', False)
    click.echo(f"Child B: Using env={env}, debug={debug}, flag={child_flag}")


@parent.command()
@click.argument('message')
@click.pass_context
def child_c(ctx, message):
    """Child command C with argument that should access parent context."""
    if ctx.obj is None:
        click.echo("Child C: ERROR - ctx.obj is None!")
        return
    
    env = ctx.obj.get('env', 'UNKNOWN')
    config = ctx.obj.get('config', 'none')
    click.echo(f"Child C: Message '{message}' in env={env}, config={config}")


# Level 2 nesting: users group with its own parameters
@parent.group()
@click.option('--database', default='main', help='Database to use')
@click.option('--timeout', type=int, default=30, help='Query timeout')
@click.pass_context
def users(ctx, database, timeout):
    """User management commands with database context."""
    if ctx.obj is None:
        ctx.ensure_object(dict)
    ctx.obj['database'] = database
    ctx.obj['timeout'] = timeout
    env = ctx.obj.get('env', 'UNKNOWN')
    click.echo(f"Users: database={database}, timeout={timeout}, env={env}")


@users.command()
@click.argument('username')
@click.option('--role', default='user', help='User role')
@click.pass_context
def create(ctx, username, role):
    """Create a new user."""
    if ctx.obj is None:
        click.echo("Create: ERROR - ctx.obj is None!")
        return
    
    env = ctx.obj.get('env', 'UNKNOWN')
    database = ctx.obj.get('database', 'unknown')
    timeout = ctx.obj.get('timeout', 0)
    debug = ctx.obj.get('debug', False)
    click.echo(f"Create: user={username}, role={role}, db={database}, timeout={timeout}, env={env}, debug={debug}")


@users.command()
@click.argument('username')
@click.option('--force', is_flag=True, help='Force deletion')
@click.pass_context
def delete(ctx, username, force):
    """Delete a user."""
    if ctx.obj is None:
        click.echo("Delete: ERROR - ctx.obj is None!")
        return
    
    env = ctx.obj.get('env', 'UNKNOWN')
    database = ctx.obj.get('database', 'unknown')
    config = ctx.obj.get('config', 'none')
    click.echo(f"Delete: user={username}, force={force}, db={database}, env={env}, config={config}")


# Level 3 nesting: permissions group under users
@users.group()
@click.option('--scope', default='global', help='Permission scope')
@click.option('--audit/--no-audit', default=True, help='Enable audit logging')
@click.pass_context
def permissions(ctx, scope, audit):
    """Permission management commands."""
    if ctx.obj is None:
        ctx.ensure_object(dict)
    ctx.obj['scope'] = scope
    ctx.obj['audit'] = audit
    database = ctx.obj.get('database', 'unknown')
    env = ctx.obj.get('env', 'UNKNOWN')
    click.echo(f"Permissions: scope={scope}, audit={audit}, db={database}, env={env}")


@permissions.command()
@click.argument('username')
@click.argument('permission')
@click.option('--expires', help='Expiration date')
@click.pass_context
def grant(ctx, username, permission, expires):
    """Grant permission to user."""
    if ctx.obj is None:
        click.echo("Grant: ERROR - ctx.obj is None!")
        return
    
    # Access all levels of context
    env = ctx.obj.get('env', 'UNKNOWN')
    debug = ctx.obj.get('debug', False)
    config = ctx.obj.get('config', 'none')
    database = ctx.obj.get('database', 'unknown')
    timeout = ctx.obj.get('timeout', 0)
    scope = ctx.obj.get('scope', 'unknown')
    audit = ctx.obj.get('audit', False)
    
    click.echo(f"Grant: user={username}, perm={permission}, expires={expires}")
    click.echo(f"  Context: env={env}, debug={debug}, config={config}")
    click.echo(f"  Database: db={database}, timeout={timeout}")
    click.echo(f"  Permissions: scope={scope}, audit={audit}")


@permissions.command()
@click.argument('username')
@click.argument('permission')
@click.option('--reason', help='Revocation reason')
@click.pass_context
def revoke(ctx, username, permission, reason):
    """Revoke permission from user."""
    if ctx.obj is None:
        click.echo("Revoke: ERROR - ctx.obj is None!")
        return
    
    # Access all levels of context
    env = ctx.obj.get('env', 'UNKNOWN')
    database = ctx.obj.get('database', 'unknown')
    scope = ctx.obj.get('scope', 'unknown')
    audit = ctx.obj.get('audit', False)
    
    click.echo(f"Revoke: user={username}, perm={permission}, reason={reason}")
    click.echo(f"  Context: env={env}, db={database}, scope={scope}, audit={audit}")


# Level 2 nesting: projects group with different parameters
@parent.group()
@click.option('--workspace', default='default', help='Workspace name')
@click.option('--version', help='API version')
@click.pass_context
def projects(ctx, workspace, version):
    """Project management commands."""
    if ctx.obj is None:
        ctx.ensure_object(dict)
    ctx.obj['workspace'] = workspace
    ctx.obj['version'] = version
    env = ctx.obj.get('env', 'UNKNOWN')
    debug = ctx.obj.get('debug', False)
    click.echo(f"Projects: workspace={workspace}, version={version}, env={env}, debug={debug}")


@projects.command()
@click.argument('name')
@click.option('--template', help='Project template')
@click.pass_context
def create_project(ctx, name, template):
    """Create a new project."""
    if ctx.obj is None:
        click.echo("CreateProject: ERROR - ctx.obj is None!")
        return
    
    env = ctx.obj.get('env', 'UNKNOWN')
    workspace = ctx.obj.get('workspace', 'unknown')
    version = ctx.obj.get('version', 'none')
    config = ctx.obj.get('config', 'none')
    click.echo(f"CreateProject: name={name}, template={template}")
    click.echo(f"  Context: workspace={workspace}, version={version}, env={env}, config={config}")


if __name__ == '__main__':
    parent()
