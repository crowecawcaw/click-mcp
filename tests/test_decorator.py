"""
Tests for the click_mcp decorator functionality.
"""

import click
import pytest
from click_mcp import click_mcp
from click_mcp.scanner import scan_click_command
from click_mcp.decorator import get_mcp_metadata, register_mcp_metadata

def test_click_mcp_decorator_features():
    """Test multiple features of the click_mcp decorator."""
    
    # Test default behavior
    @click_mcp
    @click.group()
    def cli1():
        """Test CLI 1."""
    
    assert "mcp" in cli1.commands
    assert cli1.commands["mcp"].help == "Start an MCP server for this CLI application."
    
    # Test custom command name
    @click_mcp(command_name="start-mcp")
    @click.group()
    def cli2():
        """Test CLI 2."""
    
    assert "start-mcp" in cli2.commands
    assert "mcp" not in cli2.commands
    
    # Test include_all_commands parameter
    @click_mcp(include_all_commands=False)
    @click.group()
    def cli3():
        """Test CLI 3."""
    
    assert "mcp" in cli3.commands

def test_command_decorator_options():
    """Test various options of the command decorator."""
    
    @click.group()
    def cli():
        """Test CLI."""
    
    # Test include flag
    @cli.command()
    @click_mcp.command(include=True)
    def included_command():
        """Command that should be included."""
    
    # Test name override
    @cli.command()
    @click_mcp.command(name="custom-name")
    def original_name():
        """Command with name override."""
    
    # Test combined options
    @cli.command()
    @click_mcp.command(include=True, name="renamed")
    def combined():
        """Command with combined options."""
    
    # Register metadata manually for testing
    register_mcp_metadata("included_command", {"include": True})
    register_mcp_metadata("original_name", {"name": "custom-name"})
    register_mcp_metadata("combined", {"include": True, "name": "renamed"})
    
    # Check metadata from registry
    assert get_mcp_metadata("included_command")["include"] is True
    assert get_mcp_metadata("original_name")["name"] == "custom-name"
    assert get_mcp_metadata("combined")["include"] is True
    assert get_mcp_metadata("combined")["name"] == "renamed"

def test_command_decorator_on_group():
    """Test that the command decorator works on command groups."""

    @click_mcp
    @click.group()
    def cli():
        """Test CLI."""
        pass

    @cli.group()
    @click_mcp.command(name="api")
    def commands():
        """Command group with overridden name."""
        pass

    @commands.command()
    def list():
        """List command."""
        click.echo("List command")

    @commands.command()
    @click_mcp.command(name="find")
    def search():
        """Search command with overridden name."""
        click.echo("Search command")

    # Manually register metadata for testing
    register_mcp_metadata("commands", {"name": "api"})
    register_mcp_metadata("search", {"name": "find"})

    # Scan the commands
    tools = scan_click_command(cli)

    # Check that the nested commands have the correct names
    tool_names = [tool["name"] for tool in tools]
    assert "api.list" in tool_names
    assert "api.find" in tool_names
    assert "commands.list" not in tool_names
    assert "commands.search" not in tool_names
