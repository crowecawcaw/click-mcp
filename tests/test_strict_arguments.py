from pathlib import Path

import click
import pytest

from click_mcp import ToolAdapter
from click_mcp.server import MCPServer, _ToolExecutionError
from tests.test_mcp_server import anyio_backend, mcp_server_client  # noqa: F401

CLI = Path(__file__).with_name("strict_arguments_cli.py")


@pytest.mark.anyio
async def test_strict_generated_arguments_over_stdio():
    async with mcp_server_client(CLI) as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}
        schema = tools["data_greet"].input_schema
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == {"workspace", "name", "count"}

        arguments = {"workspace": "test", "name": "Ada"}
        unknown = await session.call_tool(
            "data_greet", {**arguments, "coutn": 2, "zzz": True}
        )
        assert unknown.is_error
        assert unknown.content[0].text == (
            "Unknown tool arguments: 'coutn', 'zzz'. "
            "Valid arguments: 'count', 'name', 'workspace'."
        )

        wrong_type = await session.call_tool("data_greet", {**arguments, "count": "2"})
        assert wrong_type.is_error
        assert "$.count" in wrong_type.content[0].text
        assert "type" in wrong_type.content[0].text

        missing = await session.call_tool("data_greet", {"workspace": "test"})
        assert missing.is_error
        assert "required" in missing.content[0].text

        assert tools["status"].input_schema["additionalProperties"] is False
        unexpected = await session.call_tool("status", {"extra": True})
        assert unexpected.is_error
        assert "Valid arguments: (none)." in unexpected.content[0].text

        before = await session.call_tool("status", {})
        assert before.content[0].text == "0"

        valid = await session.call_tool("data_greet", {**arguments, "count": 2})
        assert not valid.is_error
        assert valid.content[0].text == "Ada Ada"
        after = await session.call_tool("status", {})
        assert after.content[0].text == "1"


@pytest.mark.anyio
async def test_default_arguments_still_use_click_coercion_and_ignore_extras():
    async with mcp_server_client(CLI, "mcp-default") as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}
        assert "additionalProperties" not in tools["data_greet"].input_schema
        result = await session.call_tool(
            "data_greet",
            {"workspace": "test", "name": "Ada", "count": "2", "extra": True},
        )
        assert not result.is_error
        assert result.content[0].text == "Ada Ada"


@pytest.mark.anyio
async def test_custom_schema_stays_authoritative_in_strict_mode():
    async with mcp_server_client(CLI, "mcp-adapted") as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}
        schema = tools["adapted"].input_schema
        assert set(schema["properties"]) == {"display"}
        assert "additionalProperties" not in schema

        valid = await session.call_tool("adapted", {"display": "Ada", "extra": True})
        assert not valid.is_error
        assert valid.content[0].text == "Ada"

        invalid = await session.call_tool("adapted", {"display": 123})
        assert invalid.is_error
        assert "$.display" in invalid.content[0].text


def test_strict_generated_inputs_are_validated_before_argument_adapter():
    adapted = []

    def adapt_arguments(arguments):
        adapted.append(arguments)
        return arguments

    @click.group()
    def root():
        pass

    @root.command()
    @click.option("--label", required=True)
    def show(label):
        click.echo(label)

    server = MCPServer(
        root,
        strict_arguments=True,
        command_metadata={
            "show": {"adapter": ToolAdapter(adapt_arguments=adapt_arguments)}
        },
    )
    route = server.routes["show"]

    with pytest.raises(_ToolExecutionError, match="Unknown tool arguments"):
        server._call_route(route, {"label": "Ada", "extra": True})
    assert adapted == []

    result = server._call_route(route, {"label": "Ada"})
    assert result.content[0].text == "Ada"
    assert adapted == [{"label": "Ada"}]
