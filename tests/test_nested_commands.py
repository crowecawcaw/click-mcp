"""
Tests for nested command structure handling.
"""

import pytest
from click_mcp.scanner import scan_click_command
from tests.basic_cli import cli


class TestNestedCommands:
    """Test nested command structure handling."""

    def test_nested_commands_use_underscore_notation(self):
        """Test that nested commands use underscore notation to comply with MCP spec."""
        tools = scan_click_command(cli)
        tool_names = [tool.name for tool in tools]
        
        # The basic CLI has a 'users' group with a 'list' command
        # This should create a nested command with underscore notation (MCP spec compliant)
        assert "users_list" in tool_names, f"Expected 'users_list' but found: {tool_names}"
        
        # It should NOT use dot notation (which violates MCP spec)
        assert "users.list" not in tool_names, f"Should not create dot notation 'users.list', found: {tool_names}"

    def test_nested_command_description(self):
        """Test that nested commands have correct descriptions."""
        tools = scan_click_command(cli)
        tool_dict = {tool.name: tool for tool in tools}
        
        # Find the users_list tool
        users_list_tool = tool_dict.get("users_list")
        assert users_list_tool is not None, f"users_list tool not found in {list(tool_dict.keys())}"
        
        # Check description
        assert "List all users in the system" in users_list_tool.description

    def test_root_level_commands_not_hierarchical(self):
        """Test that root level commands are not hierarchical when parent has no params."""
        tools = scan_click_command(cli)
        tool_names = [tool.name for tool in tools]
        
        # Root level commands should be simple names
        assert "greet" in tool_names, f"Expected 'greet' but found: {tool_names}"
        assert "echo" in tool_names, f"Expected 'echo' but found: {tool_names}"
        
        # They should NOT be hierarchical
        assert "cli_greet" not in tool_names, f"Should not create hierarchical 'cli_greet', found: {tool_names}"
        assert "cli_echo" not in tool_names, f"Should not create hierarchical 'cli_echo', found: {tool_names}"

    def test_all_expected_tools_present(self):
        """Test that all expected tools are present with correct naming."""
        tools = scan_click_command(cli)
        tool_names = set(tool.name for tool in tools)
        
        expected_tools = {
            "greet",       # Root level command
            "echo",        # Root level command  
            "users_list"   # Nested command with underscore notation (MCP compliant)
        }
        
        assert tool_names == expected_tools, f"Expected {expected_tools} but got {tool_names}"

    def test_nested_commands_comply_with_mcp_spec(self):
        """Test that all tool names comply with MCP specification [a-zA-Z][a-zA-Z0-9_]*."""
        import re
        
        tools = scan_click_command(cli)
        mcp_pattern = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')
        
        for tool in tools:
            assert mcp_pattern.match(tool.name), f"Tool name '{tool.name}' does not comply with MCP spec [a-zA-Z][a-zA-Z0-9_]*"
        
        # Verify no dots in tool names
        tool_names = [tool.name for tool in tools]
        dot_names = [name for name in tool_names if '.' in name]
        assert len(dot_names) == 0, f"Found tool names with dots (invalid for MCP): {dot_names}"
