import click

from click_mcp import ToolAdapter, click_mcp

invocations = 0


@click_mcp("arguments-strict", strict_arguments=True)
@click.group()
def cli():
    pass


@cli.group()
@click.option("--workspace", required=True)
def data(workspace):
    pass


@data.command()
@click.argument("name")
@click.option("--count", type=int, default=1)
def greet(name, count):
    global invocations
    invocations += 1
    click.echo(" ".join([name] * count))


@cli.command()
def status():
    click.echo(invocations)


@cli.command()
@click.option("--label", required=True)
def adapted(label):
    click.echo(label)


click_mcp("arguments-default", cli, command_name="mcp-default")
click_mcp(
    "arguments-adapted",
    cli,
    command_name="mcp-adapted",
    strict_arguments=True,
    command_metadata={
        "adapted": {
            "adapter": ToolAdapter(
                input_schema={
                    "type": "object",
                    "properties": {"display": {"type": "string"}},
                    "required": ["display"],
                },
                adapt_arguments=lambda args: {"label": args["display"]},
            )
        }
    },
)


if __name__ == "__main__":
    cli()
