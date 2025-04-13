import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Tuple

import pytest
from mcp import ClientSession, StdioServerParameters, stdio_client


@asynccontextmanager
async def mcp_server_client(
    script_path: Path, command_name: str = "mcp"
) -> Generator[Tuple[subprocess.Popen, Any, List[Dict]], None, None]:
    server_params = StdioServerParameters(
        command=sys.executable,  # Executable
        args=[str(script_path), command_name],  # Optional command line arguments
        env=None,  # Optional environment variables
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read,
            write,
        ) as session:
            await session.initialize()
            yield session


@pytest.fixture(params=["asyncio"])
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def basic_mcp_session(request):
    """Fixture that provides an MCP server context for the basic CLI."""
    script_path = Path(__file__).parent / "basic_cli.py"
    async with mcp_server_client(script_path, "mcp") as session:
        yield session


@pytest.fixture
async def advanced_mcp_session(request):
    """Fixture that provides an MCP server context for the advanced CLI."""
    script_path = Path(__file__).parent / "advanced_cli.py"
    async with mcp_server_client(script_path, "start-mcp") as session:
        yield session


@pytest.mark.anyio
async def test_basic_server_tools(basic_mcp_session):
    """Test that the basic MCP server returns correct tools."""
    result = await basic_mcp_session.list_tools()

    # Check that we have tools
    assert result is not None
    assert hasattr(result, "tools")
    tools = result.tools
    assert len(tools) > 0

    # Find the greet command
    greet_tool = None
    for tool in tools:
        if "greet" in tool.name.lower():
            greet_tool = tool
            break

    assert greet_tool is not None
    assert "name" in greet_tool.inputSchema
    assert greet_tool.inputSchema["name"]["required"] is True

    # Find the users.list command
    users_list_tool = None
    for tool in tools:
        if "users.list" in tool.name.lower():
            users_list_tool = tool
            break

    assert users_list_tool is not None

    # Find the echo command
    echo_tool = None
    for tool in tools:
        if "echo" in tool.name.lower():
            echo_tool = tool
            break

    assert echo_tool is not None
    assert "count" in echo_tool.inputSchema
    assert echo_tool.inputSchema["count"]["schema"]["type"] == "integer"
    assert "message" in echo_tool.inputSchema


@pytest.mark.anyio
async def test_invoke_greet_command(basic_mcp_session):
    """Test invoking the greet command."""
    # Get tools
    result = await basic_mcp_session.list_tools()
    tools = result.tools

    # Find the greet command
    greet_tool = None
    for tool in tools:
        if "greet" in tool.name.lower():
            greet_tool = tool
            break

    assert greet_tool is not None

    # Invoke the command
    result = await basic_mcp_session.call_tool(greet_tool.name, {"name": "World"})

    assert result is not None
    assert len(result.content) > 0
    assert result.content[0].text == "Hello, World!"


@pytest.mark.anyio
async def test_invoke_users_list_command(basic_mcp_session):
    """Test invoking the users.list command."""
    # Get tools
    result = await basic_mcp_session.list_tools()
    tools = result.tools

    # Find the users.list command
    users_list_tool = None
    for tool in tools:
        if "users.list" in tool.name.lower():
            users_list_tool = tool
            break

    assert users_list_tool is not None

    # Invoke the command
    result = await basic_mcp_session.call_tool(users_list_tool.name, {})

    assert result is not None
    assert len(result.content) > 0
    assert "User1\nUser2\nUser3" in result.content[0].text


@pytest.mark.anyio
async def test_invoke_echo_command(basic_mcp_session):
    """Test invoking the echo command with different parameters."""
    # Get tools
    result = await basic_mcp_session.list_tools()
    tools = result.tools

    # Find the echo command
    echo_tool = None
    for tool in tools:
        if "echo" in tool.name.lower():
            echo_tool = tool
            break

    assert echo_tool is not None

    # Test with default count
    result = await basic_mcp_session.call_tool(echo_tool.name, {"message": "Hello"})
    assert result is not None
    assert len(result.content) > 0
    assert result.content[0].text == "Hello"

    # Test with custom count
    result = await basic_mcp_session.call_tool(
        echo_tool.name, {"message": "Hello", "count": 3}
    )
    assert result is not None
    assert len(result.content) > 0
    assert result.content[0].text == "Hello\nHello\nHello"


