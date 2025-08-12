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
from .scanner import get_positional_args, get_parent_command, get_child_command_name, get_command_path_components, get_child_command, scan_click_command


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
        """Execute a Click command using Click's native main() method."""
        command_args = self._prepare_command_arguments(tool_name, parameters)
        return self._run_click_command(command_args)

    def _prepare_command_arguments(self, tool_name: str, parameters: Dict[str, Any]) -> List[str]:
        """Prepare command line arguments based on tool type."""
        if get_parent_command(tool_name) is not None:
            return self._prepare_hierarchical_arguments(tool_name, parameters)
        else:
            return self._prepare_simple_arguments(tool_name, parameters)
    
    def _prepare_hierarchical_arguments(self, tool_name: str, parameters: Dict[str, Any]) -> List[str]:
        """Prepare arguments for hierarchical tools (parent command + child command)."""
        args: List[str] = []
        
        # Get parent command and child command name - no string parsing needed!
        parent_cmd = get_parent_command(tool_name)
        child_name = get_child_command_name(tool_name)
        child_cmd = get_child_command(tool_name)
        
        if not parent_cmd or not child_name or not child_cmd:
            return args  # Should not happen since we check this before calling
        
        # Convert child name to CLI format (underscores to dashes)
        child_cli_name = child_name.replace("_", "-")
        
        # Filter parameters to only include parent parameters
        parent_param_names = {param.name for param in parent_cmd.params}
        parent_parameters = {k: v for k, v in parameters.items() if k in parent_param_names}
        
        # Add parent parameters first
        parent_args = self._convert_parameters_to_args(parent_parameters, [], parent_cmd.params)
        args.extend(parent_args)
        
        # Add child command name
        args.append(child_cli_name)
        
        # Add child parameters using stored command reference (no string matching!)
        child_param_names = {param.name for param in child_cmd.params}
        child_parameters = {k: v for k, v in parameters.items() if k in child_param_names}
        
        positional_order = get_positional_args(tool_name)
        child_args = self._convert_parameters_to_args(child_parameters, positional_order, child_cmd.params)
        args.extend(child_args)
        
        return args
    
    def _prepare_simple_arguments(self, tool_name: str, parameters: Dict[str, Any]) -> List[str]:
        """Prepare arguments for simple tools (direct command execution)."""
        # Use stored path components instead of parsing dotted paths
        path_components = get_command_path_components(tool_name)
        parameter_args = self._convert_parameters_to_args(
            parameters, 
            get_positional_args(tool_name)
        )
        return path_components + parameter_args
    
    def _run_click_command(self, args: List[str]) -> Dict[str, Any]:
        """Execute the Click command with prepared arguments."""
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                # Use Click's main() method which handles parent-child execution naturally
                self.cli_group.main(args=args, standalone_mode=False)
            except Exception as e:
                raise ValueError(f"Command execution failed: {str(e)}") from e
        
        return {"output": output.getvalue().rstrip()}

    def _convert_parameters_to_args(
        self, 
        parameters: Dict[str, Any], 
        positional_order: List[str],
        param_definitions: Optional[List[click.Parameter]] = None
    ) -> List[str]:
        """Convert parameters to CLI arguments."""
        args = []
        
        # Add positional arguments in order
        for param_name in positional_order:
            if param_name in parameters:
                args.append(str(parameters[param_name]))
        
        # Add options
        if param_definitions:
            # Use Click parameter definitions for accurate type handling
            for param in param_definitions:
                param_name = param.name
                if param_name in parameters and param_name not in positional_order:
                    value = parameters[param_name]
                    if isinstance(param, click.Option):
                        self._add_option_arg(args, param_name, value, 
                                           is_bool=isinstance(param.type, click.types.BoolParamType))
        else:
            # Fallback to simple type detection
            for name, value in parameters.items():
                if name not in positional_order:
                    self._add_option_arg(args, name, value, is_bool=isinstance(value, bool))
        
        return args

    def _add_option_arg(self, args: List[str], param_name: str, value: Any, is_bool: bool) -> None:
        """Add an option argument to the args list."""
        if is_bool:
            if value:
                args.append(f"--{param_name.replace('_', '-')}")
        else:
            args.extend([f"--{param_name.replace('_', '-')}", str(value)])




