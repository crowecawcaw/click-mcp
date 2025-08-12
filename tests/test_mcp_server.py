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
    # Verify inputSchema structure
    assert greet_tool.inputSchema["type"] == "object"
    assert "properties" in greet_tool.inputSchema
    assert "name" in greet_tool.inputSchema["properties"]
    assert "required" in greet_tool.inputSchema
    assert "name" in greet_tool.inputSchema["required"]

    # Find the users_list command
    users_list_tool = None
    for tool in tools:
        if "users_list" in tool.name.lower():
            users_list_tool = tool
            break

    assert users_list_tool is not None
    # Verify inputSchema structure (should only have help param)
    assert users_list_tool.inputSchema["type"] == "object"
    assert "properties" in users_list_tool.inputSchema
    # Click automatically adds --help, so we expect only that property
    assert len(users_list_tool.inputSchema["properties"]) <= 1
    if len(users_list_tool.inputSchema["properties"]) == 1:
        assert "help" in users_list_tool.inputSchema["properties"]
    assert "required" not in users_list_tool.inputSchema  # No required params

    # Find the echo command
    echo_tool = None
    for tool in tools:
        if "echo" in tool.name.lower():
            echo_tool = tool
            break

    assert echo_tool is not None
    # Verify inputSchema structure
    assert echo_tool.inputSchema["type"] == "object"
    assert "properties" in echo_tool.inputSchema
    assert "count" in echo_tool.inputSchema["properties"]
    assert echo_tool.inputSchema["properties"]["count"]["schema"]["type"] == "integer"
    assert "message" in echo_tool.inputSchema["properties"]
    assert "required" in echo_tool.inputSchema
    assert "message" in echo_tool.inputSchema["required"]  # Only message is required


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
    """Test invoking the users_list command."""
    # Get tools
    result = await basic_mcp_session.list_tools()
    tools = result.tools

    # Find the users_list command
    users_list_tool = None
    for tool in tools:
        if "users_list" in tool.name.lower():
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

    # Find the config_set command
    config_set_tool = None
    for tool in tools:
        if "config_set" in tool.name.lower():
            config_set_tool = tool
            break

    assert config_set_tool is not None
    # Verify inputSchema structure
    assert config_set_tool.inputSchema["type"] == "object"
    assert "properties" in config_set_tool.inputSchema
    assert "key" in config_set_tool.inputSchema["properties"]
    assert "value" in config_set_tool.inputSchema["properties"]
    assert "required" in config_set_tool.inputSchema
    assert "key" in config_set_tool.inputSchema["required"]
    assert "value" in config_set_tool.inputSchema["required"]

    # Find the greet command with formal option
    greet_tool = None
    for tool in tools:
        if "greet" in tool.name.lower():
            greet_tool = tool
            break

    assert greet_tool is not None
    # Verify inputSchema structure
    assert greet_tool.inputSchema["type"] == "object"
    assert "properties" in greet_tool.inputSchema
    assert "name" in greet_tool.inputSchema["properties"]
    assert "formal" in greet_tool.inputSchema["properties"]
    assert greet_tool.inputSchema["properties"]["formal"]["schema"]["type"] == "boolean"
    assert "required" in greet_tool.inputSchema
    assert "name" in greet_tool.inputSchema["required"]  # Only name is required


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

    # Find the config_set command
    config_set_tool = None
    for tool in tools:
        if "config_set" in tool.name.lower():
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

    # Find the config_get command with positional argument
    config_get_tool = None
    for tool in tools:
        if "config_get" in tool.name.lower() and tool.name.lower() == "config_get":
            config_get_tool = tool
            break

    assert config_get_tool is not None
    # Verify inputSchema structure for positional arguments
    assert config_get_tool.inputSchema["type"] == "object"
    assert "properties" in config_get_tool.inputSchema
    assert "key" in config_get_tool.inputSchema["properties"]
    assert "required" in config_get_tool.inputSchema
    assert "key" in config_get_tool.inputSchema["required"]

    # Invoke the command with positional argument
    result = await advanced_mcp_session.call_tool(
        config_get_tool.name, {"key": "test-key"}
    )
    assert result is not None
    assert len(result.content) > 0
    assert "Value for test-key: example_value" in result.content[0].text

    # Find the config_get_value command with dash in name
    config_get_value_tool = None
    for tool in tools:
        if "get_value" in tool.name.lower():
            config_get_value_tool = tool
            break

    assert config_get_value_tool is not None
    # Verify inputSchema structure for positional arguments
    assert config_get_value_tool.inputSchema["type"] == "object"
    assert "properties" in config_get_value_tool.inputSchema
    assert "key" in config_get_value_tool.inputSchema["properties"]
    assert "required" in config_get_value_tool.inputSchema
    assert "key" in config_get_value_tool.inputSchema["required"]

    # Invoke the command with positional argument
    result = await advanced_mcp_session.call_tool(
        config_get_value_tool.name, {"key": "underscore-key"}
    )
    assert result is not None
    assert len(result.content) > 0
    assert "Value for underscore-key (from get_value)" in result.content[0].text

    # Find the copy command with multiple positional arguments
    copy_tool = None
    for tool in tools:
        if "copy" in tool.name.lower():
            copy_tool = tool
            break

    assert copy_tool is not None
    # Verify inputSchema structure for multiple positional arguments
    assert copy_tool.inputSchema["type"] == "object"
    assert "properties" in copy_tool.inputSchema
    assert "source" in copy_tool.inputSchema["properties"]
    assert "destination" in copy_tool.inputSchema["properties"]
    assert "overwrite" in copy_tool.inputSchema["properties"]
    assert "required" in copy_tool.inputSchema
    assert "source" in copy_tool.inputSchema["required"]
    assert "destination" in copy_tool.inputSchema["required"]

    # Invoke the command with positional arguments
    result = await advanced_mcp_session.call_tool(
        copy_tool.name, {"source": "file.txt", "destination": "/tmp/file.txt"}
    )
    assert result is not None
    assert len(result.content) > 0
    assert "Copying file.txt to /tmp/file.txt" in result.content[0].text

    # Test with option
    result = await advanced_mcp_session.call_tool(
        copy_tool.name,
        {"source": "file.txt", "destination": "/tmp/file.txt", "overwrite": True},
    )
    assert result is not None
    assert len(result.content) > 0
    assert "Overwriting file.txt to /tmp/file.txt" in result.content[0].text

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


