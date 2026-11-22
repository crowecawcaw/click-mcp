"""
Decorator for adding MCP support to Click applications.
"""

from typing import Any, Callable, Dict, Optional, TypeVar, Union

import click

from .hooks import ConfigureServer, ToolCompletionHook

# Registry for MCP metadata
_MCP_REGISTRY: Dict[str, Dict[str, Any]] = {}

F = TypeVar("F", bound=Callable[..., Any])


def register_mcp_metadata(command_name: str, metadata: Dict[str, Any]) -> None:
    """
    Register MCP metadata for a command.

    Args:
        command_name: The CLI path relative to the root, such as users.list, or a legacy leaf name.
        metadata: The metadata to register.
    """
    _MCP_REGISTRY[command_name] = metadata


def get_mcp_metadata(command_name: str) -> Dict[str, Any]:
    """
    Get MCP metadata for a command.

    Args:
        command_name: The CLI path relative to the root, such as users.list, or a legacy leaf name.

    Returns:
        The metadata for the command, or an empty dict if none exists.
    """
    return _MCP_REGISTRY.get(command_name, {})


def click_mcp(
    server_name: str,
    cli_group: Optional[click.Group] = None,
    command_name: str = "mcp",
    include_all_commands: bool = True,
    *,
    include_hidden: bool = False,
    configure_server: ConfigureServer | None = None,
    on_tool_complete: ToolCompletionHook | None = None,
) -> Union[Callable[[click.Group], click.Group], click.Group]:
    """
    Decorator that adds MCP support to a Click application.

    Args:
        cli_group: The Click group to decorate. If None, the decorator expects
            to be used as @click_mcp.
        command_name: The name of the MCP command to add.
        server_name: The name of the MCP server to use. Required.
        include_all_commands: Whether to include commands by default.
        include_hidden: Whether hidden commands and groups can be exposed.
        configure_server: Optional callback to register SDK handlers at startup.
        on_tool_complete: Optional async callback after tool invocation.

    Returns:
        The decorated Click group.
    """
    if server_name is None:
        raise ValueError("server_name is required")
    # Handle case where decorator is used without arguments
    if cli_group is not None:
        return _add_mcp_command(
            cli_group,
            command_name,
            server_name,
            include_all_commands,
            include_hidden,
            configure_server,
            on_tool_complete,
        )

    # Handle case where decorator is used with arguments
    def decorator(group: click.Group) -> click.Group:
        return _add_mcp_command(
            group,
            command_name,
            server_name,
            include_all_commands,
            include_hidden,
            configure_server,
            on_tool_complete,
        )

    return decorator


def _add_mcp_command(
    cli_group: click.Group,
    command_name: str,
    server_name: str,
    include_all_commands: bool,
    include_hidden: bool,
    configure_server: ConfigureServer | None,
    on_tool_complete: ToolCompletionHook | None,
) -> click.Group:
    """Add an MCP command to a Click group."""
    from .server import MCPServer

    def mcp_command() -> None:
        """Start the MCP server for this CLI application."""
        server = MCPServer(
            cli_group,
            server_name,
            include_all_commands,
            include_hidden=include_hidden,
            configure_server=configure_server,
            on_tool_complete=on_tool_complete,
        )
        server.run()

    command: Any
    if hasattr(cli_group, "command"):
        command = cli_group.command(name=command_name)(mcp_command)
    else:
        from typer.core import TyperCommand

        command = TyperCommand(
            name=command_name, callback=mcp_command, help=mcp_command.__doc__
        )
        cli_group.add_command(command)

    # Mark this command as an MCP command for robust detection.
    command._is_mcp_command = True  # type: ignore[attr-defined]

    return cli_group
