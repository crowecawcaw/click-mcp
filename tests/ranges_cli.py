import inspect
import json
from typing import Annotated

import click
import typer
from typer.main import get_command

from click_mcp import ToolAdapter, click_mcp


@click.group()
def cli():
    pass


@cli.command()
@click.option("--count", type=click.IntRange(1, 3), required=True)
@click.option("--ratio", type=click.FloatRange(-0.5, 1.5), required=True)
@click.option("--clamped", type=click.IntRange(1, 3, clamp=True), default=2)
@click.option(
    "--clamped-float", type=click.FloatRange(-0.5, 1.5, clamp=True), default=0.0
)
def bounded(count, ratio, clamped, clamped_float):
    click.echo(json.dumps([count, ratio, clamped, clamped_float]))


if "min_open" in inspect.signature(click.IntRange).parameters:

    @cli.command()
    @click.option("--count", type=click.IntRange(0, 4, min_open=True, max_open=True))
    @click.option("--ratio", type=click.FloatRange(0, 1, min_open=True, max_open=True))
    def opened(count, ratio):
        click.echo(json.dumps([count, ratio]))


click_mcp("ranges", cli)
click_mcp("ranges-strict", cli, command_name="mcp-strict", strict_arguments=True)
click_mcp(
    "ranges-adapted",
    cli,
    command_name="mcp-adapted",
    strict_arguments=True,
    command_metadata={
        "bounded": {
            "adapter": ToolAdapter(
                input_schema={
                    "type": "object",
                    "properties": {"value": {"type": "integer"}},
                },
                adapt_arguments=lambda args: {
                    "count": 1,
                    "ratio": 0,
                    "clamped": args["value"],
                },
            )
        }
    },
)

app = typer.Typer()


@app.callback()
def root():
    pass


@app.command()
def bounds(
    count: Annotated[int, typer.Option(min=1, max=3)],
    ratio: Annotated[float, typer.Option(min=-0.5, max=1.5)],
    clamped: Annotated[int, typer.Option(min=1, max=3, clamp=True)] = 2,
    clamped_float: Annotated[float, typer.Option(min=-0.5, max=1.5, clamp=True)] = 0.0,
):
    typer.echo(json.dumps([count, ratio, clamped, clamped_float]))


if __name__ == "__main__":
    import sys

    if sys.argv[1].startswith("typer-"):
        group = get_command(app)
        click_mcp("typer-ranges", group, command_name="typer-mcp")
        click_mcp(
            "typer-ranges", group, command_name="typer-strict", strict_arguments=True
        )
        group()
    else:
        cli()
