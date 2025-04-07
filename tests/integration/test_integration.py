"""
Integration tests for click-mcp.
"""

import json
import subprocess
import sys
import os
from pathlib import Path
import pytest


class MCPClient:
    """Helper class to interact with an MCP server."""

    def __init__(self, process):
        self.process = process
        self.request_id = 0

        # Read the server_info response
        self.server_info = self._read_response()
        assert self.server_info["type"] == "server_info"

    def invoke(self, tool, parameters=None):
        """Invoke a tool on the MCP server."""
        if parameters is None:
            parameters = {}

        self.request_id += 1
        request = {
            "type": "invoke",
            "id": str(self.request_id),
            "tool": tool,
            "parameters": parameters,
        }

        self._send_request(request)
        return self._read_response()

    def _send_request(self, request):
        """Send a request to the MCP server."""
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()

    def _read_response(self):
        """Read a response from the MCP server."""
        response_line = self.process.stdout.readline().strip()
        if not response_line:
            error = self.process.stderr.readline().strip()
            raise RuntimeError(f"No response from server. Error: {error}")
        return json.loads(response_line)

    def close(self):
        """Close the connection to the MCP server."""
        self.process.terminate()


@pytest.fixture
def basic_mcp_client():
    """Fixture that provides an MCP client for the basic CLI."""
    script_path = Path(__file__).parent / "test_cli.py"

    # Start the MCP server
    process = subprocess.Popen(
        [sys.executable, str(script_path), "mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Create a client
    client = MCPClient(process)

    yield client

    # Clean up
    client.close()


@pytest.fixture
def advanced_mcp_client():
    """Fixture that provides an MCP client for the advanced CLI."""
    script_path = Path(__file__).parent / "test_advanced_cli.py"

    # Start the MCP server
    process = subprocess.Popen(
        [sys.executable, str(script_path), "start-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Create a client
    client = MCPClient(process)

    yield client

    # Clean up
    client.close()


def test_basic_server_info(basic_mcp_client):
    """Test that the basic MCP server returns correct server_info with tools."""
    server_info = basic_mcp_client.server_info

    # Verify the server_info structure
    assert server_info["type"] == "server_info"
    assert server_info["version"] == "1.0"
    assert "tools" in server_info

    # Verify the tools list contains our commands with correct descriptions
    tools = {tool["name"]: tool for tool in server_info["tools"]}

    # Check greet command
    assert "greet" in tools
    assert tools["greet"]["description"] == "Greet someone with a friendly message."
    assert "parameters" in tools["greet"]
    assert "name" in tools["greet"]["parameters"]
    assert tools["greet"]["parameters"]["name"]["description"] == "Name to greet"
    assert tools["greet"]["parameters"]["name"]["required"] is True

    # Check users.list command
    assert "users.list" in tools
    assert tools["users.list"]["description"] == "List all users in the system."

    # Check echo command
    assert "echo" in tools
    assert tools["echo"]["description"] == "Echo a message multiple times."
    assert "count" in tools["echo"]["parameters"]
    assert tools["echo"]["parameters"]["count"]["type"] == "integer"
    assert "message" in tools["echo"]["parameters"]


def test_advanced_server_info(advanced_mcp_client):
    """Test that advanced features like custom naming and selective inclusion work."""
    server_info = advanced_mcp_client.server_info

    # Verify the tools list contains only the included commands with correct names
    tools = {tool["name"]: tool for tool in server_info["tools"]}

    # Check custom named command
    assert "say-hello" in tools
    assert "greet" not in tools
    assert (
        tools["say-hello"]["description"] == "Greet someone with a custom command name."
    )

    # Check hidden command is not included
    assert "hidden" not in tools

    # Check custom named group and its command
    assert "api.list" in tools
    assert "endpoints.list" not in tools
    assert tools["api.list"]["description"] == "List all API endpoints."


def test_invoke_greet_command(basic_mcp_client):
    """Test invoking the greet command."""
    response = basic_mcp_client.invoke("greet", {"name": "World"})

    assert response["type"] == "invoke_response"
    assert "result" in response
    assert "output" in response["result"]
    assert response["result"]["output"] == "Hello, World!"


def test_invoke_users_list_command(basic_mcp_client):
    """Test invoking the users.list command."""
    response = basic_mcp_client.invoke("users.list")

    assert response["type"] == "invoke_response"
    assert "result" in response
    assert "output" in response["result"]
    assert "User1\nUser2\nUser3" in response["result"]["output"]


def test_invoke_echo_command(basic_mcp_client):
    """Test invoking the echo command with different parameters."""
    # Test with default count
    response = basic_mcp_client.invoke("echo", {"message": "Hello"})
    assert response["type"] == "invoke_response"
    assert response["result"]["output"] == "Hello"

    # Test with custom count
    response = basic_mcp_client.invoke("echo", {"message": "Hello", "count": 3})
    assert response["type"] == "invoke_response"
    assert response["result"]["output"] == "Hello\nHello\nHello"


def test_invoke_custom_named_command(advanced_mcp_client):
    """Test invoking a command with a custom name."""
    response = advanced_mcp_client.invoke("say-hello", {"name": "Custom"})

    assert response["type"] == "invoke_response"
    assert response["result"]["output"] == "Hello, Custom!"


def test_invoke_custom_group_command(advanced_mcp_client):
    """Test invoking a command in a custom named group."""
    response = advanced_mcp_client.invoke("api.list")

    assert response["type"] == "invoke_response"
    assert "Endpoint1\nEndpoint2" in response["result"]["output"]


def test_error_handling(basic_mcp_client):
    """Test error handling for invalid invocations."""
    # Missing required parameter
    response = basic_mcp_client.invoke("greet", {})
    assert response["type"] == "error"
    assert "name" in response["message"].lower()

    # Invalid tool name
    response = basic_mcp_client.invoke("non_existent_tool")
    assert response["type"] == "error"
    assert "non_existent_tool" in response["message"]