@pytest.mark.anyio
async def test_error_handling(basic_mcp_session):
    """Test error handling for invalid invocations."""
    # Get tools
    result = await basic_mcp_session.list_tools()
    tools = result.tools

    # Find the greet command
    greet_tool = None
    for tool in tools:
        if "greet" in tool.name.lower():
            greet_tool = tool
            break

    assert greet_tool is not None

    # Test with invalid tool name - check if it returns an error response
    # instead of raising an exception
    result = await basic_mcp_session.call_tool("non_existent_tool", {})
    assert result is not None
    assert hasattr(result, "isError")
    assert result.isError is True
    assert len(result.content) > 0
    error_message = result.content[0].text.lower()
    assert (
        "non_existent_tool" in error_message
        or "not found" in error_message
        or "unknown" in error_message
    )

    # Test with missing required parameter
    result = await basic_mcp_session.call_tool(greet_tool.name, {})
    assert result is not None
    assert hasattr(result, "isError")
    assert result.isError is True
    assert len(result.content) > 0
    error_message = result.content[0].text.lower()
    assert (
        "name" in error_message
        or "required" in error_message
        or "missing" in error_message
    )


@pytest.mark.anyio
async def test_advanced_server_tools(advanced_mcp_session):
    """Test that the advanced MCP server returns correct tools."""
    result = await advanced_mcp_session.list_tools()

    # Check that we have tools
    assert result is not None
    assert hasattr(result, "tools")
    tools = result.tools
    assert len(tools) > 0

    # Find the config.set command
    config_set_tool = None
    for tool in tools:
        if "config.set" in tool.name.lower():
            config_set_tool = tool
            break

    assert config_set_tool is not None
    assert "key" in config_set_tool.inputSchema
    assert "value" in config_set_tool.inputSchema

    # Find the greet command with formal option
    greet_tool = None
    for tool in tools:
        if "greet" in tool.name.lower():
            greet_tool = tool
            break

    assert greet_tool is not None
    assert "formal" in greet_tool.inputSchema
    assert greet_tool.inputSchema["formal"]["schema"]["type"] == "boolean"


@pytest.fixture
async def custom_server_name_session(request):
    """Fixture that provides an MCP server context for the custom server name CLI."""
    script_path = Path(__file__).parent / "custom_server_cli.py"
    async with mcp_server_client(script_path, "mcp") as session:
        yield session


@pytest.mark.anyio
async def test_custom_server_name(custom_server_name_session):
    """Test that the server_name parameter is used correctly."""
    # Get tools
    result = await custom_server_name_session.list_tools()

    # Check that we have tools
    assert result is not None
    assert hasattr(result, "tools")
    tools = result.tools
    assert len(tools) > 0

    # Find the greet command
    greet_tool = None
    for tool in tools:
        if "greet" in tool.name.lower():
            greet_tool = tool
            break

    assert greet_tool is not None

    # Invoke the command
    result = await custom_server_name_session.call_tool(
        greet_tool.name, {"name": "World"}
    )
    assert result is not None
    assert len(result.content) > 0
    assert result.content[0].text == "Hello, World!"


@pytest.mark.anyio
async def test_invoke_advanced_commands(advanced_mcp_session):
    """Test invoking commands on the advanced CLI."""
    # Get tools
    result = await advanced_mcp_session.list_tools()
    tools = result.tools

    # Find the config.set command
    config_set_tool = None
    for tool in tools:
        if "config.set" in tool.name.lower():
            config_set_tool = tool
            break

    assert config_set_tool is not None

    # Invoke the command
    result = await advanced_mcp_session.call_tool(
        config_set_tool.name, {"key": "test", "value": "value"}
    )

    assert result is not None
    assert len(result.content) > 0
    assert result.content[0].text == "Setting test=value"

    # Find the greet command
    greet_tool = None
    for tool in tools:
        if "greet" in tool.name.lower():
            greet_tool = tool
            break

    assert greet_tool is not None

    # Test formal greeting
    result = await advanced_mcp_session.call_tool(
        greet_tool.name, {"name": "World", "formal": True}
    )
    assert result is not None
    assert len(result.content) > 0
    assert result.content[0].text == "Good day, World."

    # Test casual greeting
    result = await advanced_mcp_session.call_tool(
        greet_tool.name, {"name": "World", "formal": False}
    )
    assert result is not None
    assert len(result.content) > 0
    assert result.content[0].text == "Hey World!"
