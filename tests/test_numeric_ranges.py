import inspect
import json
from pathlib import Path
from typing import Annotated

import click
import pytest
import typer
from click.testing import CliRunner
from typer.main import get_command

from click_mcp.compat import parameter_value_schema
from tests.ranges_cli import cli
from tests.test_mcp_server import anyio_backend, mcp_server_client  # noqa: F401

SCRIPT = Path(__file__).with_name("ranges_cli.py")
OPEN_BOUNDS = "min_open" in inspect.signature(click.IntRange).parameters


@pytest.mark.parametrize("command", ["mcp", "mcp-strict", "typer-mcp", "typer-strict"])
@pytest.mark.anyio
async def test_numeric_bounds_over_stdio(command):
    name = "bounds" if command.startswith("typer") else "bounded"
    async with mcp_server_client(SCRIPT, command) as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}
        schema = tools[name].input_schema
        props = schema["properties"]
        assert props["count"] == {"type": "integer", "minimum": 1, "maximum": 3}
        assert props["ratio"] == {"type": "number", "minimum": -0.5, "maximum": 1.5}
        assert props["clamped"] == {"type": "integer", "default": 2}
        assert props["clamped_float"] == {"type": "number", "default": 0.0}
        assert schema.get("additionalProperties") is (
            False if "strict" in command else None
        )
        for count, ratio, clamped, clamped_float in [
            (1, -0.5, -10, -10),
            (3, 1.5, 10, 10),
        ]:
            result = await session.call_tool(
                name,
                dict(
                    count=count,
                    ratio=ratio,
                    clamped=clamped,
                    clamped_float=clamped_float,
                ),
            )
            assert not result.is_error
            assert json.loads(result.content[0].text) == [count, ratio, count, ratio]
        for invalid in [
            {"count": 0, "ratio": 0},
            {"count": 4, "ratio": 0},
            {"count": 2, "ratio": -0.6},
            {"count": 2, "ratio": 1.6},
        ]:
            result = await session.call_tool(name, invalid)
            assert result.is_error
        if "strict" not in command:
            result = await session.call_tool(
                name, {"count": "1", "ratio": "0", "extra": True}
            )
            assert not result.is_error


@pytest.mark.skipif(not OPEN_BOUNDS, reason="Click 7.0 has no open ranges")
@pytest.mark.parametrize("command", ["mcp", "mcp-strict"])
@pytest.mark.anyio
async def test_exclusive_bounds_over_stdio(command):
    async with mcp_server_client(SCRIPT, command) as session:
        tool = next(
            tool for tool in (await session.list_tools()).tools if tool.name == "opened"
        )
        assert tool.input_schema["properties"] == {
            "count": {"type": "integer", "exclusiveMinimum": 0, "exclusiveMaximum": 4},
            "ratio": {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1},
        }
        for count, ratio in [(1, 0.1), (3, 0.9)]:
            result = await session.call_tool("opened", {"count": count, "ratio": ratio})
            assert not result.is_error
        for count, ratio in [(0, 0.5), (4, 0.5), (1, 0), (1, 1)]:
            assert (
                await session.call_tool("opened", {"count": count, "ratio": ratio})
            ).is_error


@pytest.mark.anyio
async def test_range_adapter_schema_precedence():
    async with mcp_server_client(SCRIPT, "mcp-adapted") as session:
        tool = next(
            tool
            for tool in (await session.list_tools()).tools
            if tool.name == "bounded"
        )
        assert tool.input_schema == {
            "type": "object",
            "properties": {"value": {"type": "integer"}},
        }
        result = await session.call_tool("bounded", {"value": 100})
        assert not result.is_error
        assert json.loads(result.content[0].text) == [1, 0, 3, 0]


@pytest.mark.parametrize(
    "range_type,json_type", [(click.IntRange, "integer"), (click.FloatRange, "number")]
)
@pytest.mark.parametrize("low,high", [(None, None), (0, None), (None, 0), (-2, 2)])
def test_optional_bounds(range_type, json_type, low, high):
    expected = {"type": json_type}
    if low is not None:
        expected["minimum"] = low
    if high is not None:
        expected["maximum"] = high
    assert (
        parameter_value_schema(click.Option(["--value"], type=range_type(low, high)))
        == expected
    )


def test_click_collection_bounds():
    bounded = click.IntRange(1, 3)
    item = {"type": "integer", "minimum": 1, "maximum": 3}
    assert parameter_value_schema(
        click.Argument(["values"], type=bounded, nargs=-1)
    ) == {"type": "array", "items": item}
    assert parameter_value_schema(
        click.Option(["--pair"], type=(bounded, click.FloatRange(max=0)))
    ) == {
        "type": "array",
        "prefixItems": [item, {"type": "number", "maximum": 0}],
        "minItems": 2,
        "maxItems": 2,
    }
    assert parameter_value_schema(click.Option(["--pair"], type=bounded, nargs=2)) == {
        "type": "array",
        "items": item,
        "minItems": 2,
        "maxItems": 2,
    }


def test_typer_collection_bounds():
    app = typer.Typer()

    @app.command()
    def collect(
        values: Annotated[list[int], typer.Option(min=1, max=3)],
        pair: Annotated[tuple[int, float], typer.Option(min=0)],
    ):
        pass

    params = {param.name: param for param in get_command(app).params}
    assert parameter_value_schema(params["values"]) == {
        "type": "integer",
        "minimum": 1,
        "maximum": 3,
    }
    assert parameter_value_schema(params["pair"]) == {
        "type": "array",
        "prefixItems": [
            {"type": "integer", "minimum": 0},
            {"type": "number", "minimum": 0},
        ],
        "minItems": 2,
        "maxItems": 2,
    }


def test_normal_cli_range_behavior():
    runner = CliRunner()
    result = runner.invoke(
        cli, ["bounded", "--count", "1", "--ratio", "-0.5", "--clamped", "100"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output) == [1, -0.5, 3, 0]
    assert (
        runner.invoke(cli, ["bounded", "--count", "0", "--ratio", "0"]).exit_code == 2
    )
