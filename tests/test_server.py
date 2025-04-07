"""
Tests for the server module.
"""

import io
import json
import sys
from unittest.mock import patch, MagicMock

import click
import pytest
from click_mcp import click_mcp
from click_mcp.server import MCPServer

def test_server_initialization():
    """Test server initialization."""
    
    @click_mcp
    @click.group()
    def cli():
        """Test CLI."""
    
    @cli.command()
    def command():
        """Test command."""
        pass
    
    # Initialize server
    server = MCPServer(cli)
    
    # Check that the server has the CLI group
    assert server.cli_group == cli
    
    # Check that the server has scanned the commands
    assert len(server.tools) > 0
    assert any(tool["name"] == "command" for tool in server.tools)

def test_server_execute_command():
    """Test executing a command through the server."""
    
    @click_mcp
    @click.group()
    def cli():
        """Test CLI."""
    
    @cli.command()
    @click.option("--name", required=True)
    def greet(name):
        """Greet someone."""
        click.echo(f"Hello, {name}!")
    
    # Initialize server
    server = MCPServer(cli)
    
    # Execute command
    result = server._execute_command("greet", {"name": "World"})
    
    # Check result
    assert result["output"] == "Hello, World!"

def test_server_handle_invoke():
    """Test handling an invoke request."""
    
    @click_mcp
    @click.group()
    def cli():
        """Test CLI."""
    
    @cli.command()
    @click.option("--name", required=True)
    def greet(name):
        """Greet someone."""
        click.echo(f"Hello, {name}!")
    
    # Initialize server
    server = MCPServer(cli)
    
    # Mock _send_response method
    server._send_response = MagicMock()
    
    # Handle invoke request
    request = {
        "type": "invoke",
        "tool": "greet",
        "parameters": {"name": "World"},
        "id": "test-id"
    }
    server._handle_invoke(request)
    
    # Check that _send_response was called with the correct arguments
    server._send_response.assert_called_once()
    args = server._send_response.call_args[0][0]
    assert args["type"] == "invoke_response"
    assert args["id"] == "test-id"
    assert args["result"]["output"] == "Hello, World!"

def test_server_handle_error():
    """Test handling errors."""
    
    @click_mcp
    @click.group()
    def cli():
        """Test CLI."""
    
    @cli.command()
    @click.option("--name", required=True)
    def greet(name):
        """Greet someone."""
        click.echo(f"Hello, {name}!")
    
    # Initialize server
    server = MCPServer(cli)
    
    # Mock _send_response and _send_error methods
    server._send_response = MagicMock()
    server._send_error = MagicMock()
    
    # Handle invoke request with missing parameter
    request = {
        "type": "invoke",
        "tool": "greet",
        "parameters": {},  # Missing required parameter
        "id": "test-id"
    }
    server._handle_invoke(request)
    
    # Check that _send_error was called
    server._send_error.assert_called_once()
    assert "Error invoking tool greet" in server._send_error.call_args[0][0]
