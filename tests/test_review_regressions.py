import json
from pathlib import Path

import click
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from jsonschema import validate

from click_mcp.server import MCPServer
from tests.test_mcp_server import anyio_backend, mcp_server_client  # noqa: F401


@pytest.mark.anyio
async def test_server_local_allowlists_and_custom_main_over_stdio():
    script = Path(__file__).with_name("review_cli.py")
    async with mcp_server_client(script, "mcp-first") as first:
        assert [tool.name for tool in (await first.list_tools()).tools] == ["shared"]
        result = await first.call_tool("shared", {})
        assert result.content[0].text == "first invocation 2"
    async with mcp_server_client(script, "mcp-second") as second:
        assert [tool.name for tool in (await second.list_tools()).tools] == ["status"]
        assert (await second.call_tool("status", {})).content[0].text == "second ready"


def test_duplicate_parameter_bindings_fail_during_startup():
    @click.group()
    @click.option("--format", type=click.Choice(["plain", "short"]))
    def root(format):
        pass

    @root.command()
    @click.option("--format", type=click.Choice(["json", "yaml"]))
    def render(format):
        pass

    with pytest.raises(ValueError, match="root_render.*format.*more than once"):
        MCPServer(root)


# Model the protocol's JSON strings directly. This exercises the real Click
# parser repeatedly without paying for an MCP subprocess per generated example.
cli_text = st.one_of(
    st.sampled_from(["", "-", "--", "--tag", "-1", "a=b", "two words", "雪"]),
    st.text(alphabet=st.characters(exclude_categories=("Cs",)), max_size=30),
)


@settings(max_examples=100)
@given(
    message=cli_text,
    tags=st.lists(cli_text, min_size=1, max_size=5),
    pair=st.tuples(st.integers(min_value=-100, max_value=100), cli_text),
)
def test_advertised_values_round_trip_through_click(message, tags, pair):
    @click.group()
    def root():
        pass

    @root.command()
    @click.argument("message")
    @click.option("--tag", "tags", multiple=True, required=True)
    @click.option("--pair", type=(int, str), required=True)
    def collect(message, tags, pair):
        click.echo(json.dumps([message, tags, pair]))

    server = MCPServer(root)
    [tool] = server.click_tools
    arguments = {"message": message, "tags": tags, "pair": list(pair)}
    validate(arguments, tool.input_schema)
    result = server._execute_command(tool.name, arguments)
    assert json.loads(result["output"]) == [message, tags, list(pair)]
