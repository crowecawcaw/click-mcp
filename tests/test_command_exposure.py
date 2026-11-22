from pathlib import Path

import pytest

from tests.test_mcp_server import anyio_backend, mcp_server_client  # noqa: F401

SCRIPT = Path(__file__).with_name("exposure_cli.py")


@pytest.mark.anyio
async def test_path_metadata_and_allowlist():
    async with mcp_server_client(SCRIPT) as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}
        assert set(tools) == {"users_list", "projects_browse"}
        assert tools["users_list"].annotations.read_only_hint is True
        assert tools["projects_browse"].annotations.title == "Browse projects"
        assert (await session.call_tool("users_list", {})).content[0].text == "Users"
        assert (await session.call_tool("projects_browse", {})).content[
            0
        ].text == "Projects"
        assert (await session.call_tool("projects_delete", {})).is_error


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("command", "hidden_tools"),
    [
        ("mcp-visible", set()),
        ("mcp-hidden", {"projects_repair", "admin_status", "internal_status"}),
    ],
)
async def test_hidden_commands_groups_and_aliases(command, hidden_tools):
    async with mcp_server_client(SCRIPT, command) as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}
        assert (
            set(tools)
            == {
                "users_list",
                "users_ls",
                "projects_browse",
                "projects_delete",
            }
            | hidden_tools
        )
        assert tools["users_ls"].annotations is None
        assert (await session.call_tool("users_ls", {})).content[0].text == "Users"
        if hidden_tools:
            assert (await session.call_tool("internal_status", {})).content[
                0
            ].text == "Admin status"