@pytest.mark.anyio
async def test_mcp_command_excluded_from_tools(basic_mcp_session):
    """Test that the MCP command itself is not exposed as a tool."""
    # Get all available tools
    result = await basic_mcp_session.list_tools()
    tools = result.tools
    tool_names = [tool.name for tool in tools]
    
    # Verify that the default 'mcp' command is NOT exposed as a tool
    assert "mcp" not in tool_names, f"Default MCP command 'mcp' should not be exposed as a tool, but found in {tool_names}"
    
    # Verify that expected tools are present (sanity check)
    expected_tools = ["echo", "greet", "users_list"]
    for expected_tool in expected_tools:
        assert expected_tool in tool_names, f"Expected tool '{expected_tool}' not found in {tool_names}"
    
    # Verify we have the expected number of tools (no extra MCP command)
    assert len(tool_names) == len(expected_tools), f"Expected {len(expected_tools)} tools, but got {len(tool_names)}: {tool_names}"


@pytest.mark.anyio 
async def test_custom_mcp_command_excluded_from_tools(advanced_mcp_session):
    """Test that custom MCP command names are also excluded from tool discovery."""
    # Get all available tools from advanced CLI (which uses 'start-mcp' as MCP command)
    result = await advanced_mcp_session.list_tools()
    tools = result.tools
    tool_names = [tool.name for tool in tools]
    
    # Verify that the custom 'start-mcp' command is NOT exposed as a tool
    assert "start-mcp" not in tool_names, f"Custom MCP command 'start-mcp' should not be exposed as a tool, but found in {tool_names}"
    
    # Verify that the default 'mcp' command is also not there
    assert "mcp" not in tool_names, f"Default MCP command 'mcp' should not be exposed as a tool, but found in {tool_names}"
    
    # Verify that expected tools are present (sanity check)
    expected_tools = ["config_get", "config_get_value", "config_set", "copy", "greet", "process"]
    for expected_tool in expected_tools:
        assert expected_tool in tool_names, f"Expected tool '{expected_tool}' not found in {tool_names}"
