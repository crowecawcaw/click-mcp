"""
Decorator for adding MCP support to Click applications.
"""

from typing import Dict, Any, Optional, Callable

import click


# Registry to store MCP metadata for commands
_mcp_registry = {}


def register_mcp_metadata(command_name: str, metadata: Dict[str, Any]):
    """Register MCP metadata for a command."""
    if command_name not in _mcp_registry:
        _mcp_registry[command_name] = {}

    _mcp_registry[command_name].update(metadata)


def get_mcp_metadata(command_name: str) -> Dict[str, Any]:
    """Get MCP metadata for a command."""
    return _mcp_registry.get(command_name, {})


class CommandDecorator:  # pylint: disable=too-few-public-methods
    """Decorator for customizing MCP command behavior."""

    def __call__(self, include: bool = True, name: Optional[str] = None) -> Callable:
        """
        Decorator for customizing MCP command behavior.

        Usage:
            @cli.command()
            @click_mcp.command(include=True, name="custom-name")
            def my_command():
                \"\"\"Command with custom MCP settings.\"\"\"
                pass

        Args:
            include: Whether to include this command in MCP tools (default: True).
            name: Custom name to use for this command in MCP tools.

        Returns:
            A decorator function.
        """

        def decorator(f):
            # Store metadata directly in the function object
            if not hasattr(f, "_mcp_metadata"):  # pylint: disable=protected-access
                f._mcp_metadata = {}  # pylint: disable=protected-access

            f._mcp_metadata["include"] = include  # pylint: disable=protected-access
            if name:
                f._mcp_metadata["name"] = name  # pylint: disable=protected-access

            # Register metadata with the command name
            if hasattr(f, "name"):
                register_mcp_metadata(
                    f.name, f._mcp_metadata
                )  # pylint: disable=protected-access

            # For Click commands, we need to add a callback to register metadata
            # when the command is created
            original_callback = f.callback if hasattr(f, "callback") else None

            def _register_mcp_metadata(ctx, param, value):
                cmd = ctx.command
                register_mcp_metadata(cmd.name, {"include": include, "name": name})

                if original_callback:
                    return original_callback(ctx, param, value)
                return value

            f = click.option(
                "--_mcp_register",
                is_flag=True,
                hidden=True,
                expose_value=False,
                callback=_register_mcp_metadata,
            )(f)

            return f

        return decorator


# Create a command decorator instance
command = CommandDecorator()


def click_mcp(
    cli_group=None, command_name: str = "mcp", include_all_commands: bool = True
):
    """
    Decorator that adds MCP support to a Click application.

    Usage:
        @click_mcp
        @click.group()
        def cli():
            \"\"\"Sample CLI application.\"\"\"
            pass

        # Or with custom command name:
        @click_mcp(command_name="start-mcp")
        @click.group()
        def cli():
            \"\"\"Sample CLI application.\"\"\"
            pass

        # Or with selective command inclusion:
        @click_mcp(include_all_commands=False)
        @click.group()
        def cli():
            \"\"\"Only expose specific commands as MCP tools.\"\"\"
            pass

    Args:
        cli_group: A Click Group object to extend with MCP support.
        command_name: Name of the MCP command to add (default: "mcp").
        include_all_commands: Whether to include all commands by default (default: True).

    Returns:
        The decorated Click group or a decorator function.
    """
    # Add the command decorator to the click_mcp namespace
    click_mcp.command = command  # type: ignore

    # Handle case when used as @click_mcp or @click_mcp(command_name="...")
    if cli_group is None:
        return lambda f: _add_mcp_support(f, command_name, include_all_commands)

    # Handle case when used as click_mcp(cli_group)
    return _add_mcp_support(cli_group, command_name, include_all_commands)


def _add_mcp_support(cli_group, command_name: str, include_all_commands: bool):
    """Add MCP support to a Click group."""
    if not isinstance(cli_group, (click.Command, click.Group)):
        raise TypeError(
            f"@click_mcp decorator must be applied to a Click command or group. "
            f"Got {type(cli_group).__name__} instead."
        )

    if not isinstance(cli_group, click.Group):
        raise TypeError(
            f"@click_mcp decorator must be applied to a Click group, not a Click command. "
            f"Got {type(cli_group).__name__} instead."
        )

    register_mcp_metadata(
        cli_group.name, {"include_all_commands": include_all_commands}
    )

    @cli_group.command(command_name)
    def mcp_command():
        """Start an MCP server for this CLI application."""
        # Import here to avoid circular imports
        # pylint: disable=import-outside-toplevel,cyclic-import
        from .server import MCPServer

        mcp_server = MCPServer(cli_group)
        mcp_server.run()

    return cli_group
