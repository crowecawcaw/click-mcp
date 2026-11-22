import sys

import click

from click_mcp import click_mcp
from click_mcp.decorator import register_mcp_metadata


class CustomGroup(click.Group):
    def main(self, *args, **kwargs):
        self.invocations = getattr(self, "invocations", 0) + 1
        return super().main(*args, **kwargs)


@click.group(cls=CustomGroup)
def first():
    pass


@first.command()
def shared():
    click.echo(f"first invocation {first.invocations}")


@click.group()
def second():
    pass


@second.command("shared")
def second_shared():
    click.echo("second shared")


@second.command()
def status():
    click.echo("second ready")


register_mcp_metadata("shared", {"include": True, "name": "legacy_shared"})
click_mcp(
    "first",
    first,
    include_all_commands=False,
    command_metadata={("shared",): {"include": True}},
)
click_mcp(
    "second",
    second,
    include_all_commands=False,
    command_metadata={"status": {"include": True}},
)


if __name__ == "__main__":
    app = first if sys.argv[1] == "mcp-first" else second
    app(["mcp"])
