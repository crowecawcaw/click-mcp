"""
Tests for command inclusion behavior.
"""

import click
import pytest
from click_mcp import click_mcp
from click_mcp.scanner import scan_click_command
from click_mcp.decorator import register_mcp_metadata

@pytest.mark.parametrize("include_all_commands,expected_included,expected_excluded", [
    (True, ["command1", "command2"], ["excluded"]),
    (False, ["included"], ["command1", "command2"])
])
def test_include_all_commands_parameter(include_all_commands, expected_included, expected_excluded):
    """Test the include_all_commands parameter with different values."""
    
    @click_mcp(include_all_commands=include_all_commands)
    @click.group()
    def cli():
        """Test CLI."""
    
    # Add commands based on the test case
    if include_all_commands:
        @cli.command()
        def command1():
            """Command 1."""
        
        @cli.command()
        def command2():
            """Command 2."""
        
        @cli.command()
        @click_mcp.command(include=False)
        def excluded():
            """Explicitly excluded command."""
    else:
        @cli.command()
        def command1():
            """Command 1."""
        
        @cli.command()
        def command2():
            """Command 2."""
        
        @cli.command()
        @click_mcp.command(include=True)
        def included():
            """Explicitly included command."""
    
    # Scan the commands
    tools = scan_click_command(cli)
    tool_names = [tool["name"] for tool in tools]
    
    # Check that the expected commands are included/excluded
    for name in expected_included:
        assert name in tool_names
    for name in expected_excluded:
        assert name not in tool_names

def test_nested_command_inclusion():
    """Test command inclusion with nested command groups."""
    
    @click_mcp(include_all_commands=False)
    @click.group()
    def cli():
        """Test CLI."""
    
    @cli.group()
    @click_mcp.command(include=True)
    def group1():
        """Group 1 (included)."""
    
    @group1.command()
    def command1():
        """Command in group1 (should inherit exclusion)."""
    
    @group1.command()
    @click_mcp.command(include=True)
    def command2():
        """Command in group1 (explicitly included)."""
    
    # Register metadata manually for testing
    register_mcp_metadata("group1", {"include": True})
    register_mcp_metadata("command2", {"include": True})
    
    # Scan the commands
    tools = scan_click_command(cli)
    tool_names = [tool["name"] for tool in tools]
    
    # Check that only explicitly included commands are present
    assert "group1.command2" in tool_names

def test_include_all_commands_default():
    """Test that include_all_commands defaults to True when not specified."""

    @click_mcp  # No include_all_commands parameter
    @click.group()
    def cli():
        """Test CLI."""
        pass

    @cli.command()
    def command1():
        """Command 1."""
        pass

    @cli.command()
    def command2():
        """Command 2."""
        pass

    # Scan the commands
    tools = scan_click_command(cli)

    # Check that all commands are included by default
    tool_names = [tool["name"] for tool in tools]
    assert "command1" in tool_names
    assert "command2" in tool_names
