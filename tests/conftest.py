"""
Common fixtures for click-mcp tests.
"""

import pytest
import click
from click_mcp import click_mcp

@pytest.fixture
def basic_cli():
    """Create a basic CLI with click_mcp decorator."""
    @click_mcp
    @click.group()
    def cli():
        """Test CLI."""
        pass
    
    return cli

@pytest.fixture
def cli_with_commands():
    """Create a CLI with multiple commands."""
    @click_mcp
    @click.group()
    def cli():
        """Test CLI with commands."""
        pass
    
    @cli.command()
    def command1():
        """Command 1."""
        click.echo("Command 1")
    
    @cli.command()
    def command2():
        """Command 2."""
        click.echo("Command 2")
    
    return cli
