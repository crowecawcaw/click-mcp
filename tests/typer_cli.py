from enum import Enum
from typing import Annotated

import typer
from typer.main import get_command

from click_mcp import click_mcp

app = typer.Typer()
teams = typer.Typer()
members = typer.Typer()
app.add_typer(teams, name="teams")
teams.add_typer(members, name="members")


class Mode(str, Enum):
    SHORT = "short"
    FULL = "full"


@app.callback()
def root():
    """Team directory."""


@members.command()
def show(
    member_id: Annotated[int, typer.Argument(help="Directory ID")],
    limit: Annotated[int, typer.Option(help="Maximum rows", min=1)] = 3,
    active: bool = True,
    mode: Mode = Mode.SHORT,
):
    """Show a member's directory entry."""
    typer.echo(f"{member_id}:{limit}:{active}:{mode.value}")


@members.command(hidden=True)
def maintenance():
    raise typer.Exit(4)


if __name__ == "__main__":
    group = get_command(app)
    click_mcp("typer-directory", group)
    click_mcp("typer-directory", group, command_name="mcp-hidden", include_hidden=True)
    group()
