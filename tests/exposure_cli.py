"""A CLI with an explicit MCP allowlist and several unexposed commands."""

import click

from click_mcp import click_mcp
from click_mcp.decorator import register_mcp_metadata


@click.group()
def cli():
    pass


@cli.group()
def users():
    pass


@cli.group()
def projects():
    pass


@users.command("list")
def list_users():
    click.echo("Users")


@projects.command("list")
def list_projects():
    click.echo("Projects")


@projects.command()
def delete():
    click.echo("Deleting a project")


@projects.command(hidden=True)
def repair():
    click.echo("Repairing a project")


@cli.group(hidden=True)
def admin():
    pass


@admin.command()
def status():
    click.echo("Admin status")


users.add_command(list_users, "ls")
cli.add_command(admin, "internal")
register_mcp_metadata(
    "users.list", {"include": True, "annotations": {"readOnlyHint": True}}
)
register_mcp_metadata(
    "projects.list",
    {"include": True, "name": "browse", "annotations": {"title": "Browse projects"}},
)
register_mcp_metadata("projects.repair", {"include": True})
register_mcp_metadata("internal.status", {"include": True})
click_mcp("inventory", cli, include_all_commands=False)
click_mcp("inventory", cli, command_name="mcp-hidden", include_hidden=True)
click_mcp("inventory", cli, command_name="mcp-visible")


if __name__ == "__main__":
    cli()
