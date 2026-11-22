from pathlib import Path

import pytest

from tests.test_mcp_server import anyio_backend, mcp_server_client  # noqa: F401

SCRIPT = Path(__file__).with_name("typer_cli.py")


@pytest.mark.anyio
async def test_typer_nested_tool_schema_and_invocation():
    async with mcp_server_client(SCRIPT) as session:
        [tool] = (await session.list_tools()).tools
        assert tool.name == "teams_members_show"
        assert tool.description == "Show a member's directory entry."
        assert tool.input_schema == {
            "type": "object",
            "required": ["member_id"],
            "properties": {
                "member_id": {"type": "integer", "description": "Directory ID"},
                "limit": {
                    "type": "integer",
                    "description": "Maximum rows",
                    "default": 3,
                },
                "active": {"type": "boolean", "default": True},
                "mode": {
                    "type": "string",
                    "enum": ["short", "full"],
                    "default": "short",
                },
            },
        }

        invalid = await session.call_tool(tool.name, {"member_id": 8, "limit": 0})
        assert invalid.is_error
        assert "--limit" in invalid.content[0].text
        assert "Invalid command arguments" in invalid.content[0].text

        defaults = await session.call_tool(tool.name, {"member_id": 8})
        assert not defaults.is_error
        assert defaults.content[0].text == "8:3:True:short"
        explicit = await session.call_tool(
            tool.name, {"member_id": 8, "limit": 2, "active": False, "mode": "full"}
        )
        assert not explicit.is_error
        assert explicit.content[0].text == "8:2:False:full"


@pytest.mark.anyio
async def test_typer_hidden_command_exit():
    async with mcp_server_client(SCRIPT, "mcp-hidden") as session:
        tool = "teams_members_maintenance"
        assert tool in {item.name for item in (await session.list_tools()).tools}
        result = await session.call_tool(tool, {})
        assert result.is_error
        assert result.content[0].text == "Command exited with code 4"
