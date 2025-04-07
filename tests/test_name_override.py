"""
Tests for command name overrides.
"""

import click
import pytest
from click_mcp import click_mcp
from click_mcp.scanner import scan_click_command

def test_command_name_overrides():
    """Test various command name override scenarios."""
    
    @click_mcp
    @click.group()
    def cli():
        """Test CLI."""
    
    # Simple command name override
    @cli.command()
    @click_mcp.command(name="hello-world")
    def greet():
        """Greeting command with overridden name."""
    
    # Group name override
    @cli.group()
    @click_mcp.command(name="user-management")
    def users():
        """User management group with overridden name."""
    
    @users.command()
    def list():
        """List users."""
    
    # Nested group name overrides
    @cli.group()
    @click_mcp.command(name="api")
    def commands():
        """Commands group with overridden name."""
    
    @commands.group()
    @click_mcp.command(name="users")
    def user_commands():
        """User commands group with overridden name."""
    
    @user_commands.command()
    @click_mcp.command(name="find")
    def search():
        """Search command with overridden name."""
    
    # Special characters in names
    @cli.command()
    @click_mcp.command(name="special-chars_123")
    def special():
        """Command with special characters in the overridden name."""
    
    # Scan the commands
    tools = scan_click_command(cli)
    tool_names = [tool["name"] for tool in tools]
    
    # Check simple name override
    assert "hello-world" in tool_names
    assert "greet" not in tool_names
    
    # Check group name override
    assert "user-management.list" in tool_names
    assert "users.list" not in tool_names
    
    # Check nested group name overrides
    assert "api.users.find" in tool_names
    assert "commands.user_commands.search" not in tool_names
    
    # Check special characters
    assert "special-chars_123" in tool_names

@pytest.mark.parametrize("original_name,custom_name", [
    ("technical-name", "friendly-name"),
    ("internal_name", "public-name"),
    ("long_complicated_name", "short")
])
def test_parameterized_name_overrides(original_name, custom_name):
    """Test name overrides with parameterized test cases."""
    
    @click_mcp
    @click.group()
    def cli():
        """Test CLI."""
    
    # Define a command with the original name and override it
    @cli.command(original_name)
    @click_mcp.command(name=custom_name)
    def command_func():
        """Command with overridden name."""
    
    # Scan the commands
    tools = scan_click_command(cli)
    tool_names = [tool["name"] for tool in tools]
    
    # Check that the command has the overridden name
    assert custom_name in tool_names
    assert original_name not in tool_names
