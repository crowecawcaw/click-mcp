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
        # Get the original command path
        from .scanner import get_original_path

        original_path = get_original_path(tool_name)
        path_segments = original_path.split(".")
        args = self._build_command_args_for_path(path_segments, tool_name, parameters)

        # Capture and return command output
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                # Use Click's proper command chain execution pattern
                self._execute_command_chain(self.cli_group, path_segments, args)
            except Exception as e:
                raise ValueError(f"Command execution failed: {str(e)}") from e

        return {"output": output.getvalue().rstrip()}

    def _execute_command_chain(
        self, cli_group: click.Group, path_segments: List[str], all_args: List[str]
    ) -> None:
        """
        Execute command chain with proper context inheritance.
        
        This implements Click's proper execution pattern based on Group.invoke()
        to ensure parent contexts are properly passed to child commands.
        
        Args:
            cli_group: Root Click group
            path_segments: Command path like ['parent', 'child']
            all_args: All arguments for the command chain
        """
        if not path_segments:
            return

        # For single commands (no parent-child relationship), use simple execution
        if len(path_segments) == 1:
            command = self._find_command(cli_group, path_segments)
            ctx = command.make_context(command.name, all_args)
            with ctx:
                command.invoke(ctx)
            return

        # For command chains, implement Click's proper context chain execution
        # Parse arguments to separate parent and child arguments
        parent_cmd_name = path_segments[0]
        child_path = path_segments[1:]
        
        parent_args, child_args = self._parse_command_chain_args(
            cli_group, parent_cmd_name, child_path, all_args
        )

        # Get parent command
        parent_cmd = cli_group.get_command(None, parent_cmd_name)
        if parent_cmd is None:
            raise ValueError(f"Parent command not found: {parent_cmd_name}")

        # Create parent context and execute parent command
        parent_ctx = parent_cmd.make_context(parent_cmd_name, parent_args)
        
        with parent_ctx:
            # Execute parent command first (this sets up ctx.obj)
            if hasattr(parent_cmd, 'invoke'):
                parent_cmd.invoke(parent_ctx)
            
            # Now execute child command with parent context
            if isinstance(parent_cmd, click.Group) and child_path:
                self._execute_child_command(parent_cmd, parent_ctx, child_path, child_args)

    def _execute_child_command(
        self, parent_group: click.Group, parent_ctx: click.Context, 
        child_path: List[str], child_args: List[str]
    ) -> None:
        """
        Execute child command with proper parent context inheritance.
        
        This follows Click's Group.invoke() pattern for maintaining context chains.
        """
        if not child_path:
            return

        child_cmd_name = child_path[0]
        remaining_path = child_path[1:]

        # Resolve child command
        child_cmd = parent_group.get_command(parent_ctx, child_cmd_name)
        if child_cmd is None:
            raise ValueError(f"Child command not found: {child_cmd_name}")

        # Create child context with parent context (this enables context inheritance)
        child_ctx = child_cmd.make_context(child_cmd_name, child_args, parent=parent_ctx)
        
        with child_ctx:
            if remaining_path and isinstance(child_cmd, click.Group):
                # Continue with nested child commands
                self._execute_child_command(child_cmd, child_ctx, remaining_path, [])
            else:
                # Execute the final child command
                child_cmd.invoke(child_ctx)

    def _parse_command_chain_args(
        self, cli_group: click.Group, parent_cmd_name: str, 
        child_path: List[str], all_args: List[str]
    ) -> tuple[List[str], List[str]]:
        """
        Parse arguments to separate parent and child command arguments.
        
        This is a simplified implementation that assumes all arguments
        belong to the final child command. A more sophisticated implementation
        would parse the argument structure to properly distribute arguments
        between parent and child commands.
        
        Returns:
            Tuple of (parent_args, child_args)
        """
        # For now, assume all arguments go to the child command
        # Parent commands typically use options that are parsed separately
        parent_args: List[str] = []
        child_args = all_args.copy()
        
        # TODO: Implement proper argument parsing to distribute arguments
        # between parent and child commands based on their parameter definitions
        
        return parent_args, child_args

    def _build_command_args_for_path(
        self, path_segments: List[str], tool_name: str, parameters: Dict[str, Any]
    ) -> List[str]:
        """Build command arguments for a command path."""
        # Find the final command in the path to build arguments for
        final_command = self._find_command(self.cli_group, path_segments)
        return self._build_command_args(final_command, tool_name, parameters)

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

