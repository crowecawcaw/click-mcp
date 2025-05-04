"""
MCP server implementation for Click applications using the MCP library.
"""

import asyncio
import contextlib
import io
from typing import Any, Dict, Iterable, List, Optional, cast

import click
import mcp.types as types
from mcp.server import stdio
from mcp.server.lowlevel import Server

from .decorator import get_mcp_metadata
from .scanner import get_positional_args, scan_click_command


class MCPServer:
    """MCP server for Click applications."""

    def __init__(self, cli_group: click.Group, server_name: str = "click-mcp"):
        """
        Initialize the MCP server.

        Args:
            cli_group: A Click group to expose as MCP tools.
            server_name: The name of the MCP server.
        """
        self.cli_group = cli_group
        self.server_name = server_name
        self.click_tools = scan_click_command(cli_group)
        self.tool_map = {tool.name: tool for tool in self.click_tools}
        self.server: Server = Server(server_name)

        # Register MCP handlers
        self.server.list_tools()(self._handle_list_tools)
        self.server.call_tool()(self._handle_call_tool)

    def run(self) -> None:
        """Run the MCP server with stdio transport."""
        asyncio.run(self._run_server())

    async def _run_server(self) -> None:
        """Run the MCP server asynchronously."""
        async with stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )

    async def _handle_list_tools(self) -> List[types.Tool]:
        """Handle the list_tools request."""
        return self.click_tools

    async def _handle_call_tool(
        self, name: str, arguments: Optional[Dict[str, Any]]
    ) -> Iterable[types.TextContent]:
        """Handle the call_tool request."""
        if name not in self.tool_map:
            raise ValueError(f"Unknown tool: {name}")

        arguments = arguments or {}
        result = self._execute_command(name, arguments)
        return [types.TextContent(type="text", text=result["output"])]

    def _execute_command(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Click command and return its output."""
        command = self._find_command(self.cli_group, tool_name.split("."))
        args = self._build_command_args(command, tool_name, parameters)

        # Capture and return command output
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                ctx = command.make_context(command.name, args)
                command.invoke(ctx)
            except Exception as e:
                raise ValueError(f"Command execution failed: {str(e)}") from e

        return {"output": output.getvalue().rstrip()}

    def _build_command_args(
        self, command: click.Command, tool_name: str, parameters: Dict[str, Any]
    ) -> List[str]:
        """Build command arguments from parameters."""
        args: List[str] = []

        # Get positional arguments for this tool
        positional_order = get_positional_args(tool_name)

        # First, handle positional arguments in the correct order
        for param_name in positional_order:
            if param_name in parameters:
                args.append(str(parameters[param_name]))

        # Then handle options (non-positional parameters)
        for name, value in parameters.items():
            if name not in positional_order:  # Skip positional args already processed
                # Handle boolean flags
                if isinstance(value, bool):
                    if value:
                        args.append(f"--{name}")
                else:
                    args.append(f"--{name}")
                    args.append(str(value))

        return args

    def _find_command(self, group: click.Group, path: List[str]) -> click.Command:
        """Find a command in a group by path."""
        if not path:
            return group

        # Handle the case where the first element is the group name itself
        if path[0] == group.name:
            return self._find_command(group, path[1:])

        current, *remaining = path

        # Try to find the command by name
        if current in group.commands:
            cmd = group.commands[current]
        else:
            # Try to find a command with a custom name
            cmd = None
            for cmd_name, command in group.commands.items():
                # Check command metadata
                if get_mcp_metadata(cmd_name).get("name") == current:
                    cmd = command
                    break

                # Check callback metadata
                if (
                    hasattr(command, "callback")
                    and command.callback is not None
                    and hasattr(command.callback, "_mcp_metadata")
                    and command.callback._mcp_metadata.get("name") == current
                ):
                    cmd = command
                    break

            if cmd is None:
                raise ValueError(f"Command not found: {current}")

        # If there are more path segments, the command must be a group
        if remaining and not hasattr(cmd, "commands"):
            raise ValueError(f"'{current}' is not a command group")

        # If this is the last segment, return the command
        if not remaining:
            return cast(click.Command, cmd)

        # Otherwise, continue searching in the subgroup
        return self._find_command(cast(click.Group, cmd), remaining)
